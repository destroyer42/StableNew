"""Advanced Upscale stage card for V2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.stage_cards_v2.validation_result import ValidationResult


class AdvancedUpscaleStageCardV2(ttk.LabelFrame):
    panel_header = "Upscale Configuration"

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs: Any) -> None:
        super().__init__(master, text=self.panel_header, padding=6, **kwargs)
        self.controller = controller
        self.theme = theme

        self.upscaler_var = tk.StringVar()
        self.factor_var = tk.StringVar(value="2")
        self.tile_size_var = tk.StringVar(value="0")
        self.face_restore_var = tk.BooleanVar(value=False)

        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Upscaler").grid(row=0, column=0, sticky=tk.W, pady=1, padx=2)
        ttk.Entry(self, textvariable=self.upscaler_var, width=18).grid(
            row=0, column=1, sticky=tk.EW, pady=1, padx=2
        )

        ttk.Label(self, text="Factor").grid(row=1, column=0, sticky=tk.W, pady=1, padx=2)
        ttk.Entry(self, textvariable=self.factor_var, width=8).grid(
            row=1, column=1, sticky=tk.W, pady=1, padx=2
        )

        ttk.Label(self, text="Tile size").grid(row=2, column=0, sticky=tk.W, pady=1, padx=2)
        ttk.Entry(self, textvariable=self.tile_size_var, width=8).grid(
            row=2, column=1, sticky=tk.W, pady=1, padx=2
        )

        ttk.Checkbutton(self, text="Face restore", variable=self.face_restore_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=1, padx=2
        )
        self.columnconfigure(1, weight=1)

    def load_from_config(self, cfg: dict[str, Any]) -> None:
        section = (cfg or {}).get("upscale", {}) or {}
        self.upscaler_var.set(section.get("upscaler", ""))
        self.factor_var.set(str(section.get("upscaling_resize", section.get("upscale_factor", 2))))
        self.tile_size_var.set(str(section.get("tile_size", 0)))
        self.face_restore_var.set(bool(section.get("face_restore", False)))

    def to_config_dict(self) -> dict[str, Any]:
        return {
            "upscale": {
                "upscaler": self.upscaler_var.get().strip(),
                "upscaling_resize": int(self._safe_int(self.factor_var.get(), 2)),
                "tile_size": int(self._safe_int(self.tile_size_var.get(), 0)),
                "face_restore": bool(self.face_restore_var.get()),
            }
        }

    def validate(self) -> ValidationResult:
        try:
            factor = int(self.factor_var.get())
        except Exception:
            return ValidationResult(False, "Factor must be integer")
        if factor < 1:
            return ValidationResult(False, "Factor must be >= 1")
        return ValidationResult(True, None)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default
