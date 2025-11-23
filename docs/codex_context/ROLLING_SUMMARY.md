# ROLLING_SUMMARY

> Short, cumulative summary of major changes.
> Keep this file brief: aim for bullet points, not essays.

---

## 2025-11-22 (v1 bootstrap)

- Established `docs/codex_context/` as the single source of truth for AI assistants.
- Defined v2 architecture: GUI  controller  pipeline  api  learning.
- Formalized pipeline rules (stages, adetailer as explicit stage, upscale invariants).
- Summarized Learning v2: builder + JSONL writer + execution runner/controller.

## 2025-11-22 (queue persistence)

- Added JobHistoryStore (JSONL) to persist queue submissions and lifecycle changes.
- Added JobHistoryService so controllers/GUI can read active + historical job view models.
- Queue now records lifecycle transitions to history without changing scheduling semantics.

## 2025-11-22 (GUI job history)

- Added a read-only GUI V2 Job History & Active Queue panel powered by JobHistoryService.
- Integrated the panel into AppLayoutV2 without altering existing prompt/pipeline flows.
- New GUI tests cover rendering, empty states, and refresh wiring via a fake service.

## 2025-11-22 (GUI job actions)

- Added Cancel/Retry controls to the Jobs/Queue panel, wired through JobHistoryService and queue controller APIs.
- Controller-side job actions validate status (cancel queued/running; retry completed/failed/cancelled) and submit via existing queue pathways.
- GUI tests verify action enablement and controller invocation; docs note controller-only job action flow.

## 2025-11-22 (Cluster worker registry)

- Defined WorkerDescriptor/WorkerStatus and an in-memory WorkerRegistry with a default local worker.
- Jobs and job history now carry an optional worker_id to prepare for worker-aware scheduling.
- Added ClusterController facade plus tests for registry/worker lifecycle; no change to single-node behavior yet.

## 2025-11-22 (Queue-backed run integration)

- Completed the **queue-backed execution path** by wiring `QueueExecutionController` into `PipelineController` with a `queue_execution_enabled` feature flag, enabling Run/Stop to operate on queued jobs when enabled.
- Added job status → controller lifecycle mapping (QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED), ensuring that queued runs drive the same lifecycle states and GUI updates as direct runs.
- Expanded controller and GUI V2 tests to validate queue-mode toggling, job-id tracking, and cancellation, without regressing default direct-execution behavior.

---

## 2025-11-22 (Assembler enforcement)

- `PipelineController.start_pipeline` now builds `PipelineConfig` immediately through `PipelineConfigAssembler`, eliminating the legacy `pipeline_func` shortcut and submitting the assembled config to queue/direct runners.
- State-driven overrides plus learning/randomizer metadata are extracted (when present) before assembly so tests can monkeypatch the assembler and observe calls.
- Architecture/Rule docs highlight the assembler as the required entry point for production runs.

---

## 2025-11-22 (Pipeline command bar)

> **PR-#48-GUI-V2-CommandBar-RunStopQueue-001** – Introduced a dedicated PipelineCommandBarV2 widget to host Run, Stop, and Queue mode controls inside PipelinePanelV2. StableNewGUI still exposes `run_button` for tests, but the primary pipeline actions are now grouped into a single command bar, aligning with the GUI V2 layout plan and button-placement guidance. Queue mode toggle is surfaced via the command bar using existing app_config/controller plumbing; no pipeline or controller semantics changed. New GUI V2 tests cover command bar existence and queue toggle behavior.

---

## 2025-11-22 (Advanced prompt editor overlay)

> **PR-#49-GUI-V2-AdvancedPromptEditor-001** – Added an AdvancedPromptEditorV2 widget and integrated it with the GUI V2 pipeline panel so users can edit prompts in a larger, focused text area. Opening the editor pre-fills from the current prompt input; applying changes feeds updated text back into the main pipeline prompt field(s) without changing pipeline or controller behavior. New GUI V2 tests cover editor callback behavior and prompt roundtrip between the pipeline panel and the advanced editor.

---

## How To Update

After each major PR or refactor, add 3-6 bullets:
- What changed
- Which modules were touched
- Any new invariants or rules

Keep old snapshots in `docs/codex_context/ARCHIVE/` when this file grows too large.
