"""Layout tests for stage cards inside PipelinePanelV2."""

from __future__ import annotations

from src.gui.pipeline_panel_v2 import PipelinePanelV2
from src.gui.txt2img_stage_card import Txt2ImgStageCard
from src.gui.img2img_stage_card import Img2ImgStageCard
from src.gui.upscale_stage_card import UpscaleStageCard


def test_stage_cards_present(gui_app_with_dummies):
    gui, _controller, _cfg = gui_app_with_dummies
    panel = gui.pipeline_panel_v2
    assert isinstance(panel, PipelinePanelV2)
    assert isinstance(panel.txt2img_card, Txt2ImgStageCard)
    assert isinstance(panel.img2img_card, Img2ImgStageCard)
    assert isinstance(panel.upscale_card, UpscaleStageCard)
    assert panel.txt2img_card.header_label["text"] == "txt2img Settings"
    assert panel.img2img_card.header_label["text"] == "img2img Settings"
    assert panel.upscale_card.header_label["text"] == "Upscale Settings"
