"""Pipeline controller with cancellation support."""

import threading
import queue
import logging
import time
import subprocess
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from .state import StateManager, GUIState, CancelToken, CancellationError

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

    def __init__(self, state_manager: StateManager):
        """Initialize pipeline controller.

        Args:
            state_manager: State manager instance
        """
        self.state_manager = state_manager
        self.cancel_token = CancelToken()
        self.log_queue: queue.Queue[LogMessage] = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self._pipeline = None
        self._current_subprocess: Optional[subprocess.Popen] = None
        self._subprocess_lock = threading.Lock()

    def set_pipeline(self, pipeline) -> None:
        """Set the pipeline instance to use.

        Args:
            pipeline: Pipeline executor instance
        """
        self._pipeline = pipeline

    def start_pipeline(
        self,
        pipeline_func: Callable[[], Dict[str, Any]],
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> bool:
        """Start pipeline execution in background thread.

        Args:
            pipeline_func: Function to execute (should check cancel_token)
            on_complete: Callback for successful completion
            on_error: Callback for errors

        Returns:
            True if started, False if already running
        """
        if not self.state_manager.can_run():
            logger.warning("Cannot start pipeline - not in valid state")
            return False

        if not self.state_manager.transition_to(GUIState.RUNNING):
            return False

        # Reset cancel token for new run
        self.cancel_token.reset()

        def worker():
            """Worker thread function."""
            try:
                self._log("Pipeline started", "INFO")
                start_time = time.time()

                # Execute pipeline function
                result = pipeline_func()

                elapsed = time.time() - start_time
                self._log(f"Pipeline completed in {elapsed:.1f}s", "SUCCESS")

                # Transition to IDLE on success
                self.state_manager.transition_to(GUIState.IDLE)

                # Call completion callback
                if on_complete:
                    on_complete(result)

            except CancellationError:
                self._log("Pipeline cancelled by user", "WARNING")
                self.state_manager.transition_to(GUIState.IDLE)

            except Exception as e:
                logger.exception("Pipeline error")
                self._log(f"Pipeline error: {str(e)}", "ERROR")
                self.state_manager.transition_to(GUIState.ERROR)

                if on_error:
                    on_error(e)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
        return True

    def stop_pipeline(self) -> bool:
        """Request pipeline cancellation.

        Returns:
            True if stop requested, False if not running
        """
        if not self.state_manager.can_stop():
            logger.warning("Cannot stop pipeline - not running")
            return False

        self._log("Stop requested - cancelling pipeline...", "WARNING")

        # Transition to STOPPING state
        if not self.state_manager.transition_to(GUIState.STOPPING):
            return False

        # Set cancel token
        self.cancel_token.cancel()

        # Try to terminate any subprocess
        self._terminate_subprocess()

        # Start cleanup thread
        def cleanup():
            """Cleanup after cancellation."""
            # Wait for worker to finish (with timeout)
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5.0)

            # Cleanup temporary files
            self._cleanup_temp_files()

            # Transition back to IDLE
            if self.state_manager.is_state(GUIState.STOPPING):
                self.state_manager.transition_to(GUIState.IDLE)
                self._log("Pipeline stopped and cleaned up", "INFO")

        threading.Thread(target=cleanup, daemon=True).start()
        return True

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
        try:
            # Look for temp directories
            temp_dirs = [Path("tmp"), Path("temp")]
            for temp_dir in temp_dirs:
                if temp_dir.exists() and temp_dir.is_dir():
                    # Only clean up files from current session
                    # This is a placeholder - implement actual cleanup logic
                    pass
        except Exception as e:
            logger.warning(f"Error cleaning temp files: {e}")

    def register_subprocess(self, process: subprocess.Popen) -> None:
        """Register subprocess for cancellation tracking.

        Args:
            process: Subprocess to track
        """
        with self._subprocess_lock:
            self._current_subprocess = process

    def unregister_subprocess(self) -> None:
        """Unregister subprocess."""
        with self._subprocess_lock:
            self._current_subprocess = None

    def _log(self, message: str, level: str = "INFO") -> None:
        """Add message to log queue.

        Args:
            message: Log message
            level: Log level
        """
        self.log_queue.put(LogMessage(message, level))

    def get_log_messages(self) -> list[LogMessage]:
        """Get all pending log messages.

        Returns:
            List of log messages
        """
        messages = []
        while not self.log_queue.empty():
            try:
                messages.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def is_running(self) -> bool:
        """Check if pipeline is currently running.

        Returns:
            True if running, False otherwise
        """
        return self.state_manager.is_state(GUIState.RUNNING)

    def is_stopping(self) -> bool:
        """Check if pipeline is stopping.

        Returns:
            True if stopping, False otherwise
        """
        return self.state_manager.is_state(GUIState.STOPPING)
