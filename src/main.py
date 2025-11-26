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
from .app_factory import build_v2_app
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
    """Bootstrap WebUI using the proper connection controller framework."""

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
        logging.info("No WebUI configuration available")
        return None

    # Use the proper connection controller framework
    from src.controller.webui_connection_controller import WebUIConnectionController
    connection_controller = WebUIConnectionController()
    
    # Try to ensure connection (will start WebUI if configured and needed)
    try:
        state = connection_controller.ensure_connected(autostart=proc_config.autostart_enabled)
        logging.info(f"WebUI connection state: {state}")
        
        # Create manager for the window (even if we didn't start it)
        manager = WebUIProcessManager(proc_config)
        return manager
        
    except Exception as e:
        logging.warning(f"WebUI bootstrap failed: {e}")
        return None


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



def _async_bootstrap_webui(root: tk.Tk, app_state, window) -> None:
    """Asynchronously bootstrap WebUI after GUI is loaded."""
    import threading
    
    def _bootstrap_worker():
        try:
            config = _load_webui_config()
            webui_manager = bootstrap_webui(config)
            if webui_manager:
                # Update the window with the WebUI manager
                root.after(0, lambda: _update_window_webui_manager(window, webui_manager))
                logging.info("WebUI bootstrap completed asynchronously")
        except Exception as e:
            logging.warning(f"Async WebUI bootstrap failed: {e}")
    
    # Start bootstrap in background thread
    thread = threading.Thread(target=_bootstrap_worker, daemon=True)
    thread.start()


def _update_window_webui_manager(window, webui_manager: WebUIProcessManager) -> None:
    """Update the window with the WebUI manager (called from main thread)."""
    window.webui_process_manager = webui_manager
    
    # Set up WebUI status monitoring using the proper framework
    if hasattr(window, 'status_bar_v2') and window.status_bar_v2:
        try:
            webui_panel = getattr(window.status_bar_v2, 'webui_panel', None)
            if webui_panel:
                # Create a proper WebUI connection controller
                from src.controller.webui_connection_controller import WebUIConnectionController
                connection_controller = WebUIConnectionController()
                
                # Connect the status panel to the controller
                def update_status() -> None:
                    """Update the status panel with current connection state."""
                    try:
                        state = connection_controller.get_state()
                        logging.info(f"WebUI status update: state = {state}")
                        webui_panel.set_webui_state(state)
                    except Exception as e:
                        logging.warning(f"Status update failed: {e}")
                        from src.controller.webui_connection_controller import WebUIConnectionState
                        webui_panel.set_webui_state(WebUIConnectionState.ERROR)
                
                # Set up callbacks for the buttons
                def launch_callback() -> None:
                    try:
                        logging.info("Launch WebUI button clicked")
                        # Try to ensure connection (will start WebUI if needed)
                        new_state = connection_controller.ensure_connected(autostart=True)
                        webui_panel.set_webui_state(new_state)
                    except Exception as e:
                        logging.warning(f"Failed to launch WebUI: {e}")
                
                def retry_callback() -> None:
                    try:
                        logging.info("Retry WebUI connection button clicked")
                        # Try to reconnect
                        new_state = connection_controller.reconnect()
                        webui_panel.set_webui_state(new_state)
                    except Exception as e:
                        logging.warning(f"Failed to retry WebUI connection: {e}")
                
                webui_panel.set_launch_callback(launch_callback)
                webui_panel.set_retry_callback(retry_callback)
                
                # Initial status check
                update_status()
                
                # Set up periodic status checking
                def periodic_check() -> None:
                    update_status()
                    window.after(5000, periodic_check)  # Check every 5 seconds
                
                window.after(1000, periodic_check)  # Start checking after 1 second
                
        except Exception as e:
            logging.debug(f"Failed to set up WebUI status monitoring: {e}")


def main() -> None:
    """Main function"""
    setup_logging("INFO")

    logging.info("Starting StableNew V2 GUI (MainWindowV2)")
    # Don't bootstrap WebUI synchronously - do it asynchronously after GUI loads
    webui_manager = None

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

    root, app_state, app_controller, window = build_v2_app(root=tk.Tk(), webui_manager=webui_manager)
    
    # Start WebUI connection/bootstrap asynchronously after GUI is shown
    root.after(500, lambda: _async_bootstrap_webui(root, app_state, window))
    
    root.mainloop()


if __name__ == "__main__":
    main()
