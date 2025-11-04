"""Modern Tkinter GUI for Stable Diffusion pipeline with dark theme"""

import json
import logging
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.simpledialog
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from ..api import SDWebUIClient
from ..pipeline import Pipeline, VideoCreator
from ..utils import ConfigManager, StructuredLogger, setup_logging
from ..utils.file_io import read_prompt_pack
from ..utils.webui_discovery import find_webui_api_port, launch_webui_safely, validate_webui_health
from .advanced_prompt_editor import AdvancedPromptEditor
from .controller import PipelineController
from .enhanced_slider import EnhancedSlider
from .pipeline_controls_panel import PipelineControlsPanel
from .prompt_pack_list_manager import PromptPackListManager
from .prompt_pack_panel import PromptPackPanel
from .state import GUIState, StateManager

logger = logging.getLogger(__name__)


class StableNewGUI:
    """Main GUI application with modern dark theme"""

    def __init__(self):
        """Initialize GUI"""
        self.root = tk.Tk()
        self.root.title("StableNew - Stable Diffusion WebUI Automation")
        self.root.geometry("1200x800+100+50")  # Added positioning to ensure it appears on screen
        self.root.configure(bg="#2b2b2b")

        # Ensure window is visible and on top
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(lambda: self.root.attributes("-topmost", False))

        # Prevent window from being minimized or hidden
        self.root.state("normal")

        # Initialize components
        self.config_manager = ConfigManager()
        self.structured_logger = StructuredLogger()
        self.client = None
        self.pipeline = None
        self.video_creator = VideoCreator()

        # Initialize state management and controller
        self.state_manager = StateManager()
        self.controller = PipelineController(self.state_manager)

        # Initialize prompt pack list manager
        self.pack_list_manager = PromptPackListManager()

        # GUI state
        self.selected_packs = []
        self.current_config = None
        self.api_connected = False
        self._last_selected_pack = None
        self.current_preset = "default"
        self._refreshing_config = False  # Flag to prevent recursive refreshes

        # Initialize GUI variables early
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:7860")
        self.preset_var = tk.StringVar(value="default")

        # Initialize other GUI variables that are used before UI building
        self.txt2img_enabled = tk.BooleanVar(value=True)
        self.img2img_enabled = tk.BooleanVar(value=True)
        self.upscale_enabled = tk.BooleanVar(value=True)
        self.video_enabled = tk.BooleanVar(value=False)
        self.loop_type_var = tk.StringVar(value="single")
        self.loop_count_var = tk.StringVar(value="1")
        self.pack_mode_var = tk.StringVar(value="selected")
        self.images_per_prompt_var = tk.StringVar(value="1")

        # Apply dark theme
        self._setup_dark_theme()

        # Load or create default preset
        self._ensure_default_preset()

        # Auto-launch WebUI
        self._launch_webui()

        # Build UI
        self._build_ui()

        # Setup logging redirect
        setup_logging("INFO")

    def _setup_dark_theme(self):
        """Setup dark theme for the application"""
        style = ttk.Style()

        # Configure dark theme colors
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        select_bg = "#404040"
        select_fg = "#ffffff"
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
        """Auto-launch Stable Diffusion WebUI with improved detection"""
        webui_path = Path("C:/Users/rober/stable-diffusion-webui/webui-user.bat")

        # First check if WebUI is already running
        existing_url = find_webui_api_port()
        if existing_url:
            logger.info(f"WebUI already running at {existing_url}")
            self.api_url_var.set(existing_url)
            self.root.after(2000, self._check_api_connection)
            return

        # Try to launch WebUI
        if webui_path.exists():
            self.log_message("🚀 Launching Stable Diffusion WebUI...", "INFO")

            # Launch in separate thread to avoid blocking UI
            def launch_thread():
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
                            lambda: self.log_message(
                                "⚠️ WebUI launched but API not found", "WARNING"
                            ),
                        )
                else:
                    self.root.after(0, lambda: self.log_message("❌ WebUI launch failed", "ERROR"))

            threading.Thread(target=launch_thread, daemon=True).start()
        else:
            logger.warning("WebUI not found at expected location")
            self.log_message("⚠️ WebUI not found - please start manually", "WARNING")
            messagebox.showinfo(
                "WebUI Not Found",
                f"WebUI not found at: {webui_path}\n\n"
                "Please start Stable Diffusion WebUI manually\n"
                "with --api flag and click 'Check API'",
            )

    def _ensure_default_preset(self):
        """Ensure default preset exists"""
        if "default" not in self.config_manager.list_presets():
            default_config = self.config_manager.get_default_config()
            self.config_manager.save_preset("default", default_config)

    def _build_ui(self):
        """Build the modern user interface"""
        # Create main container with minimal padding for space efficiency
        main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Compact top frame for API status
        self._build_api_status_frame(main_frame)

        # Main content frame - optimized layout
        content_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Configure grid for better space utilization
        content_frame.columnconfigure(0, weight=0, minsize=200)  # Left: compact packs
        content_frame.columnconfigure(1, weight=1)  # Center: flexible config
        content_frame.columnconfigure(2, weight=0, minsize=250)  # Right: pipeline controls
        content_frame.rowconfigure(0, weight=1)

        # Left panel - Compact prompt pack selection
        self._build_prompt_pack_panel(content_frame)

        # Right panel - Configuration and pipeline controls (moved up)
        self._build_config_pipeline_panel(content_frame)

        # Bottom frame - Compact log and action buttons
        self._build_bottom_panel(main_frame)

        # Status bar - at the very bottom
        self._build_status_bar(main_frame)

        # Initialize UI state
        self._initialize_ui_state()

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
            api_frame, text="🔄", command=self._check_api_connection, style="Dark.TButton", width=3
        )
        self.check_api_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Status indicator - compact
        self.api_status_label = ttk.Label(
            api_frame, text="● Disconnected", style="Dark.TLabel", foreground="#ff6b6b"
        )
        self.api_status_label.pack(side=tk.LEFT)

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
        """Build configuration and pipeline control panel with grid layout"""
        # Center and right panels using grid
        center_panel = ttk.Frame(parent, style="Dark.TFrame")
        center_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)

        right_panel = ttk.Frame(parent, style="Dark.TFrame")
        right_panel.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # Configuration notebook in center
        config_notebook = ttk.Notebook(center_panel, style="Dark.TNotebook")
        config_notebook.pack(fill=tk.BOTH, expand=True)

        # Configuration display tab
        self._build_config_display_tab(config_notebook)

        # Pipeline controls in right panel
        self._build_pipeline_controls_panel(right_panel)

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
        # Create the PipelineControlsPanel component
        self.pipeline_controls_panel = PipelineControlsPanel(parent, style="Dark.TFrame")
        self.pipeline_controls_panel.pack(fill=tk.BOTH, expand=True)
        # Restore previous state if available
        if prev_state:
            try:
                self.pipeline_controls_panel.set_state(prev_state)
            except Exception as e:
                logger.warning(f"Failed to restore PipelineControlsPanel state: {e}")
        # Store references to variables for backward compatibility
        self.txt2img_enabled = self.pipeline_controls_panel.txt2img_enabled
        self.img2img_enabled = self.pipeline_controls_panel.img2img_enabled
        self.upscale_enabled = self.pipeline_controls_panel.upscale_enabled
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

        ttk.Button(
            config_buttons,
            text="� Save All Changes",
            command=self._save_all_config,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            config_buttons, text="↺ Reset All", command=self._reset_all_config, style="Dark.TButton"
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            config_buttons,
            text="💾 Save Pack Config",
            command=self._save_current_pack_config,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Preset selection dropdown
        preset_frame = ttk.LabelFrame(config_buttons, text="Base Preset", padding=5)
        preset_frame.pack(side=tk.LEFT, padx=(10, 10))

        self.preset_dropdown = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            state="readonly",
            width=15,
            style="Dark.TCombobox",
            values=self.config_manager.list_presets(),
        )
        self.preset_dropdown.pack(side=tk.LEFT)
        self.preset_dropdown.bind("<<ComboboxSelected>>", self._on_preset_changed)

        ttk.Button(
            config_buttons,
            text="� Save as Override Preset",
            command=self._save_override_preset,
            style="Dark.TButton",
        ).pack(side=tk.LEFT)

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
            text="🚀 Run Full Pipeline",
            command=self._run_full_pipeline,
            style="Accent.TButton",
        )  # Blue accent for primary action
        self.run_pipeline_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            main_buttons,
            text="🎨 txt2img Only",
            command=self._run_txt2img_only,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(
            main_buttons,
            text="📈 Upscale Only",
            command=self._run_upscale_only,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(
            main_buttons, text="🎬 Create Video", command=self._create_video, style="Dark.TButton"
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Utility buttons
        util_buttons = ttk.Frame(actions_frame, style="Dark.TFrame")
        util_buttons.pack(side=tk.RIGHT)

        ttk.Button(
            util_buttons,
            text="📁 Open Output",
            command=self._open_output_folder,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(
            util_buttons, text="🛑 Stop", command=self._stop_execution, style="Danger.TButton"
        ).pack(
            side=tk.LEFT, padx=(0, 10)
        )  # Red accent for stop
        ttk.Button(
            util_buttons, text="❌ Exit", command=self._graceful_exit, style="Danger.TButton"
        ).pack(
            side=tk.LEFT
        )  # Red accent for exit

        # Compact live log panel
        log_frame = ttk.LabelFrame(bottom_frame, text="📋 Live Log", style="Dark.TFrame", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Compact log text widget
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Consolas", 8),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure log colors
        self.log_text.tag_configure("INFO", foreground="#4CAF50")
        self.log_text.tag_configure("WARNING", foreground="#FF9800")
        self.log_text.tag_configure("ERROR", foreground="#f44336")
        self.log_text.tag_configure("SUCCESS", foreground="#2196F3")

    def _build_status_bar(self, parent):
        """Build status bar showing current state"""
        status_frame = ttk.Frame(parent, style="Dark.TFrame", relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        # State indicator
        self.state_label = ttk.Label(
            status_frame, text="● Idle", style="Dark.TLabel", foreground="#4CAF50"
        )
        self.state_label.pack(side=tk.LEFT, padx=5)

        # Progress message
        self.progress_message_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.progress_message_var, style="Dark.TLabel").pack(
            side=tk.LEFT, padx=10
        )

        # Spacer
        ttk.Label(status_frame, text="", style="Dark.TLabel").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

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

            # Update button states
            if new_state == GUIState.RUNNING:
                self.run_pipeline_btn.config(state=tk.DISABLED)
            elif new_state in (GUIState.IDLE, GUIState.ERROR):
                self.run_pipeline_btn.config(state=tk.NORMAL if self.api_connected else tk.DISABLED)

        self.state_manager.on_transition(on_state_change)

    def _poll_controller_logs(self):
        """Poll controller for log messages and display them"""
        messages = self.controller.get_log_messages()
        for msg in messages:
            self.log_message(msg.message, msg.level)
            self.progress_message_var.set(msg.message)

        # Schedule next poll
        self.root.after(100, self._poll_controller_logs)

    def _check_api_connection(self):
        """Check API connection status with improved diagnostics"""

        def check_in_thread():
            api_url = self.api_url_var.get()

            # Try the specified URL first
            self.log_message("🔍 Checking API connection...", "INFO")

            # First try direct connection
            client = SDWebUIClient(api_url)
            if client.check_api_ready():
                # Perform health check
                health = validate_webui_health(api_url)

                self.api_connected = True
                self.client = client
                self.pipeline = Pipeline(client, self.structured_logger)

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
                if client.check_api_ready():
                    health = validate_webui_health(discovered_url)

                    self.api_connected = True
                    self.client = client
                    self.pipeline = Pipeline(client, self.structured_logger)

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

    def _update_api_status(self, connected: bool, url: str = None):
        """Update API status indicator"""
        if connected:
            self.api_status_label.config(text="● Connected", foreground="#4CAF50")
            self.run_pipeline_btn.config(state=tk.NORMAL)

            # Update URL field if we found a different working port
            if url and url != self.api_url_var.get():
                self.api_url_var.set(url)
                self.log_message(f"Updated API URL to working port: {url}", "INFO")

            # Refresh models, VAE, upscalers, and schedulers when connected
            def refresh_all():
                try:
                    self._refresh_models()
                    self._refresh_vae_models()
                    self._refresh_upscalers()
                    self._refresh_schedulers()
                except Exception as e:
                    self.log_message(f"⚠️ Failed to refresh model lists: {e}", "WARNING")

            # Run refresh in a separate thread to avoid blocking UI
            threading.Thread(target=refresh_all, daemon=True).start()
        else:
            self.api_status_label.config(text="● Disconnected", foreground="#f44336")
            self.run_pipeline_btn.config(state=tk.DISABLED)

    def _on_pack_selection_changed_mediator(self, selected_packs: list[str]):
        """
        Mediator callback for pack selection changes from PromptPackPanel.

        Args:
            selected_packs: List of selected pack names
        """
        # Update internal state
        self.selected_packs = selected_packs

        if selected_packs:
            pack_name = selected_packs[0]
            self._add_log_message(f"📦 Selected pack: {pack_name}")
            self._last_selected_pack = pack_name
        else:
            self._add_log_message("No pack selected")
            self._last_selected_pack = None

        # Refresh configuration for selected pack
        self._refresh_config()

    def _on_pack_selection_changed(self, event=None):
        """Handle prompt pack selection changes - update config display dynamically"""
        selected_indices = self.packs_listbox.curselection()
        if selected_indices:
            pack_name = self.packs_listbox.get(selected_indices[0])
            self._add_log_message(f"📦 Selected pack: {pack_name}")

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
                self._add_log_message("No pack selected")
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
        """Initialize UI to default state with first pack selected and display mode active."""
        # Select first pack if available (panel already loaded packs during init)
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.select_first_pack()

        # Update log
        self._add_log_message("GUI initialized - ready for pipeline configuration")

    def _refresh_prompt_packs(self):
        """Refresh the prompt packs list"""
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.refresh_packs(silent=False)
            self.log_message("Refreshed prompt packs", "INFO")

    def _refresh_prompt_packs_silent(self):
        """Refresh the prompt packs list without logging (for initialization)"""
        if hasattr(self, "prompt_pack_panel"):
            self.prompt_pack_panel.refresh_packs(silent=True)

    def _refresh_config(self):
        """Refresh configuration based on pack selection and override state"""
        # Prevent recursive refreshes
        if self._refreshing_config:
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

    def _handle_override_mode(self, selected_packs):
        """Handle override mode: current config applies to all selected packs"""
        # Enable all config controls
        self._set_config_editable(True)

        # Update status messages
        if hasattr(self, "current_pack_label"):
            pack_list = ", ".join(selected_packs) if selected_packs else "none"
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
        # Ensure pack has a config file
        pack_config = self.config_manager.ensure_pack_config(pack_name, self.preset_var.get())

        # Enable config controls
        self._set_config_editable(True)

        # Load pack's individual config into forms
        self._load_config_into_forms(pack_config)
        self.current_config = pack_config

        # Update status
        if hasattr(self, "current_pack_label"):
            self.current_pack_label.configure(text=f"Pack: {pack_name}", foreground="#00ff00")

        self._show_config_status(f"Showing individual config for pack: {pack_name}")

        self.log_message(f"Loaded individual config for pack: {pack_name}", "INFO")

    def _handle_multi_pack_mode(self, selected_packs):
        """Handle multiple pack selection: grey out config"""
        # Disable config controls
        self._set_config_editable(False)

        # Update status
        if hasattr(self, "current_pack_label"):
            self.current_pack_label.configure(
                text=f"{len(selected_packs)} packs selected", foreground="#ffff00"
            )

        self._show_config_status(
            f"Multiple packs selected ({len(selected_packs)}) - each will use its individual config. Enable override to edit."
        )

        self.log_message(f"Multiple packs selected: {', '.join(selected_packs)}", "INFO")

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
        state = "normal" if editable else "disabled"

        # Disable/enable config widgets (this will be enhanced when we add the status display)
        if hasattr(self, "txt2img_vars"):
            for widget_name in ["steps", "cfg_scale", "width", "height", "sampler_name"]:
                if widget_name in getattr(self, "txt2img_widgets", {}):
                    try:
                        self.txt2img_widgets[widget_name].configure(state=state)
                    except:
                        pass  # Some widgets might not support state changes

    def _show_config_status(self, message: str):
        """Show configuration status message in the config area"""
        if hasattr(self, "config_status_label"):
            self.config_status_label.configure(text=message)

    def _get_config_from_forms(self) -> dict[str, Any]:
        """Extract current configuration from GUI forms"""
        config = {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}

        try:
            # txt2img config
            if hasattr(self, "txt2img_vars"):
                config["txt2img"] = {
                    "steps": self.txt2img_vars.get("steps", tk.IntVar(value=20)).get(),
                    "cfg_scale": self.txt2img_vars.get("cfg_scale", tk.DoubleVar(value=7.0)).get(),
                    "width": self.txt2img_vars.get("width", tk.IntVar(value=512)).get(),
                    "height": self.txt2img_vars.get("height", tk.IntVar(value=512)).get(),
                    "negative_prompt": self.txt2img_vars.get(
                        "negative_prompt", tk.StringVar()
                    ).get(),
                    "sampler_name": self.txt2img_vars.get(
                        "sampler_name", tk.StringVar(value="Euler a")
                    ).get(),
                    "scheduler": self.txt2img_vars.get(
                        "scheduler", tk.StringVar(value="normal")
                    ).get(),
                    "seed": self.txt2img_vars.get("seed", tk.IntVar(value=-1)).get(),
                    "clip_skip": self.txt2img_vars.get("clip_skip", tk.IntVar(value=2)).get(),
                    "model": self.txt2img_vars.get("model", tk.StringVar(value="")).get(),
                    "vae": self.txt2img_vars.get("vae", tk.StringVar(value="")).get(),
                    "enable_hr": self.txt2img_vars.get(
                        "enable_hr", tk.BooleanVar(value=False)
                    ).get(),
                    "hr_scale": self.txt2img_vars.get("hr_scale", tk.DoubleVar(value=2.0)).get(),
                    "hr_upscaler": self.txt2img_vars.get(
                        "hr_upscaler", tk.StringVar(value="Latent")
                    ).get(),
                    "denoising_strength": self.txt2img_vars.get(
                        "denoising_strength", tk.DoubleVar(value=0.7)
                    ).get(),
                }

                # Get prompt from text widget if available
                if hasattr(self, "pos_text"):
                    config["txt2img"]["prompt"] = self.pos_text.get(1.0, tk.END).strip()

            # img2img config
            if hasattr(self, "img2img_vars"):
                config["img2img"] = {
                    "steps": self.img2img_vars.get("steps", tk.IntVar(value=15)).get(),
                    "denoising_strength": self.img2img_vars.get(
                        "denoising_strength", tk.DoubleVar(value=0.3)
                    ).get(),
                    "sampler_name": self.img2img_vars.get(
                        "sampler_name", tk.StringVar(value="Euler a")
                    ).get(),
                    "scheduler": self.img2img_vars.get(
                        "scheduler", tk.StringVar(value="normal")
                    ).get(),
                    "cfg_scale": self.img2img_vars.get("cfg_scale", tk.DoubleVar(value=7.0)).get(),
                    "seed": self.img2img_vars.get("seed", tk.IntVar(value=-1)).get(),
                    "clip_skip": self.img2img_vars.get("clip_skip", tk.IntVar(value=2)).get(),
                    "model": self.img2img_vars.get("model", tk.StringVar(value="")).get(),
                    "vae": self.img2img_vars.get("vae", tk.StringVar(value="")).get(),
                }

            # upscale config
            if hasattr(self, "upscale_vars"):
                config["upscale"] = {
                    "upscaler": self.upscale_vars.get(
                        "upscaler", tk.StringVar(value="R-ESRGAN 4x+")
                    ).get(),
                    "upscaling_resize": self.upscale_vars.get(
                        "upscaling_resize", tk.DoubleVar(value=2.0)
                    ).get(),
                    "mode": self.upscale_vars.get(
                        "upscale_mode", tk.StringVar(value="single")
                    ).get(),
                    "denoising_strength": self.upscale_vars.get(
                        "denoising_strength", tk.DoubleVar(value=0.2)
                    ).get(),
                    "gfpgan_visibility": self.upscale_vars.get(
                        "gfpgan_visibility", tk.DoubleVar(value=0.0)
                    ).get(),
                    "codeformer_visibility": self.upscale_vars.get(
                        "codeformer_visibility", tk.DoubleVar(value=0.0)
                    ).get(),
                    "codeformer_weight": self.upscale_vars.get(
                        "codeformer_weight", tk.DoubleVar(value=0.5)
                    ).get(),
                }

            # api config
            if hasattr(self, "api_vars"):
                config["api"] = {
                    "base_url": self.api_vars.get(
                        "base_url", tk.StringVar(value="http://127.0.0.1:7860")
                    ).get(),
                    "timeout": self.api_vars.get("timeout", tk.IntVar(value=300)).get(),
                }

        except Exception as e:
            self.log_message(f"Error reading config from forms: {e}", "ERROR")

        return config

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
        """Add message to live log"""
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # Only update GUI if log_text widget exists
        if hasattr(self, "log_text"):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_entry, level)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        # Also log to Python logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    def _run_full_pipeline(self):
        """Run the complete pipeline"""
        if not self.api_connected:
            messagebox.showerror("API Error", "Please connect to API first")
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

                    # Get configuration - use current form values if available
                    if hasattr(self, "txt2img_vars") and self.current_config:
                        config = self.current_config
                    else:
                        # Fall back to file-based config
                        pack_overrides = self.config_manager.get_pack_overrides(pack_file.stem)
                        config = self.config_manager.resolve_config(
                            preset_name="default", pack_overrides=pack_overrides
                        )

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

                # Get configuration
                config = self.current_config or self.config_manager.get_default_config()

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
        """Get list of selected prompt pack files"""
        selected_indices = self.packs_listbox.curselection()
        if not selected_indices:
            return []

        packs_dir = Path("packs")
        selected_packs = []

        for index in selected_indices:
            pack_name = self.packs_listbox.get(index)
            pack_path = packs_dir / pack_name
            if pack_path.exists():
                selected_packs.append(pack_path)

        return selected_packs

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
        info_count = len(results.get("info", []))

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

        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the GUI application"""
        # Start initial config refresh
        self._refresh_config()

        # Now refresh prompt packs with logging (log widget is ready)
        self._refresh_prompt_packs()

        # Set up proper window closing
        self.root.protocol("WM_DELETE_WINDOW", self._graceful_exit)

        self.log_message("🚀 StableNew GUI started", "SUCCESS")
        self.log_message("Please connect to WebUI API to begin", "INFO")

        # Start the GUI main loop
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
            model_row, textvariable=self.txt2img_vars["model"], width=25, state="readonly"
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
            vae_row, textvariable=self.txt2img_vars["vae"], width=25, state="readonly"
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
            model_row, textvariable=self.img2img_vars["model"], width=25, state="readonly"
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
            vae_row, textvariable=self.img2img_vars["vae"], width=25, state="readonly"
        )
        self.img2img_vae_combo.pack(side=tk.LEFT, padx=(5, 5))
        self.img2img_widgets["vae"] = self.img2img_vae_combo
        ttk.Button(
            vae_row, text="🔄", command=self._refresh_vae_models, width=3, style="Dark.TButton"
        ).pack(side=tk.LEFT)

        canvas.pack(fill="both", expand=True)

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
            upscaler_row, textvariable=self.upscale_vars["upscaler"], width=25, state="readonly"
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
            # Build config from form values
            config = {
                "txt2img": {
                    "steps": self.txt2img_vars["steps"].get(),
                    "sampler_name": self.txt2img_vars["sampler_name"].get(),
                    "cfg_scale": self.txt2img_vars["cfg_scale"].get(),
                    "width": self.txt2img_vars["width"].get(),
                    "height": self.txt2img_vars["height"].get(),
                    "negative_prompt": self.txt2img_vars["negative_prompt"].get(),
                },
                "img2img": {
                    "steps": self.img2img_vars["steps"].get(),
                    "denoising_strength": self.img2img_vars["denoising_strength"].get(),
                },
                "upscale": {
                    "upscaler": self.upscale_vars["upscaler"].get(),
                    "upscaling_resize": self.upscale_vars["upscaling_resize"].get(),
                },
                "api": {
                    "base_url": self.api_vars["base_url"].get(),
                    "timeout": self.api_vars["timeout"].get(),
                },
            }

            # Save as current config
            self.current_config = config

            # Optionally save as preset
            preset_name = tk.simpledialog.askstring("Save Preset", "Enter preset name (optional):")
            if preset_name:
                self.config_manager.save_preset(preset_name, config)
                self.log_message(f"Saved configuration as preset: {preset_name}", "SUCCESS")
            else:
                self.log_message("Configuration updated (not saved as preset)", "INFO")

        except Exception as e:
            self.log_message(f"Failed to save configuration: {e}", "ERROR")

    def _reset_all_config(self):
        """Reset all configuration to defaults"""
        defaults = self.config_manager.get_default_config()
        self._load_config_into_forms(defaults)
        self.log_message("Configuration reset to defaults", "INFO")

    def _on_preset_changed(self, event=None):
        """Handle preset dropdown selection changes"""
        preset_name = self.preset_var.get()
        if preset_name:
            config = self.config_manager.load_preset(preset_name)
            if config:
                self.current_preset = preset_name
                if not self.override_pack_var.get():
                    self._load_config_into_forms(config)
                self.current_config = config
                self.log_message(f"Selected preset: {preset_name}", "INFO")
                self._refresh_config()  # Update display based on current pack selection
            else:
                self.log_message(f"Failed to load preset: {preset_name}", "ERROR")

    def _save_override_preset(self):
        """Save current configuration as the override preset (updates default)"""
        current_config = self._get_config_from_forms()
        preset_name = self.preset_var.get()

        if self.config_manager.save_preset(preset_name, current_config):
            self.log_message(f"Updated preset '{preset_name}' with override config", "SUCCESS")
        else:
            self.log_message(f"Failed to save override preset: {preset_name}", "ERROR")

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
        # Preserve current pack selection before updating forms
        current_selection = self.packs_listbox.curselection()
        selected_pack = None
        if current_selection:
            selected_pack = self.packs_listbox.get(current_selection[0])

        try:
            # txt2img config
            txt2img_config = config.get("txt2img", {})
            if hasattr(self, "txt2img_vars"):
                self.txt2img_vars["steps"].set(txt2img_config.get("steps", 20))
                # Handle both old and new sampler format
                sampler_name = txt2img_config.get("sampler_name", "Euler a")
                if "scheduler" in txt2img_config and txt2img_config["scheduler"] != "Automatic":
                    sampler_display = f"{sampler_name} {txt2img_config['scheduler']}"
                else:
                    sampler_display = sampler_name
                self.txt2img_vars["sampler_name"].set(sampler_display)

                self.txt2img_vars["cfg_scale"].set(txt2img_config.get("cfg_scale", 7.0))
                self.txt2img_vars["width"].set(txt2img_config.get("width", 512))
                self.txt2img_vars["height"].set(txt2img_config.get("height", 512))
                self.txt2img_vars["negative_prompt"].set(txt2img_config.get("negative_prompt", ""))

                # New parameters
                self.txt2img_vars["seed"].set(txt2img_config.get("seed", -1))
                self.txt2img_vars["clip_skip"].set(txt2img_config.get("clip_skip", 2))
                self.txt2img_vars["scheduler"].set(txt2img_config.get("scheduler", "normal"))
                self.txt2img_vars["model"].set(txt2img_config.get("model", ""))
                self.txt2img_vars["vae"].set(txt2img_config.get("vae", ""))

                # Hires.fix parameters
                self.txt2img_vars["enable_hr"].set(txt2img_config.get("enable_hr", False))
                self.txt2img_vars["hr_scale"].set(txt2img_config.get("hr_scale", 2.0))
                self.txt2img_vars["hr_upscaler"].set(
                    txt2img_config.get("hr_upscaler", "R-ESRGAN 4x+")
                )
                self.txt2img_vars["denoising_strength"].set(
                    txt2img_config.get("denoising_strength", 0.7)
                )

                # Update text widgets if they exist
                if hasattr(self, "pos_text"):
                    self.pos_text.delete(1.0, tk.END)
                    self.pos_text.insert(1.0, txt2img_config.get("prompt", ""))

                if hasattr(self, "neg_text"):
                    self.neg_text.delete(1.0, tk.END)
                    self.neg_text.insert(1.0, txt2img_config.get("negative_prompt", ""))

            # img2img config
            img2img_config = config.get("img2img", {})
            if hasattr(self, "img2img_vars"):
                self.img2img_vars["steps"].set(img2img_config.get("steps", 15))
                self.img2img_vars["denoising_strength"].set(
                    img2img_config.get("denoising_strength", 0.3)
                )
                self.img2img_vars["sampler_name"].set(img2img_config.get("sampler_name", "Euler a"))
                self.img2img_vars["scheduler"].set(img2img_config.get("scheduler", "normal"))
                self.img2img_vars["cfg_scale"].set(img2img_config.get("cfg_scale", 7.0))
                self.img2img_vars["seed"].set(img2img_config.get("seed", -1))
                self.img2img_vars["clip_skip"].set(img2img_config.get("clip_skip", 2))
                self.img2img_vars["model"].set(img2img_config.get("model", ""))
                self.img2img_vars["vae"].set(img2img_config.get("vae", ""))

            # upscale config
            upscale_config = config.get("upscale", {})
            if hasattr(self, "upscale_vars"):
                self.upscale_vars["upscaler"].set(upscale_config.get("upscaler", "R-ESRGAN 4x+"))
                self.upscale_vars["upscaling_resize"].set(
                    upscale_config.get("upscaling_resize", 2.0)
                )
                if "upscale_mode" in self.upscale_vars:
                    self.upscale_vars["upscale_mode"].set(upscale_config.get("mode", "single"))
                self.upscale_vars["denoising_strength"].set(
                    upscale_config.get("denoising_strength", 0.2)
                )
                self.upscale_vars["gfpgan_visibility"].set(
                    upscale_config.get("gfpgan_visibility", 0.5)
                )
                self.upscale_vars["codeformer_visibility"].set(
                    upscale_config.get("codeformer_visibility", 0.0)
                )
                if "codeformer_weight" in self.upscale_vars:
                    self.upscale_vars["codeformer_weight"].set(
                        upscale_config.get("codeformer_weight", 0.5)
                    )

            # api config
            api_config = config.get("api", {})
            if hasattr(self, "api_vars"):
                self.api_vars["base_url"].set(api_config.get("base_url", "http://127.0.0.1:7860"))
                self.api_vars["timeout"].set(api_config.get("timeout", 300))

        except Exception as e:
            self.log_message(f"Error loading config into forms: {e}", "ERROR")

        # Restore pack selection if it was lost during form updates
        if selected_pack and not self.packs_listbox.curselection():
            for i in range(self.packs_listbox.size()):
                if self.packs_listbox.get(i) == selected_pack:
                    self.packs_listbox.selection_set(i)
                    self.packs_listbox.activate(i)
                    break

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

        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(exec_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=10)

    def _build_settings_tab(self, parent):
        """Build settings tab"""
        settings_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Show current preset
        presets = self.config_manager.list_presets()
        settings_text.insert(1.0, "Available Presets:\n\n")
        for preset in presets:
            settings_text.insert(tk.END, f"- {preset}\n")

        settings_text.insert(tk.END, "\n\nDefault Configuration:\n\n")
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
        self.log_text.insert(tk.END, message + "\n")
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
        self.progress_var.set("Checking API...")
        self._add_log_message("Checking SD WebUI API connection...")

        def check():
            url = self.api_url_var.get()
            client = SDWebUIClient(base_url=url)
            if client.check_api_ready():
                self.client = client
                self.pipeline = Pipeline(self.client, self.structured_logger)
                self.root.after(
                    0, lambda: self.api_status_label.config(text="Connected", foreground="green")
                )
                self.root.after(0, lambda: self._add_log_message("✓ API is ready"))
                self.root.after(0, lambda: self.progress_var.set("API connected"))
            else:
                self.root.after(
                    0, lambda: self.api_status_label.config(text="Failed", foreground="red")
                )
                self.root.after(0, lambda: self._add_log_message("✗ API not available"))
                self.root.after(0, lambda: self.progress_var.set("API check failed"))

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

        self.progress_message_var.set("Running pipeline...")

        # Define pipeline function that checks cancel token
        def pipeline_func():
            try:
                # Pass cancel_token to pipeline
                results = self.pipeline.run_full_pipeline(
                    prompt, config, run_name, batch_size, cancel_token=self.controller.cancel_token
                )
                return results
            except Exception:
                logger.exception("Pipeline execution error")
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
                0, lambda: self.progress_message_var.set(f"Completed: {num_images} images")
            )
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Success",
                    f"Pipeline completed!\n{num_images} images generated\nOutput: {output_dir}",
                ),
            )

        # Error callback
        def on_error(e):
            self.root.after(0, lambda: self.log_message(f"✗ Error: {str(e)}", "ERROR"))
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.progress_message_var.set("Error"))

        # Start pipeline using controller
        self.controller.start_pipeline(pipeline_func, on_complete=on_complete, on_error=on_error)

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
                    messagebox.showinfo("Success", f"Video created:\n{video_path}")
                else:
                    self._add_log_message(f"✗ Failed to create video from {subdir}")

                return

        messagebox.showerror("Error", "No image directories found")

    def _refresh_models(self):
        """Refresh the list of available SD models"""
        if not self.client:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            models = self.client.get_models()
            model_names = [""] + [
                model.get("title", model.get("model_name", "")) for model in models
            ]

            # Update all model comboboxes
            if hasattr(self, "model_combo"):
                self.model_combo["values"] = model_names
            if hasattr(self, "img2img_model_combo"):
                self.img2img_model_combo["values"] = model_names

            self._add_log_message(f"🔄 Loaded {len(models)} SD models")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh models: {e}")

    def _refresh_vae_models(self):
        """Refresh the list of available VAE models"""
        if not self.client:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            vae_models = self.client.get_vae_models()
            vae_names = [""] + [vae.get("model_name", "") for vae in vae_models]

            # Update all VAE comboboxes
            if hasattr(self, "vae_combo"):
                self.vae_combo["values"] = vae_names
            if hasattr(self, "img2img_vae_combo"):
                self.img2img_vae_combo["values"] = vae_names

            self._add_log_message(f"🔄 Loaded {len(vae_models)} VAE models")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh VAE models: {e}")

    def _refresh_upscalers(self):
        """Refresh the list of available upscalers"""
        if not self.client:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            upscalers = self.client.get_upscalers()
            upscaler_names = [
                upscaler.get("name", "") for upscaler in upscalers if upscaler.get("name")
            ]

            # Update upscaler combobox
            if hasattr(self, "upscaler_combo"):
                self.upscaler_combo["values"] = upscaler_names

            self._add_log_message(f"🔄 Loaded {len(upscalers)} upscalers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh upscalers: {e}")

    def _refresh_schedulers(self):
        """Refresh the list of available schedulers"""
        if not self.client:
            messagebox.showerror("Error", "API client not connected")
            return

        try:
            schedulers = self.client.get_schedulers()

            # Update all scheduler comboboxes
            if hasattr(self, "scheduler_combo"):
                self.scheduler_combo["values"] = schedulers
            if hasattr(self, "img2img_scheduler_combo"):
                self.img2img_scheduler_combo["values"] = schedulers

            self._add_log_message(f"🔄 Loaded {len(schedulers)} schedulers")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh schedulers: {e}")

    def _on_hires_toggle(self):
        """Handle hires.fix enable/disable toggle"""
        # This method can be used to enable/disable hires.fix related controls
        # For now, just log the change
        enabled = self.txt2img_vars.get("enable_hr", tk.BooleanVar()).get()
        self._add_log_message(f"📏 Hires.fix {'enabled' if enabled else 'disabled'}")

    def _randomize_seed(self, var_dict_name):
        """Generate a random seed for the specified variable dictionary"""
        import random

        random_seed = random.randint(1, 2147483647)  # Max int32 value
        var_dict = getattr(self, f"{var_dict_name}_vars", {})
        if "seed" in var_dict:
            var_dict["seed"].set(random_seed)
            self._add_log_message(f"🎲 Random seed generated: {random_seed}")

    def _randomize_txt2img_seed(self):
        """Generate random seed for txt2img"""
        self._randomize_seed("txt2img")

    def _randomize_img2img_seed(self):
        """Generate random seed for img2img"""
        self._randomize_seed("img2img")

    def run(self):
        """Run the GUI application"""
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

        self.root.mainloop()
