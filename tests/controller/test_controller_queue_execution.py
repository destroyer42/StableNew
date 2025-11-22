from __future__ import annotations

from types import SimpleNamespace

from src.controller.pipeline_controller import PipelineController
from src.gui.state import GUIState, StateManager


def test_controller_submits_job_and_transitions_states():
    state_manager = StateManager(initial_state=GUIState.IDLE)
    controller = PipelineController(state_manager=state_manager)
    calls = SimpleNamespace(completed=False)

    def _pipeline_func():
        calls.completed = True
        return {"ok": True}

    controller.start_pipeline(_pipeline_func)
    assert controller._active_job_id is not None
    # runner executes quickly, ensure eventual idle
    assert state_manager.current in {GUIState.RUNNING, GUIState.IDLE}
    controller._job_controller.stop()
    assert calls.completed
    assert state_manager.current in {GUIState.RUNNING, GUIState.IDLE, GUIState.STOPPING}
