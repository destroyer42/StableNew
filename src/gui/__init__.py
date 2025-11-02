"""GUI module"""

# Import state and controller modules which don't require tkinter
from .state import GUIState, StateManager, CancelToken, CancellationError
from .controller import PipelineController, LogMessage

# Don't import StableNewGUI here to avoid tkinter dependency in tests
# Users should import it directly: from src.gui.main_window import StableNewGUI

__all__ = [
    'GUIState',
    'StateManager',
    'CancelToken',
    'CancellationError',
    'PipelineController',
    'LogMessage',
]
