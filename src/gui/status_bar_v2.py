"""Status bar scaffold for GUI v2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod


class StatusBarV2(ttk.Frame):
    """Status/ETA/progress container."""

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_SM, **kwargs)
        self.controller = controller
        self.theme = theme
        self._has_validation_error = False

        header_style = getattr(theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Status", style=header_style)
        self.header_label.pack(anchor=tk.W)

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(
            self.body,
            text="Idle",
            style=getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE),
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_bar = ttk.Progressbar(
            self.body,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
            length=150,
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.eta_label = ttk.Label(
            self.body,
            text="",
            style=getattr(theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE),
        )
        self.eta_label.pack(side=tk.LEFT, padx=10)

        self.set_idle()

    # Status helpers -------------------------------------------------

    def set_idle(self) -> None:
        if self._has_validation_error:
            return
        self.status_label.config(text="Idle")
        self.update_progress(0.0)
        self.update_eta(None)

    def set_running(self) -> None:
        if self._has_validation_error:
            return
        self.status_label.config(text="Running...")

    def set_completed(self) -> None:
        if self._has_validation_error:
            return
        self.status_label.config(text="Completed")

    def set_error(self, message: str | None = None) -> None:
        if self._has_validation_error:
            return
        text = "Error"
        if message:
            cleaned = str(message).strip()
            if cleaned:
                text = f"Error: {cleaned}"
        self.status_label.config(text=text)

    # Progress / ETA helpers -----------------------------------------

    def update_progress(self, fraction: float | None = None) -> None:
        if fraction is None:
            fraction = 0.0
        try:
            value = float(fraction)
        except (TypeError, ValueError):
            value = 0.0
        value = max(0.0, min(1.0, value))
        self.progress_bar["value"] = value * 100.0

    def update_eta(self, seconds: float | None = None) -> None:
        if seconds is None:
            self.eta_label.config(text="")
            return
        try:
            total_seconds = max(0.0, float(seconds))
        except (TypeError, ValueError):
            self.eta_label.config(text="")
            return
        mins = int(total_seconds // 60)
        secs = int(total_seconds % 60)
        self.eta_label.config(text=f"ETA: {mins:02d}:{secs:02d}")

    def set_validation_error(self, message: str) -> None:
        self._has_validation_error = True
        self.status_label.config(text=f"Config Error: {message}")
        self.update_progress(0.0)
        self.update_eta(None)

    def clear_validation_error(self) -> None:
        if not self._has_validation_error:
            return
        self._has_validation_error = False
        self.set_idle()
