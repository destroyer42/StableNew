from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.learning_state import LearningVariant


class LearningPlanTable(ttk.Frame):
    """Center panel for learning plan table display."""

    def __init__(self, master: tk.Misc, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

        # Configure layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create treeview for the plan table
        self._create_table()

    def _create_table(self) -> None:
        """Create the plan table treeview."""
        # Frame for the table
        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # Treeview with columns
        columns = ("variant", "param_value", "stage", "status", "images")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10
        )

        # Define headings
        self.tree.heading("variant", text="Variant #")
        self.tree.heading("param_value", text="Parameter Value")
        self.tree.heading("stage", text="Stage")
        self.tree.heading("status", text="Status")
        self.tree.heading("images", text="Images")

        # Define column widths
        self.tree.column("variant", width=80, anchor="center")
        self.tree.column("param_value", width=120, anchor="center")
        self.tree.column("stage", width=80, anchor="center")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("images", width=80, anchor="center")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Grid the treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def update_plan(self, plan: list[LearningVariant]) -> None:
        """Update the table with the current learning plan."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add variants to the table
        for i, variant in enumerate(plan, 1):
            self.tree.insert(
                "",
                "end",
                values=(
                    f"#{i}",
                    str(variant.param_value),
                    "txt2img",  # TODO: Get from experiment stage
                    variant.status.title(),
                    f"{variant.completed_images}/{variant.planned_images}"
                )
            )