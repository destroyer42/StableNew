from __future__ import annotations

import time

import requests


class WebUIHealthCheckTimeout(TimeoutError):
    """Raised when WebUI does not respond within the allotted time."""


def wait_for_webui_ready(base_url: str, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(
        "healthcheck.wait_for_webui_ready called with base_url=%s timeout=%s poll_interval=%s",
        base_url,
        timeout,
        poll_interval,
    )
    """Poll a lightweight WebUI endpoint until it responds or timeout occurs."""

    deadline = time.time() + max(timeout, 0)
    poll_delay = max(poll_interval, 0.01)
    last_error: Exception | None = None
    probe_url = f"{base_url.rstrip('/')}/sdapi/v1/progress"
    logger.info(f"Probing WebUI at: {probe_url}")

    while time.time() < deadline:
        try:
            response = requests.get(probe_url, timeout=min(timeout, 5.0))
            if response.status_code == 200:
                logger.info(f"WebUI API ready at: {probe_url}")
                return True
        except Exception as exc:  # noqa: BLE001 - caller wants concise error later
            last_error = exc
            logger.debug(f"WebUI probe failed: {exc}")
        time.sleep(poll_delay)

    msg = "WebUI did not become ready within allotted time"
    if last_error:
        msg = f"{msg}: {last_error}"
    raise WebUIHealthCheckTimeout(msg)


def find_webui_port(base_url_template: str = "http://127.0.0.1:{port}", ports: list[int] | None = None) -> str | None:
    """Try to find WebUI running on common ports."""
    if ports is None:
        ports = [7860, 7861, 7862, 7863, 7864, 8000, 8080, 5000]
    
    import logging
    logger = logging.getLogger(__name__)
    
    for port in ports:
        url = base_url_template.format(port=port)
        probe_url = f"{url.rstrip('/')}/sdapi/v1/progress"
        try:
            logger.info(f"Checking for WebUI API on port {port}: {probe_url}")
            response = requests.get(probe_url, timeout=2.0)
            if response.status_code == 200:
                logger.info(f"Found WebUI API on port {port}")
                return url
        except Exception as exc:
            logger.debug(f"Port {port} API not responding: {exc}")
            
            # Also try the web interface (without API)
            try:
                web_url = f"{url.rstrip('/')}/"
                logger.debug(f"Checking for WebUI web interface on port {port}: {web_url}")
                response = requests.get(web_url, timeout=2.0)
                if response.status_code == 200:
                    logger.warning(f"Found WebUI web interface on port {port} but API not enabled. Please start WebUI with --api flag.")
            except Exception:
                pass
    
    return None
