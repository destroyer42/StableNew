import pytest
import tkinter as tk
from tkinter import ttk

from src.gui.main_window import StableNewGUI
from src.gui.state import GUIState


def _skip_if_no_tk():
    try:
        root = tk.Tk()
        root.destroy()
    except tk.TclError:
        pytest.skip("No display available for Tkinter tests")


@pytest.fixture
def gui_app(monkeypatch):
    _skip_if_no_tk()

    monkeypatch.setattr(StableNewGUI, "_launch_webui", lambda self: None)
    monkeypatch.setattr("src.gui.main_window.messagebox.showinfo", lambda *args, **kwargs: None)

    app = StableNewGUI()
    try:
        yield app
    finally:
        # Ensure we don't leave Tk windows dangling between tests
        app.root.destroy()


def test_status_bar_initializes_progress_and_eta(gui_app):
    assert isinstance(gui_app.progress_bar, ttk.Progressbar)
    assert gui_app.progress_bar["value"] == pytest.approx(0)
    assert gui_app.progress_bar["maximum"] == pytest.approx(100)
    assert gui_app.eta_var.get() == gui_app._progress_eta_default
    assert gui_app.progress_message_var.get() == gui_app._progress_idle_message


def test_update_progress_updates_ui(gui_app):
    gui_app._update_progress("txt2img", 45, "00:30")
    gui_app.root.update()

    assert gui_app.progress_bar["value"] == pytest.approx(45)
    assert gui_app.progress_message_var.get() == "txt2img (45%)"
    assert gui_app.eta_var.get() == "ETA: 00:30"


def test_idle_transition_resets_progress(gui_app):
    gui_app._update_progress("img2img", 80, "01:15")
    gui_app.root.update()

    assert gui_app.progress_bar["value"] == pytest.approx(80)
    assert gui_app.eta_var.get() == "ETA: 01:15"

    gui_app.state_manager.transition_to(GUIState.RUNNING)
    gui_app.state_manager.transition_to(GUIState.IDLE)
    gui_app.root.update()

    assert gui_app.progress_bar["value"] == pytest.approx(0)
    assert gui_app.eta_var.get() == gui_app._progress_eta_default
    assert gui_app.progress_message_var.get() == gui_app._progress_idle_message
