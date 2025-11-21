"""Randomizer-specific import isolation tests."""

import importlib
import sys

import pytest


@pytest.mark.parametrize("submodule", ["sanitize", "prompt_sanitizer"])
def test_randomizer_submodules_do_not_import_gui(submodule):
    module_name = f"src.utils.{submodule}" if submodule != "sanitize" else "src.utils.randomizer"
    if module_name in sys.modules:
        del sys.modules[module_name]
    module = importlib.import_module(module_name)
    assert module is not None
    for attr in tuple(sys.modules):
        if attr.startswith("src.gui"):
            raise AssertionError(f"{module_name} imported GUI dependency {attr}")
