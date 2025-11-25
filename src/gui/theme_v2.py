from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Palette
BACKGROUND_DARK = "#121212"
BACKGROUND_ELEVATED = "#1E1E1E"
BORDER_SUBTLE = "#2A2A2A"

TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#CCCCCC"
TEXT_DISABLED = "#777777"

ACCENT_GOLD = "#FFC805"
ACCENT_GOLD_HOVER = "#FFD94D"

ERROR_RED = "#FF4D4F"
SUCCESS_GREEN = "#52C41A"
INFO_BLUE = "#40A9FF"

# Fonts
DEFAULT_FONT_FAMILY = "Segoe UI"
DEFAULT_FONT_SIZE = 10
HEADING_FONT_SIZE = 11
MONO_FONT_FAMILY = "Consolas"


def apply_theme(root: tk.Tk) -> None:
    """Apply the StableNew V2 dark theme to the given Tk root."""
    style = ttk.Style(master=root)
    try:
        style.theme_use("alt")
    except tk.TclError:
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    _configure_global_colors(root)
    _configure_fonts(root)
    _configure_panel_styles(style)
    _configure_button_styles(style)
    _configure_label_styles(style)
    _configure_entry_styles(style)
    _configure_treeview_styles(style)
    _configure_statusbar_styles(style)
    _configure_progress_styles(style)


def _configure_global_colors(root: tk.Tk) -> None:
    try:
        root.configure(bg=BACKGROUND_DARK)
    except Exception:
        pass


def _configure_fonts(root: tk.Tk) -> None:
    family = f"{{{DEFAULT_FONT_FAMILY}}}"
    root.option_add("*Font", f"{family} {DEFAULT_FONT_SIZE}")
    root.option_add("*TEntry.Font", f"{family} {DEFAULT_FONT_SIZE}")
    root.option_add("*Text.Font", f"{family} {DEFAULT_FONT_SIZE}")
    root.option_add("*Treeview.Font", f"{family} {DEFAULT_FONT_SIZE}")
    root.option_add("*TNotebook.Tab.Font", f"{family} {DEFAULT_FONT_SIZE}")
    root.option_add("*Heading.Font", f"{family} {HEADING_FONT_SIZE} bold")


def _configure_panel_styles(style: ttk.Style) -> None:
    style.configure(
        "Panel.TFrame",
        background=BACKGROUND_DARK,
        borderwidth=0,
    )
    style.configure(
        "Card.TFrame",
        background=BACKGROUND_ELEVATED,
        borderwidth=1,
        relief="solid",
        bordercolor=BORDER_SUBTLE,
    )


def _configure_button_styles(style: ttk.Style) -> None:
    style.configure(
        "Primary.TButton",
        background=ACCENT_GOLD,
        foreground="#000000",
        borderwidth=0,
        focusthickness=1,
        focustcolor=ACCENT_GOLD_HOVER,
        padding=(8, 4),
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_GOLD_HOVER), ("disabled", BORDER_SUBTLE)],
        foreground=[("disabled", TEXT_DISABLED)],
    )

    style.configure(
        "Secondary.TButton",
        background=BORDER_SUBTLE,
        foreground=TEXT_PRIMARY,
        borderwidth=0,
        padding=(8, 4),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", BACKGROUND_ELEVATED), ("disabled", BORDER_SUBTLE)],
        foreground=[("disabled", TEXT_DISABLED)],
    )


def _configure_label_styles(style: ttk.Style) -> None:
    style.configure(
        "TLabel",
        background=BACKGROUND_DARK,
        foreground=TEXT_PRIMARY,
    )
    style.configure(
        "Muted.TLabel",
        background=BACKGROUND_DARK,
        foreground=TEXT_MUTED,
    )
    style.configure(
        "Heading.TLabel",
        background=BACKGROUND_DARK,
        foreground=TEXT_PRIMARY,
        font=f"{{{DEFAULT_FONT_FAMILY}}} {HEADING_FONT_SIZE} bold",
    )


def _configure_entry_styles(style: ttk.Style) -> None:
    style.configure(
        "TEntry",
        fieldbackground=BACKGROUND_ELEVATED,
        foreground=TEXT_PRIMARY,
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", BACKGROUND_ELEVATED), ("readonly", BACKGROUND_ELEVATED)],
        foreground=[("disabled", TEXT_DISABLED)],
    )


def _configure_treeview_styles(style: ttk.Style) -> None:
    style.configure(
        "Treeview",
        background=BACKGROUND_ELEVATED,
        fieldbackground=BACKGROUND_ELEVATED,
        foreground=TEXT_PRIMARY,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=BACKGROUND_DARK,
        foreground=TEXT_PRIMARY,
    )


def _configure_statusbar_styles(style: ttk.Style) -> None:
    style.configure(
        "StatusBar.TFrame",
        background=BACKGROUND_ELEVATED,
        borderwidth=1,
        relief="solid",
        bordercolor=BORDER_SUBTLE,
    )
    style.configure(
        "StatusBar.TLabel",
        background=BACKGROUND_ELEVATED,
        foreground=TEXT_MUTED,
    )


def _configure_progress_styles(style: ttk.Style) -> None:
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=BACKGROUND_ELEVATED,
        background=ACCENT_GOLD,
        bordercolor=BORDER_SUBTLE,
        lightcolor=ACCENT_GOLD,
        darkcolor=ACCENT_GOLD,
    )
