"""Shared GUI test fixtures."""

import os
import sys
import tkinter as tk

import pytest


@pytest.fixture
def tk_root():
    """Provide a Tk root window or skip if not available."""
    if sys.platform.startswith("linux") and "DISPLAY" not in os.environ:
        # Allow CI setups to inject their own xvfb display
        os.environ.setdefault("DISPLAY", ":99")

    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("Tk not available in headless environment")

    yield root

    try:
        root.destroy()
    except Exception:
        pass
