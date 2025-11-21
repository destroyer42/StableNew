"""ConfigPanel for Center Zone core settings."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from . import theme


class ConfigPanel(ttk.Frame):
    """Basic configuration controls for model/sampler/resolution/steps/CFG."""

    def __init__(
        self,
        master: tk.Misc,
        on_change: Callable[[str, Any], None] | None = None,
        *,
        coordinator: Any | None = None,
        style: str | None = None,
        **kwargs: Any,
    ) -> None:
        frame_style = style or theme.SURFACE_FRAME_STYLE
        super().__init__(master, padding=theme.PADDING_MD, style=frame_style, **kwargs)
        self.on_change = on_change
        self.coordinator = coordinator

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.model_var = tk.StringVar()
        self.sampler_var = tk.StringVar()
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.steps_var = tk.StringVar()
        self.cfg_var = tk.StringVar()

        # Legacy compatibility dictionaries expected by StableNewGUI
        self.txt2img_vars = {
            "model": self.model_var,
            "sampler_name": self.sampler_var,
            "width": self.width_var,
            "height": self.height_var,
            "steps": self.steps_var,
            "cfg_scale": self.cfg_var,
        }
        self.img2img_vars = {
            "model": tk.StringVar(),
            "sampler_name": tk.StringVar(),
        }
        self.upscale_vars = {
            "upscaler": tk.StringVar(),
        }
        self.api_vars = {"base_url": tk.StringVar()}
        self.txt2img_widgets: dict[str, tk.Widget] = {}
        self.upscale_widgets: dict[str, tk.Widget] = {}

        ttk.Label(self, text="Model", style=theme.STATUS_STRONG_LABEL_STYLE).grid(
            row=0, column=0, sticky="w", columnspan=2
        )
        self.model_combo = ttk.Combobox(
            self,
            textvariable=self.model_var,
            state="readonly",
        )
        self.model_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, theme.PADDING_MD))
        self.model_combo.bind("<<ComboboxSelected>>", self._handle_model_change)
        self.txt2img_widgets["model"] = self.model_combo

        ttk.Label(self, text="Sampler", style=theme.STATUS_STRONG_LABEL_STYLE).grid(
            row=2, column=0, sticky="w", columnspan=2
        )
        self.sampler_combo = ttk.Combobox(
            self,
            textvariable=self.sampler_var,
            state="readonly",
        )
        self.sampler_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, theme.PADDING_MD))
        self.sampler_combo.bind("<<ComboboxSelected>>", self._handle_sampler_change)
        self.txt2img_widgets["sampler_name"] = self.sampler_combo

        ttk.Label(self, text="Resolution", style=theme.STATUS_STRONG_LABEL_STYLE).grid(
            row=4, column=0, sticky="w", columnspan=2
        )
        width_entry = ttk.Entry(self, textvariable=self.width_var, width=8)
        height_entry = ttk.Entry(self, textvariable=self.height_var, width=8)
        width_entry.grid(row=5, column=0, sticky="ew", pady=(0, theme.PADDING_SM))
        height_entry.grid(row=5, column=1, sticky="ew", pady=(0, theme.PADDING_SM))
        width_entry.bind("<FocusOut>", self._handle_resolution_change)
        height_entry.bind("<FocusOut>", self._handle_resolution_change)
        self.txt2img_widgets["width"] = width_entry
        self.txt2img_widgets["height"] = height_entry

        ttk.Label(self, text="Steps", style=theme.STATUS_STRONG_LABEL_STYLE).grid(
            row=6, column=0, sticky="w"
        )
        ttk.Label(self, text="CFG", style=theme.STATUS_STRONG_LABEL_STYLE).grid(
            row=6, column=1, sticky="w"
        )

        steps_spin = ttk.Spinbox(
            self,
            from_=1,
            to=200,
            textvariable=self.steps_var,
            width=10,
            wrap=True,
        )
        cfg_spin = ttk.Spinbox(
            self,
            from_=1.0,
            to=30.0,
            increment=0.5,
            textvariable=self.cfg_var,
            width=10,
        )
        steps_spin.grid(row=7, column=0, sticky="ew", pady=(0, theme.PADDING_MD))
        cfg_spin.grid(row=7, column=1, sticky="ew", pady=(0, theme.PADDING_MD))
        steps_spin.bind("<FocusOut>", self._handle_steps_change)
        cfg_spin.bind("<FocusOut>", self._handle_cfg_change)
        self.txt2img_widgets["steps"] = steps_spin
        self.txt2img_widgets["cfg_scale"] = cfg_spin

        self.config_status_label = ttk.Label(self, text="", style=theme.STATUS_LABEL_STYLE)
        self.config_status_label.grid(row=8, column=0, columnspan=2, sticky="w")

    def refresh_from_controller(
        self,
        config: dict[str, Any],
        model_options: list[str],
        sampler_options: list[str],
    ) -> None:
        """Sync widget values with controller state and available options."""
        if model_options:
            self.model_combo["values"] = model_options
        if sampler_options:
            self.sampler_combo["values"] = sampler_options

        self.model_var.set(config.get("model", ""))
        self.sampler_var.set(config.get("sampler", ""))
        self.width_var.set(str(config.get("width", "")))
        self.height_var.set(str(config.get("height", "")))
        self.steps_var.set(str(config.get("steps", "")))
        self.cfg_var.set(str(config.get("cfg_scale", "")))

    def _handle_model_change(self, _event) -> None:
        self._notify_change("model", self.model_var.get())

    def _handle_sampler_change(self, _event) -> None:
        self._notify_change("sampler", self.sampler_var.get())

    def _handle_resolution_change(self, _event) -> None:
        self._notify_change("width", self.width_var.get())
        self._notify_change("height", self.height_var.get())

    def _handle_steps_change(self, _event) -> None:
        self._notify_change("steps", self.steps_var.get())

    def _handle_cfg_change(self, _event) -> None:
        self._notify_change("cfg_scale", self.cfg_var.get())

    def _notify_change(self, field: str, value: Any) -> None:
        if self.on_change:
            self.on_change(field, value)
