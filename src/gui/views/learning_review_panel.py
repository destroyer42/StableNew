from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from src.gui.learning_state import LearningVariant


class LearningReviewPanel(ttk.Frame):
    """Right panel for learning review and rating controls."""

    def __init__(self, master: tk.Misc, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

        # Configure layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Status section
        self.rowconfigure(1, weight=1)  # Results section
        self.rowconfigure(2, weight=0)  # Rating section

        # Status section
        self.status_frame = ttk.LabelFrame(self, text="Variant Status", padding=5)
        self.status_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.status_label = ttk.Label(self.status_frame, text="No variant selected")
        self.status_label.pack(anchor="w")

        self.progress_label = ttk.Label(self.status_frame, text="")
        self.progress_label.pack(anchor="w")

        # Results section
        self.results_frame = ttk.LabelFrame(self, text="Results", padding=5)
        self.results_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Image list
        self.image_listbox = tk.Listbox(self.results_frame, height=10)
        self.image_listbox.pack(fill="both", expand=True)

        # Rating section
        self.rating_frame = ttk.LabelFrame(self, text="Rating", padding=5)
        self.rating_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        # Rating controls
        rating_frame = ttk.Frame(self.rating_frame)
        rating_frame.pack(fill="x")

        ttk.Label(rating_frame, text="Rating:").pack(side="left")
        self.rating_var = tk.IntVar(value=0)
        for i in range(1, 6):
            ttk.Radiobutton(rating_frame, text=str(i), variable=self.rating_var, value=i).pack(side="left")

        # Notes
        ttk.Label(self.rating_frame, text="Notes:").pack(anchor="w")
        self.notes_text = tk.Text(self.rating_frame, height=3, width=40)
        self.notes_text.pack(fill="x")

        # Rate button
        self.rate_button = ttk.Button(self.rating_frame, text="Rate Image", command=self._rate_image)
        self.rate_button.pack(pady=(5, 0))

    def display_variant_results(self, variant: LearningVariant) -> None:
        """Display results for a completed learning variant."""
        # Update status
        self.status_label.config(text=f"Status: {variant.status.title()}")
        self.progress_label.config(text=f"Images: {variant.completed_images} completed")

        # Clear and populate image list
        self.image_listbox.delete(0, tk.END)
        for image_ref in variant.image_refs:
            self.image_listbox.insert(tk.END, image_ref)

        # Enable/disable rating controls based on status
        state = "normal" if variant.status == "completed" and variant.image_refs else "disabled"
        self.rate_button.config(state=state)

    def _rate_image(self) -> None:
        """Rate the currently selected image."""
        # This would integrate with the learning controller to record ratings
        # For now, just clear the form
        self.rating_var.set(0)
        self.notes_text.delete(1.0, tk.END)