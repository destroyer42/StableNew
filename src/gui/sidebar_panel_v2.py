"""Sidebar panel scaffold for GUI v2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from . import theme as theme_mod
from .core_config_panel_v2 import CoreConfigPanelV2
from .model_list_adapter_v2 import ModelListAdapterV2
from .model_manager_panel_v2 import ModelManagerPanelV2
from .negative_prompt_panel_v2 import NegativePromptPanelV2
from .output_settings_panel_v2 import OutputSettingsPanelV2
from .prompt_pack_adapter_v2 import PromptPackAdapterV2, PromptPackSummary
from .prompt_pack_panel_v2 import PromptPackPanelV2


class SidebarPanelV2(ttk.Frame):
    """Container for sidebar content (core config + negative prompt + packs)."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        controller=None,
        theme=None,
        prompt_pack_adapter: PromptPackAdapterV2 | None = None,
        on_apply_pack: Callable[[str, PromptPackSummary | None], None] | None = None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.theme = theme
        self.prompt_pack_adapter = prompt_pack_adapter or PromptPackAdapterV2()
        self._on_apply_pack = on_apply_pack

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Sidebar", style=header_style)
        self.header_label.pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        adapter = ModelListAdapterV2(lambda: getattr(self.controller, "client", None))
        self.model_manager_panel = ModelManagerPanelV2(self.body, theme=theme, adapter=adapter)
        self.model_manager_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.core_config_panel = CoreConfigPanelV2(self.body, theme=theme)
        self.core_config_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.negative_prompt_panel = NegativePromptPanelV2(self.body, theme=theme)
        self.negative_prompt_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.output_settings_panel = OutputSettingsPanelV2(self.body, theme=theme)
        self.output_settings_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.prompt_pack_panel = PromptPackPanelV2(
            self.body,
            theme=theme,
            packs=[],
            on_apply=self._handle_apply_pack,
        )
        self.prompt_pack_panel.pack(fill=tk.BOTH, expand=True)

        self.refresh_prompt_packs()

    def refresh_prompt_packs(self) -> None:
        if not self.prompt_pack_adapter:
            return
        try:
            summaries = self.prompt_pack_adapter.load_summaries()
        except Exception:
            summaries = []
        self.prompt_pack_panel.set_packs(summaries)

    def _handle_apply_pack(self, summary: PromptPackSummary) -> None:
        prompt_text = ""
        if self.prompt_pack_adapter:
            try:
                prompt_text = self.prompt_pack_adapter.get_base_prompt(summary)
            except Exception:
                prompt_text = ""
        if self._on_apply_pack:
            try:
                self._on_apply_pack(prompt_text, summary)
            except Exception:
                pass

    def get_model_overrides(self) -> dict[str, object]:
        panel = getattr(self, "model_manager_panel", None)
        if panel:
            return panel.get_selections()
        return {}

    def get_core_overrides(self) -> dict[str, object]:
        if self.core_config_panel:
            return self.core_config_panel.get_overrides()
        return {}

    def get_negative_prompt(self) -> str:
        if self.negative_prompt_panel:
            return self.negative_prompt_panel.get_negative_prompt()
        return ""

    def get_resolution(self) -> tuple[int, int]:
        if self.core_config_panel and getattr(self.core_config_panel, "resolution_panel", None):
            return self.core_config_panel.resolution_panel.get_resolution()
        return 512, 512

    def get_resolution_preset(self) -> str:
        if self.core_config_panel and getattr(self.core_config_panel, "resolution_panel", None):
            return self.core_config_panel.resolution_panel.get_preset_label()
        return ""

    def get_output_overrides(self) -> dict[str, object]:
        panel = getattr(self, "output_settings_panel", None)
        if panel:
            return panel.get_output_overrides()
        return {}


__all__ = ["SidebarPanelV2"]
