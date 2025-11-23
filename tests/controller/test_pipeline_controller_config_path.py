from unittest import mock

from src.controller.pipeline_controller import PipelineController
from src.controller.pipeline_config_assembler import PipelineConfigAssembler, GuiOverrides
from src.gui.state import StateManager


def test_controller_uses_assembler_for_runs(monkeypatch):
    sm = StateManager()
    assembler = PipelineConfigAssembler()
    monkeypatch.setattr("src.controller.pipeline_controller.PipelineConfigAssembler", lambda *args, **kwargs: assembler)
    controller = PipelineController(state_manager=sm)

    assembler.build_from_gui_input = mock.Mock(
        return_value=assembler.build_from_gui_input(overrides=GuiOverrides(prompt="p"))
    )
    controller._queue_execution_enabled = False

    def dummy_pipeline():
        return {}

    controller.start_pipeline(dummy_pipeline)
    assembler.build_from_gui_input.assert_called()
