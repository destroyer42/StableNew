import tkinter as tk

import pytest

from src.controller.webui_connection_controller import WebUIConnectionState
from src.gui.api_status_panel import APIStatusPanel


@pytest.mark.usefixtures("tk_root")
def test_status_panel_updates_and_reconnect(tk_root: tk.Tk):
    called = {}

    def reconnect():
        called["hit"] = True

    panel = APIStatusPanel(tk_root)
    panel.set_reconnect_callback(reconnect)
    panel.set_webui_state(WebUIConnectionState.READY)
    panel.update_idletasks()
    assert "Ready" in panel.status_label.cget("text")

    panel.set_webui_state(WebUIConnectionState.ERROR)
    panel.update_idletasks()
    assert "Error" in panel.status_label.cget("text")

    panel._on_reconnect_clicked()
    assert called.get("hit") is True
