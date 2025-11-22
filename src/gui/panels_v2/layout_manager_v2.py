"""Optional layout manager to compose V2 panels."""

from __future__ import annotations

from typing import Any

from src.gui.panels_v2 import (
    PipelinePanelV2,
    PreviewPanelV2,
    RandomizerPanelV2,
    SidebarPanelV2,
    StatusBarV2,
)


class LayoutManagerV2:
    """Helper to build and attach panel instances to a main window."""

    def __init__(self, main_window: Any) -> None:
        self.main_window = main_window

    def attach_panels(self) -> None:
        """Ensure core panel attributes exist on the main window."""

        mw = self.main_window
        if not hasattr(mw, "sidebar_panel_v2") and hasattr(mw, "left_zone"):
            mw.sidebar_panel_v2 = SidebarPanelV2(mw.left_zone, controller=getattr(mw, "controller", None), theme=getattr(mw, "theme", None))
        if not hasattr(mw, "pipeline_panel_v2") and hasattr(mw, "center_notebook"):
            mw.pipeline_panel_v2 = PipelinePanelV2(
                mw.center_notebook, controller=getattr(mw, "controller", None), theme=getattr(mw, "theme", None), config_manager=getattr(mw, "config_manager", None)
            )
        if not hasattr(mw, "randomizer_panel_v2") and hasattr(mw, "center_notebook"):
            mw.randomizer_panel_v2 = RandomizerPanelV2(mw.center_notebook, controller=getattr(mw, "controller", None), theme=getattr(mw, "theme", None))
        if not hasattr(mw, "preview_panel_v2") and hasattr(mw, "center_notebook"):
            mw.preview_panel_v2 = PreviewPanelV2(mw.center_notebook, controller=getattr(mw, "controller", None), theme=getattr(mw, "theme", None))
        if not hasattr(mw, "status_bar_v2") and hasattr(mw, "bottom_zone"):
            mw.status_bar_v2 = StatusBarV2(mw.bottom_zone, controller=getattr(mw, "controller", None), theme=getattr(mw, "theme", None))
