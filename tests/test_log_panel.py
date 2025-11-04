
"""Tests for LogPanel log method and scrolling.
Created: 2025-11-02 22:31:47
Updated: 2025-11-04
"""
from src.gui.log_panel import LogPanel
import time

def test_log_appends_to_widget_and_scrolls(tk_root):
    """Test that log() appends messages and keeps view at bottom."""
    panel = LogPanel(tk_root, height=3)
    
    # Add several log messages to force scrolling
    for i in range(20):
        panel.log(f"Message {i+1}", "INFO")
    
    # Process the queue with multiple update cycles
    for _ in range(3):
        tk_root.update()
        time.sleep(0.1)
    
    # Check that messages were added
    log_content = panel.log_text.get("1.0", "end-1c")
    assert "Message 1" in log_content
    assert "Message 20" in log_content
    
    # Verify scrolled near the bottom
    yview = panel.log_text.yview()
    # Should be scrolled to bottom (bottom_fraction should be high)
    # Using 0.9 threshold to account for Tk event loop timing
    assert yview[1] >= 0.9, f"Not scrolled near bottom: yview={yview}"
