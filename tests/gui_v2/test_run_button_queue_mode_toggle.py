import pytest

from src.gui.main_window_v2 import MainWindow
from src.controller.app_controller import AppController


def test_run_button_calls_controller(monkeypatch):
    calls = []

    class FakeRunner:
        def run(self, *_args, **_kwargs):
            calls.append("direct")

    root = None
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:  # pragma: no cover - Tk unavailable
        pytest.skip(f"Tkinter not available: {exc}")

    window = MainWindow(root)
    controller = AppController(window, pipeline_runner=FakeRunner(), threaded=False)

    window.header_zone.run_button.invoke()
    assert calls == ["direct"]

    root.destroy()
