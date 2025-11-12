"""Prompt randomization utilities for txt2img pipeline."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class PromptVariant:
    """Represents one randomized prompt."""

    text: str
    label: str | None = None


class PromptRandomizer:
    """Applies Prompt S/R, wildcard, and matrix rules prior to pipeline runs."""

    def __init__(self, config: dict[str, Any] | None, rng: random.Random | None = None) -> None:
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled"))
        self._rng = rng or random.Random()

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
                token
                for token in raw_tokens
                if token.get("token") and token.get("values")
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
        self._matrix_mode = (self._matrix_config.get("mode") or "fanout").lower()
        self._matrix_limit = int(self._matrix_config.get("limit") or 0)
        self._matrix_combos = self._build_matrix_combos()
        self._matrix_index = 0

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
            if self._matrix_prompt_mode == "append":
                # Append matrix base_prompt to pack prompt
                working_prompt = f"{prompt_text}, {self._matrix_base_prompt}"
            elif self._matrix_prompt_mode == "prepend":
                # Prepend matrix base_prompt before pack prompt
                working_prompt = f"{self._matrix_base_prompt}, {prompt_text}"
            else:
                # Default "replace" mode - base_prompt replaces pack prompt
                working_prompt = self._matrix_base_prompt

        matrix_combos = self._matrix_combos_for_prompt()
        sr_variants = self._expand_prompt_sr(working_prompt)

        variants: list[PromptVariant] = []
        for sr_text, sr_labels in sr_variants:
            wildcard_variants = self._expand_wildcards(sr_text, list(sr_labels))
            for wildcard_text, wildcard_labels in wildcard_variants:
                for combo in matrix_combos:
                    labels = list(wildcard_labels)
                    final_text = self._apply_matrix(wildcard_text, combo, labels)
                    label_value = "; ".join(labels) or None
                    variants.append(PromptVariant(text=final_text, label=label_value))

        # Deduplicate while preserving order
        deduped: list[PromptVariant] = []
        seen: set[tuple[str, str | None]] = set()
        for variant in variants or [PromptVariant(prompt_text, None)]:
            key = (variant.text, variant.label)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(variant)

        return deduped or [PromptVariant(prompt_text, None)]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ordered_sr_choices(self, rule_index: int, replacements: list[str]) -> list[str]:
        if self._sr_mode == "round_robin":
            start = self._sr_indices[rule_index]
            rotated = replacements[start:] + replacements[:start]
            return rotated or replacements
        if self._sr_mode == "random":
            choices = list(replacements)
            self._rng.shuffle(choices)
            return choices
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

            choices = self._ordered_sr_choices(idx, replacements)
            applied = False
            new_variants: list[tuple[str, list[str]]] = []
            for current_text, current_labels in variants:
                if search not in current_text:
                    new_variants.append((current_text, current_labels))
                    continue
                applied = True
                for replacement in choices:
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
        if self._wildcard_mode == "random":
            choices = list(values)
            self._rng.shuffle(choices)
            return choices
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

            choices = self._ordered_wildcard_values(token_name, values)
            applied = False
            new_variants: list[tuple[str, list[str]]] = []
            for current_text, current_labels in variants:
                if token_name not in current_text:
                    new_variants.append((current_text, current_labels))
                    continue
                applied = True
                for value in choices:
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
        if not self._matrix_enabled or not self._matrix_slots or not self._matrix_combos:
            return [None]

        if self._matrix_mode == "fanout":
            return self._matrix_combos

        combo = self._matrix_combos[self._matrix_index]
        self._matrix_index = (self._matrix_index + 1) % len(self._matrix_combos)
        return [combo]

    def _build_matrix_combos(self) -> list[dict[str, str] | None]:
        if not self._matrix_slots:
            return [None]

        combos: list[dict[str, str]] = []
        limit = max(0, self._matrix_limit)

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


# --- Minimal stubs for missing functions ---
def build_variant_plan(*args, **kwargs):
    return []


def apply_variant_to_config(*args, **kwargs):
    return {}
