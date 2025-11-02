"""Main entry point for StableNew GUI application"""

import sys
from .gui.main_window import StableNewGUI
from .utils import setup_logging


def main():
    """Main function"""
    setup_logging("INFO")

    app = StableNewGUI()
    app.run()


if __name__ == "__main__":
    main()
