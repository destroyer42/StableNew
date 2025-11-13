# --- logging bypass ---
import logging
import os

if os.getenv("STABLENEW_LOGGING_BYPASS") == "1":
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(h)
    root.setLevel(logging.DEBUG)
    logging.raiseExceptions = False

from .gui.main_window import StableNewGUI
from .utils import setup_logging


def main():
    """Main function"""
    setup_logging("INFO")

    app = StableNewGUI()
    app.run()


if __name__ == "__main__":
    main()
