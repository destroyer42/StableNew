"""Compatibility wrapper that exposes the GUI pipeline controller at src.controller."""

from typing import Callable

from src.gui.controller import PipelineController as _GUIPipelineController
from src.gui.state import StateManager
from src.learning.learning_record import LearningRecord, LearningRecordWriter
from src.controller.job_execution_controller import JobExecutionController
from src.controller.queue_execution_controller import QueueExecutionController
from src.queue.job_model import JobStatus
from src.pipeline.stage_sequencer import StageExecutionPlan, build_stage_execution_plan
from src.pipeline.pipeline_runner import PipelineRunResult
from src.gui.state import GUIState
from src.config.app_config import is_queue_execution_enabled
from src.controller.job_history_service import JobHistoryService
from src.controller.pipeline_config_assembler import PipelineConfigAssembler, GuiOverrides


class PipelineController(_GUIPipelineController):
    def build_pipeline_config_with_profiles(
        self,
        base_model_name: str,
        lora_names: list[str],
        user_overrides: dict[str, any],
    ) -> dict:
        """Build pipeline config using ModelProfile and LoraProfile priors."""
        from pathlib import Path
        from src.learning.model_profiles import find_model_profile_for_checkpoint, find_lora_profile_for_name, suggest_preset_for
        # Resolve checkpoint path (stub: assumes models are in 'models/' dir)
        checkpoint_path = Path("models") / f"{base_model_name}.ckpt"
        model_profile = find_model_profile_for_checkpoint(checkpoint_path)
        lora_search_paths = [Path("loras")]
        lora_profiles = [find_lora_profile_for_name(name, lora_search_paths) for name in lora_names]
        lora_profiles = [lp for lp in lora_profiles if lp]
        suggested = suggest_preset_for(model_profile, lora_profiles)
        # Start from default config
        config = self.get_default_config() if hasattr(self, "get_default_config") else {}
        # Always ensure txt2img key exists and populate with defaults if missing
        if "txt2img" not in config:
            config["txt2img"] = {
                "sampler_name": "Euler",
                "scheduler": None,
                "steps": 20,
                "cfg_scale": 5.0,
                "width": 512,
                "height": 512,
                "loras": [],
            }
        # Apply suggested preset if available
        if suggested:
            config["txt2img"].update({
                "sampler_name": suggested.sampler,
                "scheduler": suggested.scheduler,
                "steps": suggested.steps,
                "cfg_scale": suggested.cfg,
                "width": suggested.resolution[0],
                "height": suggested.resolution[1],
            })
            # Apply LoRA weights
            config["txt2img"]["loras"] = [
                {"name": name, "weight": suggested.lora_weights.get(name, 0.6)} for name in lora_names
            ]
            import logging
            logging.info(f"Using model profile preset {suggested.preset_id} (source={suggested.source}) for {base_model_name} + {lora_names}.")
        # Apply user overrides last
        for k, v in user_overrides.items():
            # Map common override keys to txt2img
            if k in ("sampler_name", "scheduler", "steps", "cfg_scale", "width", "height", "loras"):
                config["txt2img"][k] = v
            elif k == "cfg":
                config["txt2img"]["cfg_scale"] = v
            elif k == "resolution" and isinstance(v, (tuple, list)) and len(v) == 2:
                config["txt2img"]["width"] = v[0]
                config["txt2img"]["height"] = v[1]
            else:
                config[k] = v
        return config

    """Provide a default StateManager so legacy imports keep working."""

    def __init__(
        self,
        state_manager: StateManager | None = None,
        *,
        learning_record_writer: LearningRecordWriter | None = None,
        on_learning_record: Callable[[LearningRecord], None] | None = None,
        **kwargs,
    ):
        queue_execution_controller = kwargs.pop("queue_execution_controller", None)
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
        self._queue_execution_controller: QueueExecutionController | None = queue_execution_controller or QueueExecutionController(job_controller=self._job_controller)
        self._queue_execution_enabled: bool = is_queue_execution_enabled()
        self._config_assembler = PipelineConfigAssembler()
        if self._queue_execution_controller:
            try:
                self._queue_execution_controller.observe("pipeline_ctrl", self._on_queue_status)
            except Exception:
                pass
        self._job_history_service: JobHistoryService | None = None
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
        """Submit a pipeline job using queue mode when enabled, else direct path."""

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

        if self._queue_execution_enabled and self._queue_execution_controller:
            self._active_job_id = self._queue_execution_controller.submit_pipeline_job(_payload)
            try:
                self.state_manager.transition_to(GUIState.RUNNING)
            except Exception:
                pass
            return True

        self._active_job_id = self._job_controller.submit_pipeline_run(_payload)
        try:
            self.state_manager.transition_to(GUIState.RUNNING)
        except Exception:
            pass
        return True

    def stop_pipeline(self) -> bool:
        """Cancel the active job."""

        if self._active_job_id:
            if self._queue_execution_enabled and self._queue_execution_controller:
                try:
                    self._queue_execution_controller.cancel_job(self._active_job_id)
                except Exception:
                    pass
            else:
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
        self._handle_status(job.job_id, status)

    def _on_queue_status(self, job, status: JobStatus) -> None:
        self._handle_status(getattr(job, "job_id", None), status)

    def _handle_status(self, job_id: str | None, status: JobStatus) -> None:
        if job_id is None or job_id != self._active_job_id:
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
        elif status in {JobStatus.QUEUED, JobStatus.RUNNING}:
            try:
                self.state_manager.transition_to(GUIState.RUNNING)
            except Exception:
                pass

    def get_job_history_service(self) -> JobHistoryService:
        """Return a JobHistoryService bound to this controller's queue/history."""

        if self._job_history_service is None:
            try:
                queue = self._job_controller.get_queue()
                history = self._job_controller.get_history_store()
                self._job_history_service = JobHistoryService(queue, history, job_controller=self._job_controller)
            except Exception:
                pass
        return self._job_history_service
