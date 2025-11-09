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
        """Return one or more prompt variants for the supplied text."""

        if not self.enabled:
            return [PromptVariant(prompt_text, None)]

        matrix_combos = self._matrix_combos_for_prompt()
        variants: list[PromptVariant] = []

        for combo in matrix_combos:
            text = prompt_text
            label_parts: list[str] = []

            text = self._apply_prompt_sr(text, label_parts)
            text = self._apply_wildcards(text, label_parts)
            text = self._apply_matrix(text, combo, label_parts)

            variants.append(PromptVariant(text=text, label="; ".join(label_parts) or None))

        return variants or [PromptVariant(prompt_text, None)]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_prompt_sr(self, text: str, label_parts: list[str]) -> str:
        if not self._sr_rules:
            return text

        for idx, rule in enumerate(self._sr_rules):
            search = rule.get("search", "")
            replacements = rule.get("replacements") or []
            if not search or not replacements or search not in text:
                continue

            if self._sr_mode == "round_robin":
                choice = replacements[self._sr_indices[idx]]
                self._sr_indices[idx] = (self._sr_indices[idx] + 1) % len(replacements)
            else:
                choice = self._rng.choice(replacements)

            text = text.replace(search, choice)
            label_parts.append(f"{search}->{choice}")

        return text

    def _apply_wildcards(self, text: str, label_parts: list[str]) -> str:
        if not self._wildcard_tokens:
            return text

        for token in self._wildcard_tokens:
            token_name = token.get("token")
            values = token.get("values") or []
            if not token_name or not values or token_name not in text:
                continue

            if self._wildcard_mode == "sequential":
                idx = self._wildcard_indices.get(token_name, 0)
                choice = values[idx % len(values)]
                self._wildcard_indices[token_name] = (idx + 1) % len(values)
            else:
                choice = self._rng.choice(values)

            text = text.replace(token_name, choice)
            label_parts.append(f"{token_name}={choice}")

        return text

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
