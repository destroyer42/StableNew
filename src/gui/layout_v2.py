from __future__ import annotations

import tkinter as tk


def configure_root_grid(root: tk.Tk) -> None:
    """Apply baseline grid weights and minimum sizes for the V2 app shell."""

    root.rowconfigure(0, weight=1)  # main content
    root.rowconfigure(1, weight=0)  # status bar

    root.columnconfigure(0, weight=0, minsize=260)  # sidebar
    root.columnconfigure(1, weight=3, minsize=500)  # pipeline / main
    root.columnconfigure(2, weight=2, minsize=400)  # preview / history
