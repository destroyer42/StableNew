"""Advanced Img2Img stage card for V2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.stage_cards_v2.validation_result import ValidationResult


class AdvancedImg2ImgStageCardV2(ttk.LabelFrame):
    panel_header = "Img2Img Configuration"

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs: Any) -> None:
        super().__init__(master, text=self.panel_header, padding=6, **kwargs)
        self.controller = controller
        self.theme = theme

        self.sampler_var = tk.StringVar()
        self.cfg_var = tk.StringVar(value="7.0")
        self.denoise_var = tk.StringVar(value="0.3")
        self.width_var = tk.StringVar(value="")
        self.height_var = tk.StringVar(value="")
        self.mask_mode_var = tk.StringVar(value="none")

        self._build()

    def _build(self) -> None:
        fields = [
            ("Sampler", self.sampler_var),
            ("CFG", self.cfg_var),
            ("Denoise", self.denoise_var),
            ("Width", self.width_var),
            ("Height", self.height_var),
            ("Mask mode", self.mask_mode_var),
        ]
        for idx, (label, var) in enumerate(fields):
            ttk.Label(self, text=label).grid(row=idx, column=0, sticky=tk.W, pady=1, padx=2)
            entry = ttk.Entry(self, textvariable=var, width=18)
            entry.grid(row=idx, column=1, sticky=tk.EW, pady=1, padx=2)
        self.columnconfigure(1, weight=1)

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
