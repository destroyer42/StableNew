"""Tk-free helpers for building effective pipeline configs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


def _merge_section(target: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(target) if target else {}
    for key, value in (overrides or {}).items():
        merged[key] = value
    return merged


def build_effective_config(
    base_config: dict[str, Any],
    *,
    txt2img_overrides: dict[str, Any] | None = None,
    img2img_overrides: dict[str, Any] | None = None,
    upscale_overrides: dict[str, Any] | None = None,
    pipeline_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a merged config without mutating the base dict."""

    effective = deepcopy(base_config or {})
    effective["txt2img"] = _merge_section(effective.get("txt2img", {}), txt2img_overrides)
    effective["img2img"] = _merge_section(effective.get("img2img", {}), img2img_overrides)
    effective["upscale"] = _merge_section(effective.get("upscale", {}), upscale_overrides)
    effective["pipeline"] = _merge_section(effective.get("pipeline", {}), pipeline_overrides)
    return effective


def run_controller(controller: Any, config: dict[str, Any], *, runner: Callable | None = None):
    """
    Invoke the controller run entry point with the provided config.

    Prefers a supplied runner callable; otherwise attempts common method names
    without altering semantics.
    """

    payload = deepcopy(config or {})
    if runner is not None:
        return runner(payload)

    for attr in ("run_pipeline", "run", "start_pipeline"):
        candidate = getattr(controller, attr, None)
        if callable(candidate):
            return candidate(payload)

    raise AttributeError("Controller does not expose a compatible run method")
