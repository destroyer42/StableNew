"""Output settings panel for GUI V2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.config import app_config
from src.gui import theme as theme_mod


class OutputSettingsPanelV2(ttk.Frame):
    """Expose output directory/profile, filename pattern, batch size, image format, seed mode."""

    FORMATS = ("png", "jpg", "webp")
    SEED_MODES = ("fixed", "increment", "random")

    def __init__(self, master: tk.Misc, *, theme=None) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD)
        self.theme = theme or theme_mod

        header_style = getattr(self.theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        ttk.Label(self, text="Output Settings", style=header_style).pack(anchor=tk.W, pady=(0, 6))

        self.output_dir_var = tk.StringVar(value=app_config.output_dir_default())
        self.filename_pattern_var = tk.StringVar(value=app_config.filename_pattern_default())
        self.image_format_var = tk.StringVar(value=app_config.image_format_default())
        self.batch_size_var = tk.StringVar(value=str(app_config.batch_size_default()))
        self.seed_mode_var = tk.StringVar(value=app_config.seed_mode_default())

        self._build_row("Output Dir", ttk.Entry(self, textvariable=self.output_dir_var))
        self._build_row("Filename", ttk.Entry(self, textvariable=self.filename_pattern_var))
        self._build_row(
            "Format",
            ttk.Combobox(self, textvariable=self.image_format_var, values=self.FORMATS, state="readonly", width=8),
        )
        self._build_row(
            "Batch Size",
            ttk.Spinbox(self, from_=1, to=99, increment=1, textvariable=self.batch_size_var, width=6),
        )
        self._build_row(
            "Seed Mode",
            ttk.Combobox(self, textvariable=self.seed_mode_var, values=self.SEED_MODES, state="readonly", width=10),
        )

    def _build_row(self, label: str, widget: tk.Widget) -> None:
        row = ttk.Frame(self, style=getattr(self.theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE))
        row.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        ttk.Label(row, text=label, style=getattr(self.theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE)).pack(
            side=tk.LEFT
        )
        widget.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def get_output_overrides(self) -> dict[str, object]:
        return {
            "output_dir": self.output_dir_var.get().strip(),
            "filename_pattern": self.filename_pattern_var.get().strip(),
            "image_format": self.image_format_var.get().strip(),
            "batch_size": self._safe_int(self.batch_size_var.get(), app_config.batch_size_default()),
            "seed_mode": self.seed_mode_var.get().strip(),
        }

    def apply_from_overrides(self, overrides: dict[str, object]) -> None:
        if not overrides:
            return
        self.output_dir_var.set(str(overrides.get("output_dir", self.output_dir_var.get())))
        self.filename_pattern_var.set(str(overrides.get("filename_pattern", self.filename_pattern_var.get())))
        fmt = overrides.get("image_format")
        if fmt:
            self.image_format_var.set(str(fmt))
        batch = overrides.get("batch_size")
        if batch is not None:
            try:
                self.batch_size_var.set(str(int(batch)))
            except Exception:
                pass
        seed = overrides.get("seed_mode")
        if seed:
            self.seed_mode_var.set(str(seed))

    @staticmethod
    def _safe_int(value: object, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default


__all__ = ["OutputSettingsPanelV2"]
