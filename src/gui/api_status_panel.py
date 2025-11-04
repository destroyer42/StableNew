"""
APIStatusPanel - UI component for displaying API connection status.

This panel shows the current API connection status with colored indicators.
"""

import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class APIStatusPanel(ttk.Frame):
    """
    A UI panel for API connection status display.

    This panel handles:
    - Displaying connection status text
    - Color-coded status indicators (green=connected, yellow=connecting, red=error)
    - Simple set_status(text, color) API
    """

    def __init__(self, parent: tk.Widget, coordinator: object | None = None, **kwargs):
        """
        Initialize the APIStatusPanel.

        Args:
            parent: Parent widget
            coordinator: Coordinator object (for mediator pattern)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.coordinator = coordinator

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the panel UI."""
        # Status bar with dark theme
        status_frame = ttk.Frame(self, style="Dark.TFrame", relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, expand=True)

        # Status indicator
        self.status_indicator = ttk.Label(
            status_frame,
            text="●",
            style="Dark.TLabel",
            foreground="#888888",  # Default gray
            font=("Segoe UI", 12, "bold"),
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(5, 2))

        # Status text
        self.status_label = ttk.Label(
            status_frame, text="Not connected", style="Dark.TLabel", font=("Segoe UI", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=(2, 5))

    def set_status(self, text: str, color: str = "gray") -> None:
        """
        Set the status display.

        Args:
            text: Status text to display
            color: Color for the indicator (green, yellow, red, gray)
        """
        # Map color names to hex codes
        color_map = {
            "green": "#4CAF50",
            "yellow": "#FF9800",
            "orange": "#FF9800",
            "red": "#f44336",
            "gray": "#888888",
            "grey": "#888888",
        }

        # Get hex color
        hex_color = color_map.get(color.lower(), color)

        # Update UI (thread-safe via after)
        def update():
            self.status_indicator.config(foreground=hex_color)
            self.status_label.config(text=text)

        # Schedule update on main thread
        try:
            self.after(0, update)
        except:
            # Fallback if not in main thread
            update()

        logger.debug(f"API status set to: {text} ({color})")
