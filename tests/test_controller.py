"""Tests for pipeline controller."""

import pytest
import time
import threading
from src.gui.controller import PipelineController, LogMessage
from src.gui.state import StateManager, GUIState, CancellationError


class TestLogMessage:
    """Tests for LogMessage."""

    def test_creation(self):
        """Test log message creation."""
        msg = LogMessage("test message", "INFO")
        assert msg.message == "test message"
        assert msg.level == "INFO"
        assert msg.timestamp > 0

    def test_default_level(self):
        """Test default log level."""
        msg = LogMessage("test")
        assert msg.level == "INFO"


class TestPipelineController:
    """Tests for PipelineController."""

    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        state_manager = StateManager()
        return PipelineController(state_manager)

    def test_initial_state(self, controller):
        """Test initial controller state."""
        assert not controller.is_running()
        assert not controller.is_stopping()
        assert controller.state_manager.current == GUIState.IDLE

    def test_start_pipeline_success(self, controller):
        """Test successful pipeline start."""
        completed = []

        def pipeline_func():
            time.sleep(0.05)  # Small delay to ensure we can check running state
            return {"status": "success"}

        def on_complete(result):
            completed.append(result)

        started = controller.start_pipeline(pipeline_func, on_complete=on_complete)
        assert started

        # Give thread a moment to actually start
        time.sleep(0.01)
        assert controller.is_running()

        # Wait for completion
        controller.worker_thread.join(timeout=1.0)

        assert len(completed) == 1
        assert completed[0]["status"] == "success"
        assert controller.state_manager.current == GUIState.IDLE

    def test_start_pipeline_already_running(self, controller):
        """Test cannot start pipeline when already running."""

        def long_pipeline():
            time.sleep(0.5)
            return {}

        controller.start_pipeline(long_pipeline)
        assert controller.is_running()

        # Try to start again
        started = controller.start_pipeline(long_pipeline)
        assert not started

        # Cleanup
        controller.stop_pipeline()
        if controller.worker_thread:
            controller.worker_thread.join(timeout=1.0)

    def test_pipeline_error_handling(self, controller):
        """Test pipeline error handling."""
        errors = []

        def failing_pipeline():
            raise ValueError("Test error")

        def on_error(e):
            errors.append(e)

        controller.start_pipeline(failing_pipeline, on_error=on_error)
        time.sleep(0.1)
        controller.worker_thread.join(timeout=1.0)

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert controller.state_manager.current == GUIState.ERROR

    def test_pipeline_cancellation(self, controller):
        """Test pipeline cancellation."""
        started = []
        completed = []

        def cancellable_pipeline():
            started.append(True)
            for i in range(100):
                controller.cancel_token.check_cancelled()
                time.sleep(0.01)
            completed.append(True)
            return {}

        controller.start_pipeline(cancellable_pipeline)
        time.sleep(0.05)  # Let it start

        assert len(started) == 1
        assert len(completed) == 0

        # Stop the pipeline
        stopped = controller.stop_pipeline()
        assert stopped
        assert controller.is_stopping() or controller.state_manager.current == GUIState.IDLE

        # Wait for cleanup
        time.sleep(0.2)

        # Should not have completed
        assert len(completed) == 0

    def test_stop_when_not_running(self, controller):
        """Test stop does nothing when not running."""
        stopped = controller.stop_pipeline()
        assert not stopped

    def test_log_messages(self, controller):
        """Test log message queuing."""
        controller._log("Test message 1", "INFO")
        controller._log("Test message 2", "WARNING")

        messages = controller.get_log_messages()
        assert len(messages) == 2
        assert messages[0].message == "Test message 1"
        assert messages[0].level == "INFO"
        assert messages[1].message == "Test message 2"
        assert messages[1].level == "WARNING"

        # Queue should be empty now
        messages = controller.get_log_messages()
        assert len(messages) == 0

    def test_cancel_token_reset(self, controller):
        """Test cancel token is reset on new run."""

        def quick_pipeline():
            return {}

        # First run
        controller.start_pipeline(quick_pipeline)
        time.sleep(0.1)
        if controller.worker_thread:
            controller.worker_thread.join(timeout=1.0)

        # Cancel
        controller.cancel_token.cancel()
        assert controller.cancel_token.is_cancelled()

        # Start new run - token should be reset
        controller.state_manager.reset()
        controller.start_pipeline(quick_pipeline)
        assert not controller.cancel_token.is_cancelled()

        # Cleanup
        time.sleep(0.1)
        if controller.worker_thread:
            controller.worker_thread.join(timeout=1.0)

    def test_subprocess_registration(self, controller):
        """Test subprocess registration for cancellation."""
        import subprocess

        # Create dummy subprocess
        proc = subprocess.Popen(["sleep", "10"])

        try:
            controller.register_subprocess(proc)
            assert controller._current_subprocess == proc

            controller.unregister_subprocess()
            assert controller._current_subprocess is None
        finally:
            # Cleanup
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                pass
