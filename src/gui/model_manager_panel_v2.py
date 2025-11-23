"""Model and VAE selector panel for GUI V2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable

from src.config import app_config
from src.gui import theme as theme_mod
from src.gui.model_list_adapter_v2 import ModelListAdapterV2


class ModelManagerPanelV2(ttk.Frame):
    """Expose checkpoint and VAE selectors with a refresh hook."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        theme=None,
        adapter: ModelListAdapterV2 | None = None,
        models: Iterable[str] | None = None,
        vaes: Iterable[str] | None = None,
    ) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD)

        self.theme = theme or theme_mod
        self.adapter = adapter or ModelListAdapterV2()

        self.model_var = tk.StringVar(value=app_config.get_core_model_name())
        self.vae_var = tk.StringVar(value=app_config.get_core_vae_name())

        header_style = getattr(self.theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        ttk.Label(self, text="Model Manager", style=header_style).pack(anchor=tk.W, pady=(0, 6))

        self.model_combo = self._build_combo(self.model_var, models or [])
        self._build_row("Model", self.model_combo)

        self.vae_combo = self._build_combo(self.vae_var, vaes or [])
        self._build_row("VAE", self.vae_combo)

        ttk.Button(self, text="Refresh", command=self.refresh_lists, style=getattr(self.theme, "BUTTON_PRIMARY_STYLE", None)).pack(
            anchor=tk.E, pady=(theme_mod.PADDING_SM, 0)
        )

    def _build_row(self, label: str, widget: tk.Widget) -> None:
        row = ttk.Frame(self, style=getattr(self.theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE))
        row.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        ttk.Label(row, text=label, style=getattr(self.theme, "STATUS_LABEL_STYLE", theme_mod.STATUS_LABEL_STYLE)).pack(
            side=tk.LEFT
        )
        widget.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def _build_combo(self, variable: tk.StringVar, values: Iterable[str]) -> ttk.Combobox:
        combo = ttk.Combobox(
            self,
            textvariable=variable,
            values=tuple(values),
            state="normal",
        )
        return combo

    def refresh_lists(self) -> None:
        """Reload model/vae names from the adapter and keep current selections if possible."""

        if self.adapter:
            try:
                models = self.adapter.get_model_names()
                if models:
                    self.model_combo["values"] = tuple(models)
            except Exception:
                pass
            try:
                vaes = self.adapter.get_vae_names()
                if vaes:
                    self.vae_combo["values"] = tuple(vaes)
            except Exception:
                pass

    def get_selections(self) -> dict[str, str]:
        return {
            "model_name": self.model_var.get().strip(),
            "vae_name": self.vae_var.get().strip(),
        }

    def set_selections(self, model_name: str | None = None, vae_name: str | None = None) -> None:
        if model_name is not None:
            self.model_var.set(str(model_name))
        if vae_name is not None:
            self.vae_var.set(str(vae_name))


__all__ = ["ModelManagerPanelV2"]
