"""Advanced Txt2Img stage card for V2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.stage_cards_v2.base_stage_card_v2 import BaseStageCardV2
from src.gui.stage_cards_v2.components import SamplerSection, SeedSection
from src.gui.stage_cards_v2.validation_result import ValidationResult


class AdvancedTxt2ImgStageCardV2(BaseStageCardV2):
    panel_header = "Txt2Img Configuration"

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs: Any) -> None:
        self.controller = controller
        self.theme = theme
        self._on_change = None
        super().__init__(master, title=self.panel_header, **kwargs)

    def _build_body(self, parent: ttk.Frame) -> None:
        # Core vars
        self.model_var = tk.StringVar()
        self.vae_var = tk.StringVar()
        self.sampler_var = tk.StringVar()
        self.scheduler_var = tk.StringVar()
        self.steps_var = tk.StringVar(value="20")
        self.cfg_var = tk.StringVar(value="7.0")
        self.width_var = tk.StringVar(value="512")
        self.height_var = tk.StringVar(value="512")
        self.clip_skip_var = tk.StringVar(value="2")

        # Sampler/steps/cfg
        self.sampler_section = SamplerSection(parent)
        self.sampler_section.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        # Link primary sampler vars to section vars to preserve API
        self.sampler_section.sampler_var = self.sampler_var  # type: ignore[assignment]
        self.sampler_section.steps_var = self.steps_var  # type: ignore[assignment]
        self.sampler_section.cfg_var = self.cfg_var  # type: ignore[assignment]

        # Model/vae/scheduler/clip/size
        meta = ttk.Frame(parent, style="Panel.TFrame")
        meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(meta, text="Model", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Entry(meta, textvariable=self.model_var, width=18).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(meta, text="VAE", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(meta, textvariable=self.vae_var, width=18).grid(row=0, column=3, sticky="ew")

        ttk.Label(meta, text="Scheduler", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.scheduler_var, width=14).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(meta, text="Clip skip", style="Muted.TLabel").grid(row=1, column=2, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.clip_skip_var, width=6).grid(row=1, column=3, sticky="ew")

        ttk.Label(meta, text="Width", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.width_var, width=8).grid(row=2, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(meta, text="Height", style="Muted.TLabel").grid(row=2, column=2, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.height_var, width=8).grid(row=2, column=3, sticky="ew")
        for col in range(4):
            meta.columnconfigure(col, weight=1 if col in (1, 3) else 0)

        # Seed/randomize
        self.seed_section = SeedSection(parent)
        self.seed_section.grid(row=2, column=0, sticky="ew")
        self.seed_var = self.seed_section.seed_var  # exposed for compatibility

        for var in self.watchable_vars():
            try:
                var.trace_add("write", lambda *_: self._notify_change())
            except Exception:
                pass

        parent.columnconfigure(0, weight=1)

    def set_on_change(self, callback) -> None:
        self._on_change = callback

    def _notify_change(self) -> None:
        if self._on_change:
            try:
                self._on_change()
            except Exception:
                pass

    def load_from_config(self, cfg: dict[str, Any]) -> None:
        section = (cfg or {}).get("txt2img", {}) or {}
        self.model_var.set(section.get("model") or section.get("model_name", ""))
        self.vae_var.set(section.get("vae") or section.get("vae_name", ""))
        self.sampler_var.set(section.get("sampler_name", ""))
        self.scheduler_var.set(section.get("scheduler", ""))
        self.steps_var.set(str(section.get("steps", 20)))
        self.cfg_var.set(str(section.get("cfg_scale", 7.0)))
        self.width_var.set(str(section.get("width", 512)))
        self.height_var.set(str(section.get("height", 512)))
        self.clip_skip_var.set(str(section.get("clip_skip", 2)))

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "txt2img": {
                "model": self.model_var.get().strip(),
                "vae": self.vae_var.get().strip(),
                "sampler_name": self.sampler_var.get().strip(),
                "scheduler": self.scheduler_var.get().strip(),
                "steps": int(self._safe_int(self.steps_var.get(), 20)),
                "cfg_scale": float(self._safe_float(self.cfg_var.get(), 7.0)),
                "width": int(self._safe_int(self.width_var.get(), 512)),
                "height": int(self._safe_int(self.height_var.get(), 512)),
                "clip_skip": int(self._safe_int(self.clip_skip_var.get(), 2)),
            }
        }

    def validate(self) -> ValidationResult:
        try:
            steps = int(self.steps_var.get())
        except Exception:
            return ValidationResult(False, "Steps must be an integer", errors={"steps": "Steps must be an integer"})
        if steps < 1:
            return ValidationResult(False, "Steps must be >= 1", errors={"steps": "Steps must be >= 1"})
        try:
            cfg = float(self.cfg_var.get())
        except Exception:
            return ValidationResult(False, "CFG must be numeric", errors={"cfg_scale": "CFG must be numeric"})
        if not 1.0 <= cfg <= 30.0:
            return ValidationResult(False, "CFG must be between 1 and 30", errors={"cfg_scale": "CFG must be between 1 and 30"})
        for name, var in (("Width", self.width_var), ("Height", self.height_var)):
            try:
                val = int(var.get())
            except Exception:
                return ValidationResult(False, f"{name} must be integer", errors={name.lower(): f"{name} must be integer"})
            if val % 8 != 0:
                return ValidationResult(False, f"{name} must be divisible by 8", errors={name.lower(): f"{name} must be divisible by 8"})
        return ValidationResult(True, None)

    def watchable_vars(self) -> list[tk.Variable]:
        return [
            self.model_var,
            self.vae_var,
            self.sampler_var,
            self.scheduler_var,
            self.steps_var,
            self.cfg_var,
            self.width_var,
            self.height_var,
            self.clip_skip_var,
        ]

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default
