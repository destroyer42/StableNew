<<<<<<< HEAD
"""Fixtures for GUI tests"""
=======
"""Test fixtures for GUI tests."""
>>>>>>> b61eb89eee85375efbff034c51ee4437992c141e

import time
import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
<<<<<<< HEAD
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
=======
    """Provide a Tk root window for GUI tests."""
    root = tk.Tk()
    root.withdraw()  # headless
    yield root
    try:
        root.destroy()
    except Exception:
        pass
>>>>>>> b61eb89eee85375efbff034c51ee4437992c141e


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
<<<<<<< HEAD
=======


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
>>>>>>> b61eb89eee85375efbff034c51ee4437992c141e
