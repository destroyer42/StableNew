from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Callable

from src.api.healthcheck import wait_for_webui_ready, WebUIHealthCheckTimeout
from src.api.webui_process_manager import WebUIProcessConfig, WebUIProcessManager, build_default_webui_process_config
from src.config import app_config


class WebUIConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


class WebUIConnectionController:
    """Encapsulates WebUI connection workflow and state."""

    def __init__(self, *, logger: logging.Logger | None = None, base_url_provider: Callable[[], str] | None = None) -> None:
        self._state = WebUIConnectionState.DISCONNECTED
        self._logger = logger or logging.getLogger(__name__)
        self._base_url_provider = base_url_provider or (lambda: app_config._env_default("STABLENEW_WEBUI_BASE_URL", "http://127.0.0.1:7860"))

    def get_state(self) -> WebUIConnectionState:
        return self._state

    def _set_state(self, state: WebUIConnectionState) -> None:
        self._state = state

    def ensure_connected(self, autostart: bool = True) -> WebUIConnectionState:
        base_url = self._base_url_provider()
        initial_timeout = app_config.get_webui_health_initial_timeout_seconds()
        retry_count = app_config.get_webui_health_retry_count()
        retry_interval = app_config.get_webui_health_retry_interval_seconds()
        total_timeout = app_config.get_webui_health_total_timeout_seconds()
        autostart_enabled = app_config.get_webui_autostart_enabled()

        # fast probe
        self._set_state(WebUIConnectionState.CONNECTING)
        try:
            if wait_for_webui_ready(base_url, timeout=initial_timeout, poll_interval=retry_interval):
                self._set_state(WebUIConnectionState.READY)
                return self._state
        except Exception:
            pass

        if not autostart or not autostart_enabled:
            self._set_state(WebUIConnectionState.ERROR)
            return self._state

        # attempt autostart
        try:
            proc_cfg = build_default_webui_process_config()
            if proc_cfg is None:
                raise RuntimeError("No WebUI process config available")
            WebUIProcessManager(proc_cfg).start()
        except Exception as exc:  # pragma: no cover - surface as error state
            self._logger.warning("WebUI autostart failed: %s", exc)
            self._set_state(WebUIConnectionState.ERROR)
            return self._state

        # wait a bit before retries
        time.sleep(min(10.0, total_timeout))

        for _ in range(max(retry_count, 0)):
            try:
                if wait_for_webui_ready(base_url, timeout=retry_interval, poll_interval=retry_interval):
                    self._set_state(WebUIConnectionState.READY)
                    return self._state
            except WebUIHealthCheckTimeout:
                pass
            except Exception as exc:  # pragma: no cover
                self._logger.debug("WebUI probe failed: %s", exc)
            time.sleep(retry_interval)

        self._set_state(WebUIConnectionState.ERROR)
        return self._state

    def reconnect(self) -> WebUIConnectionState:
        try:
            return self.ensure_connected(autostart=True)
        except Exception as exc:  # pragma: no cover
            self._logger.warning("WebUI reconnect failed: %s", exc)
            self._set_state(WebUIConnectionState.ERROR)
            return self._state


__all__ = ["WebUIConnectionController", "WebUIConnectionState"]
