# --- logging bypass ---
import logging
import os
import socket
import sys
from typing import Any

if os.getenv("STABLENEW_LOGGING_BYPASS") == "1":
    root = logging.getLogger()
    root.handlers.clear()
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(h)
    root.setLevel(logging.DEBUG)
    logging.raiseExceptions = False

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:  # pragma: no cover - Tk not ready
    tk = None
    messagebox = None

from .api.healthcheck import wait_for_webui_ready
from .api.webui_process_manager import WebUIProcessConfig, WebUIProcessManager
from .controller.app_controller import AppController
from .gui.main_window_v2 import MainWindow
from .utils import setup_logging

_INSTANCE_PORT = 47631


def _acquire_single_instance_lock() -> socket.socket | None:
    """Attempt to bind a localhost TCP port as a simple process lock."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", _INSTANCE_PORT))
        sock.listen(1)
    except OSError:
        return None
    return sock


def main():
    """Main function"""
    setup_logging("INFO")

    bootstrap_webui(_load_webui_config())

    lock_sock = _acquire_single_instance_lock()
    if lock_sock is None:
        msg = (
            "StableNew is already running.\n\n"
            "Please close the existing window before starting a new one."
        )
        if messagebox is not None:
            try:
                messagebox.showerror("StableNew", msg)
            except Exception:
                print(msg, file=sys.stderr)
        else:
            print(msg, file=sys.stderr)
        return

    if tk is None:
        print("Tkinter is not available; cannot start StableNew GUI.", file=sys.stderr)
        return

    root = tk.Tk()
    window = MainWindow(root)
    AppController(window, threaded=True)
    root.mainloop()


if __name__ == "__main__":
    main()


def _load_webui_config() -> dict[str, Any]:
    command = os.getenv("STABLENEW_WEBUI_COMMAND", "").split()
    return {
        "webui_autostart_enabled": os.getenv("STABLENEW_WEBUI_AUTOSTART", "false").lower()
        in {"1", "true", "yes"},
        "webui_command": command or ["python", "webui.py"],
        "webui_working_dir": os.getenv("STABLENEW_WEBUI_WORKDIR"),
        "webui_base_url": os.getenv("STABLENEW_WEBUI_BASE_URL", "http://127.0.0.1:7860"),
        "webui_startup_timeout_seconds": float(os.getenv("STABLENEW_WEBUI_TIMEOUT", "30")),
    }


def bootstrap_webui(config: dict[str, Any]) -> None:
    base_url: str = config.get("webui_base_url", "http://127.0.0.1:7860")
    timeout = float(config.get("webui_startup_timeout_seconds", 30))
    poll_interval = min(timeout, 0.5) if timeout else 0.5
    if config.get("webui_autostart_enabled"):
        manager = WebUIProcessManager(
            WebUIProcessConfig(
                command=list(config.get("webui_command") or []),
                working_dir=config.get("webui_working_dir"),
                startup_timeout_seconds=timeout,
            )
        )
        manager.start()
        wait_for_webui_ready(base_url, timeout=timeout, poll_interval=poll_interval)
    else:
        wait_for_webui_ready(base_url, timeout=timeout, poll_interval=poll_interval)
