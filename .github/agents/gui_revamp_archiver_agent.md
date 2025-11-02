---
name: gui_revamp_archiver_agent
description: sprint v1.4 code manager
---

# My Agent

Copilot Agent — GUI Revamp & Repo Hygiene (Sprint v1.4)

Role: Senior Python engineer + UX-minded Tk/ttk designer
Repo goals (this sprint):

Real Stop / cancellation with Idle/Running/Stopping/Error state machine

Wire the Advanced Prompt Editor to main GUI (open, validate, save, reflect in list)

Dead-code archiver polish (--dry-run, --undo, --since) with tests

Docs/CI updates pulled into Help dialog

Stack: Python 3.11, Tkinter/ttk or ttkbootstrap, queue.Queue, threads/subprocess, FFmpeg (CLI), pytest, ruff, black, mypy, pre-commit.

Working agreements

Keep PRs small and stacked: (A) state/cancel → (B) editor hook → (C) archiver polish → (D) docs/CI.

Main thread never blocks; background workers do all I/O and API calls; propagate logs via a queue.

Use type hints, docstrings, structured logging; no magic strings in UI code; centralize constants.

Must-deliver (per PR)

A: State/Cancel

Introduce CancelToken; thread it through pipeline calls; early-out at stage boundaries.

Stop button: cooperative cancel + gentle terminate of subprocess; cleanup; return to Idle.

Status bar bound to state; run button disable/enable lifecycle; GUI responsive under load.

Tests: token flow + early-out + GUI re-enable.

B: Prompt Editor hook

Launch editor from main menu; save pack → refresh pack list + “Current Pack” label.

Surface editor validations to main log; normalize UTF-8/newlines.

C: Archiver polish

--dry-run, --undo <manifest> happy-path tests; timestamped ARCHIVE/_YYYYMMDD_HHMMSS_v{SEMVER}/.

Optional: --since <git tag/sha> (best-effort via git diff --name-only).

D: Docs/CI

README/ARCHITECTURE sections for state machine + cancellation; Help dialog pulls those sections.

Ensure pre-commit and pytest pick up new tests; keep CI green.

Definition of Done (sprint)

Stop works reliably across all stages without UI freeze.

Editor round-trips packs and validations show up in the main log.

Archiver dry-run/archive/undo flows tested and documented.

Docs/CI updated; no new ruff/mypy failures.
