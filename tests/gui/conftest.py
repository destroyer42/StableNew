"""Shared fixtures and utilities for GUI tests."""

import time


def wait_until(predicate, tk_root, timeout=1.0, interval=0.01):
    """Pump Tk events until predicate returns True or timeout expires.

    Args:
        predicate: Callable that returns True when the condition is met
        tk_root: Tk root window to pump events on
        timeout: Maximum time in seconds to wait
        interval: Time in seconds between checks

    Returns:
        True if predicate returned True, False if timeout expired
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tk_root.update()
        if predicate():
            return True
        time.sleep(interval)
    return False
