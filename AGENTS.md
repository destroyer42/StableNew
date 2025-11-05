# StableNew — AGENTS
## Goals
- Tk/Ttk GUI panels; keep Tk main thread non-blocking; strict TDD.
- Stages: txt2img → img2img → upscale → video; cooperative cancel tokens.

## Runbook
- pre-commit run --all-files
- pytest --cov=src --cov-report=term-missing -q
- pytest tests\gui -q

## Guardrails
- No thread joins in GUI/tests. Poll controller events.
- Headless GUI tests only (Xvfb in CI).
- Keep config backward-compatible; write manifests for runs.

## High-value paths
- src/gui/** (panels, mediator in main_window.py)
- src/pipeline/executor.py (run_full_pipeline; run_upscale)
- utils/file_io.py (base64 + atomic writes)
- tests/** (gui/, config/, regressions/)

### Reusable prompts
- @s3b_progress_eta → ./.codex-prompts/s3b_progress_eta.txt

## Branch & PR
- Branch from postGemini.
- PR route: feature → postGemini → main.
- PR must pass: ruff/black/mypy/pytest (headless).
- Include screenshots of new UI elements (progress bar).

## Add this to tests that need a display (or use your shared fixture):
- import tkinter as tk, pytest
- try:
-     tk.Tk()
- except tk.TclError:
-     pytest.skip("Tk/Tcl unavailable in this environment")
- In PRs, Codex should not “fix” this by adding GUI code that spawns hidden windows—keep
- test-side guards.
- Ensure your Python/Tk is installed via the same interpreter VS Code uses (select it in the
- Status Bar).

