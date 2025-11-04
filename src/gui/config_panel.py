"""
ConfigPanel - UI component for configuration management with tabs.

This panel encapsulates all configuration UI and provides a clean API for
getting/setting configuration and validation.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any

logger = logging.getLogger(__name__)

# Constants for dimension bounds
MAX_DIMENSION = 2260
MIN_DIMENSION = 64


class ConfigPanel(ttk.Frame):
    """
    A UI panel for configuration management.

    This panel handles:
    - Configuration tabs (txt2img, img2img, upscale, api)
    - Configuration validation
    - Dimension bounds checking (≤2260)
    - Face restoration toggle with show/hide controls
    - Hires fix steps setting

    It exposes get_config(), set_config(), and validate() methods.
    """

    def __init__(self, parent: tk.Widget, coordinator: object | None = None, **kwargs):
        """
        Initialize the ConfigPanel.

        Args:
            parent: Parent widget
            coordinator: Coordinator object (for mediator pattern)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.coordinator = coordinator

        # Initialize variable dictionaries
        self.txt2img_vars: dict[str, tk.Variable] = {}
        self.img2img_vars: dict[str, tk.Variable] = {}
        self.upscale_vars: dict[str, tk.Variable] = {}
        self.api_vars: dict[str, tk.Variable] = {}

        # Widget dictionaries for enabling/disabling
        self.txt2img_widgets: dict[str, tk.Widget] = {}
        self.img2img_widgets: dict[str, tk.Widget] = {}
        self.upscale_widgets: dict[str, tk.Widget] = {}

        # Face restoration widgets (for show/hide)
        self.face_restoration_widgets: list[tk.Widget] = []

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the panel UI."""
        # Configuration status section
        status_frame = ttk.LabelFrame(
            self, text="Configuration Status", style="Dark.TFrame", padding=5
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

        # Create notebook for stage-specific configurations
        self.notebook = ttk.Notebook(self, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Create individual tabs
        self._build_txt2img_tab()
        self._build_img2img_tab()
        self._build_upscale_tab()
        self._build_api_tab()

        # Add buttons at bottom
        self._build_action_buttons()

    def _build_txt2img_tab(self):
        """Build txt2img configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🎨 txt2img")

        # Create scrollable container
        canvas = tk.Canvas(tab, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initialize variables with defaults
        self.txt2img_vars["steps"] = tk.IntVar(value=20)
        self.txt2img_vars["cfg_scale"] = tk.DoubleVar(value=7.0)
        self.txt2img_vars["width"] = tk.IntVar(value=512)
        self.txt2img_vars["height"] = tk.IntVar(value=512)
        self.txt2img_vars["sampler_name"] = tk.StringVar(value="Euler a")
        self.txt2img_vars["scheduler"] = tk.StringVar(value="normal")
        self.txt2img_vars["seed"] = tk.IntVar(value=-1)
        self.txt2img_vars["clip_skip"] = tk.IntVar(value=2)
        self.txt2img_vars["model"] = tk.StringVar(value="")
        self.txt2img_vars["vae"] = tk.StringVar(value="")
        self.txt2img_vars["negative_prompt"] = tk.StringVar(value="")

        # Hires fix
        self.txt2img_vars["enable_hr"] = tk.BooleanVar(value=False)
        self.txt2img_vars["hr_scale"] = tk.DoubleVar(value=2.0)
        self.txt2img_vars["hr_upscaler"] = tk.StringVar(value="Latent")
        self.txt2img_vars["denoising_strength"] = tk.DoubleVar(value=0.7)
        self.txt2img_vars["hires_steps"] = tk.IntVar(value=0)  # NEW: hires_steps

        # Face restoration (NEW)
        self.txt2img_vars["face_restoration_enabled"] = tk.BooleanVar(value=False)
        self.txt2img_vars["face_restoration_model"] = tk.StringVar(value="GFPGAN")
        self.txt2img_vars["face_restoration_weight"] = tk.DoubleVar(value=0.5)

        # Basic settings section
        basic_frame = ttk.LabelFrame(scrollable_frame, text="Basic Settings", padding=10)
        basic_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        # Steps
        ttk.Label(basic_frame, text="Steps:").grid(row=row, column=0, sticky=tk.W, pady=2)
        steps_spin = ttk.Spinbox(
            basic_frame, from_=1, to=150, textvariable=self.txt2img_vars["steps"], width=15
        )
        steps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["steps"] = steps_spin
        row += 1

        # CFG Scale
        ttk.Label(basic_frame, text="CFG Scale:").grid(row=row, column=0, sticky=tk.W, pady=2)
        cfg_spin = ttk.Spinbox(
            basic_frame,
            from_=1.0,
            to=30.0,
            increment=0.5,
            textvariable=self.txt2img_vars["cfg_scale"],
            width=15,
        )
        cfg_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["cfg_scale"] = cfg_spin
        row += 1

        # Dimensions section with bounds warning
        dim_frame = ttk.LabelFrame(scrollable_frame, text="Image Dimensions", padding=10)
        dim_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(dim_frame, text="Width:").grid(row=row, column=0, sticky=tk.W, pady=2)
        width_spin = ttk.Spinbox(
            dim_frame,
            from_=MIN_DIMENSION,
            to=MAX_DIMENSION,
            increment=64,
            textvariable=self.txt2img_vars["width"],
            width=15,
        )
        width_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["width"] = width_spin
        row += 1

        ttk.Label(dim_frame, text="Height:").grid(row=row, column=0, sticky=tk.W, pady=2)
        height_spin = ttk.Spinbox(
            dim_frame,
            from_=MIN_DIMENSION,
            to=MAX_DIMENSION,
            increment=64,
            textvariable=self.txt2img_vars["height"],
            width=15,
        )
        height_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["height"] = height_spin
        row += 1

        # Dimension warning label
        self.dim_warning_label = ttk.Label(
            dim_frame,
            text=f"⚠️ Maximum recommended: {MAX_DIMENSION}x{MAX_DIMENSION}",
            foreground="#FF9800",
            font=("Segoe UI", 8),
        )
        self.dim_warning_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # Sampler section
        sampler_frame = ttk.LabelFrame(scrollable_frame, text="Sampler Settings", padding=10)
        sampler_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(sampler_frame, text="Sampler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        sampler_combo = ttk.Combobox(
            sampler_frame,
            textvariable=self.txt2img_vars["sampler_name"],
            values=["Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "LMS", "Heun"],
            state="readonly",
            width=13,
        )
        sampler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["sampler_name"] = sampler_combo
        row += 1

        ttk.Label(sampler_frame, text="Scheduler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        scheduler_combo = ttk.Combobox(
            sampler_frame,
            textvariable=self.txt2img_vars["scheduler"],
            values=["normal", "karras", "exponential", "sgm_uniform"],
            state="readonly",
            width=13,
        )
        scheduler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["scheduler"] = scheduler_combo
        row += 1

        # Hires fix section
        hires_frame = ttk.LabelFrame(scrollable_frame, text="Hires Fix", padding=10)
        hires_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        enable_hr_check = ttk.Checkbutton(
            hires_frame, text="Enable Hires Fix", variable=self.txt2img_vars["enable_hr"]
        )
        enable_hr_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(hires_frame, text="Hires Steps:").grid(row=row, column=0, sticky=tk.W, pady=2)
        hires_steps_spin = ttk.Spinbox(
            hires_frame, from_=0, to=150, textvariable=self.txt2img_vars["hires_steps"], width=15
        )
        hires_steps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["hires_steps"] = hires_steps_spin
        row += 1

        ttk.Label(hires_frame, text="Upscale by:").grid(row=row, column=0, sticky=tk.W, pady=2)
        hr_scale_spin = ttk.Spinbox(
            hires_frame,
            from_=1.0,
            to=4.0,
            increment=0.1,
            textvariable=self.txt2img_vars["hr_scale"],
            width=15,
        )
        hr_scale_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(hires_frame, text="Denoising:").grid(row=row, column=0, sticky=tk.W, pady=2)
        denoise_spin = ttk.Spinbox(
            hires_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.txt2img_vars["denoising_strength"],
            width=15,
        )
        denoise_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # Face Restoration section (NEW)
        face_frame = ttk.LabelFrame(scrollable_frame, text="Face Restoration", padding=10)
        face_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        enable_face_check = ttk.Checkbutton(
            face_frame,
            text="Enable Face Restoration",
            variable=self.txt2img_vars["face_restoration_enabled"],
            command=self._toggle_face_restoration,
        )
        enable_face_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)
        row += 1

        # Face restoration controls (initially hidden)
        ttk.Label(face_frame, text="Model:").grid(row=row, column=0, sticky=tk.W, pady=2)
        face_model_combo = ttk.Combobox(
            face_frame,
            textvariable=self.txt2img_vars["face_restoration_model"],
            values=["GFPGAN", "CodeFormer"],
            state="readonly",
            width=13,
        )
        face_model_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.face_restoration_widgets.append(face_model_combo)
        face_model_combo.grid_remove()  # Hide initially
        row += 1

        ttk.Label(face_frame, text="Weight:").grid(row=row, column=0, sticky=tk.W, pady=2)
        face_weight_spin = ttk.Spinbox(
            face_frame,
            from_=0.0,
            to=1.0,
            increment=0.1,
            textvariable=self.txt2img_vars["face_restoration_weight"],
            width=15,
        )
        face_weight_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.face_restoration_widgets.append(face_weight_spin)
        face_weight_spin.grid_remove()  # Hide initially
        row += 1

        # Store label widgets too for show/hide
        face_model_label = ttk.Label(face_frame, text="Model:")
        face_weight_label = ttk.Label(face_frame, text="Weight:")
        self.face_restoration_widgets.extend([face_model_label, face_weight_label])

        # Seed and advanced
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="Advanced", padding=10)
        advanced_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(advanced_frame, text="Seed:").grid(row=row, column=0, sticky=tk.W, pady=2)
        seed_entry = ttk.Entry(advanced_frame, textvariable=self.txt2img_vars["seed"], width=15)
        seed_entry.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(advanced_frame, text="CLIP Skip:").grid(row=row, column=0, sticky=tk.W, pady=2)
        clip_spin = ttk.Spinbox(
            advanced_frame, from_=1, to=12, textvariable=self.txt2img_vars["clip_skip"], width=15
        )
        clip_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

    def _toggle_face_restoration(self):
        """Show/hide face restoration controls based on checkbox."""
        enabled = self.txt2img_vars["face_restoration_enabled"].get()

        for widget in self.face_restoration_widgets:
            if enabled:
                widget.grid()
            else:
                widget.grid_remove()

    def _build_img2img_tab(self):
        """Build img2img configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🧹 img2img")

        # Initialize variables
        self.img2img_vars["steps"] = tk.IntVar(value=15)
        self.img2img_vars["denoising_strength"] = tk.DoubleVar(value=0.3)
        self.img2img_vars["cfg_scale"] = tk.DoubleVar(value=7.0)
        self.img2img_vars["sampler_name"] = tk.StringVar(value="Euler a")
        self.img2img_vars["scheduler"] = tk.StringVar(value="normal")
        self.img2img_vars["seed"] = tk.IntVar(value=-1)
        self.img2img_vars["clip_skip"] = tk.IntVar(value=2)

        # Basic settings
        basic_frame = ttk.LabelFrame(tab, text="img2img Settings", padding=10)
        basic_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(basic_frame, text="Steps:").grid(row=row, column=0, sticky=tk.W, pady=2)
        steps_spin = ttk.Spinbox(
            basic_frame, from_=1, to=150, textvariable=self.img2img_vars["steps"], width=15
        )
        steps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["steps"] = steps_spin
        row += 1

        ttk.Label(basic_frame, text="Denoising:").grid(row=row, column=0, sticky=tk.W, pady=2)
        denoise_spin = ttk.Spinbox(
            basic_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.img2img_vars["denoising_strength"],
            width=15,
        )
        denoise_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["denoising_strength"] = denoise_spin
        row += 1

        ttk.Label(basic_frame, text="CFG Scale:").grid(row=row, column=0, sticky=tk.W, pady=2)
        cfg_spin = ttk.Spinbox(
            basic_frame,
            from_=1.0,
            to=30.0,
            increment=0.5,
            textvariable=self.img2img_vars["cfg_scale"],
            width=15,
        )
        cfg_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

    def _build_upscale_tab(self):
        """Build upscale configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="📈 Upscale")

        # Initialize variables
        self.upscale_vars["upscaler"] = tk.StringVar(value="R-ESRGAN 4x+")
        self.upscale_vars["scale"] = tk.IntVar(value=2)

        # Settings
        settings_frame = ttk.LabelFrame(tab, text="Upscale Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(settings_frame, text="Upscaler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        upscaler_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.upscale_vars["upscaler"],
            values=["R-ESRGAN 4x+", "ESRGAN_4x", "Latent", "None"],
            state="readonly",
            width=13,
        )
        upscaler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["upscaler"] = upscaler_combo
        row += 1

        ttk.Label(settings_frame, text="Scale:").grid(row=row, column=0, sticky=tk.W, pady=2)
        scale_spin = ttk.Spinbox(
            settings_frame, from_=1, to=4, textvariable=self.upscale_vars["scale"], width=15
        )
        scale_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

    def _build_api_tab(self):
        """Build API configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🔌 API")

        # Initialize variables
        self.api_vars["api_url"] = tk.StringVar(value="http://127.0.0.1:7860")
        self.api_vars["timeout"] = tk.IntVar(value=30)

        # Settings
        settings_frame = ttk.LabelFrame(tab, text="API Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(settings_frame, text="API URL:").grid(row=row, column=0, sticky=tk.W, pady=2)
        api_entry = ttk.Entry(settings_frame, textvariable=self.api_vars["api_url"], width=30)
        api_entry.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(settings_frame, text="Timeout (s):").grid(row=row, column=0, sticky=tk.W, pady=2)
        timeout_spin = ttk.Spinbox(
            settings_frame, from_=10, to=300, textvariable=self.api_vars["timeout"], width=15
        )
        timeout_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

    def _build_action_buttons(self):
        """Build action buttons at bottom of panel."""
        button_frame = ttk.Frame(self, style="Dark.TFrame")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(5, 10))

        ttk.Button(
            button_frame,
            text="💾 Save All Changes",
            command=self._on_save_all,
            style="Dark.TButton",
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame, text="↺ Reset All", command=self._on_reset_all, style="Dark.TButton"
        ).pack(side=tk.LEFT, padx=(0, 5))

    def _on_save_all(self):
        """Handle save all button click."""
        # This would be wired to coordinator
        if self.coordinator and hasattr(self.coordinator, "on_config_save"):
            config = self.get_config()
            self.coordinator.on_config_save(config)

    def _on_reset_all(self):
        """Handle reset all button click."""
        # Reset to defaults
        default_config = self._get_default_config()
        self.set_config(default_config)

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "txt2img": {
                "steps": 20,
                "cfg_scale": 7.0,
                "width": 512,
                "height": 512,
                "sampler_name": "Euler a",
                "scheduler": "normal",
                "seed": -1,
                "clip_skip": 2,
                "model": "",
                "vae": "",
                "negative_prompt": "",
                "enable_hr": False,
                "hr_scale": 2.0,
                "hr_upscaler": "Latent",
                "denoising_strength": 0.7,
                "hires_steps": 0,
                "face_restoration_enabled": False,
                "face_restoration_model": "GFPGAN",
                "face_restoration_weight": 0.5,
            },
            "img2img": {
                "steps": 15,
                "denoising_strength": 0.3,
                "cfg_scale": 7.0,
                "sampler_name": "Euler a",
                "scheduler": "normal",
                "seed": -1,
                "clip_skip": 2,
            },
            "upscale": {
                "upscaler": "R-ESRGAN 4x+",
                "scale": 2,
            },
            "api": {
                "api_url": "http://127.0.0.1:7860",
                "timeout": 30,
            },
        }

    def get_config(self) -> dict[str, Any]:
        """
        Get current configuration from UI.

        Returns:
            Dictionary containing all configuration values
        """
        config = {"txt2img": {}, "img2img": {}, "upscale": {}, "api": {}}

        # Extract txt2img config
        for key, var in self.txt2img_vars.items():
            config["txt2img"][key] = var.get()

        # Extract img2img config
        for key, var in self.img2img_vars.items():
            config["img2img"][key] = var.get()

        # Extract upscale config
        for key, var in self.upscale_vars.items():
            config["upscale"][key] = var.get()

        # Extract API config
        for key, var in self.api_vars.items():
            config["api"][key] = var.get()

        return config

    def set_config(self, config: dict[str, Any]) -> None:
        """
        Set configuration in UI.

        Args:
            config: Dictionary containing configuration values
        """
        # Set txt2img config
        if "txt2img" in config:
            for key, value in config["txt2img"].items():
                if key in self.txt2img_vars:
                    self.txt2img_vars[key].set(value)

        # Set img2img config
        if "img2img" in config:
            for key, value in config["img2img"].items():
                if key in self.img2img_vars:
                    self.img2img_vars[key].set(value)

        # Set upscale config
        if "upscale" in config:
            for key, value in config["upscale"].items():
                if key in self.upscale_vars:
                    self.upscale_vars[key].set(value)

        # Set API config
        if "api" in config:
            for key, value in config["api"].items():
                if key in self.api_vars:
                    self.api_vars[key].set(value)

        # Update face restoration visibility
        self._toggle_face_restoration()

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate current configuration.

        Returns:
            Tuple of (ok: bool, messages: List[str])
            ok is True if valid, False if there are errors
            messages contains warning/error messages
        """
        messages = []
        ok = True

        # Check dimension bounds
        width = self.txt2img_vars["width"].get()
        height = self.txt2img_vars["height"].get()

        if width > MAX_DIMENSION:
            ok = False
            messages.append(f"Width {width} exceeds maximum of {MAX_DIMENSION}")

        if height > MAX_DIMENSION:
            ok = False
            messages.append(f"Height {height} exceeds maximum of {MAX_DIMENSION}")

        if width < MIN_DIMENSION:
            ok = False
            messages.append(f"Width {width} below minimum of {MIN_DIMENSION}")

        if height < MIN_DIMENSION:
            ok = False
            messages.append(f"Height {height} below minimum of {MIN_DIMENSION}")

        # Check steps are positive
        if self.txt2img_vars["steps"].get() < 1:
            ok = False
            messages.append("txt2img steps must be at least 1")

        if self.img2img_vars["steps"].get() < 1:
            ok = False
            messages.append("img2img steps must be at least 1")

        return ok, messages

    def set_editable(self, editable: bool) -> None:
        """
        Enable or disable editing of config controls.

        Args:
            editable: True to enable editing, False to disable
        """
        state = "normal" if editable else "disabled"

        # Update txt2img widgets
        for widget in self.txt2img_widgets.values():
            try:
                widget.configure(state=state)
            except:
                pass  # Some widgets may not support state

        # Update img2img widgets
        for widget in self.img2img_widgets.values():
            try:
                widget.configure(state=state)
            except:
                pass

        # Update upscale widgets
        for widget in self.upscale_widgets.values():
            try:
                widget.configure(state=state)
            except:
                pass

    def set_status_message(self, message: str) -> None:
        """
        Set configuration status message.

        Args:
            message: Status message to display
        """
        if hasattr(self, "config_status_label"):
            self.config_status_label.configure(text=message)
