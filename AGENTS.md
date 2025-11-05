# StableNew — AGENTS

## Goals
- Maintain a modern Tk/Ttk GUI for Stable Diffusion automation (txt2img → img2img → upscale → video).
- Keep **Tk main thread non-blocking**; heavy work in workers/subprocesses; **cooperative cancel tokens** everywhere.
- Enforce **TDD**: write/extend tests first; keep PRs small and reviewable.

## Runbook
- `pre-commit run --all-files`
- `pytest --cov=src --cov-report=term-missing -q`
- GUI-only: `pytest tests\gui -q`
- Config tests: `pytest tests\config -q`

## Guardrails
- ❌ Never `join()` worker threads from GUI/tests; **poll controller events** with bounded waits.
- Headless GUI tests only (Xvfb in CI); skip gracefully if Tcl/Tk is unavailable.
- Backward-compatible configs; preserve output manifests per run.
- Keep acceptance criteria and DoD in each issue/PR; use repo PR template.

## High-value Paths
- `src/gui/**` (panels; mediator in `main_window.py`)
- `src/pipeline/executor.py` (stage orchestration; `run_full_pipeline`, `run_upscale`)
- `utils/file_io.py` (base64 + atomic writes)
- `tests/**` (gui/, config/, regressions/)

## Branch & PR Policy
- Branch from `postGemini`.
- PR route: `feature/*` → `postGemini` → `main` (protected).
- PR must pass: ruff, black, mypy, pytest (headless). Include screenshots for visible UI changes.

## Definition of Done (applies to all PRs)
- ✅ CI green (ruff/black/mypy/pytest).
- ✅ No Tk main-thread blocking; cancel honored in new code paths.
- ✅ Tests added/updated for changed behavior.
- ✅ README/ARCHITECTURE updated as needed; configs remain backward compatible.

## Reusable Prompts
- `@s3b_progress_eta` → `./.codex-prompts/s3b_progress_eta.txt`
- `@cancel_token_upscale` → `./.codex-prompts/cancel_token_upscale.txt`
- `@config_passthrough_tests` → `./.codex-prompts/config_passthrough_tests.txt`


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

