"""Application-level configuration flags for GUI toggles."""

from __future__ import annotations

import os

_learning_enabled: bool | None = None
_job_history_path: str | None = None
_queue_execution_enabled: bool | None = None


def learning_enabled_default() -> bool:
    """Return default for learning toggle (opt-in by default)."""

    env_flag = os.environ.get("STABLENEW_LEARNING_ENABLED")
    if env_flag is None:
        return False
    return env_flag.lower() in {"1", "true", "yes", "on"}


def get_learning_enabled() -> bool:
    """Return current learning toggle (module-level memory)."""

    global _learning_enabled
    if _learning_enabled is None:
        _learning_enabled = learning_enabled_default()
    return bool(_learning_enabled)


def set_learning_enabled(enabled: bool) -> None:
    """Persist learning toggle in module-level memory."""

    global _learning_enabled
    _learning_enabled = bool(enabled)


def job_history_path_default() -> str:
    """Return default path for job history storage."""

    env_path = os.environ.get("STABLENEW_JOB_HISTORY_PATH")
    if env_path:
        return env_path
    return os.path.join("data", "job_history.jsonl")


def get_job_history_path() -> str:
    """Return current job history path (module-level memory)."""

    global _job_history_path
    if _job_history_path is None:
        _job_history_path = job_history_path_default()
    return _job_history_path


def set_job_history_path(path: str) -> None:
    """Override job history storage path."""

    global _job_history_path
    _job_history_path = path


def queue_execution_enabled_default() -> bool:
    """Return default for queue-backed execution (disabled by default)."""

    env_flag = os.environ.get("STABLENEW_QUEUE_EXECUTION_ENABLED")
    if env_flag is None:
        return False
    return env_flag.lower() in {"1", "true", "yes", "on"}


def is_queue_execution_enabled() -> bool:
    """Return current queue execution flag."""

    global _queue_execution_enabled
    if _queue_execution_enabled is None:
        _queue_execution_enabled = queue_execution_enabled_default()
    return bool(_queue_execution_enabled)


def set_queue_execution_enabled(enabled: bool) -> None:
    """Set queue execution flag (module-local only)."""

    global _queue_execution_enabled
    _queue_execution_enabled = bool(enabled)
