"""Tk-free helpers for GUI v2 learning hooks."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.learning.learning_adapter import prepare_learning_run
from src.learning.learning_record import LearningRecord, LearningRecordWriter
from src.learning.learning_plan import LearningPlan, LearningRunStep
from src.learning.learning_runner import LearningRunner


def create_learning_context(
    base_config: Dict[str, Any] | None,
    one_click_action: str | None = None,
    run_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Return a normalized context payload for future learning flows.

    This does not trigger any GUI behavior and remains Tk-free.
    """

    return {
        "base_config": deepcopy(base_config or {}),
        "one_click_action": one_click_action,
        "metadata": deepcopy(run_metadata or {}),
    }


def prepare_learning_plan_and_steps(
    base_config: Dict[str, Any],
    options: Dict[str, Any],
) -> Tuple[LearningPlan, list[LearningRunStep]]:
    """Small wrapper around the existing learning adapter for GUI-facing code."""

    return prepare_learning_run(deepcopy(base_config), deepcopy(options))


def get_runner(base_config: Dict[str, Any] | None = None) -> LearningRunner:
    """Return a LearningRunner instance without importing GUI modules."""

    return LearningRunner(deepcopy(base_config or {}))


def list_recent_learning_records(records_path: Path, limit: int = 10) -> List[LearningRecord]:
    """Return the most recent learning records from a JSONL file."""

    path = Path(records_path)
    if path.is_dir():
        path = path / "learning_records.jsonl"
    if not path.exists():
        return []
    records: List[LearningRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines[-limit:]:
        try:
            records.append(LearningRecord.from_json(line))
        except Exception:
            continue
    records.reverse()
    return records


def save_learning_feedback(
    records_path: Path,
    record: LearningRecord,
    rating: int,
    tags: str | None = None,
) -> LearningRecord | None:
    """Append a LearningRecord with updated rating/tags for a prior run."""

    try:
        metadata = dict(record.metadata or {})
        if rating:
            metadata["rating"] = int(rating)
        if tags is not None:
            metadata["tags"] = tags
        updated = LearningRecord(
            run_id=record.run_id,
            timestamp=record.timestamp,
            base_config=record.base_config,
            variant_configs=record.variant_configs,
            randomizer_mode=record.randomizer_mode,
            randomizer_plan_size=record.randomizer_plan_size,
            primary_model=record.primary_model,
            primary_sampler=record.primary_sampler,
            primary_scheduler=record.primary_scheduler,
            primary_steps=record.primary_steps,
            primary_cfg_scale=record.primary_cfg_scale,
            metadata=metadata,
            stage_plan=record.stage_plan,
            stage_events=record.stage_events,
            outputs=record.outputs,
        )
        writer = LearningRecordWriter(records_path)
        writer.append_record(updated)
        return updated
    except Exception:
        return None
