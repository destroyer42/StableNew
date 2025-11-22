"""Compatibility wrapper that exposes the GUI pipeline controller at src.controller."""

from typing import Callable

from src.gui.controller import PipelineController as _GUIPipelineController
from src.gui.state import StateManager
from src.learning.learning_record import LearningRecord, LearningRecordWriter
from src.controller.job_execution_controller import JobExecutionController
from src.queue.job_model import JobStatus
from src.pipeline.stage_sequencer import StageExecutionPlan, build_stage_execution_plan
from src.pipeline.pipeline_runner import PipelineRunResult
from src.gui.state import GUIState


class PipelineController(_GUIPipelineController):
    """Provide a default StateManager so legacy imports keep working."""

    def __init__(
        self,
        state_manager: StateManager | None = None,
        *,
        learning_record_writer: LearningRecordWriter | None = None,
        on_learning_record: Callable[[LearningRecord], None] | None = None,
        **kwargs,
    ):
        super().__init__(state_manager or StateManager(), **kwargs)
        self._learning_runner = None
        self._learning_record_writer = learning_record_writer
        self._learning_record_callback = on_learning_record
        self._last_learning_record: LearningRecord | None = None
        self._last_run_result: PipelineRunResult | None = None
        self._last_stage_execution_plan: StageExecutionPlan | None = None
        self._last_stage_events: list[dict] | None = None
        self._learning_enabled: bool = False
        self._job_controller = JobExecutionController(execute_job=self._execute_job)
        self._active_job_id: str | None = None
        self._job_controller.set_status_callback("pipeline", self._on_job_status)

    def _get_learning_runner(self):
        if self._learning_runner is None:
            from src.learning.learning_runner import LearningRunner

            self._learning_runner = LearningRunner()
        return self._learning_runner

    def get_learning_runner_for_tests(self):
        """Return the learning runner instance for test inspection."""

        return self._get_learning_runner()

    def handle_learning_record(self, record: LearningRecord) -> None:
        """Handle learning records forwarded from pipeline runner."""

        self._last_learning_record = record
        if self._learning_record_writer and self._learning_enabled:
            try:
                append = getattr(self._learning_record_writer, "append_record", None)
                if callable(append):
                    append(record)
                else:
                    self._learning_record_writer.write(record)
            except Exception:
                pass
        if self._learning_record_callback:
            try:
                self._learning_record_callback(record)
            except Exception:
                pass

    def get_learning_record_handler(self):
        """Return a callback suitable for passing to PipelineRunner."""

        return self.handle_learning_record

    def get_last_learning_record(self) -> LearningRecord | None:
        """Return the most recent LearningRecord handled by the controller."""

        return self._last_learning_record

    def set_learning_enabled(self, enabled: bool) -> None:
        """Enable or disable passive learning record emission."""

        self._learning_enabled = bool(enabled)

    def is_learning_enabled(self) -> bool:
        """Return whether learning record emission is enabled."""

        return self._learning_enabled

    def record_run_result(self, result: PipelineRunResult) -> None:
        """Record the last PipelineRunResult for inspection by higher layers/tests."""

        self._last_run_result = result
        self._last_stage_events = getattr(result, "stage_events", None)

    def get_last_run_result(self) -> PipelineRunResult | None:
        """Return the most recent PipelineRunResult recorded on this controller."""

        return self._last_run_result

    def validate_stage_plan(self, config: dict) -> StageExecutionPlan:
        """Build and store a stage execution plan for testing/inspection."""

        plan = build_stage_execution_plan(config)
        self._last_stage_execution_plan = plan
        return plan

    def get_last_stage_execution_plan_for_tests(self) -> StageExecutionPlan | None:
        """Return the most recent StageExecutionPlan built by this controller."""

        return self._last_stage_execution_plan

    def get_last_stage_events_for_tests(self) -> list[dict] | None:
        """Return last emitted stage events."""

        return self._last_stage_events

    # Queue-backed execution -------------------------------------------------
    def start_pipeline(
        self,
        pipeline_func: Callable[[], dict[str, any]],
        on_complete: Callable[[dict[str, any]], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> bool:
        """Submit a pipeline job to the queue instead of running directly."""

        def _payload():
            try:
                result = pipeline_func()
                if on_complete:
                    on_complete(result)
                return result
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    on_error(exc)
                raise

        if not self.state_manager.can_run():
            return False

        self._active_job_id = self._job_controller.submit_pipeline_run(_payload)
        try:
            self.state_manager.transition_to(GUIState.RUNNING)
        except Exception:
            pass
        return True

    def stop_pipeline(self) -> bool:
        """Cancel the active job."""

        if self._active_job_id:
            self._job_controller.cancel_job(self._active_job_id)
            self._active_job_id = None
            try:
                self.state_manager.transition_to(GUIState.STOPPING)
            except Exception:
                pass
            return True
        return False

    def _execute_job(self, job) -> dict:
        if hasattr(job, "payload") and callable(job.payload):
            return job.payload()
        return {}

    def _on_job_status(self, job, status: JobStatus) -> None:
        if job.job_id != self._active_job_id:
            return
        if status == JobStatus.COMPLETED:
            try:
                self.state_manager.transition_to(GUIState.IDLE)
            except Exception:
                pass
            self._active_job_id = None
        elif status == JobStatus.FAILED:
            try:
                self.state_manager.transition_to(GUIState.ERROR)
            except Exception:
                pass
            self._active_job_id = None
        elif status == JobStatus.CANCELLED:
            try:
                self.state_manager.transition_to(GUIState.IDLE)
            except Exception:
                pass
            self._active_job_id = None
