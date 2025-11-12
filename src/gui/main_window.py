"""Modern Tkinter GUI for Stable Diffusion pipeline with dark theme"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.simpledialog
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from ..api import SDWebUIClient
from ..pipeline import Pipeline, VideoCreator
from ..pipeline.variant_planner import apply_variant_to_config, build_variant_plan
from ..utils import ConfigManager, PreferencesManager, StructuredLogger, setup_logging
from ..utils.aesthetic import detect_aesthetic_extension
from ..utils.file_io import get_prompt_packs, read_prompt_pack
from ..utils.randomizer import PromptRandomizer, PromptVariant
from ..utils.webui_discovery import find_webui_api_port, launch_webui_safely, validate_webui_health
from .advanced_prompt_editor import AdvancedPromptEditor
from .api_status_panel import APIStatusPanel
from .config_panel import ConfigPanel
from .controller import PipelineController
from .enhanced_slider import EnhancedSlider
from .log_panel import LogPanel, TkinterLogHandler
from .pipeline_controls_panel import PipelineControlsPanel
from .prompt_pack_list_manager import PromptPackListManager
from .prompt_pack_panel import PromptPackPanel
from .state import CancellationError, GUIState, StateManager
from .tooltip import Tooltip

logger = logging.getLogger(__name__)
logging.raiseExceptions = False


class StableNewGUI:
    def __init__(self, *args, **kwargs):
        # ---- double-init guard ----
        if getattr(self, "_constructed", False):
            print("[DIAG] StableNewGUI.__init__: called twice; ignoring second call")
            return
        self._constructed = True

        print("[DIAG] StableNewGUI.__init__ (main): start")

        # ---- create Tk root first ----
        import tkinter as tk
        self.root = tk.Tk()

        # ---- build UI widgets/panels (no IO here) ----
        self._build_widgets()        # create frames, panels, variables
        self._wire_events()          # bind <<ListboxSelect>>, buttons, etc.

        # ---- install runtime guards now that root exists ----
        self._install_tk_exception_reporter()   # sets self.root.report_callback_exception
        self._start_heartbeat()                 # logger.debug heartbeat via root.after

        # ---- defer initialization so Tk can paint ----
        self.root.after(0, self._initialize_ui_state)          # UI-only work
        self.root.after(250, self._start_webui_discovery_async)  # network in worker

        print("[DIAG] StableNewGUI.__init__ (main): scheduling done, entering mainloop")
        self.root.mainloop()

    def _install_tk_exception_reporter(self):
        import logging, traceback
        log = logging.getLogger(__name__)

        def _transition_error():
            try:
                self.controller.lifecycle_event.set()
            except Exception:
                pass
            try:
                self.root.after(0, lambda: self.state_manager.transition_to(GUIState.ERROR))
            except Exception:
                pass

        def _report_callback_exception(exc, val, tb):
            log.error("Tk callback exception: %s: %s", getattr(exc, "__name__", exc), val)
            for line in traceback.format_tb(tb):
                log.error(line.rstrip())
            _transition_error()

        self.root.report_callback_exception = _report_callback_exception
        print("[DIAG] Tk exception reporter installed")

    def _start_heartbeat(self):
        import logging
        log = logging.getLogger(__name__)
        def _hb():
            log.debug("[HEARTBEAT] ui alive")
            self.root.after(1000, _hb)
        self.root.after(1000, _hb)
        print("[DIAG] Heartbeat scheduled")

    def _initialize_ui_state(self):
        print("[DIAG] _initialize_ui_state: entered")
        try:
            self.prompt_pack_panel.select_first_pack()  # must be UI-only
        except Exception as e:
            import logging; logging.getLogger(__name__).exception("init UI state failed: %s", e)
            try:
                self.root.after(0, lambda: self.state_manager.transition_to(GUIState.ERROR))
            except Exception:
                pass

    def _start_webui_discovery_async(self):
        print("[DIAG] _start_webui_discovery_async: spawn worker")
        import threading, logging
        log = logging.getLogger(__name__)

        def worker():
            try:
                status = self.webui_discovery.discover(timeout=(1.5, 6.0))  # no Tk calls here
                self.root.after(0, lambda: self._apply_webui_status(status))
            except Exception as e:
                log.exception("WebUI discovery failed: %s", e)
                self.root.after(0, lambda: self._apply_webui_error(e))

        threading.Thread(target=worker, daemon=True).start()
    def _safe_messagebox(self, kind: str, title: str, text: str) -> None:
        """Thread-safe messagebox helper (runs on main thread).
        See: BUG_FIX_GUI_HANG_SECOND_RUN.md for rationale.
        """
        if os.getenv("STABLENEW_NO_ERROR_DIALOG") in {"1","true","TRUE"} and kind.lower() in {"error","warning"}:
            logger.warning(f"[DIAG] Messagebox suppressed: {title}: {text}")
            return
        def _do():
            try:
                getattr(messagebox, f"show{kind}")(title, text)
            except Exception:
                logger.exception("messagebox failed")
        try:
            self.root.after(0, _do)
        except Exception:
            _do()

    def force_reset(self):
        """Force a full GUI and state reset after a crash or error."""
        logger.info("[DIAG] StableNewGUI.force_reset: starting reset", extra={"flush": True})
        # Destroy and recreate PromptPackPanel and other panels as needed
        try:
            if hasattr(self, 'prompt_pack_panel') and self.prompt_pack_panel.winfo_exists():
                self.prompt_pack_panel.destroy()
            # Recreate PromptPackPanel
            self.prompt_pack_panel = PromptPackPanel(self.root, coordinator=self)
            self.prompt_pack_panel.pack(fill=tk.BOTH, expand=True)
            logger.info("[DIAG] StableNewGUI.force_reset: PromptPackPanel recreated", extra={"flush": True})
        except Exception as exc:
            logger.error(f"[DIAG] StableNewGUI.force_reset: error recreating PromptPackPanel: {exc}", exc_info=True, extra={"flush": True})
        # Reset other internal state as needed (add more panels if required)
        self._error_dialog_shown = False
        # Optionally, reset controller, config, etc. if needed
        logger.info("[DIAG] StableNewGUI.force_reset: reset complete", extra={"flush": True})

    def __init__(self):
        """Initialize GUI"""
        # Guard against multiple instantiations or long blocking init
        self._init_start_ts = time.time()
        # Diagnostics flag and helper for startup tracing
        self._diag_enabled = os.environ.get("STABLENEW_DIAG", "").lower() in {"1", "true", "yes"}
        def _diag(msg: str) -> None:
            if self._diag_enabled:
                try:
                    ts = f"{time.time() - self._init_start_ts:0.3f}s"
                    logger.info(f"[DIAG][startup {ts}] {msg}")
                except Exception:
                    pass
        _diag("constructor start")
        self.root = tk.Tk()
        self.root.title("StableNew - Stable Diffusion WebUI Automation")
        # Widen default window to take advantage of horizontal space for wider dropdowns
        self.root.geometry("1550x1020+60+40")
        self.root.configure(bg="#2b2b2b")

        # Ensure window is visible and on top
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(lambda: self.root.attributes("-topmost", False))

        # Prevent window from being minimized or hidden
        self.root.state("normal")

        # Initialize components
        self.config_manager = ConfigManager()
        self.preferences_manager = PreferencesManager()
        self.preferences = self.preferences_manager.load_preferences(
            self.config_manager.get_default_config()
        )
        self.structured_logger = StructuredLogger()
        self.client = None
        self.pipeline = None
        self.video_creator = VideoCreator()
        self.available_hypernetworks: list[str] = ["None"]

        # Initialize state management and controller
        self.state_manager = StateManager()
        self.controller = PipelineController(self.state_manager)

        # Progress/UI state
        self.progress_message_var = tk.StringVar(value="Ready")
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_percent_var = tk.StringVar(value="0%")
        self.eta_var = tk.StringVar(value="ETA: --")
        self.progress_bar: ttk.Progressbar | None = None
        # Back-compat aliases expected by tests
        self.progress_status_var = self.progress_message_var
        self.progress_eta_var = self.eta_var

        # Register progress callbacks with a flexible API to support test harness controllers
        registered = False

        # Compatibility wrapper: allow (percent, status) signature
        def _compat_progress(*args, **kwargs):
            try:
                if len(args) >= 1:
                    self._queue_progress_update(args[0])
                if len(args) >= 2:
                    self._queue_status_update(args[1])
            except Exception:
                pass

        for meth in (
            "set_progress_callbacks",
            "register_progress_callbacks",
            "configure_progress_callbacks",
        ):
            if hasattr(self.controller, meth):
                try:
                    getattr(self.controller, meth)(
                        progress=_compat_progress,
                        eta=self._queue_eta_update,
                        reset=lambda: self._reset_progress_ui(),
                        status=self._queue_status_update,
                    )
                    registered = True
                    break
                except Exception:
                    pass
        if not registered:
            # Fall back to individual callbacks if supported
            if hasattr(self.controller, "set_progress_callback"):
                try:
                    self.controller.set_progress_callback(self._queue_progress_update)
                except Exception:
                    pass
            if hasattr(self.controller, "set_eta_callback"):
                try:
                    self.controller.set_eta_callback(self._queue_eta_update)
                except Exception:
                    pass
            if hasattr(self.controller, "set_status_callback"):
                try:
                    self.controller.set_status_callback(self._queue_status_update)
                except Exception:
                    pass

        # Initialize prompt pack list manager
        self.pack_list_manager = PromptPackListManager()

        # GUI state
        config_preferences = self.preferences.get("config", {})
        api_preferences = config_preferences.get("api", {})

        self.selected_packs = list(self.preferences.get("selected_packs", []))
        self.current_config = None
        self.api_connected = False
        self._last_selected_pack = None
        self.current_preset = self.preferences.get("preset", "default")
        self._refreshing_config = False  # Flag to prevent recursive refreshes
        # Error dialog control for tests
        self._error_dialog_shown = False
        self._force_error_status = False

        # Initialize GUI variables early
        self.api_url_var = tk.StringVar(
            value=api_preferences.get("base_url", "http://127.0.0.1:7860")
        )
        self.preset_var = tk.StringVar(value=self.current_preset)

        # Initialize other GUI variables that are used before UI building
        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.adetailer_enabled = tk.BooleanVar(value=False)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)
        self.loop_type_var = tk.StringVar(value="single")
        self.loop_count_var = tk.StringVar(value="1")
        self.pack_mode_var = tk.StringVar(value="selected")
        self.images_per_prompt_var = tk.StringVar(value="1")
        # Override: apply current GUI config to all selected packs when enabled
        self.override_pack_var = tk.BooleanVar(value=False)
        # Randomization & Aesthetic controls (populated when tab builds)
        self.randomization_vars: dict[str, tk.Variable] = {}
        self.randomization_widgets: dict[str, tk.Widget] = {}
        self.aesthetic_vars: dict[str, tk.Variable] = {}
        self.aesthetic_widgets: dict[str, tk.Widget] = {}
        self.aesthetic_embedding_var = tk.StringVar(value="None")
        (
            self.aesthetic_script_available,
            self.aesthetic_extension_root,
        ) = self._detect_aesthetic_extension_root()
        self.aesthetic_embeddings: list[str] = ["None"]
        self.aesthetic_status_var = tk.StringVar(value="")
        # Force status error label in tests when pipeline error occurs
        self._force_error_status = False

        # Status bar defaults
        self._progress_eta_default = "ETA: --"
        self._progress_idle_message = "Ready for next run"

        # Initialize metadata attributes early to avoid NameErrors
        self.schedulers = []
        self.upscaler_names = []
        self.vae_names = []

        # Initialize log panel early (before any log calls) to avoid AttributeError

        # Add proxy methods for consistent API (log_panel will be created in _build_bottom_panel)
        self.log_panel = None
        self.add_log = None
        self.log_text = None

        # Apply dark theme
        self._setup_dark_theme()

        # Load or create default preset
        self._ensure_default_preset()

        # Build UI
        self._build_ui()
        _diag("UI built")

        # Apply saved preferences after UI construction
        def _apply_prefs_task():
            _diag("apply_saved_preferences scheduling")
            self._apply_saved_preferences()
            _diag("apply_saved_preferences done")
        self.root.after(0, _apply_prefs_task)

        # Schedule a watchdog to detect hangs during early startup (logs only)
        def _startup_watchdog():
            try:
                elapsed = time.time() - self._init_start_ts
                if elapsed > 5 and not getattr(self, "_startup_completed", False):
                    logger.warning(
                        "Startup taking >5s; if window is unresponsive, enable STABLENEW_DIAG=1 for verbose traces"
                    )
                    if self._diag_enabled:
                        logger.info(f"[DIAG] watchdog fired at {elapsed:0.3f}s without completion flag")
            except Exception:
                pass
        self.root.after(6000, _startup_watchdog)

        # Auto-launch WebUI after the window is built to avoid blocking init
        try:
            self.root.after(0, self._launch_webui)
        except Exception:
            pass

        # Setup logging redirect
        setup_logging("INFO")

    def _setup_dark_theme(self):
        """Setup dark theme for the application"""
        style = ttk.Style()

        # Configure dark theme colors
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        button_bg = "#404040"
        button_active = "#505050"
        entry_bg = "#3d3d3d"

        self.root.configure(bg=bg_color)

        # Configure ttk styles
        style.theme_use("clam")

        style.configure("Dark.TFrame", background=bg_color, borderwidth=1, relief="flat")
        style.configure(
            "Dark.TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 9)
        )
        style.configure(
            "Dark.TButton",
            background=button_bg,
            foreground=fg_color,
            borderwidth=1,
            focuscolor="none",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Dark.TEntry",
            background=entry_bg,
            foreground=fg_color,
            borderwidth=1,
            insertcolor=fg_color,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Dark.TSpinbox",
            background=entry_bg,
            foreground=fg_color,
            fieldbackground=entry_bg,
            borderwidth=1,
            insertcolor=fg_color,
            font=("Segoe UI", 9),
        )
        # Fix Combobox dropdown styling
        style.configure(
            "Dark.TCombobox",
            background=entry_bg,
            foreground=fg_color,
            fieldbackground=entry_bg,
            selectbackground="#0078d4",
            selectforeground=fg_color,
            borderwidth=1,
            insertcolor=fg_color,
            font=("Segoe UI", 9),
        )

        style.configure(
            "Dark.TCheckbutton",
            background=bg_color,
            foreground=fg_color,
            focuscolor="none",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Dark.TRadiobutton",
            background=bg_color,
            foreground=fg_color,
            focuscolor="none",
            font=("Segoe UI", 9),
        )
        style.configure("Dark.TNotebook", background=bg_color, borderwidth=0)
        style.configure(
            "Dark.TNotebook.Tab",
            background=button_bg,
            foreground=fg_color,
            padding=[20, 8],
            borderwidth=0,
        )

        # Accent button styles for CTAs
        style.configure(
            "Accent.TButton",
            background="#0078d4",
            foreground=fg_color,
            borderwidth=1,
            focuscolor="none",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Danger.TButton",
            background="#dc3545",
            foreground=fg_color,
            borderwidth=1,
            focuscolor="none",
            font=("Segoe UI", 9, "bold"),
        )

        # Map states
        style.map(
            "Dark.TButton",
            background=[("active", button_active), ("pressed", "#0078d4")],
            foreground=[("active", fg_color)],
        )

        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", entry_bg)],
            selectbackground=[("readonly", "#0078d4")],
        )

        style.map(
            "Accent.TButton",
            background=[("active", "#106ebe"), ("pressed", "#005a9e")],
            foreground=[("active", fg_color)],
        )

        style.map(
            "Danger.TButton",
            background=[("active", "#c82333"), ("pressed", "#bd2130")],
            foreground=[("active", fg_color)],
        )

        style.map(
            "Dark.TNotebook.Tab", background=[("selected", "#0078d4"), ("active", button_active)]
        )

    def _launch_webui(self):
        """Auto-launch Stable Diffusion WebUI with improved detection (non-blocking)."""
        # Allow disabling auto-launch in headless/CI environments
        if os.environ.get("STABLENEW_NO_WEBUI", "").lower() in {"1", "true", "yes"}:
            logger.info("Auto-launch of WebUI disabled by STABLENEW_NO_WEBUI")
            return

        webui_path = Path("C:/Users/rober/stable-diffusion-webui/webui-user.bat")

        # Run discovery/launch in background to avoid freezing Tk mainloop
        def discovery_and_launch():
            # 1) Check if WebUI is already running (may take a few seconds)
            existing_url = find_webui_api_port()
            if existing_url:
                logger.info(f"WebUI already running at {existing_url}")
                self.root.after(0, lambda: self.api_url_var.set(existing_url))
                self.root.after(1000, self._check_api_connection)
                return

            # 2) Attempt to launch WebUI if path exists
            if webui_path.exists():
                self.root.after(0, lambda: self.log_message("🚀 Launching Stable Diffusion WebUI...", "INFO"))
                success = launch_webui_safely(webui_path, wait_time=15)
                if success:
                    # Find the actual URL and update UI
                    api_url = find_webui_api_port()
                    if api_url:
                        self.root.after(0, lambda: self.api_url_var.set(api_url))
                        self.root.after(1000, self._check_api_connection)
                    else:
                        self.root.after(
                            0,
                            lambda: self.log_message("⚠️ WebUI launched but API not found", "WARNING"),
                        )
                else:
                    self.root.after(0, lambda: self.log_message("❌ WebUI launch failed", "ERROR"))
            else:
                logger.warning("WebUI not found at expected location")
                self.root.after(0, lambda: self.log_message("⚠️ WebUI not found - please start manually", "WARNING"))
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "WebUI Not Found",
                        (
                            f"WebUI not found at: {webui_path}\n"
                            "Please start Stable Diffusion WebUI manually "
                            "with --api flag and click 'Check API'"
                        ),
                    ),
                )

        threading.Thread(target=discovery_and_launch, daemon=True).start()

    def _ensure_default_preset(self):
        """Ensure default preset exists and load it if set as startup default"""
        if "default" not in self.config_manager.list_presets():
            default_config = self.config_manager.get_default_config()
            self.config_manager.save_preset("default", default_config)

        # Check if a default preset is configured for startup
        default_preset_name = self.config_manager.get_default_preset()
        if default_preset_name:
            logger.info(f"Loading default preset on startup: {default_preset_name}")
            preset_config = self.config_manager.load_preset(default_preset_name)
            if preset_config:
                self.current_preset = default_preset_name
                self.current_config = preset_config
                # preset_var will be set in __init__ after this call
                self.preferences["preset"] = default_preset_name
            else:
                logger.warning(f"Failed to load default preset '{default_preset_name}'")

    def _build_ui(self):
        """Build the modern user interface"""
        # Create main container with minimal padding for space efficiency
        main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Compact top frame for API status
        self._build_api_status_frame(main_frame)

        # Main content + log splitter so the bottom panel stays visible
        vertical_split = ttk.Panedwindow(main_frame, orient=tk.VERTICAL)
        vertical_split.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Main content frame - optimized layout
        content_frame = ttk.Frame(vertical_split, style="Dark.TFrame")
        vertical_split.add(content_frame, weight=4)

        # Configure grid for better space utilization
        content_frame.columnconfigure(0, weight=0, minsize=280)  # Left: wider pack list for long names
        content_frame.columnconfigure(1, weight=1)  # Center: flexible config
        content_frame.columnconfigure(2, weight=0, minsize=260)  # Right: pipeline controls
        content_frame.rowconfigure(0, weight=1)

        # Left panel - Compact prompt pack selection
        self._build_prompt_pack_panel(content_frame)

        # Right panel - Configuration and pipeline controls (moved up)
        self._build_config_pipeline_panel(content_frame)

        # Bottom frame - Compact log and action buttons (resizable split)
        bottom_shell = ttk.Frame(vertical_split, style="Dark.TFrame")
        vertical_split.add(bottom_shell, weight=3)
        self._build_bottom_panel(bottom_shell)

        # Status bar - at the very bottom
        self._build_status_bar(main_frame)

        # Defer all heavy UI state initialization until after Tk mainloop starts
        try:
            self.root.after(0, self._initialize_ui_state_async)
        except Exception as exc:
            logger.warning("Failed to schedule UI state init: %s", exc)

        # Setup state callbacks
        self._setup_state_callbacks()

        # Start log update polling
        self._poll_controller_logs()

    def _build_api_status_frame(self, parent):
        """Build compact API connection status frame"""
        api_frame = ttk.Frame(parent, style="Dark.TFrame")
        api_frame.pack(fill=tk.X, pady=(0, 5))

        # Single line layout for space efficiency
        ttk.Label(api_frame, text="WebUI API:", style="Dark.TLabel", width=10).pack(side=tk.LEFT)
        api_entry = ttk.Entry(
            api_frame, textvariable=self.api_url_var, style="Dark.TEntry", width=30
        )
        api_entry.pack(side=tk.LEFT, padx=(2, 5))

        # Check API button - compact
        self.check_api_btn = ttk.Button(
            api_frame,
            text="Check API",
            command=self._check_api_connection,
            style="Dark.TButton",
            width=10,
        )
        self.check_api_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(
            self.check_api_btn,
            "Validate the WebUI API connection using the URL above. Refreshes model/vae lists when successful.",
        )

        # Status indicator panel
        self.api_status_panel = APIStatusPanel(api_frame, coordinator=self, style="Dark.TFrame")
        self.api_status_panel.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_prompt_pack_panel(self, parent):
        """Build compact prompt pack selection panel using PromptPackPanel component"""
        # Left panel container - grid layout
        left_panel = ttk.Frame(parent, style="Dark.TFrame")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Create the PromptPackPanel component
        self.prompt_pack_panel = PromptPackPanel(
            left_panel,
            coordinator=self,
            list_manager=self.pack_list_manager,
            on_selection_changed=self._on_pack_selection_changed_mediator,
            on_advanced_editor=self._open_advanced_editor,
            style="Dark.TFrame",
        )
        self.prompt_pack_panel.pack(fill=tk.BOTH, expand=True)

        # Store reference to listbox for backward compatibility
        self.packs_listbox = self.prompt_pack_panel.packs_listbox

    def _build_config_pipeline_panel(self, parent):
        """Build tabbed configuration and pipeline panels."""
        center_panel = ttk.Frame(parent, style="Dark.TFrame")
        center_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        center_panel.columnconfigure(0, weight=1)
        # Notebook is on row 1 (row 0 is the preset bar)
        center_panel.rowconfigure(1, weight=1)

        # Global preset management bar (applies to all tabs: Pipeline / Randomization / General)
        preset_bar = ttk.Frame(center_panel, style="Dark.TFrame")
        preset_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        preset_bar.columnconfigure(0, weight=0)
        preset_bar.columnconfigure(1, weight=0)
        preset_bar.columnconfigure(2, weight=0)
        preset_bar.columnconfigure(3, weight=1)

        ttk.Label(preset_bar, text="Preset:", style="Dark.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(2, 4))
        # Single authoritative preset dropdown (moved from Pipeline tab)
        self.preset_dropdown = ttk.Combobox(
            preset_bar,
            textvariable=self.preset_var,
            state="readonly",
            width=28,
            values=self.config_manager.list_presets(),
        )
        self.preset_dropdown.grid(row=0, column=1, sticky=tk.W)
        self.preset_dropdown.bind("<<ComboboxSelected>>", lambda _e: self._on_preset_dropdown_changed())
        self._attach_tooltip(
            self.preset_dropdown,
            "Select a preset to load its settings into the active configuration (spans all tabs).",
        )

        apply_default_btn = ttk.Button(
            preset_bar,
            text="Apply Default",
            command=self._apply_default_to_selected_packs,
            width=14,
            style="Dark.TButton",
        )
        apply_default_btn.grid(row=0, column=2, padx=(8, 4))
        self._attach_tooltip(apply_default_btn, "Load the 'default' preset into the form (not saved until you click Save to Pack(s)).")

        # Right-aligned action strip
        actions_strip = ttk.Frame(preset_bar, style="Dark.TFrame")
        actions_strip.grid(row=0, column=3, sticky=tk.E, padx=(10, 4))

        save_packs_btn = ttk.Button(
            actions_strip,
            text="Save to Pack(s)",
            command=self._save_config_to_packs,
            style="Accent.TButton",
            width=18,
        )
        save_packs_btn.pack(side=tk.LEFT, padx=2)
        self._attach_tooltip(
            save_packs_btn,
            "Persist current configuration to selected pack(s). Single selection saves that pack; multi-selection saves all.",
        )

        save_as_btn = ttk.Button(
            actions_strip,
            text="Save As Preset…",
            command=self._save_preset_as,
            width=16,
        )
        save_as_btn.pack(side=tk.LEFT, padx=2)
        self._attach_tooltip(save_as_btn, "Create a new preset from the current configuration state.")

        set_default_btn = ttk.Button(
            actions_strip,
            text="Set Default",
            command=self._set_as_default_preset,
            width=12,
        )
        set_default_btn.pack(side=tk.LEFT, padx=2)
        self._attach_tooltip(set_default_btn, "Mark the selected preset as the startup default.")

        del_preset_btn = ttk.Button(
            actions_strip,
            text="Delete",
            command=self._delete_selected_preset,
            style="Danger.TButton",
            width=10,
        )
        del_preset_btn.pack(side=tk.LEFT, padx=2)
        self._attach_tooltip(del_preset_btn, "Delete the selected preset (cannot delete 'default').")

        # Notebook sits below preset bar
        notebook = ttk.Notebook(center_panel, style="Dark.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew")
        self.config_notebook = notebook

        pipeline_tab = ttk.Frame(notebook, style="Dark.TFrame")
        randomization_tab = ttk.Frame(notebook, style="Dark.TFrame")
        general_tab = ttk.Frame(notebook, style="Dark.TFrame")

        notebook.add(pipeline_tab, text="Pipeline")
        notebook.add(randomization_tab, text="Randomization")
        notebook.add(general_tab, text="General")

        # Pipeline tab content (preset bar removed from here and placed globally)
        self._build_info_box(
            pipeline_tab,
            "Pipeline Overview",
            "Configure txt2img, img2img, and upscale behavior for the next run. "
            "Use override mode to apply these settings to every selected pack.",
        ).pack(fill=tk.X, padx=10, pady=(10, 4))

        try:
            override_header = ttk.Frame(pipeline_tab, style="Dark.TFrame")
            override_header.pack(fill=tk.X, padx=10, pady=(0, 4))
            override_checkbox = ttk.Checkbutton(
                override_header,
                text="Override pack settings with current config",
                variable=self.override_pack_var,
                style="Dark.TCheckbutton",
                command=self._on_override_changed,
            )
            override_checkbox.pack(side=tk.LEFT)
            self._attach_tooltip(
                override_checkbox,
                "When enabled, the visible configuration is applied to every selected pack. Disable to use each pack's saved config.",
            )
        except Exception:
            pass

        self.config_panel = ConfigPanel(pipeline_tab, coordinator=self, style="Dark.TFrame")
        self.config_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.txt2img_vars = self.config_panel.txt2img_vars
        self.img2img_vars = self.config_panel.img2img_vars
        self.upscale_vars = self.config_panel.upscale_vars
        self.api_vars = self.config_panel.api_vars
        self.config_status_label = self.config_panel.config_status_label
        self.adetailer_panel = getattr(self.config_panel, "adetailer_panel", None)

        try:
            summary_frame = ttk.LabelFrame(
                pipeline_tab, text="Next Run Summary", style="Dark.TFrame", padding=5
            )
            summary_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            self.txt2img_summary_var = getattr(self, "txt2img_summary_var", tk.StringVar(value=""))
            self.img2img_summary_var = getattr(self, "img2img_summary_var", tk.StringVar(value=""))
            self.upscale_summary_var = getattr(self, "upscale_summary_var", tk.StringVar(value=""))

            for var in (
                self.txt2img_summary_var,
                self.img2img_summary_var,
                self.upscale_summary_var,
            ):
                ttk.Label(
                    summary_frame,
                    textvariable=var,
                    style="Dark.TLabel",
                    font=("Consolas", 9),
                ).pack(anchor=tk.W, pady=1)

            self._attach_summary_traces()
            self._update_live_config_summary()
        except Exception:
            pass

        # Randomization tab content
        self._build_randomization_tab(randomization_tab)

        # General tab with pipeline controls, API settings, and sidebar actions
        general_split = ttk.Frame(general_tab, style="Dark.TFrame")
        general_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        general_scroll_container, general_body = self._create_scrollable_container(general_split)
        general_scroll_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(general_split, style="Dark.TFrame", width=220)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        self._build_info_box(
            general_body,
            "General Settings",
            "Manage batch size, looping behavior, and API connectivity. "
            "These settings apply to every run regardless of prompt pack.",
        ).pack(fill=tk.X, pady=(0, 6))

        video_frame = ttk.Frame(general_body, style="Dark.TFrame")
        video_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(
            video_frame,
            text="Enable video stage",
            variable=self.video_enabled,
            style="Dark.TCheckbutton",
        ).pack(anchor=tk.W)

        self._build_pipeline_controls_panel(general_body)

        api_frame = ttk.LabelFrame(
            general_body, text="API Configuration", style="Dark.TFrame", padding=8
        )
        api_frame.pack(fill=tk.X, pady=(10, 10))
        ttk.Label(api_frame, text="Base URL:", style="Dark.TLabel").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(
            api_frame,
            textvariable=self.api_vars.get("base_url"),
            style="Dark.TEntry",
            width=32,
        ).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        ttk.Label(api_frame, text="Timeout (s):", style="Dark.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        ttk.Spinbox(
            api_frame,
            from_=10,
            to=600,
            textvariable=self.api_vars.get("timeout"),
            width=8,
        ).grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))

        for child in api_frame.winfo_children():
            child.configure(style="Dark.TLabel")

        # Sidebar actions & utilities
        actions_box = ttk.LabelFrame(sidebar, text="Pipeline Actions", style="Dark.TFrame", padding=8)
        actions_box.pack(fill=tk.X, pady=(0, 10))

        def add_action_button(parent, text, command, tooltip, style="Dark.TButton"):
            btn = ttk.Button(parent, text=text, command=command, style=style)
            btn.pack(fill=tk.X, pady=4)
            self._attach_tooltip(btn, tooltip)
            return btn

        add_action_button(
            actions_box,
            "Run Full Pipeline",
            self._run_full_pipeline,
            "Process every highlighted pack sequentially using the current configuration. Override mode applies when enabled.",
            style="Accent.TButton",
        )
        add_action_button(
            actions_box,
            "txt2img Only",
            self._run_txt2img_only,
            "Generate txt2img outputs for the selected pack(s) only.",
        )
        add_action_button(
            actions_box,
            "Upscale Only",
            self._run_upscale_only,
            "Run only the upscale stage for the currently selected outputs (skips txt2img/img2img).",
        )
        add_action_button(
            actions_box,
            "Create Video",
            self._create_video,
            "Combine rendered images into a video file.",
        )

        utility_box = ttk.LabelFrame(sidebar, text="Utilities", style="Dark.TFrame", padding=8)
        utility_box.pack(fill=tk.X)
        add_action_button(
            utility_box,
            "Open Output Folder",
            self._open_output_folder,
            "Open the output directory in your system file browser.",
        )
        add_action_button(
            utility_box,
            "Stop Pipeline",
            self._stop_execution,
            "Request cancellation of the pipeline run. The current stage finishes before stopping.",
            style="Danger.TButton",
        )
        add_action_button(
            utility_box,
            "Exit StableNew",
            self._graceful_exit,
            "Gracefully stop background work and close StableNew.",
            style="Danger.TButton",
        )

    def _build_randomization_tab(self, parent: tk.Widget) -> None:
        """Build the randomization tab UI and data bindings."""

        container, body = self._create_scrollable_container(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 10))

        self._build_info_box(
            body,
            "Prompt Randomization & Aesthetic Tools",
            "Enable randomized prompt variations using AUTOMATIC1111-style syntax. "
            "Combine Prompt S/R rules, wildcard tokens, matrices, and optional aesthetic gradients.",
        ).pack(fill=tk.X, padx=10, pady=(0, 6))

        self.randomization_vars = {
            "enabled": tk.BooleanVar(value=False),
            "prompt_sr_enabled": tk.BooleanVar(value=False),
            "prompt_sr_mode": tk.StringVar(value="random"),
            "wildcards_enabled": tk.BooleanVar(value=False),
            "wildcard_mode": tk.StringVar(value="random"),
            "matrix_enabled": tk.BooleanVar(value=False),
            "matrix_mode": tk.StringVar(value="fanout"),
            "matrix_prompt_mode": tk.StringVar(value="replace"),
            "matrix_limit": tk.IntVar(value=8),
        }
        self.randomization_widgets = {}

        self.aesthetic_vars = {
            "enabled": tk.BooleanVar(value=False),
            "mode": tk.StringVar(value="script" if self.aesthetic_script_available else "prompt"),
            "weight": tk.DoubleVar(value=0.9),
            "steps": tk.IntVar(value=5),
            "learning_rate": tk.StringVar(value="0.0001"),
            "slerp": tk.BooleanVar(value=False),
            "slerp_angle": tk.DoubleVar(value=0.1),
            "text": tk.StringVar(value=""),
            "text_is_negative": tk.BooleanVar(value=False),
            "fallback_prompt": tk.StringVar(value=""),
        }
        self.aesthetic_widgets = {"all": [], "script": [], "prompt": []}

        master_frame = ttk.Frame(body, style="Dark.TFrame")
        master_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Checkbutton(
            master_frame,
            text="Enable randomization for the next run",
            variable=self.randomization_vars["enabled"],
            style="Dark.TCheckbutton",
            command=self._update_randomization_states,
        ).pack(side=tk.LEFT)

        ttk.Label(
            master_frame,
            text="Randomization expands prompts before the pipeline starts, so counts multiply per stage.",
            style="Dark.TLabel",
            wraplength=600,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Prompt S/R section
        sr_frame = ttk.LabelFrame(body, text="Prompt S/R", style="Dark.TFrame", padding=10)
        sr_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        sr_header = ttk.Frame(sr_frame, style="Dark.TFrame")
        sr_header.pack(fill=tk.X)
        ttk.Checkbutton(
            sr_header,
            text="Enable Prompt S/R replacements",
            variable=self.randomization_vars["prompt_sr_enabled"],
            style="Dark.TCheckbutton",
            command=self._update_randomization_states,
        ).pack(side=tk.LEFT)

        sr_mode_frame = ttk.Frame(sr_frame, style="Dark.TFrame")
        sr_mode_frame.pack(fill=tk.X, pady=(4, 2))
        ttk.Label(sr_mode_frame, text="Selection mode:", style="Dark.TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(
            sr_mode_frame,
            text="Random per prompt",
            variable=self.randomization_vars["prompt_sr_mode"],
            value="random",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            sr_mode_frame,
            text="Round robin",
            variable=self.randomization_vars["prompt_sr_mode"],
            value="round_robin",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            sr_frame,
            text="Format: search term => replacement A | replacement B. One rule per line. "
            "Matches are case-sensitive and apply before wildcard/matrix expansion.",
            style="Dark.TLabel",
            wraplength=700,
        ).pack(fill=tk.X, pady=(2, 4))

        sr_text = scrolledtext.ScrolledText(sr_frame, height=6, wrap=tk.WORD)
        sr_text.pack(fill=tk.BOTH, expand=True)
        self.randomization_widgets["prompt_sr_text"] = sr_text
        self._enable_mousewheel(sr_text)
        # Persist on edits
        self._bind_autosave_text(sr_text)

        # Wildcards section
        wildcard_frame = ttk.LabelFrame(
            body, text="Wildcards (__token__ syntax)", style="Dark.TFrame", padding=10
        )
        wildcard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        wildcard_header = ttk.Frame(wildcard_frame, style="Dark.TFrame")
        wildcard_header.pack(fill=tk.X)
        ttk.Checkbutton(
            wildcard_header,
            text="Enable wildcard replacements",
            variable=self.randomization_vars["wildcards_enabled"],
            style="Dark.TCheckbutton",
            command=self._update_randomization_states,
        ).pack(side=tk.LEFT)

        ttk.Label(
            wildcard_frame,
            text="Use __token__ in your prompts (same as AUTOMATIC1111 wildcards). "
            "Provide values below using token: option1 | option2.",
            style="Dark.TLabel",
            wraplength=700,
        ).pack(fill=tk.X, pady=(4, 4))

        wildcard_mode_frame = ttk.Frame(wildcard_frame, style="Dark.TFrame")
        wildcard_mode_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(wildcard_mode_frame, text="Selection mode:", style="Dark.TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(
            wildcard_mode_frame,
            text="Random per prompt",
            variable=self.randomization_vars["wildcard_mode"],
            value="random",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            wildcard_mode_frame,
            text="Sequential (loop through values)",
            variable=self.randomization_vars["wildcard_mode"],
            value="sequential",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))

        wildcard_text = scrolledtext.ScrolledText(wildcard_frame, height=6, wrap=tk.WORD)
        wildcard_text.pack(fill=tk.BOTH, expand=True)
        self.randomization_widgets["wildcard_text"] = wildcard_text
        self._enable_mousewheel(wildcard_text)
        self._bind_autosave_text(wildcard_text)

        # Prompt matrix section
        matrix_frame = ttk.LabelFrame(
            body, text="Prompt Matrix ([[Slot]] syntax)", style="Dark.TFrame", padding=10
        )
        matrix_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        matrix_header = ttk.Frame(matrix_frame, style="Dark.TFrame")
        matrix_header.pack(fill=tk.X)
        ttk.Checkbutton(
            matrix_header,
            text="Enable prompt matrix expansion",
            variable=self.randomization_vars["matrix_enabled"],
            style="Dark.TCheckbutton",
            command=self._update_randomization_states,
        ).pack(side=tk.LEFT)

        matrix_mode_frame = ttk.Frame(matrix_frame, style="Dark.TFrame")
        matrix_mode_frame.pack(fill=tk.X, pady=(4, 2))
        ttk.Label(matrix_mode_frame, text="Expansion mode:", style="Dark.TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(
            matrix_mode_frame,
            text="Fan-out (all combos)",
            variable=self.randomization_vars["matrix_mode"],
            value="fanout",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            matrix_mode_frame,
            text="Rotate per prompt",
            variable=self.randomization_vars["matrix_mode"],
            value="rotate",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Prompt mode: how base_prompt relates to pack prompt
        prompt_mode_frame = ttk.Frame(matrix_frame, style="Dark.TFrame")
        prompt_mode_frame.pack(fill=tk.X, pady=(2, 2))
        ttk.Label(prompt_mode_frame, text="Prompt mode:", style="Dark.TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(
            prompt_mode_frame,
            text="Replace pack",
            variable=self.randomization_vars["matrix_prompt_mode"],
            value="replace",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            prompt_mode_frame,
            text="Append to pack",
            variable=self.randomization_vars["matrix_prompt_mode"],
            value="append",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(
            prompt_mode_frame,
            text="Prepend before pack",
            variable=self.randomization_vars["matrix_prompt_mode"],
            value="prepend",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(8, 0))

        limit_frame = ttk.Frame(matrix_frame, style="Dark.TFrame")
        limit_frame.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(limit_frame, text="Combination cap:", style="Dark.TLabel").pack(side=tk.LEFT)
        ttk.Spinbox(
            limit_frame,
            from_=1,
            to=64,
            width=5,
            textvariable=self.randomization_vars["matrix_limit"],
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(
            limit_frame,
            text="(prevents runaway combinations when many slots are defined)",
            style="Dark.TLabel",
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Base prompt field
        base_prompt_frame = ttk.Frame(matrix_frame, style="Dark.TFrame")
        base_prompt_frame.pack(fill=tk.X, pady=(4, 2))
        ttk.Label(
            base_prompt_frame,
            text="Base prompt:",
            style="Dark.TLabel",
            width=14,
        ).pack(side=tk.LEFT)
        base_prompt_entry = ttk.Entry(base_prompt_frame)
        base_prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self.randomization_widgets["matrix_base_prompt"] = base_prompt_entry
        self._bind_autosave_entry(base_prompt_entry)

        ttk.Label(
            matrix_frame,
            text="Add [[Slot Name]] markers in your base prompt. Define combination slots below:",
            style="Dark.TLabel",
            wraplength=700,
        ).pack(fill=tk.X, pady=(2, 4))

        # Scrollable container for slot rows
        slots_container = ttk.Frame(matrix_frame, style="Dark.TFrame")
        slots_container.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        slots_canvas = tk.Canvas(
            slots_container,
            bg="#2b2b2b",
            highlightthickness=0,
            height=150,
        )
        slots_scrollbar = ttk.Scrollbar(
            slots_container,
            orient=tk.VERTICAL,
            command=slots_canvas.yview,
        )
        slots_scrollable_frame = ttk.Frame(slots_canvas, style="Dark.TFrame")

        slots_scrollable_frame.bind(
            "<Configure>",
            lambda e: slots_canvas.configure(scrollregion=slots_canvas.bbox("all")),
        )

        slots_canvas.create_window((0, 0), window=slots_scrollable_frame, anchor="nw")
        slots_canvas.configure(yscrollcommand=slots_scrollbar.set)

        slots_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        slots_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.randomization_widgets["matrix_slots_frame"] = slots_scrollable_frame
        self.randomization_widgets["matrix_slots_canvas"] = slots_canvas
        self.randomization_widgets["matrix_slot_rows"] = []

        # Add slot button
        add_slot_btn = ttk.Button(
            matrix_frame,
            text="+ Add Combination Slot",
            command=self._add_matrix_slot_row,
        )
        add_slot_btn.pack(fill=tk.X, pady=(0, 4))

        # Legacy text view (hidden by default, for advanced users)
        legacy_frame = ttk.Frame(matrix_frame, style="Dark.TFrame")
        legacy_frame.pack(fill=tk.BOTH, expand=True)

        self.randomization_vars["matrix_show_legacy"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            legacy_frame,
            text="Show advanced text editor (legacy format)",
            variable=self.randomization_vars["matrix_show_legacy"],
            style="Dark.TCheckbutton",
            command=self._toggle_matrix_legacy_view,
        ).pack(fill=tk.X, pady=(0, 2))

        legacy_text_container = ttk.Frame(legacy_frame, style="Dark.TFrame")
        self.randomization_widgets["matrix_legacy_container"] = legacy_text_container

        matrix_text = scrolledtext.ScrolledText(
            legacy_text_container,
            height=6,
            wrap=tk.WORD,
        )
        matrix_text.pack(fill=tk.BOTH, expand=True)
        self.randomization_widgets["matrix_text"] = matrix_text
        self._enable_mousewheel(matrix_text)
        self._bind_autosave_text(matrix_text)

        # Aesthetic gradient section
        aesthetic_frame = ttk.LabelFrame(
            body, text="Aesthetic Gradient", style="Dark.TFrame", padding=10
        )
        aesthetic_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        aesthetic_header = ttk.Frame(aesthetic_frame, style="Dark.TFrame")
        aesthetic_header.pack(fill=tk.X)
        ttk.Checkbutton(
            aesthetic_header,
            text="Enable aesthetic gradient adjustments",
            variable=self.aesthetic_vars["enabled"],
            style="Dark.TCheckbutton",
            command=self._update_aesthetic_states,
        ).pack(side=tk.LEFT)

        ttk.Label(
            aesthetic_header,
            textvariable=self.aesthetic_status_var,
            style="Dark.TLabel",
            wraplength=400,
        ).pack(side=tk.LEFT, padx=(12, 0))

        mode_frame = ttk.Frame(aesthetic_frame, style="Dark.TFrame")
        mode_frame.pack(fill=tk.X, pady=(6, 4))
        ttk.Label(mode_frame, text="Mode:", style="Dark.TLabel").pack(side=tk.LEFT)
        script_radio = ttk.Radiobutton(
            mode_frame,
            text="Use Aesthetic Gradient script",
            variable=self.aesthetic_vars["mode"],
            value="script",
            style="Dark.TRadiobutton",
            state=tk.NORMAL if self.aesthetic_script_available else tk.DISABLED,
            command=self._update_aesthetic_states,
        )
        script_radio.pack(side=tk.LEFT, padx=(6, 0))
        prompt_radio = ttk.Radiobutton(
            mode_frame,
            text="Fallback prompt / embedding",
            variable=self.aesthetic_vars["mode"],
            value="prompt",
            style="Dark.TRadiobutton",
            command=self._update_aesthetic_states,
        )
        prompt_radio.pack(side=tk.LEFT, padx=(6, 0))
        self.aesthetic_widgets["all"].extend([script_radio, prompt_radio])

        embedding_row = ttk.Frame(aesthetic_frame, style="Dark.TFrame")
        embedding_row.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(embedding_row, text="Embedding:", style="Dark.TLabel", width=14).pack(side=tk.LEFT)
        self.aesthetic_embedding_combo = ttk.Combobox(
            embedding_row,
            textvariable=self.aesthetic_embedding_var,
            state="readonly",
            width=24,
            values=self.aesthetic_embeddings,
        )
        self.aesthetic_embedding_combo.pack(side=tk.LEFT, padx=(4, 0))
        refresh_btn = ttk.Button(
            embedding_row, text="Refresh", command=self._refresh_aesthetic_embeddings, width=8
        )
        refresh_btn.pack(side=tk.LEFT, padx=(6, 0))
        self.aesthetic_widgets["all"].extend([self.aesthetic_embedding_combo, refresh_btn])

        script_box = ttk.LabelFrame(
            aesthetic_frame, text="Script Parameters", style="Dark.TFrame", padding=6
        )
        script_box.pack(fill=tk.X, pady=(4, 4))

        weight_row = ttk.Frame(script_box, style="Dark.TFrame")
        weight_row.pack(fill=tk.X, pady=2)
        ttk.Label(weight_row, text="Weight:", style="Dark.TLabel", width=14).pack(side=tk.LEFT)
        weight_slider = EnhancedSlider(
            weight_row,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            variable=self.aesthetic_vars["weight"],
            width=140,
        )
        weight_slider.pack(side=tk.LEFT, padx=(4, 10))

        steps_row = ttk.Frame(script_box, style="Dark.TFrame")
        steps_row.pack(fill=tk.X, pady=2)
        ttk.Label(steps_row, text="Steps:", style="Dark.TLabel", width=14).pack(side=tk.LEFT)
        steps_slider = EnhancedSlider(
            steps_row,
            from_=0,
            to=50,
            resolution=1,
            variable=self.aesthetic_vars["steps"],
            width=140,
        )
        steps_slider.pack(side=tk.LEFT, padx=(4, 10))

        lr_row = ttk.Frame(script_box, style="Dark.TFrame")
        lr_row.pack(fill=tk.X, pady=2)
        ttk.Label(lr_row, text="Learning rate:", style="Dark.TLabel", width=14).pack(side=tk.LEFT)
        lr_entry = ttk.Entry(lr_row, textvariable=self.aesthetic_vars["learning_rate"], width=12)
        lr_entry.pack(side=tk.LEFT, padx=(4, 10))

        slerp_row = ttk.Frame(script_box, style="Dark.TFrame")
        slerp_row.pack(fill=tk.X, pady=2)
        slerp_check = ttk.Checkbutton(
            slerp_row,
            text="Enable slerp interpolation",
            variable=self.aesthetic_vars["slerp"],
            style="Dark.TCheckbutton",
            command=self._update_aesthetic_states,
        )
        slerp_check.pack(side=tk.LEFT)
        ttk.Label(slerp_row, text="Angle:", style="Dark.TLabel", width=8).pack(side=tk.LEFT, padx=(10, 0))
        slerp_angle_slider = EnhancedSlider(
            slerp_row,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            variable=self.aesthetic_vars["slerp_angle"],
            width=120,
        )
        slerp_angle_slider.pack(side=tk.LEFT, padx=(4, 0))

        text_row = ttk.Frame(script_box, style="Dark.TFrame")
        text_row.pack(fill=tk.X, pady=2)
        ttk.Label(text_row, text="Text prompt:", style="Dark.TLabel", width=14).pack(side=tk.LEFT)
        text_entry = ttk.Entry(text_row, textvariable=self.aesthetic_vars["text"])
        text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        text_neg_check = ttk.Checkbutton(
            text_row,
            text="Apply as negative text",
            variable=self.aesthetic_vars["text_is_negative"],
            style="Dark.TCheckbutton",
        )
        text_neg_check.pack(side=tk.LEFT, padx=(6, 0))

        self.aesthetic_widgets["script"].extend(
            [
                weight_slider,
                steps_slider,
                lr_entry,
                slerp_check,
                slerp_angle_slider,
                text_entry,
                text_neg_check,
            ]
        )

        prompt_box = ttk.LabelFrame(
            aesthetic_frame, text="Fallback Prompt Injection", style="Dark.TFrame", padding=6
        )
        prompt_box.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(
            prompt_box,
            text="Optional phrase appended to the positive prompt when using fallback mode.",
            style="Dark.TLabel",
            wraplength=700,
        ).pack(fill=tk.X, pady=(0, 4))
        fallback_entry = ttk.Entry(prompt_box, textvariable=self.aesthetic_vars["fallback_prompt"])
        fallback_entry.pack(fill=tk.X, padx=2)

        self.aesthetic_widgets["prompt"].append(fallback_entry)
        self.aesthetic_widgets["all"].append(fallback_entry)
        self.aesthetic_widgets["all"].extend(
            [weight_slider, steps_slider, lr_entry, slerp_check, slerp_angle_slider, text_entry, text_neg_check]
        )

        for key in ("enabled", "prompt_sr_enabled", "wildcards_enabled", "matrix_enabled"):
            try:
                def _rand_trace_cb(*_args, _k=key):
                    self._update_randomization_states()
                    if _k.endswith("enabled"):
                        self._autosave_preferences_if_needed()
                self.randomization_vars[key].trace_add("write", _rand_trace_cb)
            except Exception:
                pass
        # Persist changes to modes/limits too
        for key in ("prompt_sr_mode", "wildcard_mode", "matrix_mode", "matrix_prompt_mode", "matrix_limit"):
            try:
                self.randomization_vars[key].trace_add("write", lambda *_: self._autosave_preferences_if_needed())
            except Exception:
                pass

        try:
            self.aesthetic_vars["enabled"].trace_add("write", lambda *_: self._aesthetic_autosave_handler())
            self.aesthetic_vars["mode"].trace_add("write", lambda *_: self._aesthetic_autosave_handler())
            self.aesthetic_vars["slerp"].trace_add("write", lambda *_: self._aesthetic_autosave_handler())
            # Also persist other aesthetic fields on change
            for _k, _var in self.aesthetic_vars.items():
                try:
                    _var.trace_add("write", lambda *_: self._autosave_preferences_if_needed())
                except Exception:
                    pass
        except Exception:
            pass

        self._update_randomization_states()
        self._refresh_aesthetic_embeddings()
        self._update_aesthetic_states()

    def _update_randomization_states(self) -> None:
        """Enable/disable randomization widgets based on current toggles."""

        vars_dict = getattr(self, "randomization_vars", None)
        widgets = getattr(self, "randomization_widgets", None)
        if not vars_dict or not widgets:
            return

        master = bool(vars_dict.get("enabled", tk.BooleanVar(value=False)).get())
        section_enabled = {
            "prompt_sr_text": master and bool(vars_dict.get("prompt_sr_enabled", tk.BooleanVar()).get()),
            "wildcard_text": master and bool(vars_dict.get("wildcards_enabled", tk.BooleanVar()).get()),
            "matrix_text": master and bool(vars_dict.get("matrix_enabled", tk.BooleanVar()).get()),
        }

        for key, widget in widgets.items():
            if widget is None or isinstance(widget, list):
                continue
            state = tk.NORMAL if section_enabled.get(key, master) else tk.DISABLED
            try:
                widget.configure(state=state)
            except (tk.TclError, AttributeError):
                pass
        # Throttled autosave to keep last_settings.json aligned with UI
        self._autosave_preferences_if_needed()

    def _autosave_preferences_if_needed(self) -> None:
        """Autosave preferences (including randomization enabled flag) with 2s throttle."""
        now = time.time()
        last = getattr(self, "_last_pref_autosave", 0.0)
        if now - last < 2.0:
            return
        self._last_pref_autosave = now
        try:
            prefs = self._collect_preferences()
            if self.preferences_manager.save_preferences(prefs):
                self.preferences = prefs
        except Exception:
            pass

    def _bind_autosave_text(self, widget: tk.Text) -> None:
        """Bind common events on a Text widget to autosave preferences (throttled)."""
        try:
            widget.bind("<KeyRelease>", lambda _e: self._autosave_preferences_if_needed())
            widget.bind("<FocusOut>", lambda _e: self._autosave_preferences_if_needed())
        except Exception:
            pass

    def _bind_autosave_entry(self, widget: tk.Entry) -> None:
        """Bind common events on an Entry widget to autosave preferences (throttled)."""
        try:
            widget.bind("<KeyRelease>", lambda _e: self._autosave_preferences_if_needed())
            widget.bind("<FocusOut>", lambda _e: self._autosave_preferences_if_needed())
        except Exception:
            pass

    def _aesthetic_autosave_handler(self) -> None:
        """Handler for aesthetic state changes that also triggers autosave."""
        self._update_aesthetic_states()
        self._autosave_preferences_if_needed()

    def _get_randomization_text(self, key: str) -> str:
        """Return trimmed contents of a randomization text widget."""

        widget = self.randomization_widgets.get(key)
        if widget is None:
            return ""
        try:
            current_state = widget["state"]
        except (tk.TclError, KeyError):
            current_state = tk.NORMAL

        try:
            if current_state == tk.DISABLED:
                widget.configure(state=tk.NORMAL)
                value = widget.get("1.0", tk.END)
                widget.configure(state=tk.DISABLED)
            else:
                value = widget.get("1.0", tk.END)
        except tk.TclError:
            value = ""
        return value.strip()

    def _set_randomization_text(self, key: str, value: str) -> None:
        """Populate a randomization text widget with new content."""

        widget = self.randomization_widgets.get(key)
        if widget is None:
            return
        try:
            current_state = widget["state"]
        except (tk.TclError, KeyError):
            current_state = tk.NORMAL

        try:
            widget.configure(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            if value:
                widget.insert(tk.END, value)
        except tk.TclError:
            pass
        finally:
            try:
                widget.configure(state=current_state)
            except tk.TclError:
                pass

    def _update_aesthetic_states(self) -> None:
        """Enable/disable aesthetic widgets based on mode and availability."""

        vars_dict = getattr(self, "aesthetic_vars", None)
        widgets = getattr(self, "aesthetic_widgets", None)
        if not vars_dict or not widgets:
            return

        enabled = bool(vars_dict.get("enabled", tk.BooleanVar(value=False)).get())
        mode = vars_dict.get("mode", tk.StringVar(value="prompt")).get()
        if mode == "script" and not self.aesthetic_script_available:
            mode = "prompt"
            vars_dict["mode"].set("prompt")

        def set_state(target_widgets: list[tk.Widget], active: bool) -> None:
            for widget in target_widgets:
                if widget is None:
                    continue
                state = tk.NORMAL if active else tk.DISABLED
                try:
                    widget.configure(state=state)
                except (tk.TclError, AttributeError):
                    if hasattr(widget, "configure_state"):
                        try:
                            widget.configure_state("normal" if active else "disabled")
                        except Exception:
                            continue

        set_state(widgets.get("all", []), enabled)
        set_state(widgets.get("script", []), enabled and mode == "script")
        set_state(widgets.get("prompt", []), enabled and mode == "prompt")

        if self.aesthetic_script_available:
            status = "Aesthetic extension detected"
        else:
            status = "Extension not detected – fallback mode only"
        if len(self.aesthetic_embeddings) <= 1:
            status += " (no embeddings found)"
        self.aesthetic_status_var.set(status)

    def _detect_aesthetic_extension_root(self):
        """Locate the Aesthetic Gradient extension directory if present."""

        candidates: list[Path] = []
        env_root = os.environ.get("WEBUI_ROOT")
        if env_root:
            candidates.append(Path(env_root))
        candidates.append(Path.home() / "stable-diffusion-webui")
        repo_candidate = Path(__file__).resolve().parents[3] / "stable-diffusion-webui"
        candidates.append(repo_candidate)
        local_candidate = Path("..") / "stable-diffusion-webui"
        candidates.append(local_candidate.resolve())

        detected, extension_dir = detect_aesthetic_extension(candidates)
        if detected and extension_dir:
            return True, extension_dir
        return False, None

    def _refresh_aesthetic_embeddings(self, *_):
        """Reload available aesthetic embedding names from disk."""

        embeddings = ["None"]
        if self.aesthetic_extension_root:
            embed_dir = self.aesthetic_extension_root / "aesthetic_embeddings"
            if embed_dir.exists():
                for file in sorted(embed_dir.glob("*.pt")):
                    embeddings.append(file.stem)
        self.aesthetic_embeddings = sorted(dict.fromkeys(embeddings), key=lambda name: (name != "None", name.lower()))

        if self.aesthetic_embedding_var.get() not in self.aesthetic_embeddings:
            self.aesthetic_embedding_var.set("None")

        if hasattr(self, "aesthetic_embedding_combo"):
            try:
                self.aesthetic_embedding_combo["values"] = self.aesthetic_embeddings
            except Exception:
                pass

        if self.aesthetic_script_available:
            status = "Aesthetic extension detected"
        else:
            status = "Extension not detected – fallback mode only"
        if len(self.aesthetic_embeddings) <= 1:
            status += " (no embeddings found)"
        self.aesthetic_status_var.set(status)

    def _collect_randomization_config(self) -> dict[str, Any]:
        """Collect randomization settings into a serializable dict."""

        vars_dict = getattr(self, "randomization_vars", None)
        if not vars_dict:
            return {}

        sr_text = self._get_randomization_text("prompt_sr_text")
        wildcard_text = self._get_randomization_text("wildcard_text")

        # Collect matrix data from UI fields (not legacy text)
        base_prompt_widget = self.randomization_widgets.get("matrix_base_prompt")
        base_prompt = base_prompt_widget.get() if base_prompt_widget else ""

        matrix_slots = []
        for row in self.randomization_widgets.get("matrix_slot_rows", []):
            name = row["name_entry"].get().strip()
            values_text = row["values_entry"].get().strip()
            if name and values_text:
                values = [v.strip() for v in values_text.split("|") if v.strip()]
                if values:
                    matrix_slots.append({"name": name, "values": values})

        # Build raw_text for backward compatibility
        matrix_raw_lines = []
        if base_prompt:
            matrix_raw_lines.append(f"# Base: {base_prompt}")
        matrix_raw_lines.append(self._format_matrix_lines(matrix_slots))
        matrix_raw_text = "\n".join(matrix_raw_lines)

        return {
            "enabled": bool(vars_dict["enabled"].get()),
            "prompt_sr": {
                "enabled": bool(vars_dict["prompt_sr_enabled"].get()),
                "mode": vars_dict["prompt_sr_mode"].get(),
                "rules": self._parse_prompt_sr_rules(sr_text),
                "raw_text": sr_text,
            },
            "wildcards": {
                "enabled": bool(vars_dict["wildcards_enabled"].get()),
                "mode": vars_dict["wildcard_mode"].get(),
                "tokens": self._parse_token_lines(wildcard_text),
                "raw_text": wildcard_text,
            },
            "matrix": {
                "enabled": bool(vars_dict["matrix_enabled"].get()),
                "mode": vars_dict["matrix_mode"].get(),
                "prompt_mode": vars_dict["matrix_prompt_mode"].get(),
                "limit": int(vars_dict["matrix_limit"].get() or 0),
                "slots": matrix_slots,
                "raw_text": matrix_raw_text,
                "base_prompt": base_prompt,
            },
        }

    def _load_randomization_config(self, config: dict[str, Any]) -> None:
        """Populate randomization UI from configuration values."""

        vars_dict = getattr(self, "randomization_vars", None)
        if not vars_dict:
            return

        data = (config or {}).get("randomization", {})
        vars_dict["enabled"].set(bool(data.get("enabled", False)))

        sr = data.get("prompt_sr", {})
        vars_dict["prompt_sr_enabled"].set(bool(sr.get("enabled", False)))
        vars_dict["prompt_sr_mode"].set(sr.get("mode", "random"))
        sr_text = sr.get("raw_text") or self._format_prompt_sr_rules(sr.get("rules", []))
        self._set_randomization_text("prompt_sr_text", sr_text)

        wildcards = data.get("wildcards", {})
        vars_dict["wildcards_enabled"].set(bool(wildcards.get("enabled", False)))
        vars_dict["wildcard_mode"].set(wildcards.get("mode", "random"))
        wildcard_text = wildcards.get("raw_text") or self._format_token_lines(wildcards.get("tokens", []))
        self._set_randomization_text("wildcard_text", wildcard_text)

        matrix = data.get("matrix", {})
        vars_dict["matrix_enabled"].set(bool(matrix.get("enabled", False)))
        vars_dict["matrix_mode"].set(matrix.get("mode", "fanout"))
        vars_dict["matrix_prompt_mode"].set(matrix.get("prompt_mode", "replace"))
        vars_dict["matrix_limit"].set(int(matrix.get("limit", 8)))

        # Load matrix base prompt
        base_prompt = matrix.get("base_prompt", "")
        base_prompt_widget = self.randomization_widgets.get("matrix_base_prompt")
        if base_prompt_widget:
            base_prompt_widget.delete(0, tk.END)
            base_prompt_widget.insert(0, base_prompt)

        # Load matrix slots into UI
        slots = matrix.get("slots", [])
        self._clear_matrix_slot_rows()
        for slot in slots:
            name = slot.get("name", "")
            values = slot.get("values", [])
            if name and values:
                values_str = " | ".join(values)
                self._add_matrix_slot_row(name, values_str)

        # Also populate legacy text for users who want to see it
        matrix_text = matrix.get("raw_text") or self._format_matrix_lines(slots)
        self._set_randomization_text("matrix_text", matrix_text)

        self._update_randomization_states()

    def _collect_aesthetic_config(self) -> dict[str, Any]:
        """Collect aesthetic gradient settings."""

        vars_dict = getattr(self, "aesthetic_vars", None)
        if not vars_dict:
            return {}

        mode = vars_dict["mode"].get()
        if mode == "script" and not self.aesthetic_script_available:
            mode = "prompt"

        def _safe_float(value: Any, default: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        config = {
            "enabled": bool(vars_dict["enabled"].get()),
            "mode": mode,
            "weight": _safe_float(vars_dict["weight"].get(), 0.9),
            "steps": int(vars_dict["steps"].get() or 0),
            "learning_rate": _safe_float(vars_dict["learning_rate"].get(), 0.0001),
            "slerp": bool(vars_dict["slerp"].get()),
            "slerp_angle": _safe_float(vars_dict["slerp_angle"].get(), 0.1),
            "embedding": self.aesthetic_embedding_var.get() or "None",
            "text": vars_dict["text"].get().strip(),
            "text_is_negative": bool(vars_dict["text_is_negative"].get()),
            "fallback_prompt": vars_dict["fallback_prompt"].get().strip(),
        }
        return config

    def _load_aesthetic_config(self, config: dict[str, Any]) -> None:
        """Populate aesthetic gradient UI from stored configuration."""

        vars_dict = getattr(self, "aesthetic_vars", None)
        if not vars_dict:
            return

        data = (config or {}).get("aesthetic", {})
        vars_dict["enabled"].set(bool(data.get("enabled", False)))
        desired_mode = data.get("mode", "script")
        if desired_mode == "script" and not self.aesthetic_script_available:
            desired_mode = "prompt"
        vars_dict["mode"].set(desired_mode)
        vars_dict["weight"].set(float(data.get("weight", 0.9)))
        vars_dict["steps"].set(int(data.get("steps", 5)))
        vars_dict["learning_rate"].set(str(data.get("learning_rate", 0.0001)))
        vars_dict["slerp"].set(bool(data.get("slerp", False)))
        vars_dict["slerp_angle"].set(float(data.get("slerp_angle", 0.1)))
        vars_dict["text"].set(data.get("text", ""))
        vars_dict["text_is_negative"].set(bool(data.get("text_is_negative", False)))
        vars_dict["fallback_prompt"].set(data.get("fallback_prompt", ""))

        embedding = data.get("embedding", "None") or "None"
        if embedding not in self.aesthetic_embeddings:
            embedding = "None"
        self.aesthetic_embedding_var.set(embedding)
        self._update_aesthetic_states()

    @staticmethod
    def _parse_prompt_sr_rules(text: str) -> list[dict[str, Any]]:
        """Parse Prompt S/R rule definitions."""

        rules: list[dict[str, Any]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=>" not in line:
                continue
            search, replacements = line.split("=>", 1)
            search = search.strip()
            replacement_values = [item.strip() for item in replacements.split("|") if item.strip()]
            if search and replacement_values:
                rules.append({"search": search, "replacements": replacement_values})
        return rules

    @staticmethod
    def _format_prompt_sr_rules(rules: list[dict[str, Any]]) -> str:
        """Format Prompt S/R rules back into editable text."""

        lines: list[str] = []
        for entry in rules or []:
            search = entry.get("search", "")
            replacements = entry.get("replacements", [])
            if not search or not replacements:
                continue
            lines.append(f"{search} => {' | '.join(replacements)}")
        return "\n".join(lines)

    @staticmethod
    def _parse_token_lines(text: str) -> list[dict[str, Any]]:
        """Parse wildcard token definitions."""

        tokens: list[dict[str, Any]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            token, values = line.split(":", 1)
            base_name = token.strip().strip("_")
            value_list = [item.strip() for item in values.split("|") if item.strip()]
            if base_name and value_list:
                tokens.append({"token": f"__{base_name}__", "values": value_list})
        return tokens

    @staticmethod
    def _format_token_lines(tokens: list[dict[str, Any]]) -> str:
        """Format wildcard tokens back into editable text."""

        lines: list[str] = []
        for token in tokens or []:
            name = token.get("token", "")
            values = token.get("values", [])
            if not name or not values:
                continue
            stripped_name = name.strip("_") if name.startswith("__") and name.endswith("__") else name
            lines.append(f"{stripped_name}: {' | '.join(values)}")
        return "\n".join(lines)

    @staticmethod
    def _parse_matrix_lines(text: str) -> list[dict[str, Any]]:
        """Parse matrix slot definitions."""

        slots: list[dict[str, Any]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            slot, values = line.split(":", 1)
            slot_name = slot.strip()
            value_list = [item.strip() for item in values.split("|") if item.strip()]
            if slot_name and value_list:
                slots.append({"name": slot_name, "values": value_list})
        return slots

    @staticmethod
    def _format_matrix_lines(slots: list[dict[str, Any]]) -> str:
        """Format matrix slots back into editable text."""

        lines: list[str] = []
        for slot in slots or []:
            name = slot.get("name", "")
            values = slot.get("values", [])
            if not name or not values:
                continue
            lines.append(f"{name}: {' | '.join(values)}")
        return "\n".join(lines)

    def _add_matrix_slot_row(self, slot_name: str = "", slot_values: str = "") -> None:
        """Add a new matrix slot row to the UI."""

        slots_frame = self.randomization_widgets.get("matrix_slots_frame")
        if not slots_frame:
            return

        row_frame = ttk.Frame(slots_frame, style="Dark.TFrame")
        row_frame.pack(fill=tk.X, pady=2)

        # Slot name entry
        ttk.Label(row_frame, text="Slot:", style="Dark.TLabel", width=6).pack(side=tk.LEFT)
        name_entry = ttk.Entry(row_frame, width=15)
        name_entry.pack(side=tk.LEFT, padx=(2, 4))
        if slot_name:
            name_entry.insert(0, slot_name)
        # Autosave when editing slot name
        self._bind_autosave_entry(name_entry)

        # Values entry
        ttk.Label(row_frame, text="Options (| separated):", style="Dark.TLabel").pack(side=tk.LEFT, padx=(4, 2))
        values_entry = ttk.Entry(row_frame)
        values_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 4))
        if slot_values:
            values_entry.insert(0, slot_values)
        # Autosave when editing slot values
        self._bind_autosave_entry(values_entry)

        # Remove button
        remove_btn = ttk.Button(
            row_frame,
            text="−",
            width=3,
            command=lambda: self._remove_matrix_slot_row(row_frame),
        )
        remove_btn.pack(side=tk.LEFT)

        # Store row data
        row_data = {
            "frame": row_frame,
            "name_entry": name_entry,
            "values_entry": values_entry,
        }
        self.randomization_widgets["matrix_slot_rows"].append(row_data)

        # Update scroll region
        canvas = self.randomization_widgets.get("matrix_slots_canvas")
        if canvas:
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _remove_matrix_slot_row(self, row_frame: tk.Widget) -> None:
        """Remove a matrix slot row from the UI."""

        slot_rows = self.randomization_widgets.get("matrix_slot_rows", [])
        self.randomization_widgets["matrix_slot_rows"] = [
            row for row in slot_rows if row["frame"] != row_frame
        ]
        row_frame.destroy()

        # Update scroll region
        canvas = self.randomization_widgets.get("matrix_slots_canvas")
        if canvas:
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _clear_matrix_slot_rows(self) -> None:
        """Clear all matrix slot rows from the UI."""

        for row in self.randomization_widgets.get("matrix_slot_rows", []):
            row["frame"].destroy()
        self.randomization_widgets["matrix_slot_rows"] = []

        # Update scroll region
        canvas = self.randomization_widgets.get("matrix_slots_canvas")
        if canvas:
            canvas.configure(scrollregion=canvas.bbox("all"))

    def _toggle_matrix_legacy_view(self) -> None:
        """Toggle between modern UI and legacy text editor for matrix config."""

        show_legacy = self.randomization_vars.get("matrix_show_legacy", tk.BooleanVar()).get()
        legacy_container = self.randomization_widgets.get("matrix_legacy_container")

        if legacy_container:
            if show_legacy:
                # Sync from UI to legacy text before showing
                self._sync_matrix_ui_to_text()
                legacy_container.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
            else:
                # Sync from legacy text to UI before hiding
                self._sync_matrix_text_to_ui()
                legacy_container.pack_forget()

    def _sync_matrix_ui_to_text(self) -> None:
        """Sync matrix UI fields to the legacy text widget."""

        base_prompt_widget = self.randomization_widgets.get("matrix_base_prompt")
        base_prompt = base_prompt_widget.get() if base_prompt_widget else ""

        slots = []
        for row in self.randomization_widgets.get("matrix_slot_rows", []):
            name = row["name_entry"].get().strip()
            values_text = row["values_entry"].get().strip()
            if name and values_text:
                slots.append({"name": name, "values": [v.strip() for v in values_text.split("|") if v.strip()]})

        # Build legacy format: base prompt on first line, then slots
        lines = []
        if base_prompt:
            lines.append(f"# Base: {base_prompt}")
        lines.append(self._format_matrix_lines(slots))

        matrix_text = self.randomization_widgets.get("matrix_text")
        if matrix_text:
            matrix_text.delete("1.0", tk.END)
            matrix_text.insert("1.0", "\n".join(lines))

    def _sync_matrix_text_to_ui(self) -> None:
        """Sync legacy text widget to matrix UI fields."""

        matrix_text = self.randomization_widgets.get("matrix_text")
        if not matrix_text:
            return

        text = matrix_text.get("1.0", tk.END).strip()
        lines = text.splitlines()

        # Check for base prompt marker
        base_prompt = ""
        slot_lines = []
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("# Base:"):
                base_prompt = line_stripped[7:].strip()
            elif line_stripped and not line_stripped.startswith("#"):
                slot_lines.append(line_stripped)

        # Update base prompt
        base_prompt_widget = self.randomization_widgets.get("matrix_base_prompt")
        if base_prompt_widget:
            base_prompt_widget.delete(0, tk.END)
            base_prompt_widget.insert(0, base_prompt)

        # Parse slots and rebuild UI
        slots = self._parse_matrix_lines("\n".join(slot_lines))
        self._clear_matrix_slot_rows()
        for slot in slots:
            values_str = " | ".join(slot.get("values", []))
            self._add_matrix_slot_row(slot.get("name", ""), values_str)
        return "\n".join(lines)

    def _build_pipeline_controls_panel(self, parent):
        """Build compact pipeline controls panel using PipelineControlsPanel component, with state restore."""
        # Save previous state if panel exists
        prev_state = None
        if hasattr(self, "pipeline_controls_panel") and self.pipeline_controls_panel is not None:
            try:
                prev_state = self.pipeline_controls_panel.get_state()
            except Exception as e:
                logger.warning(f"Failed to get PipelineControlsPanel state: {e}")
        # Destroy old panel if present
        if hasattr(self, "pipeline_controls_panel") and self.pipeline_controls_panel is not None:
            self.pipeline_controls_panel.destroy()
        # Determine initial state for the new panel
        initial_state = (
            prev_state if prev_state is not None else self.preferences.get("pipeline_controls")
        )

        # Create the PipelineControlsPanel component
        stage_vars = {
            "txt2img": self.txt2img_enabled,
            "img2img": self.img2img_enabled,
            "adetailer": self.adetailer_enabled,
            "upscale": self.upscale_enabled,
            "video": self.video_enabled,
        }

        self.pipeline_controls_panel = PipelineControlsPanel(
            parent,
            initial_state=initial_state,
            stage_vars=stage_vars,
            style="Dark.TFrame",
        )
        self.pipeline_controls_panel.pack(fill=tk.BOTH, expand=True)
        # Restore previous state if available
        if prev_state:
            try:
                self.pipeline_controls_panel.set_state(prev_state)
            except Exception as e:
                logger.warning(f"Failed to restore PipelineControlsPanel state: {e}")
        # Keep shared references for non-stage settings
        self.video_enabled = self.pipeline_controls_panel.video_enabled
        self.loop_type_var = self.pipeline_controls_panel.loop_type_var
        self.loop_count_var = self.pipeline_controls_panel.loop_count_var
        self.pack_mode_var = self.pipeline_controls_panel.pack_mode_var
        self.images_per_prompt_var = self.pipeline_controls_panel.images_per_prompt_var

    def _build_config_display_tab(self, notebook):
        """Build interactive configuration tabs"""

        config_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(config_frame, text="⚙️ Configuration")

        # Configuration status section with dark theme
        status_frame = ttk.LabelFrame(
            config_frame, text="Configuration Status", style="Dark.TFrame", padding=5
        )
        status_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.config_status_label = ttk.Label(
            status_frame,
            text="Ready",
            style="Dark.TLabel",
            foreground="#cccccc",
            font=("Segoe UI", 9),
            wraplength=600,
        )
        self.config_status_label.pack(fill=tk.X)

        # Create nested notebook for stage-specific configurations with proper spacing
        config_notebook = ttk.Notebook(config_frame, style="Dark.TNotebook")
        config_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Create individual tabs for each stage
        self._build_txt2img_config_tab(config_notebook)
        self._build_img2img_config_tab(config_notebook)
        self._build_upscale_config_tab(config_notebook)
        self._build_api_config_tab(config_notebook)

        # Add buttons for save/load/reset with proper spacing at bottom
        config_buttons = ttk.Frame(config_frame, style="Dark.TFrame")
        config_buttons.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(5, 10))

        save_all_btn = ttk.Button(
            config_buttons,
            text="Save All Changes",
            command=self._save_all_config,
            style="Dark.TButton",
        )
        save_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._attach_tooltip(
            save_all_btn,
            "Write every visible setting to the current preset/override so multi-pack runs stay consistent.",
        )

        reset_all_btn = ttk.Button(
            config_buttons, text="Reset All", command=self._reset_all_config, style="Dark.TButton"
        )
        reset_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._attach_tooltip(
            reset_all_btn,
            "Revert the form back to the base preset. Does not touch pack-specific files.",
        )

        save_pack_btn = ttk.Button(
            config_buttons,
            text="Save Pack Config",
            command=self._save_current_pack_config,
            style="Dark.TButton",
        )
        save_pack_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._attach_tooltip(
            save_pack_btn,
            "Stores the current values into the highlighted pack's JSON. Available only when a single pack is selected and override is off.",
        )

        # Auto-apply toggle and top save indicator
        try:
            self.auto_apply_var = tk.BooleanVar(value=False)
            auto_apply_check = ttk.Checkbutton(
                config_buttons,
                text="Auto-apply on change",
                variable=self.auto_apply_var,
                style="Dark.TCheckbutton",
            )
            auto_apply_check.pack(side=tk.LEFT, padx=(10, 5))
            self._attach_tooltip(
                auto_apply_check,
                "Immediately save edits to the active pack/preset whenever a field changes. Helpful for rapid tweaking.",
            )

            self.top_save_indicator_var = tk.StringVar(value="")
            self.top_save_indicator = ttk.Label(
                config_buttons, textvariable=self.top_save_indicator_var, style="Dark.TLabel"
            )
            self.top_save_indicator.pack(side=tk.LEFT, padx=(8, 0))
        except Exception:
            pass

        # Preset selection dropdown
        preset_frame = ttk.LabelFrame(config_buttons, text="Base Preset", padding=5)
        preset_frame.pack(side=tk.LEFT, padx=(10, 10))

        preset_controls = ttk.Frame(preset_frame, style="Dark.TFrame")
        preset_controls.pack(fill=tk.X)

        self.preset_dropdown = ttk.Combobox(
            preset_controls,
            textvariable=self.preset_var,
            state="readonly",
            width=15,
            style="Dark.TCombobox",
            values=self.config_manager.list_presets(),
        )
        self.preset_dropdown.pack(side=tk.LEFT, padx=(0, 4))
        self.preset_dropdown.bind("<<ComboboxSelected>>", self._on_preset_changed)

        # Preset action buttons
        preset_buttons = ttk.Frame(preset_controls, style="Dark.TFrame")
        preset_buttons.pack(side=tk.LEFT)

        load_btn = ttk.Button(
            preset_buttons,
            text="↻ Load",
            command=self._load_selected_preset,
            width=6,
            style="Dark.TButton",
        )
        load_btn.pack(side=tk.LEFT, padx=1)
        self._attach_tooltip(load_btn, "Load the selected preset into the current configuration")

        save_as_btn = ttk.Button(
            preset_buttons,
            text="💾 Save As",
            command=self._save_preset_as,
            width=8,
            style="Dark.TButton",
        )
        save_as_btn.pack(side=tk.LEFT, padx=1)
        self._attach_tooltip(save_as_btn, "Save current config as a new preset")

        update_btn = ttk.Button(
            preset_buttons,
            text="✓ Update",
            command=self._save_override_preset,
            width=7,
            style="Dark.TButton",
        )
        update_btn.pack(side=tk.LEFT, padx=1)
        self._attach_tooltip(update_btn, "Update the selected preset with current settings")

        delete_btn = ttk.Button(
            preset_buttons,
            text="🗑 Delete",
            command=self._delete_selected_preset,
            width=7,
            style="Danger.TButton",
        )
        delete_btn.pack(side=tk.LEFT, padx=1)
        self._attach_tooltip(delete_btn, "Delete the selected preset (default cannot be deleted)")

        set_default_btn = ttk.Button(
            preset_buttons,
            text="⭐ Set Default",
            command=self._set_default_preset,
            width=11,
            style="Dark.TButton",
        )
        set_default_btn.pack(side=tk.LEFT, padx=1)
        self._attach_tooltip(set_default_btn, "Set this preset to load automatically on startup")

    def _build_pipeline_controls_tab(self, notebook):
        """Build pipeline execution controls tab"""
        pipeline_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(pipeline_frame, text="🚀 Pipeline Controls")

        # Pipeline execution options
        exec_options_frame = ttk.LabelFrame(
            pipeline_frame, text="Execution Options", style="Dark.TFrame", padding=10
        )
        exec_options_frame.pack(fill=tk.X, pady=(10, 10))

        # Stage selection
        stages_frame = ttk.Frame(exec_options_frame, style="Dark.TFrame")
        stages_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(stages_frame, text="Pipeline Stages:", style="Dark.TLabel").pack(anchor=tk.W)

        stage_checks_frame = ttk.Frame(stages_frame, style="Dark.TFrame")
        stage_checks_frame.pack(fill=tk.X, pady=(5, 0))

        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            stage_checks_frame,
            text="🎨 txt2img",
            variable=self.txt2img_enabled,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(
            stage_checks_frame,
            text="🧹 img2img cleanup",
            variable=self.img2img_enabled,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(
            stage_checks_frame,
            text="📈 Upscale",
            variable=self.upscale_enabled,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(
            stage_checks_frame,
            text="🎬 Create Video",
            variable=self.video_enabled,
            style="Dark.TCheckbutton",
        ).pack(side=tk.LEFT)

        # Loop configuration
        loop_frame = ttk.Frame(exec_options_frame, style="Dark.TFrame")
        loop_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(loop_frame, text="Loop Configuration:", style="Dark.TLabel").pack(anchor=tk.W)

        loop_controls = ttk.Frame(loop_frame, style="Dark.TFrame")
        loop_controls.pack(fill=tk.X, pady=(5, 0))

        # Loop type
        self.loop_type_var = tk.StringVar(value="single")
        ttk.Radiobutton(
            loop_controls,
            text="Single run",
            variable=self.loop_type_var,
            value="single",
            style="Dark.TRadiobutton",
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(
            loop_controls,
            text="Loop stages",
            variable=self.loop_type_var,
            value="stages",
            style="Dark.TRadiobutton",
        ).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(
            loop_controls,
            text="Loop pipeline",
            variable=self.loop_type_var,
            value="pipeline",
            style="Dark.TRadiobutton",
        ).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))

        # Loop count
        loop_count_frame = ttk.Frame(loop_controls, style="Dark.TFrame")
        loop_count_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

        ttk.Label(loop_count_frame, text="Loop count:", style="Dark.TLabel").pack(side=tk.LEFT)
        self.loop_count_var = tk.StringVar(value="1")
        loop_count_spin = ttk.Spinbox(
            loop_count_frame,
            from_=1,
            to=100,
            width=5,
            textvariable=self.loop_count_var,
            style="Dark.TEntry",
        )
        loop_count_spin.pack(side=tk.LEFT, padx=(5, 0))

        # Batch configuration
        batch_frame = ttk.LabelFrame(
            pipeline_frame, text="Batch Configuration", style="Dark.TFrame", padding=10
        )
        batch_frame.pack(fill=tk.X, pady=(0, 10))

        # Pack selection mode
        pack_mode_frame = ttk.Frame(batch_frame, style="Dark.TFrame")
        pack_mode_frame.pack(fill=tk.X)

        self.pack_mode_var = tk.StringVar(value="selected")
        ttk.Radiobutton(
            pack_mode_frame,
            text="Selected packs only",
            variable=self.pack_mode_var,
            value="selected",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(
            pack_mode_frame,
            text="All packs",
            variable=self.pack_mode_var,
            value="all",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(
            pack_mode_frame,
            text="Custom list",
            variable=self.pack_mode_var,
            value="custom",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT)

        # Images per prompt
        images_frame = ttk.Frame(batch_frame, style="Dark.TFrame")
        images_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(images_frame, text="Images per prompt:", style="Dark.TLabel").pack(side=tk.LEFT)
        self.images_per_prompt_var = tk.StringVar(value="1")
        images_spin = ttk.Spinbox(
            images_frame,
            from_=1,
            to=10,
            width=5,
            textvariable=self.images_per_prompt_var,
            style="Dark.TEntry",
        )
        images_spin.pack(side=tk.LEFT, padx=(5, 0))

    def _build_bottom_panel(self, parent):
        """Build bottom panel with logs and action buttons"""
        bottom_frame = ttk.Frame(parent, style="Dark.TFrame")
        bottom_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

        # Compact action buttons frame
        actions_frame = ttk.Frame(bottom_frame, style="Dark.TFrame")
        actions_frame.pack(fill=tk.X, pady=(0, 5))

        # Main execution buttons with accent colors
        main_buttons = ttk.Frame(actions_frame, style="Dark.TFrame")
        main_buttons.pack(side=tk.LEFT)

        self.run_pipeline_btn = ttk.Button(
            main_buttons,
            text="Run Full Pipeline",
            command=self._run_full_pipeline,
            style="Accent.TButton",
        )  # Blue accent for primary action
        self.run_pipeline_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(
            self.run_pipeline_btn,
            "Process every highlighted pack sequentially using the current configuration. Override mode applies when enabled.",
        )

        txt2img_only_btn = ttk.Button(
            main_buttons,
            text="txt2img Only",
            command=self._run_txt2img_only,
            style="Dark.TButton",
        )
        txt2img_only_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(
            txt2img_only_btn,
            "Generate txt2img outputs for the selected pack(s) only.",
        )

        upscale_only_btn = ttk.Button(
            main_buttons,
            text="Upscale Only",
            command=self._run_upscale_only,
            style="Dark.TButton",
        )
        upscale_only_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(
            upscale_only_btn,
            "Run only the upscale stage for the currently selected outputs (skips txt2img/img2img).",
        )

        create_video_btn = ttk.Button(
            main_buttons, text="Create Video", command=self._create_video, style="Dark.TButton"
        )
        create_video_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(create_video_btn, "Combine rendered images into a video file.")

        # Utility buttons
        util_buttons = ttk.Frame(actions_frame, style="Dark.TFrame")
        util_buttons.pack(side=tk.RIGHT)

        open_output_btn = ttk.Button(
            util_buttons,
            text="Open Output",
            command=self._open_output_folder,
            style="Dark.TButton",
        )
        open_output_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(open_output_btn, "Open the output directory in your system file browser.")

        stop_btn = ttk.Button(
            util_buttons, text="Stop", command=self._stop_execution, style="Danger.TButton"
        )
        stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._attach_tooltip(
            stop_btn,
            "Request cancellation of the pipeline run. The current stage finishes before stopping.",
        )

        exit_btn = ttk.Button(
            util_buttons, text="Exit", command=self._graceful_exit, style="Danger.TButton"
        )
        exit_btn.pack(side=tk.LEFT)
        self._attach_tooltip(exit_btn, "Gracefully stop background work and close StableNew.")


        # Reparent early log panel to bottom_frame
        # (log_panel was created early in __init__ to avoid AttributeError)
        # Create log panel directly with bottom_frame as parent
        self.log_panel = LogPanel(bottom_frame, coordinator=self, height=18, style="Dark.TFrame")
        self.log_panel.pack(fill=tk.BOTH, expand=True)
        self.add_log = self.log_panel.append
        self.log_text = getattr(self.log_panel, "log_text", None)
        if self.log_text is not None:
            self._enable_mousewheel(self.log_text)

        # Attach logging handler to redirect standard logging to GUI
        if not hasattr(self, "gui_log_handler"):
            self.gui_log_handler = TkinterLogHandler(self.log_panel)
            logging.getLogger().addHandler(self.gui_log_handler)

    def _build_status_bar(self, parent):
        """Build status bar showing current state"""
        status_frame = ttk.Frame(parent, style="Dark.TFrame", relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        # State indicator
        self.state_label = ttk.Label(
            status_frame, text="● Idle", style="Dark.TLabel", foreground="#4CAF50"
        )
        self.state_label.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.config(maximum=100, value=0)
        self.progress_bar.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # ETA indicator
        self.eta_var = tk.StringVar(value=self._progress_eta_default)
        # Keep alias in sync for tests
        self.progress_eta_var = self.eta_var
        ttk.Label(status_frame, textvariable=self.eta_var, style="Dark.TLabel").pack(
            side=tk.LEFT, padx=5
        )

        # Progress message
        self.progress_message_var = tk.StringVar(value=self._progress_idle_message)
        # Keep alias in sync for tests
        self.progress_status_var = self.progress_message_var
        ttk.Label(status_frame, textvariable=self.progress_message_var, style="Dark.TLabel").pack(
            side=tk.LEFT, padx=10
        )

        # Spacer
        ttk.Label(status_frame, text="", style="Dark.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        self._apply_progress_reset()

    def _apply_progress_reset(self, message: str | None = None) -> None:
        """Reset progress UI elements synchronously."""
        if hasattr(self, "progress_bar"):
            self.progress_bar.config(value=0)
        if hasattr(self, "eta_var"):
            self.eta_var.set(self._progress_eta_default)
        if hasattr(self, "progress_message_var"):
            self.progress_message_var.set(message or self._progress_idle_message)

    def _reset_progress_ui(self, message: str | None = None) -> None:
        """Reset the progress UI immediately when possible, else schedule on Tk loop."""
        try:
            self._apply_progress_reset(message)
        except Exception:
            pass
        try:
            self.root.after(0, lambda: self._apply_progress_reset(message))
        except Exception:
            pass

    def _apply_progress_update(self, stage: str, percent: float, eta: str | None) -> None:
        """Apply progress updates to the UI synchronously."""
        clamped_percent = max(0.0, min(100.0, float(percent) if percent is not None else 0.0))
        if hasattr(self, "progress_bar"):
            self.progress_bar.config(value=clamped_percent)

        if hasattr(self, "progress_message_var"):
            stage_text = stage.strip() if stage else "Progress"
            self.progress_message_var.set(f"{stage_text} ({clamped_percent:.0f}%)")

        if hasattr(self, "eta_var"):
            self.eta_var.set(f"ETA: {eta}" if eta else self._progress_eta_default)

    def _update_progress(self, stage: str, percent: float, eta: str | None = None) -> None:
        """Update progress UI, immediately if on Tk thread, else via event loop."""
        try:
            # Attempt immediate update (helps tests that call from main thread)
            self._apply_progress_update(stage, percent, eta)
        except Exception:
            # Fallback to Tk event loop scheduling only
            pass
        # Always ensure an event-loop scheduled update as well
        try:
            self.root.after(0, lambda: self._apply_progress_update(stage, percent, eta))
        except Exception:
            pass

    def _setup_state_callbacks(self):
        """Setup callbacks for state transitions"""

        def on_state_change(old_state, new_state):
            """Called when state changes"""
            state_colors = {
                GUIState.IDLE: ("#4CAF50", "● Idle"),
                GUIState.RUNNING: ("#2196F3", "● Running"),
                GUIState.STOPPING: ("#FF9800", "● Stopping"),
                GUIState.ERROR: ("#f44336", "● Error"),
            }

            color, text = state_colors.get(new_state, ("#888888", "● Unknown"))
            self.state_label.config(text=text, foreground=color)

            if new_state == GUIState.RUNNING:
                self.progress_message_var.set("Running pipeline...")
            elif new_state == GUIState.STOPPING:
                self.progress_message_var.set("Cancelling pipeline...")
            elif new_state == GUIState.ERROR:
                self.progress_message_var.set("Error")
            elif new_state == GUIState.IDLE and old_state == GUIState.STOPPING:
                self.progress_message_var.set("Ready")

            # Update button states
            if new_state == GUIState.RUNNING:
                self.run_pipeline_btn.config(state=tk.DISABLED)
            elif new_state == GUIState.IDLE:
                self._reset_progress_ui()
                self.run_pipeline_btn.config(state=tk.NORMAL if self.api_connected else tk.DISABLED)
            elif new_state == GUIState.ERROR:
                self.run_pipeline_btn.config(state=tk.NORMAL if self.api_connected else tk.DISABLED)

        self.state_manager.on_transition(on_state_change)

    def _queue_progress_update(self, percent: float) -> None:
        """Update progress widgets on the Tk thread."""

        def update() -> None:
            clamped = max(0.0, min(100.0, float(percent) if percent is not None else 0.0))
            if self.progress_bar is not None:
                self.progress_bar["value"] = clamped
            self.progress_percent_var.set(f"{clamped:.0f}%")

        self.root.after(0, update)

    def _queue_eta_update(self, eta: str | None) -> None:
        """Update ETA label on the Tk thread."""

        def update() -> None:
            self.eta_var.set(eta if eta else "ETA: --")

        self.root.after(0, update)

    def _queue_status_update(self, text: str | None) -> None:
        """Update status text via Tk event loop."""
        # If forced error status (test harness), ignore non-error updates
        if getattr(self, "_force_error_status", False):
            if not (text and str(text).strip().lower() == "error"):
                return
        self.root.after(0, lambda: self._apply_status_text(text))

    def _apply_status_text(self, text: str | None) -> None:
        """Apply status text to both status bar and execution label."""
        # If forced error status (tests), always show Error regardless of queued updates
        if getattr(self, "_force_error_status", False):
            forced = "Error" if not (text and str(text).strip().lower() == "error") else "Error"
            self.progress_message_var.set(forced)
            self.progress_var.set(forced)
            return

        if text is None:
            try:
                from .state import GUIState

                if hasattr(self, "state_manager") and self.state_manager.is_state(GUIState.ERROR):
                    message = "Error"
                else:
                    message = "Ready"
            except Exception:
                message = "Ready"
        else:
            message = text
        # Normalize cancellation text to Ready once we've returned to IDLE
        try:
            from .state import GUIState

            if (
                str(message).strip().lower() == "cancelled"
                and hasattr(self, "state_manager")
                and self.state_manager.is_state(GUIState.IDLE)
            ):
                message = "Ready"
        except Exception:
            pass
        self.progress_message_var.set(message)
        self.progress_var.set(message)

    def _poll_controller_logs(self):
        """Poll controller for log messages and display them"""
        messages = self.controller.get_log_messages()
        for msg in messages:
            self.log_message(msg.message, msg.level)
            self._apply_status_text(msg.message)

        # Schedule next poll
        self.root.after(100, self._poll_controller_logs)

    # Class-level API check method
    def _check_api_connection(self):
        """Check API connection status with improved diagnostics."""

        def check_in_thread():
            api_url = self.api_url_var.get()

            # Try the specified URL first
            self.log_message("🔍 Checking API connection...", "INFO")

            # First try direct connection
            client = SDWebUIClient(api_url)
            # Apply configured timeout from API tab (keeps UI responsive on failures)
            try:
                if hasattr(self, "api_vars") and "timeout" in self.api_vars:
                    client.timeout = int(self.api_vars["timeout"].get() or 30)
            except Exception:
                pass
            if client.check_api_ready():
                # Perform health check
                health = validate_webui_health(api_url)

                self.api_connected = True
                self.client = client
                self.pipeline = Pipeline(client, self.structured_logger)
                self.controller.set_pipeline(self.pipeline)

                self.root.after(0, lambda: self._update_api_status(True, api_url))

                if health["models_loaded"]:
                    self.log_message(
                        f"✅ API connected! Found {health.get('model_count', 0)} models", "SUCCESS"
                    )
                else:
                    self.log_message("⚠️ API connected but no models loaded", "WARNING")
                return

            # If direct connection failed, try port discovery
            self.log_message("🔍 Trying port discovery...", "INFO")
            discovered_url = find_webui_api_port()

            if discovered_url:
                # Test the discovered URL
                client = SDWebUIClient(discovered_url)
                try:
                    if hasattr(self, "api_vars") and "timeout" in self.api_vars:
                        client.timeout = int(self.api_vars["timeout"].get() or 30)
                except Exception:
                    pass
                if client.check_api_ready():
                    health = validate_webui_health(discovered_url)

                    self.api_connected = True
                    self.client = client
                    self.pipeline = Pipeline(client, self.structured_logger)
                    self.controller.set_pipeline(self.pipeline)

                    # Update URL field and status
                    self.root.after(0, lambda: self.api_url_var.set(discovered_url))
                    self.root.after(0, lambda: self._update_api_status(True, discovered_url))

                    if health["models_loaded"]:
                        self.log_message(
                            f"✅ API found at {discovered_url}! Found {health.get('model_count', 0)} models",
                            "SUCCESS",
                        )
                    else:
                        self.log_message("⚠️ API found but no models loaded", "WARNING")
                    return

            # Connection failed
            self.api_connected = False
            self.root.after(0, lambda: self._update_api_status(False))
            self.log_message(
                "❌ API connection failed. Please ensure WebUI is running with --api", "ERROR"
            )
            self.log_message("💡 Tip: Check ports 7860-7864, restart WebUI if needed", "INFO")

        threading.Thread(target=check_in_thread, daemon=True).start()
        # Note: previously this method started two identical threads; that was redundant and has been removed

    def _update_api_status(self, connected: bool, url: str = None):
        """Update API status indicator"""
        if connected:
            if hasattr(self, "api_status_panel"):
                self.api_status_panel.set_status("Connected", "green")
            self.run_pipeline_btn.config(state=tk.NORMAL)

            # Update URL field if we found a different working port
            if url and url != self.api_url_var.get():
                self.api_url_var.set(url)
                self.log_message(f"Updated API URL to working port: {url}", "INFO")

            # Refresh models, VAE, upscalers, and schedulers when connected
            def refresh_all():
                try:
                    # Perform API calls in worker thread
                    self._refresh_models_async()
                    self._refresh_vae_models_async()
                    self._refresh_hypernetworks_async()
                    self._refresh_upscalers_async()
                    self._refresh_schedulers_async()
                except Exception as exc:
                    # Marshal error message back to main thread
                    # Capture exception in default argument to avoid closure issues
                    self.root.after(
                        0,
                        lambda err=exc: self.log_message(
                            f"⚠️ Failed to refresh model lists: {err}", "WARNING"
                        ),
                    )

            # Run refresh in a separate thread to avoid blocking UI
            threading.Thread(target=refresh_all, daemon=True).start()
        else:
            if hasattr(self, "api_status_panel"):
                self.api_status_panel.set_status("Disconnected", "red")
            self.run_pipeline_btn.config(state=tk.DISABLED)

    def _on_pack_selection_changed_mediator(self, selected_packs: list[str]):
        """
        Mediator callback for pack selection changes from PromptPackPanel.

        Args:
            selected_packs: List of selected pack names
        """
        if getattr(self, "_diag_enabled", False):
            logger.info(
                f"[DIAG] mediator _on_pack_selection_changed_mediator start; packs={selected_packs}"
            )
        # Update internal state
        self.selected_packs = selected_packs

        if selected_packs:
            pack_name = selected_packs[0]
            self.log_message(f"📦 Selected pack: {pack_name}")
            self._last_selected_pack = pack_name
        else:
            self.log_message("No pack selected")
            self._last_selected_pack = None

        # Refresh configuration for selected pack
        self._refresh_config()
        if getattr(self, "_diag_enabled", False):
            logger.info("[DIAG] mediator _on_pack_selection_changed_mediator end")

    def _on_pack_selection_changed(self, event=None):
        """Handle prompt pack selection changes - update config display dynamically"""
        selected_indices = self.packs_listbox.curselection()
        if selected_indices:
            pack_name = self.packs_listbox.get(selected_indices[0])
            self.log_message(f"📦 Selected pack: {pack_name}")

            # Store current selection to prevent unwanted deselection
            self._last_selected_pack = pack_name
        else:
            # If no selection but we have a last selected pack, try to restore it
            if (
                hasattr(self, "_last_selected_pack")
                and self._last_selected_pack
                and not self._refreshing_config
            ):
                self._preserve_pack_selection()
                return  # Don't proceed if we're restoring selection
            else:
                self.log_message("No pack selected")
                self._last_selected_pack = None

        # Refresh configuration for selected pack
        self._refresh_config()

        # Highlight selection with custom styling
        self._update_selection_highlights()

    def _update_selection_highlights(self):
        """Update visual highlighting for selected items"""
        # Reset all items to default background
        for i in range(self.packs_listbox.size()):
            self.packs_listbox.itemconfig(i, {"bg": "#3d3d3d"})

        # Highlight selected items
        for index in self.packs_listbox.curselection():
            self.packs_listbox.itemconfig(index, {"bg": "#0078d4"})

    def _initialize_ui_state(self):
        logger.info("[DIAG] _initialize_ui_state: entered method", extra={"flush": True})
        """Initialize UI to default state with first pack selected and display mode active."""
        # Select first pack if available (panel already loaded packs during init)
        logger.info("[DIAG] _initialize_ui_state: before select_first_pack", extra={"flush": True})
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.select_first_pack()
        logger.info("[DIAG] _initialize_ui_state: after select_first_pack", extra={"flush": True})

        # Update log
        self.log_message("GUI initialized - ready for pipeline configuration")
        self._startup_completed = True

    def _initialize_ui_state_async(self) -> None:
        """Schedule UI state initialization in small chunks to keep the UI responsive."""
        # Keep initial status unchanged for tests; perform work asynchronously
        if getattr(self, "_diag_enabled", False):
            logger.info(
                f"[DIAG] scheduling _initialize_ui_state_async at {time.time() - self._init_start_ts:0.3f}s"
            )

        def _do_init():
            try:
                if getattr(self, "_diag_enabled", False):
                    logger.info(
                        f"[DIAG] _initialize_ui_state() start at {time.time() - self._init_start_ts:0.3f}s"
                    )
                # Use the existing initializer (tests may monkeypatch this to a no-op)
                self._initialize_ui_state()
            except Exception:
                # Non-fatal in headless/minimal harness
                logger.warning("UI state init encountered a non-fatal issue", exc_info=True)
            finally:
                try:
                    self._apply_status_text(None)  # resolves to Ready/Error based on state
                except Exception:
                    pass
                if getattr(self, "_diag_enabled", False):
                    logger.info(
                        f"[DIAG] _initialize_ui_state() end at {time.time() - self._init_start_ts:0.3f}s"
                    )

        # Defer to Tk loop so window paints first
        try:
            self.root.after(0, _do_init)
        except Exception:
            # Fallback to synchronous call if scheduling fails
            _do_init()

    def _refresh_prompt_packs(self):
        """Refresh the prompt packs list"""
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.refresh_packs(silent=False)
            self.log_message("Refreshed prompt packs", "INFO")

    def _refresh_prompt_packs_silent(self):
        """Refresh the prompt packs list without logging (for initialization)"""
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.refresh_packs(silent=True)

    def _refresh_prompt_packs_async(self):
        """Scan packs directory on a worker thread and populate asynchronously."""
        if not hasattr(self, "prompt_pack_panel"):
            return

        def scan_and_populate():
            try:
                packs_dir = Path("packs")
                pack_files = get_prompt_packs(packs_dir)
                self.root.after(0, lambda: self.prompt_pack_panel.populate(pack_files))
                self.root.after(
                    0, lambda: self.log_message(f"?? Loaded {len(pack_files)} prompt packs", "INFO")
                )
            except Exception as exc:
                self.root.after(
                    0, lambda err=exc: self.log_message(f"? Failed to load packs: {err}", "WARNING")
                )

        threading.Thread(target=scan_and_populate, daemon=True).start()

    def _refresh_config(self):
        """Refresh configuration based on pack selection and override state"""
        if getattr(self, "_diag_enabled", False):
            logger.info("[DIAG] _refresh_config start")
        # Prevent recursive refreshes
        if self._refreshing_config:
            if getattr(self, "_diag_enabled", False):
                logger.info("[DIAG] _refresh_config skipped (already refreshing)")
            return

        self._refreshing_config = True
        try:
            selected_indices = self.packs_listbox.curselection()
            selected_packs = [self.packs_listbox.get(i) for i in selected_indices]

            # Update UI state based on selection and override mode
            if self.override_pack_var.get():
                # Override mode: use current GUI config for all selected packs
                self._handle_override_mode(selected_packs)
            elif len(selected_packs) == 1:
                # Single pack: show that pack's individual config
                self._handle_single_pack_mode(selected_packs[0])
            elif len(selected_packs) > 1:
                # Multiple packs: grey out config, show status message
                self._handle_multi_pack_mode(selected_packs)
            else:
                # No packs selected: show preset config
                self._handle_no_pack_mode()

        finally:
            self._refreshing_config = False
            if getattr(self, "_diag_enabled", False):
                logger.info("[DIAG] _refresh_config end")

    def _handle_override_mode(self, selected_packs):
        """Handle override mode: current config applies to all selected packs"""
        # Enable all config controls
        self._set_config_editable(True)

        # Update status messages
        if hasattr(self, "current_pack_label"):
            self.current_pack_label.configure(
                text=f"Override mode: {len(selected_packs)} packs selected", foreground="#ffa500"
            )

        # Show override message in config area
        self._show_config_status(
            "Override mode active - current config will be used for all selected packs"
        )

        self.log_message(f"Override mode: Config will apply to {len(selected_packs)} packs", "INFO")

    def _handle_single_pack_mode(self, pack_name):
        """Handle single pack selection: show pack's individual config"""
        if getattr(self, "_diag_enabled", False):
            logger.info(f"[DIAG] _handle_single_pack_mode start; pack={pack_name}")
        # If override mode is NOT enabled, load the pack's config
        if not self.override_pack_var.get():
            # Ensure pack has a config file
            pack_config = self.config_manager.ensure_pack_config(pack_name, self.preset_var.get() or "default")

            # Load pack's individual config into forms
            self._load_config_into_forms(pack_config)
            self.current_config = pack_config

            self.log_message(f"Loaded config for pack: {pack_name}", "INFO")
        else:
            # Override mode: keep current config visible (don't reload from pack)
            self.log_message(f"Override mode: keeping current config for pack: {pack_name}", "INFO")

        # Enable config controls
        self._set_config_editable(True)

        # Update status
        if hasattr(self, "current_pack_label"):
            if self.override_pack_var.get():
                self.current_pack_label.configure(text=f"Pack: {pack_name} (Override)", foreground="#ffa500")
            else:
                self.current_pack_label.configure(text=f"Pack: {pack_name}", foreground="#00ff00")

        if self.override_pack_var.get():
            self._show_config_status(f"Override mode: current config will apply to {pack_name}")
        else:
            self._show_config_status(f"Showing config for pack: {pack_name}")
        if getattr(self, "_diag_enabled", False):
            logger.info(f"[DIAG] _handle_single_pack_mode end; pack={pack_name}")

    def _handle_multi_pack_mode(self, selected_packs):
        """Handle multiple pack selection: show first pack's config, save applies to all"""
        # If override mode is NOT enabled, load the first pack's config
        if not self.override_pack_var.get():
            first_pack = selected_packs[0]
            pack_config = self.config_manager.ensure_pack_config(first_pack, self.preset_var.get() or "default")

            # Load first pack's config into forms
            self._load_config_into_forms(pack_config)
            self.current_config = pack_config

            self.log_message(f"Showing config from first selected pack: {first_pack}", "INFO")
        else:
            # Override mode: keep current config visible
            self.log_message(f"Override mode: current config will apply to {len(selected_packs)} packs", "INFO")

        # Enable config controls
        self._set_config_editable(True)

        # Update status
        if hasattr(self, "current_pack_label"):
            if self.override_pack_var.get():
                self.current_pack_label.configure(
                    text=f"{len(selected_packs)} packs (Override)", foreground="#ffa500"
                )
            else:
                self.current_pack_label.configure(
                    text=f"{len(selected_packs)} packs selected", foreground="#ffff00"
                )

        if self.override_pack_var.get():
            self._show_config_status(
                f"Override mode: current config will apply to all {len(selected_packs)} packs"
            )
        else:
            self._show_config_status(
                f"Showing config from first pack ({selected_packs[0]}). Click Save to apply to all {len(selected_packs)} pack(s)."
            )

    def _handle_no_pack_mode(self):
        """Handle no pack selection: show preset config"""
        # Enable config controls
        self._set_config_editable(True)

        # Load preset config
        preset_config = self.config_manager.load_preset(self.preset_var.get())
        if preset_config:
            self._load_config_into_forms(preset_config)
            self.current_config = preset_config

        # Update status
        if hasattr(self, "current_pack_label"):
            self.current_pack_label.configure(text="No pack selected", foreground="#ff6666")

        self._show_config_status(f"Showing preset config: {self.preset_var.get()}")

    def _set_config_editable(self, editable: bool):
        """Enable/disable config form controls"""
        if hasattr(self, "config_panel"):
            self.config_panel.set_editable(editable)

    def _show_config_status(self, message: str):
        """Show configuration status message in the config area"""
        if hasattr(self, "config_panel"):
            self.config_panel.set_status_message(message)

    def _get_config_from_forms(self) -> dict[str, Any]:
        """Extract current configuration from GUI forms"""
        config = {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}
        # 1) Start with ConfigPanel values if present
        if hasattr(self, "config_panel") and self.config_panel is not None:
            try:
                config = self.config_panel.get_config()
            except Exception as exc:
                self.log_message(f"Error reading config from panel: {exc}", "ERROR")
        # 2) Overlay with values from this form if available (authoritative when present)
        try:
            if hasattr(self, "txt2img_vars"):
                for k, v in self.txt2img_vars.items():
                    config.setdefault("txt2img", {})[k] = v.get()
            if hasattr(self, "img2img_vars"):
                for k, v in self.img2img_vars.items():
                    config.setdefault("img2img", {})[k] = v.get()
            if hasattr(self, "upscale_vars"):
                for k, v in self.upscale_vars.items():
                    config.setdefault("upscale", {})[k] = v.get()
        except Exception as exc:
            self.log_message(f"Error overlaying config from main form: {exc}", "ERROR")

        # 3) Pipeline controls
        if hasattr(self, "pipeline_controls_panel") and self.pipeline_controls_panel is not None:
            try:
                config["pipeline"] = self.pipeline_controls_panel.get_settings()
            except Exception:
                pass

        if hasattr(self, "adetailer_panel") and self.adetailer_panel is not None:
            try:
                config["adetailer"] = self.adetailer_panel.get_config()
            except Exception:
                pass

        try:
            config["randomization"] = self._collect_randomization_config()
        except Exception:
            config["randomization"] = {}

        try:
            config["aesthetic"] = self._collect_aesthetic_config()
        except Exception:
            config["aesthetic"] = {}

        return config
    def _attach_summary_traces(self) -> None:
        """Attach change traces to update live summaries."""
        if getattr(self, "_summary_traces_attached", False):
            return
        try:
            def attach_dict(dct: dict):
                for var in dct.values():
                    try:
                        var.trace_add("write", lambda *_: self._update_live_config_summary())
                    except Exception:
                        pass

            if hasattr(self, "txt2img_vars"):
                attach_dict(self.txt2img_vars)
            if hasattr(self, "img2img_vars"):
                attach_dict(self.img2img_vars)
            if hasattr(self, "upscale_vars"):
                attach_dict(self.upscale_vars)
            if hasattr(self, "pipeline_controls_panel"):
                p = self.pipeline_controls_panel
                for v in (
                    getattr(p, "txt2img_enabled", None),
                    getattr(p, "img2img_enabled", None),
                    getattr(p, "upscale_enabled", None),
                ):
                    try:
                        v and v.trace_add("write", lambda *_: self._update_live_config_summary())
                    except Exception:
                        pass
            self._summary_traces_attached = True
        except Exception:
            pass

    def _update_live_config_summary(self) -> None:
        """Compute and render the per-tab "next run" summaries from current vars."""
        try:
            # txt2img summary
            if hasattr(self, "txt2img_vars") and hasattr(self, "txt2img_summary_var"):
                t = self.txt2img_vars
                steps = t.get("steps").get() if "steps" in t else "-"
                sampler = t.get("sampler_name").get() if "sampler_name" in t else "-"
                cfg = t.get("cfg_scale").get() if "cfg_scale" in t else "-"
                width = t.get("width").get() if "width" in t else "-"
                height = t.get("height").get() if "height" in t else "-"
                self.txt2img_summary_var.set(f"Next run: steps {steps}, sampler {sampler}, cfg {cfg}, size {width}x{height}")

            # img2img summary
            if hasattr(self, "img2img_vars") and hasattr(self, "img2img_summary_var"):
                i2i = self.img2img_vars
                steps = i2i.get("steps").get() if "steps" in i2i else "-"
                denoise = i2i.get("denoising_strength").get() if "denoising_strength" in i2i else "-"
                sampler = i2i.get("sampler_name").get() if "sampler_name" in i2i else "-"
                self.img2img_summary_var.set(f"Next run: steps {steps}, denoise {denoise}, sampler {sampler}")

            # upscale summary
            if hasattr(self, "upscale_vars") and hasattr(self, "upscale_summary_var"):
                up = self.upscale_vars
                mode = (up.get("upscale_mode").get() if "upscale_mode" in up else "single").lower()
                scale = up.get("upscaling_resize").get() if "upscaling_resize" in up else "-"
                if mode == "img2img":
                    steps = up.get("steps").get() if "steps" in up else "-"
                    denoise = up.get("denoising_strength").get() if "denoising_strength" in up else "-"
                    sampler = up.get("sampler_name").get() if "sampler_name" in up else "-"
                    self.upscale_summary_var.set(
                        f"Mode: img2img — steps {steps}, denoise {denoise}, sampler {sampler}, scale {scale}x"
                    )
                else:
                    upscaler = up.get("upscaler").get() if "upscaler" in up else "-"
                    self.upscale_summary_var.set(f"Mode: single — upscaler {upscaler}, scale {scale}x")
        except Exception:
            pass

    def _save_current_pack_config(self):
        """Save current configuration to the selected pack (single pack mode only)"""
        selected_indices = self.packs_listbox.curselection()
        if len(selected_indices) == 1 and not self.override_pack_var.get():
            pack_name = self.packs_listbox.get(selected_indices[0])
            current_config = self._get_config_from_forms()

            if self.config_manager.save_pack_config(pack_name, current_config):
                self.log_message(f"Saved configuration for pack: {pack_name}", "SUCCESS")
                self._show_config_status(f"Configuration saved for pack: {pack_name}")
            else:
                self.log_message(f"Failed to save configuration for pack: {pack_name}", "ERROR")

    def log_message(self, message: str, level: str = "INFO"):
        """Add message to live log with safe console fallback."""
        import datetime
        import sys

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        # Prefer GUI log panel once available
        try:
            add_log = getattr(self, "add_log", None)
            if callable(add_log):
                add_log(log_entry.strip(), level)
            elif getattr(self, "log_panel", None) is not None:
                self.log_panel.log(log_entry.strip(), level)
            else:
                raise RuntimeError("GUI log not ready")
        except Exception:
            # Safe console fallback that won't crash on Windows codepages
            try:
                enc = getattr(sys.stdout, "encoding", None) or "utf-8"
                safe_line = f"[{level}] {log_entry.strip()}".encode(enc, errors="replace").decode(
                    enc, errors="replace"
                )
                print(safe_line)
            except Exception:
                # Last-resort: swallow to avoid crashing the GUI init
                pass

        # Mirror to standard logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    def _attach_tooltip(self, widget: tk.Widget, text: str, delay: int = 1500) -> None:
        """Attach a tooltip to a widget if possible."""
        try:
            Tooltip(widget, text, delay=delay)
        except Exception:
            pass

    def _enable_mousewheel(self, widget: tk.Widget) -> None:
        """Enable cross-platform mousewheel scrolling for a widget that supports yview."""

        def _on_mousewheel(event):
            delta = event.delta
            if not delta and getattr(event, "num", None) in (4, 5):
                delta = 120 if event.num == 4 else -120
            step = int(-1 * (delta / 120))
            try:
                widget.yview_scroll(step, "units")
            except Exception:
                return
            return "break"

        def _bind(_event):
            widget.bind_all("<MouseWheel>", _on_mousewheel)
            widget.bind_all("<Button-4>", _on_mousewheel)
            widget.bind_all("<Button-5>", _on_mousewheel)

        def _unbind(_event):
            widget.unbind_all("<MouseWheel>")
            widget.unbind_all("<Button-4>")
            widget.unbind_all("<Button-5>")

        widget.bind("<Enter>", _bind, add="+")
        widget.bind("<Leave>", _unbind, add="+")

    def _create_scrollable_container(self, parent: tk.Widget):
        """
        Return (container_frame, scrollable_frame) where scrollable_frame grows inside a canvas with vertical scrollbar.
        Caller is responsible for packing the container.
        """

        container = ttk.Frame(parent, style="Dark.TFrame")
        canvas = tk.Canvas(container, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._enable_mousewheel(canvas)
        return container, scrollable_frame

    def _run_full_pipeline(self):
        """Run the complete pipeline"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return

        # Controller-based, cancellable implementation (bypasses legacy thread path below)
        from src.utils.file_io import read_prompt_pack

        from .state import CancellationError

        selected_packs = self._get_selected_packs()
        if not selected_packs:
            self.log_message("No prompt packs selected", "WARNING")
            return

        pack_summary = ", ".join(pack.name for pack in selected_packs)
        self.log_message(
            f"▶️ Starting pipeline execution for {len(selected_packs)} pack(s): {pack_summary}",
            "INFO",
        )
        try:
            override_mode = bool(self.override_pack_var.get())
        except Exception:
            override_mode = False

        # Snapshot Tk-backed values on the main thread (thread-safe)
        try:
            config_snapshot = self._get_config_from_forms()
        except Exception:
            config_snapshot = {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}
        try:
            batch_size_snapshot = int(self.images_per_prompt_var.get())
        except Exception:
            batch_size_snapshot = 1

        config_snapshot = config_snapshot or {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}
        pipeline_overrides = deepcopy(config_snapshot.get("pipeline", {}))
        api_overrides = deepcopy(config_snapshot.get("api", {}))
        try:
            preset_snapshot = self.preset_var.get()
        except Exception:
            preset_snapshot = "default"

        def resolve_config_for_pack(pack_file: Path) -> dict[str, Any]:
            """Return per-pack configuration honoring override mode."""
            if override_mode:
                return deepcopy(config_snapshot)

            pack_config: dict[str, Any] = {}
            if hasattr(self, "config_manager") and self.config_manager:
                try:
                    pack_config = self.config_manager.ensure_pack_config(
                        pack_file.name, preset_snapshot or "default"
                    )
                except Exception as exc:
                    self.log_message(
                        f"⚠️ Failed to load config for {pack_file.name}: {exc}. Using current form values.",
                        "WARNING",
                    )

            merged = deepcopy(pack_config) if pack_config else {}
            if pipeline_overrides:
                merged.setdefault("pipeline", {}).update(pipeline_overrides)
            if api_overrides:
                merged.setdefault("api", {}).update(api_overrides)
            # Always honor runtime-only sections from the current form (they are not stored per-pack)
            for runtime_key in ("randomization", "aesthetic"):
                snapshot_section = deepcopy(config_snapshot.get(runtime_key)) if config_snapshot else None
                if snapshot_section:
                    merged[runtime_key] = snapshot_section

            # Overlay live model / VAE selections from the form in non-override mode if present.
            # Packs often persist a model/vae, but user dropdown changes should take effect for the run.
            try:
                live_txt2img = (config_snapshot or {}).get("txt2img", {})
                if live_txt2img:
                    for k in ("model", "sd_model_checkpoint", "vae"):
                        val = live_txt2img.get(k)
                        if isinstance(val, str) and val.strip():
                            merged.setdefault("txt2img", {})[k] = val.strip()
                live_img2img = (config_snapshot or {}).get("img2img", {})
                if live_img2img:
                    for k in ("model", "sd_model_checkpoint", "vae"):
                        val = live_img2img.get(k)
                        if isinstance(val, str) and val.strip():
                            merged.setdefault("img2img", {})[k] = val.strip()
            except Exception as exc:
                self.log_message(f"⚠️ Failed to overlay live model/VAE selections: {exc}", "WARNING")

            if merged:
                return merged
            return deepcopy(config_snapshot)

        def pipeline_func():
            cancel = self.controller.cancel_token
            session_run_dir = self.structured_logger.create_run_directory()
            self.log_message(f"📁 Session directory: {session_run_dir.name}", "INFO")

            total_generated = 0
            for pack_file in list(selected_packs):
                if cancel.is_cancelled():
                    raise CancellationError("User cancelled before pack start")
                self.log_message(f"📦 Processing pack: {pack_file.name}", "INFO")
                prompts = read_prompt_pack(pack_file)
                if not prompts:
                    self.log_message(f"No prompts found in {pack_file.name}", "WARNING")
                    continue
                config = resolve_config_for_pack(pack_file)
                config_mode = "override" if override_mode else "pack"
                self.log_message(
                    f"⚙️ Using {config_mode} configuration for {pack_file.name}", "INFO"
                )
                rand_cfg = config.get("randomization", {}) or {}
                if rand_cfg.get("enabled"):
                    sr_count = len((rand_cfg.get("prompt_sr", {}) or {}).get("rules", []) or [])
                    wc_count = len((rand_cfg.get("wildcards", {}) or {}).get("tokens", []) or [])
                    mx_slots = len((rand_cfg.get("matrix", {}) or {}).get("slots", []) or [])
                    mx_base = (rand_cfg.get("matrix", {}) or {}).get("base_prompt", "")
                    mx_prompt_mode = (rand_cfg.get("matrix", {}) or {}).get("prompt_mode", "replace")
                    self.log_message(
                        f"🎲 Randomization active: S/R={sr_count}, wildcards={wc_count}, matrix slots={mx_slots}",
                        "INFO",
                    )
                    if mx_base:
                        mode_verb = {"replace": "replace", "append": "append to", "prepend": "prepend to"}
                        verb = mode_verb.get(mx_prompt_mode, "replace")
                        self.log_message(
                            f"🎯 Matrix base_prompt will {verb} pack prompts: {mx_base[:60]}...",
                            "INFO",
                        )
                randomizer = PromptRandomizer(rand_cfg)
                variant_plan = build_variant_plan(config)
                if variant_plan.active:
                    self.log_message(
                        f"🎛️ Variant plan ({variant_plan.mode}) with {len(variant_plan.variants)} combo(s)",
                        "INFO",
                    )
                batch_size = batch_size_snapshot
                rotate_cursor = 0
                prompt_run_index = 0

                for i, prompt_data in enumerate(prompts):
                    if cancel.is_cancelled():
                        raise CancellationError("User cancelled during prompt loop")
                    prompt_text = prompt_data.get("positive", "")
                    self.log_message(
                        f"📝 Prompt {i+1}/{len(prompts)}: {prompt_text[:50]}...",
                        "INFO",
                    )

                    randomized_variants = randomizer.generate(prompt_text)
                    if rand_cfg.get("enabled") and len(randomized_variants) == 1:
                        self.log_message(
                            "ℹ️ Randomization produced only one variant. Ensure prompt contains tokens (e.g. __mood__, [[slot]]) and rules have matches.",
                            "INFO",
                        )
                    if not randomized_variants:
                        randomized_variants = [PromptVariant(text=prompt_text, label=None)]

                    for random_variant in randomized_variants:
                        random_label = random_variant.label
                        variant_prompt_text = random_variant.text
                        if random_label:
                            self.log_message(f"🎲 Randomization: {random_label}", "INFO")

                        if variant_plan.active and variant_plan.variants:
                            if variant_plan.mode == "fanout":
                                variants_to_run = variant_plan.variants
                            else:
                                variant = variant_plan.variants[
                                    rotate_cursor % len(variant_plan.variants)
                                ]
                                variants_to_run = [variant]
                                rotate_cursor += 1
                        else:
                            variants_to_run = [None]

                        for variant in variants_to_run:
                            if cancel.is_cancelled():
                                raise CancellationError("User cancelled during prompt loop")

                            stage_variant_label = None
                            variant_index = 0
                            if variant is not None:
                                stage_variant_label = variant.label
                                variant_index = variant.index
                                self.log_message(
                                    f"🎭 Variant {variant.index + 1}/{len(variant_plan.variants)}: {stage_variant_label}",
                                    "INFO",
                                )

                            effective_config = apply_variant_to_config(config, variant)
                            # Log effective model/VAE selections for visibility in live log
                            try:
                                t2i_cfg = (effective_config or {}).get("txt2img", {}) or {}
                                model_name = t2i_cfg.get("model") or t2i_cfg.get("sd_model_checkpoint") or ""
                                vae_name = t2i_cfg.get("vae") or ""
                                if model_name or vae_name:
                                    self.log_message(
                                        f"🎛️ txt2img weights → model: {model_name or '(unchanged)'}; VAE: {vae_name or '(unchanged)'}",
                                        "INFO",
                                    )
                                i2i_enabled = bool((effective_config or {}).get("pipeline", {}).get("img2img_enabled", False))
                                if i2i_enabled:
                                    i2i_cfg = (effective_config or {}).get("img2img", {}) or {}
                                    i2i_model = i2i_cfg.get("model") or i2i_cfg.get("sd_model_checkpoint") or ""
                                    i2i_vae = i2i_cfg.get("vae") or ""
                                    if i2i_model or i2i_vae:
                                        self.log_message(
                                            f"🎛️ img2img weights → model: {i2i_model or '(unchanged)'}; VAE: {i2i_vae or '(unchanged)'}",
                                            "INFO",
                                        )
                            except Exception:
                                pass
                            result = self.pipeline.run_pack_pipeline(
                                pack_name=pack_file.stem,
                                prompt=variant_prompt_text,
                                config=effective_config,
                                run_dir=session_run_dir,
                                prompt_index=prompt_run_index,
                                batch_size=batch_size,
                                variant_index=variant_index,
                                variant_label=stage_variant_label,
                            )
                            prompt_run_index += 1

                            if cancel.is_cancelled():
                                raise CancellationError("User cancelled after pack stage")

                            if result and result.get("summary"):
                                gen = len(result["summary"])
                                total_generated += gen
                                suffix_parts = []
                                if random_label:
                                    suffix_parts.append(f"random: {random_label}")
                                if stage_variant_label:
                                    suffix_parts.append(f"variant {variant_index + 1}")
                                suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
                                self.log_message(
                                    f"✅ Generated {gen} image(s) for prompt {i+1}{suffix}",
                                    "SUCCESS",
                                )
                            else:
                                suffix_parts = []
                                if random_label:
                                    suffix_parts.append(f"random: {random_label}")
                                if stage_variant_label:
                                    suffix_parts.append(f"variant {variant_index + 1}")
                                suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
                                self.log_message(
                                    f"❌ Failed to generate images for prompt {i+1}{suffix}",
                                    "ERROR",
                                )
                self.log_message(f"✅ Completed pack '{pack_file.stem}'", "SUCCESS")
            return {"images_generated": total_generated, "output_dir": str(session_run_dir)}

        def on_complete(result: dict):
            try:
                num_images = int(result.get("images_generated", 0)) if result else 0
                output_dir = result.get("output_dir", "") if result else ""
            except Exception:
                num_images, output_dir = 0, ""
            self.log_message(f"🎉 Pipeline completed: {num_images} image(s)", "SUCCESS")
            if output_dir:
                self.log_message(f"📂 Output: {output_dir}", "INFO")
            # Combined summary of effective weights
            try:
                model = getattr(self.pipeline, "_current_model", None)
                vae = getattr(self.pipeline, "_current_vae", None)
                hyper = getattr(self.pipeline, "_current_hypernetwork", None)
                hn_strength = getattr(self.pipeline, "_current_hn_strength", None)
                self.log_message(
                    f"🧾 Run summary → model={model or '(none)'}; vae={vae or '(none)'}; hypernetwork={hyper or '(none)'}; strength={hn_strength if hn_strength is not None else '(n/a)'}",
                    "INFO",
                )
            except Exception:
                pass

        def on_error(e: Exception):
            self._handle_pipeline_error(e)

        self.controller.start_pipeline(pipeline_func, on_complete=on_complete, on_error=on_error)
        return

        def run_pipeline_thread():
            try:
                # Create single session run directory for all packs
                session_run_dir = self.structured_logger.create_run_directory()
                self.log_message(f"📁 Created session directory: {session_run_dir.name}", "INFO")

                # Get selected prompt packs
                selected_packs = self._get_selected_packs()
                if not selected_packs:
                    self.log_message("No prompt packs selected", "WARNING")
                    return

                # Process each pack
                for pack_file in selected_packs:
                    self.log_message(f"Processing pack: {pack_file.name}", "INFO")

                    # Read prompts from pack
                    prompts = read_prompt_pack(pack_file)
                    if not prompts:
                        self.log_message(f"No prompts found in {pack_file.name}", "WARNING")
                        continue

                    # Always read the latest form values to ensure UI changes are respected
                    config = self._get_config_from_forms()

                    # Process each prompt in the pack
                    images_generated = 0
                    for i, prompt_data in enumerate(prompts):
                        try:
                            self.log_message(
                                f"Processing prompt {i+1}/{len(prompts)}: {prompt_data['positive'][:50]}...",
                                "INFO",
                            )

                            # Run pipeline with new directory structure
                            result = self.pipeline.run_pack_pipeline(
                                pack_name=pack_file.stem,
                                prompt=prompt_data["positive"],
                                config=config,
                                run_dir=session_run_dir,
                                prompt_index=i,
                                batch_size=int(self.images_per_prompt_var.get()),
                            )

                            if result and result.get("summary"):
                                images_generated += len(result["summary"])
                                self.log_message(
                                    f"✅ Generated {len(result['summary'])} images for prompt {i+1}",
                                    "SUCCESS",
                                )
                            else:
                                self.log_message(
                                    f"❌ Failed to generate images for prompt {i+1}", "ERROR"
                                )

                        except Exception as e:
                            self.log_message(f"❌ Error processing prompt {i+1}: {str(e)}", "ERROR")
                            continue

                    self.log_message(
                        f"Completed pack {pack_file.name}: {images_generated} images", "SUCCESS"
                    )

                self.log_message("🎉 Pipeline execution completed!", "SUCCESS")

            except Exception as e:
                self.log_message(f"Pipeline execution failed: {e}", "ERROR")

        # Run in separate thread to avoid blocking UI
        self.log_message("🚀 Starting pipeline execution...", "INFO")
        threading.Thread(target=run_pipeline_thread, daemon=True).start()

    def _run_txt2img_only(self):
        """Run only txt2img generation"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return

        # Check if packs are selected
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Selection Error", "Please select at least one prompt pack")
            return

        self.log_message("🎨 Running txt2img only...", "INFO")

        def txt2img_thread():
            try:
                # Get selected packs
                selected_packs = [self.packs_listbox.get(i) for i in selected_indices]

                # Create run directory
                run_dir = self.structured_logger.create_run_directory("txt2img_only")

                # Run txt2img for selected packs
                for pack_name in selected_packs:
                    self.log_message(f"Processing pack: {pack_name}", "INFO")

                    # Load prompts from pack
                    pack_path = Path("packs") / pack_name
                    prompts = read_prompt_pack(pack_path)

                    if not prompts:
                        self.log_message(f"No prompts found in {pack_name}", "WARNING")
                        continue

                    # Get pack-specific overrides
                    pack_overrides = self.config_manager.get_pack_overrides(pack_path.stem)
                    pack_config = self.config_manager.resolve_config("default", pack_overrides)

                    # Generate images for each prompt
                    for i, prompt_data in enumerate(prompts):
                        try:
                            self.log_message(
                                f"Generating image {i+1}/{len(prompts)}: {prompt_data['positive'][:50]}...",
                                "INFO",
                            )

                            # Run txt2img using the pipeline
                            results = self.pipeline.run_txt2img(
                                prompt=prompt_data["positive"],
                                config=pack_config.get("txt2img", {}),
                                run_dir=run_dir,
                                batch_size=1,
                            )

                            if results:
                                self.log_message(f"✅ Generated {len(results)} images", "SUCCESS")
                            else:
                                self.log_message(f"❌ Failed to generate image {i+1}", "ERROR")

                        except Exception as e:
                            self.log_message(f"❌ Error generating image {i+1}: {str(e)}", "ERROR")
                            continue

                self.log_message("🎉 Txt2img generation completed!", "SUCCESS")

            except Exception as e:
                self.log_message(f"❌ Txt2img generation failed: {str(e)}", "ERROR")

        # Run in background thread
        import threading

        thread = threading.Thread(target=txt2img_thread)
        thread.daemon = True
        thread.start()

    def _run_upscale_only(self):
        """Run upscaling on existing images"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
            return

        # Open file dialog to select images
        file_paths = filedialog.askopenfilenames(
            title="Select Images to Upscale",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")],
        )

        if not file_paths:
            return

        def upscale_thread():
            try:
                config = self.current_config or self.config_manager.get_default_config()
                run_dir = self.structured_logger.create_run_directory("upscale_only")

                for file_path in file_paths:
                    image_path = Path(file_path)
                    self.log_message(f"Upscaling: {image_path.name}", "INFO")

                    result = self.pipeline.run_upscale(image_path, config["upscale"], run_dir)
                    if result:
                        self.log_message(f"✅ Upscaled: {image_path.name}", "SUCCESS")
                    else:
                        self.log_message(f"❌ Failed to upscale: {image_path.name}", "ERROR")

                self.log_message("Upscaling completed!", "SUCCESS")

            except Exception as e:
                self.log_message(f"Upscaling failed: {e}", "ERROR")

        threading.Thread(target=upscale_thread, daemon=True).start()

    def _create_video(self):
        """Create video from image sequence"""
        # Open folder dialog to select image directory
        folder_path = filedialog.askdirectory(title="Select Image Directory")
        if not folder_path:
            return

        def video_thread():
            try:
                image_dir = Path(folder_path)
                image_files = []

                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    image_files.extend(image_dir.glob(ext))

                if not image_files:
                    self.log_message("No images found in selected directory", "WARNING")
                    return

                # Create output video path
                video_path = image_dir / "output_video.mp4"

                self.log_message(f"Creating video from {len(image_files)} images...", "INFO")

                success = self.video_creator.create_video_from_images(
                    image_files, video_path, fps=24
                )

                if success:
                    self.log_message(f"✅ Video created: {video_path}", "SUCCESS")
                else:
                    self.log_message("❌ Video creation failed", "ERROR")

            except Exception as e:
                self.log_message(f"Video creation failed: {e}", "ERROR")

        threading.Thread(target=video_thread, daemon=True).start()

    def _get_selected_packs(self) -> list[Path]:
        """Resolve the currently selected prompt packs in UI order."""
        pack_names: list[str] = []

        if getattr(self, "selected_packs", None):
            pack_names = list(dict.fromkeys(self.selected_packs))
        elif hasattr(self, "prompt_pack_panel") and hasattr(
            self.prompt_pack_panel, "get_selected_packs"
        ):
            try:
                pack_names = list(self.prompt_pack_panel.get_selected_packs())
            except Exception:
                pack_names = []

        if not pack_names and hasattr(self, "packs_listbox"):
            try:
                selected_indices = self.packs_listbox.curselection()
                pack_names = [self.packs_listbox.get(i) for i in selected_indices]
            except Exception:
                pack_names = []

        packs_dir = Path("packs")
        resolved: list[Path] = []
        for pack_name in pack_names:
            pack_path = packs_dir / pack_name
            if pack_path.exists():
                resolved.append(pack_path)
            else:
                self.log_message(f"⚠️ Pack not found on disk: {pack_path}", "WARNING")

        return resolved

    def _build_info_box(self, parent, title: str, text: str):
        """Reusable helper for informational sections within tabs."""
        frame = ttk.LabelFrame(parent, text=title, style="Dark.TFrame", padding=6)
        ttk.Label(frame, text=text, style="Dark.TLabel", wraplength=520, justify=tk.LEFT).pack(
            fill=tk.X
        )
        return frame

    def _open_output_folder(self):
        """Open the output folder"""
        output_dir = Path("output")
        if output_dir.exists():
            if sys.platform == "win32":
                subprocess.run(["explorer", str(output_dir)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(output_dir)])
            else:
                subprocess.run(["xdg-open", str(output_dir)])
        else:
            messagebox.showinfo("No Output", "Output directory doesn't exist yet")

    def _stop_execution(self):
        """Stop the running pipeline"""
        if self.controller.stop_pipeline():
            self.log_message("⏹️ Stop requested - cancelling pipeline...", "WARNING")
        else:
            self.log_message("⏹️ No pipeline running", "INFO")

    def _open_prompt_editor(self):
        """Open the advanced prompt pack editor"""
        selected_indices = self.packs_listbox.curselection()
        pack_path = None

        if selected_indices:
            pack_name = self.packs_listbox.get(selected_indices[0])
            pack_path = Path("packs") / pack_name

        # Initialize advanced editor if not already done
        if not hasattr(self, "advanced_editor"):
            self.advanced_editor = AdvancedPromptEditor(
                parent_window=self.root,
                config_manager=self.config_manager,
                on_packs_changed=self._refresh_prompt_packs,
                on_validation=self._handle_editor_validation,
            )

        # Open editor with selected pack
        self.advanced_editor.open_editor(pack_path)

    def _handle_editor_validation(self, results):
        """Handle validation results from the prompt editor"""
        # Log validation summary
        error_count = len(results.get("errors", []))
        warning_count = len(results.get("warnings", []))
    # info_count = len(results.get("info", []))  # Removed unused variable

        if error_count == 0 and warning_count == 0:
            self.log_message("✅ Pack validation passed - no issues found", "SUCCESS")
        else:
            if error_count > 0:
                self.log_message(f"❌ Pack validation found {error_count} error(s)", "ERROR")
                for error in results["errors"][:3]:  # Show first 3 errors
                    self.log_message(f"  • {error}", "ERROR")
                if error_count > 3:
                    self.log_message(f"  ... and {error_count - 3} more", "ERROR")

            if warning_count > 0:
                self.log_message(f"⚠️  Pack has {warning_count} warning(s)", "WARNING")
                for warning in results["warnings"][:2]:  # Show first 2 warnings
                    self.log_message(f"  • {warning}", "WARNING")
                if warning_count > 2:
                    self.log_message(f"  ... and {warning_count - 2} more", "WARNING")

        # Show stats
        stats = results.get("stats", {})
        self.log_message(
            f"📊 Pack stats: {stats.get('prompt_count', 0)} prompts, "
            f"{stats.get('embedding_count', 0)} embeddings, "
            f"{stats.get('lora_count', 0)} LoRAs",
            "INFO",
        )

    def _open_advanced_editor(self):
        """Wrapper method for opening advanced editor (called by button)"""
        self._open_prompt_editor()

    def _graceful_exit(self):
        """Gracefully exit the application"""
        self.log_message("Shutting down gracefully...", "INFO")

        # Save any pending manifests
        try:
            # Finalize logs and manifests
            self.log_message("✅ Graceful shutdown complete", "SUCCESS")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        # Persist current preferences
        try:
            preferences = self._collect_preferences()
            if self.preferences_manager.save_preferences(preferences):
                self.preferences = preferences
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.error(f"Failed to save preferences: {exc}")

        # Attempt to stop any running pipeline cleanly
        try:
            if hasattr(self, "controller") and self.controller is not None and not self.controller.is_terminal:
                try:
                    self.controller.stop_pipeline()
                except Exception:
                    pass
                # Wait briefly for cleanup
                try:
                    self.controller.lifecycle_event.wait(timeout=5.0)
                except Exception:
                    pass
        except Exception:
            pass

        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the GUI application"""
        # Start initial config refresh
        self._refresh_config()

        # Now refresh prompt packs asynchronously to avoid blocking
        self._refresh_prompt_packs_async()

        # Set up proper window closing
        self.root.protocol("WM_DELETE_WINDOW", self._graceful_exit)

        self.log_message("🚀 StableNew GUI started", "SUCCESS")
        self.log_message("Please connect to WebUI API to begin", "INFO")

        # Ensure window is visible and focused before starting mainloop
        self.root.deiconify()  # Make sure window is not minimized
        self.root.lift()  # Bring to front
        self.root.focus_force()  # Force focus

        # Log window state for debugging
        self.log_message("🖥️ GUI window should now be visible", "INFO")

        # Add a periodic check to ensure window stays visible
        def check_window_visibility():
            if self.root.state() == "iconic":  # Window is minimized
                self.log_message("⚠️ Window was minimized, restoring...", "WARNING")
                self.root.deiconify()
                self.root.lift()
            # Schedule next check in 30 seconds
            self.root.after(30000, check_window_visibility)

        # Start the visibility checker
        self.root.after(5000, check_window_visibility)  # First check after 5 seconds


    def run(self):
        """Start the Tkinter main loop with diagnostics."""
        logger.info("[DIAG] About to enter Tkinter mainloop", extra={"flush": True})
        self.root.mainloop()

    def _build_txt2img_config_tab(self, notebook):
        """Build txt2img configuration form"""
        tab_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(tab_frame, text="🎨 txt2img")

        # Pack status header
        pack_status_frame = ttk.Frame(tab_frame, style="Dark.TFrame")
        pack_status_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(
            pack_status_frame, text="Current Pack:", style="Dark.TLabel", font=("Arial", 9, "bold")
        ).pack(side=tk.LEFT)
        self.current_pack_label = ttk.Label(
            pack_status_frame,
            text="No pack selected",
            style="Dark.TLabel",
            font=("Arial", 9),
            foreground="#ffa500",
        )
        self.current_pack_label.pack(side=tk.LEFT, padx=(5, 0))

        # Override controls
        override_frame = ttk.Frame(tab_frame, style="Dark.TFrame")
        override_frame.pack(fill=tk.X, padx=10, pady=5)

        self.override_pack_var = tk.BooleanVar(value=False)
        override_checkbox = ttk.Checkbutton(
            override_frame,
            text="Override pack settings with current config",
            variable=self.override_pack_var,
            style="Dark.TCheckbutton",
            command=self._on_override_changed,
        )
        override_checkbox.pack(side=tk.LEFT)

        ttk.Separator(tab_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)

        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Initialize config variables and widget references
        self.txt2img_vars = {}
        self.txt2img_widgets = {}

        # Compact generation settings
        gen_frame = ttk.LabelFrame(
            scrollable_frame, text="Generation Settings", style="Dark.TFrame", padding=5
        )
        gen_frame.pack(fill=tk.X, pady=2)

        # Steps - compact inline
        steps_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        steps_row.pack(fill=tk.X, pady=2)
        ttk.Label(steps_row, text="Generation Steps:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.txt2img_vars["steps"] = tk.IntVar(value=20)
        steps_spin = ttk.Spinbox(
            steps_row, from_=1, to=150, width=8, textvariable=self.txt2img_vars["steps"]
        )
        steps_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["steps"] = steps_spin

        # Sampler - compact inline
        sampler_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        sampler_row.pack(fill=tk.X, pady=2)
        ttk.Label(sampler_row, text="Sampler:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["sampler_name"] = tk.StringVar(value="Euler a")
        sampler_combo = ttk.Combobox(
            sampler_row,
            textvariable=self.txt2img_vars["sampler_name"],
            values=[
                "Euler a",
                "Euler",
                "LMS",
                "Heun",
                "DPM2",
                "DPM2 a",
                "DPM++ 2S a",
                "DPM++ 2M",
                "DPM++ SDE",
                "DPM fast",
                "DPM adaptive",
                "LMS Karras",
                "DPM2 Karras",
                "DPM2 a Karras",
                "DPM++ 2S a Karras",
                "DPM++ 2M Karras",
                "DPM++ SDE Karras",
                "DDIM",
                "PLMS",
            ],
            width=18,
            state="readonly",
        )
        sampler_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["sampler_name"] = sampler_combo

        # CFG Scale - compact inline
        cfg_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        cfg_row.pack(fill=tk.X, pady=2)
        ttk.Label(cfg_row, text="CFG Scale:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["cfg_scale"] = tk.DoubleVar(value=7.0)
        cfg_slider = EnhancedSlider(
            cfg_row,
            from_=1.0,
            to=20.0,
            variable=self.txt2img_vars["cfg_scale"],
            resolution=0.1,
            width=120,
        )
        cfg_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.txt2img_widgets["cfg_scale"] = cfg_slider

        # Dimensions - compact single row
        dims_frame = ttk.LabelFrame(
            scrollable_frame, text="Image Dimensions", style="Dark.TFrame", padding=5
        )
        dims_frame.pack(fill=tk.X, pady=2)

        dims_row = ttk.Frame(dims_frame, style="Dark.TFrame")
        dims_row.pack(fill=tk.X)

        ttk.Label(dims_row, text="Width:", style="Dark.TLabel", width=8).pack(side=tk.LEFT)
        self.txt2img_vars["width"] = tk.IntVar(value=512)
        width_combo = ttk.Combobox(
            dims_row,
            textvariable=self.txt2img_vars["width"],
            values=[256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024],
            width=8,
        )
        width_combo.pack(side=tk.LEFT, padx=(2, 10))
        self.txt2img_widgets["width"] = width_combo

        ttk.Label(dims_row, text="Height:", style="Dark.TLabel", width=8).pack(side=tk.LEFT)
        self.txt2img_vars["height"] = tk.IntVar(value=512)
        height_combo = ttk.Combobox(
            dims_row,
            textvariable=self.txt2img_vars["height"],
            values=[256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024],
            width=8,
        )
        height_combo.pack(side=tk.LEFT, padx=2)
        self.txt2img_widgets["height"] = height_combo

        # Advanced Settings
        advanced_frame = ttk.LabelFrame(
            scrollable_frame, text="Advanced Settings", style="Dark.TFrame", padding=5
        )
        advanced_frame.pack(fill=tk.X, pady=2)

        # Seed controls
        seed_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        seed_row.pack(fill=tk.X, pady=2)
        ttk.Label(seed_row, text="Seed:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["seed"] = tk.IntVar(value=-1)
        seed_spin = ttk.Spinbox(
            seed_row, from_=-1, to=2147483647, width=12, textvariable=self.txt2img_vars["seed"]
        )
        seed_spin.pack(side=tk.LEFT, padx=(5, 5))
        self.txt2img_widgets["seed"] = seed_spin
        ttk.Button(
            seed_row,
            text="🎲 Random",
            command=lambda: self.txt2img_vars["seed"].set(-1),
            width=10,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(5, 0))

        # CLIP Skip
        clip_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        clip_row.pack(fill=tk.X, pady=2)
        ttk.Label(clip_row, text="CLIP Skip:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["clip_skip"] = tk.IntVar(value=2)
        clip_spin = ttk.Spinbox(
            clip_row, from_=1, to=12, width=8, textvariable=self.txt2img_vars["clip_skip"]
        )
        clip_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["clip_skip"] = clip_spin

        # Scheduler
        scheduler_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        scheduler_row.pack(fill=tk.X, pady=2)
        ttk.Label(scheduler_row, text="Scheduler:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.txt2img_vars["scheduler"] = tk.StringVar(value="normal")
        scheduler_combo = ttk.Combobox(
            scheduler_row,
            textvariable=self.txt2img_vars["scheduler"],
            values=[
                "normal",
                "Karras",
                "exponential",
                "sgm_uniform",
                "simple",
                "ddim_uniform",
                "beta",
                "linear",
                "cosine",
            ],
            width=15,
            state="readonly",
        )
        scheduler_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["scheduler"] = scheduler_combo

        # Model Selection
        model_frame = ttk.LabelFrame(
            scrollable_frame, text="Model & VAE Selection", style="Dark.TFrame", padding=5
        )
        model_frame.pack(fill=tk.X, pady=2)

        # SD Model
        model_row = ttk.Frame(model_frame, style="Dark.TFrame")
        model_row.pack(fill=tk.X, pady=2)
        ttk.Label(model_row, text="SD Model:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["model"] = tk.StringVar(value="")
        self.model_combo = ttk.Combobox(
            model_row, textvariable=self.txt2img_vars["model"], width=40, state="readonly"
        )
        self.model_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.txt2img_widgets["model"] = self.model_combo
        ttk.Button(
            model_row, text="🔄", command=self._refresh_models, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        # VAE Model
        vae_row = ttk.Frame(model_frame, style="Dark.TFrame")
        vae_row.pack(fill=tk.X, pady=2)
        ttk.Label(vae_row, text="VAE Model:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["vae"] = tk.StringVar(value="")
        self.vae_combo = ttk.Combobox(
            vae_row, textvariable=self.txt2img_vars["vae"], width=40, state="readonly"
        )
        self.vae_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.txt2img_widgets["vae"] = self.vae_combo
        ttk.Button(
            vae_row, text="🔄", command=self._refresh_vae_models, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        # Hires.Fix Settings
        hires_frame = ttk.LabelFrame(
            scrollable_frame, text="High-Res Fix (Hires.fix)", style="Dark.TFrame", padding=5
        )
        hires_frame.pack(fill=tk.X, pady=2)

        # Enable Hires.fix checkbox
        hires_enable_row = ttk.Frame(hires_frame, style="Dark.TFrame")
        hires_enable_row.pack(fill=tk.X, pady=2)
        self.txt2img_vars["enable_hr"] = tk.BooleanVar(value=False)
        hires_check = ttk.Checkbutton(
            hires_enable_row,
            text="Enable High-Resolution Fix",
            variable=self.txt2img_vars["enable_hr"],
            style="Dark.TCheckbutton",
            command=self._on_hires_toggle,
        )
        hires_check.pack(side=tk.LEFT)
        self.txt2img_widgets["enable_hr"] = hires_check

        # Hires scale
        scale_row = ttk.Frame(hires_frame, style="Dark.TFrame")
        scale_row.pack(fill=tk.X, pady=2)
        ttk.Label(scale_row, text="Scale Factor:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.txt2img_vars["hr_scale"] = tk.DoubleVar(value=2.0)
        scale_spin = ttk.Spinbox(
            scale_row,
            from_=1.1,
            to=4.0,
            increment=0.1,
            width=8,
            textvariable=self.txt2img_vars["hr_scale"],
        )
        scale_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["hr_scale"] = scale_spin

        # Hires upscaler
        upscaler_row = ttk.Frame(hires_frame, style="Dark.TFrame")
        upscaler_row.pack(fill=tk.X, pady=2)
        ttk.Label(upscaler_row, text="HR Upscaler:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.txt2img_vars["hr_upscaler"] = tk.StringVar(value="Latent")
        hr_upscaler_combo = ttk.Combobox(
            upscaler_row,
            textvariable=self.txt2img_vars["hr_upscaler"],
            values=[
                "Latent",
                "Latent (antialiased)",
                "Latent (bicubic)",
                "Latent (bicubic antialiased)",
                "Latent (nearest)",
                "Latent (nearest-exact)",
                "None",
                "Lanczos",
                "Nearest",
                "LDSR",
                "BSRGAN",
                "ESRGAN_4x",
                "R-ESRGAN General 4xV3",
                "ScuNET GAN",
                "ScuNET PSNR",
                "SwinIR 4x",
            ],
            width=20,
            state="readonly",
        )
        hr_upscaler_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.txt2img_widgets["hr_upscaler"] = hr_upscaler_combo

        # Hires denoising strength
        hr_denoise_row = ttk.Frame(hires_frame, style="Dark.TFrame")
        hr_denoise_row.pack(fill=tk.X, pady=2)
        ttk.Label(hr_denoise_row, text="HR Denoising:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.txt2img_vars["denoising_strength"] = tk.DoubleVar(value=0.7)
        hr_denoise_slider = EnhancedSlider(
            hr_denoise_row,
            from_=0.0,
            to=1.0,
            variable=self.txt2img_vars["denoising_strength"],
            resolution=0.05,
            length=150,
        )
        hr_denoise_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.txt2img_widgets["denoising_strength"] = hr_denoise_slider

        # Additional Positive Prompt - compact
        pos_frame = ttk.LabelFrame(
            scrollable_frame,
            text="Additional Positive Prompt (appended to pack prompts)",
            style="Dark.TFrame",
            padding=5,
        )
        pos_frame.pack(fill=tk.X, pady=2)
        self.txt2img_vars["prompt"] = tk.StringVar(value="")
        self.pos_text = tk.Text(
            pos_frame, height=2, bg="#3d3d3d", fg="#ffffff", wrap=tk.WORD, font=("Segoe UI", 9)
        )
        self.pos_text.pack(fill=tk.X, pady=2)

        # Additional Negative Prompt - compact
        neg_frame = ttk.LabelFrame(
            scrollable_frame,
            text="Additional Negative Prompt (appended to pack negative prompts)",
            style="Dark.TFrame",
            padding=5,
        )
        neg_frame.pack(fill=tk.X, pady=2)
        self.txt2img_vars["negative_prompt"] = tk.StringVar(
            value="blurry, bad quality, distorted, ugly, malformed"
        )
        self.neg_text = tk.Text(
            neg_frame, height=2, bg="#3d3d3d", fg="#ffffff", wrap=tk.WORD, font=("Segoe UI", 9)
        )
        self.neg_text.pack(fill=tk.X, pady=2)
        self.neg_text.insert(1.0, self.txt2img_vars["negative_prompt"].get())

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._enable_mousewheel(canvas)
        self._enable_mousewheel(canvas)
        self._enable_mousewheel(canvas)

        # Live summary for next run (txt2img)
        try:
            self.txt2img_summary_var = getattr(self, "txt2img_summary_var", tk.StringVar(value=""))
            summary_frame = ttk.Frame(tab_frame, style="Dark.TFrame")
            summary_frame.pack(fill=tk.X, padx=10, pady=(5, 8))
            ttk.Label(
                summary_frame,
                textvariable=self.txt2img_summary_var,
                style="Dark.TLabel",
                font=("Consolas", 9),
            ).pack(side=tk.LEFT)
        except Exception:
            pass

        # Attach traces and initialize summary text
        try:
            self._attach_summary_traces()
            self._update_live_config_summary()
        except Exception:
            pass

    def _build_img2img_config_tab(self, notebook):
        """Build img2img configuration form"""
        tab_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(tab_frame, text="🧹 img2img")

        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg="#2b2b2b")
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Initialize config variables
        self.img2img_vars = {}
        self.img2img_widgets = {}

        # Generation Settings
        gen_frame = ttk.LabelFrame(
            scrollable_frame, text="Generation Settings", style="Dark.TFrame", padding=5
        )
        gen_frame.pack(fill=tk.X, pady=2)

        # Steps
        steps_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        steps_row.pack(fill=tk.X, pady=2)
        ttk.Label(steps_row, text="Steps:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["steps"] = tk.IntVar(value=15)
        steps_spin = ttk.Spinbox(
            steps_row, from_=1, to=150, width=8, textvariable=self.img2img_vars["steps"]
        )
        steps_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.img2img_widgets["steps"] = steps_spin

        # Denoising Strength
        denoise_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        denoise_row.pack(fill=tk.X, pady=2)
        ttk.Label(denoise_row, text="Denoising:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["denoising_strength"] = tk.DoubleVar(value=0.3)
        denoise_slider = EnhancedSlider(
            denoise_row,
            from_=0.0,
            to=1.0,
            variable=self.img2img_vars["denoising_strength"],
            resolution=0.01,
            width=120,
        )
        denoise_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["denoising_strength"] = denoise_slider

        # Sampler
        sampler_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        sampler_row.pack(fill=tk.X, pady=2)
        ttk.Label(sampler_row, text="Sampler:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["sampler_name"] = tk.StringVar(value="Euler a")
        sampler_combo = ttk.Combobox(
            sampler_row,
            textvariable=self.img2img_vars["sampler_name"],
            values=[
                "Euler a",
                "Euler",
                "LMS",
                "Heun",
                "DPM2",
                "DPM2 a",
                "DPM++ 2S a",
                "DPM++ 2M",
                "DPM++ SDE",
                "DPM fast",
                "DPM adaptive",
                "LMS Karras",
                "DPM2 Karras",
                "DPM2 a Karras",
                "DPM++ 2S a Karras",
                "DPM++ 2M Karras",
                "DPM++ SDE Karras",
                "DDIM",
                "PLMS",
            ],
            width=18,
            state="readonly",
        )
        sampler_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.img2img_widgets["sampler_name"] = sampler_combo

        # CFG Scale
        cfg_row = ttk.Frame(gen_frame, style="Dark.TFrame")
        cfg_row.pack(fill=tk.X, pady=2)
        ttk.Label(cfg_row, text="CFG Scale:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["cfg_scale"] = tk.DoubleVar(value=7.0)
        cfg_slider = EnhancedSlider(
            cfg_row,
            from_=1.0,
            to=20.0,
            variable=self.img2img_vars["cfg_scale"],
            resolution=0.5,
            length=150,
        )
        cfg_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["cfg_scale"] = cfg_slider

        # Advanced Settings
        advanced_frame = ttk.LabelFrame(
            scrollable_frame, text="Advanced Settings", style="Dark.TFrame", padding=5
        )
        advanced_frame.pack(fill=tk.X, pady=2)

        # Seed
        seed_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        seed_row.pack(fill=tk.X, pady=2)
        ttk.Label(seed_row, text="Seed:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["seed"] = tk.IntVar(value=-1)
        seed_spin = ttk.Spinbox(
            seed_row, from_=-1, to=2147483647, width=12, textvariable=self.img2img_vars["seed"]
        )
        seed_spin.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["seed"] = seed_spin
        ttk.Button(
            seed_row,
            text="🎲 Random",
            command=lambda: self.img2img_vars["seed"].set(-1),
            width=10,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(5, 0))

        # CLIP Skip
        clip_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        clip_row.pack(fill=tk.X, pady=2)
        ttk.Label(clip_row, text="CLIP Skip:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["clip_skip"] = tk.IntVar(value=2)
        clip_spin = ttk.Spinbox(
            clip_row, from_=1, to=12, width=8, textvariable=self.img2img_vars["clip_skip"]
        )
        clip_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.img2img_widgets["clip_skip"] = clip_spin

        # Scheduler
        scheduler_row = ttk.Frame(advanced_frame, style="Dark.TFrame")
        scheduler_row.pack(fill=tk.X, pady=2)
        ttk.Label(scheduler_row, text="Scheduler:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.img2img_vars["scheduler"] = tk.StringVar(value="normal")
        scheduler_combo = ttk.Combobox(
            scheduler_row,
            textvariable=self.img2img_vars["scheduler"],
            values=[
                "normal",
                "Karras",
                "exponential",
                "sgm_uniform",
                "simple",
                "ddim_uniform",
                "beta",
                "linear",
                "cosine",
            ],
            width=15,
            state="readonly",
        )
        scheduler_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.img2img_widgets["scheduler"] = scheduler_combo

        # Model Selection
        model_frame = ttk.LabelFrame(
            scrollable_frame, text="Model & VAE Selection", style="Dark.TFrame", padding=5
        )
        model_frame.pack(fill=tk.X, pady=2)

        # SD Model
        model_row = ttk.Frame(model_frame, style="Dark.TFrame")
        model_row.pack(fill=tk.X, pady=2)
        ttk.Label(model_row, text="SD Model:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["model"] = tk.StringVar(value="")
        self.img2img_model_combo = ttk.Combobox(
            model_row, textvariable=self.img2img_vars["model"], width=40, state="readonly"
        )
        self.img2img_model_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["model"] = self.img2img_model_combo
        ttk.Button(
            model_row, text="🔄", command=self._refresh_models, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        # VAE Model
        vae_row = ttk.Frame(model_frame, style="Dark.TFrame")
        vae_row.pack(fill=tk.X, pady=2)
        ttk.Label(vae_row, text="VAE Model:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.img2img_vars["vae"] = tk.StringVar(value="")
        self.img2img_vae_combo = ttk.Combobox(
            vae_row, textvariable=self.img2img_vars["vae"], width=40, state="readonly"
        )
        self.img2img_vae_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["vae"] = self.img2img_vae_combo
        ttk.Button(
            vae_row, text="🔄", command=self._refresh_vae_models, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        canvas.pack(fill="both", expand=True)

        # Live summary for next run (upscale)
        try:
            self.upscale_summary_var = getattr(self, "upscale_summary_var", tk.StringVar(value=""))
            summary_frame = ttk.Frame(tab_frame, style="Dark.TFrame")
            summary_frame.pack(fill=tk.X, padx=10, pady=(5, 8))
            ttk.Label(
                summary_frame,
                textvariable=self.upscale_summary_var,
                style="Dark.TLabel",
                font=("Consolas", 9),
            ).pack(side=tk.LEFT)
        except Exception:
            pass

        try:
            self._attach_summary_traces()
            self._update_live_config_summary()
        except Exception:
            pass

        # Live summary for next run (img2img)
        try:
            self.img2img_summary_var = getattr(self, "img2img_summary_var", tk.StringVar(value=""))
            summary_frame = ttk.Frame(tab_frame, style="Dark.TFrame")
            summary_frame.pack(fill=tk.X, padx=10, pady=(5, 8))
            ttk.Label(
                summary_frame,
                textvariable=self.img2img_summary_var,
                style="Dark.TLabel",
                font=("Consolas", 9),
            ).pack(side=tk.LEFT)
        except Exception:
            pass

        try:
            self._attach_summary_traces()
            self._update_live_config_summary()
        except Exception:
            pass

    def _build_upscale_config_tab(self, notebook):
        """Build upscale configuration form"""
        tab_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(tab_frame, text="📈 Upscale")

        # Create scrollable frame
        canvas = tk.Canvas(tab_frame, bg="#2b2b2b")
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Initialize config variables
        self.upscale_vars = {}
        self.upscale_widgets = {}

        # Upscaling Method
        method_frame = ttk.LabelFrame(
            scrollable_frame, text="Upscaling Method", style="Dark.TFrame", padding=5
        )
        method_frame.pack(fill=tk.X, pady=2)

        method_row = ttk.Frame(method_frame, style="Dark.TFrame")
        method_row.pack(fill=tk.X, pady=2)
        ttk.Label(method_row, text="Method:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.upscale_vars["upscale_mode"] = tk.StringVar(value="single")
        method_combo = ttk.Combobox(
            method_row,
            textvariable=self.upscale_vars["upscale_mode"],
            values=["single", "img2img"],
            width=20,
            state="readonly",
        )
        method_combo.pack(side=tk.LEFT, padx=(5, 5))
        try:
            method_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_upscale_method_state())
        except Exception:
            pass
        self.upscale_widgets["upscale_mode"] = method_combo
        ttk.Label(method_row, text="ℹ️ img2img allows denoising", style="Dark.TLabel").pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Basic Upscaling Settings
        basic_frame = ttk.LabelFrame(
            scrollable_frame, text="Basic Settings", style="Dark.TFrame", padding=5
        )
        basic_frame.pack(fill=tk.X, pady=2)

        # Upscaler selection
        upscaler_row = ttk.Frame(basic_frame, style="Dark.TFrame")
        upscaler_row.pack(fill=tk.X, pady=2)
        ttk.Label(upscaler_row, text="Upscaler:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.upscale_vars["upscaler"] = tk.StringVar(value="R-ESRGAN 4x+")
        self.upscaler_combo = ttk.Combobox(
            upscaler_row, textvariable=self.upscale_vars["upscaler"], width=40, state="readonly"
        )
        self.upscaler_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.upscale_widgets["upscaler"] = self.upscaler_combo
        ttk.Button(
            upscaler_row, text="🔄", command=self._refresh_upscalers, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        # Scale factor
        scale_row = ttk.Frame(basic_frame, style="Dark.TFrame")
        scale_row.pack(fill=tk.X, pady=2)
        ttk.Label(scale_row, text="Scale Factor:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.upscale_vars["upscaling_resize"] = tk.DoubleVar(value=2.0)
        scale_spin = ttk.Spinbox(
            scale_row,
            from_=1.1,
            to=4.0,
            increment=0.1,
            width=8,
            textvariable=self.upscale_vars["upscaling_resize"],
        )
        scale_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.upscale_widgets["upscaling_resize"] = scale_spin

        # Steps for img2img mode
        steps_row = ttk.Frame(basic_frame, style="Dark.TFrame")
        steps_row.pack(fill=tk.X, pady=2)
        ttk.Label(steps_row, text="Steps (img2img):", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        try:
            self.upscale_vars["steps"]
        except Exception:
            self.upscale_vars["steps"] = tk.IntVar(value=20)
        steps_spin = ttk.Spinbox(
            steps_row,
            from_=1,
            to=150,
            textvariable=self.upscale_vars["steps"],
            width=8,
        )
        steps_spin.pack(side=tk.LEFT, padx=(5, 0))
        self.upscale_widgets["steps"] = steps_spin

        # Denoising (for img2img mode)
        denoise_row = ttk.Frame(basic_frame, style="Dark.TFrame")
        denoise_row.pack(fill=tk.X, pady=2)
        ttk.Label(denoise_row, text="Denoising:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.upscale_vars["denoising_strength"] = tk.DoubleVar(value=0.35)
        denoise_slider = EnhancedSlider(
            denoise_row,
            from_=0.0,
            to=1.0,
            variable=self.upscale_vars["denoising_strength"],
            resolution=0.05,
            length=150,
        )
        denoise_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.upscale_widgets["denoising_strength"] = denoise_slider

        # Face Restoration
        face_frame = ttk.LabelFrame(
            scrollable_frame, text="Face Restoration", style="Dark.TFrame", padding=5
        )
        face_frame.pack(fill=tk.X, pady=2)

        # GFPGAN
        gfpgan_row = ttk.Frame(face_frame, style="Dark.TFrame")
        gfpgan_row.pack(fill=tk.X, pady=2)
        ttk.Label(gfpgan_row, text="GFPGAN:", style="Dark.TLabel", width=15).pack(side=tk.LEFT)
        self.upscale_vars["gfpgan_visibility"] = tk.DoubleVar(value=0.5)  # Default to 0.5
        gfpgan_slider = EnhancedSlider(
            gfpgan_row,
            from_=0.0,
            to=1.0,
            variable=self.upscale_vars["gfpgan_visibility"],
            resolution=0.01,
            width=120,
        )
        gfpgan_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.upscale_widgets["gfpgan_visibility"] = gfpgan_slider

        # CodeFormer
        codeformer_row = ttk.Frame(face_frame, style="Dark.TFrame")
        codeformer_row.pack(fill=tk.X, pady=2)
        ttk.Label(codeformer_row, text="CodeFormer:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.upscale_vars["codeformer_visibility"] = tk.DoubleVar(value=0.0)
        codeformer_slider = EnhancedSlider(
            codeformer_row,
            from_=0.0,
            to=1.0,
            variable=self.upscale_vars["codeformer_visibility"],
            resolution=0.05,
            length=150,
        )
        codeformer_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.upscale_widgets["codeformer_visibility"] = codeformer_slider

        # CodeFormer Weight
        cf_weight_row = ttk.Frame(face_frame, style="Dark.TFrame")
        cf_weight_row.pack(fill=tk.X, pady=2)
        ttk.Label(cf_weight_row, text="CF Fidelity:", style="Dark.TLabel", width=15).pack(
            side=tk.LEFT
        )
        self.upscale_vars["codeformer_weight"] = tk.DoubleVar(value=0.5)
        cf_weight_slider = EnhancedSlider(
            cf_weight_row,
            from_=0.0,
            to=1.0,
            variable=self.upscale_vars["codeformer_weight"],
            resolution=0.05,
            length=150,
        )
        cf_weight_slider.pack(side=tk.LEFT, padx=(5, 5))
        self.upscale_widgets["codeformer_weight"] = cf_weight_slider

        canvas.pack(fill="both", expand=True)

        # Apply initial enabled/disabled state for img2img-only controls
        try:
            self._apply_upscale_method_state()
        except Exception:
            pass

    def _apply_upscale_method_state(self) -> None:
        """Enable/disable Upscale img2img-only controls based on selected method."""
        try:
            mode = str(self.upscale_vars.get("upscale_mode").get()).lower()
        except Exception:
            mode = "single"
        use_img2img = mode == "img2img"
        # Steps (standard widget)
        steps_widget = self.upscale_widgets.get("steps")
        if steps_widget is not None:
            try:
                steps_widget.configure(state=("normal" if use_img2img else "disabled"))
            except Exception:
                pass
        # Denoising (EnhancedSlider supports .configure(state=...))
        denoise_widget = self.upscale_widgets.get("denoising_strength")
        if denoise_widget is not None:
            try:
                denoise_widget.configure(state=("normal" if use_img2img else "disabled"))
            except Exception:
                pass

    def _build_api_config_tab(self, notebook):
        """Build API configuration form"""
        tab_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(tab_frame, text="🔌 API")

        # API settings
        api_frame = ttk.LabelFrame(
            tab_frame, text="API Connection", style="Dark.TFrame", padding=10
        )
        api_frame.pack(fill=tk.X, pady=5)

        # Base URL
        url_frame = ttk.Frame(api_frame, style="Dark.TFrame")
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="Base URL:", style="Dark.TLabel").pack(side=tk.LEFT)
        self.api_vars = {}
        self.api_vars["base_url"] = self.api_url_var  # Use the same variable
        url_entry = ttk.Entry(url_frame, textvariable=self.api_vars["base_url"], width=30)
        url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Timeout
        timeout_frame = ttk.Frame(api_frame, style="Dark.TFrame")
        timeout_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timeout_frame, text="Timeout (s):", style="Dark.TLabel").pack(side=tk.LEFT)
        self.api_vars["timeout"] = tk.IntVar(value=300)
        timeout_spin = ttk.Spinbox(
            timeout_frame, from_=30, to=3600, width=10, textvariable=self.api_vars["timeout"]
        )
        timeout_spin.pack(side=tk.LEFT, padx=5)

    def _save_all_config(self):
        """Save all configuration changes"""
        try:
            # Build full config via form binder
            config = self._get_config_from_forms()

            # When packs are selected and not in override mode, persist to each selected pack
            selected = []
            if hasattr(self, "packs_listbox"):
                selected = [self.packs_listbox.get(i) for i in self.packs_listbox.curselection()]
            # Fallback: if UI focus cleared the visual selection, use last-known pack
            if (not selected) and hasattr(self, "_last_selected_pack") and self._last_selected_pack:
                selected = [self._last_selected_pack]

            if selected and not self.override_pack_var.get():
                saved_any = False
                for pack_name in selected:
                    if self.config_manager.save_pack_config(pack_name, config):
                        saved_any = True
                if saved_any:
                    self.log_message(
                        f"Saved configuration for {len(selected)} selected pack(s)", "SUCCESS"
                    )
                    self._show_config_status(
                        f"Configuration saved for {len(selected)} selected pack(s)"
                    )
                    try:
                        messagebox.showinfo(
                            "Config Saved",
                            f"Saved configuration for {len(selected)} selected pack(s)",
                        )
                    except Exception:
                        pass
                    try:
                        if hasattr(self, "config_panel"):
                            self.config_panel.show_save_indicator("Saved")
                    except Exception:
                        pass
                    try:
                        self.show_top_save_indicator("Saved")
                    except Exception:
                        pass
                else:
                    self.log_message("Failed to save configuration for selected packs", "ERROR")
            else:
                # Save as current config and optionally preset (override/preset path)
                self.current_config = config
                preset_name = tk.simpledialog.askstring(
                    "Save Preset", "Enter preset name (optional):"
                )
                if preset_name:
                    self.config_manager.save_preset(preset_name, config)
                    self.log_message(f"Saved configuration as preset: {preset_name}", "SUCCESS")
                    try:
                        messagebox.showinfo(
                            "Preset Saved",
                            f"Saved configuration as preset: {preset_name}",
                        )
                    except Exception:
                        pass
                    try:
                        if hasattr(self, "config_panel"):
                            self.config_panel.show_save_indicator("Saved")
                    except Exception:
                        pass
                    try:
                        self.show_top_save_indicator("Saved")
                    except Exception:
                        pass
                else:
                    self.log_message("Configuration updated (not saved as preset)", "INFO")
                    self._show_config_status("Configuration updated (not saved as preset)")
                    try:
                        if hasattr(self, "config_panel"):
                            self.config_panel.show_save_indicator("Saved")
                    except Exception:
                        pass
                    try:
                        self.show_top_save_indicator("Saved")
                    except Exception:
                        pass

        except Exception as e:
            self.log_message(f"Failed to save configuration: {e}", "ERROR")

    def _reset_all_config(self):
        """Reset all configuration to defaults"""
        defaults = self.config_manager.get_default_config()
        self._load_config_into_forms(defaults)
        self.log_message("Configuration reset to defaults", "INFO")

    def on_config_save(self, _config: dict) -> None:
        """Coordinator callback from ConfigPanel to save current settings."""
        try:
            self._save_all_config()
            if hasattr(self, "config_panel"):
                self.config_panel.show_save_indicator("Saved")
            self.show_top_save_indicator("Saved")
        except Exception:
            pass

    def show_top_save_indicator(self, text: str = "Saved", duration_ms: int = 2000) -> None:
        """Show a colored indicator next to the top Save button."""
        try:
            color = "#00c853" if (text or "").lower() == "saved" else "#ffa500"
            try:
                self.top_save_indicator.configure(foreground=color)
            except Exception:
                pass
            self.top_save_indicator_var.set(text)
            if duration_ms and (text or "").lower() == "saved":
                self.root.after(duration_ms, lambda: self.top_save_indicator_var.set(""))
        except Exception:
            pass

    def _on_preset_changed(self, event=None):
        """Handle preset dropdown selection changes"""
        preset_name = self.preset_var.get()
        if preset_name:
            self.log_message(f"Preset selected: {preset_name} (click Load to apply)", "INFO")

    def _on_preset_dropdown_changed(self):
        """Handle preset dropdown selection changes"""
        preset_name = self.preset_var.get()
        if not preset_name:
            return

        config = self.config_manager.load_preset(preset_name)
        if not config:
            self.log_message(f"Failed to load preset: {preset_name}", "ERROR")
            return

        self.current_preset = preset_name

        # Load the preset into the visible forms
        self._load_config_into_forms(config)

        # If override mode is enabled, this becomes the new override config
        if self.override_pack_var.get():
            self.current_config = config
            self.log_message(
                f"✓ Loaded preset '{preset_name}' (Pipeline + Randomization + General)",
                "SUCCESS",
            )
        else:
            # Not in override mode - preset loaded but not persisted until Save is clicked
            self.current_config = config
            self.log_message(
                f"✓ Loaded preset '{preset_name}' (Pipeline + Randomization + General). Click Save to apply to selected pack",
                "INFO",
            )

    def _apply_default_to_selected_packs(self):
        """Apply the default preset to currently selected pack(s)"""
        default_config = self.config_manager.load_preset("default")
        if not default_config:
            self.log_message("Failed to load default preset", "ERROR")
            return

        # Load into forms
        self._load_config_into_forms(default_config)
        self.current_config = default_config
        self.preset_var.set("default")
        self.current_preset = "default"

        self.log_message("✓ Loaded default preset (click Save to apply to selected pack)", "SUCCESS")

    def _save_config_to_packs(self):
        """Save current configuration to selected pack(s)"""
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            self.log_message("No packs selected", "WARNING")
            return

        selected_packs = [self.packs_listbox.get(i) for i in selected_indices]
        current_config = self._get_config_from_forms()

        saved_count = 0
        for pack_name in selected_packs:
            if self.config_manager.save_pack_config(pack_name, current_config):
                saved_count += 1

        if saved_count > 0:
            if len(selected_packs) == 1:
                self.log_message(f"✓ Saved config to pack: {selected_packs[0]}", "SUCCESS")
            else:
                self.log_message(f"✓ Saved config to {saved_count}/{len(selected_packs)} pack(s)", "SUCCESS")
        else:
            self.log_message("Failed to save config to packs", "ERROR")

    def _load_selected_preset(self):
        """Load the currently selected preset into the form"""
        preset_name = self.preset_var.get()
        if not preset_name:
            self.log_message("No preset selected", "WARNING")
            return

        config = self.config_manager.load_preset(preset_name)
        if config:
            self.current_preset = preset_name
            if not self.override_pack_var.get():
                self._load_config_into_forms(config)
            self.current_config = config
            self.log_message(f"✓ Loaded preset: {preset_name}", "SUCCESS")
            self._refresh_config()
            # Refresh pack list asynchronously to reflect any changes
            try:
                self._refresh_prompt_packs_async()
            except Exception:
                pass
        else:
            self.log_message(f"Failed to load preset: {preset_name}", "ERROR")

    def _save_preset_as(self):
        """Save current configuration as a new preset with user-provided name"""
        from tkinter import simpledialog

        current_config = self._get_config_from_forms()

        preset_name = simpledialog.askstring(
            "Save Preset As",
            "Enter a name for the new preset:",
            initialvalue="",
        )

        if not preset_name:
            return

        # Clean up the name
        preset_name = preset_name.strip()
        if not preset_name:
            self.log_message("Preset name cannot be empty", "WARNING")
            return

        # Check if preset already exists
        if preset_name in self.config_manager.list_presets():
            from tkinter import messagebox

            overwrite = messagebox.askyesno(
                "Preset Exists",
                f"Preset '{preset_name}' already exists. Overwrite it?",
            )
            if not overwrite:
                return

        if self.config_manager.save_preset(preset_name, current_config):
            self.log_message(f"✓ Saved preset as: {preset_name}", "SUCCESS")
            # Refresh dropdown
            self.preset_dropdown["values"] = self.config_manager.list_presets()
            # Select the new preset
            self.preset_var.set(preset_name)
            self.current_preset = preset_name
        else:
            self.log_message(f"Failed to save preset: {preset_name}", "ERROR")

    def _delete_selected_preset(self):
        """Delete the currently selected preset after confirmation"""
        from tkinter import messagebox

        preset_name = self.preset_var.get()
        if not preset_name:
            self.log_message("No preset selected", "WARNING")
            return

        if preset_name == "default":
            messagebox.showwarning(
                "Cannot Delete Default",
                "The 'default' preset is protected and cannot be deleted.\n\nYou can overwrite it with different settings, but it cannot be removed."
            )
            return

        confirm = messagebox.askyesno(
            "Delete Preset",
            f"Are you sure you want to delete the '{preset_name}' preset forever?",
        )

        if not confirm:
            return

        if self.config_manager.delete_preset(preset_name):
            self.log_message(f"✓ Deleted preset: {preset_name}", "SUCCESS")
            # Refresh dropdown
            self.preset_dropdown["values"] = self.config_manager.list_presets()
            # Select default
            self.preset_var.set("default")
            self.current_preset = "default"
            # Load default into forms
            self._on_preset_dropdown_changed()
        else:
            self.log_message(f"Failed to delete preset: {preset_name}", "ERROR")

    def _set_as_default_preset(self):
        """Mark the currently selected preset as the default (auto-loads on startup)"""
        from tkinter import messagebox

        preset_name = self.preset_var.get()
        if not preset_name:
            self.log_message("No preset selected", "WARNING")
            return

        # Check if there's already a default
        current_default = self.config_manager.get_default_preset()
        if current_default == preset_name:
            messagebox.showinfo(
                "Already Default",
                f"'{preset_name}' is already marked as the default preset.",
            )
            return

        if self.config_manager.set_default_preset(preset_name):
            self.log_message(f"⭐ Marked '{preset_name}' as default preset", "SUCCESS")
            messagebox.showinfo(
                "Default Preset Set",
                f"'{preset_name}' will now auto-load when the application starts.",
            )
        else:
            self.log_message(f"Failed to set default preset: {preset_name}", "ERROR")

    def _save_override_preset(self):
        """Save current configuration as the override preset (updates selected preset)"""
        current_config = self._get_config_from_forms()
        preset_name = self.preset_var.get()

        if not preset_name:
            self.log_message("No preset selected to update", "WARNING")
            return

        if self.config_manager.save_preset(preset_name, current_config):
            self.log_message(f"✓ Updated preset: {preset_name}", "SUCCESS")
        else:
            self.log_message(f"Failed to update preset: {preset_name}", "ERROR")

    def _on_override_changed(self):
        """Handle override checkbox changes"""
        # Refresh configuration display based on new override state
        self._refresh_config()

        if self.override_pack_var.get():
            self.log_message(
                "📝 Override mode enabled - current config will apply to all selected packs", "INFO"
            )
        else:
            self.log_message(
                "📝 Override mode disabled - packs will use individual configs", "INFO"
            )

    def _preserve_pack_selection(self):
        """Preserve pack selection when config changes"""
        if hasattr(self, "_last_selected_pack") and self._last_selected_pack:
            # Find and reselect the last selected pack
            current_selection = self.packs_listbox.curselection()
            if not current_selection:  # Only restore if nothing is selected
                for i in range(self.packs_listbox.size()):
                    if self.packs_listbox.get(i) == self._last_selected_pack:
                        self.packs_listbox.selection_set(i)
                        self.packs_listbox.activate(i)
                        # Pack selection restored silently - no need to log every restore
                        break

    def _load_config_into_forms(self, config):
        """Load configuration values into form widgets"""
        if getattr(self, "_diag_enabled", False):
            logger.info("[DIAG] _load_config_into_forms: start", extra={"flush": True})
        # Preserve current pack selection before updating forms
        current_selection = self.packs_listbox.curselection()
        selected_pack = None
        if current_selection:
            selected_pack = self.packs_listbox.get(current_selection[0])

        try:
            if hasattr(self, "config_panel"):
                if getattr(self, "_diag_enabled", False):
                    logger.info("[DIAG] _load_config_into_forms: calling config_panel.set_config", extra={"flush": True})
                self.config_panel.set_config(config)
                if getattr(self, "_diag_enabled", False):
                    logger.info("[DIAG] _load_config_into_forms: config_panel.set_config returned", extra={"flush": True})
            if hasattr(self, "adetailer_panel") and self.adetailer_panel:
                if getattr(self, "_diag_enabled", False):
                    logger.info("[DIAG] _load_config_into_forms: calling adetailer_panel.set_config", extra={"flush": True})
                self.adetailer_panel.set_config(config.get("adetailer", {}))
            if getattr(self, "_diag_enabled", False):
                logger.info("[DIAG] _load_config_into_forms: calling _load_randomization_config", extra={"flush": True})
            self._load_randomization_config(config)
            if getattr(self, "_diag_enabled", False):
                logger.info("[DIAG] _load_config_into_forms: calling _load_aesthetic_config", extra={"flush": True})
            self._load_aesthetic_config(config)
        except Exception as e:
            self.log_message(f"Error loading config into forms: {e}", "ERROR")
            if getattr(self, "_diag_enabled", False):
                logger.error(f"[DIAG] _load_config_into_forms: exception {e}", exc_info=True, extra={"flush": True})

        # Restore pack selection if it was lost during form updates
        if selected_pack and not self.packs_listbox.curselection():
            if getattr(self, "_diag_enabled", False):
                logger.info("[DIAG] _load_config_into_forms: restoring pack selection", extra={"flush": True})
            for i in range(self.packs_listbox.size()):
                if self.packs_listbox.get(i) == selected_pack:
                    # Use unwrapped selection_set to avoid triggering callback recursively
                    if hasattr(self.prompt_pack_panel, '_orig_selection_set'):
                        self.prompt_pack_panel._orig_selection_set(i)
                    else:
                        self.packs_listbox.selection_set(i)
                    self.packs_listbox.activate(i)
                    break
        if getattr(self, "_diag_enabled", False):
            logger.info("[DIAG] _load_config_into_forms: end", extra={"flush": True})

    def _apply_saved_preferences(self):
        """Apply persisted preferences to the current UI session."""

        prefs = getattr(self, "preferences", None)
        if not prefs:
            return

        try:
            # Restore preset selection and override mode
            self.current_preset = prefs.get("preset", "default")
            if hasattr(self, "preset_var"):
                self.preset_var.set(self.current_preset)
            if hasattr(self, "override_pack_var"):
                self.override_pack_var.set(prefs.get("override_pack", False))

            # Restore pipeline control toggles
            pipeline_state = prefs.get("pipeline_controls")
            if pipeline_state and hasattr(self, "pipeline_controls_panel"):
                try:
                    self.pipeline_controls_panel.set_state(pipeline_state)
                except Exception as exc:
                    logger.warning(f"Failed to restore pipeline preferences: {exc}")

            # Restore pack selections
            selected_packs = prefs.get("selected_packs", [])
            if selected_packs and hasattr(self, "packs_listbox"):
                self.packs_listbox.selection_clear(0, tk.END)
                for pack_name in selected_packs:
                    for index in range(self.packs_listbox.size()):
                        if self.packs_listbox.get(index) == pack_name:
                            self.packs_listbox.selection_set(index)
                            self.packs_listbox.activate(index)
                self._update_selection_highlights()
                self.selected_packs = selected_packs
                if selected_packs:
                    self._last_selected_pack = selected_packs[0]

            # Restore configuration values into forms
            config = prefs.get("config")
            if config:
                self._load_config_into_forms(config)
                self.current_config = config
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning(f"Failed to apply saved preferences: {exc}")

    def _collect_preferences(self) -> dict[str, Any]:
        """Collect current UI preferences for persistence."""

        preferences = {
            "preset": self.preset_var.get() if hasattr(self, "preset_var") else "default",
            "selected_packs": [],
            "override_pack": (
                bool(self.override_pack_var.get()) if hasattr(self, "override_pack_var") else False
            ),
            "pipeline_controls": self.preferences_manager.default_pipeline_controls(),
            "config": self._get_config_from_forms(),
        }

        if hasattr(self, "packs_listbox"):
            preferences["selected_packs"] = [
                self.packs_listbox.get(i) for i in self.packs_listbox.curselection()
            ]

        if hasattr(self, "pipeline_controls_panel") and self.pipeline_controls_panel is not None:
            try:
                preferences["pipeline_controls"] = self.pipeline_controls_panel.get_state()
            except Exception as exc:  # pragma: no cover - defensive logging path
                logger.warning(f"Failed to capture pipeline controls state: {exc}")

        return preferences

    def _build_pipeline_tab(self, parent):
        """Build pipeline execution tab"""
        # API Connection Frame
        api_frame = ttk.LabelFrame(parent, text="API Connection", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(api_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(api_frame, textvariable=self.api_url_var, width=40).grid(
            row=0, column=1, padx=5, pady=2
        )

        self.check_api_btn = ttk.Button(api_frame, text="Check API", command=self._check_api)
        self.check_api_btn.grid(row=0, column=2, padx=5)

        self.api_status_label = ttk.Label(api_frame, text="Not connected", foreground="red")
        self.api_status_label.grid(row=0, column=3, padx=5)

        # Prompt Frame
        prompt_frame = ttk.LabelFrame(parent, text="Prompt", padding=10)
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Label(prompt_frame, text="Enter your prompt:").pack(anchor=tk.W)
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=6, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.prompt_text.insert(1.0, "a beautiful landscape, high quality, detailed")

        # Preset Frame
        preset_frame = ttk.LabelFrame(parent, text="Preset", padding=10)
        preset_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(preset_frame, text="Select preset:").grid(row=0, column=0, padx=5)
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            preset_frame, textvariable=self.preset_var, state="readonly", width=20
        )
        self.preset_combo.grid(row=0, column=1, padx=5)
        self._refresh_presets()

        ttk.Button(preset_frame, text="Refresh", command=self._refresh_presets).grid(
            row=0, column=2, padx=5
        )

        # Options Frame
        options_frame = ttk.LabelFrame(parent, text="Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(options_frame, text="Batch size:").grid(row=0, column=0, padx=5)
        self.batch_size_var = tk.IntVar(value=1)
        ttk.Spinbox(options_frame, from_=1, to=10, textvariable=self.batch_size_var, width=10).grid(
            row=0, column=1, padx=5
        )

        ttk.Label(options_frame, text="Run name (optional):").grid(row=0, column=2, padx=5)
        self.run_name_var = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.run_name_var, width=20).grid(
            row=0, column=3, padx=5
        )

        # Pipeline stages
        self.enable_img2img_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Enable img2img cleanup", variable=self.enable_img2img_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        self.enable_upscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Enable upscaling", variable=self.enable_upscale_var
        ).grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5, pady=2)

        # Execution Frame
        exec_frame = ttk.Frame(parent, padding=10)
        exec_frame.pack(fill=tk.X, padx=10, pady=5)

        self.run_pipeline_btn = ttk.Button(
            exec_frame, text="Run Pipeline", command=self._run_pipeline, style="Accent.TButton"
        )
        self.run_pipeline_btn.pack(side=tk.LEFT, padx=5)

        self.create_video_btn = ttk.Button(
            exec_frame, text="Create Video from Output", command=self._create_video
        )
        self.create_video_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(exec_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=10)

        progress_frame = ttk.Frame(parent, padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
            length=200,
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress_bar["value"] = 0

        ttk.Label(progress_frame, textvariable=self.progress_percent_var, style="Dark.TLabel").pack(
            side=tk.LEFT, padx=8
        )
        ttk.Label(progress_frame, textvariable=self.eta_var, style="Dark.TLabel").pack(
            side=tk.LEFT, padx=8
        )

    def _build_settings_tab(self, parent):
        """Build settings tab"""
        settings_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Show current preset
        presets = self.config_manager.list_presets()
        settings_text.insert(1.0, "Available Presets:")
        for preset in presets:
            settings_text.insert(tk.END, f"- {preset}")

        settings_text.insert(tk.END, "Default Configuration:")
        default_config = self.config_manager.get_default_config()
        settings_text.insert(tk.END, json.dumps(default_config, indent=2))

        settings_text.config(state=tk.DISABLED)

    def _build_log_tab(self, parent):
        """Build log tab"""
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add a handler to redirect logs to the text widget
        # This is a simple implementation - could be enhanced
        self._add_log_message("Log viewer initialized")

    def _add_log_message(self, message: str):
        """Add message to log viewer"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _refresh_presets(self):
        """Refresh preset list"""
        presets = self.config_manager.list_presets()
        self.preset_combo["values"] = presets
        if presets and not self.preset_var.get():
            self.preset_var.set(presets[0])

    def _check_api(self):
        """Check API connection"""
        self._apply_status_text("Checking API...")
        self._add_log_message("Checking SD WebUI API connection...")

        def check():
            url = self.api_url_var.get()
            client = SDWebUIClient(base_url=url)
            if client.check_api_ready():
                self.client = client
                self.pipeline = Pipeline(self.client, self.structured_logger)
                self.controller.set_pipeline(self.pipeline)
                self.root.after(
                    0, lambda: self.api_status_label.config(text="Connected", foreground="green")
                )
                self.root.after(0, lambda: self._add_log_message("✓ API is ready"))
                self.root.after(0, lambda: self._apply_status_text("API connected"))
            else:
                self.root.after(
                    0, lambda: self.api_status_label.config(text="Failed", foreground="red")
                )
                self.root.after(0, lambda: self._add_log_message("✗ API not available"))
                self.root.after(0, lambda: self._apply_status_text("API check failed"))

        threading.Thread(target=check, daemon=True).start()

    def _run_pipeline(self):
        """Run the full pipeline using controller"""
        if not self.client or not self.pipeline:
            messagebox.showerror("Error", "Please check API connection first")
            return

        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt")
            return

        # Get configuration from GUI forms (current user settings)
        config = self._get_config_from_forms()
        if not config:
            messagebox.showerror("Error", "Failed to read configuration from forms")
            return

        # Modify config based on options
        if not self.enable_img2img_var.get():
            config.pop("img2img", None)
        if not self.enable_upscale_var.get():
            config.pop("upscale", None)

        batch_size = self.batch_size_var.get()
        run_name = self.run_name_var.get() or None

        self.controller.report_progress("Running pipeline...", 0.0, "ETA: --")

        # Define pipeline function that checks cancel token
        # Snapshot Tk-backed values on the main thread (thread-safe)
        try:
            config_snapshot = self._get_config_from_forms()
        except Exception:
            config_snapshot = {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}
        try:
            batch_size_snapshot = int(self.images_per_prompt_var.get())
        except Exception:
            batch_size_snapshot = 1
        def pipeline_func():
            try:
                # Pass cancel_token to pipeline
                results = self.pipeline.run_full_pipeline(
                    prompt, config, run_name, batch_size, cancel_token=self.controller.cancel_token
                )
                return results
            except CancellationError:
                # Signal completion and prefer Ready status after cancellation
                try:
                    self.controller.lifecycle_event.set()
                except Exception:
                    pass
                try:
                    self._force_error_status = False
                    if hasattr(self, "progress_message_var"):
                        # Schedule on Tk to mirror normal status handling
                        self.root.after(0, lambda: self.progress_message_var.set("Ready"))
                except Exception:
                    pass
                raise
            except Exception:
                logger.exception("Pipeline execution error")
                # Build error text up-front
                try:
                    import sys

                    ex_type, ex, _ = sys.exc_info()
                    err_text = (
                        f"Pipeline failed: {ex_type.__name__}: {ex}"
                        if (ex_type and ex)
                        else "Pipeline failed"
                    )
                except Exception:
                    err_text = "Pipeline failed"

                # Log friendly error line to app log first (test captures this)
                try:
                    self.log_message(f"? {err_text}", "ERROR")
                except Exception:
                    pass

                # Marshal error dialog to Tk thread (or bypass if env says so)
                def _show_err():
                    try:
                        import os
                        if os.environ.get("STABLENEW_NO_ERROR_DIALOG") in {"1","true","TRUE"}:
                            return
                        if not getattr(self, "_error_dialog_shown", False):
                            messagebox.showerror("Pipeline Error", err_text)
                            self._error_dialog_shown = True
                    except Exception:
                        logger.exception("Unable to display error dialog")
                try:
                    self.root.after(0, _show_err)
                except Exception:
                    # Fallback for test harnesses without a real root loop
                    _show_err()

                # Ensure tests waiting on lifecycle_event are not blocked
                try:
                    self.controller.lifecycle_event.set()
                except Exception:
                    pass

                # Force visible error state/status
                self._force_error_status = True
                try:
                    if hasattr(self, "progress_message_var"):
                        self.progress_message_var.set("Error")
                except Exception:
                    pass
                try:
                    from .state import GUIState

                    # Schedule transition on Tk thread for deterministic callback behavior
                    self.root.after(0, lambda: self.state_manager.transition_to(GUIState.ERROR))
                except Exception:
                    pass

                # (Already logged above)
                raise

        # Completion callback
        def on_complete(results):
            output_dir = results.get("run_dir", "Unknown")
            num_images = len(results.get("summary", []))

            self.root.after(
                0,
                lambda: self.log_message(
                    f"✓ Pipeline completed: {num_images} images generated", "SUCCESS"
                ),
            )
            self.root.after(0, lambda: self.log_message(f"Output directory: {output_dir}", "INFO"))
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Success",
                    f"Pipeline completed!{num_images} images generatedOutput: {output_dir}",
                ),
            )
            # Reset error-control flags for the next run
            try:
                self._force_error_status = False
                self._error_dialog_shown = False
            except Exception:
                pass
            # Ensure lifecycle_event is signaled for tests waiting on completion
            try:
                self.controller.lifecycle_event.set()
            except Exception:
                pass

        # Error callback
        def on_error(e):
            # Log and alert immediately (safe for tests with mocked messagebox)
            try:
                err_text = f"Pipeline failed: {type(e).__name__}: {e}"
                self.log_message(f"? {err_text}", "ERROR")
                try:
                    if hasattr(self, "progress_message_var"):
                        self.progress_message_var.set("Error")
                except Exception:
                    pass
                try:
                    if not getattr(self, "_error_dialog_shown", False):
                        messagebox.showerror("Pipeline Error", err_text)
                        self._error_dialog_shown = True
                except Exception:
                    pass
                try:
                    # Also schedule to ensure it wins over any queued 'Running' updates
                    self.root.after(
                        0,
                        lambda: hasattr(self, "progress_message_var")
                        and self.progress_message_var.set("Error"),
                    )
                    # Schedule explicit ERROR transition to drive status callbacks
                    from .state import GUIState

                    self.root.after(0, lambda: self.state_manager.transition_to(GUIState.ERROR))
                except Exception:
                    pass
            except Exception:
                pass
            # Also schedule the standard UI error handler
            def _show_err():
                import os
                if os.environ.get("STABLENEW_NO_ERROR_DIALOG") in {"1","true","TRUE"}:
                    return
                try:
                    if not getattr(self, "_error_dialog_shown", False):
                        messagebox.showerror("Pipeline Error", str(e))
                        self._error_dialog_shown = True
                except Exception:
                    logger.exception("Unable to display error dialog")
            try:
                self.root.after(0, _show_err)
            except Exception:
                _show_err()
            # Ensure lifecycle_event is signaled promptly on error
            try:
                self.controller.lifecycle_event.set()
            except Exception:
                pass

        # Start pipeline using controller
        self.controller.start_pipeline(pipeline_func, on_complete=on_complete, on_error=on_error)

    def _handle_pipeline_error(self, error: Exception) -> None:
        """Log and surface pipeline errors to the user.

        This method may be called from a worker thread, so GUI operations
        must be marshaled to the main thread using root.after().
        """

        error_message = f"Pipeline failed: {type(error).__name__}: {error}\nA fatal error occurred. Please restart StableNew to continue."
        self.log_message(f"✗ {error_message}", "ERROR")

        # Marshal messagebox to main thread to avoid Tkinter threading violations
        def show_error_dialog():
            try:
                if not getattr(self, "_error_dialog_shown", False):
                    messagebox.showerror("Pipeline Error", error_message)
                    self._error_dialog_shown = True
            except tk.TclError:
                logger.error("Unable to display error dialog", exc_info=True)

        import os
        import sys
        import threading
        def exit_app():
            try:
                self.root.destroy()
            except Exception:
                pass
            try:
                sys.exit(1)
            except SystemExit:
                pass
        def force_exit_thread():
            import time
            time.sleep(1)
            os._exit(1)
        threading.Thread(target=force_exit_thread, daemon=True).start()

        try:
            self.root.after(0, show_error_dialog)
            self.root.after(100, exit_app)
        except Exception:
            show_error_dialog()
            exit_app()
        # Progress message update is handled by state transition callback; redundant here.

    def _create_video(self):
        """Create video from output images"""
        # Ask user to select output directory
        output_dir = filedialog.askdirectory(title="Select output directory containing images")

        if not output_dir:
            return

        output_path = Path(output_dir)

        # Try to find upscaled images first, then img2img, then txt2img
        for subdir in ["upscaled", "img2img", "txt2img"]:
            image_dir = output_path / subdir
            if image_dir.exists():
                video_path = output_path / "video" / f"{subdir}_video.mp4"
                video_path.parent.mkdir(exist_ok=True)

                self._add_log_message(f"Creating video from {subdir}...")

                if self.video_creator.create_video_from_directory(image_dir, video_path):
                    self._add_log_message(f"✓ Video created: {video_path}")
                    messagebox.showinfo("Success", f"Video created:{video_path}")
                else:
                    self._add_log_message(f"✗ Failed to create video from {subdir}")

                return

        messagebox.showerror("Error", "No image directories found")

    def _refresh_models(self):
        """Refresh the list of available SD models (main thread version)"""
        if self.client is None:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            models = self.client.get_models()
            model_names = [""] + [
                model.get("title", model.get("model_name", "")) for model in models
            ]

            if hasattr(self, "config_panel"):
                self.config_panel.set_model_options(model_names)

            self.log_message(f"🔄 Loaded {len(models)} SD models")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh models: {e}")

    def _refresh_models_async(self):
        """Refresh the list of available SD models (thread-safe version)"""
        from functools import partial

        if self.client is None:
            # Schedule error message on main thread
            self.root.after(0, lambda: messagebox.showerror("Error", "API client not connected"))
            return

        try:
            # Perform API call in worker thread
            models = self.client.get_models()
            model_names = [""] + [
                model.get("title", model.get("model_name", "")) for model in models
            ]

            # Marshal widget updates back to main thread
            def update_widgets():
                if hasattr(self, "model_combo"):
                    self.model_combo["values"] = tuple(model_names)
                if hasattr(self, "img2img_model_combo"):
                    self.img2img_model_combo["values"] = tuple(model_names)
                self._add_log_message(f"🔄 Loaded {len(models)} SD models")

            self.root.after(0, update_widgets)

            # Also update unified ConfigPanel if present using partial to capture value
            if hasattr(self, "config_panel"):
                self.root.after(0, partial(self.config_panel.set_model_options, list(model_names)))

        except Exception as exc:
            # Marshal error message back to main thread
            # Capture exception in default argument to avoid closure issues
            self.root.after(
                0,
                lambda err=exc: messagebox.showerror("Error", f"Failed to refresh models: {err}"),
            )

    def _refresh_hypernetworks_async(self):
        """Refresh available hypernetworks (thread-safe)."""

        if self.client is None:
            self.root.after(
                0, lambda: messagebox.showerror("Error", "API client not connected")
            )
            return

        def worker():
            try:
                entries = self.client.get_hypernetworks()
                names = ["None"]
                for entry in entries:
                    name = ""
                    if isinstance(entry, dict):
                        name = entry.get("name") or entry.get("title") or ""
                    else:
                        name = str(entry)
                    name = name.strip()
                    if name and name not in names:
                        names.append(name)

                self.available_hypernetworks = names

                def update_widgets():
                    if hasattr(self, "config_panel"):
                        try:
                            self.config_panel.set_hypernetwork_options(names)
                        except Exception:
                            pass

                self.root.after(0, update_widgets)
                self._add_log_message(f"🔄 Loaded {len(names) - 1} hypernetwork(s)")
            except Exception as exc:  # pragma: no cover - Tk loop dispatch
                self.root.after(
                    0,
                    lambda err=exc: messagebox.showerror(
                        "Error", f"Failed to refresh hypernetworks: {err}"
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_vae_models(self):
        """Refresh the list of available VAE models (main thread version)"""
        if self.client is None:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            vae_models = self.client.get_vae_models()
            vae_names = [""] + [vae.get("model_name", "") for vae in vae_models]

            if hasattr(self, "config_panel"):
                self.config_panel.set_vae_options(vae_names)

            self.log_message(f"🔄 Loaded {len(vae_models)} VAE models")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh VAE models: {e}")

    def _refresh_vae_models_async(self):
        """Refresh the list of available VAE models (thread-safe version)"""
        from functools import partial

        if self.client is None:
            # Schedule error message on main thread
            self.root.after(0, lambda: messagebox.showerror("Error", "API client not connected"))
            return

        try:
            # Perform API call in worker thread
            vae_models = self.client.get_vae_models()
            vae_names_local = [""] + [vae.get("model_name", "") for vae in vae_models]

            # Store in instance attribute
            self.vae_names = list(vae_names_local)

            # Marshal widget updates back to main thread
            def update_widgets():
                if hasattr(self, "vae_combo"):
                    self.vae_combo["values"] = tuple(self.vae_names)
                if hasattr(self, "img2img_vae_combo"):
                    self.img2img_vae_combo["values"] = tuple(self.vae_names)
                self._add_log_message(f"🔄 Loaded {len(vae_models)} VAE models")

            self.root.after(0, update_widgets)

            # Also update config panel if present using partial to capture value
            if hasattr(self, "config_panel"):
                self.root.after(0, partial(self.config_panel.set_vae_options, list(self.vae_names)))

        except Exception as exc:
            # Marshal error message back to main thread
            # Capture exception in default argument to avoid closure issues
            self.root.after(
                0,
                lambda err=exc: messagebox.showerror(
                    "Error", f"Failed to refresh VAE models: {err}"
                ),
            )

    def _refresh_upscalers(self):
        """Refresh the list of available upscalers (main thread version)"""
        if self.client is None:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            upscalers = self.client.get_upscalers()
            upscaler_names = [
                upscaler.get("name", "") for upscaler in upscalers if upscaler.get("name")
            ]

            if hasattr(self, "config_panel"):
                self.config_panel.set_upscaler_options(upscaler_names)

            self.log_message(f"🔄 Loaded {len(upscalers)} upscalers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh upscalers: {e}")

    def _refresh_upscalers_async(self):
        """Refresh the list of available upscalers (thread-safe version)"""
        from functools import partial

        if self.client is None:
            # Schedule error message on main thread
            self.root.after(0, lambda: messagebox.showerror("Error", "API client not connected"))
            return

        try:
            # Perform API call in worker thread
            upscalers = self.client.get_upscalers()
            upscaler_names_local = [
                upscaler.get("name", "") for upscaler in upscalers if upscaler.get("name")
            ]

            # Store in instance attribute
            self.upscaler_names = list(upscaler_names_local)

            # Marshal widget updates back to main thread
            def update_widgets():
                if hasattr(self, "upscaler_combo"):
                    self.upscaler_combo["values"] = tuple(self.upscaler_names)
                self._add_log_message(f"🔄 Loaded {len(upscalers)} upscalers")

            self.root.after(0, update_widgets)

            # Also update config panel if present using partial to capture value
            if hasattr(self, "config_panel"):
                self.root.after(
                    0, partial(self.config_panel.set_upscaler_options, list(self.upscaler_names))
                )

        except Exception as exc:
            # Marshal error message back to main thread
            # Capture exception in default argument to avoid closure issues
            self.root.after(
                0,
                lambda err=exc: messagebox.showerror(
                    "Error", f"Failed to refresh upscalers: {err}"
                ),
            )

    def _refresh_schedulers(self):
        """Refresh the list of available schedulers (main thread version)"""
        if not self.client:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            schedulers = self.client.get_schedulers()

            if hasattr(self, "config_panel"):
                self.config_panel.set_scheduler_options(schedulers)

            self.log_message(f"🔄 Loaded {len(schedulers)} schedulers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh schedulers: {e}")

    def _refresh_schedulers_async(self):
        """Refresh the list of available schedulers (thread-safe version)"""
        from functools import partial

        if not self.client:
            # Schedule error message on main thread
            self.root.after(0, lambda: messagebox.showerror("Error", "API client not connected"))
            return

        try:
            # Perform API call in worker thread
            schedulers = self.client.get_schedulers()

            # Store in instance attribute
            self.schedulers = list(schedulers)

            # Marshal widget updates back to main thread using partial
            def update_widgets():
                if hasattr(self, "scheduler_combo"):
                    self.scheduler_combo["values"] = tuple(self.schedulers)
                if hasattr(self, "img2img_scheduler_combo"):
                    self.img2img_scheduler_combo["values"] = tuple(self.schedulers)
                self._add_log_message(f"🔄 Loaded {len(self.schedulers)} schedulers")

            self.root.after(0, update_widgets)

            # Also update config panel if present using partial to capture value
            if hasattr(self, "config_panel"):
                self.root.after(
                    0, partial(self.config_panel.set_scheduler_options, list(self.schedulers))
                )

        except Exception as exc:
            # Marshal error message back to main thread
            # Capture exception in default argument to avoid closure issues
            self.root.after(
                0,
                lambda err=exc: messagebox.showerror(
                    "Error", f"Failed to refresh schedulers: {err}"
                ),
            )

    def _on_hires_toggle(self):
        """Handle hires.fix enable/disable toggle"""
        # This method can be used to enable/disable hires.fix related controls
        # For now, just log the change
        enabled = self.txt2img_vars.get("enable_hr", tk.BooleanVar()).get()
        self.log_message(f"📏 Hires.fix {'enabled' if enabled else 'disabled'}")

    def _randomize_seed(self, var_dict_name):
        """Generate a random seed for the specified variable dictionary"""
        import random

        random_seed = random.randint(1, 2147483647)  # Max int32 value
        var_dict = getattr(self, f"{var_dict_name}_vars", {})
        if "seed" in var_dict:
            var_dict["seed"].set(random_seed)
            self.log_message(f"🎲 Random seed generated: {random_seed}")

    def _randomize_txt2img_seed(self):
        """Generate random seed for txt2img"""
        self._randomize_seed("txt2img")

    def _randomize_img2img_seed(self):
        """Generate random seed for img2img"""
        self._randomize_seed("img2img")




