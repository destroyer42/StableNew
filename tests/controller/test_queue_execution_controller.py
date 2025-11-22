from unittest import mock

from src.controller.queue_execution_controller import QueueExecutionController


def test_queue_execution_controller_proxies_calls():
    executor = mock.Mock()
    controller = QueueExecutionController(job_controller=executor)

    controller.submit(lambda: None)
    controller.cancel("job-1")
    controller.observe("k", lambda *_: None)
    controller.clear_observer("k")

    executor.submit_pipeline_run.assert_called_once()
    executor.cancel_job.assert_called_once_with("job-1")
    executor.set_status_callback.assert_called_once()
    executor.clear_status_callback.assert_called_once_with("k")
