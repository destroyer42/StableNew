"""Tk-free helpers for extracting GUI overrides for the controller/assembler."""

from __future__ import annotations

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
