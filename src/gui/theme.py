"""Shared theming helpers for StableNew GUIs."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# --- ASWF palette --------------------------------------------------------- #

ASWF_BLACK = "#221F20"
ASWF_GOLD = "#FFC805"
ASWF_DARK_GREY = "#2B2A2C"
ASWF_MED_GREY = "#3A393D"
ASWF_LIGHT_GREY = "#4A4950"
ASWF_ERROR_RED = "#CC3344"
ASWF_OK_GREEN = "#44AA55"

FONT_FAMILY = "Calibri"
FONT_SIZE_BASE = 11
FONT_SIZE_LABEL = 11
FONT_SIZE_BUTTON = 11
FONT_SIZE_HEADING = 13

# Derived tokens used by the newer ttk-based surfaces.
COLOR_BG = ASWF_BLACK
COLOR_SURFACE = ASWF_DARK_GREY
COLOR_SURFACE_ALT = "#2F2D30"
COLOR_TEXT = "#F5F5F5"
COLOR_TEXT_MUTED = "#D5D5D8"
COLOR_BORDER_SUBTLE = "#3F3F46"
COLOR_ACCENT = ASWF_GOLD
COLOR_ACCENT_DANGER = ASWF_ERROR_RED

PADDING_XS = 2
PADDING_SM = 4
PADDING_MD = 8
PADDING_LG = 12

PRIMARY_BUTTON_STYLE = "Primary.TButton"
GHOST_BUTTON_STYLE = "Ghost.TButton"
DANGER_BUTTON_STYLE = "Danger.TButton"
STATUS_LABEL_STYLE = "Status.TLabel"
STATUS_STRONG_LABEL_STYLE = "StatusStrong.TLabel"
SURFACE_FRAME_STYLE = "Surface.TFrame"
HEADER_FRAME_STYLE = "Header.TFrame"
# Pipeline-specific styles
PIPELINE_FRAME_STYLE = "Pipeline.TFrame"
PIPELINE_LABEL_STYLE = "Pipeline.TLabel"
PIPELINE_HEADING_STYLE = "PipelineHeading.TLabel"
PIPELINE_BUTTON_STYLE = "Pipeline.TButton"
# Pipeline-specific styles
PIPELINE_FRAME_STYLE = "Pipeline.TFrame"
PIPELINE_LABEL_STYLE = "Pipeline.TLabel"
PIPELINE_HEADING_STYLE = "PipelineHeading.TLabel"
PIPELINE_BUTTON_STYLE = "Pipeline.TButton"


class Theme:
    """Helper with Tk widget styling methods (legacy UI expectations)."""




def configure_style(root: tk.Misc | None) -> ttk.Style:
    """
    Configure ttk styles used by the StableNew V2 GUI.

    This centralizes all ttk.Style configuration so the rest of the GUI code
    can refer to named styles like PRIMARY_BUTTON_STYLE, SURFACE_FRAME_STYLE,
    PIPELINE_FRAME_STYLE, etc.
    """
    style = ttk.Style(master=root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Removed invalid root.configure(bg=COLOR_BG) call
    # --- Dark mode variants for all interactive elements ---
    # (see previous patch for full implementation)
    # ...existing code...
    # ...existing code...
        style.configure(
            PIPELINE_FRAME_STYLE,
            background=COLOR_SURFACE,
            borderwidth=0,
            relief="flat",
            padding=PADDING_SM,
        )
        style.configure(
            PIPELINE_LABEL_STYLE,
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            font=(FONT_FAMILY, FONT_SIZE_LABEL, "bold"),
        )
        style.configure(
            PIPELINE_HEADING_STYLE,
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            font=(FONT_FAMILY, FONT_SIZE_HEADING, "bold"),
        )
    # Removed stray lines and unmatched parenthesis
    style.configure(
        "Dark.TEntry",
        fieldbackground=COLOR_SURFACE_ALT,
        background=COLOR_SURFACE_ALT,
        foreground=COLOR_TEXT,
        bordercolor=COLOR_BORDER_SUBTLE,
        lightcolor=COLOR_BORDER_SUBTLE,
        darkcolor=COLOR_BORDER_SUBTLE,
        insertcolor=COLOR_ACCENT,
        padding=(PADDING_SM, PADDING_XS),
    )
    style.map(
        "Dark.TEntry",
        fieldbackground=[("focus", COLOR_SURFACE_ALT)],
        foreground=[("disabled", COLOR_TEXT_MUTED)],
    )
    style.configure(
        "Dark.TLabelframe",
        background=COLOR_SURFACE,
        foreground=COLOR_TEXT,
        borderwidth=1,
        relief="solid",
        bordercolor=COLOR_BORDER_SUBTLE,
    )
    style.configure(
        "Dark.TLabelframe.Label",
        background=COLOR_SURFACE,
        foreground=COLOR_TEXT,
        font=(FONT_FAMILY, FONT_SIZE_HEADING, "bold"),
        padding=(PADDING_SM, 0),
    )
    style.configure(
        "Dark.TNotebook",
        background=COLOR_SURFACE,
        tabmargins=(6, 4, 6, 0),
        borderwidth=0,
    )
    style.configure(
        "Dark.TNotebook.Tab",
        background=COLOR_SURFACE_ALT,
        foreground=COLOR_TEXT_MUTED,
        padding=(PADDING_MD, PADDING_SM),
        font=(FONT_FAMILY, FONT_SIZE_LABEL),
    )
    style.map(
        "Dark.TNotebook.Tab",
        background=[("selected", COLOR_SURFACE)],
        foreground=[("selected", COLOR_TEXT)],
    )
    style.configure("Dark.TSeparator", background=COLOR_BORDER_SUBTLE)
    style.configure("Dark.TPanedwindow", background=COLOR_BG, borderwidth=0)
    style.configure("Dark.TScrollbar", background=COLOR_SURFACE, troughcolor=COLOR_SURFACE_ALT)
    style.configure(SURFACE_FRAME_STYLE, background=COLOR_SURFACE)
    style.configure(HEADER_FRAME_STYLE, background=COLOR_SURFACE_ALT)

    style.configure(
        PRIMARY_BUTTON_STYLE,
        padding=(PADDING_MD, PADDING_SM),
        background=COLOR_ACCENT,
        foreground=ASWF_BLACK,
        borderwidth=0,
        focusthickness=0,
        font=(FONT_FAMILY, FONT_SIZE_BUTTON, "bold"),
    )
    style.map(
        PRIMARY_BUTTON_STYLE,
        background=[("pressed", "#e6b204"), ("active", "#ffd84d")],
    )

    style.configure(
        DANGER_BUTTON_STYLE,
        padding=(PADDING_MD, PADDING_SM),
        background=COLOR_ACCENT_DANGER,
        foreground="#ffffff",
        borderwidth=0,
        focusthickness=0,
        font=(FONT_FAMILY, FONT_SIZE_BUTTON, "bold"),
    )
    style.map(
        DANGER_BUTTON_STYLE,
        background=[("pressed", "#b82836"), ("active", "#f15965")],
    )

    style.configure(
        GHOST_BUTTON_STYLE,
        padding=(PADDING_MD - 2, PADDING_SM),
        background=COLOR_SURFACE_ALT,
        foreground=COLOR_TEXT,
        borderwidth=1,
        focusthickness=0,
        relief="raised",
        font=(FONT_FAMILY, FONT_SIZE_BUTTON),
        bordercolor=COLOR_BORDER_SUBTLE,
        lightcolor=COLOR_BORDER_SUBTLE,
        darkcolor=COLOR_BORDER_SUBTLE,
    )
    style.map(
        GHOST_BUTTON_STYLE,
        background=[("pressed", "#3a3a45"), ("active", "#2b2b34")],
        foreground=[("pressed", COLOR_TEXT), ("active", COLOR_TEXT)],
        relief=[("pressed", "sunken"), ("active", "raised")],
        bordercolor=[("pressed", COLOR_ACCENT), ("active", COLOR_BORDER_SUBTLE)],
    )

    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=COLOR_SURFACE_ALT,
        background=COLOR_ACCENT,
        bordercolor=COLOR_SURFACE,
        lightcolor=COLOR_ACCENT,
        darkcolor=COLOR_ACCENT,
    )

    style.configure(
        STATUS_LABEL_STYLE,
        background=COLOR_SURFACE,
        foreground=COLOR_TEXT_MUTED,
        font=(FONT_FAMILY, FONT_SIZE_BASE),
        padding=(0, PADDING_XS),
    )
    style.configure(
        STATUS_STRONG_LABEL_STYLE,
        background=COLOR_SURFACE,
        foreground=COLOR_TEXT,
        font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
        padding=(0, PADDING_XS),
    )
    return style


__all__ = [
    "ASWF_BLACK",
    "ASWF_GOLD",
    "ASWF_DARK_GREY",
    "ASWF_MED_GREY",
    "ASWF_LIGHT_GREY",
    "ASWF_ERROR_RED",
    "ASWF_OK_GREEN",
    "FONT_FAMILY",
    "FONT_SIZE_BASE",
    "FONT_SIZE_LABEL",
    "FONT_SIZE_BUTTON",
    "FONT_SIZE_HEADING",
    "COLOR_BG",
    "COLOR_SURFACE",
    "COLOR_SURFACE_ALT",
    "COLOR_TEXT",
    "COLOR_TEXT_MUTED",
    "COLOR_BORDER_SUBTLE",
    "COLOR_ACCENT",
    "COLOR_ACCENT_DANGER",
    "PADDING_XS",
    "PADDING_SM",
    "PADDING_MD",
    "PADDING_LG",
    "PRIMARY_BUTTON_STYLE",
    "GHOST_BUTTON_STYLE",
    "DANGER_BUTTON_STYLE",
    "STATUS_LABEL_STYLE",
    "STATUS_STRONG_LABEL_STYLE",
    "SURFACE_FRAME_STYLE",
    "HEADER_FRAME_STYLE",
    "Theme",
    "configure_style",
]
