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

        header_style = getattr(theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Status", style=header_style)
        self.header_label.pack(anchor=tk.W)

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(
            self.body,
            text="Ready",
            style=getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE),
        )
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_widget = ttk.Progressbar(
            self.body,
            orient=tk.HORIZONTAL,
            mode="determinate",
            length=150,
        )
        self.progress_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
