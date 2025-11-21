"""Production pipeline runner integration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, TYPE_CHECKING

from src.api.client import SDWebUIClient
from src.learning.learning_record import LearningRecord, LearningRecordWriter
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
    variant_configs: Optional[List[dict[str, Any]]] = None
    randomizer_mode: Optional[str] = None
    randomizer_plan_size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineRunner:
    """Adapter that drives the real multi-stage Pipeline executor."""

    def __init__(
        self,
        api_client: SDWebUIClient,
        structured_logger: StructuredLogger,
        *,
        config_manager: Optional[ConfigManager] = None,
        learning_record_writer: Optional[LearningRecordWriter] = None,
        on_learning_record: Optional[Callable[[LearningRecord], None]] = None,
    ) -> None:
        self._api_client = api_client
        self._structured_logger = structured_logger
        self._config_manager = config_manager or ConfigManager()
        self._pipeline = Pipeline(api_client, structured_logger)
        self._learning_record_writer = learning_record_writer
        self._learning_record_callback = on_learning_record

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
        success = False

        try:
            self._pipeline.run_full_pipeline(
                prompt,
                executor_config,
                run_name=run_name,
                batch_size=1,
                cancel_token=cancel_token,
            )
            success = True
        finally:
            if success:
                self._emit_learning_record(config, executor_config)

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

    def _emit_learning_record(self, config: PipelineConfig, executor_config: dict[str, Any]) -> None:
        if not (self._learning_record_writer or self._learning_record_callback):
            return
        try:
            variants = config.variant_configs or []
            if not variants:
                variants = [executor_config]
            variant_payload = [deepcopy(variant) for variant in variants]
            pipeline_section = executor_config.get("pipeline", {}) or {}
            randomizer_mode = (
                config.randomizer_mode
                or pipeline_section.get("variant_mode")
                or ""
            )
            plan_size = config.randomizer_plan_size or len(variant_payload)
            metadata = dict(config.metadata or {})
            if config.pack_name:
                metadata["pack_name"] = config.pack_name
            if config.preset_name:
                metadata["preset_name"] = config.preset_name

            record = LearningRecord.from_pipeline_context(
                base_config=deepcopy(executor_config),
                variant_configs=variant_payload,
                randomizer_mode=randomizer_mode,
                randomizer_plan_size=plan_size,
                extract_primary=_extract_primary_knobs,
                metadata=metadata,
            )
        except Exception:
            return

        if self._learning_record_writer:
            try:
                self._learning_record_writer.write(record)
            except Exception:
                pass
        if self._learning_record_callback:
            try:
                self._learning_record_callback(record)
            except Exception:
                pass


def _extract_primary_knobs(config: dict[str, Any]) -> dict[str, Any]:
    txt2img = (config or {}).get("txt2img", {}) or {}
    return {
        "model": txt2img.get("model", ""),
        "sampler": txt2img.get("sampler_name", ""),
        "scheduler": txt2img.get("scheduler", ""),
        "steps": txt2img.get("steps", 0),
        "cfg_scale": txt2img.get("cfg_scale", 0.0),
    }


__all__ = ["PipelineConfig", "PipelineRunner"]
