# StableNew — GitHub Copilot Instructions (merged 2025-11-04)

> **Context:** Stable Diffusion WebUI automation (txt2img → img2img → upscale → video) with Python 3.11, Tk/Ttk GUI, FFmpeg, pytest, ruff, black, mypy, and pre-commit. This file guides GitHub Copilot coding agent, Copilot Chat, and human contributors for **StableNew**.

 ### AI-Assisted Development

  StableNew uses GitHub Copilot / Codex + ChatGPT under a documented process:

  - [Codex Integration SOP](.github/CODEX_SOP.md)
  - [Codex Autopilot Workflow v1](docs/dev/Codex_Autopilot_Workflow_v1.md)

  Please read these before using AI tools to modify this repo.

## 1) Branching & Release Flow
- **main**: release-only (protected). No direct pushes.
- **postGemini**: integration branch for GUI + controller work.
- **Feature branches**: create per task, e.g. `feature/gui-stop-cancel`, `fix/editor-status-text`.
- **PR route**: `feature` → `postGemini` (manual journey tests) → `main` (RC/tag).

## 2) Architecture Guardrails (GUI + Controller)
- GUI is componentized; `main_window.py` is the **mediator**.
  - Panels: `PromptPackPanel`, `PipelineControlsPanel`, `ConfigPanel`, `APIStatusPanel`, `LogPanel`.
  - Panels own their `tk.*Var` state and expose `get_state()/set_state()` or `get_settings()`.
  - Events bubble **up** to mediator; mediator pushes updates **down**.
- Controller is authoritative for lifecycle and the **only** place that joins workers.
  - GUI/tests **must not** join worker threads.
  - Use cooperative cancellation; Tk main thread must remain non‑blocking.
- Pipeline (high level): `txt2img` → (optional) `img2img` → `upscale` → `video`.
  - SD WebUI API readiness is checked before calls; use exponential backoff.
  - Base64 image handling goes through `utils/file_io.py` helpers.
  - Each run writes manifests (JSON) + CSV rollups into time‑stamped `output/run_YYYYMMDD_HHMMSS/...`

## 3) How to Work (Copilot + Humans)
**We use strict TDD and small PRs.**
1. Write/extend tests under `tests/` first (`tests/gui` for panels).
2. Run: `pre-commit run --all-files` then `pytest --cov=src --cov-report=term-missing`.
3. Implement the minimal change to make tests pass.
4. Refactor with tests green. Update docs and changelog.

**Task sizing for Copilot**
- Prefer focused tasks: bug fixes, UI polish, test coverage, docs, config validation, technical debt.
- Avoid broad refactors, cross-repo changes, or domain‑heavy business logic in a single task.
- If a task is ambiguous, add acceptance criteria **before** starting.

**How to assign tasks/prompts**
- Issues double as prompts. Include:
  - What to change (files/paths), acceptance tests, success criteria.
  - Any GUI behaviors (non‑blocking, cancel, log, status text) and validation points.
- In PRs, mention **@copilot** with batched review comments (use “Start a review”), not single comments.

## 4) Build, Test, Lint (local + CI)
```cmd
:: Windows developer quick checks
pre-commit run --all-files
pytest -q
pytest --cov=src --cov-report=term-missing
```
- Linters/formatters: `ruff`, `black`, `mypy` (strict enough to catch regressions).
- GUI tests run **headless** (xvfb in CI). Tests should poll controller state/events rather than join threads.

## 5) Definition of Done (applies to every PR)
- ✅ CI green: ruff, black, mypy, pytest (+ headless GUI lane).
- ✅ No Tk main‑thread blocking; cooperative cancel is honored.
- ✅ Tests added/updated for all new behavior.
- ✅ README/ARCHITECTURE updated; CHANGELOG entry for user‑visible changes.
- ✅ Config backward compatible; manifests preserved.

## 6) PR Template (enforced by Copilot and humans)
Copy lives at `.github/PULL_REQUEST_TEMPLATE.md` and is inlined here for Copilot context:

---
# Summary
Describe what this PR changes and why.

# Linked Issues
- Closes # (list the issues this PR addresses)

# Type of change
- [ ] Feature
- [ ] Bugfix
- [ ] Refactor
- [ ] Docs / CI
- [ ] Tests

# Validation
- [ ] I ran `pre-commit run --all-files` and fixed findings.
- [ ] I ran `pytest -q` and **0 failures** locally.
- [ ] New/changed behavior has tests (unit and/or GUI headless where applicable).
- [ ] No main-thread blocking (Tk); heavy work is in threads/subprocesses with queue callbacks.
- [ ] Cooperative cancel is honored in new/changed paths.

## Test commands used
```
pytest -q
pytest tests/gui -q
pytest tests/editor -q
```

# Screenshots / GIF (if UI changes)
(attach images)

# Docs
- [ ] README/ARCHITECTURE updated where relevant.
- [ ] In-app Help updated (pulled from README sections).

# Risk & Rollback
- Risk level: Low / Medium / High
- Rollback plan: Revert this PR; archived unused files unchanged; config backward compatible.
---

## 7) Repository Structure (high‑value paths for Copilot)
- `src/api/client.py` — SD WebUI communication + readiness checks (backoff).
- `src/pipeline/executor.py` — stage orchestration and error logging.
- `src/pipeline/video.py` — FFmpeg assembly.
- `utils/file_io.py` — base64 helpers and atomic writes.
- `presets/` — hierarchical JSON configs (`txt2img/img2img/upscale/video/api`).
- `packs/` — prompt packs (`.txt` and `.tsv`; `neg:` prefix supported).

## 8) Path‑Specific Instructions (auto‑applied by Copilot)
- **GUI tests** (`tests/gui/**`)
  - Use headless harness, poll controller events (e.g., `lifecycle_event`) and widget state.
  - No `join()` on worker threads; never block Tk.
- **Config tests** (`tests/config/**`)
  - Verify pass‑through of settings to API calls; cover `global_neg` safety list.
- **Editor panel** (`src/gui/editor/**`)
  - Preserve `status_text`, `name:` prefix handling, angle‑brackets, Global Negative, and Save‑All UX.

## 9) Copilot Environment (Actions) — Setup Steps
- We pre‑install dependencies in `copilot-setup-steps.yml` (runs before the agent session).
- Environment secrets/variables (if needed) should be set in the `copilot` environment.
- Larger runners may be configured later; current default is ubuntu‑latest.

## 10) Working Agreements (sequence of small PRs Copilot can follow)
1) Extract/finish panels + mediator wiring.
2) Stop/Cancel: controller cancel token plumbed; non‑blocking logs.
3) Generation params: hires steps, dimensions, face‑restore toggles.
4) ADetailer panel + per‑image decision loop.
5) Editor polish (status_text, name prefix, angle brackets, Global Negative; Save‑All UX).
6) Docs/CI polish.

---
**Appendix A — Quick Prompts Copilot Can Use**
- “Update `PipelineControlsPanel` to honor CancelToken with non‑blocking UI; add tests under `tests/gui/test_cancel.py`.”
- “Add config pass‑through tests to `tests/config/test_preset_passthrough.py` for new `hires_steps` and `face_restore` fields.”
- “Refactor `client.check_api_ready()` to exponential backoff; add unit tests for timeout behavior.”

**Appendix B — Known Non‑Goals for Copilot**
- Cross‑repo refactors, major redesigns, or production‑critical auth/security changes in one PR.
- Tasks lacking acceptance criteria or reproducible steps.
