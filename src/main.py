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

from .api.webui_process_manager import (
    WebUIProcessConfig,
    WebUIProcessManager,
    build_default_webui_process_config,
)
from .api.healthcheck import wait_for_webui_ready
from .app_factory import build_v2_app
from .gui.main_window import ENTRYPOINT_GUI_CLASS, StableNewGUI
from .gui.main_window_v2 import run_app as run_app_v2
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

def bootstrap_webui(config: dict[str, Any]) -> WebUIProcessManager | None:
    """Best-effort WebUI bootstrap that never blocks GUI startup."""

    proc_config: WebUIProcessConfig | None = config.get("process_config")
    if proc_config is None and config.get("webui_command"):
        proc_config = WebUIProcessConfig(
            command=list(config.get("webui_command") or []),
            working_dir=config.get("webui_workdir"),
            startup_timeout_seconds=float(config.get("webui_startup_timeout_seconds") or 60.0),
            autostart_enabled=bool(config.get("webui_autostart_enabled")),
            base_url=config.get("webui_base_url"),
        )
    if proc_config is None:
        logging.info("WebUI autostart is disabled; GUI will launch without waiting.")
        # Even when disabled, sanity-check health if requested
        if config.get("webui_base_url"):
            try:
                wait_for_webui_ready(config["webui_base_url"], timeout=0.5, poll_interval=0.1)
            except Exception:
                pass
        return None

    manager = WebUIProcessManager(proc_config)
    if proc_config.autostart_enabled:
        try:
            manager.start()
            logging.info("WebUI autostart requested (non-blocking)")
            try:
                base_url = proc_config.base_url or config.get("webui_base_url") or "http://127.0.0.1:7860"
                wait_for_webui_ready(
                    base_url,
                    timeout=proc_config.startup_timeout_seconds,
                    poll_interval=proc_config.poll_interval_seconds,
                )
            except Exception:
                pass
        except Exception as exc:
            logging.warning("WebUI autostart failed (non-fatal): %s", exc)
    else:
        logging.info("WebUI autostart is disabled; GUI will launch without waiting.")
        try:
            base_url = proc_config.base_url or config.get("webui_base_url")
            if base_url:
                wait_for_webui_ready(base_url, timeout=proc_config.startup_timeout_seconds, poll_interval=0.25)
        except Exception:
            pass
    return manager


def _load_webui_config() -> dict[str, Any]:
    cfg = {
        "webui_base_url": os.getenv("STABLENEW_WEBUI_BASE_URL", "http://127.0.0.1:7860"),
    }

    proc_config = build_default_webui_process_config()
    if proc_config:
        env_override_cmd = os.getenv("STABLENEW_WEBUI_COMMAND", "").split()
        if env_override_cmd:
            proc_config.command = env_override_cmd
        workdir_override = os.getenv("STABLENEW_WEBUI_WORKDIR")
        if workdir_override:
            proc_config.working_dir = workdir_override
        autostart_env = os.getenv("STABLENEW_WEBUI_AUTOSTART")
        if autostart_env is not None:
            proc_config.autostart_enabled = autostart_env.lower() in {"1", "true", "yes"}
        timeout_override = os.getenv("STABLENEW_WEBUI_TIMEOUT")
        if timeout_override:
            try:
                proc_config.startup_timeout_seconds = float(timeout_override)
            except Exception:
                pass
        cfg["process_config"] = proc_config
    return cfg



def main() -> None:
    """Main function"""
    setup_logging("INFO")

    logging.info("Starting StableNew V2 GUI (MainWindowV2)")
    webui_manager = bootstrap_webui(_load_webui_config())

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

    root, _, _, _ = build_v2_app(root=tk.Tk(), webui_manager=webui_manager)
    root.mainloop()


if __name__ == "__main__":
    main()
