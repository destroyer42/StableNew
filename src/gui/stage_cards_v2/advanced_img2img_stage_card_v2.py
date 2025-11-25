"""Advanced Img2Img stage card for V2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.stage_cards_v2.base_stage_card_v2 import BaseStageCardV2
from src.gui.stage_cards_v2.components import SamplerSection, SeedSection
from src.gui.stage_cards_v2.validation_result import ValidationResult


class AdvancedImg2ImgStageCardV2(BaseStageCardV2):
    panel_header = "Img2Img Configuration"

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs: Any) -> None:
        self.controller = controller
        self.theme = theme
        super().__init__(master, title=self.panel_header, **kwargs)

    def _build_body(self, parent: ttk.Frame) -> None:
        # Core vars
        self.sampler_var = tk.StringVar()
        self.cfg_var = tk.StringVar(value="7.0")
        self.denoise_var = tk.StringVar(value="0.3")
        self.width_var = tk.StringVar(value="")
        self.height_var = tk.StringVar(value="")
        self.mask_mode_var = tk.StringVar(value="none")

        # Sampler/steps/cfg shared section (reuse cfg var)
        self.sampler_section = SamplerSection(parent)
        self.sampler_section.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.sampler_section.sampler_var = self.sampler_var  # type: ignore[assignment]
        self.sampler_section.cfg_var = self.cfg_var  # type: ignore[assignment]
        # Keep steps_var but we don't persist it; still watchable for consistency

        meta = ttk.Frame(parent, style="Panel.TFrame")
        meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(meta, text="Denoise", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Entry(meta, textvariable=self.denoise_var, width=10).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(meta, text="Mask mode", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Entry(meta, textvariable=self.mask_mode_var, width=12).grid(row=0, column=3, sticky="ew")

        ttk.Label(meta, text="Width", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.width_var, width=8).grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(meta, text="Height", style="Muted.TLabel").grid(row=1, column=2, sticky="w", pady=(6, 2))
        ttk.Entry(meta, textvariable=self.height_var, width=8).grid(row=1, column=3, sticky="ew")
        for col in range(4):
            meta.columnconfigure(col, weight=1 if col in (1, 3) else 0)

        self.seed_section = SeedSection(parent)
        self.seed_section.grid(row=2, column=0, sticky="ew")
        self.seed_var = self.seed_section.seed_var  # compatibility exposure

        for var in self.watchable_vars():
            try:
                var.trace_add("write", lambda *_: None)
            except Exception:
                pass

        parent.columnconfigure(0, weight=1)

    def load_from_config(self, cfg: dict[str, Any]) -> None:
        section = (cfg or {}).get("img2img", {}) or {}
        self.sampler_var.set(section.get("sampler_name", ""))
        self.cfg_var.set(str(section.get("cfg_scale", 7.0)))
        self.denoise_var.set(str(section.get("denoising_strength", 0.3)))
        self.width_var.set(str(section.get("width", "")))
        self.height_var.set(str(section.get("height", "")))
        self.mask_mode_var.set(str(section.get("mask_mode", "none")))

    def to_config_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sampler_name": self.sampler_var.get().strip(),
            "cfg_scale": float(self._safe_float(self.cfg_var.get(), 7.0)),
            "denoising_strength": float(self._safe_float(self.denoise_var.get(), 0.3)),
        }
        if self.width_var.get().strip():
            payload["width"] = int(self._safe_int(self.width_var.get(), 0))
        if self.height_var.get().strip():
            payload["height"] = int(self._safe_int(self.height_var.get(), 0))
        if self.mask_mode_var.get().strip():
            payload["mask_mode"] = self.mask_mode_var.get().strip()
        return {"img2img": payload}

    def validate(self) -> ValidationResult:
        try:
            denoise = float(self.denoise_var.get())
        except Exception:
            return ValidationResult(False, "Denoise must be numeric")
        if not 0.0 <= denoise <= 1.0:
            return ValidationResult(False, "Denoise must be between 0 and 1")
        return ValidationResult(True, None)

    def watchable_vars(self) -> list[tk.Variable]:
        return [
            self.sampler_var,
            self.cfg_var,
            self.denoise_var,
            self.width_var,
            self.height_var,
            self.mask_mode_var,
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
