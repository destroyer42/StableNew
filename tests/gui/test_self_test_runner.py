"""Tests for the smoke self-test runner integration."""

import pytest

pytest.importorskip("tkinter")

from src.gui.self_test_runner import SelfTestRunner, TestSummary, parse_pytest_summary
from src.gui import self_test_runner as runner_module
from tests.gui.conftest import wait_until


class DummyResult:
    def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.mark.gui
def test_parse_pytest_summary_combines_counts():
    output = "1 failed, 3 passed, 2 skipped, 1 error in 0.20s"
    summary = parse_pytest_summary(output)

    assert isinstance(summary, TestSummary)
    assert summary.passed == 3
    assert summary.failed == 1
    assert summary.errors == 1
    assert summary.skipped == 2
    assert summary.failure_total == 2


@pytest.mark.gui
def test_self_test_runner_shows_success_dialog(tk_root, monkeypatch):
    events: list[tuple[str, str, str]] = []
    commands: list[tuple[str, ...]] = []

    def fake_run(command):
        commands.append(tuple(command))
        return DummyResult(0, "collected 2 items\n\n..\n2 passed in 0.10s\n")

    runner = SelfTestRunner(tk_root, run_command=fake_run)

    monkeypatch.setattr(
        runner_module.messagebox,
        "showinfo",
        lambda title, message: events.append(("info", title, message)),
    )
    monkeypatch.setattr(
        runner_module.messagebox,
        "showerror",
        lambda title, message: events.append(("error", title, message)),
    )

    assert runner.run_smoke_tests()
    assert wait_until(lambda: events, tk_root), "Smoke test info dialog was not shown"

    assert events[0][0] == "info"
    assert "2 passed" in events[0][2]
    assert "0 failed" in events[0][2]
    assert commands[0] == ("pytest", "-k", "smoke", "-q")
    assert not any(event[0] == "error" for event in events)


@pytest.mark.gui
def test_self_test_runner_shows_failure_dialog(tk_root, monkeypatch):
    events: list[tuple[str, str, str]] = []

    def fake_run(command):
        return DummyResult(1, "collected 2 items\n\n.F\n1 failed, 1 passed in 0.05s\n")

    runner = SelfTestRunner(tk_root, run_command=fake_run)

    monkeypatch.setattr(
        runner_module.messagebox,
        "showinfo",
        lambda title, message: events.append(("info", title, message)),
    )
    monkeypatch.setattr(
        runner_module.messagebox,
        "showerror",
        lambda title, message: events.append(("error", title, message)),
    )

    assert runner.run_smoke_tests()
    assert wait_until(lambda: any(evt[0] == "error" for evt in events), tk_root)

    error_events = [evt for evt in events if evt[0] == "error"]
    assert error_events, "Expected an error dialog when smoke tests fail"
    title, message = error_events[0][1], error_events[0][2]
    assert "1 failed" in message
    assert "1 passed" in message
    assert title == "Smoke Tests Failed"
    assert not any(evt[0] == "info" for evt in events)
