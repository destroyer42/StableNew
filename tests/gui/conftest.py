"""Test fixtures for GUI tests."""

import time
import tkinter as tk

import pytest


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
