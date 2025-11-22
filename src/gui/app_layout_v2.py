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
            try:
                owner.sidebar_panel_v2.pack(fill="both", expand=True)
            except Exception:
                pass

        # Pipeline / center panel
        center_parent = getattr(owner, "center_stack", None) or getattr(owner, "center_zone", None)
        if not hasattr(owner, "pipeline_panel_v2") and center_parent is not None:
            owner.pipeline_panel_v2 = PipelinePanelV2(
                center_parent,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
                config_manager=getattr(owner, "config_manager", None),
            )
            try:
                owner.pipeline_panel_v2.pack(fill="both", expand=True)
            except Exception:
                pass

        if (
            not hasattr(owner, "randomizer_panel_v2")
            and center_parent is not None
            and hasattr(owner, "pipeline_panel_v2")
        ):
            owner.randomizer_panel_v2 = RandomizerPanelV2(
                center_parent, controller=getattr(owner, "controller", None), theme=self.theme
            )
            try:
                owner.randomizer_panel_v2.pack(fill="both", expand=True, pady=(5, 0))
            except Exception:
                pass

        # Right-side panels: preview
        if not hasattr(owner, "preview_panel_v2") and hasattr(owner, "right_zone"):
            owner.preview_panel_v2 = PreviewPanelV2(
                owner.right_zone,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
            )
            try:
                owner.preview_panel_v2.pack(fill="both", expand=True)
            except Exception:
                pass

        # Status bar
        if not hasattr(owner, "status_bar_v2") and hasattr(owner, "bottom_zone"):
            owner.status_bar_v2 = StatusBarV2(
                owner.bottom_zone,
                controller=getattr(owner, "controller", None),
                theme=self.theme,
            )
            try:
                owner.status_bar_v2.pack(fill="x", pady=(4, 0))
            except Exception:
                pass

    def attach_run_button(self, run_button: Any | None = None) -> None:
        """Expose the run button reference consistently."""

        if run_button is not None:
            self.owner.run_button = run_button
