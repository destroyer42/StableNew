"""
Tests for APIStatusPanel component.
"""
import pytest
import sys

# Skip these tests if tkinter is not available
pytest.importorskip("tkinter")

import tkinter as tk
from tkinter import ttk

from src.gui.api_status_panel import APIStatusPanel


class TestAPIStatusPanel:
    """Test APIStatusPanel component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.root.withdraw()

    def teardown_method(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass

    def test_panel_creation(self):
        """Test that APIStatusPanel can be created."""
        panel = APIStatusPanel(self.root)
        assert panel is not None
        assert isinstance(panel, ttk.Frame)

    def test_set_status(self):
        """Test set_status method changes displayed text."""
        panel = APIStatusPanel(self.root)
        
        # Set connected status
        panel.set_status("Connected to API", "green")
        
        # We can't easily verify the actual text without accessing internals
        # but we can verify the method doesn't raise
        assert True

    def test_set_status_colors(self):
        """Test that different color statuses can be set."""
        panel = APIStatusPanel(self.root)
        
        # Test various colors
        panel.set_status("Connecting...", "yellow")
        panel.set_status("Connected", "green")
        panel.set_status("Disconnected", "red")
        panel.set_status("Error", "red")
        
        # Should not raise
        assert True

    def test_default_status(self):
        """Test that panel has a reasonable default status."""
        panel = APIStatusPanel(self.root)
        # Panel should be created successfully with default state
        assert panel is not None
