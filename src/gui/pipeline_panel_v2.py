"""Pipeline panel composed of modular stage cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod
from .txt2img_stage_card import Txt2ImgStageCard
from .img2img_stage_card import Img2ImgStageCard
from .upscale_stage_card import UpscaleStageCard
from src.gui_v2.validation.pipeline_txt2img_validator import validate_txt2img, ValidationResult


class PipelinePanelV2(ttk.Frame):
    """Container for pipeline stage cards."""

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
        ttk.Label(self, text="Pipeline", style=header_style).pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self._txt2img_change_callback = None

        self.txt2img_card = Txt2ImgStageCard(self.body, controller=controller, theme=theme)
        self.txt2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.txt2img_card.set_on_change(self._handle_txt2img_change)

        self.img2img_card = Img2ImgStageCard(self.body, controller=controller, theme=theme)
        self.img2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.upscale_card = UpscaleStageCard(self.body, controller=controller, theme=theme)
        self.upscale_card.pack(fill=tk.BOTH, expand=True)

    def load_from_config(self, config: dict | None) -> None:
        data = config or {}
        self.txt2img_card.load_from_config(data)
        self.img2img_card.load_from_config(data)
        self.upscale_card.load_from_config(data)

    def to_config_delta(self) -> dict:
        delta: dict[str, dict[str, object]] = {}
        for card in (self.txt2img_card, self.img2img_card, self.upscale_card):
            section_delta = card.to_config_dict()
            for section, values in section_delta.items():
                if not values:
                    continue
                delta.setdefault(section, {}).update(values)
        return delta

    def get_txt2img_form_view(self) -> dict:
        return self.txt2img_card.get_form_values()

    def validate_txt2img(self) -> ValidationResult:
        return validate_txt2img(self.get_txt2img_form_view())

    def set_txt2img_change_callback(self, callback) -> None:
        self._txt2img_change_callback = callback

    def _handle_txt2img_change(self) -> None:
        if self._txt2img_change_callback:
            self._txt2img_change_callback()
