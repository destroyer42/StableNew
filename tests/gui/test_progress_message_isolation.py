"""Test that log polling doesn't clobber progress message."""

import time
from unittest import mock

import pytest


@pytest.fixture
def minimal_app(tk_root, monkeypatch):
    """Create a minimal StableNewGUI instance for testing log isolation."""

    from src.gui import main_window as main_window_module
    from src.gui.controller import LogMessage

    # Reuse provided Tk root
    monkeypatch.setattr(main_window_module.tk, "Tk", lambda: tk_root)

    # Disable heavy startup
    monkeypatch.setattr(main_window_module.StableNewGUI, "_launch_webui", lambda self: None)
    monkeypatch.setattr(main_window_module.StableNewGUI, "_initialize_ui_state", lambda self: None)

    def minimal_build_ui(self):
        """Minimal UI for testing."""
        self.progress_message_var = main_window_module.tk.StringVar(value="Ready")
        self.log_messages = []

    def minimal_log_message(self, message, level="INFO"):
        """Capture log messages."""
        self.log_messages.append((message, level))

    def minimal_state_callbacks(self):
        """Setup minimal state callbacks."""
        from src.gui.state import GUIState

        def on_state_change(old_state, new_state):
            if new_state == GUIState.RUNNING:
                self.progress_message_var.set("Running pipeline...")
            elif new_state == GUIState.STOPPING:
                self.progress_message_var.set("Cancelling pipeline...")
            elif new_state == GUIState.IDLE and old_state == GUIState.STOPPING:
                self.progress_message_var.set("Ready")
            elif new_state == GUIState.ERROR:
                self.progress_message_var.set("Error")

        self.state_manager.on_transition(on_state_change)

    monkeypatch.setattr(main_window_module.StableNewGUI, "_build_ui", minimal_build_ui)
    monkeypatch.setattr(main_window_module.StableNewGUI, "log_message", minimal_log_message)
    monkeypatch.setattr(main_window_module.StableNewGUI, "_setup_state_callbacks", minimal_state_callbacks)

    app = main_window_module.StableNewGUI()
    yield app

    # Teardown
    if hasattr(app, "controller"):
        app.controller.cancel_token.cancel()


@pytest.mark.gui
def test_poll_controller_logs_does_not_clobber_progress_message(minimal_app, tk_pump):
    """Verify that polling controller logs doesn't overwrite progress_message_var."""

    from src.gui.controller import LogMessage

    # Set an explicit progress message (simulating a stage update)
    minimal_app.progress_message_var.set("txt2img (50%)")
    initial_progress = minimal_app.progress_message_var.get()

    # Inject log messages into controller
    minimal_app.controller.log_queue.put(LogMessage("Processing image 1/10", "INFO"))
    minimal_app.controller.log_queue.put(LogMessage("Applying upscale...", "INFO"))

    # Poll the controller logs
    minimal_app._poll_controller_logs()

    # Pump events to ensure any after() callbacks are processed
    tk_pump(0.1)

    # Verify the log messages were processed
    assert len(minimal_app.log_messages) == 2
    assert minimal_app.log_messages[0][0] == "Processing image 1/10"
    assert minimal_app.log_messages[1][0] == "Applying upscale..."

    # The critical assertion: progress_message_var should NOT have been changed
    assert minimal_app.progress_message_var.get() == initial_progress
    assert minimal_app.progress_message_var.get() == "txt2img (50%)"


@pytest.mark.gui
def test_progress_message_not_clobbered_when_set_manually(minimal_app, tk_pump):
    """Verify that manually set progress messages are preserved when logs arrive."""

    from src.gui.controller import LogMessage

    # Manually set a progress message (like a future progress helper would do)
    minimal_app.progress_message_var.set("Upscaling images (75%)")

    # Log messages arrive
    minimal_app.controller.log_queue.put(LogMessage("Processing...", "INFO"))
    minimal_app._poll_controller_logs()
    tk_pump(0.05)

    # Progress message should be unchanged
    assert minimal_app.progress_message_var.get() == "Upscaling images (75%)"

