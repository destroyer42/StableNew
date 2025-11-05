"""Helper to run GUI-triggered smoke tests without blocking Tk."""

from __future__ import annotations

import logging
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol, Sequence

from tkinter import messagebox

logger = logging.getLogger(__name__)


class _CommandRunner(Protocol):
    def __call__(self, command: Sequence[str]) -> "_CommandResult":
        """Callable signature for executing a command."""


@dataclass
class _CommandResult:
    """Lightweight representation of a completed command."""

    returncode: int
    stdout: str
    stderr: str


@dataclass
class TestSummary:
    """Pytest summary counts for convenience."""

    __test__ = False  # Prevent pytest from trying to collect this dataclass as a test case

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def failure_total(self) -> int:
        """Aggregate failing counts (failed + errors)."""

        return self.failed + self.errors


SUMMARY_PATTERN = re.compile(r"(\d+)\s+(passed|failed|errors?|skipped)")


def parse_pytest_summary(output: str | Iterable[str]) -> TestSummary:
    """Parse pytest summary text into counts.

    Args:
        output: Pytest stdout/stderr as string or iterable of lines.

    Returns:
        A ``TestSummary`` populated with parsed counts. Missing values default to 0.
    """

    if isinstance(output, str):
        text = output
    else:
        text = "\n".join(output)

    summary = TestSummary()
    if not text:
        return summary

    for match in SUMMARY_PATTERN.finditer(text):
        count = int(match.group(1))
        label = match.group(2)
        if label.startswith("pass"):
            summary.passed = count
        elif label.startswith("fail"):
            summary.failed = count
        elif label.startswith("error"):
            summary.errors = count
        elif label == "skipped":
            summary.skipped = count

    return summary


class SelfTestRunner:
    """Run smoke tests in a background worker and surface results to the GUI."""

    def __init__(
        self,
        root,
        *,
        command: Sequence[str] | None = None,
        run_command: _CommandRunner | None = None,
        on_log: Callable[[str], None] | None = None,
        on_state_change: Callable[[bool], None] | None = None,
    ) -> None:
        self._root = root
        self._command: tuple[str, ...] = tuple(command or ("pytest", "-k", "smoke", "-q"))
        self._run_command: _CommandRunner = run_command or self._default_run_command
        self._on_log = on_log
        self._on_state_change = on_state_change

        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()
        self._is_running = False

        self._notify_state_change()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def run_smoke_tests(self) -> bool:
        """Kick off the smoke pytest subset on a worker thread.

        Returns ``True`` if the worker was started, ``False`` if a run is already in
        progress.
        """

        with self._lock:
            if self._is_running:
                self._log("Smoke tests already running; ignoring duplicate request.")
                return False
            self._is_running = True

        self._notify_state_change()
        self._log("🧪 Starting smoke tests (pytest -k smoke -q)…")

        self._worker = threading.Thread(target=self._worker_entry, daemon=True)
        self._worker.start()
        return True

    def _worker_entry(self) -> None:
        try:
            raw_result = self._run_command(self._command)
            result = self._coerce_result(raw_result)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Smoke tests invocation raised an exception")
            result = _CommandResult(returncode=1, stdout="", stderr=str(exc))

        self._root.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result: _CommandResult) -> None:
        with self._lock:
            self._is_running = False

        self._notify_state_change()

        combined_output = "\n".join(filter(None, [result.stdout, result.stderr]))
        summary = parse_pytest_summary(combined_output)
        details = self._format_summary(summary)
        success = result.returncode == 0 and summary.failure_total == 0

        if combined_output:
            logger.debug("Smoke tests output:\n%s", combined_output)

        self._log(f"🧪 Smoke tests completed: {details}")

        message = f"Smoke test results:\n{details}"
        if success:
            messagebox.showinfo("Smoke Tests Complete", message)
        else:
            messagebox.showerror("Smoke Tests Failed", message)

    def _coerce_result(self, raw_result) -> _CommandResult:
        if isinstance(raw_result, _CommandResult):
            return raw_result

        stdout = getattr(raw_result, "stdout", "") or ""
        stderr = getattr(raw_result, "stderr", "") or ""
        returncode = getattr(raw_result, "returncode", 1)
        return _CommandResult(returncode=returncode, stdout=stdout, stderr=stderr)

    def _format_summary(self, summary: TestSummary) -> str:
        parts = [f"{summary.passed} passed", f"{summary.failure_total} failed"]
        if summary.skipped:
            parts.append(f"{summary.skipped} skipped")
        return ", ".join(parts)

    def _log(self, message: str) -> None:
        if self._on_log:
            try:
                self._on_log(message)
            except Exception:  # pragma: no cover - avoid breaking UI logging
                logger.exception("Failed to publish self-test log message")
        else:
            logger.info(message)

    def _notify_state_change(self) -> None:
        if self._on_state_change:
            try:
                self._on_state_change(self.is_running)
            except Exception:  # pragma: no cover - avoid breaking UI callbacks
                logger.exception("Self-test state change callback failed")

    def _default_run_command(self, command: Sequence[str]) -> _CommandResult:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
        )
        return self._coerce_result(completed)

