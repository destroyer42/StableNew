"""Pipeline panel composed of modular stage cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod
from src.gui.stage_cards_v2.advanced_txt2img_stage_card_v2 import AdvancedTxt2ImgStageCardV2
from src.gui.stage_cards_v2.advanced_img2img_stage_card_v2 import AdvancedImg2ImgStageCardV2
from src.gui.stage_cards_v2.advanced_upscale_stage_card_v2 import AdvancedUpscaleStageCardV2
from src.gui.stage_cards_v2.validation_result import ValidationResult
from .widgets.scrollable_frame_v2 import ScrollableFrame


class PipelinePanelV2(ttk.Frame):
    """Container for pipeline stage cards."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        controller=None,
        app_state=None,
        theme=None,
        config_manager=None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.app_state = app_state
        self.theme = theme
        self.config_manager = config_manager

        header_style = getattr(theme, "PIPELINE_HEADING_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        ttk.Label(self, text="Pipeline", style=header_style).pack(anchor=tk.W, pady=(0, 4))

        # Layout: left sidebar, center stage cards (scrollable), right preview
        # Deprecated: use PipelineTabFrame instead of PipelinePanelV2
        self.run_button = None
        self.stop_button = None

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
        return self.txt2img_card.to_config_dict().get("txt2img", {})

    def validate_txt2img(self) -> ValidationResult:
        return self.txt2img_card.validate()

    def set_txt2img_change_callback(self, callback) -> None:
        self._txt2img_change_callback = callback

    def _handle_txt2img_change(self) -> None:
        if self._txt2img_change_callback:
            self._txt2img_change_callback()

    def validate_full_pipeline(self) -> ValidationResult:
        for card in (self.txt2img_card, self.img2img_card, self.upscale_card):
            result = card.validate()
            if not result.ok:
                return result
        return ValidationResult(True, None)

    def _apply_stage_visibility(self) -> None:
        enabled = set(self.sidebar.get_enabled_stages()) if hasattr(self, "sidebar") else {"txt2img", "img2img", "upscale"}
        if "txt2img" in enabled:
            self.txt2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        else:
            self.txt2img_card.pack_forget()
        if "img2img" in enabled:
            self.img2img_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        else:
            self.img2img_card.pack_forget()
        if "upscale" in enabled:
            self.upscale_card.pack(fill=tk.BOTH, expand=True)
        else:
            self.upscale_card.pack_forget()

    def _handle_sidebar_change(self) -> None:
        self._apply_stage_visibility()
        try:
            if hasattr(self, "preview_panel"):
                self.preview_panel.update_from_controls(self.sidebar)
        except Exception:
            pass
