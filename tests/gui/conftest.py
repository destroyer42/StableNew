"""Fixtures for GUI tests"""

import time
import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
    """Fixture to provide a Tk root window for GUI tests."""
    try:
        root = tk.Tk()
        root.withdraw()  # headless
        yield root
        try:
            root.destroy()
        except Exception:
            pass
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
