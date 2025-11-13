"""Shared helpers for scrollable Tk/ttk containers."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


SCROLL_CANVAS_BG = "#2B2A2C"


def enable_mousewheel(widget: tk.Widget) -> None:
    """Enable mousewheel scrolling for the given widget in a cross-platform way."""

    def _on_mousewheel(event):
        delta = event.delta
        if delta == 0 and getattr(event, "num", None) in (4, 5):
            delta = 120 if event.num == 4 else -120
        step = int(-1 * (delta / 120))
        try:
            widget.yview_scroll(step, "units")
        except Exception:
            return
        return "break"

    def _bind(_event):
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_mousewheel)
        widget.bind_all("<Button-5>", _on_mousewheel)

    def _unbind(_event):
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    widget.bind("<Enter>", _bind, add="+")
    widget.bind("<Leave>", _unbind, add="+")


def make_scrollable(parent: tk.Widget, *, style: str = "Dark.TFrame") -> tuple[tk.Canvas, tk.Frame]:
    """Create a scrollable region inside *parent* using a canvas + frame + scrollbar."""

    canvas = tk.Canvas(parent, bg=SCROLL_CANVAS_BG, highlightthickness=0, borderwidth=0)
    scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas, style=style)

    window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def _on_frame_config(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_config(event):
        canvas.itemconfigure(window_id, width=event.width)

    scrollable_frame.bind("<Configure>", _on_frame_config)
    canvas.bind("<Configure>", _on_canvas_config)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    enable_mousewheel(canvas)

    # Expose scrollbar for callers/tests when needed
    canvas._vertical_scrollbar = scrollbar  # type: ignore[attr-defined]
    scrollable_frame._vertical_scrollbar = scrollbar  # type: ignore[attr-defined]

    return canvas, scrollable_frame
