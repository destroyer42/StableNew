"""Tests covering PipelinePanelV2 <-> config roundtrip behavior."""

from __future__ import annotations

from types import SimpleNamespace


def test_pipeline_panel_loads_initial_config(gui_app_with_dummies):
    app, _controller, config_manager = gui_app_with_dummies
    panel = app.pipeline_panel_v2
    base_cfg = config_manager.get_default_config()

    txt_card = panel.txt2img_card
    txt_cfg = base_cfg["txt2img"]
    assert txt_card._vars["model"].get() == txt_cfg["model"]
    assert txt_card._vars["vae"].get() == txt_cfg["vae"]
    assert txt_card._vars["sampler_name"].get() == txt_cfg["sampler_name"]
    assert txt_card._vars["scheduler"].get() == txt_cfg["scheduler"]
    assert txt_card._vars["steps"].get() == str(txt_cfg["steps"])
    assert txt_card._vars["cfg_scale"].get() == str(txt_cfg["cfg_scale"])
    assert txt_card._vars["width"].get() == str(txt_cfg["width"])
    assert txt_card._vars["height"].get() == str(txt_cfg["height"])

    img_cfg = base_cfg["img2img"]
    img_card = panel.img2img_card
    assert img_card._vars["model"].get() == img_cfg["model"]
    assert img_card._vars["sampler_name"].get() == img_cfg["sampler_name"]

    up_card = panel.upscale_card
    up_cfg = base_cfg["upscale"]
    assert up_card._vars["upscaler"].get() == up_cfg["upscaler"]


def test_pipeline_panel_run_roundtrip(gui_app_with_dummies):
    app, controller, _config_manager = gui_app_with_dummies
    panel = app.pipeline_panel_v2

    txt_card = panel.txt2img_card
    txt_card._vars["model"].set("new_model")
    txt_card._vars["vae"].set("new_vae")
    txt_card._vars["sampler_name"].set("DPM++")
    txt_card._vars["scheduler"].set("Karras")
    txt_card._vars["steps"].set("42")
    txt_card._vars["cfg_scale"].set("9.5")
    txt_card._vars["width"].set("960")
    txt_card._vars["height"].set("640")

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
