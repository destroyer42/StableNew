"""
LogPanel - UI component for displaying live log messages.

This panel provides a scrolling log view with thread-safe logging handler integration.
"""

import logging
import queue
import tkinter as tk
from tkinter import scrolledtext, ttk

logger = logging.getLogger(__name__)


class LogPanel(ttk.Frame):
    """
    A UI panel for displaying live log messages.

    This panel handles:
    - Scrolled text widget for log display
    - Color-coded log levels (INFO, WARNING, ERROR, SUCCESS)
    - Thread-safe log message queue
    - log(message, level) API for direct logging
    """

    def __init__(
        self, parent: tk.Widget, coordinator: object | None = None, height: int = 6, **kwargs
    ):
        """
        Initialize the LogPanel.

        Args:
            parent: Parent widget
            coordinator: Coordinator object (for mediator pattern)
            height: Height of log text widget in lines
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.coordinator = coordinator
        self.height = height

        # Message queue for thread-safe logging
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        # Build UI
        self._build_ui()

        # Start queue processing
        self._process_queue()

    def _build_ui(self):
        """Build the panel UI."""
        # Log frame with dark theme
        log_frame = ttk.LabelFrame(self, text="📋 Live Log", style="Dark.TFrame", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Scrolled text widget
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=self.height,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Consolas", 8),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure log level colors
        self.log_text.tag_configure("INFO", foreground="#4CAF50")
        self.log_text.tag_configure("WARNING", foreground="#FF9800")
        self.log_text.tag_configure("ERROR", foreground="#f44336")
        self.log_text.tag_configure("SUCCESS", foreground="#2196F3")
        self.log_text.tag_configure("DEBUG", foreground="#888888")

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Add a log message to the display.

        This method is thread-safe and can be called from any thread.

        Args:
            message: Log message text
            level: Log level (INFO, WARNING, ERROR, SUCCESS, DEBUG)
        """
        # Add to queue for processing on main thread
        self.log_queue.put((message, level))

    def _process_queue(self):
        """Process pending log messages from queue."""
        # Process all pending messages
        while not self.log_queue.empty():
            try:
                message, level = self.log_queue.get_nowait()
                self._add_log_message(message, level)
            except queue.Empty:
                break

        # Schedule next processing
        self.after(100, self._process_queue)

    def _add_log_message(self, message: str, level: str) -> None:
        """
        Add a log message to the text widget (must be called on main thread).

        Args:
            message: Log message text
            level: Log level for coloring
        """
        # Enable editing temporarily
        self.log_text.configure(state=tk.NORMAL)

        # Insert message with appropriate tag
        self.log_text.insert(tk.END, f"{message}\n", level)

        # Scroll to end
        self.log_text.see(tk.END)

        # Disable editing
        self.log_text.configure(state=tk.DISABLED)

        # Limit log size (keep last 1000 lines)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 1000:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", f"{line_count - 1000}.0")
            self.log_text.configure(state=tk.DISABLED)

    def clear(self) -> None:
        """Clear all log messages."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)


class TkinterLogHandler(logging.Handler):
    """
    Logging handler that forwards log records to a LogPanel.

    This handler is thread-safe and can be used to redirect Python logging
    to the GUI log display.
    """

    def __init__(self, log_panel: LogPanel):
        """
        Initialize the handler.

        Args:
            log_panel: LogPanel instance to send log messages to
        """
        super().__init__()
        self.log_panel = log_panel

        # Set default format
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        self.setFormatter(formatter)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the panel.

        Args:
            record: Log record to emit
        """
        try:
            # Format the message
            message = self.format(record)

            # Map logging level to panel level
            level_map = {
                logging.DEBUG: "DEBUG",
                logging.INFO: "INFO",
                logging.WARNING: "WARNING",
                logging.ERROR: "ERROR",
                logging.CRITICAL: "ERROR",
            }

            level = level_map.get(record.levelno, "INFO")

            # Send to panel (thread-safe)
            self.log_panel.log(message, level)

        except Exception:
            # Don't let logging errors break the app
            self.handleError(record)
