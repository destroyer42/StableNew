"""txt2img stage card for PipelinePanelV2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod


class Txt2ImgStageCard(ttk.Frame):
    """Stage card managing txt2img-related fields."""

    FIELD_NAMES = [
        "model",
        "vae",
        "sampler_name",
        "scheduler",
        "steps",
        "cfg_scale",
        "width",
        "height",
    ]

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.theme = theme

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="txt2img Settings", style=header_style)
        self.header_label.pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self._vars: dict[str, tk.StringVar] = {}
        self._widgets: dict[str, ttk.Widget] = {}
        self._on_change = None

        for idx, field in enumerate(self.FIELD_NAMES):
            var = tk.StringVar()
            self._vars[field] = var
            if field in {"steps", "width", "height"}:
                widget = self._add_spinbox(self.body, field, var, idx, from_=1, to=8192)
            elif field == "cfg_scale":
                widget = self._add_spinbox(
                    self.body, field, var, idx, from_=0.0, to=30.0, increment=0.5
                )
            else:
                widget = self._add_entry(self.body, field, var, idx)
            self._widgets[field] = widget

    def _add_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label.title(), style="Dark.TLabel").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        entry = ttk.Entry(parent, textvariable=variable, width=28)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        parent.columnconfigure(1, weight=1)
        return entry

    def _add_spinbox(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        *,
        from_: float,
        to: float,
        increment: float = 1.0,
    ) -> ttk.Spinbox:
        ttk.Label(parent, text=label.title(), style="Dark.TLabel").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        spin = ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=from_,
            to=to,
            increment=increment,
            width=10,
        )
        spin.grid(row=row, column=1, sticky="ew", pady=2)
        return spin

    def load_from_config(self, config: dict | None) -> None:
        section = self._get_section(config)
        for field in self.FIELD_NAMES:
            self._vars[field].set(self._coerce_str(section.get(field)))

    def to_config_dict(self) -> dict:
        section: dict[str, object] = {}
        for field in self.FIELD_NAMES:
            value = self._vars[field].get()
            if field in {"steps", "width", "height"}:
                converted = self._coerce_int(value)
            elif field == "cfg_scale":
                converted = self._coerce_float(value)
            else:
                converted = value.strip() if isinstance(value, str) else ""
                if not converted:
                    converted = None
            if converted not in (None, ""):
                section[field] = converted
        return {"txt2img": section} if section else {}

    def get_form_values(self) -> dict:
        return {field: self._vars[field].get() for field in self.FIELD_NAMES}

    def set_on_change(self, callback) -> None:
        self._on_change = callback
        for var in self._vars.values():
            var.trace_add("write", self._handle_var_change)

    def _handle_var_change(self, *_args) -> None:
        if self._on_change:
            self._on_change()

    @staticmethod
    def _get_section(config: dict | None) -> dict:
        if isinstance(config, dict):
            section = config.get("txt2img") or {}
            return section if isinstance(section, dict) else {}
        return {}

    @staticmethod
    def _coerce_str(value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        try:
            if value is None or str(value).strip() == "":
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        try:
            if value is None or str(value).strip() == "":
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
