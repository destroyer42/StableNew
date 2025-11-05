"""Pipeline controller with cancellation support."""

import logging
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from .state import CancellationError, CancelToken, GUIState, StateManager

logger = logging.getLogger(__name__)


class LogMessage:
    """Log message with level and timestamp."""

    def __init__(self, message: str, level: str = "INFO"):
        """Initialize log message.

        Args:
            message: Log message text
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        self.message = message
        self.level = level
        self.timestamp = time.time()


class PipelineController:
    """Controls pipeline execution with cancellation support."""
    @property
    def is_terminal(self):
        return self.state_manager.current in (GUIState.IDLE, GUIState.ERROR)

    _JOIN_TIMEOUT = 5.0

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.cancel_token = CancelToken()
        self.log_queue: queue.Queue[LogMessage] = queue.Queue()

        # Worker + subprocess
        self._worker: threading.Thread | None = None
        self._pipeline = None
        self._current_subprocess: subprocess.Popen | None = None
        self._subprocess_lock = threading.Lock()

        # Cleanup & joining
        self._join_lock = threading.Lock()
        self._cleanup_lock = threading.Lock()
        self._cleanup_started = False            # per-run guard (reset at start of each pipeline run)
        self._cleanup_done = threading.Event()   # signals cleanup completed (per run)

        # Lifecycle signals
        self.lifecycle_event = threading.Event()  # terminal (IDLE/ERROR)
        self.state_change_event = threading.Event()  # pulse on change

        # Test hook
        self._sync_cleanup = False

        # Epoch
        self._epoch_lock = threading.Lock()
        self._epoch_id = 0

        # Progress callbacks
        self._progress_lock = threading.Lock()
        self._progress_callback: Callable[[float], None] | None = None
        self._eta_callback: Callable[[str], None] | None = None
        self._status_callback: Callable[[str], None] | None = None
        self._last_progress: dict[str, Any] = {
            "stage": "Idle",
            "percent": 0.0,
            "eta": "ETA: --",
        }

    def start_pipeline(
        self,
        pipeline_func: Callable[[], dict[str, Any]],
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> bool:
        if not self.state_manager.can_run():
            logger.warning("Cannot start pipeline - not in valid state")
            return False
        if not self.state_manager.transition_to(GUIState.RUNNING):
            return False

        # 1) Wait for previous cleanup (if any) to finish
        self._cleanup_done.wait(timeout=10.0)

        # 2) New epoch
        with self._epoch_lock:
            self._epoch_id += 1
            eid = self._epoch_id

        # 3) Reset per-run signals (allocate new Event)
        self._cleanup_done = threading.Event()
        self._cleanup_started = False
        self.lifecycle_event.clear()
        self.cancel_token.reset()

        def worker():
            error_occurred = False
            try:
                self._log("Pipeline started", "INFO")
                result = pipeline_func()
                if on_complete:
                    on_complete(result)
            except CancellationError:
                self._log("Pipeline cancelled by user", "WARNING")
                self.report_progress("Cancelled", self._last_progress["percent"], "Cancelled")
            except Exception as e:
                error_occurred = True
                self._log(f"Pipeline error: {e}", "ERROR")
                self.state_manager.transition_to(GUIState.ERROR)
                self.report_progress("Error", self._last_progress["percent"], "Error")
                if on_error:
                    on_error(e)

            def cleanup():
                self._do_cleanup(eid, error_occurred)

            if self._sync_cleanup:
                cleanup()
            else:
                threading.Thread(target=cleanup, daemon=True).start()

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()
        return True

    def stop_pipeline(self) -> bool:
        if not self.state_manager.can_stop():
            logger.warning("Cannot stop pipeline - not running")
            return False
        self._log("Stop requested - cancelling pipeline...", "WARNING")
        if not self.state_manager.transition_to(GUIState.STOPPING):
            return False
        self.cancel_token.cancel()
        self._terminate_subprocess()
        self.report_progress("Cancelled", self._last_progress["percent"], "Cancelled")

        def cleanup():
            with self._epoch_lock:
                eid = self._epoch_id
            self._do_cleanup(eid, error_occurred=False)

        if self._sync_cleanup:
            cleanup()
        else:
            threading.Thread(target=cleanup, daemon=True).start()
        return True

    def _do_cleanup(self, eid: int, error_occurred: bool):
        # Ignore stale cleanup from a previous run
        with self._epoch_lock:
            if eid != self._epoch_id:
                return

        # Single-entry guard
        with self._cleanup_lock:
            if self._cleanup_started:
                return
            self._cleanup_started = True

        # Join once, owned by controller
        with self._join_lock:
            if self._worker is not None and threading.current_thread() is not self._worker:
                self._worker.join(timeout=self._JOIN_TIMEOUT)
            self._worker = None

        # Terminate subprocess if still around
        self._terminate_subprocess()

        # State to terminal AFTER join/teardown
        if not self.state_manager.is_state(GUIState.ERROR):
            self.state_manager.transition_to(GUIState.IDLE)

        # Pulse state change
        self.state_change_event.set()
        self.state_change_event.clear()

        # Signal “done” last
        self.lifecycle_event.set()
        self._cleanup_done.set()

        if not error_occurred and not self.cancel_token.is_cancelled():
            self.report_progress("Idle", 0.0, "Idle")

    def set_pipeline(self, pipeline) -> None:
        """Set the pipeline instance to use."""
        self._pipeline = pipeline
        if pipeline and hasattr(pipeline, "set_progress_controller"):
            try:
                pipeline.set_progress_controller(self)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.debug("Failed to attach progress controller: %s", exc)

    def set_progress_callback(self, callback: Callable[[float], None] | None) -> None:
        """Register callback for progress percentage updates."""
        with self._progress_lock:
            self._progress_callback = callback

    def set_eta_callback(self, callback: Callable[[str], None] | None) -> None:
        """Register callback for ETA updates."""
        with self._progress_lock:
            self._eta_callback = callback

    def set_status_callback(self, callback: Callable[[str], None] | None) -> None:
        """Register callback for status/stage text updates."""
        with self._progress_lock:
            self._status_callback = callback

    def report_progress(self, stage: str, percent: float, eta: str | None) -> None:
        """Report progress to registered callbacks in a thread-safe manner."""

        eta_text = eta if eta else "ETA: --"
        with self._progress_lock:
            self._last_progress = {
                "stage": stage,
                "percent": float(percent),
                "eta": eta_text,
            }

            if self._status_callback:
                self._status_callback(stage)
            if self._progress_callback:
                self._progress_callback(float(percent))
            if self._eta_callback:
                self._eta_callback(eta_text)

    def _terminate_subprocess(self) -> None:
        """Terminate any running subprocess (e.g., FFmpeg)."""
        with self._subprocess_lock:
            if self._current_subprocess:
                try:
                    self._log("Terminating subprocess...", "INFO")
                    self._current_subprocess.terminate()
                    self._current_subprocess.wait(timeout=3.0)
                    self._log("Subprocess terminated", "INFO")
                except Exception as e:
                    logger.warning(f"Error terminating subprocess: {e}")
                    try:
                        self._current_subprocess.kill()
                    except Exception:
                        pass
                finally:
                    self._current_subprocess = None

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files created during pipeline execution."""
        # Disabled during test debugging due to fatal Windows exception
        pass

    def register_subprocess(self, process: subprocess.Popen) -> None:
        """Register subprocess for cancellation tracking."""
        with self._subprocess_lock:
            self._current_subprocess = process

    def unregister_subprocess(self) -> None:
        """Unregister subprocess."""
        with self._subprocess_lock:
            self._current_subprocess = None

    def _log(self, message: str, level: str = "INFO") -> None:
        """Add message to log queue."""
        self.log_queue.put(LogMessage(message, level))

    def get_log_messages(self) -> list[LogMessage]:
        """Get all pending log messages."""
        messages = []
        while not self.log_queue.empty():
            try:
                messages.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self.state_manager.is_state(GUIState.RUNNING)

    def is_stopping(self) -> bool:
        """Check if pipeline is stopping."""
        return self.state_manager.is_state(GUIState.STOPPING)
