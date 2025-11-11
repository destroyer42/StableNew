from src.gui.controller import PipelineController
from src.gui.state import GUIState, StateManager


def test_lifecycle_event_set_after_two_runs(monkeypatch):
    """Controller should set lifecycle_event after two sequential runs without hanging."""

    sm = StateManager()
    ctrl = PipelineController(sm)

    # Provide no-op pipeline
    ctrl.set_pipeline(None)

    call_count = {"runs": 0}

    def pipeline_func():
        call_count["runs"] += 1
        return {"ok": True}

    # Run 1
    assert ctrl.start_pipeline(pipeline_func) is True
    # Wait for lifecycle
    assert ctrl.lifecycle_event.wait(timeout=2.0)
    assert sm.is_state(GUIState.IDLE)

    # Reset event for next run (start_pipeline clears it)
    assert ctrl.start_pipeline(pipeline_func) is True
    assert ctrl.lifecycle_event.wait(timeout=2.0)
    assert sm.is_state(GUIState.IDLE)

    assert call_count["runs"] == 2
