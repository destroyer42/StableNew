from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Mapping


class WebUIStartupError(RuntimeError):
    """Raised when WebUI fails to start."""


@dataclass
class WebUIProcessConfig:
    command: list[str]
    working_dir: str | None = None
    env_overrides: Mapping[str, str] | None = None
    startup_timeout_seconds: float = 60.0
    poll_interval_seconds: float = 0.5

    def build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update({k: v for k, v in (self.env_overrides or {}).items()})
        return env


class WebUIProcessManager:
    """Owns the lifecycle of the external WebUI process."""

    def __init__(self, config: WebUIProcessConfig) -> None:
        self._config = config
        self._process: subprocess.Popen | None = None

    @property
    def process(self) -> subprocess.Popen | None:
        return self._process

    def start(self) -> subprocess.Popen:
        """Start the WebUI process if not already running."""

        if self._process and self.is_running():
            return self._process

        try:
            self._process = subprocess.Popen(
                self._config.command,
                cwd=self._config.working_dir or None,
                env=self._config.build_env(),
            )
        except Exception as exc:  # noqa: BLE001 - surface structured error
            raise WebUIStartupError(f"Failed to start WebUI: {exc}") from exc

        return self._process

    def stop(self) -> None:
        """Attempt to terminate the process if running."""

        if not self._process:
            return

        if self.is_running():
            try:
                self._process.terminate()
            except Exception:
                pass

        self._process = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
