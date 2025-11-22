"""Simple dialog for reviewing recent learning runs."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Iterable

from src.learning.learning_record import LearningRecord


class LearningReviewDialogV2(tk.Toplevel):
    """Dialog that lists recent LearningRecords and allows rating/tag edits."""

    def __init__(
        self,
        parent: tk.Misc,
        controller: Any,
        records: Iterable[LearningRecord] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Review Recent Runs")
        self.controller = controller
        self._rows: list[tuple[LearningRecord, tk.StringVar, tk.StringVar]] = []
        self._build_ui(records or [])
        self.grab_set()

    def _build_ui(self, records: Iterable[LearningRecord]) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text="Recent Runs", style="Dark.TLabel")
        header.pack(anchor=tk.W, pady=(0, 6))

        table = ttk.Frame(container)
        table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(table, text="Timestamp").grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Label(table, text="Prompt/Model").grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Label(table, text="Rating").grid(row=0, column=2, sticky=tk.W, padx=4)
        ttk.Label(table, text="Tags").grid(row=0, column=3, sticky=tk.W, padx=4)

        for idx, record in enumerate(records, start=1):
            rating_var = tk.StringVar(value=str(record.metadata.get("rating", "")))
            tags_value = ""
            if record.metadata:
                tags_value = str(record.metadata.get("tags", ""))
            tags_var = tk.StringVar(value=tags_value)
            summary = record.metadata.get("prompt", "") if record.metadata else ""
            model = record.primary_model
            ttk.Label(table, text=record.timestamp).grid(row=idx, column=0, sticky=tk.W, padx=4, pady=2)
            ttk.Label(table, text=f"{summary or record.run_id} / {model}").grid(
                row=idx, column=1, sticky=tk.W, padx=4, pady=2
            )
            rating_spin = ttk.Spinbox(table, from_=1, to=5, textvariable=rating_var, width=4)
            rating_spin.grid(row=idx, column=2, sticky=tk.W, padx=4, pady=2)
            tags_entry = ttk.Entry(table, textvariable=tags_var, width=24)
            tags_entry.grid(row=idx, column=3, sticky=tk.W, padx=4, pady=2)
            self._rows.append((record, rating_var, tags_var))

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(actions, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def _on_save(self) -> None:
        for record, rating_var, tags_var in self._rows:
            try:
                rating = int(rating_var.get())
            except Exception:
                rating = 0
            tags = tags_var.get().strip()
            if hasattr(self.controller, "save_feedback"):
                try:
                    self.controller.save_feedback(record, rating, tags)
                except Exception:
                    continue

    def run_modal(self) -> None:
        """Convenience to start modal loop in tests."""

        try:
            self.wait_window(self)
        except Exception:
            pass
