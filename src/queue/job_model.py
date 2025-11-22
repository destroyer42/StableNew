"""Job model for single-node and future cluster execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum
from typing import Any, Dict, Optional

from src.pipeline.pipeline_runner import PipelineConfig


class JobPriority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class Job:
    job_id: str
    pipeline_config: PipelineConfig
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    learning_enabled: bool = False
    randomizer_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def mark_status(self, status: JobStatus, error_message: str | None = None) -> None:
        self.status = status
        self.updated_at = _utcnow()
        if error_message:
            self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "priority": int(self.priority),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "learning_enabled": self.learning_enabled,
            "randomizer_metadata": self.randomizer_metadata or {},
            "error_message": self.error_message,
            "result": self.result,
            "pipeline_config": self.pipeline_config.__dict__,
        }
