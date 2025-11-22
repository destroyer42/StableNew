from __future__ import annotations

import time

import requests


class WebUIHealthCheckTimeout(TimeoutError):
    """Raised when WebUI does not respond within the allotted time."""


def wait_for_webui_ready(base_url: str, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
    """Poll a lightweight WebUI endpoint until it responds or timeout occurs."""

    deadline = time.time() + max(timeout, 0)
    poll_delay = max(poll_interval, 0.01)
    last_error: Exception | None = None
    probe_url = f"{base_url.rstrip('/')}/sdapi/v1/progress"

    while time.time() < deadline:
        try:
            response = requests.get(probe_url, timeout=min(timeout, 5.0))
            if response.status_code == 200:
                return True
        except Exception as exc:  # noqa: BLE001 - caller wants concise error later
            last_error = exc
        time.sleep(poll_delay)

    msg = "WebUI did not become ready within allotted time"
    if last_error:
        msg = f"{msg}: {last_error}"
    raise WebUIHealthCheckTimeout(msg)
