import logging
import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from ..utils.file_io import get_prompt_packs
from .theme import ASWF_BLACK, ASWF_DARK_GREY, ASWF_GOLD
from .tooltip import Tooltip


"""
Prompt Pack Panel - UI component for managing and selecting prompt packs.
"""

logger = logging.getLogger(__name__)


class PromptPackPanel(ttk.Frame):
    def tk_safe_call(self, func, *args, wait=False, **kwargs):
        # (removed local imports; all imports are now at the top of the file)
        if threading.current_thread() is threading.main_thread():
            return func(*args, **kwargs)
        if not wait:
            self.after(0, lambda: func(*args, **kwargs))
            return None
        q: queue.Queue = queue.Queue(maxsize=1)

        def wrapper():
            try:
                q.put(func(*args, **kwargs))
            except Exception as e:
                q.put(e)

        self.after(0, wrapper)
        try:
            result = q.get(timeout=2)
        except queue.Empty:
            logging.error(
                "tk_safe_call: main thread did not process scheduled call within 2 seconds; possible deadlock."
            )
            return None
        if isinstance(result, Exception):
            raise result
        return result

    """
    A UI panel for managing and selecting prompt packs.

    This panel handles:
    - Displaying available prompt packs
    - Multi-select listbox for pack selection
    - Custom pack lists (save/load/edit/delete)
    - Refresh and advanced editor integration

    It communicates with a coordinator via callbacks for selection changes.
    """

    def __init__(
        self,
        parent: tk.Widget,
        coordinator: object | None = None,
        list_manager: object | None = None,
        on_selection_changed: Callable[[list[str]], None] | None = None,
        on_advanced_editor: Callable[[], None] | None = None,
        **kwargs,
    ):
        logger.debug("PromptPackPanel: init start")
        """
        Initialize the PromptPackPanel.

        Args:
            parent: Parent widget
            coordinator: Coordinator object (for mediator pattern)
            list_manager: PromptPackListManager instance for custom lists
            on_selection_changed: Callback when pack selection changes, receives list of selected pack names
            on_advanced_editor: Callback to open advanced editor
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.coordinator = coordinator
        self.list_manager = list_manager
        self._on_selection_changed = on_selection_changed
        self._on_advanced_editor = on_advanced_editor

        # Internal state
        self._last_selected_pack: str | None = None
        self._last_selection: list[str] = []
        self._suppress_selection_callbacks = False
        self._is_handling_selection = False

        # Build UI
        self._build_ui()

        # Load initial packs
        self.refresh_packs(silent=True)
        logger.debug("PromptPackPanel: initial refresh complete")

    def _attach_tooltip(self, widget: tk.Widget, text: str, delay: int = 1500) -> None:
        """Best-effort tooltip attachment that won't crash headless tests."""
        try:
            Tooltip(widget, text, delay=delay)
        except Exception:
            pass

    def _build_ui(self):
        """Build the panel UI."""
        # Prompt packs section - compact
        packs_frame = ttk.LabelFrame(self, text="📝 Prompt Packs", style="Dark.TLabelframe", padding=5)
        packs_frame.pack(fill=tk.BOTH, expand=True)

        # Compact list management
        self._build_list_management(packs_frame)

        # Multi-select listbox for prompt packs
        self._build_packs_listbox(packs_frame)

        # Pack management buttons
        self._build_pack_buttons(packs_frame)

    def _build_list_management(self, parent):
        """Build custom list management controls."""
        list_mgmt_frame = ttk.Frame(parent, style="Dark.TFrame")
        list_mgmt_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(list_mgmt_frame, text="Lists:", style="Dark.TLabel").pack(side=tk.LEFT)

        self.saved_lists_var = tk.StringVar()
        self.saved_lists_combo = ttk.Combobox(
            list_mgmt_frame,
            textvariable=self.saved_lists_var,
            style="Dark.TCombobox",
            width=24,
            state="readonly",
        )
        self.saved_lists_combo.pack(side=tk.LEFT, padx=(3, 2))

        # Update combo values if list_manager is available
        if self.list_manager:
            self.saved_lists_combo["values"] = self.list_manager.get_list_names()

        # Compact button layout
        btn_frame = ttk.Frame(list_mgmt_frame, style="Dark.TFrame")
        btn_frame.pack(side=tk.LEFT, padx=(3, 0))

        load_btn = ttk.Button(
            btn_frame, text="📁", command=self._load_pack_list, style="Dark.TButton", width=3
        )
        load_btn.grid(row=0, column=0, padx=1)
        self._attach_tooltip(
            load_btn,
            "Apply the packs stored in the selected list. Current selection is replaced.",
        )

        save_btn = ttk.Button(
            btn_frame, text="💾", command=self._save_pack_list, style="Dark.TButton", width=3
        )
        save_btn.grid(row=0, column=1, padx=1)
        self._attach_tooltip(
            save_btn,
            "Save the currently highlighted packs as a reusable list for future runs.",
        )

        edit_btn = ttk.Button(
            btn_frame, text="✏️", command=self._edit_pack_list, style="Dark.TButton", width=3
        )
        edit_btn.grid(row=0, column=2, padx=1)
        self._attach_tooltip(
            edit_btn,
            "Load the saved list into the selector so you can adjust it before saving again.",
        )

        delete_btn = ttk.Button(
            btn_frame, text="🗑️", command=self._delete_pack_list, style="Dark.TButton", width=3
        )
        delete_btn.grid(row=0, column=3, padx=1)
        self._attach_tooltip(
            delete_btn, "Remove the saved list entry (does not delete pack files)."
        )

    def _build_packs_listbox(self, parent):
        """Build the packs listbox with scrollbar."""
        packs_list_frame = ttk.Frame(parent, style="Dark.TFrame")
        packs_list_frame.pack(fill=tk.BOTH, expand=True)

        # Listbox with scrollbar
        listbox_frame = tk.Frame(packs_list_frame, bg=ASWF_DARK_GREY)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, bg=ASWF_DARK_GREY, troughcolor=ASWF_BLACK)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.packs_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            exportselection=False,
            borderwidth=2,
            highlightthickness=1,
            highlightcolor=ASWF_GOLD,
            activestyle="dotbox",
        )
        # Apply theme styling
        from .theme import Theme

        theme = Theme()
        theme.style_listbox(self.packs_listbox)
        self.packs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.packs_listbox.yview)
        self._attach_tooltip(
            self.packs_listbox,
            "Ctrl/Cmd-click or Shift-click to select multiple packs. Selection persists even when focus changes.",
        )

        # Bind selection events (use lambda + add to avoid clobbering default virtual bindings)
        self.packs_listbox.bind("<<ListboxSelect>>", self._on_pack_selection_changed, add="+")

    def _build_pack_buttons(self, parent):
        """Build pack management buttons."""
        pack_buttons_frame = ttk.Frame(parent, style="Dark.TFrame")
        pack_buttons_frame.pack(pady=(10, 0))

        refresh_btn = ttk.Button(
            pack_buttons_frame,
            text="🔄 Refresh Packs",
            command=lambda: self.refresh_packs(silent=False),
            style="Dark.TButton",
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._attach_tooltip(
            refresh_btn,
            "Rescan the packs folder and keep any current selection when possible.",
        )

        if self._on_advanced_editor:
            editor_btn = ttk.Button(
                pack_buttons_frame,
                text="✏️ Advanced Editor",
                command=self._on_advanced_editor,
                style="Dark.TButton",
            )
            editor_btn.pack(side=tk.LEFT)
            self._attach_tooltip(
                editor_btn,
                "Open the Advanced Prompt Editor for the first selected pack (multi-select safe).",
            )

    def _on_pack_selection_changed(self, event: object = None) -> None:
        if self._suppress_selection_callbacks:
            logger.debug("PromptPackPanel: selection change suppressed")
            return

        selected_indices = list(self.packs_listbox.curselection())
        selected_packs = [self.packs_listbox.get(i) for i in selected_indices]

        if selected_packs == self._last_selection:
            return
        self._last_selection = list(selected_packs)
        self._last_selected_pack = selected_packs[0] if selected_packs else None

        self._update_selection_highlights(selected_indices)

        if selected_packs:
            logger.info("PromptPackPanel: pack selection changed: %s", selected_packs)
        else:
            logger.info("PromptPackPanel: no pack selected")

        if self._on_selection_changed:
            try:
                self._on_selection_changed(selected_packs)
            except Exception:
                logger.exception("PromptPackPanel: selection callback failed")

    def _update_selection_highlights(self, selected_indices: list[int] | None = None):
        """Update visual highlighting for selected items."""
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self._update_selection_highlights(selected_indices))
            return
        size = self.packs_listbox.size()
        for i in range(size):
            self.packs_listbox.itemconfig(i, {"bg": "#3d3d3d"})
        if selected_indices is None:
            selected_indices = list(self.packs_listbox.curselection())
        for index in selected_indices:
            self.packs_listbox.itemconfig(index, {"bg": "#0078d4"})

    def refresh_packs(self, silent: bool = False) -> None:
        """
        Refresh the prompt packs list from the packs directory.
        Args:
            silent: If True, don't log the refresh action
        """
        packs_dir = Path("packs")
        pack_files = get_prompt_packs(packs_dir)
        # Save current selection
        current_selection = self.get_selected_packs()
        # Clear and repopulate
        self.tk_safe_call(self.packs_listbox.delete, 0, tk.END)
        for pack_file in pack_files:
            self.packs_listbox.insert(tk.END, pack_file.name)
        # Restore selection if possible
        if current_selection:
            size = self.tk_safe_call(self.packs_listbox.size, wait=True)
            for i in range(size):
                pack_name = self.tk_safe_call(self.packs_listbox.get, i, wait=True)
                if pack_name in current_selection:
                    self.packs_listbox.selection_set(i)
        if not silent:
            logger.info(f"PromptPackPanel: Refreshed, found {len(pack_files)} prompt packs.")

    def populate(self, packs: list[Path] | list[str]) -> None:
        """Populate the listbox with provided pack entries on the Tk thread.

        Args:
            packs: List of Path or str representing pack files
        """
        # Normalize to names
        names: list[str] = []
        for p in packs:
            try:
                names.append(p.name if isinstance(p, Path) else str(p))
            except Exception:
                continue

        # Preserve selection
        current_selection = self.get_selected_packs()
        self.tk_safe_call(self.packs_listbox.delete, 0, tk.END)
        for name in names:
            self.packs_listbox.insert(tk.END, name)
        if current_selection:
            size = self.tk_safe_call(self.packs_listbox.size, wait=True)
            for i in range(size):
                pack_name = self.tk_safe_call(self.packs_listbox.get, i, wait=True)
                if pack_name in current_selection:
                    self.packs_listbox.selection_set(i)
        logger.debug("PromptPackPanel: populated %s packs (async)", len(names))

    def get_selected_packs(self) -> list[str]:
        """
        Get list of currently selected pack names.
        Returns:
            List of selected pack names
        """
        selected_indices = self.tk_safe_call(self.packs_listbox.curselection)
        return [self.packs_listbox.get(i) for i in selected_indices]

    def set_selected_packs(self, pack_names: list[str]) -> None:
        """
        Set the selected packs by name.
        Args:
            pack_names: List of pack names to select
        """
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self.set_selected_packs(pack_names))
            return

        desired = {str(name) for name in pack_names}
        selected_indices: list[int] = []
        self._suppress_selection_callbacks = True
        try:
            self.packs_listbox.selection_clear(0, tk.END)
            for i in range(self.packs_listbox.size()):
                pack_name = self.packs_listbox.get(i)
                if pack_name in desired:
                    self.packs_listbox.selection_set(i)
                    selected_indices.append(i)
            if selected_indices:
                self.packs_listbox.activate(selected_indices[0])
            elif self.packs_listbox.size() > 0:
                self.packs_listbox.activate(0)
            self._update_selection_highlights(selected_indices)
        finally:
            self._suppress_selection_callbacks = False

        logger.debug("PromptPackPanel: set_selected_packs -> %s", pack_names)
        self._on_pack_selection_changed()

    def select_first_pack(self) -> None:
        """Select the first pack if available."""
        size = self.tk_safe_call(self.packs_listbox.size)
        if size > 0:
            first_name = self.packs_listbox.get(0)
            self.set_selected_packs([first_name])
            logger.debug("PromptPackPanel: first pack selected via helper")

    def _load_pack_list(self):
        """Load saved pack list."""
        if not self.list_manager:
            messagebox.showwarning("No Manager", "List manager not configured")
            return

        list_name = self.saved_lists_var.get()
        if not list_name:
            return

        pack_list = self.list_manager.get_list(list_name)
        if pack_list is None:
            return

        # Set selection to the packs in the list
        self.set_selected_packs(pack_list)
        logger.info(f"Loaded pack list: {list_name}")

    def _save_pack_list(self):
        """Save current pack selection as list."""
        if not self.list_manager:
            messagebox.showwarning("No Manager", "List manager not configured")
            return
        selected_packs = self.get_selected_packs()
        if not selected_packs:
            messagebox.showwarning("No Selection", "Please select prompt packs first")
            return

        list_name = simpledialog.askstring("Save List", "Enter list name:")
        if not list_name:
            return

        if self.list_manager.save_list(list_name, selected_packs):
            # Update combo box
            self.saved_lists_combo["values"] = self.list_manager.get_list_names()
            logger.info(f"Saved pack list: {list_name}")
            messagebox.showinfo("Success", f"List '{list_name}' saved successfully")
        else:
            messagebox.showerror("Save Error", "Failed to save list")

    def _edit_pack_list(self):
        """Edit existing pack list."""
        if not self.list_manager:
            messagebox.showwarning("No Manager", "List manager not configured")
            return

        list_name = self.saved_lists_var.get()
        if not list_name:
            messagebox.showinfo("No List Selected", "Please select a list to edit")
            return

        # Load the list for editing
        self._load_pack_list()
        messagebox.showinfo(
            "Edit Mode",
            f"List '{list_name}' loaded for editing.\n" "Modify selection and save to update.",
        )

    def _delete_pack_list(self):
        """Delete saved pack list."""
        if not self.list_manager:
            messagebox.showwarning("No Manager", "List manager not configured")
            return

        list_name = self.saved_lists_var.get()
        if not list_name:
            return

        if messagebox.askyesno("Confirm Delete", f"Delete list '{list_name}'?"):
            if self.list_manager.delete_list(list_name):
                # Update combo box
                self.saved_lists_combo["values"] = self.list_manager.get_list_names()
                self.saved_lists_var.set("")
                logger.info(f"Deleted pack list: {list_name}")
                messagebox.showinfo("Success", f"List '{list_name}' deleted")
            else:
                messagebox.showerror("Delete Error", "Failed to delete list")
