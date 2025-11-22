"""Compatibility shim that re-exports the v2 randomizer adapter."""

from __future__ import annotations

from src.gui_v2.adapters.randomizer_adapter_v2 import (
    RandomizerPlanResult,
    build_randomizer_plan,
    compute_variant_count,
)

__all__ = ["RandomizerPlanResult", "build_randomizer_plan", "compute_variant_count"]
