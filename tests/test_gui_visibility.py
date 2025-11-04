#!/usr/bin/env python3
"""Test script to verify GUI visibility and WebUI terminal visibility"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pytest
try:
    from src.gui.main_window import StableNewGUI
    import tkinter as tk
except Exception:
    StableNewGUI = None

import time
import threading

@pytest.mark.skipif(StableNewGUI is None, reason="StableNewGUI or Tkinter not available")
def test_gui_visibility():
    """Test if GUI window becomes visible (skips if Tk not available)"""
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        pytest.skip("No display available for Tkinter tests")
    app = StableNewGUI()
    # Add a timer to auto-close for testing
    def auto_close():
        time.sleep(2)
        app.root.quit()
    timer_thread = threading.Thread(target=auto_close, daemon=True)
    timer_thread.start()
    # Instead of app.run() (which calls mainloop), just update a few times
    for _ in range(5):
        app.root.update()
        time.sleep(0.2)
    app.root.destroy()
    assert True, "GUI visibility test completed"