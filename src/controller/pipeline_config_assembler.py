from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.pipeline.pipeline_runner import PipelineConfig
from src.utils.config import ConfigManager


@dataclass
class GuiOverrides:
    prompt: str = ""
    model: str = ""
    sampler: str = ""
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: float = 7.0
    metadata: dict[str, Any] | None = None


class PipelineConfigAssembler:
    """Translate GUI/controller inputs into a PipelineConfig instance."""

    def __init__(self, *, config_manager: ConfigManager | None = None, max_megapixels: float = 16.0) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._max_megapixels = max(max_megapixels, 0.1)

    def build_from_gui_input(
        self,
        *,
        base_config: dict[str, Any] | None = None,
        overrides: GuiOverrides | dict[str, Any] | None = None,
        randomizer_metadata: dict[str, Any] | None = None,
        learning_metadata: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        gui_overrides = self._normalize_overrides(overrides)
        base = deepcopy(base_config or self._default_txt2img())
        merged = self._merge_base_and_overrides(base, gui_overrides)
        merged = self.apply_megapixel_clamp(merged)

        metadata = dict(gui_overrides.get("metadata") or {})
        if learning_metadata:
            metadata["learning"] = learning_metadata
            metadata["learning_enabled"] = bool(learning_metadata.get("learning_enabled", True))
        if randomizer_metadata:
            metadata["randomizer"] = randomizer_metadata

        return PipelineConfig(
            prompt=gui_overrides.get("prompt", merged.get("prompt", "")),
            model=gui_overrides.get("model", merged.get("model", "")),
            sampler=gui_overrides.get("sampler", merged.get("sampler_name", "")),
            width=int(merged.get("width", 512)),
            height=int(merged.get("height", 512)),
            steps=int(merged.get("steps", 20)),
            cfg_scale=float(merged.get("cfg_scale", 7.0)),
            metadata=metadata,
        )

    def build_for_learning_run(
        self,
        *,
        base_config: dict[str, Any] | None = None,
        overrides: GuiOverrides | dict[str, Any] | None = None,
        learning_metadata: dict[str, Any] | None = None,
        randomizer_metadata: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        learning_meta = dict(learning_metadata or {})
        learning_meta["learning_enabled"] = True
        return self.build_from_gui_input(
            base_config=base_config,
            overrides=overrides,
            randomizer_metadata=randomizer_metadata,
            learning_metadata=learning_meta,
        )

    def apply_megapixel_clamp(self, cfg: dict[str, Any]) -> dict[str, Any]:
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

    def attach_randomizer_metadata(self, config: PipelineConfig, rand_meta: dict[str, Any]) -> PipelineConfig:
        config.metadata = config.metadata or {}
        config.metadata["randomizer"] = rand_meta
        return config

    def _default_txt2img(self) -> dict[str, Any]:
        defaults = self._config_manager.get_default_config()
        return deepcopy(defaults.get("txt2img", {}))

    def _normalize_overrides(self, overrides: GuiOverrides | dict[str, Any] | None) -> dict[str, Any]:
        if overrides is None:
            return {}
        if isinstance(overrides, GuiOverrides):
            return {
                "prompt": overrides.prompt,
                "model": overrides.model,
                "sampler": overrides.sampler,
                "width": overrides.width,
                "height": overrides.height,
                "steps": overrides.steps,
                "cfg_scale": overrides.cfg_scale,
                "metadata": overrides.metadata or {},
            }
        return dict(overrides)

    def _merge_base_and_overrides(self, base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base or {})
        for k, v in overrides.items():
            if v is None:
                continue
            merged[k] = v
        return merged
