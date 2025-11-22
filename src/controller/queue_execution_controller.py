from __future__ import annotations

from typing import Callable

from src.controller.job_execution_controller import JobExecutionController
from src.queue.job_model import JobPriority


class QueueExecutionController:
    """Facade around JobExecutionController for controller/GUI usage."""

    def __init__(self, *, job_controller: JobExecutionController | None = None) -> None:
        self._job_controller = job_controller or JobExecutionController()

    def submit(self, payload_callable, *, priority: JobPriority = JobPriority.NORMAL) -> str:
        return self._job_controller.submit_pipeline_run(payload_callable, priority=priority)

    def cancel(self, job_id: str) -> None:
        self._job_controller.cancel_job(job_id)

    def observe(self, key: str, callback: Callable) -> None:
        self._job_controller.set_status_callback(key, callback)

    def clear_observer(self, key: str) -> None:
        self._job_controller.clear_status_callback(key)
