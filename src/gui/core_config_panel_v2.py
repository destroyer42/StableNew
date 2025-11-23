"""Core configuration panel for GUI V2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable

from src.config import app_config
from src.gui import theme as theme_mod
from src.gui.resolution_panel_v2 import ResolutionPanelV2


class CoreConfigPanelV2(ttk.Frame):
    """Expose core pipeline fields (model, sampler, steps, cfg, resolution)."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        theme=None,
        models: Iterable[str] | None = None,
        samplers: Iterable[str] | None = None,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD)

        self.theme = theme or theme_mod

        # Vars seeded from app_config defaults
        self.model_var = tk.StringVar(value=app_config.get_core_model_name())
        self.sampler_var = tk.StringVar(value=app_config.get_core_sampler_name())
        self.steps_var = tk.StringVar(value=str(app_config.get_core_steps()))
        self.cfg_var = tk.StringVar(value=str(app_config.get_core_cfg_scale()))

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        ttk.Label(self, text="Core Config", style=header_style).pack(anchor=tk.W, pady=(0, 6))

        self._build_field(
            label="Model",
            widget=self._build_combo(self.model_var, models or []),
        )
        self._build_field(
            label="Sampler",
            widget=self._build_combo(self.sampler_var, samplers or []),
        )
        self._build_field(
            label="Steps",
            widget=self._build_spin(self.steps_var, from_=1, to=200, increment=1),
        )
        self._build_field(
            label="CFG",
            widget=self._build_spin(self.cfg_var, from_=0.0, to=30.0, increment=0.5),
        )

        # Resolution sub-panel
        self.resolution_panel = ResolutionPanelV2(self, theme=self.theme)
        self.resolution_var = self.resolution_panel.preset_var
        self.resolution_panel.pack(fill=tk.X, pady=(theme_mod.PADDING_SM, 0))

    def _build_field(self, *, label: str, widget: tk.Widget) -> None:
        row = ttk.Frame(self, style=getattr(self.theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE))
        row.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        ttk.Label(row, text=label, style=getattr(self.theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE)).pack(
            side=tk.LEFT
        )
        widget.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _build_combo(self, variable: tk.StringVar, values: Iterable[str]) -> ttk.Combobox:
        combo = ttk.Combobox(
            self,
            textvariable=variable,
            values=tuple(values),
            state="normal",
        )
        return combo

    def _build_spin(self, variable: tk.StringVar, *, from_: float, to: float, increment: float) -> ttk.Spinbox:
        spin = ttk.Spinbox(
            self,
            from_=from_,
            to=to,
            increment=increment,
            textvariable=variable,
        )
        return spin

    def get_overrides(self) -> dict[str, object]:
        """Return current core config overrides as a dict suitable for GuiOverrides."""

        width, height = self.resolution_panel.get_resolution() if self.resolution_panel else (512, 512)
        preset = self.resolution_panel.get_preset_label() if self.resolution_panel else ""
        if preset:
            try:
                w_str, h_str = preset.lower().replace(" ", "").split("x", 1)
                width = int(w_str)
                height = int(h_str)
            except Exception:
                pass
        return {
            "model": self.model_var.get().strip(),
            "sampler": self.sampler_var.get().strip(),
            "steps": self._safe_int(self.steps_var.get(), 20),
            "cfg_scale": self._safe_float(self.cfg_var.get(), 7.0),
            "resolution_preset": preset,
            "width": width,
            "height": height,
        }

    def apply_from_overrides(self, overrides: dict[str, object]) -> None:
        if not overrides:
            return
        self.model_var.set(str(overrides.get("model", self.model_var.get())))
        self.sampler_var.set(str(overrides.get("sampler", self.sampler_var.get())))
        self.steps_var.set(str(overrides.get("steps", self.steps_var.get())))
        self.cfg_var.set(str(overrides.get("cfg_scale", self.cfg_var.get())))
        width = overrides.get("width")
        height = overrides.get("height")
        preset = overrides.get("resolution_preset")
        if self.resolution_panel:
            if preset:
                self.resolution_panel.apply_preset(str(preset))
            if width is not None and height is not None:
                try:
                    self.resolution_panel.set_resolution(int(width), int(height))
                except Exception:
                    pass

    @staticmethod
    def _safe_int(value: object, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: object, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default


__all__ = ["CoreConfigPanelV2"]
