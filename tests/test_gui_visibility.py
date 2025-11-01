#!/usr/bin/env python3
"""Test script to verify GUI visibility and WebUI terminal visibility"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui.main_window import StableNewGUI
import time
import threading

def test_gui_visibility():
    """Test if GUI window becomes visible"""
    print("🔍 Testing GUI visibility...")
    
    app = StableNewGUI()
    
    # Add a timer to auto-close for testing
    def auto_close():
        print("⏰ Auto-closing GUI after 10 seconds for testing")
        time.sleep(10)
        app.root.quit()
    
    # Start auto-close timer in background
    timer_thread = threading.Thread(target=auto_close, daemon=True)
    timer_thread.start()
    
    print("🖥️ Starting GUI - window should appear now")
    app.run()
    print("✅ GUI test completed")

if __name__ == "__main__":
    test_gui_visibility()