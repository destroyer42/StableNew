"""Tk-free helpers for GUI v2 learning hooks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Tuple

from src.learning.learning_adapter import prepare_learning_run
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
