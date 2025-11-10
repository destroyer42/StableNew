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
    first_run = randomizer.generate("a knight in armor")
    assert [variant.text for variant in first_run] == [
        "a paladin in armor",
        "a warrior in armor",
    ]

    second_run = randomizer.generate("a knight in armor")
    assert [variant.text for variant in second_run] == [
        "a warrior in armor",
        "a paladin in armor",
    ]


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

    variants = randomizer.generate("a __creature__")
    assert {variant.text for variant in variants} == {"a dragon", "a phoenix"}


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


def test_randomizer_combines_all_features():
    config = {
        "enabled": True,
        "prompt_sr": {
            "enabled": True,
            "mode": "round_robin",
            "rules": [
                {"search": "hero", "replacements": ["hero", "champion"]},
            ],
        },
        "wildcards": {
            "enabled": True,
            "mode": "sequential",
            "tokens": [
                {"token": "__creature__", "values": ["dragon", "phoenix"]},
            ],
        },
        "matrix": {
            "enabled": True,
            "mode": "fanout",
            "limit": 0,
            "slots": [
                {"name": "Weather", "values": ["day", "night"]},
            ],
        },
    }
    randomizer = PromptRandomizer(config)
    variants = randomizer.generate("[[Weather]] hero vs __creature__")

    assert len(variants) == 8
    texts = {variant.text for variant in variants}
    assert texts == {
        "day hero vs dragon",
        "day hero vs phoenix",
        "day champion vs dragon",
        "day champion vs phoenix",
        "night hero vs dragon",
        "night hero vs phoenix",
        "night champion vs dragon",
        "night champion vs phoenix",
    }
