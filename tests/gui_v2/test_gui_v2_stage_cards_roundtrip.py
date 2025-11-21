"""Roundtrip tests for stage cards."""

from __future__ import annotations


def test_stage_cards_roundtrip(gui_app_with_dummies):
    gui, _controller, config_manager = gui_app_with_dummies
    panel = gui.pipeline_panel_v2
    base_config = config_manager.get_default_config()
    panel.load_from_config(base_config)
    delta = panel.to_config_delta()
    assert delta["txt2img"] == base_config["txt2img"]
    assert delta["img2img"] == base_config["img2img"]
    assert delta["upscale"] == base_config["upscale"]
