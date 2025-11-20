"""Production pipeline runner integration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

from src.api.client import SDWebUIClient
from src.pipeline.executor import Pipeline
from src.utils import StructuredLogger
from src.utils.config import ConfigManager

if TYPE_CHECKING:  # pragma: no cover
    from src.controller.app_controller import CancelToken


@dataclass
class PipelineConfig:
    """Controller-facing configuration passed into the pipeline runner."""

    prompt: str
    model: str
    sampler: str
    width: int
    height: int
    steps: int
    cfg_scale: float
    pack_name: Optional[str] = None
    preset_name: Optional[str] = None


class PipelineRunner:
    """Adapter that drives the real multi-stage Pipeline executor."""

    def __init__(
        self,
        api_client: SDWebUIClient,
        structured_logger: StructuredLogger,
        *,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        self._api_client = api_client
        self._structured_logger = structured_logger
        self._config_manager = config_manager or ConfigManager()
        self._pipeline = Pipeline(api_client, structured_logger)

    def run(
        self,
        config: PipelineConfig,
        cancel_token: "CancelToken",
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Execute the full pipeline using the provided configuration."""

        if log_fn:
            log_fn("[pipeline] PipelineRunner starting execution.")

        executor_config = self._build_executor_config(config)
        prompt = config.prompt.strip() or config.pack_name or config.preset_name or "StableNew GUI Run"
        run_name = config.pack_name or config.preset_name or "stable_new_session"

        self._pipeline.run_full_pipeline(
            prompt,
            executor_config,
            run_name=run_name,
            batch_size=1,
            cancel_token=cancel_token,
        )

        if log_fn:
            log_fn("[pipeline] PipelineRunner completed execution.")

    def _build_executor_config(self, config: PipelineConfig) -> dict[str, Any]:
        """Prepare the executor configuration dict from PipelineConfig."""

        base = deepcopy(self._config_manager.get_default_config())

        txt2img = base.setdefault("txt2img", {})
        txt2img["model"] = config.model
        txt2img["sampler_name"] = config.sampler
        txt2img["width"] = config.width
        txt2img["height"] = config.height
        txt2img["steps"] = config.steps
        txt2img["cfg_scale"] = config.cfg_scale

        img2img = base.setdefault("img2img", {})
        img2img["model"] = config.model
        img2img["sampler_name"] = config.sampler
        img2img["steps"] = max(img2img.get("steps", 15), 1)

        metadata = base.setdefault("metadata", {})
        if config.pack_name:
            metadata["pack_name"] = config.pack_name
        if config.preset_name:
            metadata["preset_name"] = config.preset_name

        return base


__all__ = ["PipelineConfig", "PipelineRunner"]
