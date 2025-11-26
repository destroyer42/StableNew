"""Sidebar panel scaffold for GUI v2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from . import theme as theme_mod
from .core_config_panel_v2 import CoreConfigPanelV2
from .model_list_adapter_v2 import ModelListAdapterV2
from .model_manager_panel_v2 import ModelManagerPanelV2
from .negative_prompt_panel_v2 import NegativePromptPanelV2
from .output_settings_panel_v2 import OutputSettingsPanelV2
from .prompt_pack_adapter_v2 import PromptPackAdapterV2, PromptPackSummary
from .prompt_pack_panel_v2 import PromptPackPanelV2
from .widgets.scrollable_frame_v2 import ScrollableFrame


class SidebarPanelV2(ttk.Frame):
    """Container for sidebar content (core config + negative prompt + packs + pipeline controls)."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        controller=None,
        app_state=None,
        theme=None,
        prompt_pack_adapter: PromptPackAdapterV2 | None = None,
        on_apply_pack: Callable[[str, PromptPackSummary | None], None] | None = None,
        on_change: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        style_name = getattr(theme, "PIPELINE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_SM, **kwargs)
        self.controller = controller
        self.app_state = app_state
        self.theme = theme
        self.prompt_pack_adapter = prompt_pack_adapter or PromptPackAdapterV2()
        self._on_apply_pack = on_apply_pack
        self._on_change = on_change
        self.stage_states: dict[str, tk.BooleanVar] = {
            "txt2img": tk.BooleanVar(value=True),
            "img2img": tk.BooleanVar(value=True),
            "upscale": tk.BooleanVar(value=True),
        }
        self.run_mode_var = tk.StringVar(value="direct")
        self.run_scope_var = tk.StringVar(value="full")

        header_style = getattr(theme, "PIPELINE_HEADING_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Pipeline Controls", style=header_style)
        self.header_label.pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "PIPELINE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)

        # Stage toggles
        stage_frame = ttk.LabelFrame(self, text="Stages", style="Dark.TLabelframe")
        stage_frame.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        for name, var in self.stage_states.items():
            ttk.Checkbutton(stage_frame, text=name, variable=var, command=self._emit_change, style="Dark.TCheckbutton").pack(
                anchor="w"
            )

        # Run mode and scope
        run_frame = ttk.LabelFrame(self, text="Run Mode", style="Dark.TLabelframe")
        run_frame.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        ttk.Radiobutton(run_frame, text="Direct", value="direct", variable=self.run_mode_var, command=self._on_run_mode_change).pack(
            anchor="w"
        )
        ttk.Radiobutton(run_frame, text="Queue", value="queue", variable=self.run_mode_var, command=self._on_run_mode_change).pack(
            anchor="w"
        )

        scope_frame = ttk.LabelFrame(self, text="Run Scope", style="Dark.TLabelframe")
        scope_frame.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        for label, val in [("Selected only", "selected"), ("From selected", "from_selected"), ("Full pipeline", "full")]:
            ttk.Radiobutton(scope_frame, text=label, value=val, variable=self.run_scope_var, command=self._emit_change).pack(
                anchor="w"
            )

        # Run controls
        run_controls = ttk.Frame(self, style=body_style)
        run_controls.pack(fill=tk.X, pady=(0, theme_mod.PADDING_SM))
        self.run_now_btn = ttk.Button(run_controls, text="Run Now", style="Pipeline.TButton")
        self.run_now_btn.pack(fill=tk.X, pady=(0, theme_mod.PADDING_XS))
        self.add_to_queue_btn = ttk.Button(run_controls, text="Add to Queue", style="Pipeline.TButton")
        self.add_to_queue_btn.pack(fill=tk.X, pady=(0, theme_mod.PADDING_XS))
        self._refresh_run_mode_widgets()

        self._scroll = ScrollableFrame(self, style=body_style)
        self._scroll.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        body_parent = self._scroll.inner
        self.body = body_parent  # backward-compat hook for existing wiring

        adapter = ModelListAdapterV2(lambda: getattr(self.controller, "client", None))
        self.model_manager_panel = ModelManagerPanelV2(body_parent, theme=theme, adapter=adapter)
        self.model_manager_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.core_config_panel = CoreConfigPanelV2(body_parent, theme=theme)
        self.core_config_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.negative_prompt_panel = NegativePromptPanelV2(body_parent, theme=theme)
        self.negative_prompt_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.output_settings_panel = OutputSettingsPanelV2(body_parent, theme=theme)
        self.output_settings_panel.pack(fill=tk.X, pady=(0, theme_mod.PADDING_MD))

        self.prompt_pack_panel = PromptPackPanelV2(
            body_parent,
            theme=theme,
            packs=[],
            on_apply=self._handle_apply_pack,
        )
        self.prompt_pack_panel.pack(fill=tk.BOTH, expand=True)
        self.packs_list = self.prompt_pack_panel.listbox  # legacy compatibility

        self.refresh_prompt_packs()
        self._emit_change()

    def refresh_prompt_packs(self) -> None:
        if not self.prompt_pack_adapter:
            return
        try:
            summaries = self.prompt_pack_adapter.load_summaries()
        except Exception:
            summaries = []
        self.prompt_pack_panel.set_packs(summaries)
        # Keep the legacy list view in sync for AppController-based flows.
        if getattr(self, "packs_list", None):
            self.packs_list.delete(0, tk.END)
            for summary in summaries:
                self.packs_list.insert(tk.END, summary.name)

    def set_pack_names(self, names: list[str]) -> None:
        """Best-effort helper for simple string lists (used by AppController)."""
        if not getattr(self, "packs_list", None):
            return
        self.packs_list.delete(0, tk.END)
        for name in names:
            self.packs_list.insert(tk.END, name)

    # --- Pipeline control helpers -------------------------------------
    def get_enabled_stages(self) -> list[str]:
        return [name for name, var in self.stage_states.items() if var.get()]

    def get_run_mode(self) -> str:
        return self.run_mode_var.get()

    def get_run_scope(self) -> str:
        return self.run_scope_var.get()

    def get_job_counts(self) -> tuple[int, int]:
        stages = len(self.get_enabled_stages())
        jobs = max(1, stages)
        images_per_job = 1
        return jobs, images_per_job

    def _emit_change(self) -> None:
        if callable(self._on_change):
            try:
                self._on_change()
            except Exception:
                pass

    def _on_run_mode_change(self) -> None:
        self._refresh_run_mode_widgets()
        self._emit_change()

    def _refresh_run_mode_widgets(self) -> None:
        if self.run_mode_var.get() == "queue":
            self.add_to_queue_btn.state(["!disabled"])
            self.add_to_queue_btn.pack(fill=tk.X, pady=(0, theme_mod.PADDING_XS))
        else:
            self.add_to_queue_btn.state(["disabled"])
            self.add_to_queue_btn.pack_forget()

    def _handle_apply_pack(self, summary: PromptPackSummary) -> None:
        prompt_text = ""
        if self.prompt_pack_adapter:
            try:
                prompt_text = self.prompt_pack_adapter.get_base_prompt(summary)
            except Exception:
                prompt_text = ""
        if self._on_apply_pack:
            try:
                self._on_apply_pack(prompt_text, summary)
            except Exception:
                pass

    def get_model_overrides(self) -> dict[str, object]:
        panel = getattr(self, "model_manager_panel", None)
        if panel:
            return panel.get_selections()
        return {}

    def get_core_overrides(self) -> dict[str, object]:
        if self.core_config_panel:
            return self.core_config_panel.get_overrides()
        return {}

    def get_negative_prompt(self) -> str:
        if self.negative_prompt_panel:
            return self.negative_prompt_panel.get_negative_prompt()
        return ""

    def get_resolution(self) -> tuple[int, int]:
        if self.core_config_panel and getattr(self.core_config_panel, "resolution_panel", None):
            return self.core_config_panel.resolution_panel.get_resolution()
        return 512, 512

    def get_resolution_preset(self) -> str:
        if self.core_config_panel and getattr(self.core_config_panel, "resolution_panel", None):
            return self.core_config_panel.resolution_panel.get_preset_label()
        return ""

    def get_output_overrides(self) -> dict[str, object]:
        panel = getattr(self, "output_settings_panel", None)
        if panel:
            return panel.get_output_overrides()
        return {}


__all__ = ["SidebarPanelV2"]
