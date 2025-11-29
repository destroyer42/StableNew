from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from src.api.webui_process_manager import WebUIProcessManager, build_default_webui_process_config
from src.gui.app_state_v2 import AppStateV2
from src.gui.gui_invoker import GuiInvoker
from src.gui.layout_v2 import configure_root_grid
from src.gui.theme_v2 import apply_theme, BACKGROUND_ELEVATED, TEXT_PRIMARY, ACCENT_GOLD
from src.gui.sidebar_panel_v2 import SidebarPanelV2
from src.gui.pipeline_panel_v2 import PipelinePanelV2
from src.gui.preview_panel_v2 import PreviewPanelV2
from src.gui.status_bar_v2 import StatusBarV2
from src.gui.views.prompt_tab_frame import PromptTabFrame
from src.gui.views.pipeline_tab_frame import PipelineTabFrame
from src.gui.views.learning_tab_frame import LearningTabFrame


class HeaderZone(ttk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master, style="Panel.TFrame")
        self.run_button = ttk.Button(self, text="Run", style="Primary.TButton")
        self.stop_button = ttk.Button(self, text="Stop", style="Secondary.TButton")
        self.preview_button = ttk.Button(self, text="Preview", style="Secondary.TButton")
        self.settings_button = ttk.Button(self, text="Settings", style="Secondary.TButton")
        self.help_button = ttk.Button(self, text="Help", style="Secondary.TButton")

        for idx, btn in enumerate(
            [
                self.run_button,
                self.stop_button,
                self.preview_button,
                self.settings_button,
                self.help_button,
            ]
        ):
            btn.grid(row=0, column=idx, padx=4, pady=4)


class LeftZone(ttk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master, style="Panel.TFrame")
        self.load_pack_button = ttk.Button(self, text="Load Pack")
        self.edit_pack_button = ttk.Button(self, text="Edit Pack")
        self.packs_list = tk.Listbox(self, exportselection=False)
        self.preset_combo = ttk.Combobox(self, values=[])

        self.load_pack_button.pack(fill="x", padx=4, pady=2)
        self.edit_pack_button.pack(fill="x", padx=4, pady=2)
        self.packs_list.pack(fill="both", expand=True, padx=4, pady=4)
        ttk.Label(self, text="Preset").pack(anchor="w", padx=4)
        self.preset_combo.pack(fill="x", padx=4, pady=2)


class BottomZone(ttk.Frame):
    def __init__(self, master: tk.Misc, *, controller=None, app_state=None):
        super().__init__(master, style="StatusBar.TFrame")
        self.status_bar_v2 = StatusBarV2(self, controller=controller, app_state=app_state)
        self.status_bar_v2.pack(side=tk.TOP, fill="x", padx=4, pady=(4, 2))

        # Compatibility aliases expected by AppController-based tests.
        self.api_status_label = getattr(getattr(self.status_bar_v2, "webui_panel", None), "status_label", None)
        if self.api_status_label is None:
            self.api_status_label = ttk.Label(self, text="API: Unknown", style="StatusBar.TLabel")
        self.status_label = getattr(self.status_bar_v2, "status_label", ttk.Label(self, text="Status: Idle"))

        log_style_kwargs = {"bg": BACKGROUND_ELEVATED, "fg": TEXT_PRIMARY, "insertbackground": TEXT_PRIMARY}
        self.log_text = tk.Text(self, height=6, **log_style_kwargs)
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(2, 4))


class MainWindowV2:
    """Minimal V2 spine used by legacy controllers and new app entrypoint."""

    def __init__(
        self,
        root: tk.Tk,
        app_state: AppStateV2 | None = None,
        webui_manager: WebUIProcessManager | None = None,
        app_controller=None,
        packs_controller=None,
        pipeline_controller=None,
    ) -> None:
        self.root = root
        self._disposed = False
        self.app_state = app_state or AppStateV2()
        self.webui_process_manager = webui_manager
        self.app_controller = app_controller
        self.packs_controller = packs_controller
        self.pipeline_controller = pipeline_controller
        self._invoker = GuiInvoker(self.root)
        self.app_state.set_invoker(self._invoker)

        self.root.title("StableNew V2 (Spine)")
        self.root.geometry("1400x850")
        self.root.minsize(1024, 700)
        apply_theme(self.root)
        configure_root_grid(self.root)


        # Use LayoutManagerV2 for all panel placement
        from src.gui.panels_v2.layout_manager_v2 import LayoutManagerV2
        self.layout_manager_v2 = LayoutManagerV2(self)
        self.layout_manager_v2.attach_panels()

        # Provide delegation helpers expected by controllers/tests
        self.after = self.root.after  # type: ignore[attr-defined]

        self._wire_toolbar_callbacks()
        self._wire_status_bar()

        # Make main content row stretch
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.root.bind("<Destroy>", self._on_destroy, add="+")
        except Exception:
            pass

    # Compatibility hook for controllers
    def connect_controller(self, controller) -> None:
        self.controller = controller
        if self.app_controller is None:
            self.app_controller = controller
            self._wire_toolbar_callbacks()
        if getattr(self, "status_bar_v2", None):
            try:
                self.status_bar_v2.controller = controller
            except Exception:
                pass

    def update_pack_list(self, packs: list[str]) -> None:
        left = getattr(self, "left_zone", None)
        if hasattr(left, "set_pack_names"):
            try:
                left.set_pack_names(packs)
                return
            except Exception:
                pass
        lb = getattr(left, "packs_list", None)
        if lb is None:
            return
        lb.delete(0, "end")
        for name in packs:
            lb.insert("end", name)

    def _wire_toolbar_callbacks(self) -> None:
        header = getattr(self, "header_zone", None)
        if header is None:
            return
        # Prefer the lightweight AppController wiring if provided
        ctrl = self.app_controller
        if ctrl:
            for attr, btn in [
                ("on_run_clicked", header.run_button),
                ("on_stop_clicked", header.stop_button),
                ("on_preview_clicked", header.preview_button),
                ("on_open_settings", header.settings_button),
                ("on_help_clicked", header.help_button),
            ]:
                callback = getattr(ctrl, attr, None)
                if callable(callback):
                    try:
                        btn.configure(command=callback)
                    except Exception:
                        pass
            return

        # Best-effort fallback wiring using pipeline/pack controllers
        if self.pipeline_controller:
            start_cb = getattr(self.pipeline_controller, "start_pipeline", None) or getattr(
                self.pipeline_controller, "start", None
            )
            stop_cb = getattr(self.pipeline_controller, "stop_pipeline", None) or getattr(
                self.pipeline_controller, "stop", None
            )
            if callable(start_cb):
                header.run_button.configure(command=start_cb)
            if callable(stop_cb):
                header.stop_button.configure(command=stop_cb)

    def _wire_left_zone_callbacks(self) -> None:
        left = getattr(self, "left_zone", None)
        if left is None:
            return

        ctrl = self.packs_controller or self.app_controller
        if not ctrl:
            return

        if hasattr(left, "load_pack_button"):
            cb = getattr(ctrl, "on_load_pack", None) or getattr(ctrl, "load_pack", None)
            if callable(cb):
                try:
                    left.load_pack_button.configure(command=cb)
                except Exception:
                    pass

        if hasattr(left, "edit_pack_button"):
            cb = getattr(ctrl, "on_edit_pack", None) or getattr(ctrl, "edit_pack", None)
            if callable(cb):
                try:
                    left.edit_pack_button.configure(command=cb)
                except Exception:
                    pass

        if hasattr(left, "packs_list") and callable(getattr(ctrl, "on_pack_selected", None)):
            try:
                left.packs_list.bind("<<ListboxSelect>>", lambda _e: self._handle_pack_selection(ctrl))
            except Exception:
                pass

        if hasattr(left, "preset_combo") and callable(getattr(ctrl, "on_preset_selected", None)):
            try:
                left.preset_combo.bind(
                    "<<ComboboxSelected>>", lambda _e: ctrl.on_preset_selected(left.preset_combo.get())
                )
            except Exception:
                pass

    def _handle_pack_selection(self, ctrl) -> None:
        lb = getattr(getattr(self, "left_zone", None), "packs_list", None)
        if lb is None:
            return
        try:
            selection = lb.curselection()
            if selection:
                ctrl.on_pack_selected(int(selection[0]))
        except Exception:
            pass

    def _on_close(self) -> None:
        self.cleanup()
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_destroy(self, event) -> None:
        if event is not None and getattr(event, "widget", None) not in {None, self.root}:
            return
        self.cleanup()

    def cleanup(self) -> None:
        """Best-effort shutdown to make Tk teardown safe for tests and runtime."""
        if self._disposed:
            return
        self._disposed = True

        try:
            self.app_state.disable_notifications()
        except Exception:
            pass

        try:
            if self._invoker:
                self._invoker.dispose()
        except Exception:
            pass

        # Stop background work if controllers expose hooks.
        try:
            if self.pipeline_controller:
                stop = getattr(self.pipeline_controller, "stop_all", None) or getattr(
                    self.pipeline_controller, "shutdown", None
                )
                if callable(stop):
                    stop()
        except Exception:
            pass

        try:
            if self.app_controller:
                stop = getattr(self.app_controller, "stop_all_background_work", None) or getattr(
                    self.app_controller, "stop_all", None
                )
                if callable(stop):
                    stop()
        except Exception:
            pass

        try:
            if self.webui_process_manager:
                stop = getattr(self.webui_process_manager, "shutdown", None) or getattr(
                    self.webui_process_manager, "stop", None
                )
                if callable(stop):
                    stop()
        except Exception:
            pass

    def _wire_status_bar(self) -> None:
        if not getattr(self, "status_bar_v2", None):
            return
        try:
            self.status_bar_v2.app_state = self.app_state
            if hasattr(self.app_state, "subscribe"):
                self.app_state.subscribe("status_text", self.status_bar_v2._sync_status_text)
            try:
                self.status_bar_v2._sync_status_text()
            except Exception:
                pass
        except Exception:
            pass

    def _handle_apply_pack(self, prompt_text: str, summary) -> None:
        if getattr(self, "pipeline_panel", None) and hasattr(self.pipeline_panel, "set_prompt"):
            try:
                self.pipeline_panel.set_prompt(prompt_text or "")
            except Exception:
                pass
        if getattr(self, "app_state", None):
            try:
                pack_name = getattr(summary, "name", None)
                if pack_name:
                    self.app_state.set_current_pack(pack_name)
                    self.app_state.set_status_text(f"Pack applied: {pack_name}")
            except Exception:
                pass



def run_app(
    root: Optional[tk.Tk] = None,
    webui_manager: Optional[WebUIProcessManager] = None,
    app_controller=None,
    packs_controller=None,
    pipeline_controller=None,
) -> None:
    """Launch the V2 application shell."""

    if root is None:
        root = tk.Tk()

    if webui_manager is None:
        proc_config = build_default_webui_process_config()
        if proc_config:
            webui_manager = WebUIProcessManager(proc_config)
            if proc_config.autostart_enabled:
                try:
                    webui_manager.start()
                except Exception:
                    pass

    app_state = AppStateV2()
    MainWindowV2(
        root=root,
        app_state=app_state,
        webui_manager=webui_manager,
        app_controller=app_controller,
        packs_controller=packs_controller,
        pipeline_controller=pipeline_controller,
    )
    root.mainloop()


# Backward-compatible alias expected by controllers/tests
MainWindow = MainWindowV2
