"""Theme system for StableNew GUI using ASWF color tokens."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ASWF Color Tokens
ASWF_BLACK = "#221F20"
ASWF_GOLD = "#FFC805"
ASWF_DARK_GREY = "#2B2A2C"
ASWF_MED_GREY = "#3A393D"
ASWF_LIGHT_GREY = "#4A4950"
ASWF_ERROR_RED = "#CC3344"
ASWF_OK_GREEN = "#44AA55"

# Font Tokens
FONT_FAMILY = "Calibri"
FONT_SIZE_BASE = 11  # Consistent base size for all widgets
FONT_SIZE_LABEL = 11  # Same as base for consistency
FONT_SIZE_BUTTON = 11  # Same as base for consistency
FONT_SIZE_HEADING = 13  # Increased for headings only


class Theme:
    """Central theme management for StableNew GUI."""

    def apply_root(self, root: tk.Tk) -> None:
        """Apply theme to the root Tk window."""
        root.configure(bg=ASWF_BLACK)
        root.option_add("*Font", f"{FONT_FAMILY} {FONT_SIZE_BASE}")
        root.option_add("*background", ASWF_BLACK)
        root.option_add("*foreground", ASWF_GOLD)

    def apply_ttk_styles(self, style: ttk.Style) -> None:
        """Apply ttk theme and style settings using ASWF theme."""
        # Set default ttk theme to use our custom styles
        style.theme_use('default')  # Use default theme as base

        # Configure default ttk styles to use our dark theme
        style.configure(
            "TFrame",
            background=ASWF_BLACK,  # Black background for all frames
        )
        style.configure(
            "TLabel",
            background=ASWF_BLACK,  # Black background
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.configure(
            "TButton",
            background=ASWF_DARK_GREY,  # Grey background for buttons
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            relief="raised",  # Raised for curved appearance
            borderwidth=2,
        )
        style.map(
            "TButton",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "TCombobox",
            fieldbackground=ASWF_BLACK,  # Black background
            background=ASWF_DARK_GREY,  # Grey frame
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", ASWF_BLACK)],
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "TEntry",
            fieldbackground=ASWF_BLACK,  # Black background
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
        )
        style.map(
            "TEntry",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "TNotebook",
            background=ASWF_BLACK,  # Black background
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=ASWF_DARK_GREY,  # Grey background for tabs
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
            padding=[10, 5],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ASWF_BLACK)],  # Black background when selected
            foreground=[("selected", ASWF_GOLD)],  # Gold text when selected
        )
        style.configure(
            "TLabelframe",
            background=ASWF_BLACK,  # Black background
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            borderwidth=2,
            relief="raised",
        )
        style.configure(
            "TLabelframe.Label",
            background=ASWF_BLACK,  # Black background
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
        )
        style.configure(
            "TRadiobutton",
            background=ASWF_BLACK,  # Black background
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.map(
            "TRadiobutton",
            background=[("active", ASWF_BLACK)],
            foreground=[("active", ASWF_GOLD)],
        )
        style.configure(
            "TCheckbutton",
            background=ASWF_BLACK,  # Black background
            foreground=ASWF_GOLD,  # Gold text
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.map(
            "TCheckbutton",
            background=[("active", ASWF_BLACK)],
            foreground=[("active", ASWF_GOLD)],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=ASWF_DARK_GREY,  # Grey background
            troughcolor=ASWF_BLACK,  # Black trough
            borderwidth=2,
            relief="raised",
        )

        # Configure Dark.* styles for explicit usage
        style.configure(
            "Dark.TFrame",
            background=ASWF_BLACK,
        )
        style.configure(
            "Dark.TLabel",
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.configure(
            "Dark.TButton",
            background=ASWF_DARK_GREY,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Dark.TButton",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "Dark.TCombobox",
            fieldbackground=ASWF_BLACK,
            background=ASWF_DARK_GREY,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", ASWF_BLACK)],
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "Dark.TEntry",
            fieldbackground=ASWF_BLACK,
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
        )
        style.map(
            "Dark.TEntry",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "Dark.TNotebook",
            background=ASWF_BLACK,
            borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background=ASWF_DARK_GREY,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            borderwidth=2,
            relief="raised",
            padding=[10, 5],
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", ASWF_BLACK)],
            foreground=[("selected", ASWF_GOLD)],
        )
        style.configure(
            "Dark.TLabelframe",
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            borderwidth=2,
            relief="raised",
        )
        style.configure(
            "Dark.TLabelframe.Label",
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
        )
        style.configure(
            "Dark.TRadiobutton",
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.map(
            "Dark.TRadiobutton",
            background=[("active", ASWF_BLACK)],
            foreground=[("active", ASWF_GOLD)],
        )
        style.configure(
            "Dark.TCheckbutton",
            background=ASWF_BLACK,
            foreground=ASWF_GOLD,
            font=(FONT_FAMILY, FONT_SIZE_BASE),
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", ASWF_BLACK)],
            foreground=[("active", ASWF_GOLD)],
        )

        # Spinbox styling (increment boxes)
        spinbox_common = {
            "background": ASWF_DARK_GREY,
            "fieldbackground": ASWF_BLACK,
            "foreground": ASWF_GOLD,
            "arrowcolor": ASWF_GOLD,
            "font": (FONT_FAMILY, FONT_SIZE_BASE),
            "borderwidth": 2,
            "relief": "raised",
        }
        style.configure("TSpinbox", **spinbox_common)
        style.configure("Dark.TSpinbox", **spinbox_common)
        style.map(
            "Dark.TSpinbox",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
            fieldbackground=[("readonly", ASWF_BLACK)],
        )

        # Slider styling
        scale_common = {
            "background": ASWF_BLACK,
            "troughcolor": ASWF_DARK_GREY,
            "borderwidth": 0,
            "sliderthickness": 16,
        }
        style.configure("Horizontal.TScale", **scale_common)
        style.configure("Dark.Horizontal.TScale", **scale_common)

        # Special button styles
        style.configure(
            "Primary.TButton",
            background=ASWF_GOLD,
            foreground=ASWF_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Primary.TButton",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "Danger.TButton",
            background=ASWF_ERROR_RED,
            foreground="white",
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Danger.TButton",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )
        style.configure(
            "Success.TButton",
            background=ASWF_OK_GREEN,
            foreground="white",
            font=(FONT_FAMILY, FONT_SIZE_BASE, "bold"),
            relief="raised",
            borderwidth=2,
        )
        style.map(
            "Success.TButton",
            background=[("active", ASWF_LIGHT_GREY)],
            foreground=[("active", ASWF_BLACK)],
        )

    def style_button_primary(self, btn: tk.Button) -> None:
        """Style a primary action button."""
        btn.configure(
            bg=ASWF_GOLD,
            fg=ASWF_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_BUTTON, "bold"),
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=5,
        )

    def style_button_danger(self, btn: tk.Button) -> None:
        """Style a danger/error button."""
        btn.configure(
            bg=ASWF_ERROR_RED,
            fg="white",
            font=(FONT_FAMILY, FONT_SIZE_BUTTON),
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=5,
        )

    def style_frame(self, frame: tk.Frame) -> None:
        """Style a frame."""
        frame.configure(bg=ASWF_DARK_GREY, relief=tk.FLAT, borderwidth=0)

    def style_label(self, label: tk.Label) -> None:
        """Style a label."""
        label.configure(
            bg=ASWF_DARK_GREY,
            fg=ASWF_GOLD,  # Gold text on dark background for contrast
            font=(FONT_FAMILY, FONT_SIZE_LABEL),
        )

    def style_label_heading(self, label: tk.Label) -> None:
        """Style a heading label."""
        label.configure(
            bg=ASWF_DARK_GREY,
            fg=ASWF_GOLD,  # Gold text on dark background
            font=(FONT_FAMILY, FONT_SIZE_HEADING, "bold"),
        )

    def style_entry(self, entry: tk.Entry) -> None:
        """Style an entry widget."""
        entry.configure(
            bg=ASWF_MED_GREY,  # Gray background
            fg="white",  # White text on gray background for contrast
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            insertbackground=ASWF_GOLD,
            relief=tk.FLAT,
            borderwidth=1,
        )

    def style_text(self, text: tk.Text) -> None:
        """Style a text widget."""
        text.configure(
            bg=ASWF_MED_GREY,  # Gray background
            fg=ASWF_LIGHT_GREY,  # Light grey text on gray background for contrast
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            insertbackground=ASWF_GOLD,
            relief=tk.FLAT,
            borderwidth=1,
        )

    def style_listbox(self, listbox: tk.Listbox) -> None:
        """Style a listbox."""
        listbox.configure(
            bg=ASWF_MED_GREY,  # Gray background
            fg="white",  # White text on gray background for contrast
            font=(FONT_FAMILY, FONT_SIZE_BASE),
            selectbackground=ASWF_GOLD,
            selectforeground=ASWF_BLACK,
            relief=tk.FLAT,
            borderwidth=1,
        )

    def style_scrollbar(self, scrollbar: tk.Scrollbar) -> None:
        """Style a scrollbar."""
        scrollbar.configure(
            bg=ASWF_MED_GREY,
            troughcolor=ASWF_DARK_GREY,
            relief=tk.FLAT,
            borderwidth=1,
        )
