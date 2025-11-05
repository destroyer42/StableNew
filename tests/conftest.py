import time
import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
    """Fixture to provide a Tk root window for GUI tests, skips if Tk is not available or no display."""
    try:
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()
    except tk.TclError:
        pytest.skip("No display available for Tkinter tests")


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


"""Test configuration"""


# Test configuration


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide a temporary directory for tests"""
    return tmp_path_factory.mktemp("test_data")
