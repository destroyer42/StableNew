"""V2 randomizer adapter that bridges GUI state to utils.randomizer."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from src.utils.randomizer import apply_variant_to_config, build_variant_plan


@dataclass(frozen=True)
class RandomizerPlanResult:
    """Result bundle returned by the randomizer adapter."""

    base_config: dict
    options: dict
    plan: Any
    configs: list[dict]
    fanout: int = 1

    @property
    def variant_count(self) -> int:
        return len(self.configs)


def build_randomizer_plan(
    base_config: dict | None,
    options: dict | None,
) -> RandomizerPlanResult:
    """Return a plan + per-variant configs using utils.randomizer helpers."""

    working_base = deepcopy(base_config or {})
    fanout = _extract_fanout(options or {})
    normalized_options = _options_to_pipeline_section(options or {}, fanout)

    if normalized_options:
        pipeline_cfg = deepcopy(working_base.get("pipeline") or {})
        pipeline_cfg.update(normalized_options)
        working_base["pipeline"] = pipeline_cfg

    plan = build_variant_plan(working_base)
    configs: list[dict] = []

    variants = getattr(plan, "variants", None) or []
    if variants:
        for variant in variants:
            configs.append(apply_variant_to_config(working_base, variant))

    configs = _apply_fanout(configs, working_base, fanout)

    return RandomizerPlanResult(
        base_config=deepcopy(base_config or {}),
        options=normalized_options,
        plan=plan,
        configs=configs,
        fanout=fanout,
    )


def compute_variant_count(base_config: dict | None, options: dict | None) -> int:
    """Return variant count for the given options/base config."""

    return build_randomizer_plan(base_config, options).variant_count


def _options_to_pipeline_section(options: dict, fanout: int) -> dict:
    pipeline: Dict[str, Any] = {}
    variant_mode = str(options.get("variant_mode", "fanout")).strip().lower()
    if variant_mode:
        pipeline["variant_mode"] = variant_mode

    matrix_entries = _clean_entries(options.get("model_matrix"))
    if matrix_entries:
        pipeline["model_matrix"] = matrix_entries

    hyper_entries = _clean_hyper_entries(options.get("hypernetworks"))
    if hyper_entries:
        pipeline["hypernetworks"] = hyper_entries

    if fanout > 1:
        pipeline["variant_fanout"] = fanout

    return pipeline


def _clean_entries(raw: Any) -> List[str]:
    if isinstance(raw, str):
        candidates: Iterable[str] = raw.split(",")
    elif isinstance(raw, Iterable):
        candidates = raw
    else:
        return []
    cleaned: List[str] = []
    for entry in candidates:
        if entry is None:
            continue
        text = str(entry).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _clean_hyper_entries(raw: Any) -> List[dict]:
    cleaned: List[dict] = []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, Iterable):
        return cleaned
    for entry in raw:
        if entry is None:
            continue
        if isinstance(entry, dict):
            name = entry.get("name")
            strength = entry.get("strength")
        else:
            name = entry
            strength = None
        if name is None:
            continue
        name_text = str(name).strip()
        if not name_text:
            continue
        try:
            strength_value = float(strength) if strength is not None else None
        except (TypeError, ValueError):
            strength_value = None
        cleaned.append({"name": name_text, "strength": strength_value})
    return cleaned


def _extract_fanout(options: dict) -> int:
    candidate = options.get("fanout") or options.get("variant_fanout") or 1
    try:
        value = int(candidate)
        return value if value > 0 else 1
    except (TypeError, ValueError):
        return 1


def _apply_fanout(configs: List[dict], fallback_config: dict, fanout: int) -> List[dict]:
    if fanout <= 1:
        return configs if configs else [deepcopy(fallback_config)]

    source = configs if configs else [deepcopy(fallback_config)]
    expanded: List[dict] = []
    for cfg in source:
        for _ in range(fanout):
            expanded.append(deepcopy(cfg))
    return expanded
