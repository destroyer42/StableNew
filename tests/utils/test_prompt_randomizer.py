import random

import pytest

from src.utils.randomizer import PromptRandomizer


def test_prompt_sr_round_robin_reuses_indices():
    config = {
        "enabled": True,
        "prompt_sr": {
            "enabled": True,
            "mode": "round_robin",
            "rules": [
                {"search": "knight", "replacements": ["paladin", "warrior"]},
            ],
        },
    }
    randomizer = PromptRandomizer(config, rng=random.Random(42))
    first = randomizer.generate("a knight in armor")[0]
    second = randomizer.generate("a knight in armor")[0]
    assert first.text == "a paladin in armor"
    assert second.text == "a warrior in armor"


def test_wildcard_random_selection(monkeypatch):
    config = {
        "enabled": True,
        "wildcards": {
            "enabled": True,
            "mode": "random",
            "tokens": [{"token": "__creature__", "values": ["dragon", "phoenix"]}],
        },
    }
    rand = random.Random(0)
    randomizer = PromptRandomizer(config, rng=rand)

    results = {randomizer.generate("a __creature__")[0].text for _ in range(5)}
    assert results == {"a dragon", "a phoenix"}


def test_matrix_fanout_limit():
    config = {
        "enabled": True,
        "matrix": {
            "enabled": True,
            "mode": "fanout",
            "limit": 2,
            "slots": [
                {"name": "Style", "values": ["A", "B"]},
                {"name": "Lighting", "values": ["Day", "Night"]},
            ],
        },
    }
    randomizer = PromptRandomizer(config)
    variants = randomizer.generate("[[Style]] scene at [[Lighting]]")
    assert len(variants) == 2
    assert all("Style" in (variant.label or "") for variant in variants)


def test_matrix_rotate_advances_between_calls():
    config = {
        "enabled": True,
        "matrix": {
            "enabled": True,
            "mode": "rotate",
            "slots": [
                {"name": "Style", "values": ["A", "B"]},
            ],
        },
    }
    randomizer = PromptRandomizer(config)
    first = randomizer.generate("look [[Style]]")[0].text
    second = randomizer.generate("look [[Style]]")[0].text
    assert first == "look A"
    assert second == "look B"
