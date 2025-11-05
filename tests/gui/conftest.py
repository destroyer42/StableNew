import time
import tkinter as tk

import pytest


@pytest.fixture
def tk_pump():
    """Pump Tk events without blocking the main thread.
    
    This fixture provides a function to process Tk event loop iterations
    in a controlled way, which is necessary when UI updates are scheduled
    via root.after(0, ...) or similar asynchronous mechanisms.
    
    Args:
        duration: Time in seconds to pump events (default: 0.2)
        step: Time in seconds between update() calls (default: 0.01)
    """
    def pump(root, duration=0.2, step=0.01):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            try:
                root.update()
            except Exception:
                break
            time.sleep(step)
    return pump
