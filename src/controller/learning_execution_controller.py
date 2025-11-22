"""Controller wrapper for learning execution (non-GUI)."""

from __future__ import annotations

from typing import Any, Callable

from src.learning.learning_execution import (
    LearningExecutionContext,
    LearningExecutionResult,
    LearningExecutionRunner,
)
from src.learning.learning_plan import LearningPlan
from src.pipeline.pipeline_runner import PipelineRunResult


class LearningExecutionController:
    """Expose a high-level API to run learning plans via an injected pipeline run callable."""

    def __init__(self, run_callable: Callable[[dict, Any], PipelineRunResult] | None = None) -> None:
        self._run_callable = run_callable
        self._last_result: LearningExecutionResult | None = None

    def run_learning_plan(
        self,
        plan: LearningPlan,
        base_config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> LearningExecutionResult:
        if self._run_callable is None:
            raise RuntimeError("No pipeline run callable provided for learning execution.")
        context = LearningExecutionContext(plan=plan, base_config=base_config, metadata=metadata or {})
        runner = LearningExecutionRunner(run_callable=self._wrap_callable())
        self._last_result = runner.run(context)
        return self._last_result

    def _wrap_callable(self):
        def _call(cfg: dict[str, Any], step: Any) -> PipelineRunResult:
            return self._run_callable(cfg, step)

        return _call

    def get_last_learning_execution_result_for_tests(self) -> LearningExecutionResult | None:
        return self._last_result
