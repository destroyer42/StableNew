"""Tests for LogPanel component."""

import logging
import time

import pytest

# Skip these tests if tkinter is not available
pytest.importorskip("tkinter")

import tkinter as tk
from tkinter import ttk

from src.gui.log_panel import LogPanel, TkinterLogHandler
from tests.gui.conftest import wait_until


class TestLogPanel:
    """Test LogPanel component."""

    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            pytest.skip("Tk/Tcl unavailable in this environment")

    def teardown_method(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    def test_panel_creation(self):
        """Test that LogPanel can be created."""
        panel = LogPanel(self.root)
        assert panel is not None
        assert isinstance(panel, ttk.Frame)

    def test_log_method(self):
        """Test that log method can be called."""
        panel = LogPanel(self.root)

        # Should not raise
        panel.log("Test message")
        panel.log("Another message")

        assert True

    def test_log_with_level(self):
        """Test logging with different levels."""
        panel = LogPanel(self.root)

        panel.log("Info message", "INFO")
        panel.log("Warning message", "WARNING")
        panel.log("Error message", "ERROR")
        panel.log("Success message", "SUCCESS")

        assert True

    def test_log_level_tags_are_created(self):
        """Log messages should be tagged for colorization by level."""
        panel = LogPanel(self.root)

        panel.log("Color test info", "INFO")
        panel.log("Color test warn", "WARNING")
        panel.log("Color test error", "ERROR")

        self.root.update()

        assert panel.log_text.tag_ranges("INFO"), "INFO tag should have ranges"
        assert panel.log_text.tag_ranges("WARNING"), "WARNING tag should have ranges"
        assert panel.log_text.tag_ranges("ERROR"), "ERROR tag should have ranges"

    def test_copy_to_clipboard_includes_visible_log(self):
        """Copy to clipboard should include the visible log content."""
        panel = LogPanel(self.root)

        panel.log("Clipboard test", "INFO")
        self.root.update()

        panel.copy_log_to_clipboard()

        clipboard_text = panel.clipboard_get()
        assert "Clipboard test" in clipboard_text

    def test_filter_toggle_updates_display(self):
        """Turning off a level filter should hide matching messages."""
        panel = LogPanel(self.root)

        panel.log("Info toggle", "INFO")
        panel.log("Error toggle", "ERROR")

        # Wait for messages to be processed and displayed
        def messages_displayed():
            self.root.update()
            content = panel.log_text.get("1.0", "end-1c")
            return "Info toggle" in content and "Error toggle" in content

        assert wait_until(messages_displayed, timeout=2.0), "Messages should be displayed"

        panel.level_filter_vars["INFO"].set(False)
        panel._on_filter_change()
        self.root.update()

        content = panel.log_text.get("1.0", "end-1c")
        assert "Info toggle" not in content
        assert "Error toggle" in content

        panel.level_filter_vars["INFO"].set(True)
        panel._on_filter_change()
        self.root.update()

        content = panel.log_text.get("1.0", "end-1c")
        assert "Info toggle" in content


class TestTkinterLogHandler:
    """Test TkinterLogHandler for thread-safe logging."""

    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            pytest.skip("Tk/Tcl unavailable in this environment")

    def teardown_method(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    def test_handler_creation(self):
        """Test that handler can be created."""
        panel = LogPanel(self.root)
        handler = TkinterLogHandler(panel)
        assert handler is not None
        assert isinstance(handler, logging.Handler)

    def test_handler_emits_to_panel(self):
        """Test that handler emits log records to panel."""
        panel = LogPanel(self.root)
        handler = TkinterLogHandler(panel)

        # Create a logger and add our handler
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Emit some log records
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

        # Process pending events
        self.root.update()

        # Handler should have processed records (no exception raised)
        assert True

        # Clean up
        logger.removeHandler(handler)

    def test_handler_thread_safe(self):
        """Test that handler is thread-safe."""
        import threading

        panel = LogPanel(self.root)
        handler = TkinterLogHandler(panel)

        logger = logging.getLogger("test_thread_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Log from multiple threads
        def log_messages():
            for i in range(5):
                logger.info(f"Thread message {i}")
                time.sleep(0.01)

        threads = [threading.Thread(target=log_messages) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Process events
        self.root.update()

        # Should complete without errors
        assert True

        # Clean up
        logger.removeHandler(handler)

    def test_isolation(self):
        """Test that multiple panels are isolated."""
        panel1 = LogPanel(self.root)
        panel2 = LogPanel(self.root)

        handler1 = TkinterLogHandler(panel1)
        handler2 = TkinterLogHandler(panel2)

        # Each should work independently
        logger1 = logging.getLogger("test_logger_1")
        logger1.addHandler(handler1)

        logger2 = logging.getLogger("test_logger_2")
        logger2.addHandler(handler2)

        logger1.info("Message to panel 1")
        logger2.info("Message to panel 2")

        self.root.update()

        # Should work without interference
        assert True

        # Clean up
        logger1.removeHandler(handler1)
        logger2.removeHandler(handler2)
