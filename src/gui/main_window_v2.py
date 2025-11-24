"""Deprecated legacy MainWindow skeleton kept for Architecture_v2-era tests.

Prefer StableNewGUI from src.gui.main_window for all new entrypoints.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, TYPE_CHECKING

from .config_panel import ConfigPanel
from . import theme

if TYPE_CHECKING:  # pragma: no cover
    from src.controller.app_controller import AppController


class HeaderZone(ttk.Frame):
    def __init__(self, master: tk.Misc, *, frame_style: Optional[str] = None) -> None:
        style_kwargs = {"style": frame_style} if frame_style else {}
        super().__init__(master, padding=theme.PADDING_MD, **style_kwargs)
        self.run_button = ttk.Button(
            self,
            text="Run",
            style=theme.PRIMARY_BUTTON_STYLE,
        )
        self.stop_button = ttk.Button(
            self,
            text="Stop",
            style=theme.DANGER_BUTTON_STYLE,
        )
        self.preview_button = ttk.Button(
            self,
            text="Preview",
            style=theme.GHOST_BUTTON_STYLE,
        )
        self.settings_button = ttk.Button(
            self,
            text="Settings",
            style=theme.GHOST_BUTTON_STYLE,
        )
        self.help_button = ttk.Button(
            self,
            text="Help",
            style=theme.GHOST_BUTTON_STYLE,
        )

        for btn in (
            self.run_button,
            self.stop_button,
            self.preview_button,
            self.settings_button,
            self.help_button,
        ):
            btn.pack(side="left", padx=theme.PADDING_SM)


class LeftZone(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(
            master, padding=theme.PADDING_MD, style=theme.SURFACE_FRAME_STYLE
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.load_pack_button = ttk.Button(
            self, text="Load Pack", style=theme.GHOST_BUTTON_STYLE
        )
        self.edit_pack_button = ttk.Button(
            self, text="Edit Pack", style=theme.GHOST_BUTTON_STYLE
        )
        self.load_pack_button.grid(row=0, column=0, sticky="ew")
        self.edit_pack_button.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(theme.PADDING_SM, theme.PADDING_MD),
        )

        self.packs_card = ttk.Frame(
            self,
            padding=theme.PADDING_MD,
            style=theme.SURFACE_FRAME_STYLE,
        )
        self.packs_card.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, theme.PADDING_MD),
        )
        self.packs_card.columnconfigure(0, weight=1)
        self.packs_card.rowconfigure(1, weight=1)

        ttk.Label(
            self.packs_card, text="Packs", style=theme.STATUS_STRONG_LABEL_STYLE
        ).grid(row=0, column=0, sticky="w", pady=(0, theme.PADDING_SM))

        self.packs_list = tk.Listbox(
            self.packs_card,
            height=10,
            width=34,
            relief="flat",
            borderwidth=0,
            background=theme.COLOR_SURFACE_ALT,
            foreground=theme.COLOR_TEXT,
            highlightthickness=1,
            highlightcolor=theme.COLOR_BORDER_SUBTLE,
            highlightbackground=theme.COLOR_BORDER_SUBTLE,
            selectbackground=theme.COLOR_ACCENT,
            selectforeground=theme.ASWF_BLACK,
            activestyle="none",
        )
        self.packs_list.grid(row=1, column=0, sticky="nsew")

        self.preset_card = ttk.Frame(
            self,
            padding=theme.PADDING_MD,
            style=theme.SURFACE_FRAME_STYLE,
        )
        self.preset_card.grid(row=3, column=0, sticky="ew")
        self.preset_card.columnconfigure(0, weight=1)

        self.preset_label = ttk.Label(
            self.preset_card, text="Preset", style=theme.STATUS_STRONG_LABEL_STYLE
        )
        self.preset_label.grid(row=0, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(self.preset_card, values=[])
        self.preset_combo.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(theme.PADDING_XS, 0),
        )

    def update_pack_list(self, pack_names: list[str]) -> None:
        self.packs_list.delete(0, "end")
        for name in pack_names:
            self.packs_list.insert("end", name)


class BottomZone(ttk.Frame):
    def __init__(self, master: tk.Misc, *, frame_style: Optional[str] = None) -> None:
        style_kwargs = {"style": frame_style} if frame_style else {}
        super().__init__(master, padding=theme.PADDING_MD, **style_kwargs)
        self.status_label = ttk.Label(
            self,
            text="Status: Idle",
            style=theme.STATUS_STRONG_LABEL_STYLE,
        )
        self.status_label.pack(anchor="w")

        self.api_status_label = ttk.Label(
            self,
            text="API: Unknown",
            style=theme.STATUS_LABEL_STYLE,
        )
        self.api_status_label.pack(anchor="w", pady=(0, theme.PADDING_SM))

        self.log_text = tk.Text(self, height=10, width=60, relief="flat", borderwidth=0)
        self.log_text.configure(
            state="normal",
            background=theme.COLOR_SURFACE_ALT,
            foreground=theme.COLOR_TEXT,
            insertbackground=theme.COLOR_TEXT,
            highlightthickness=1,
            highlightcolor=theme.COLOR_BORDER_SUBTLE,
            highlightbackground=theme.COLOR_BORDER_SUBTLE,
        )
        self.log_text.pack(fill="both", expand=True)


class RightZone(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=theme.PADDING_MD, style=theme.SURFACE_FRAME_STYLE)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self, text="Preview", style=theme.STATUS_STRONG_LABEL_STYLE
        ).grid(row=0, column=0, sticky="w")

        self.preview_placeholder = ttk.Frame(
            self,
            style=theme.SURFACE_FRAME_STYLE,
            padding=theme.PADDING_MD,
        )
        self.preview_placeholder.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(theme.PADDING_SM, 0),
        )
        ttk.Label(
            self.preview_placeholder,
            text="Preview area coming soon",
            style=theme.STATUS_LABEL_STYLE,
        ).pack(anchor="center", expand=True)


class MainWindow:
    """Lightweight window used by the PR-0 controller tests (deprecated)."""

    def __init__(self, root: tk.Misc | None = None) -> None:
        self.root = root or tk.Tk()
        self.root.title("StableNew")
        self.root.geometry("960x680")
        self.root.minsize(840, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.style = theme.configure_style(self.root)
        self.controller: Optional["AppController"] = None

        self.header_zone = HeaderZone(self.root, frame_style=theme.HEADER_FRAME_STYLE)
        self.header_zone.pack(fill="x", side="top")

        body = ttk.Frame(self.root, style=theme.SURFACE_FRAME_STYLE, padding=theme.PADDING_MD)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        self.left_zone = LeftZone(body)
        self.left_zone.grid(row=0, column=0, sticky="nsew", padx=(0, theme.PADDING_MD))

        self.center_zone = ttk.Frame(
            body,
            style=theme.SURFACE_FRAME_STYLE,
            padding=theme.PADDING_MD,
        )
        self.center_zone.grid(row=0, column=1, sticky="nsew")
        self.center_zone.columnconfigure(0, weight=1)
        self.center_zone.rowconfigure(0, weight=1)
        self.config_panel = ConfigPanel(self.center_zone, self.on_config_field_changed)
        self.config_panel.grid(row=0, column=0, sticky="nsew")

        self.right_zone = RightZone(body)
        self.right_zone.grid(row=0, column=2, sticky="nsew", padx=(theme.PADDING_MD, 0))

        self.bottom_zone = BottomZone(
            self.root,
            frame_style=theme.SURFACE_FRAME_STYLE,
        )
        self.bottom_zone.pack(fill="both", expand=True, side="bottom")

    def after(self, delay_ms: int, callback: Callable[[], None]):
        return self.root.after(delay_ms, callback)

    def withdraw(self) -> None:
        self.root.withdraw()

    def destroy(self) -> None:
        self.root.destroy()

    def update_pack_list(self, pack_names: list[str]) -> None:
        self.left_zone.update_pack_list(pack_names)

    def connect_controller(self, controller: "AppController") -> None:
        self.controller = controller
        self.refresh_config_panel()

    def refresh_config_panel(self) -> None:
        if not self.controller:
            return
        config = self.controller.get_current_config()
        models = self.controller.get_available_models()
        samplers = self.controller.get_available_samplers()
        self.config_panel.refresh_from_controller(config, models, samplers)

    def on_config_field_changed(self, field: str, value) -> None:
        if not self.controller:
            return
        self.controller.update_config(**{field: value})
        self.refresh_config_panel()
