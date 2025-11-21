"""Utilities module with lazy exports to avoid heavy imports at package load."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    "ConfigManager",
    "build_sampler_scheduler_payload",
    "StructuredLogger",
    "setup_logging",
    "PreferencesManager",
    "save_image_from_base64",
    "load_image_to_base64",
    "read_text_file",
    "write_text_file",
    "read_prompt_pack",
    "get_prompt_packs",
    "get_safe_filename",
    "find_webui_api_port",
    "wait_for_webui_ready",
]

_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    "ConfigManager": ("src.utils.config", "ConfigManager"),
    "build_sampler_scheduler_payload": ("src.utils.config", "build_sampler_scheduler_payload"),
    "StructuredLogger": ("src.utils.logger", "StructuredLogger"),
    "setup_logging": ("src.utils.logger", "setup_logging"),
    "PreferencesManager": ("src.utils.preferences", "PreferencesManager"),
    "save_image_from_base64": ("src.utils.file_io", "save_image_from_base64"),
    "load_image_to_base64": ("src.utils.file_io", "load_image_to_base64"),
    "read_text_file": ("src.utils.file_io", "read_text_file"),
    "write_text_file": ("src.utils.file_io", "write_text_file"),
    "read_prompt_pack": ("src.utils.file_io", "read_prompt_pack"),
    "get_prompt_packs": ("src.utils.file_io", "get_prompt_packs"),
    "get_safe_filename": ("src.utils.file_io", "get_safe_filename"),
    "find_webui_api_port": ("src.utils.webui_discovery", "find_webui_api_port"),
    "wait_for_webui_ready": ("src.utils.webui_discovery", "wait_for_webui_ready"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _LAZY_IMPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__} has no attribute {name}") from exc
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    base_dir = list(globals().keys())
    base_dir.extend(_LAZY_IMPORTS.keys())
    return sorted(set(base_dir))

