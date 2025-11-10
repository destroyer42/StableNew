"""Test fixtures for GUI tests."""

import time
import tkinter as tk

import pytest

from src.gui.main_window import StableNewGUI


_shared_root: tk.Tk | None = None


@pytest.fixture(scope="session")
def tk_root_session():
    """Create a shared Tk root for GUI tests; skip cleanly when unavailable."""
    global _shared_root
    if _shared_root is None:
        try:
            _shared_root = tk.Tk()
        except tk.TclError:
            pytest.skip("No display available for Tkinter tests")
        else:
            _shared_root.withdraw()

    assert _shared_root is not None  # for type checkers
    try:
        yield _shared_root
    finally:
        # Session-scope root is destroyed in fixture finalizer below
        pass


@pytest.fixture
def tk_root(tk_root_session):
    """Provide a clean Tk root for each test using the shared session instance."""
    # Clear out any remaining widgets from previous tests
    for child in list(tk_root_session.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass
    yield tk_root_session


@pytest.fixture(scope="session", autouse=True)
def _destroy_shared_root(request, tk_root_session):
    """Ensure the shared Tk root is destroyed when the test session ends."""

    def _finalize():
        global _shared_root
        if _shared_root is not None:
            try:
                _shared_root.destroy()
            except Exception:
                pass
            finally:
                _shared_root = None

    request.addfinalizer(_finalize)


@pytest.fixture
def tk_pump(tk_root):
    """Pump Tk events without blocking the main thread."""

    def pump(duration=0.2, step=0.01):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            try:
                tk_root.update()
            except Exception:
                break
            time.sleep(step)

    return pump


def wait_until(pred, timeout=5.0, step=0.02):
    """Wait until a predicate becomes True or timeout expires.
    
    Args:
        pred: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        step: Time between predicate checks in seconds
        
    Returns:
        True if predicate became True, False if timeout expired
    """
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(step)
    return False


@pytest.fixture
def minimal_gui_app(monkeypatch, tk_root):
    """Provide a lightweight StableNewGUI with heavy side effects stubbed out."""

    def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(StableNewGUI, "_initialize_ui_state", _noop)
    monkeypatch.setattr(StableNewGUI, "_launch_webui", _noop)
    monkeypatch.setattr("src.gui.main_window.messagebox.showerror", _noop)
    monkeypatch.setattr("src.gui.main_window.messagebox.showinfo", _noop)
    monkeypatch.setattr("src.gui.main_window.tk.Tk", lambda: tk_root)

    app = StableNewGUI()
    app.api_connected = True
    yield app

    # Cleanup widgets created inside the shared root so tests do not leak windows
    for child in list(tk_root.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass
