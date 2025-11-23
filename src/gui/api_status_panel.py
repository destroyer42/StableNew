"""
APIStatusPanel - UI component for displaying API connection status.

Shows current WebUI/API connection health and exposes a reconnect hook.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from src.controller.webui_connection_controller import WebUIConnectionState

logger = logging.getLogger(__name__)


class APIStatusPanel(ttk.Frame):
    """A UI panel for API connection status display."""

    def __init__(self, parent: tk.Widget, coordinator: object | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.coordinator = coordinator
        self._reconnect_callback = None
        self._build_ui()

    def _build_ui(self):
        status_frame = ttk.Frame(self, style="Dark.TFrame", relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, expand=True)

        self.status_indicator = ttk.Label(
            status_frame,
            text="?",
            style="Dark.TLabel",
            foreground="#888888",
            font=("Segoe UI", 12, "bold"),
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(5, 2))

        self.status_label = ttk.Label(
            status_frame, text="Not connected", style="Dark.TLabel", font=("Segoe UI", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=(2, 5))

        self.reconnect_button = ttk.Button(status_frame, text="Reconnect", command=self._on_reconnect_clicked)
        self.reconnect_button.pack(side=tk.RIGHT, padx=(6, 4))

    def set_status(self, text: str, color: str = "gray") -> None:
        color_map = {
            "green": "#4CAF50",
            "yellow": "#FF9800",
            "orange": "#FF9800",
            "red": "#f44336",
            "gray": "#888888",
            "grey": "#888888",
        }
        hex_color = color_map.get(color.lower(), color)
        self.status_indicator.config(foreground=hex_color)
        self.status_label.config(text=text)
        try:
            self.update_idletasks()
        except Exception:
            pass
        logger.debug("API status set to: %s (%s)", text, color)

    def set_webui_state(self, state: WebUIConnectionState) -> None:
        mapping = {
            WebUIConnectionState.READY: ("WebUI: Ready", "green"),
            WebUIConnectionState.CONNECTING: ("WebUI: Connecting", "yellow"),
            WebUIConnectionState.ERROR: ("WebUI: Error", "red"),
            WebUIConnectionState.DISCONNECTED: ("WebUI: Disconnected", "orange"),
            WebUIConnectionState.DISABLED: ("WebUI: Disabled", "gray"),
        }
        text, color = mapping.get(state, ("WebUI: Unknown", "gray"))
        self.set_status(text, color=color)

    def set_reconnect_callback(self, callback):
        self._reconnect_callback = callback

    def _on_reconnect_clicked(self):
        if callable(self._reconnect_callback):
            try:
                self._reconnect_callback()
            except Exception:
                logger.debug("Reconnect callback failed", exc_info=True)


__all__ = ["APIStatusPanel"]
