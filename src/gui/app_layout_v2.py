"""V2 application layout builder for StableNewGUI.

This helper centralizes panel instantiation and attachment for the V2 GUI shell.
It is intentionally limited to Tk layout concerns and does not touch controller,
pipeline, or learning logic.
"""

from __future__ import annotations

from typing import Any

from src.gui.panels_v2 import (
    PipelinePanelV2,
    PreviewPanelV2,
    RandomizerPanelV2,
    SidebarPanelV2,
    StatusBarV2,
)


class AppLayoutV2:
    """Builds and attaches V2 panels to a StableNewGUI owner."""

    def __init__(self, owner: Any, theme: Any = None) -> None:
        self.owner = owner
        self.theme = theme

    def build_layout(self, root_frame: Any | None = None) -> None:
        """Instantiate panels and attach them to the owner if not already present."""

        owner = self.owner

        # Sidebar
        if not hasattr(owner, "sidebar_panel_v2") and hasattr(owner, "left_zone"):
            owner.sidebar_panel_v2 = SidebarPanelV2(
                owner.left_zone, controller=getattr(owner, "controller", None), theme=self.theme
            )

        # Pipeline / center panel
        if not hasattr(owner, "pipeline_panel_v2") and hasattr(owner, "center_notebook"):
            owner.pipeline_panel_v2 = PipelinePanelV2(
                owner.center_notebook,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
                config_manager=getattr(owner, "config_manager", None),
            )

        # Right-side panels: preview + randomizer
        if not hasattr(owner, "preview_panel_v2") and hasattr(owner, "right_zone"):
            owner.preview_panel_v2 = PreviewPanelV2(
                owner.right_zone,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
            )

        if not hasattr(owner, "randomizer_panel_v2") and hasattr(owner, "right_zone"):
            owner.randomizer_panel_v2 = RandomizerPanelV2(
                owner.right_zone,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
            )

        # Status bar
        if not hasattr(owner, "status_bar_v2") and hasattr(owner, "bottom_zone"):
            owner.status_bar_v2 = StatusBarV2(
                owner.bottom_zone,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
            )

        # Run button (keep existing handler)
        if not hasattr(owner, "run_button") and hasattr(owner, "bottom_zone"):
            import tkinter as tk
            from tkinter import ttk

            try:
                btn = ttk.Button(
                    owner.bottom_zone,
                    text="Run",
                    command=getattr(owner, "_run_full_pipeline", None),
                )
                btn.pack(side=tk.LEFT, padx=(0, 10))
                owner.run_button = btn
            except Exception:
                owner.run_button = None
