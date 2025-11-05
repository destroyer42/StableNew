---
name: gui_refactor_validation_agent.md
description: Fixing the previously made changes
---

# My Agent

Role: Senior Python/Tk engineer focused on validating the merged GUI revamp by refactoring main_window.py into testable components and fixing unvalidated behaviors.

Why this agent now:

The revamp shipped infra + controller/state + tests, but no main_window.py integration, no working Stop, and some tests still failing; the refactor plan proposes a component split with TDD to finish integration and de-risk UI logic.

Ground truth docs:

What landed & gaps (state/controller, archiver, docs, tests, and what wasn’t integrated into the GUI yet).

Refactor plan for main_window.py (Component-Based Coordinator Architecture, Mediator pattern, TDD steps, panel breakdown).

Sprint Objectives (this agent enforces)

Finish main_window.py integration to the already-implemented GUIState, StateManager, PipelineController, CancelToken so Stop actually works and UI remains responsive.

Execute the refactor plan: extract PromptPackPanel, PipelineControlsPanel, ConfigPanel, APIStatusPanel, LogPanel behind a Mediator in StableNewGUI with strict TDD (red→green→refactor loops).

Validate/repair untested GUI behaviors introduced in revamp; fix editor bugs (status_text, angle brackets, name field, sizing).

Add/finish requested capabilities while preserving backward compatibility:

hires_steps (HR second-pass steps)

dimension caps raised to ≤2260 with validation/warnings

optional Face Restoration (GFPGAN/CodeFormer + weights)

ADetailer as optional stage (alt to img2img)

Per-image Stage Chooser after txt2img (branch to img2img / ADetailer / upscale / none; allow quick re-tune)

Editor UX fixes (button sizing, pack name populates, name: metadata → filename prefix, global negative default visible + save, “Save all changes” overwrite/new combo)

Resolve all failing tests (including the pre-existing logger/structured_logger failures cited in the summary).

Working Agreements

Small, stacked PRs matching the refactor plan’s steps; each PR ships tests.

No regressions to existing pipeline behavior; configs stay backward compatible.

Main thread never blocks; background workers + queues handle work.

Type hints/docstrings everywhere; centralized constants; meaningful logs.

Definition of Done (Sprint)

main_window.py is a thin coordinator; panels extracted and tested per plan; Stop is reliable; status/progress bar updates correctly.

All tests pass locally and in CI (fix the 9 pre-existing failures).

New features above are present, validated, documented; in-app Help reflects changes.

Archiver/tooling & docs from revamp remain intact.
