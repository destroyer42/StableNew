"""Learning record models and persistence helpers."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class LearningRecord:
    """Durable record describing an executed pipeline run."""

    run_id: str
    timestamp: str
    base_config: Dict[str, Any]
    variant_configs: List[Dict[str, Any]]
    randomizer_mode: str
    randomizer_plan_size: int
    primary_model: str
    primary_sampler: str
    primary_scheduler: str
    primary_steps: int
    primary_cfg_scale: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_json(text: str) -> "LearningRecord":
        payload = json.loads(text)
        return LearningRecord(
            run_id=payload["run_id"],
            timestamp=payload["timestamp"],
            base_config=payload.get("base_config", {}),
            variant_configs=payload.get("variant_configs", []),
            randomizer_mode=payload.get("randomizer_mode", ""),
            randomizer_plan_size=payload.get("randomizer_plan_size", 0),
            primary_model=payload.get("primary_model", ""),
            primary_sampler=payload.get("primary_sampler", ""),
            primary_scheduler=payload.get("primary_scheduler", ""),
            primary_steps=int(payload.get("primary_steps", 0)),
            primary_cfg_scale=float(payload.get("primary_cfg_scale", 0.0)),
            metadata=payload.get("metadata", {}),
        )

    @staticmethod
    def from_pipeline_context(
        *,
        base_config: Dict[str, Any],
        variant_configs: Iterable[Dict[str, Any]] | None,
        randomizer_mode: str = "",
        randomizer_plan_size: int = 0,
        extract_primary: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> "LearningRecord":
        run_id = str(uuid.uuid4())
        timestamp = _now_iso()
        variants = list(variant_configs or [])
        base_cfg = base_config or {}
        primary_cfg = variants[0] if variants else base_cfg

        knob_info = extract_primary(primary_cfg) if extract_primary else {}
        return LearningRecord(
            run_id=run_id,
            timestamp=timestamp,
            base_config=base_cfg,
            variant_configs=variants,
            randomizer_mode=randomizer_mode or "",
            randomizer_plan_size=randomizer_plan_size,
            primary_model=str(knob_info.get("model", "")),
            primary_sampler=str(knob_info.get("sampler", "")),
            primary_scheduler=str(knob_info.get("scheduler", "")),
            primary_steps=_safe_int(knob_info.get("steps"), 0),
            primary_cfg_scale=_safe_float(knob_info.get("cfg_scale"), 0.0),
            metadata=dict(metadata or {}),
        )


class LearningRecordWriter:
    """Writes learning records atomically to disk."""

    def __init__(self, base_dir: str | os.PathLike[str]) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: LearningRecord) -> None:
        try:
            payload = record.to_json()
            filename = f"{record.timestamp}_{record.run_id}.json".replace(":", "-")
            temp_path = self.base_dir / f".{filename}.tmp"
            final_path = self.base_dir / filename
            with open(temp_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, final_path)
        except Exception:
            logger.debug("Failed to write learning record", exc_info=True)
logger = logging.getLogger(__name__)
