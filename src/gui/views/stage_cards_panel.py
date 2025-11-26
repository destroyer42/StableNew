from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class _StageCard(ttk.Frame):
    """Minimal stage card scaffold with hide/show toggle."""

    def __init__(self, master: tk.Misc, title: str, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=title).grid(row=0, column=0, sticky="w")
        self.toggle_btn = ttk.Button(header, text="Hide", width=8, command=self._toggle_body)
        self.toggle_btn.grid(row=0, column=1, sticky="e")

        self.body = ttk.Frame(self, padding=6, style="Panel.TFrame")
        self.body.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        ttk.Label(self.body, text=f"{title} Content (Scaffold)").pack(anchor="w")
        self._visible = True

    def _toggle_body(self) -> None:
        if self._visible:
            self.body.grid_remove()
            self.toggle_btn.config(text="Show")
        else:
            self.body.grid()
            self.toggle_btn.config(text="Hide")
        self._visible = not self._visible


class StageCardsPanel(ttk.Frame):
    """Container for pipeline stage cards (UI scaffold only)."""

    def __init__(self, master: tk.Misc, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.columnconfigure(0, weight=1)

        self.txt2img_card = _StageCard(self, title="txt2img Stage")
        self.img2img_card = _StageCard(self, title="img2img / ADetailer Stage")
        self.upscale_card = _StageCard(self, title="Upscale Stage")

        self.txt2img_card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        self.img2img_card.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        self.upscale_card.grid(row=2, column=0, sticky="nsew")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

    def set_stage_enabled(self, stage: str, enabled: bool) -> None:
        mapping = {
            "txt2img": self.txt2img_card,
            "img2img": self.img2img_card,
            "upscale": self.upscale_card,
        }
        card = mapping.get(stage)
        if not card:
            return
        if enabled and not card._visible:
            card._toggle_body()
        elif not enabled and card._visible:
            card._toggle_body()
