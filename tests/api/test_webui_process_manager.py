import types
from unittest import mock

import pytest

from src.api.webui_process_manager import WebUIProcessConfig, WebUIProcessManager, WebUIStartupError


class _DummyProcess:
    def __init__(self):
        self.terminated = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True


def test_start_invokes_subprocess_with_config(monkeypatch):
    dummy = _DummyProcess()
    popen_mock = mock.Mock(return_value=dummy)
    monkeypatch.setattr("subprocess.Popen", popen_mock)

    cfg = WebUIProcessConfig(command=["python", "webui.py"], working_dir="/tmp/webui", env_overrides={"A": "1"})
    manager = WebUIProcessManager(cfg)

    process = manager.start()

    assert process is dummy
    popen_mock.assert_called_once()
    kwargs = popen_mock.call_args.kwargs
    assert kwargs["cwd"] == "/tmp/webui"
    assert kwargs["env"].get("A") == "1"


def test_start_raises_structured_error(monkeypatch):
    popen_mock = mock.Mock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("subprocess.Popen", popen_mock)

    manager = WebUIProcessManager(WebUIProcessConfig(command=["bad"]))

    with pytest.raises(WebUIStartupError):
        manager.start()


def test_stop_handles_already_exited_process(monkeypatch):
    dummy = _DummyProcess()
    dummy.poll = types.MethodType(lambda self: 1, dummy)
    popen_mock = mock.Mock(return_value=dummy)
    monkeypatch.setattr("subprocess.Popen", popen_mock)

    manager = WebUIProcessManager(WebUIProcessConfig(command=["python", "webui.py"]))
    manager.start()

    # Process reports exit code; stop should not raise
    manager.stop()
    assert dummy.terminated is False
