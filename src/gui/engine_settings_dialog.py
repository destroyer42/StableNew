"""Dialog for editing a curated subset of WebUI engine settings."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict

from src.api.client import SDWebUIClient


class EngineSettingsDialog(tk.Toplevel):
    """
    Minimal dialog to edit select /sdapi/v1/options settings.
    """

    def __init__(self, parent: tk.Misc, client: SDWebUIClient) -> None:
        super().__init__(parent)
        self.title("Engine Settings")
        self.client = client
        self._options: Dict[str, Any] = {}

        self._jpeg_quality_var = tk.IntVar(value=95)
        self._webp_lossless_var = tk.BooleanVar()
        self._img_max_size_mp_var = tk.DoubleVar(value=0.0)

        self._enable_pnginfo_var = tk.BooleanVar(value=True)
        self._save_txt_var = tk.BooleanVar()
        self._add_model_name_var = tk.BooleanVar(value=True)
        self._add_model_hash_var = tk.BooleanVar(value=True)
        self._add_vae_name_var = tk.BooleanVar(value=True)
        self._add_vae_hash_var = tk.BooleanVar(value=True)

        self._show_progressbar_var = tk.BooleanVar(value=True)
        self._live_previews_enable_var = tk.BooleanVar(value=True)
        self._show_progress_every_n_steps_var = tk.IntVar(value=10)
        self._live_preview_refresh_period_var = tk.DoubleVar(value=0.5)
        self._interrupt_after_current_var = tk.BooleanVar()

        self._memmon_poll_rate_var = tk.DoubleVar(value=0.5)
        self._enable_upscale_progressbar_var = tk.BooleanVar(value=True)
        self._samples_log_stdout_var = tk.BooleanVar()

        self._build_ui()
        self._load_options()

        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_output_tab(notebook)
        self._build_metadata_tab(notebook)
        self._build_runtime_tab(notebook)
        self._build_monitor_tab(notebook)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="Apply", command=self._on_apply).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right")

    def _build_output_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Output")

        row = 0
        ttk.Label(frame, text="JPEG quality (1–100):").grid(row=row, column=0, sticky="w")
        ttk.Spinbox(
            frame,
            from_=1,
            to=100,
            textvariable=self._jpeg_quality_var,
            width=6,
        ).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Checkbutton(
            frame,
            text="Use lossless WebP",
            variable=self._webp_lossless_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Label(frame, text="Max image size (MP):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self._img_max_size_mp_var, width=8).grid(
            row=row, column=1, sticky="w"
        )

    def _build_metadata_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Metadata")

        options = [
            ("Write infotext into PNG metadata", self._enable_pnginfo_var),
            ("Save .txt next to every image", self._save_txt_var),
            ("Add model name to infotext", self._add_model_name_var),
            ("Add model hash to infotext", self._add_model_hash_var),
            ("Add VAE name to infotext", self._add_vae_name_var),
            ("Add VAE hash to infotext", self._add_vae_hash_var),
        ]
        for row, (label, var) in enumerate(options):
            ttk.Checkbutton(frame, text=label, variable=var).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=(0 if row == 0 else 2, 0),
            )

    def _build_runtime_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Runtime")

        row = 0
        ttk.Checkbutton(
            frame,
            text="Show progress bar",
            variable=self._show_progressbar_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Checkbutton(
            frame,
            text="Enable live previews",
            variable=self._live_previews_enable_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Label(frame, text="Preview every N steps:").grid(row=row, column=0, sticky="w")
        ttk.Spinbox(
            frame,
            from_=1,
            to=999,
            textvariable=self._show_progress_every_n_steps_var,
            width=6,
        ).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frame, text="Live preview refresh (s):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self._live_preview_refresh_period_var, width=8).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        ttk.Checkbutton(
            frame,
            text="Interrupt only after current image",
            variable=self._interrupt_after_current_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")

    def _build_monitor_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Monitoring")

        row = 0
        ttk.Label(frame, text="VRAM poll rate (Hz):").grid(row=row, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self._memmon_poll_rate_var, width=8).grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        ttk.Checkbutton(
            frame,
            text="Show upscaling progress bar",
            variable=self._enable_upscale_progressbar_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Checkbutton(
            frame,
            text="Log samples to stdout",
            variable=self._samples_log_stdout_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w")

    def _load_options(self) -> None:
        try:
            self._options = self.client.get_options()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Engine Settings", f"Failed to load engine settings: {exc}")
            self.destroy()
            return

        get = self._options.get

        self._jpeg_quality_var.set(int(get("jpeg_quality", 95)))
        self._webp_lossless_var.set(bool(get("webp_lossless", False)))
        self._img_max_size_mp_var.set(float(get("img_max_size_mp", 0)))

        self._enable_pnginfo_var.set(bool(get("enable_pnginfo", True)))
        self._save_txt_var.set(bool(get("save_txt", False)))
        self._add_model_name_var.set(bool(get("add_model_name_to_info", True)))
        self._add_model_hash_var.set(bool(get("add_model_hash_to_info", True)))
        self._add_vae_name_var.set(bool(get("add_vae_name_to_info", True)))
        self._add_vae_hash_var.set(bool(get("add_vae_hash_to_info", True)))

        self._show_progressbar_var.set(bool(get("show_progressbar", True)))
        self._live_previews_enable_var.set(bool(get("live_previews_enable", True)))
        self._show_progress_every_n_steps_var.set(int(get("show_progress_every_n_steps", 10)))
        self._live_preview_refresh_period_var.set(
            float(get("live_preview_refresh_period", 0.5))
        )
        self._interrupt_after_current_var.set(bool(get("interrupt_after_current", False)))

        self._memmon_poll_rate_var.set(float(get("memmon_poll_rate", 0.5)))
        self._enable_upscale_progressbar_var.set(bool(get("enable_upscale_progressbar", True)))
        self._samples_log_stdout_var.set(bool(get("samples_log_stdout", False)))

    def _on_apply(self) -> None:
        updates: Dict[str, Any] = {
            "jpeg_quality": int(self._jpeg_quality_var.get()),
            "webp_lossless": bool(self._webp_lossless_var.get()),
            "img_max_size_mp": float(self._img_max_size_mp_var.get()),
            "enable_pnginfo": bool(self._enable_pnginfo_var.get()),
            "save_txt": bool(self._save_txt_var.get()),
            "add_model_name_to_info": bool(self._add_model_name_var.get()),
            "add_model_hash_to_info": bool(self._add_model_hash_var.get()),
            "add_vae_name_to_info": bool(self._add_vae_name_var.get()),
            "add_vae_hash_to_info": bool(self._add_vae_hash_var.get()),
            "show_progressbar": bool(self._show_progressbar_var.get()),
            "live_previews_enable": bool(self._live_previews_enable_var.get()),
            "show_progress_every_n_steps": int(self._show_progress_every_n_steps_var.get()),
            "live_preview_refresh_period": float(self._live_preview_refresh_period_var.get()),
            "interrupt_after_current": bool(self._interrupt_after_current_var.get()),
            "memmon_poll_rate": float(self._memmon_poll_rate_var.get()),
            "enable_upscale_progressbar": bool(self._enable_upscale_progressbar_var.get()),
            "samples_log_stdout": bool(self._samples_log_stdout_var.get()),
        }

        try:
            self.client.update_options(updates)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Engine Settings", f"Failed to apply settings: {exc}")
            return

        messagebox.showinfo("Engine Settings", "Settings applied successfully.")
        self.destroy()
