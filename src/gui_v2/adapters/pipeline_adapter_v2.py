"""Tk-free helpers for extracting GUI overrides for the controller/assembler."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class GuiPipelineOverrides:
    prompt: str = ""
    model: str = ""
    sampler: str = ""
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: float = 7.0
    metadata: dict[str, Any] | None = None


def extract_overrides_from_form(form_data: dict[str, Any]) -> GuiPipelineOverrides:
    """Convert raw form data into structured overrides."""

    return GuiPipelineOverrides(
        prompt=str(form_data.get("prompt", "")),
        model=str(form_data.get("model", "")),
        sampler=str(form_data.get("sampler", "")),
        width=int(form_data.get("width", 512) or 512),
        height=int(form_data.get("height", 512) or 512),
        steps=int(form_data.get("steps", 20) or 20),
        cfg_scale=float(form_data.get("cfg_scale", 7.0) or 7.0),
        metadata=dict(form_data.get("metadata") or {}),
    )


def build_effective_config(
    base_config: dict[str, Any],
    *,
    txt2img_overrides: dict[str, Any] | None = None,
    img2img_overrides: dict[str, Any] | None = None,
    upscale_overrides: dict[str, Any] | None = None,
    pipeline_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge per-stage overrides into a copy of the base config without mutation."""

    effective = deepcopy(base_config or {})

    def _apply(stage: str, overrides: dict[str, Any] | None) -> None:
        if not overrides:
            return
        stage_cfg = effective.setdefault(stage, {})
        stage_cfg.update(deepcopy(overrides))

    _apply("txt2img", txt2img_overrides)
    _apply("img2img", img2img_overrides)
    _apply("upscale", upscale_overrides)
    _apply("pipeline", pipeline_overrides)

    return effective


def run_controller(controller: Any, config: dict[str, Any]) -> Any:
    """Execute controller run entrypoint for tests without GUI bindings."""

    runner = getattr(controller, "run_pipeline", None)
    if callable(runner):
        return runner(config)
    raise AttributeError("controller.run_pipeline is not callable")
