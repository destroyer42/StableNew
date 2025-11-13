"""Compatibility wrapper that exposes the GUI pipeline controller at src.controller."""

from src.gui.controller import PipelineController as _GUIPipelineController
from src.gui.state import StateManager


class PipelineController(_GUIPipelineController):
    """Provide a default StateManager so legacy imports keep working."""

    def __init__(self, state_manager: StateManager | None = None, *args, **kwargs):
        super().__init__(state_manager or StateManager(), *args, **kwargs)
