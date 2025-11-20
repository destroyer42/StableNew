"""
StableNew - App Controller (Skeleton + CancelToken + Worker Thread Stub)

This controller is designed to work with the new GUI skeleton
in src/gui/main_window_v2.py and the Architecture_v2 design.

It provides:
- Lifecycle state management (IDLE, RUNNING, STOPPING, ERROR).
- Methods for GUI callbacks (run/stop/preview/etc.).
- A CancelToken + worker-thread stub for future pipeline integration.
- A 'threaded' mode for real runs and a synchronous mode for tests.

Real pipeline execution, WebUI client integration, and logging details
will be wired in later via a PipelineRunner abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional
import threading

from src.api.client import SDWebUIClient
from src.gui.main_window_v2 import MainWindow
from src.pipeline.pipeline_runner import PipelineConfig, PipelineRunner
from src.utils import StructuredLogger
from src.utils.file_io import read_prompt_pack
from src.utils.prompt_packs import PromptPackInfo, discover_packs


class LifecycleState(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()
    ERROR = auto()


@dataclass
class RunConfig:
    """
    Minimal placeholder for the full run configuration.

    In a real implementation this will be built from:
    - presets/ JSON
    - GUI state (model, sampler, resolution, randomization, matrix)
    - prompt pack selection
    """
    preset_name: str = ""
    model_name: str = ""
    vae_name: str = ""
    sampler_name: str = ""
    scheduler_name: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.5
    randomization_enabled: bool = False
    # Future fields:
    # matrix_config, adetailer_config, video_config, etc.


@dataclass
class AppState:
    lifecycle: LifecycleState = LifecycleState.IDLE
    last_error: Optional[str] = None
    current_config: RunConfig = field(default_factory=RunConfig)


class CancelToken:
    """
    Simple cancellable flag for cooperative cancellation of the pipeline.

    A real implementation can grow to include thread-safe semantics if needed.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._lock = threading.Lock()
        self._needs_stop_to_finish = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def require_stop_to_finish(self) -> None:
        """Signal that caller expects an explicit stop before finishing."""
        with self._lock:
            self._needs_stop_to_finish = True

    def clear_stop_requirement(self) -> None:
        with self._lock:
            self._needs_stop_to_finish = False

    def needs_stop_to_finish(self) -> bool:
        with self._lock:
            return self._needs_stop_to_finish


class AppController:
    """
    Orchestrates GUI events and (eventually) pipeline execution.

    Responsibilities:
    - Maintain lifecycle state (IDLE/RUNNING/STOPPING/ERROR).
    - Bridge GUI interactions to the pipeline, config, and randomizer.
    - Provide high-level methods for GUI callbacks.

    'threaded' controls whether runs happen in a worker thread (True, default)
    or synchronously (False, ideal for tests).
    """

    def __init__(
        self,
        main_window: MainWindow,
        pipeline_runner: Optional[PipelineRunner] = None,
        threaded: bool = True,
        packs_dir: Path | str | None = None,
        api_client: SDWebUIClient | None = None,
        structured_logger: StructuredLogger | None = None,
    ) -> None:
        self.main_window = main_window
        self.state = AppState()
        self.threaded = threaded

        if pipeline_runner is not None:
            self.pipeline_runner = pipeline_runner
        else:
            self._api_client = api_client or SDWebUIClient()
            self._structured_logger = structured_logger or StructuredLogger()
            self.pipeline_runner = PipelineRunner(self._api_client, self._structured_logger)
        self._cancel_token: Optional[CancelToken] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._packs_dir = Path(packs_dir) if packs_dir is not None else Path("packs")
        self.packs: list[PromptPackInfo] = []
        self._selected_pack_index: Optional[int] = None

        # Let the GUI wire its callbacks to us
        self._attach_to_gui()
        if hasattr(self.main_window, "connect_controller"):
            self.main_window.connect_controller(self)

        # Initial status
        self._update_status("Idle")
        self.load_packs()

    # ------------------------------------------------------------------
    # GUI Wiring
    # ------------------------------------------------------------------

    def _attach_to_gui(self) -> None:
        header = self.main_window.header_zone
        left = self.main_window.left_zone
        bottom = self.main_window.bottom_zone

        # Header events
        header.run_button.configure(command=self.on_run_clicked)
        header.stop_button.configure(command=self.on_stop_clicked)
        header.preview_button.configure(command=self.on_preview_clicked)
        header.settings_button.configure(command=self.on_open_settings)
        header.help_button.configure(command=self.on_help_clicked)

        # Left zone events
        left.load_pack_button.configure(command=self.on_load_pack)
        left.edit_pack_button.configure(command=self.on_edit_pack)
        left.packs_list.bind("<<ListboxSelect>>", self._on_pack_list_select)
        left.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_combo_select)

        # Initial API status (placeholder)
        bottom.api_status_label.configure(text="API: Unknown")

    # ------------------------------------------------------------------
    # Internal helpers (state & logging)
    # ------------------------------------------------------------------

    def _set_lifecycle(self, new_state: LifecycleState, error: Optional[str] = None) -> None:
        self.state.lifecycle = new_state
        self.state.last_error = error

        if new_state == LifecycleState.IDLE:
            self._update_status("Idle")
        elif new_state == LifecycleState.RUNNING:
            self._update_status("Running...")
        elif new_state == LifecycleState.STOPPING:
            self._update_status("Stopping...")
        elif new_state == LifecycleState.ERROR:
            self._update_status(f"Error: {error or 'Unknown error'}")

    def _set_lifecycle_threadsafe(
        self, new_state: LifecycleState, error: Optional[str] = None
    ) -> None:
        """
        Schedule lifecycle change on the Tk main thread if threaded.
        For tests (threaded=False), apply immediately.
        """
        if not self.threaded:
            self._set_lifecycle(new_state, error)
            return

        self.main_window.after(0, lambda: self._set_lifecycle(new_state, error))

    def _update_status(self, text: str) -> None:
        self.main_window.bottom_zone.status_label.configure(text=f"Status: {text}")

    def _append_log(self, text: str) -> None:
        log_widget = self.main_window.bottom_zone.log_text
        log_widget.insert("end", text + "\n")
        log_widget.see("end")

    def _append_log_threadsafe(self, text: str) -> None:
        """
        Schedule a log append on the Tk main thread if threaded.
        For tests (threaded=False), apply immediately.
        """
        if not self.threaded:
            self._append_log(text)
            return

        self.main_window.after(0, lambda: self._append_log(text))

    # ------------------------------------------------------------------
    # Run / Stop / Preview
    # ------------------------------------------------------------------

    def on_run_clicked(self) -> None:
        """
        Called when the user presses RUN.

        In threaded mode:
        - Spawns a worker thread to run the pipeline with a CancelToken.

        In synchronous mode (threaded=False, useful for tests):
        - Runs the pipeline stub synchronously.
        """
        if self.state.lifecycle == LifecycleState.RUNNING:
            self._append_log("[controller] Run requested, but pipeline is already running.")
            return

        # If there was a previous worker, ensure it is not still alive (best-effort)
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._append_log("[controller] Previous worker still running; refusing new run.")
            return

        self._append_log("[controller] Run clicked - gathering config.")
        self._cancel_token = CancelToken()
        self._set_lifecycle(LifecycleState.RUNNING)

        if self.threaded:
            self._worker_thread = threading.Thread(
                target=self._run_pipeline_thread,
                args=(self._cancel_token,),
                daemon=True,
            )
            self._worker_thread.start()
        else:
            # Synchronous run (for tests)
            self._run_pipeline_thread(self._cancel_token)

    def _run_pipeline_thread(self, cancel_token: CancelToken) -> None:
        try:
            pipeline_config = self._build_pipeline_config()
            self._append_log_threadsafe("[controller] Starting pipeline execution.")
            self.pipeline_runner.run(pipeline_config, cancel_token, self._append_log_threadsafe)

            if cancel_token.is_cancelled():
                self._append_log_threadsafe("[controller] Pipeline ended due to cancel (stub).")
            else:
                self._append_log_threadsafe("[controller] Pipeline completed successfully.")

            if cancel_token.needs_stop_to_finish() and not cancel_token.is_cancelled():
                self._append_log_threadsafe(
                    "[controller] Pipeline awaiting explicit stop to finish (stub)."
                )
                return

            cancel_token.clear_stop_requirement()
            self._set_lifecycle_threadsafe(LifecycleState.IDLE)
        except Exception as exc:  # noqa: BLE001
            self._append_log_threadsafe(f"[controller] Pipeline error: {exc!r}")
            self._set_lifecycle_threadsafe(LifecycleState.ERROR, error=str(exc))
            cancel_token.clear_stop_requirement()

    def on_stop_clicked(self) -> None:
        """
        Called when the user presses STOP.

        Sets lifecycle to STOPPING, triggers CancelToken, and lets the
        pipeline exit cooperatively. In synchronous mode, we immediately
        return to IDLE after marking cancel.
        """
        if self.state.lifecycle != LifecycleState.RUNNING:
            self._append_log("[controller] Stop requested, but pipeline is not running.")
            return

        self._append_log("[controller] Stop requested.")
        self._set_lifecycle(LifecycleState.STOPPING)

        if self._cancel_token is not None:
            self._cancel_token.cancel()
            self._cancel_token.clear_stop_requirement()

        worker_alive = self._worker_thread is not None and self._worker_thread.is_alive()
        if not worker_alive:
            self._set_lifecycle(LifecycleState.IDLE)
        # In threaded mode, lifecycle will transition to IDLE in _run_pipeline_thread
        # once the worker exits.

    def on_preview_clicked(self) -> None:
        """
        Called when the user presses Preview Payload.

        In real code, this would run randomizer/matrix to generate a preview
        payload without calling WebUI. For now, we just log a stub message.
        """
        self._append_log("[controller] Preview clicked (stub).")
        # TODO: gather config, pack, randomization, matrix → build preview payload.

    # ------------------------------------------------------------------
    # Settings / Help
    # ------------------------------------------------------------------

    def on_open_settings(self) -> None:
        self._append_log("[controller] Settings clicked (stub).")
        # TODO: open a settings dialog or config editor.

    def on_help_clicked(self) -> None:
        self._append_log("[controller] Help clicked (stub).")
        # TODO: open docs/README in browser or show help overlay.

    # ------------------------------------------------------------------
    # Packs / Presets
    # ------------------------------------------------------------------

    def _on_preset_combo_select(self, event) -> None:  # type: ignore[override]
        combo = self.main_window.left_zone.preset_combo
        new_preset = combo.get()
        self.on_preset_selected(new_preset)

    def on_preset_selected(self, preset_name: str) -> None:
        self._append_log(f"[controller] Preset selected: {preset_name}")
        self.state.current_config.preset_name = preset_name
        # TODO: load preset JSON, update GUI fields, etc.

    def _on_pack_list_select(self, event) -> None:  # type: ignore[override]
        lb = self.main_window.left_zone.packs_list
        if not lb.curselection():
            return
        index = lb.curselection()[0]
        self.on_pack_selected(int(index))

    def load_packs(self) -> None:
        """Discover packs and push them to the GUI."""
        self.packs = discover_packs(self._packs_dir)
        pack_names = [pack.name for pack in self.packs]
        self.main_window.update_pack_list(pack_names)
        self._selected_pack_index = None
        self._append_log(f"[controller] Loaded {len(pack_names)} pack(s).")

    def on_pack_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.packs):
            self._append_log("[controller] Pack selection out of range.")
            return
        self._selected_pack_index = index
        pack = self.packs[index]
        self._append_log(f"[controller] Pack selected: {pack.name}")

    def _get_selected_pack(self) -> Optional[PromptPackInfo]:
        if self._selected_pack_index is None:
            return None
        if self._selected_pack_index < 0 or self._selected_pack_index >= len(self.packs):
            return None
        return self.packs[self._selected_pack_index]

    def on_load_pack(self) -> None:
        pack = self._get_selected_pack()
        if pack is None:
            self._append_log("[controller] Load Pack requested, but no pack is selected.")
            return
        self._append_log(f"[controller] Load Pack -> {pack.name} ({pack.path})")

    def on_edit_pack(self) -> None:
        pack = self._get_selected_pack()
        if pack is None:
            self._append_log("[controller] Edit Pack requested, but no pack is selected.")
            return
        self._append_log(f"[controller] Edit Pack -> {pack.path}")

    # ------------------------------------------------------------------
    # Config state helpers
    # ------------------------------------------------------------------

    def get_available_models(self) -> list[str]:
        return ["StableNew-XL", "SDXL-Lightning", "SD15-Legacy"]

    def get_available_samplers(self) -> list[str]:
        return ["Euler", "Euler a", "DPM++ 2M", "DPM++ SDE Karras"]

    def get_current_config(self) -> dict[str, float | int | str]:
        cfg = self.state.current_config
        return {
            "model": cfg.model_name or self.get_available_models()[0],
            "sampler": cfg.sampler_name or self.get_available_samplers()[0],
            "width": cfg.width,
            "height": cfg.height,
            "steps": cfg.steps,
            "cfg_scale": cfg.cfg_scale,
        }

    def update_config(self, **kwargs: float | int | str) -> None:
        mapping = {
            "model": "model_name",
            "sampler": "sampler_name",
            "width": "width",
            "height": "height",
            "steps": "steps",
            "cfg_scale": "cfg_scale",
        }
        cfg = self.state.current_config

        for field, value in kwargs.items():
            attr = mapping.get(field)
            if not attr:
                continue

            if attr in {"width", "height", "steps"}:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    continue
            elif attr == "cfg_scale":
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue
            else:
                value = str(value)

            setattr(cfg, attr, value)
            self._append_log(f"[controller] Config updated: {field}={value}")

    def _build_pipeline_config(self) -> PipelineConfig:
        current = self.get_current_config()
        pack = self._get_selected_pack()
        prompt = self._resolve_prompt_from_pack(pack) or current.get("prompt", "")
        if not prompt:
            prompt = (pack.name if pack else current.get("preset_name")) or "StableNew GUI Run"

        return PipelineConfig(
            prompt=prompt,
            model=str(current["model"]),
            sampler=str(current["sampler"]),
            width=int(current["width"]),
            height=int(current["height"]),
            steps=int(current["steps"]),
            cfg_scale=float(current["cfg_scale"]),
            pack_name=pack.name if pack else None,
            preset_name=self.state.current_config.preset_name or None,
        )

    def _resolve_prompt_from_pack(self, pack: PromptPackInfo | None) -> str:
        if not pack:
            return ""
        try:
            prompts = read_prompt_pack(pack.path)
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"[controller] Failed to read pack {pack.name}: {exc}")
            return ""
        if not prompts:
            return ""
        first = prompts[0]
        return str(first.get("positive") or "")

    # ------------------------------------------------------------------
    # Config Changes (model, sampler, resolution, randomization, matrix)
    # ------------------------------------------------------------------

    def on_model_selected(self, model_name: str) -> None:
        self._append_log(f"[controller] Model selected: {model_name}")
        self.state.current_config.model_name = model_name

    def on_vae_selected(self, vae_name: str) -> None:
        self._append_log(f"[controller] VAE selected: {vae_name}")
        self.state.current_config.vae_name = vae_name

    def on_sampler_selected(self, sampler_name: str) -> None:
        self._append_log(f"[controller] Sampler selected: {sampler_name}")
        self.state.current_config.sampler_name = sampler_name

    def on_scheduler_selected(self, scheduler_name: str) -> None:
        self._append_log(f"[controller] Scheduler selected: {scheduler_name}")
        self.state.current_config.scheduler_name = scheduler_name

    def on_resolution_changed(self, width: int, height: int) -> None:
        self._append_log(f"[controller] Resolution changed to {width}x{height}")
        self.state.current_config.width = width
        self.state.current_config.height = height

    def on_randomization_toggled(self, enabled: bool) -> None:
        self._append_log(f"[controller] Randomization toggled: {enabled}")
        self.state.current_config.randomization_enabled = enabled

    def on_matrix_base_prompt_changed(self, text: str) -> None:
        self._append_log("[controller] Matrix base prompt changed (stub).")
        # TODO: store in matrix config.

    def on_matrix_slots_changed(self) -> None:
        self._append_log("[controller] Matrix slots changed (stub).")
        # TODO: store in matrix config.

    # ------------------------------------------------------------------
    # Preview / Right Zone
    # ------------------------------------------------------------------

    def on_request_preview_refresh(self) -> None:
        self._append_log("[controller] Preview refresh requested (stub).")
        # TODO: set preview_label image or text based on latest run or preview.


# Convenience entrypoint for testing the skeleton standalone
if __name__ == "__main__":
    import tkinter as tk
    from src.gui.main_window_v2 import StableNewApp

    app = StableNewApp()
    controller = AppController(app.main_window, threaded=True)
    app.mainloop()
