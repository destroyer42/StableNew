from src.controller.pipeline_config_assembler import PipelineConfigAssembler


def test_build_pipeline_config_applies_overrides_and_limits():
    assembler = PipelineConfigAssembler(max_megapixels=1.0)
    gui_overrides = {
        "prompt": "hello",
        "model": "sdxl",
        "sampler": "Euler",
        "width": 2048,
        "height": 2048,
    }

    config = assembler.build_pipeline_config(gui_overrides=gui_overrides)

    assert config.prompt == "hello"
    # width/height should be clamped down to respect megapixel limit
    assert config.width * config.height <= 1_000_000
    assert config.model == "sdxl"


def test_build_pipeline_config_includes_metadata():
    assembler = PipelineConfigAssembler()
    config = assembler.build_pipeline_config(gui_overrides={"prompt": "hi"}, learning_enabled=True)

    assert config.metadata.get("learning_enabled") is True
