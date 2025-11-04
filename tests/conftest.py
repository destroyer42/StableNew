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


# Test configuration


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide a temporary directory for tests"""
    return tmp_path_factory.mktemp("test_data")
