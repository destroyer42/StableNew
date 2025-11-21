"""Randomizer panel scaffold for GUI v2."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme as theme_mod
from src.gui_v2.randomizer_adapter import build_randomizer_plan


class RandomizerPanelV2(ttk.Frame):
    """Container for randomization controls (structure only)."""

    def __init__(self, master: tk.Misc, *, controller=None, theme=None, **kwargs) -> None:
        style_name = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        super().__init__(master, style=style_name, padding=theme_mod.PADDING_MD, **kwargs)
        self.controller = controller
        self.theme = theme

        header_style = getattr(theme, "STATUS_STRONG_LABEL_STYLE", theme_mod.STATUS_STRONG_LABEL_STYLE)
        self.header_label = ttk.Label(self, text="Randomizer", style=header_style)
        self.header_label.pack(anchor=tk.W, pady=(0, 4))

        body_style = getattr(theme, "SURFACE_FRAME_STYLE", theme_mod.SURFACE_FRAME_STYLE)
        self.body = ttk.Frame(self, style=body_style)
        self.body.pack(fill=tk.BOTH, expand=True)

        self.variant_mode_var = tk.StringVar(value="fanout")
        self.fanout_var = tk.StringVar(value="1")
        self.variant_count_var = tk.StringVar(value="Total variants: 1")
        self._variant_count = 1
        self._change_callback = None

        self._matrix_dimensions = (
            {"key": "model", "label": "Model matrix entries", "parser": "simple", "pipeline_field": "model_matrix"},
            {
                "key": "hypernetwork",
                "label": "Hypernetworks (name[:strength])",
                "parser": "hyper",
                "pipeline_field": "hypernetworks",
            },
        )
        self.matrix_vars: dict[str, tk.StringVar] = {}
        self.matrix_entries: dict[str, ttk.Entry] = {}

        self._build_controls()

    def _build_controls(self) -> None:
        ttk.Label(self.body, text="Variant mode", style="Dark.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=2
        )
        mode_box = ttk.Combobox(
            self.body,
            textvariable=self.variant_mode_var,
            state="readonly",
            values=("off", "fanout", "rotate"),
            width=14,
        )
        mode_box.grid(row=0, column=1, sticky=tk.W, pady=2)
        mode_box.set("fanout")
        self.variant_mode_var.trace_add("write", self._handle_var_change)

        ttk.Label(self.body, text="Fanout per variant", style="Dark.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        fanout_spin = ttk.Spinbox(
            self.body,
            from_=1,
            to=999,
            textvariable=self.fanout_var,
            width=6,
        )
        fanout_spin.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.fanout_var.trace_add("write", self._handle_var_change)

        ttk.Label(self.body, textvariable=self.variant_count_var, style="Dark.TLabel").grid(
            row=1, column=2, sticky=tk.W, padx=(10, 0)
        )

        self.body.columnconfigure(1, weight=1)
        row = 2
        for dimension in self._matrix_dimensions:
            label = ttk.Label(self.body, text=dimension["label"], style="Dark.TLabel")
            label.grid(row=row, column=0, sticky=tk.W, pady=2)
            var = tk.StringVar(value="")
            entry = ttk.Entry(self.body, textvariable=var, width=40)
            entry.grid(row=row, column=1, columnspan=2, sticky=tk.EW, pady=2)
            var.trace_add("write", self._handle_var_change)
            self.matrix_vars[dimension["key"]] = var
            self.matrix_entries[dimension["key"]] = entry
            row += 1

    def load_from_config(self, config: dict | None) -> None:
        pipeline_cfg = ((config or {}).get("pipeline") or {})
        mode = pipeline_cfg.get("variant_mode", "fanout") or "fanout"
        self.variant_mode_var.set(str(mode).lower())
        fanout = pipeline_cfg.get("variant_fanout") or 1
        self.fanout_var.set(str(fanout))

        model_values = pipeline_cfg.get("model_matrix") or []
        self.matrix_vars["model"].set(", ".join(str(entry) for entry in model_values if entry))

        hyper_entries = pipeline_cfg.get("hypernetworks") or []
        hyper_texts = []
        for entry in hyper_entries:
            if isinstance(entry, dict):
                name = entry.get("name")
                strength = entry.get("strength")
            else:
                name = entry
                strength = None
            if not name:
                continue
            name_text = str(name).strip()
            if not name_text:
                continue
            if strength is None or strength == "":
                hyper_texts.append(name_text)
            else:
                hyper_texts.append(f"{name_text}:{strength}")
        self.matrix_vars["hypernetwork"].set(", ".join(hyper_texts))

    def get_randomizer_options(self) -> dict:
        selected_mode = (self.variant_mode_var.get() or "").strip().lower()
        active_mode = selected_mode if selected_mode not in {"", "off"} else ""
        fanout = self._coerce_positive_int(self.fanout_var.get(), default=1)

        options: dict[str, object] = {
            "mode": selected_mode or "fanout",
            "fanout": fanout,
        }
        if active_mode:
            options["variant_mode"] = active_mode
        matrix_payload: dict[str, object] = {}

        model_entries = self._parse_simple_entries(self.matrix_vars["model"].get())
        if model_entries:
            options["model_matrix"] = model_entries
            matrix_payload["model"] = model_entries

        hyper_entries = self._parse_hyper_entries(self.matrix_vars["hypernetwork"].get())
        if hyper_entries:
            options["hypernetworks"] = hyper_entries
            matrix_payload["hypernetwork"] = hyper_entries

        if matrix_payload:
            options["matrix"] = matrix_payload

        return options

    def build_variant_plan(self, base_config: dict | None):
        return build_randomizer_plan(base_config, self.get_randomizer_options())

    def set_change_callback(self, callback) -> None:
        self._change_callback = callback

    def update_variant_count(self, count: int) -> None:
        safe_count = max(0, int(count)) if isinstance(count, int) else 0
        if safe_count != self._variant_count:
            self._variant_count = safe_count
        self.variant_count_var.set(f"Total variants: {self._variant_count}")

    def get_variant_count(self) -> int:
        return self._variant_count

    def _handle_var_change(self, *_args) -> None:
        if self._change_callback:
            try:
                self._change_callback()
            except Exception:
                pass

    @staticmethod
    def _coerce_positive_int(value: str | int | None, default: int = 1) -> int:
        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_simple_entries(text: str) -> list[str]:
        if not text:
            return []
        parts = [segment.strip() for segment in text.replace("\n", ",").split(",")]
        return [part for part in parts if part]

    @staticmethod
    def _parse_hyper_entries(text: str) -> list[dict]:
        if not text:
            return []
        entries: list[dict] = []
        for raw_entry in text.replace("\n", ",").split(","):
            cleaned = raw_entry.strip()
            if not cleaned:
                continue
            if ":" in cleaned:
                name, strength_text = cleaned.split(":", 1)
            else:
                name, strength_text = cleaned, ""
            name = name.strip()
            if not name:
                continue
            strength_value = None
            if strength_text.strip():
                try:
                    strength_value = float(strength_text.strip())
                except (TypeError, ValueError):
                    strength_value = None
            entries.append({"name": name, "strength": strength_value})
        return entries
