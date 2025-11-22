"""Application-level configuration flags for GUI toggles."""

from __future__ import annotations

import os

_learning_enabled: bool | None = None


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
