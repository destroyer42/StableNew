import unittest
from unittest.mock import MagicMock
import tkinter as tk

# This import will fail until we create the PromptPackPanel class
from src.gui.prompt_pack_panel import PromptPackPanel

class TestPromptPackPanel(unittest.TestCase):

    def test_panel_instantiation(self):
        """
        Test that the PromptPackPanel can be instantiated.
        """
        # Create a mock parent widget and a mock coordinator
        parent = tk.Frame()
        mock_coordinator = MagicMock()
        mock_list_manager = MagicMock()

        # Attempt to instantiate the panel
        # This will fail if the class cannot be imported or if the constructor has issues
        panel = PromptPackPanel(parent, mock_coordinator, mock_list_manager)

        # Assert that the panel is created and is a tkinter Frame
        self.assertIsInstance(panel, tk.Frame)
        self.assertIsNotNone(panel)

if __name__ == '__main__':
    unittest.main()
