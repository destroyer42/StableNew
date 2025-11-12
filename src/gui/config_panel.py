"""
ConfigPanel - UI component for configuration management with tabs.

This panel encapsulates all configuration UI and provides a clean API for
getting/setting configuration and validation.
"""

import logging
import tkinter as tk
from collections.abc import Iterable
from tkinter import ttk
from typing import Any

from .adetailer_config_panel import ADetailerConfigPanel

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

        # Widget dictionaries for enabling/disabling and list updates
        self.txt2img_widgets: dict[str, tk.Widget] = {}
        self.img2img_widgets: dict[str, tk.Widget] = {}
        self.upscale_widgets: dict[str, tk.Widget] = {}
        self.adetailer_panel: ADetailerConfigPanel | None = None

        # Face restoration widgets (for show/hide)
        self.face_restoration_widgets: list[tk.Widget] = []
        self._scheduler_options = [
            "Normal",
            "Karras",
            "Exponential",
            "Polyexponential",
            "SGM Uniform",
            "Simple",
            "DDIM Uniform",
            "Beta",
            "Linear",
            "Cosine",
        ]

        # Build UI
        self._build_ui()

    def _normalize_scheduler_value(self, value: str | None) -> str:
        mapping = {
            "normal": "Normal",
            "karras": "Karras",
            "exponential": "Exponential",
            "polyexponential": "Polyexponential",
            "sgm_uniform": "SGM Uniform",
            "sgm uniform": "SGM Uniform",
            "simple": "Simple",
            "ddim_uniform": "DDIM Uniform",
            "ddim uniform": "DDIM Uniform",
            "beta": "Beta",
            "linear": "Linear",
            "cosine": "Cosine",
        }
        if not value:
            return "Normal"
        normalized = str(value).strip()
        return mapping.get(normalized.lower(), normalized)

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
        self._build_adetailer_tab()
        self._build_upscale_tab()
        self._build_api_tab()

        # Add buttons at bottom
        self._build_action_buttons()
        # Create inline save/apply indicator next to Save button
        try:
            self._ensure_save_indicator()
        except Exception:
            pass

        # Track changes and mark as Apply when any field changes
        try:
            self._attach_change_traces()
        except Exception:
            pass

    def _build_txt2img_tab(self):
        """Build txt2img configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🎨 txt2img")

        toggle_var = getattr(self.coordinator, "txt2img_enabled", None)
        self._add_stage_toggle(tab, "Enable txt2img stage", toggle_var)
        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(0, 5))

        container = ttk.Frame(tab, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
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
        self.txt2img_vars["scheduler"] = tk.StringVar(value="Normal")
        self.txt2img_vars["seed"] = tk.IntVar(value=-1)
        self.txt2img_vars["clip_skip"] = tk.IntVar(value=2)
        self.txt2img_vars["model"] = tk.StringVar(value="")
        self.txt2img_vars["vae"] = tk.StringVar(value="")
        self.txt2img_vars["negative_prompt"] = tk.StringVar(value="")
        self.txt2img_vars["hypernetwork"] = tk.StringVar(value=self._get_hypernetwork_options()[0])
        self.txt2img_vars["hypernetwork_strength"] = tk.DoubleVar(value=1.0)

        # Hires fix
        self.txt2img_vars["enable_hr"] = tk.BooleanVar(value=False)
        self.txt2img_vars["hr_scale"] = tk.DoubleVar(value=2.0)
        self.txt2img_vars["hr_upscaler"] = tk.StringVar(value="Latent")
        self.txt2img_vars["hr_sampler_name"] = tk.StringVar(value="")
        self.txt2img_vars["denoising_strength"] = tk.DoubleVar(value=0.7)
        self.txt2img_vars["hires_steps"] = tk.IntVar(value=0)

        # Face restoration
        self.txt2img_vars["face_restoration_enabled"] = tk.BooleanVar(value=False)
        self.txt2img_vars["face_restoration_model"] = tk.StringVar(value="GFPGAN")
        self.txt2img_vars["face_restoration_weight"] = tk.DoubleVar(value=0.5)

        # Refiner (SDXL)
        self.txt2img_vars["refiner_checkpoint"] = tk.StringVar(value="None")
        self.txt2img_vars["refiner_switch_at"] = tk.DoubleVar(value=0.8)
        self.txt2img_vars["refiner_switch_steps"] = tk.IntVar(value=0)

        basic_frame = ttk.LabelFrame(scrollable_frame, text="Basic Settings", padding=10)
        basic_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(basic_frame, text="Steps:").grid(row=row, column=0, sticky=tk.W, pady=2)
        steps_spin = ttk.Spinbox(
            basic_frame, from_=1, to=150, textvariable=self.txt2img_vars["steps"], width=15
        )
        steps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["steps"] = steps_spin
        row += 1

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
            width=18,  # widened for readability
        )
        sampler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["sampler_name"] = sampler_combo
        row += 1

        ttk.Label(sampler_frame, text="Scheduler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        scheduler_combo = ttk.Combobox(
            sampler_frame,
            textvariable=self.txt2img_vars["scheduler"],
            values=self._scheduler_options,
            state="readonly",
            width=18,  # widened for readability
        )
        scheduler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["scheduler"] = scheduler_combo
        row += 1

        ttk.Label(sampler_frame, text="Model:").grid(row=row, column=0, sticky=tk.W, pady=2)
        model_combo = ttk.Combobox(
            sampler_frame,
            textvariable=self.txt2img_vars["model"],
            values=[],
            state="readonly",
            width=40,  # widened for long model names
        )
        model_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["model"] = model_combo
        row += 1

        ttk.Label(sampler_frame, text="VAE:").grid(row=row, column=0, sticky=tk.W, pady=2)
        vae_combo = ttk.Combobox(
            sampler_frame,
            textvariable=self.txt2img_vars["vae"],
            values=[],
            state="readonly",
            width=40,  # widened for long VAE names
        )
        vae_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["vae"] = vae_combo
        row += 1

        self._build_hypernetwork_section(scrollable_frame, self.txt2img_vars, "txt2img")

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

        ttk.Label(hires_frame, text="Upscaler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        hr_upscaler_combo = ttk.Combobox(
            hires_frame,
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
                "ESRGAN_4x",
                "LDSR",
                "R-ESRGAN 4x+",
                "R-ESRGAN 4x+ Anime6B",
                "ScuNET GAN",
                "ScuNET PSNR",
                "SwinIR 4x",
            ],
            state="readonly",
            width=25,
        )
        hr_upscaler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["hr_upscaler"] = hr_upscaler_combo
        row += 1

        ttk.Label(hires_frame, text="Hires Sampler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        hr_sampler_combo = ttk.Combobox(
            hires_frame,
            textvariable=self.txt2img_vars["hr_sampler_name"],
            values=["", "Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "LMS", "Heun"],
            state="readonly",
            width=25,
        )
        hr_sampler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["hr_sampler_name"] = hr_sampler_combo
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
        face_model_label = ttk.Label(face_frame, text="Model:")
        face_model_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        face_model_combo = ttk.Combobox(
            face_frame,
            textvariable=self.txt2img_vars["face_restoration_model"],
            values=["GFPGAN", "CodeFormer"],
            state="readonly",
            width=13,
        )
        face_model_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.face_restoration_widgets.extend([face_model_label, face_model_combo])
        face_model_label.grid_remove()
        face_model_combo.grid_remove()  # Hide initially
        row += 1

        face_weight_label = ttk.Label(face_frame, text="Weight:")
        face_weight_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        face_weight_spin = ttk.Spinbox(
            face_frame,
            from_=0.0,
            to=1.0,
            increment=0.1,
            textvariable=self.txt2img_vars["face_restoration_weight"],
            width=15,
        )
        face_weight_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.face_restoration_widgets.extend([face_weight_label, face_weight_spin])
        face_weight_label.grid_remove()
        face_weight_spin.grid_remove()  # Hide initially
        row += 1

        # Refiner section (SDXL)
        refiner_frame = ttk.LabelFrame(scrollable_frame, text="🎨 Refiner (SDXL)", padding=10)
        refiner_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        ttk.Label(refiner_frame, text="Refiner Model:").grid(row=row, column=0, sticky=tk.W, pady=2)
        refiner_combo = ttk.Combobox(
            refiner_frame,
            textvariable=self.txt2img_vars["refiner_checkpoint"],
            values=["None"],
            state="readonly",
            width=25,
        )
        refiner_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["refiner_checkpoint"] = refiner_combo
        row += 1

        ttk.Label(refiner_frame, text="Switch ratio:").grid(row=row, column=0, sticky=tk.W, pady=2)
        refiner_switch_spin = ttk.Spinbox(
            refiner_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            textvariable=self.txt2img_vars["refiner_switch_at"],
            width=10,
        )
        refiner_switch_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["refiner_switch_at"] = refiner_switch_spin
        row += 1

        ttk.Label(refiner_frame, text="Switch step (abs):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        refiner_steps_spin = ttk.Spinbox(
            refiner_frame,
            from_=0,
            to=999,
            increment=1,
            textvariable=self.txt2img_vars["refiner_switch_steps"],
            width=10,
        )
        refiner_steps_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.txt2img_widgets["refiner_switch_steps"] = refiner_steps_spin
        row += 1

        # Live computed mapping label
        self.refiner_mapping_label = ttk.Label(
            refiner_frame, text="", font=("Segoe UI", 8), foreground="#888888"
        )
        self.refiner_mapping_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1

        # Helper text for refiner
        refiner_help = ttk.Label(
            refiner_frame,
            text="💡 Set either ratio or absolute step (ratio ignored if step > 0)",
            font=("Segoe UI", 8),
            foreground="#888888",
        )
        refiner_help.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=2)

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

        toggle_var = getattr(self.coordinator, "img2img_enabled", None)
        self._add_stage_toggle(tab, "Enable img2img stage", toggle_var)
        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(0, 5))

        container = ttk.Frame(tab, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="Dark.TFrame")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initialize variables
        self.img2img_vars["steps"] = tk.IntVar(value=15)
        self.img2img_vars["denoising_strength"] = tk.DoubleVar(value=0.3)
        self.img2img_vars["cfg_scale"] = tk.DoubleVar(value=7.0)
        self.img2img_vars["sampler_name"] = tk.StringVar(value="Euler a")
        self.img2img_vars["scheduler"] = tk.StringVar(value="Normal")
        self.img2img_vars["seed"] = tk.IntVar(value=-1)
        self.img2img_vars["clip_skip"] = tk.IntVar(value=2)
        self.img2img_vars["model"] = tk.StringVar(value="")
        self.img2img_vars["vae"] = tk.StringVar(value="")
        self.img2img_vars["hypernetwork"] = tk.StringVar(value=self._get_hypernetwork_options()[0])
        self.img2img_vars["hypernetwork_strength"] = tk.DoubleVar(value=1.0)
        self.img2img_vars["prompt_adjust"] = tk.StringVar(value="")
        self.img2img_vars["negative_adjust"] = tk.StringVar(value="")

        # Basic settings
        basic_frame = ttk.LabelFrame(scrollable_frame, text="img2img Settings", padding=10)
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
        self.img2img_widgets["cfg_scale"] = cfg_spin
        row += 1

        ttk.Label(basic_frame, text="Sampler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_sampler_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.img2img_vars["sampler_name"],
            values=["Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "LMS", "Heun"],
            state="readonly",
            width=18,  # widened for readability
        )
        img_sampler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["sampler_name"] = img_sampler_combo
        row += 1

        ttk.Label(basic_frame, text="Scheduler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_scheduler_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.img2img_vars["scheduler"],
            values=self._scheduler_options,
            state="readonly",
            width=18,  # widened for readability
        )
        img_scheduler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["scheduler"] = img_scheduler_combo
        row += 1

        ttk.Label(basic_frame, text="Model:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_model_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.img2img_vars["model"],
            values=[],
            state="readonly",
            width=40,  # widened for long model names
        )
        img_model_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["model"] = img_model_combo
        row += 1

        ttk.Label(basic_frame, text="VAE:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_vae_combo = ttk.Combobox(
            basic_frame,
            textvariable=self.img2img_vars["vae"],
            values=[],
            state="readonly",
            width=40,  # widened for long VAE names
        )
        img_vae_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["vae"] = img_vae_combo
        row += 1

        self._build_hypernetwork_section(scrollable_frame, self.img2img_vars, "img2img")

        # Prompt adjustments (appended to positive prompt during img2img)
        ttk.Label(basic_frame, text="Prompt Adjust:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_prompt_adjust = ttk.Entry(
            basic_frame,
            textvariable=self.img2img_vars["prompt_adjust"],
            width=60,
        )
        img_prompt_adjust.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["prompt_adjust"] = img_prompt_adjust
        row += 1

        # Negative adjustments
        ttk.Label(basic_frame, text="Negative Adjust:").grid(row=row, column=0, sticky=tk.W, pady=2)
        img_neg_adjust = ttk.Entry(
            basic_frame,
            textvariable=self.img2img_vars["negative_adjust"],
            width=60,
        )
        img_neg_adjust.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.img2img_widgets["negative_adjust"] = img_neg_adjust
        row += 1

    def _build_adetailer_tab(self):
        """Build ADetailer configuration tab inside the pipeline notebook."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🖌️ ADetailer")

        toggle_var = getattr(self.coordinator, "adetailer_enabled", None)
        self._add_stage_toggle(tab, "Enable ADetailer stage", toggle_var)

        container = ttk.Frame(tab, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.adetailer_panel = ADetailerConfigPanel(container)
        self.adetailer_panel.frame.configure(style="Dark.TFrame")
        self.adetailer_panel.frame.pack(fill=tk.BOTH, expand=True)

    def _build_upscale_tab(self):
        """Build upscale configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="📈 Upscale")

        toggle_var = getattr(self.coordinator, "upscale_enabled", None)
        self._add_stage_toggle(tab, "Enable upscale stage", toggle_var)
        ttk.Separator(tab, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(0, 5))

        container = ttk.Frame(tab, style="Dark.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        # Initialize variables
        self.upscale_vars["upscaler"] = tk.StringVar(value="R-ESRGAN 4x+")
        self.upscale_vars["upscaling_resize"] = tk.DoubleVar(value=2.0)
        self.upscale_vars["upscale_mode"] = tk.StringVar(value="single")
        self.upscale_vars["steps"] = tk.IntVar(value=20)  # Used when Upscale runs via img2img
        self.upscale_vars["sampler_name"] = tk.StringVar(value="Euler a")
        self.upscale_vars["scheduler"] = tk.StringVar(value="Normal")
        self.upscale_vars["denoising_strength"] = tk.DoubleVar(value=0.2)
        self.upscale_vars["gfpgan_visibility"] = tk.DoubleVar(value=0.0)
        self.upscale_vars["codeformer_visibility"] = tk.DoubleVar(value=0.0)
        self.upscale_vars["codeformer_weight"] = tk.DoubleVar(value=0.5)

        # Settings
        settings_frame = ttk.LabelFrame(container, text="Upscale Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(settings_frame, text="Method:").grid(row=row, column=0, sticky=tk.W, pady=2)
        method_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.upscale_vars["upscale_mode"],
            values=["single", "img2img"],
            state="readonly",
            width=13,
        )
        method_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        method_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_upscale_mode_state())
        self.upscale_widgets["upscale_mode"] = method_combo
        row += 1
        ttk.Label(settings_frame, text="Upscaler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        upscaler_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.upscale_vars["upscaler"],
            values=["R-ESRGAN 4x+", "ESRGAN_4x", "Latent", "None"],
            state="readonly",
            width=30,
        )
        upscaler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["upscaler"] = upscaler_combo
        row += 1

        ttk.Label(settings_frame, text="Resize:").grid(row=row, column=0, sticky=tk.W, pady=2)
        resize_spin = ttk.Spinbox(
            settings_frame,
            from_=1.0,
            to=4.0,
            increment=0.1,
            textvariable=self.upscale_vars["upscaling_resize"],
            width=15,
        )
        resize_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["upscaling_resize"] = resize_spin
        row += 1

        ttk.Label(settings_frame, text="Steps (img2img):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        upscale_steps = ttk.Spinbox(
            settings_frame,
            from_=1,
            to=150,
            textvariable=self.upscale_vars["steps"],
            width=15,
        )
        upscale_steps.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["steps"] = upscale_steps
        row += 1

        ttk.Label(settings_frame, text="Denoise:").grid(row=row, column=0, sticky=tk.W, pady=2)
        upscale_denoise = ttk.Spinbox(
            settings_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.upscale_vars["denoising_strength"],
            width=15,
        )
        upscale_denoise.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["denoising_strength"] = upscale_denoise
        row += 1

        # Optional sampler/scheduler (used in img2img upscale mode)
        ttk.Label(settings_frame, text="Sampler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        up_sampler_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.upscale_vars["sampler_name"],
            values=["Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "LMS", "Heun"],
            state="readonly",
            width=15,
        )
        up_sampler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["sampler_name"] = up_sampler_combo
        row += 1

        ttk.Label(settings_frame, text="Scheduler:").grid(row=row, column=0, sticky=tk.W, pady=2)
        up_scheduler_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.upscale_vars["scheduler"],
            values=self._scheduler_options,
            state="readonly",
            width=15,
        )
        up_scheduler_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["scheduler"] = up_scheduler_combo
        row += 1

        ttk.Label(settings_frame, text="GFPGAN:").grid(row=row, column=0, sticky=tk.W, pady=2)
        gfpgan_spin = ttk.Spinbox(
            settings_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.upscale_vars["gfpgan_visibility"],
            width=15,
        )
        gfpgan_spin.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["gfpgan_visibility"] = gfpgan_spin
        row += 1

        ttk.Label(settings_frame, text="CodeFormer Vis:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        codeformer_vis = ttk.Spinbox(
            settings_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.upscale_vars["codeformer_visibility"],
            width=15,
        )
        codeformer_vis.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["codeformer_visibility"] = codeformer_vis
        row += 1

        ttk.Label(settings_frame, text="CodeFormer Weight:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        codeformer_weight = ttk.Spinbox(
            settings_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.upscale_vars["codeformer_weight"],
            width=15,
        )
        codeformer_weight.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.upscale_widgets["codeformer_weight"] = codeformer_weight
        row += 1

        # Initial enable/disable for img2img-specific controls
        self._apply_upscale_mode_state()

    def _apply_upscale_mode_state(self) -> None:
        """Enable/disable img2img-specific controls based on selected method."""
        try:
            mode = str(self.upscale_vars.get("upscale_mode").get()).lower()
        except Exception:
            mode = "single"
        use_img2img = mode == "img2img"
        for key in ("steps", "denoising_strength", "sampler_name", "scheduler"):
            widget = self.upscale_widgets.get(key)
            if widget is None:
                continue
            try:
                widget.configure(state=("normal" if use_img2img else "disabled"))
            except Exception:
                pass

    def _build_api_tab(self):
        """Build API configuration tab."""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="🔌 API")

        # Initialize variables
        self.api_vars["base_url"] = tk.StringVar(value="http://127.0.0.1:7860")
        self.api_vars["timeout"] = tk.IntVar(value=30)

        # Settings
        settings_frame = ttk.LabelFrame(tab, text="API Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=10)

        row = 0
        ttk.Label(settings_frame, text="API URL:").grid(row=row, column=0, sticky=tk.W, pady=2)
        api_entry = ttk.Entry(settings_frame, textvariable=self.api_vars["base_url"], width=30)
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
        # Keep a reference for inline indicators
        self._button_frame = button_frame
        # Keep a reference for later indicator placement
        self._button_frame = button_frame

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
            self.show_save_indicator("Saved")

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
                "scheduler": "Normal",
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
                "scheduler": "Normal",
                "seed": -1,
                "clip_skip": 2,
                "model": "",
                "vae": "",
                "prompt_adjust": "",
            },
            "upscale": {
                "upscaler": "R-ESRGAN 4x+",
                "upscaling_resize": 2.0,
                "upscale_mode": "single",
                "steps": 20,
                "denoising_strength": 0.2,
                "gfpgan_visibility": 0.0,
                "codeformer_visibility": 0.0,
                "codeformer_weight": 0.5,
            },
            "api": {
                "base_url": "http://127.0.0.1:7860",
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

        # Map UI-only keys to API config keys
        try:
            # Map hires_steps spinbox to hr_second_pass_steps used by WebUI
            if "hires_steps" in config["txt2img"]:
                config["txt2img"]["hr_second_pass_steps"] = int(
                    config["txt2img"].get("hires_steps", 0)
                )
            # Pass through refiner absolute steps if provided (>0)
            if int(config["txt2img"].get("refiner_switch_steps", 0) or 0) > 0:
                # Keep as user-set; executor converts this to ratio
                config["txt2img"]["refiner_switch_steps"] = int(
                    config["txt2img"].get("refiner_switch_steps", 0)
                )
        except Exception:
            pass

        # Extract img2img config
        for key, var in self.img2img_vars.items():
            config["img2img"][key] = var.get()

        # Extract upscale config
        for key, var in self.upscale_vars.items():
            config["upscale"][key] = var.get()

        # Extract API config
        for key, var in self.api_vars.items():
            config["api"][key] = var.get()

        # Normalize scheduler casing before returning
        for section in ("txt2img", "img2img", "upscale"):
            sec = config.get(section)
            if isinstance(sec, dict) and "scheduler" in sec:
                try:
                    sec["scheduler"] = self._normalize_scheduler_value(sec.get("scheduler"))
                except Exception:
                    pass

        return config

    def _ensure_save_indicator(self) -> None:
        """Ensure the inline Save/Apply indicator is created next to buttons."""
        try:
            if hasattr(self, "_save_indicator") and self._save_indicator:
                return
            self._save_indicator_var = tk.StringVar(value="")
            self._save_indicator = ttk.Label(
                self._button_frame, textvariable=self._save_indicator_var, style="Dark.TLabel"
            )
            self._save_indicator.pack(side=tk.LEFT, padx=(8, 0))
        except Exception:
            pass

    def _add_stage_toggle(
        self, parent: tk.Widget, label: str, variable: tk.BooleanVar | None
    ) -> None:
        """Add a stage enable checkbox to the provided container."""
        if not isinstance(variable, tk.BooleanVar):
            return
        frame = ttk.Frame(parent, style="Dark.TFrame")
        frame.pack(fill=tk.X, padx=10, pady=(5, 4))
        ttk.Checkbutton(
            frame,
            text=label,
            variable=variable,
            style="Dark.TCheckbutton",
        ).pack(anchor=tk.W)

    def _build_hypernetwork_section(
        self, parent: tk.Widget, var_dict: dict[str, tk.Variable], stage_name: str
    ) -> None:
        """Shared hypernetwork dropdown + strength slider."""
        options = self._get_hypernetwork_options()
        if "hypernetwork" not in var_dict:
            var_dict["hypernetwork"] = tk.StringVar(value=options[0])
        if "hypernetwork_strength" not in var_dict:
            var_dict["hypernetwork_strength"] = tk.DoubleVar(value=1.0)

        frame = ttk.LabelFrame(parent, text="Hypernetwork", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Hypernetwork:").grid(row=0, column=0, sticky=tk.W, pady=2)
        combo = ttk.Combobox(
            frame,
            textvariable=var_dict["hypernetwork"],
            values=options,
            state="readonly",
            width=25,
        )
        combo.grid(row=0, column=1, sticky=tk.W, pady=2)

        widget_store = {
            "txt2img": self.txt2img_widgets,
            "img2img": self.img2img_widgets,
        }.get(stage_name)
        if widget_store is not None:
            widget_store["hypernetwork"] = combo

        ttk.Label(frame, text="Strength:").grid(row=1, column=0, sticky=tk.W, pady=2)
        value_label = ttk.Label(frame, text=f"{var_dict['hypernetwork_strength'].get():.2f}")
        value_label.grid(row=1, column=2, sticky=tk.W, padx=(6, 0))
        slider = ttk.Scale(
            frame,
            from_=0.0,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=var_dict["hypernetwork_strength"],
            length=180,
        )
        slider.grid(row=1, column=1, sticky=tk.W, pady=2)

        def _sync_label(*_):
            value_label.config(text=f"{var_dict['hypernetwork_strength'].get():.2f}")

        var_dict["hypernetwork_strength"].trace_add("write", lambda *_: _sync_label())

    def _get_hypernetwork_options(self) -> list[str]:
        """Fetch available hypernetworks from the coordinator/pipeline."""
        options: list[str] = []
        coordinator = getattr(self, "coordinator", None)
        if coordinator is not None:
            possible = []
            for attr in ("available_hypernetworks", "hypernetworks"):
                value = getattr(coordinator, attr, None)
                if isinstance(value, (list, tuple, set)):
                    possible.extend(value)
            if possible:
                options = sorted({str(item) for item in possible if item})
        return options or ["None"]

    def show_save_indicator(self, text: str = "Saved", duration_ms: int = 2000) -> None:
        """Show a transient indicator next to the Save button with color coding."""
        try:
            self._ensure_save_indicator()
            # Colorize: green for Saved, orange for Apply/others
            color = "#00c853" if (text or "").lower() == "saved" else "#ffa500"
            try:
                self._save_indicator.configure(foreground=color)
            except Exception:
                pass
            self._save_indicator_var.set(text)
            if duration_ms and (text or "").lower() == "saved":
                self.after(duration_ms, lambda: self._save_indicator_var.set(""))
        except Exception:
            pass

    # (Old _attach_change_traces removed; see enhanced version later in file)

    def _mark_unsaved(self, *args) -> None:
        try:
            # Show Apply (orange)
            self.show_save_indicator("Apply", duration_ms=0)
            # Auto-apply when the coordinator enables it
            auto = False
            try:
                auto = bool(self.coordinator.auto_apply_var.get())
            except Exception:
                auto = bool(getattr(self.coordinator, "auto_apply_enabled", False))
            if auto and hasattr(self.coordinator, "on_config_save"):
                self.coordinator.on_config_save(self.get_config())
                self.show_save_indicator("Saved")
        except Exception:
            pass

    def set_config(self, config: dict[str, Any]) -> None:
        """
        Set configuration in UI.

        Args:
            config: Dictionary containing configuration values
        """
        import os

        diag = os.environ.get("STABLENEW_DIAG", "").lower() in {"1", "true", "yes"}
        if diag:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("[DIAG] ConfigPanel.set_config: start", extra={"flush": True})
        # Set txt2img config
        if "txt2img" in config:
            if diag:
                logger.info(
                    "[DIAG] ConfigPanel.set_config: processing txt2img", extra={"flush": True}
                )
            # Pre-map hr_second_pass_steps to hires_steps for the UI control
            txt_cfg = dict(config["txt2img"])  # shallow copy
            try:
                if "hr_second_pass_steps" in txt_cfg and "hires_steps" in self.txt2img_vars:
                    self.txt2img_vars["hires_steps"].set(
                        int(txt_cfg.get("hr_second_pass_steps") or 0)
                    )
            except Exception:
                pass
            for key, value in txt_cfg.items():
                if key in self.txt2img_vars:
                    if key == "scheduler":
                        value = self._normalize_scheduler_value(value)
                    self.txt2img_vars[key].set(value)
            # Sync mapping label after setting fields
            try:
                self._update_refiner_mapping_label()
            except Exception:
                pass
            if diag:
                logger.info("[DIAG] ConfigPanel.set_config: txt2img done", extra={"flush": True})

        # Set img2img config
        if "img2img" in config:
            if diag:
                logger.info(
                    "[DIAG] ConfigPanel.set_config: processing img2img", extra={"flush": True}
                )
            for key, value in config["img2img"].items():
                if key in self.img2img_vars:
                    if key == "scheduler":
                        value = self._normalize_scheduler_value(value)
                    self.img2img_vars[key].set(value)
            if diag:
                logger.info("[DIAG] ConfigPanel.set_config: img2img done", extra={"flush": True})

        # Set upscale config
        if "upscale" in config:
            if diag:
                logger.info(
                    "[DIAG] ConfigPanel.set_config: processing upscale", extra={"flush": True}
                )
            for key, value in config["upscale"].items():
                if key in self.upscale_vars:
                    if key == "scheduler":
                        value = self._normalize_scheduler_value(value)
                    self.upscale_vars[key].set(value)
            if diag:
                logger.info("[DIAG] ConfigPanel.set_config: upscale done", extra={"flush": True})

        # Set API config
        if "api" in config:
            if diag:
                logger.info("[DIAG] ConfigPanel.set_config: processing api", extra={"flush": True})
            for key, value in config["api"].items():
                if key in self.api_vars:
                    self.api_vars[key].set(value)
            if diag:
                logger.info("[DIAG] ConfigPanel.set_config: api done", extra={"flush": True})

        # Update face restoration visibility
        if diag:
            logger.info(
                "[DIAG] ConfigPanel.set_config: calling _toggle_face_restoration",
                extra={"flush": True},
            )
        self._toggle_face_restoration()
        if diag:
            logger.info(
                "[DIAG] ConfigPanel.set_config: calling _update_refiner_mapping_label",
                extra={"flush": True},
            )
        try:
            self._update_refiner_mapping_label()
        except Exception:
            pass
        if diag:
            logger.info("[DIAG] ConfigPanel.set_config: end", extra={"flush": True})

    def _update_refiner_mapping_label(self):
        """Compute and display the effective switch mapping."""
        if not hasattr(self, "refiner_mapping_label"):
            return
        try:
            steps = int(self.txt2img_vars.get("steps").get())
        except Exception:
            steps = 0
        ratio = float(self.txt2img_vars.get("refiner_switch_at").get()) if steps else 0.0
        abs_step = int(self.txt2img_vars.get("refiner_switch_steps").get())
        if abs_step > 0 and steps > 0:
            # Show both representations
            computed_ratio = abs_step / float(steps)
            self.refiner_mapping_label.configure(
                text=f"🔀 Will switch at step {abs_step}/{steps} (ratio={computed_ratio:.3f})"
            )
        elif steps > 0 and 0 < ratio < 1:
            target_step = int(round(ratio * steps))
            self.refiner_mapping_label.configure(
                text=f"🔀 Ratio {ratio:.3f} => switch ≈ step {target_step}/{steps}"
            )
        else:
            self.refiner_mapping_label.configure(text="")

    def _attach_change_traces(self) -> None:
        """Attach variable traces to flag unsaved changes (extended to update refiner mapping)."""

        def attach(d: dict[str, tk.Variable]):
            for k, v in d.items():
                try:

                    def _cb(*_):
                        self._mark_unsaved()
                        if k in {"refiner_switch_at", "refiner_switch_steps", "steps"}:
                            self._update_refiner_mapping_label()

                    v.trace_add("write", _cb)
                except Exception:
                    try:
                        v.trace("w", _cb)  # type: ignore[attr-defined]
                    except Exception:
                        pass

        for var_dict in (self.txt2img_vars, self.img2img_vars, self.upscale_vars, self.api_vars):
            attach(var_dict)

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

    # ------------------------------------------------------------------
    # Option update helpers for integration with main window
    # ------------------------------------------------------------------

    def _set_combobox_values(self, widget: tk.Widget | None, values: Iterable[str]) -> None:
        if widget is None:
            return
        try:
            widget["values"] = tuple(values)
        except (AttributeError, tk.TclError) as e:
            logger.warning(
                "Failed to set combobox values on widget %s: %s",
                type(widget).__name__,
                e,
            )

    def set_model_options(self, models: Iterable[str]) -> None:
        """Update base model selections for txt2img/img2img and refiner."""
        self._set_combobox_values(self.txt2img_widgets.get("model"), models)
        self._set_combobox_values(self.img2img_widgets.get("model"), models)

        # Also populate refiner dropdown with models (prepend "None" option)
        refiner_models = ["None"]
        for m in models or []:
            if m and str(m).strip():
                refiner_models.append(str(m).strip())
        self._set_combobox_values(self.txt2img_widgets.get("refiner_checkpoint"), refiner_models)

    def set_vae_options(self, vae_models: Iterable[str]) -> None:
        """Update VAE selections for txt2img/img2img."""
        self._set_combobox_values(self.txt2img_widgets.get("vae"), vae_models)
        self._set_combobox_values(self.img2img_widgets.get("vae"), vae_models)

    def set_upscaler_options(self, upscalers: Iterable[str]) -> None:
        """Update upscaler list."""
        self._set_combobox_values(self.upscale_widgets.get("upscaler"), upscalers)

    def set_scheduler_options(self, schedulers: Iterable[str]) -> None:
        """Update scheduler dropdowns."""
        normalized = [self._normalize_scheduler_value(s) for s in schedulers or [] if s is not None]
        if not normalized:
            normalized = list(self._scheduler_options)
        self._set_combobox_values(self.txt2img_widgets.get("scheduler"), normalized)
        self._set_combobox_values(self.img2img_widgets.get("scheduler"), normalized)
        self._set_combobox_values(self.upscale_widgets.get("scheduler"), normalized)

    def set_hypernetwork_options(self, hypernets: Iterable[str]) -> None:
        """Update hypernetwork dropdowns for txt2img/img2img."""

        cleaned: list[str] = []
        for entry in hypernets or []:
            if entry is None:
                continue
            text = str(entry).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if "None" not in cleaned:
            cleaned.insert(0, "None")
        self._set_combobox_values(self.txt2img_widgets.get("hypernetwork"), cleaned)
        self._set_combobox_values(self.img2img_widgets.get("hypernetwork"), cleaned)
