"""Simple tooltip helper for Tk widgets."""

import tkinter as tk


class Tooltip:
    """Attach a hover tooltip to any Tk widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 1500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id: str | None = None
        self._tooltip: tk.Toplevel | None = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event):
        self._schedule()

    def _on_leave(self, _event=None):
        self._cancel()
        self._hide_tooltip()

    def _schedule(self):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show_tooltip)

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show_tooltip(self):
        if self._tooltip or not self.text:
            return
        self._tooltip = tk.Toplevel(self.widget)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.configure(bg="#202020")
        try:
            x, y, cx, cy = self.widget.bbox("insert") or (0, 0, 0, 0)
        except Exception:
            x = y = cx = cy = 0
        screen_x = self.widget.winfo_rootx() + x + cx + 10
        screen_y = self.widget.winfo_rooty() + y + cy + 10
        self._tooltip.wm_geometry(f"+{screen_x}+{screen_y}")
        label = tk.Label(
            self._tooltip,
            text=self.text,
            justify=tk.LEFT,
            background="#202020",
            foreground="#ffffff",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 8),
            wraplength=300,
        )
        label.pack(ipadx=6, ipady=4)

    def _hide_tooltip(self):
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None
