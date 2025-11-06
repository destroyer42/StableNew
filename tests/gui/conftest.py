"""Test fixtures for GUI tests."""

import time
import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
    """Provide a Tk root window for GUI tests, skip if Tk/Tcl unavailable."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No display available for Tkinter tests")
        return
    root.withdraw()  # headless
    try:
        yield root
    finally:
        try:
            root.destroy()
        except Exception:
            pass


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
