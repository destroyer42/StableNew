from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.state import PipelineState
from src.gui.views.pipeline_config_panel import PipelineConfigPanel
from src.gui.views.run_control_bar import RunControlBar
from src.gui.views.stage_cards_panel import StageCardsPanel


class PipelineTabFrame(ttk.Frame):
    """Layout scaffold for the Pipeline tab."""

    def __init__(self, master: tk.Misc, *, prompt_workspace_state: Any = None, app_state: Any = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.prompt_workspace_state = prompt_workspace_state
        self.app_state = app_state

        # Top run control bar
        self.run_bar = ttk.Frame(self, padding=8, style="Panel.TFrame")
        self.run_bar.grid(row=0, column=0, sticky="ew")

        # Body with three columns
        self.body_frame = ttk.Frame(self, padding=8, style="Panel.TFrame")
        self.body_frame.grid(row=1, column=0, sticky="nsew")
        self.body_frame.columnconfigure(0, weight=1)
        self.body_frame.columnconfigure(1, weight=2)
        self.body_frame.columnconfigure(2, weight=1)
        self.body_frame.rowconfigure(0, weight=1)

        self.config_frame = ttk.Frame(self.body_frame, padding=6, style="Panel.TFrame")
        self.stage_cards_frame = ttk.Frame(self.body_frame, padding=6, style="Panel.TFrame")
        self.preview_frame = ttk.Frame(self.body_frame, padding=6, style="Panel.TFrame")

        self.config_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.stage_cards_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        self.preview_frame.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        self.pipeline_state = PipelineState()
        PipelineConfigPanel(
            self.config_frame,
            pipeline_state=self.pipeline_state,
            app_state=self.app_state,
            on_change=lambda: self._refresh_run_summary(),
        ).pack(fill="both", expand=True)
        self.stage_cards_panel = StageCardsPanel(self.stage_cards_frame)
        self.stage_cards_panel.pack(fill="both", expand=True)
        ttk.Label(self.preview_frame, text="Preview (Scaffold)").pack(anchor="center", pady=8)

        self.run_control_bar = RunControlBar(
            self.run_bar,
            pipeline_state=self.pipeline_state,
            stage_cards_panel=self.stage_cards_panel,
            prompt_workspace_state=self.prompt_workspace_state,
            on_run_now=getattr(self.master, "run_pipeline", None),
            on_add_queue=getattr(self.master, "add_to_queue", None),
        )
        self.run_control_bar.pack(fill="x")

    def _refresh_run_summary(self) -> None:
        try:
            self.run_control_bar._refresh_summary()
        except Exception:
            pass
