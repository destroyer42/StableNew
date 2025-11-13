"""
LogPanel - UI component for displaying live log messages.

This panel provides a scrolling log view with thread-safe logging handler integration.
"""

import logging
import queue
import tkinter as tk
from tkinter import scrolledtext, ttk

logger = logging.getLogger(__name__)


LEVEL_STYLES: dict[str, str] = {
    "DEBUG": "#888888",
    "INFO": "#4CAF50",
    "SUCCESS": "#2196F3",
    "WARNING": "#FF9800",
    "ERROR": "#f44336",
}

LEVEL_ORDER: tuple[str, ...] = tuple(LEVEL_STYLES.keys())
DEFAULT_LEVEL = "INFO"


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

        # Buffer to support filtering and clipboard operations
        self.log_records: list[tuple[str, str]] = []
        self.max_log_lines = 1000
        self._line_count = 0

        # Scroll and filter state
        self.scroll_lock_var = tk.BooleanVar(master=self, value=False)
        self.level_filter_vars: dict[str, tk.BooleanVar] = {}

        # Build UI
        self._build_ui()

        # Start queue processing
        self._process_queue()

    def _build_ui(self):
        """Build the panel UI."""
        # Log frame with dark theme
        log_frame = ttk.LabelFrame(self, text="📋 Live Log", style="Dark.TLabelframe", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(log_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Checkbutton(
            controls_frame,
            text="Scroll Lock",
            variable=self.scroll_lock_var,
            command=self._on_scroll_lock_toggle,
        ).pack(side=tk.LEFT)

        ttk.Button(
            controls_frame,
            text="Copy Log",
            command=self.copy_log_to_clipboard,
        ).pack(side=tk.RIGHT)

        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        for level in LEVEL_ORDER:
            var = tk.BooleanVar(master=self, value=True)
            self.level_filter_vars[level] = var
            ttk.Checkbutton(
                filter_frame,
                text=level.title(),
                variable=var,
                command=self._on_filter_change,
            ).pack(side=tk.LEFT, padx=(0, 4))

        # Scrolled text widget
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=self.height,
            wrap=tk.WORD,
            bg="#2B2A2C",  # ASWF_DARK_GREY
            fg="#FFC805",  # ASWF_GOLD
            font=("Calibri", 11),  # Consistent with theme
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        for level, color in LEVEL_STYLES.items():
            self.log_text.tag_configure(level, foreground=color)

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
        try:
            self.after(0, self._process_queue)
        except Exception:
            pass

    def append(self, message: str, level: str = "INFO") -> None:
        """
        Append a log message to the display (alias for log()).

        This method is thread-safe and can be called from any thread.

        Args:
            message: Log message text
            level: Log level (INFO, WARNING, ERROR, SUCCESS, DEBUG)
        """
        self.log(message, level)

    def _process_queue(self):
        """Process pending log messages from queue."""
        # Process all pending messages
        while not self.log_queue.empty():
            try:
                message, level = self.log_queue.get_nowait()
                try:
                    self._add_log_message(message, level)
                except Exception:
                    # Ignore UI errors (widget may be destroyed during teardown)
                    pass
            except queue.Empty:
                break

        # Schedule next processing
        self.after(100, self._process_queue)

    # Test/utility: process queued log messages synchronously (no scheduling)
    def _flush_queue_sync(self) -> None:
        """Synchronously flush the log queue; intended for tests."""
        while not self.log_queue.empty():
            try:
                message, level = self.log_queue.get_nowait()
                self._add_log_message(message, level)
            except queue.Empty:
                break

    def _add_log_message(self, message: str, level: str) -> None:
        """
        Add a log message to the text widget (must be called on main thread).

        Args:
            message: Log message text
            level: Log level for coloring
        """
        normalized_level = level.upper()
        if normalized_level not in LEVEL_STYLES:
            logger.debug(
                f"Unknown log level '{level}' encountered; falling back to DEFAULT_LEVEL ('{DEFAULT_LEVEL}')."
            )
            normalized_level = DEFAULT_LEVEL

        self.log_records.append((message, normalized_level))

        if len(self.log_records) > self.max_log_lines:
            # Only trim and refresh when the log first exceeds the limit
            self.log_records = self.log_records[-self.max_log_lines :]
            self._refresh_display()
            return
        elif len(self.log_records) == self.max_log_lines:
            # Already at limit, pop oldest and insert efficiently
            self.log_records.pop(0)
            self.log_records.append((message, normalized_level))
            if self._should_display(normalized_level):
                self._insert_message(message, normalized_level)
            return

        if self._should_display(normalized_level):
            self._insert_message(message, normalized_level)

    def _insert_message(self, message: str, level: str) -> None:
        preserve_pos = bool(self.scroll_lock_var.get())
        try:
            top_before = self.log_text.yview()[0] if preserve_pos else None
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{message}\n", level)
            if not self.scroll_lock_var.get():
                self.log_text.see(tk.END)
            elif top_before is not None:
                try:
                    self.log_text.yview_moveto(top_before)
                except Exception:
                    pass
            self.log_text.configure(state=tk.DISABLED)
        except Exception:
            # Widget likely destroyed; safely ignore
            return
        if self._should_display(level) and self._line_count < self.max_log_lines:
            self._line_count += 1

    def _should_display(self, level: str) -> bool:
        var = self.level_filter_vars.get(level)
        return True if var is None else bool(var.get())

    def _refresh_display(self) -> None:
        preserve_pos = bool(self.scroll_lock_var.get())
        try:
            top_before = self.log_text.yview()[0] if preserve_pos else None
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            visible_count = 0
            for message, level in self.log_records:
                if self._should_display(level):
                    self.log_text.insert(tk.END, f"{message}\n", level)
                    visible_count += 1
            if not self.scroll_lock_var.get():
                self.log_text.see(tk.END)
            elif preserve_pos and top_before is not None:
                try:
                    self.log_text.yview_moveto(top_before)
                except Exception:
                    pass
            self.log_text.configure(state=tk.DISABLED)
            self._line_count = min(visible_count, self.max_log_lines)
        except Exception:
            # Widget likely destroyed; ignore refresh request
            pass

    def _on_filter_change(self) -> None:
        self._refresh_display()

    def _on_scroll_lock_toggle(self) -> None:
        if not self.scroll_lock_var.get():
            # Unlock: follow new messages
            self.log_text.see(tk.END)
            if hasattr(self, "_locked_view_top"):
                delattr(self, "_locked_view_top")
        else:
            # Lock: preserve current view top
            try:
                self._locked_view_top = self.log_text.yview()[0]
            except Exception:
                self._locked_view_top = 0.0

    # Convenience API expected by tests
    @property
    def text(self) -> scrolledtext.ScrolledText:
        """Return the underlying text widget (for legacy compatibility)."""
        return self.log_text

    def get_scroll_lock(self) -> bool:
        """Return True if scroll lock is enabled, else False."""
        return bool(self.scroll_lock_var.get())

    def set_scroll_lock(self, enabled: bool) -> None:
        """Enable or disable scroll lock and apply behavior immediately."""
        self.scroll_lock_var.set(bool(enabled))
        self._on_scroll_lock_toggle()

    def copy_log_to_clipboard(self) -> None:
        """Copy the current log contents to the system clipboard."""
        content = self.log_text.get("1.0", tk.END).strip()
        try:
            self.clipboard_clear()
            if content:
                self.clipboard_append(content)
            self._clipboard_cache = content
        except tk.TclError:
            logger.debug("Clipboard unavailable for log copy")
            self._clipboard_cache = content

    def clear(self) -> None:
        """Clear all log messages."""
        self.log_records.clear()
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self._line_count = 0
            self.log_text.configure(state=tk.DISABLED)
        except Exception:
            # Widget may be destroyed
            self._line_count = 0

    def clipboard_get(self, **kw):  # type: ignore[override]
        try:
            return super().clipboard_get(**kw)
        except tk.TclError:
            return getattr(self, "_clipboard_cache", "")


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
