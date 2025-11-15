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
from typing import Callable, Optional, Protocol
import threading
import time

from src.gui.main_window_v2 import MainWindow


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

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled


class PipelineRunner(Protocol):
    """
    Protocol for something that can run the pipeline.

    Implementations should:
    - Honor CancelToken for cooperative cancellation.
    - Use log_fn to append log messages.
    """

    def run(
        self,
        config: RunConfig,
        cancel_token: CancelToken,
        log_fn: Callable[[str], None],
    ) -> None:
        ...


class DummyPipelineRunner:
    """
    Default stub runner used when no real pipeline_runner is supplied.

    It just logs a couple of messages and respects CancelToken.
    """

    def run(
        self,
        config: RunConfig,
        cancel_token: CancelToken,
        log_fn: Callable[[str], None],
    ) -> None:
        log_fn("[pipeline] DummyPipelineRunner starting (stub).")
        for i in range(3):
            if cancel_token.is_cancelled():
                log_fn("[pipeline] Cancel detected, aborting (stub).")
                return
            log_fn(f"[pipeline] Working... step {i + 1}/3 (stub).")
            time.sleep(0.05)
        log_fn("[pipeline] DummyPipelineRunner finished (stub).")


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
    ) -> None:
        self.main_window = main_window
        self.state = AppState()
        self.threaded = threaded

        self.pipeline_runner: PipelineRunner = pipeline_runner or DummyPipelineRunner()
        self._cancel_token: Optional[CancelToken] = None
        self._worker_thread: Optional[threading.Thread] = None

        # Let the GUI wire its callbacks to us
        self._attach_to_gui()

        # Initial status
        self._update_status("Idle")

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

        self._append_log("[controller] Run clicked – gathering config (stub).")
        self._cancel_token = CancelToken()
        self._set_lifecycle(LifecycleState.RUNNING)

        config = self.state.current_config

        if self.threaded:
            self._worker_thread = threading.Thread(
                target=self._run_pipeline_thread, args=(config, self._cancel_token), daemon=True
            )
            self._worker_thread.start()
        else:
            # Synchronous run (for tests)
            self._run_pipeline_thread(config, self._cancel_token)

    def _run_pipeline_thread(self, config: RunConfig, cancel_token: CancelToken) -> None:
        try:
            self._append_log_threadsafe("[controller] Starting pipeline (stub runner).")
            self.pipeline_runner.run(config, cancel_token, self._append_log_threadsafe)

            if cancel_token.is_cancelled():
                self._append_log_threadsafe("[controller] Pipeline ended due to cancel (stub).")
            else:
                self._append_log_threadsafe("[controller] Pipeline completed successfully (stub).")

            self._set_lifecycle_threadsafe(LifecycleState.IDLE)
        except Exception as exc:  # noqa: BLE001
            self._append_log_threadsafe(f"[controller] Pipeline error: {exc!r}")
            self._set_lifecycle_threadsafe(LifecycleState.ERROR, error=str(exc))

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

        if not self.threaded:
            # In synchronous mode, worker has already finished or is in-process;
            # for the stub we just go to IDLE here.
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
        pack_name = lb.get(index)
        self.on_pack_selected(pack_name)

    def on_pack_selected(self, pack_name: str) -> None:
        self._append_log(f"[controller] Pack selected: {pack_name}")
        # TODO: map pack name to file path and load metadata.

    def on_load_pack(self) -> None:
        self._append_log("[controller] Load Pack clicked (stub).")
        # TODO: open file dialog or load selected pack.

    def on_edit_pack(self) -> None:
        self._append_log("[controller] Edit Pack clicked (stub).")
        # TODO: open Advanced Prompt Editor pre-populated with pack contents.

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