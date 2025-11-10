"""
Prompt Pack Panel - UI component for managing and selecting prompt packs.
"""

import logging
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from ..utils.file_io import get_prompt_packs
from .tooltip import Tooltip

logger = logging.getLogger(__name__)


class PromptPackPanel(ttk.Frame):
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
        self._last_curselection: tuple[int, ...] = ()

        # Build UI
        self._build_ui()

        # Load initial packs
        self.refresh_packs(silent=True)

        # Start a lightweight watcher that notices programmatic selection changes
        # (e.g., tests calling selection_set) and forwards them to our callback.
        # This ensures mediator callbacks fire even without actual user events.
        # Poll at a small interval to avoid saturating Tk's idle loop
        self.after(150, self._watch_selection_change)

    def _attach_tooltip(self, widget: tk.Widget, text: str, delay: int = 1500) -> None:
        """Best-effort tooltip attachment that won't crash headless tests."""
        try:
            Tooltip(widget, text, delay=delay)
        except Exception:
            pass

    def _watch_selection_change(self) -> None:
        """Detect selection changes even when set programmatically and notify."""
        try:
            current = self.packs_listbox.curselection()
        except Exception:
            current = ()
        if current != self._last_curselection:
            self._last_curselection = current
            # Defer to the standard handler to update highlights and notify
            self._on_pack_selection_changed()
        # Keep watching while widget exists
        try:
            # Keep polling at a low frequency
            self.after(150, self._watch_selection_change)
        except Exception:
            pass

    def _build_ui(self):
        """Build the panel UI."""
        # Prompt packs section - compact
        packs_frame = ttk.LabelFrame(self, text="📝 Prompt Packs", style="Dark.TFrame", padding=5)
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
            width=15,
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
        self._attach_tooltip(delete_btn, "Remove the saved list entry (does not delete pack files).")

    def _build_packs_listbox(self, parent):
        """Build the packs listbox with scrollbar."""
        packs_list_frame = ttk.Frame(parent, style="Dark.TFrame")
        packs_list_frame.pack(fill=tk.BOTH, expand=True)

        # Listbox with scrollbar
        listbox_frame = tk.Frame(packs_list_frame, bg="#2b2b2b")
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, bg="#404040", troughcolor="#2b2b2b")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.packs_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            exportselection=False,
            bg="#3d3d3d",
            fg="#ffffff",
            selectbackground="#0078d4",
            selectforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            borderwidth=2,
            highlightthickness=1,
            highlightcolor="#0078d4",
            activestyle="dotbox",
        )
        self.packs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.packs_listbox.yview)
        self._attach_tooltip(
            self.packs_listbox,
            "Ctrl/Cmd-click or Shift-click to select multiple packs. Selection persists even when focus changes.",
        )

        # Bind selection events
        self.packs_listbox.bind("<<ListboxSelect>>", self._on_pack_selection_changed)

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
        """
        Handle prompt pack selection changes.
        Args:
            event: The event object (optional)
        """
        selected_indices = self.packs_listbox.curselection()
        selected_packs = [self.packs_listbox.get(i) for i in selected_indices]
        if selected_packs:
            self._last_selected_pack = selected_packs[0]
            logger.info(f"PromptPackPanel: Pack selection changed: {selected_packs}")
        else:
            self._last_selected_pack = None
            logger.info("PromptPackPanel: No pack selected.")
        # Update visuals, but never block callback on styling errors (e.g., headless CI)
        try:
            self._update_selection_highlights()
        except Exception as exc:  # noqa: BLE001 - best-effort UI polish
            logger.debug("PromptPackPanel: highlight update skipped: %s", exc)
        if self._on_selection_changed:
            self._on_selection_changed(selected_packs)

    def _update_selection_highlights(self):
        """Update visual highlighting for selected items."""
        # Reset all items to default background
        for i in range(self.packs_listbox.size()):
            self.packs_listbox.itemconfig(i, {"bg": "#3d3d3d"})

        # Highlight selected items
        for index in self.packs_listbox.curselection():
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
        self.packs_listbox.delete(0, tk.END)
        for pack_file in pack_files:
            self.packs_listbox.insert(tk.END, pack_file.name)
        # Restore selection if possible
        if current_selection:
            for i in range(self.packs_listbox.size()):
                pack_name = self.packs_listbox.get(i)
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
        self.packs_listbox.delete(0, tk.END)
        for name in names:
            self.packs_listbox.insert(tk.END, name)
        if current_selection:
            for i in range(self.packs_listbox.size()):
                pack_name = self.packs_listbox.get(i)
                if pack_name in current_selection:
                    self.packs_listbox.selection_set(i)
        logger.info(f"PromptPackPanel: Populated {len(names)} packs (async)")

    def get_selected_packs(self) -> list[str]:
        """
        Get list of currently selected pack names.
        Returns:
            List of selected pack names
        """
        selected_indices = self.packs_listbox.curselection()
        return [self.packs_listbox.get(i) for i in selected_indices]

    def set_selected_packs(self, pack_names: list[str]) -> None:
        """
        Set the selected packs by name.
        Args:
            pack_names: List of pack names to select
        """
        self.packs_listbox.selection_clear(0, tk.END)
        for i in range(self.packs_listbox.size()):
            pack_name = self.packs_listbox.get(i)
            if pack_name in pack_names:
                self.packs_listbox.selection_set(i)
        logger.info(f"PromptPackPanel: Set selected packs: {pack_names}")
        self._on_pack_selection_changed()

    def select_first_pack(self) -> None:
        """Select the first pack if available."""
        if self.packs_listbox.size() > 0:
            self.packs_listbox.selection_set(0)
            self.packs_listbox.activate(0)
            logger.info("PromptPackPanel: First pack selected.")
            self._on_pack_selection_changed()

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
