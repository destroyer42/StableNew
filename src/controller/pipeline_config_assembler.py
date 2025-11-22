from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from src.pipeline.pipeline_runner import PipelineConfig
from src.utils.config import ConfigManager


class PipelineConfigAssembler:
    """Translate GUI/controller inputs into a PipelineConfig instance."""

    def __init__(self, *, config_manager: ConfigManager | None = None, max_megapixels: float = 16.0) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._max_megapixels = max(max_megapixels, 0.1)

    def build_pipeline_config(
        self,
        *,
        base_config: dict[str, Any] | None = None,
        gui_overrides: dict[str, Any] | None = None,
        randomizer_overlay: dict[str, Any] | None = None,
        learning_enabled: bool = False,
    ) -> PipelineConfig:
        gui_overrides = gui_overrides or {}
        base = deepcopy(base_config or self._default_txt2img())
        base.update({k: v for k, v in gui_overrides.items() if v is not None})
        base = self._apply_megapixel_limit(base)

        metadata = dict(gui_overrides.get("metadata") or {})
        metadata["learning_enabled"] = bool(learning_enabled)
        if randomizer_overlay:
            metadata["randomizer"] = randomizer_overlay

        return PipelineConfig(
            prompt=gui_overrides.get("prompt", base.get("prompt", "")),
            model=gui_overrides.get("model", base.get("model", "")),
            sampler=gui_overrides.get("sampler", base.get("sampler_name", "")),
            width=int(base.get("width", 512)),
            height=int(base.get("height", 512)),
            steps=int(base.get("steps", 20)),
            cfg_scale=float(base.get("cfg_scale", 7.0)),
            metadata=metadata,
        )

    def _default_txt2img(self) -> dict[str, Any]:
        defaults = self._config_manager.get_default_config()
        return deepcopy(defaults.get("txt2img", {}))

    def _apply_megapixel_limit(self, cfg: dict[str, Any]) -> dict[str, Any]:
        width = int(cfg.get("width", 512))
        height = int(cfg.get("height", 512))
        if width <= 0 or height <= 0:
            return cfg

        current_mp = (width * height) / 1_000_000
        if current_mp <= self._max_megapixels:
            return cfg

        scale = math.sqrt(self._max_megapixels / current_mp)
        cfg["width"] = max(64, int(width * scale))
        cfg["height"] = max(64, int(height * scale))
        return cfg
