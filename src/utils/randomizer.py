"""Prompt randomization utilities for txt2img pipeline."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from src.pipeline.variant_planner import (
    VariantPlan,
    VariantSpec,
    apply_variant_to_config,
    build_variant_plan,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_VARIANTS = 512
HARD_MAX_VARIANTS = 8192

@dataclass
class PromptVariant:
    """Represents one randomized prompt."""

    text: str
    label: str | None = None


class PromptRandomizer:
    """Applies Prompt S/R, wildcard, and matrix rules prior to pipeline runs."""

    def __init__(
        self,
        config: dict[str, Any] | None,
        rng: random.Random | None = None,
        max_variants: int | None = None,
    ) -> None:
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled"))
        self._rng = rng or random.Random()
        self._max_variants = self._resolve_max_variants(cfg, max_variants)

        # Prompt S/R
        self._sr_config = cfg.get("prompt_sr", {}) or {}
        self._sr_rules = []
        if self._sr_config.get("enabled"):
            self._sr_rules = [
                rule
                for rule in (self._sr_config.get("rules") or [])
                if rule.get("search") and rule.get("replacements")
            ]
        self._sr_mode = (self._sr_config.get("mode") or "random").lower()
        self._sr_indices = [0] * len(self._sr_rules)

        # Wildcards
        self._wildcard_config = cfg.get("wildcards", {}) or {}
        self._wildcard_tokens = []
        if self._wildcard_config.get("enabled"):
            raw_tokens = self._wildcard_config.get("tokens") or []
            self._wildcard_tokens = [
                token for token in raw_tokens if token.get("token") and token.get("values")
            ]
        self._wildcard_mode = (self._wildcard_config.get("mode") or "random").lower()
        self._wildcard_indices = {token["token"]: 0 for token in self._wildcard_tokens}

        # Matrix
        self._matrix_config = cfg.get("matrix", {}) or {}
        self._matrix_enabled = bool(self._matrix_config.get("enabled"))
        self._matrix_base_prompt = self._matrix_config.get("base_prompt", "")
        self._matrix_prompt_mode = (self._matrix_config.get("prompt_mode") or "replace").lower()
        self._matrix_slots = []
        if self._matrix_enabled:
            self._matrix_slots = [
                slot
                for slot in (self._matrix_config.get("slots") or [])
                if slot.get("name") and slot.get("values")
            ]

        raw_mode = (self._matrix_config.get("mode") or "fanout").lower()
        if raw_mode in {"fanout", "grid", "all"}:
            self._matrix_mode = "fanout"
        elif raw_mode in {"rotate", "random", "per_prompt"}:
            self._matrix_mode = "random"
        elif raw_mode in {"sequential", "round_robin"}:
            self._matrix_mode = "sequential"
        else:
            logger.warning(
                "Randomizer: unknown matrix mode '%s'; defaulting to sequential", raw_mode
            )
            self._matrix_mode = "sequential"

        self._matrix_limit = int(self._matrix_config.get("limit") or 0)
        self._matrix_total_possible = self._estimate_matrix_combo_total()
        self._matrix_effective_limit = self._resolve_matrix_limit()
        self._matrix_combos = self._build_matrix_combos()
        self._matrix_requested = (
            min(self._matrix_total_possible, self._matrix_limit)
            if self._matrix_limit > 0
            else self._matrix_total_possible
        )
        self._matrix_index = 0

        estimated = self.estimated_matrix_combos()
        if estimated:
            slot_names = [slot.get("name") for slot in self._matrix_slots if slot.get("name")]
            logger.info(
                "Randomizer matrix: mode=%s slots=%s limit=%s combos=%s",
                self._matrix_mode,
                ", ".join(slot_names),
                self._matrix_limit,
                estimated,
            )
            if self._matrix_limit == 0 and estimated > 1024:
                logger.warning(
                    "Randomizer: matrix limit is 0 (unlimited) and %s combos were built; "
                    "runs may be slow or memory-heavy.",
                    estimated,
                )

    def generate(self, prompt_text: str) -> list[PromptVariant]:
        """Return one or more prompt variants for the supplied text.

        Matrix prompt_mode behavior:
        - "replace": base_prompt replaces pack prompt (default for backward compatibility)
        - "append": base_prompt is appended to pack prompt with ", " separator
        - "prepend": base_prompt is prepended to pack prompt with ", " separator
        """

        if not self.enabled:
            return [PromptVariant(prompt_text, None)]

        # Determine working prompt based on matrix prompt_mode
        working_prompt = prompt_text
        if self._matrix_enabled and self._matrix_base_prompt:
            base_prompt = self._matrix_base_prompt
            if self._matrix_prompt_mode == "append":
                base_norm = base_prompt.strip().lower()
                prompt_norm = prompt_text.strip().lower()
                if base_norm and prompt_norm.endswith(base_norm):
                    working_prompt = prompt_text
                else:
                    working_prompt = f"{prompt_text}, {base_prompt}"
            elif self._matrix_prompt_mode == "prepend":
                base_norm = base_prompt.strip().lower()
                prompt_norm = prompt_text.strip().lower()
                if base_norm and prompt_norm.startswith(base_norm):
                    working_prompt = prompt_text
                else:
                    working_prompt = f"{base_prompt}, {prompt_text}"
            else:
                working_prompt = base_prompt

        matrix_combos = self._matrix_combos_for_prompt()
        sr_variants = self._expand_prompt_sr(working_prompt)
        matrix_requested = self._matrix_requested if self._matrix_enabled else 1

        variants: list[PromptVariant] = []
        truncated = False
        for sr_text, sr_labels in sr_variants:
            wildcard_variants = self._expand_wildcards(sr_text, list(sr_labels))
            for wildcard_text, wildcard_labels in wildcard_variants:
                for combo in matrix_combos:
                    labels = list(wildcard_labels)
                    final_text = self._apply_matrix(wildcard_text, combo, labels)
                    label_value = "; ".join(labels) or None
                    variants.append(PromptVariant(text=final_text, label=label_value))
                    if len(variants) >= self._max_variants:
                        truncated = True
                        break
                if truncated:
                    break
            if truncated:
                break

        # Deduplicate while preserving order
        deduped: list[PromptVariant] = []
        seen: set[tuple[str, str | None]] = set()
        for variant in variants or [PromptVariant(prompt_text, None)]:
            key = (variant.text, variant.label)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(variant)

        if truncated:
            estimated = self._estimate_variant_upper_bound(
                working_prompt, matrix_requested or 1
            )
            logger.warning(
                "Randomization requested approximately %s combinations but cap is %s; "
                "returning first %s variant(s). Reduce randomization scope or set "
                "`randomization.max_variants` to raise the cap.",
                estimated,
                self._max_variants,
                self._max_variants,
            )

        return deduped or [PromptVariant(prompt_text, None)]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ordered_sr_choices(self, rule_index: int, replacements: list[str]) -> list[str]:
        if self._sr_mode == "round_robin":
            start = self._sr_indices[rule_index]
            rotated = replacements[start:] + replacements[:start]
            return rotated or replacements
        return list(replacements)

    def _select_replacements_for_rule(
        self, rule_index: int, replacements: list[str]
    ) -> list[str]:
        """
        Decide which replacements to use for a given S/R rule.

        - mode == "fanout": use ALL replacements (backward-compatible grid behavior)
        - mode == "random": use ONE random replacement per rule per prompt
        - mode == "round_robin": use ONE replacement, cycling through the list over time
        """
        choices = self._ordered_sr_choices(rule_index, replacements)

        if self._sr_mode == "random":
            return [self._rng.choice(replacements)]
        if self._sr_mode == "round_robin":
            return [choices[0]]
        return list(replacements)

    def _expand_prompt_sr(self, text: str) -> list[tuple[str, list[str]]]:
        variants: list[tuple[str, list[str]]] = [(text, [])]
        if not self._sr_rules:
            return variants

        for idx, rule in enumerate(self._sr_rules):
            search = rule.get("search", "")
            replacements = rule.get("replacements") or []
            if not search or not replacements:
                continue

            selected_replacements = self._select_replacements_for_rule(idx, replacements)
            applied = False
            new_variants: list[tuple[str, list[str]]] = []
            for current_text, current_labels in variants:
                if search not in current_text:
                    new_variants.append((current_text, current_labels))
                    continue
                applied = True
                for replacement in selected_replacements:
                    replaced_text = current_text.replace(search, replacement)
                    new_labels = current_labels + [f"{search}->{replacement}"]
                    new_variants.append((replaced_text, new_labels))
            variants = new_variants or variants
            if applied and self._sr_mode == "round_robin" and replacements:
                start = self._sr_indices[idx]
                self._sr_indices[idx] = (start + 1) % len(replacements)
        return variants

    def _ordered_wildcard_values(self, token_name: str, values: list[str]) -> list[str]:
        if self._wildcard_mode == "sequential":
            start = self._wildcard_indices.get(token_name, 0)
            return values[start:] + values[:start]
        return list(values)

    def _select_values_for_wildcard(
        self, token_name: str, values: list[str]
    ) -> list[str]:
        """
        Decide which values to use for a wildcard token.

        - mode == "fanout": use ALL values (backward-compatible grid behavior)
        - mode == "random": use ONE random value per token per prompt
        - mode == "sequential": use ONE value, cycling through values over time
        """
        choices = self._ordered_wildcard_values(token_name, values)

        if self._wildcard_mode == "random":
            return [self._rng.choice(values)]
        if self._wildcard_mode == "sequential":
            return [choices[0]]
        return list(values)

    def _expand_wildcards(self, text: str, base_labels: list[str]) -> list[tuple[str, list[str]]]:
        variants: list[tuple[str, list[str]]] = [(text, base_labels)]
        if not self._wildcard_tokens:
            return variants

        for token in self._wildcard_tokens:
            token_name = token.get("token")
            values = token.get("values") or []
            if not token_name or not values:
                continue

            selected_values = self._select_values_for_wildcard(token_name, values)
            applied = False
            new_variants: list[tuple[str, list[str]]] = []
            for current_text, current_labels in variants:
                if token_name not in current_text:
                    new_variants.append((current_text, current_labels))
                    continue
                applied = True
                for value in selected_values:
                    replaced_text = current_text.replace(token_name, value)
                    new_labels = current_labels + [f"{token_name}={value}"]
                    new_variants.append((replaced_text, new_labels))
            variants = new_variants or variants
            if applied and self._wildcard_mode == "sequential" and values:
                start = self._wildcard_indices.get(token_name, 0)
                self._wildcard_indices[token_name] = (start + 1) % len(values)
        return variants

    def _apply_matrix(
        self,
        text: str,
        combo: dict[str, str] | None,
        label_parts: list[str],
    ) -> str:
        if not combo:
            return text

        for slot_name, slot_value in combo.items():
            token = f"[[{slot_name}]]"
            if token in text:
                text = text.replace(token, slot_value)
                label_parts.append(f"[{slot_name}]={slot_value}")

        return text

    def _matrix_combos_for_prompt(self) -> list[dict[str, str] | None]:
        """
        Return the matrix combinations to apply for the current prompt.

        - Disabled/no slots -> [None]
        - mode == "fanout": return every combination for this prompt (grid behavior)
        - mode == "random": return one random combo per prompt
        - other modes: return exactly one combo, rotating across prompts ("sequential")
        """
        if not self._matrix_enabled or not self._matrix_slots or not self._matrix_combos:
            return [None]

        if self._matrix_mode == "fanout":
            return self._matrix_combos

        if self._matrix_mode == "random":
            return [self._rng.choice(self._matrix_combos)]

        combo = self._matrix_combos[self._matrix_index]
        self._matrix_index = (self._matrix_index + 1) % len(self._matrix_combos)
        return [combo]

    def _build_matrix_combos(self) -> list[dict[str, str] | None]:
        if not self._matrix_slots:
            return [None]

        combos: list[dict[str, str]] = []
        limit = max(0, self._matrix_effective_limit)

        def backtrack(idx: int, current: dict[str, str]) -> None:
            if limit > 0 and len(combos) >= limit:
                return
            if idx == len(self._matrix_slots):
                combos.append(current.copy())
                return

            slot = self._matrix_slots[idx]
            values = slot.get("values") or []
            for value in values:
                current[slot["name"]] = value
                backtrack(idx + 1, current)
                if limit > 0 and len(combos) >= limit:
                    break

        backtrack(0, {})
        return combos or [None]

    def _resolve_max_variants(
        self, cfg: dict[str, Any], override: int | None = None
    ) -> int:
        candidate = override if override is not None else cfg.get("max_variants")
        try:
            candidate_int = int(candidate)
        except (TypeError, ValueError):
            candidate_int = None

        if candidate_int is None or candidate_int <= 0:
            return DEFAULT_MAX_VARIANTS

        if candidate_int > HARD_MAX_VARIANTS:
            logger.warning(
                "randomization.max_variants=%s exceeds hard safety cap (%s); using %s",
                candidate_int,
                HARD_MAX_VARIANTS,
                HARD_MAX_VARIANTS,
            )
            return HARD_MAX_VARIANTS
        return candidate_int

    def _estimate_matrix_combo_total(self) -> int:
        if not self._matrix_slots:
            return 1
        total = 1
        for slot in self._matrix_slots:
            values = slot.get("values") or []
            total *= max(1, len(values))
        return total

    def _resolve_matrix_limit(self) -> int:
        if not self._matrix_enabled or not self._matrix_slots:
            return 0

        user_limit = max(0, self._matrix_limit)
        if self._matrix_mode != "fanout":
            return user_limit

        if user_limit > 0:
            if user_limit > self._max_variants:
                logger.warning(
                    "Matrix limit %s exceeds randomization max_variants %s; capping to %s",
                    user_limit,
                    self._max_variants,
                    self._max_variants,
                )
            return min(user_limit, self._max_variants)

        if self._matrix_total_possible > self._max_variants:
            logger.warning(
                "Matrix fanout would expand to %s combinations; auto-limiting to %s. "
                "Set matrix.limit or randomization.max_variants to override.",
                self._matrix_total_possible,
                self._max_variants,
            )
            return self._max_variants
        return 0

    def _estimate_variant_upper_bound(self, prompt: str, matrix_count: int) -> int:
        sr_total = 1
        for rule in self._sr_rules:
            search = rule.get("search")
            replacements = rule.get("replacements") or []
            if search and search in prompt and replacements:
                sr_total *= len(replacements)

        wildcard_total = 1
        for token in self._wildcard_tokens:
            token_name = token.get("token")
            values = token.get("values") or []
            if token_name and token_name in prompt and values:
                wildcard_total *= len(values)

        matrix_total = max(1, matrix_count)
        return max(1, sr_total) * max(1, wildcard_total) * matrix_total

    def estimated_matrix_combos(self) -> int:
        """Return how many matrix combinations were pre-computed."""
        if not self._matrix_enabled or not self._matrix_slots:
            return 0
        if not self._matrix_combos:
            return 0
        if len(self._matrix_combos) == 1 and self._matrix_combos[0] is None:
            return 0
        return len(self._matrix_combos)


# --- Minimal stubs for missing functions ---
