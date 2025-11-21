"""Tests covering PipelinePanelV2 <-> config roundtrip behavior."""

from __future__ import annotations

from types import SimpleNamespace


def test_pipeline_panel_loads_initial_config(gui_app_with_dummies):
    app, _controller, config_manager = gui_app_with_dummies
    panel = app.pipeline_panel_v2
    base_cfg = config_manager.get_default_config()["txt2img"]

    assert panel.model_var.get() == base_cfg["model"]
    assert panel.vae_var.get() == base_cfg["vae"]
    assert panel.sampler_var.get() == base_cfg["sampler_name"]
    assert panel.scheduler_var.get() == base_cfg["scheduler"]
    assert panel.steps_var.get() == str(base_cfg["steps"])
    assert panel.cfg_scale_var.get() == str(base_cfg["cfg_scale"])
    assert panel.width_var.get() == str(base_cfg["width"])
    assert panel.height_var.get() == str(base_cfg["height"])


def test_pipeline_panel_run_roundtrip(gui_app_with_dummies):
    app, controller, _config_manager = gui_app_with_dummies
    panel = app.pipeline_panel_v2

    panel.model_var.set("new_model")
    panel.vae_var.set("new_vae")
    panel.sampler_var.set("DPM++")
    panel.scheduler_var.set("Karras")
    panel.steps_var.set("42")
    panel.cfg_scale_var.set("9.5")
    panel.width_var.set("960")
    panel.height_var.set("640")

    app._get_selected_packs = lambda: [SimpleNamespace(name="pack1", stem="pack1")]

    run_button = getattr(app, "run_button", app.run_pipeline_btn)
    run_button.invoke()

    assert controller.start_calls == 1
    run_cfg = controller.last_run_config
    assert run_cfg is not None
    txt2img = run_cfg.get("txt2img") or {}

    assert txt2img["model"] == "new_model"
    assert txt2img["vae"] == "new_vae"
    assert txt2img["sampler_name"] == "DPM++"
    assert txt2img["scheduler"] == "Karras"
    assert txt2img["steps"] == 42
    assert txt2img["cfg_scale"] == 9.5
    assert txt2img["width"] == 960
    assert txt2img["height"] == 640
