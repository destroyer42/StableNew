from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from src.controller.app_controller import AppController
from src.gui.app_state_v2 import AppStateV2
from src.gui.main_window_v2 import MainWindowV2
from src.api.webui_process_manager import WebUIProcessManager


def build_v2_app(
    *,
    root: Optional[tk.Tk] = None,
    pipeline_runner=None,
    webui_manager: WebUIProcessManager | None = None,
    threaded: bool = False,
) -> Tuple[tk.Tk, AppStateV2, AppController, MainWindowV2]:
    """
    Build the V2 application stack with injectable runner for tests.

    Returns (root, app_state, app_controller, window).
    """

    if root is None:
        root = tk.Tk()

    app_state = AppStateV2()

    window = MainWindowV2(
        root=root,
        app_state=app_state,
        webui_manager=webui_manager,
        app_controller=None,
        packs_controller=None,
        pipeline_controller=None,
    )

    app_controller = AppController(window, pipeline_runner=pipeline_runner, threaded=threaded)
    if hasattr(window, "connect_controller"):
        window.connect_controller(app_controller)

    return root, app_state, app_controller, window
