"""Application-level configuration flags for GUI toggles."""

from __future__ import annotations

import os


def learning_enabled_default() -> bool:
    """Return default for learning toggle (opt-in by default)."""

    env_flag = os.environ.get("STABLENEW_LEARNING_ENABLED")
    if env_flag is None:
        return False
    return env_flag.lower() in {"1", "true", "yes", "on"}
