from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from src.gui.stage_cards_v2.validation_result import ValidationResult


class BaseStageCardV2(ttk.Frame):
    """Base class for V2 stage cards with shared header and validation area."""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        description: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, style="Card.TFrame", padding=6, **kwargs)

        self._title = title
        self._description = description
        self._build_header()
        self._build_body_container()
        self._build_validation_area()

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 4))
        self.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(header, text=self._title, style="Heading.TLabel")
        self.title_label.pack(side="left")

        if self._description:
            self.description_label = ttk.Label(
                header,
                text=self._description,
                style="Muted.TLabel",
                wraplength=420,
                justify="left",
            )
            self.description_label.pack(side="left", padx=(8, 0))

    def _build_body_container(self) -> None:
        body = ttk.Frame(self, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.rowconfigure(1, weight=1)
        self.body_frame = body
        self._build_body(body)

    def _build_validation_area(self) -> None:
        val_frame = ttk.Frame(self, style="Card.TFrame")
        val_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.validation_label = ttk.Label(val_frame, text="", style="Muted.TLabel")
        self.validation_label.pack(side="left")

    # --- Hooks for subclasses -------------------------------------------------
    def _build_body(self, parent: ttk.Frame) -> None:
        raise NotImplementedError

    def show_validation_result(self, result: ValidationResult) -> None:
        message = result.message or ""
        self.validation_label.config(text=message)


__all__ = ["BaseStageCardV2"]
