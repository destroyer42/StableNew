"""Shared theming helpers for the Architecture_v2 GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Color palette
COLOR_BG = "#18181b"
COLOR_SURFACE = "#1f1f25"
COLOR_SURFACE_ALT = "#24242b"
COLOR_ACCENT = "#facc15"
COLOR_ACCENT_DANGER = "#ef4444"
COLOR_TEXT = "#f9fafb"
COLOR_TEXT_MUTED = "#9ca3af"
COLOR_BORDER_SUBTLE = "#3f3f46"

# Spacing tokens
PADDING_XS = 2
PADDING_SM = 4
PADDING_MD = 8
PADDING_LG = 12

# Font families
FONT_FAMILY_BASE = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

# Style identifiers
PRIMARY_BUTTON_STYLE = "Primary.TButton"
DANGER_BUTTON_STYLE = "Danger.TButton"
GHOST_BUTTON_STYLE = "Ghost.TButton"
STATUS_LABEL_STYLE = "Status.TLabel"
STATUS_STRONG_LABEL_STYLE = "StatusStrong.TLabel"
SURFACE_FRAME_STYLE = "Surface.TFrame"
HEADER_FRAME_STYLE = "Header.TFrame"


def configure_style(root: tk.Misc) -> ttk.Style:
    """Configure ttk styles for StableNew's dark theme."""

    style = ttk.Style(master=root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLOR_BG)

    # Base frame styling
    style.configure("TFrame", background=COLOR_BG)
    style.configure(
        SURFACE_FRAME_STYLE,
        background=COLOR_SURFACE,
    )
    style.configure(
        HEADER_FRAME_STYLE,
        background=COLOR_SURFACE_ALT,
    )

    # Buttons
    style.configure(
        PRIMARY_BUTTON_STYLE,
        padding=(PADDING_MD, PADDING_SM),
        background=COLOR_ACCENT,
        foreground="#000000",
        borderwidth=0,
        focusthickness=0,
        font=(FONT_FAMILY_BASE, 10, "bold"),
    )
    style.map(
        PRIMARY_BUTTON_STYLE,
        background=[("pressed", "#e7b40f"), ("active", "#fde047")],
    )

    style.configure(
        DANGER_BUTTON_STYLE,
        padding=(PADDING_MD, PADDING_SM),
        background=COLOR_ACCENT_DANGER,
        foreground="#ffffff",
        borderwidth=0,
        focusthickness=0,
        font=(FONT_FAMILY_BASE, 10, "bold"),
    )
    style.map(
        DANGER_BUTTON_STYLE,
        background=[("pressed", "#dc2626"), ("active", "#f87171")],
    )

    style.configure(
        GHOST_BUTTON_STYLE,
        padding=(PADDING_MD - 2, PADDING_SM),
        background=COLOR_SURFACE_ALT,
        foreground=COLOR_TEXT,
        borderwidth=1,
        focusthickness=0,
        relief="raised",
        font=(FONT_FAMILY_BASE, 10),
        bordercolor=COLOR_BORDER_SUBTLE,
        lightcolor=COLOR_BORDER_SUBTLE,
        darkcolor=COLOR_BORDER_SUBTLE,
    )
    style.map(
        GHOST_BUTTON_STYLE,
        background=[
            ("pressed", "#3a3a45"),
            ("active", "#2b2b34"),
        ],
        foreground=[
            ("pressed", COLOR_TEXT),
            ("active", COLOR_TEXT),
        ],
        relief=[("pressed", "sunken"), ("active", "raised")],
        bordercolor=[
            ("pressed", COLOR_ACCENT),
            ("active", COLOR_BORDER_SUBTLE),
        ],
    )

    # Status labels
    style.configure(
        STATUS_LABEL_STYLE,
        background=COLOR_SURFACE,
        foreground=COLOR_TEXT_MUTED,
        font=(FONT_FAMILY_BASE, 9),
        padding=(0, PADDING_XS),
    )
    style.configure(
        STATUS_STRONG_LABEL_STYLE,
        background=COLOR_SURFACE,
        foreground="#e4e4e7",
        font=(FONT_FAMILY_BASE, 10, "bold"),
        padding=(0, PADDING_XS),
    )

    return style


__all__ = [
    "COLOR_BG",
    "COLOR_SURFACE",
    "COLOR_SURFACE_ALT",
    "COLOR_ACCENT",
    "COLOR_ACCENT_DANGER",
    "COLOR_TEXT",
    "COLOR_TEXT_MUTED",
    "COLOR_BORDER_SUBTLE",
    "PADDING_XS",
    "PADDING_SM",
    "PADDING_MD",
    "PADDING_LG",
    "PRIMARY_BUTTON_STYLE",
    "DANGER_BUTTON_STYLE",
    "GHOST_BUTTON_STYLE",
    "STATUS_LABEL_STYLE",
    "STATUS_STRONG_LABEL_STYLE",
    "SURFACE_FRAME_STYLE",
    "HEADER_FRAME_STYLE",
    "configure_style",
]
