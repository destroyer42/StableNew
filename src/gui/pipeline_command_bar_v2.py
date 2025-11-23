"""Command bar widget for primary pipeline actions in the V2 layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod


class PipelineCommandBarV2(ttk.Frame):
    """Hosts Run, Stop, and Queue mode controls for the pipeline panel."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        theme=None,
        queue_enabled: bool = False,
        on_queue_toggle=None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_SM, **kwargs)
        self.theme = theme
        self._queue_toggle_callback = on_queue_toggle
        self.queue_var = tk.BooleanVar(master=self, value=bool(queue_enabled))

        run_style = getattr(theme, "PRIMARY_BUTTON_STYLE", theme_mod.PRIMARY_BUTTON_STYLE)
        stop_style = getattr(theme, "DANGER_BUTTON_STYLE", theme_mod.DANGER_BUTTON_STYLE)

        self.run_button = ttk.Button(self, text="Run Full Pipeline", style=run_style)
        self.stop_button = ttk.Button(self, text="Stop", style=stop_style)
        self.queue_toggle = ttk.Checkbutton(
            self,
            text="Queue mode",
            variable=self.queue_var,
            command=self._handle_queue_toggle,
        )

        self.run_button.pack(side=tk.LEFT, padx=(0, theme_mod.PADDING_SM))
        self.stop_button.pack(side=tk.LEFT, padx=(0, theme_mod.PADDING_SM))
        self.queue_toggle.pack(side=tk.LEFT, padx=(theme_mod.PADDING_SM, 0))

    def set_running_state(self, is_running: bool) -> None:
        """Enable/disable controls based on running state."""

        state = tk.DISABLED if is_running else tk.NORMAL
        try:
            self.run_button.config(state=state)
        except Exception:
            pass
        try:
            self.stop_button.config(state=tk.NORMAL if is_running else tk.NORMAL)
        except Exception:
            pass

    def set_queue_mode(self, enabled: bool) -> None:
        """Update the queue toggle state without firing callbacks."""

        try:
            self.queue_var.set(bool(enabled))
        except Exception:
            pass

    def get_queue_mode(self) -> bool:
        """Return the current queue toggle value."""

        return bool(self.queue_var.get())

    def set_queue_toggle_callback(self, callback) -> None:
        """Replace the queue toggle callback."""

        self._queue_toggle_callback = callback

    def _handle_queue_toggle(self) -> None:
        if callable(self._queue_toggle_callback):
            try:
                self._queue_toggle_callback(self.get_queue_mode())
            except Exception:
                pass
