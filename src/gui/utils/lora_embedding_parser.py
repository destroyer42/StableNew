from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class LoraReference:
    name: str
    weight: float | None = None
    start: int | None = None
    end: int | None = None


@dataclass
class EmbeddingReference:
    name: str
    start: int | None = None
    end: int | None = None


_LORA_PATTERN = re.compile(r"\{lora:([^:}]+)(?::([0-9.]+))?\}")
_EMBED_PATTERN = re.compile(r"<embedding:([^>]+)>")


def parse_loras(text: str) -> List[LoraReference]:
    """Parse LoRA references from prompt text."""
    refs: List[LoraReference] = []
    for match in _LORA_PATTERN.finditer(text or ""):
        name = match.group(1).strip()
        weight_raw = match.group(2)
        try:
            weight = float(weight_raw) if weight_raw is not None else None
        except (TypeError, ValueError):
            weight = None
        refs.append(
            LoraReference(
                name=name,
                weight=weight,
                start=match.start(),
                end=match.end(),
            )
        )
    return refs


def parse_embeddings(text: str) -> List[EmbeddingReference]:
    """Parse embedding references from prompt text."""
    refs: List[EmbeddingReference] = []
    for match in _EMBED_PATTERN.finditer(text or ""):
        name = match.group(1).strip()
        refs.append(
            EmbeddingReference(
                name=name,
                start=match.start(),
                end=match.end(),
            )
        )
    return refs


def parse_prompt_metadata(text: str) -> dict:
    """Return a simple metadata dict for convenience."""
    return {
        "loras": parse_loras(text),
        "embeddings": parse_embeddings(text),
    }
