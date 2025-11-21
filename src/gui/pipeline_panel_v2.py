"""Pipeline panel scaffold for GUI v2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod


class PipelinePanelV2(ttk.Frame):
    """Container for pipeline controls tied to txt2img config."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        controller=None,
        theme=None,
        config_manager=None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.theme = theme
        self.config_manager = config_manager

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Pipeline", style=header_style)
        self.header_label.pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self._build_txt2img_section(body_style)

    def _build_txt2img_section(self, body_style: str) -> None:
        section = ttk.LabelFrame(
            self.body,
            text="txt2img",
            style=body_style,
            padding=theme_mod.PADDING_MD,
        )
        section.pack(fill=tk.BOTH, expand=True)

        self.model_var = tk.StringVar()
        self.vae_var = tk.StringVar()
        self.sampler_var = tk.StringVar()
        self.scheduler_var = tk.StringVar()
        self.steps_var = tk.StringVar()
        self.cfg_scale_var = tk.StringVar()
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()

        row = 0
        self.model_entry = self._add_labeled_entry(section, "Model", self.model_var, row)
        row += 1
        self.vae_entry = self._add_labeled_entry(section, "VAE", self.vae_var, row)
        row += 1
        self.sampler_entry = self._add_labeled_entry(section, "Sampler", self.sampler_var, row)
        row += 1
        self.scheduler_entry = self._add_labeled_entry(section, "Scheduler", self.scheduler_var, row)
        row += 1
        self.steps_entry = self._add_spinbox(section, "Steps", self.steps_var, row, from_=1, to=200)
        row += 1
        self.cfg_scale_entry = self._add_spinbox(
            section, "CFG Scale", self.cfg_scale_var, row, from_=1, to=30, increment=0.5
        )
        row += 1
        self.width_entry = self._add_spinbox(section, "Width", self.width_var, row, from_=64, to=2048)
        row += 1
        self.height_entry = self._add_spinbox(section, "Height", self.height_var, row, from_=64, to=2048)

    def _add_labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        row: int,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label, style="Dark.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        entry = ttk.Entry(parent, textvariable=variable, width=28)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        parent.columnconfigure(1, weight=1)
        return entry

    def _add_spinbox(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        row: int,
        *,
        from_: float,
        to: float,
        increment: float = 1.0,
    ) -> ttk.Spinbox:
        ttk.Label(parent, text=label, style="Dark.TLabel").grid(row=row, column=0, sticky="w", pady=2)
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
        section = self._get_txt2img_section(config)
        self.model_var.set(self._coerce_str(section.get("model")))
        self.vae_var.set(self._coerce_str(section.get("vae")))
        self.sampler_var.set(self._coerce_str(section.get("sampler_name")))
        self.scheduler_var.set(self._coerce_str(section.get("scheduler")))
        self.steps_var.set(self._coerce_str(section.get("steps")))
        self.cfg_scale_var.set(self._coerce_str(section.get("cfg_scale")))
        self.width_var.set(self._coerce_str(section.get("width")))
        self.height_var.set(self._coerce_str(section.get("height")))

    def to_config_delta(self) -> dict:
        txt2img_delta: dict[str, object] = {}
        self._set_if_value(txt2img_delta, "model", self.model_var.get())
        self._set_if_value(txt2img_delta, "vae", self.vae_var.get())
        self._set_if_value(txt2img_delta, "sampler_name", self.sampler_var.get())
        self._set_if_value(txt2img_delta, "scheduler", self.scheduler_var.get())
        steps = self._coerce_int(self.steps_var.get())
        if steps is not None:
            txt2img_delta["steps"] = steps
        cfg_scale = self._coerce_float(self.cfg_scale_var.get())
        if cfg_scale is not None:
            txt2img_delta["cfg_scale"] = cfg_scale
        width = self._coerce_int(self.width_var.get())
        if width is not None:
            txt2img_delta["width"] = width
        height = self._coerce_int(self.height_var.get())
        if height is not None:
            txt2img_delta["height"] = height

        return {"txt2img": txt2img_delta} if txt2img_delta else {}

    @staticmethod
    def _get_txt2img_section(config: dict | None) -> dict:
        if not isinstance(config, dict):
            return {}
        section = config.get("txt2img") or {}
        return section if isinstance(section, dict) else {}

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

    @staticmethod
    def _set_if_value(target: dict, key: str, value: str) -> None:
        if value is not None:
            value = str(value).strip()
            if value:
                target[key] = value
