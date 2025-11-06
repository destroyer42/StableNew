# StableNew — AI Coding Agent Instructions

> **Context:** Stable Diffusion WebUI automation pipeline (txt2img → img2img/ADetailer → upscale → video) with Python 3.11, Tkinter GUI, FFmpeg, pytest. Strict TDD workflow with pre-commit hooks (ruff, black, mypy).

## 1) Project Architecture

**Pipeline Flow:** `txt2img` → **stage chooser** → (img2img | ADetailer) → upscale → video
- Each stage optional via config flags (`img2img_enabled`, `upscale_enabled`) or per-image modal selection
- Output to timestamped dirs: `output/run_YYYYMMDD_HHMMSS/{txt2img,img2img,upscaled,video,manifests}/`
- All metadata tracked in JSON manifests + CSV rollups for reproducibility

**GUI Architecture (MVC + Mediator Pattern):**
- `src/gui/main_window.py` is the **mediator** - coordinates all panels
- Panels (`PromptPackPanel`, `PipelineControlsPanel`, `ConfigPanel`, `APIStatusPanel`, `LogPanel`) own their `tk.*Var` state
- Data flows: Events bubble **up** to mediator → mediator pushes state **down** to panels
- Each panel exposes `get_state()/set_state()` or `get_settings()` - never access vars directly from other components

**Critical Threading Rules:**
- `PipelineController` (`src/gui/controller.py`) is the **only** place that joins worker threads
- GUI and tests **must never** call `.join()` on threads - use event polling instead
- All heavy work (API calls, FFmpeg) runs in threads/subprocesses with queue-based callbacks
- Tk main loop must **never** block - use `root.after()` for periodic checks

## 2) Cooperative Cancellation Pattern

**Cancel Token Usage** (`src/gui/state.py::CancelToken`):
```python
# In pipeline stages, check at safe points:
if cancel_token and cancel_token.is_cancelled():
    logger.info("Operation cancelled")
    return None

# Controller resets token before each run:
self.cancel_token.reset()
```
- Cancellation is **cooperative** - check between stages, after API calls, not during tight loops
- Never abruptly kill threads - allow cleanup (close connections, delete temp files, terminate FFmpeg)

## 3) Configuration Integrity (CRITICAL)

**When adding/modifying config parameters:**
1. Update `src/utils/config.py::get_default_config()` with new field
2. Add GUI controls in relevant panel (`src/gui/config_panel.py` or component)
3. Update `src/pipeline/executor.py` to use the parameter in API payloads
4. **MUST** update `tests/test_config_passthrough.py`:
   - Add parameter to `EXPECTED_TXT2IMG_PARAMS`, `EXPECTED_IMG2IMG_PARAMS`, or `EXPECTED_UPSCALE_PARAMS`
5. Run validation: `pytest tests/test_config_passthrough.py`
6. Ensure 90-100% pass-through accuracy before merging

**Why:** Silent config drift causes unexpected generation results. This test is mandatory.

## 4) API Client Patterns

**Retry/Backoff** (`src/api/client.py::SDWebUIClient`):
- Uses exponential backoff with jitter for resilience
- Configurable via `max_retries`, `backoff_factor`, `max_backoff`, `jitter`
- Example: `backoff_factor=1.0` → delays of 1s, 2s, 4s, 8s (capped at `max_backoff`)
- Jitter prevents thundering herd: adds random 0-`jitter` seconds to each delay

**Readiness Checks:**
- Before pipeline execution, check `/sdapi/v1/sd-models` endpoint
- Fail fast if WebUI not responding - don't waste time on doomed runs
- Discovery: `src/utils/webui_discovery.py::find_webui_api_port()` scans common ports (7860, 7861, 7862)

## 5) File I/O Conventions

**UTF-8 Discipline:**
- All file reads/writes use `encoding="utf-8"` - supports international prompts
- Prompt packs (`.txt`, `.tsv`) can include any Unicode characters
- `name:` prefix in prompts allows custom filenames (also UTF-8 safe)

**Base64 Image Handling** (`src/utils/file_io.py`):
- `load_image_to_base64(path)` - read image → base64 string for API
- `save_image_from_base64(b64_str, path)` - decode API response → PNG/JPG
- Never write raw bytes directly - use these helpers for consistency

**Prompt Pack Parsing:**
- Blank lines separate prompts in `.txt` format
- `neg:` prefix marks negative prompt lines (joined with spaces)
- Embeddings: `<embedding:name>` or `<embedding:name-neg>`
- LoRAs: `<lora:model:0.7>` with float weights

## 6) Testing Strategy (TDD Required)

**Workflow:**
1. Write test **first** under `tests/` (or `tests/gui/` for panels)
2. Run `pre-commit run --all-files` to check style
3. Run `pytest --cov=src --cov-report=term-missing` - aim for 80%+ coverage
4. Implement minimal code to pass test
5. Refactor with tests green

**GUI Test Patterns** (see `.github/instructions/gui-tests.instructions.md`):
- Use `tests/conftest.py::tk_root` fixture (headless-safe)
- Use `tk_pump(duration=0.2)` to process Tk events without blocking
- Poll controller state via `state_manager.current` - **never** join worker threads
- Example: Wait for state transition by checking `state_manager.is_state(GUIState.IDLE)` in loop

**Markers:**
- `@pytest.mark.gui` - requires Tk display (skipped in headless CI)
- `@pytest.mark.integration` - needs external services (SD WebUI API)
- `@pytest.mark.slow` - takes >5s (skip with `-m "not slow"`)

## 7) Development Workflow

**Local Quick Checks:**
```bash
pre-commit run --all-files   # ruff, black, mypy
pytest -q                     # fast run, no coverage
pytest --cov=src --cov-report=term-missing  # full validation
```

**Branching:**
- `main` - release-only (protected)
- `postGemini` - integration branch for GUI/controller work
- Feature branches: `feature/gui-stop-cancel`, `fix/config-passthrough`

**PR Route:** `feature` → `postGemini` (manual journey tests) → `main` (tagged release)

## 8) Task Sizing for AI Agents

**Good Copilot Tasks:**
- Bug fixes with clear reproduction steps
- UI polish (button states, status text, validation messages)
- Test coverage for specific modules
- Config validation and pass-through accuracy
- Documentation updates (README, ARCHITECTURE, inline docs)
- Technical debt cleanup (linting, type hints, deprecation fixes)

**Avoid:**
- Broad refactors spanning multiple subsystems
- Cross-repo changes or external dependency upgrades
- Domain-heavy business logic without context
- Tasks lacking acceptance criteria or reproducible steps

**How to Assign Tasks:**
- Issues = prompts. Include: files/paths, acceptance tests, success criteria
- For GUI changes: specify non-blocking requirements, cancel behavior, log output
- In PR reviews: batch comments (use "Start a review"), mention **@copilot** once

## 9) Definition of Done

Every PR must satisfy:
- ✅ CI green: ruff, black, mypy, pytest (headless GUI tests)
- ✅ No Tk main-thread blocking; cooperative cancel honored
- ✅ Tests added/updated for new behavior
- ✅ README/ARCHITECTURE updated; CHANGELOG entry for user-visible changes
- ✅ Config backward compatible; manifests preserved

## 10) PR Template (enforced)

```markdown
# Summary
Describe what this PR changes and why.

# Linked Issues
- Closes # (list issues)

# Type of change
- [ ] Feature / [ ] Bugfix / [ ] Refactor / [ ] Docs/CI / [ ] Tests

# Validation
- [ ] `pre-commit run --all-files` passed
- [ ] `pytest -q` shows 0 failures
- [ ] New behavior has tests (unit and/or GUI headless)
- [ ] No main-thread blocking (Tk); heavy work in threads/subprocesses
- [ ] Cooperative cancel honored in new paths

## Test commands
pytest -q
pytest tests/gui -q

# Screenshots (if UI changes)
(attach images)

# Docs
- [ ] README/ARCHITECTURE updated
- [ ] In-app Help updated

# Risk & Rollback
- Risk: Low/Medium/High
- Rollback: Revert PR; config backward compatible
```

## 11) Key File Reference

| Path | Purpose |
|------|---------|
| `src/api/client.py` | SD WebUI communication + retry/backoff logic |
| `src/pipeline/executor.py` | Stage orchestration (txt2img/img2img/upscale) |
| `src/pipeline/video.py` | FFmpeg video assembly |
| `src/gui/main_window.py` | GUI mediator - coordinates all panels |
| `src/gui/controller.py` | Pipeline lifecycle - **only** place that joins threads |
| `src/gui/state.py` | State machine + CancelToken for cooperative cancellation |
| `src/utils/config.py` | Config management - **update here when adding params** |
| `src/utils/file_io.py` | Base64 helpers, UTF-8 file I/O |
| `tests/test_config_passthrough.py` | **Mandatory** validation for config changes |
| `tests/gui/conftest.py` | GUI test fixtures (tk_root, tk_pump) |
| `presets/` | JSON config presets (txt2img/img2img/upscale/video/api) |
| `packs/` | Prompt packs (.txt, .tsv with `neg:` prefix support) |

## 12) Quick Copilot Prompts

**Config Changes:**
```
Add `hires_steps` parameter to control second-pass steps independently:
1. Update src/utils/config.py::get_default_config()
2. Add slider to src/gui/config_panel.py
3. Use in src/pipeline/executor.py txt2img payload
4. Update tests/test_config_passthrough.py EXPECTED_TXT2IMG_PARAMS
5. Run pytest tests/test_config_passthrough.py
```

**GUI Panel:**
```
Create ADetailerPanel in src/gui/adetailer_panel.py:
1. Expose get_config() returning dict with adetailer_enabled, adetailer_model
2. Wire to main_window.py mediator
3. Add tests in tests/gui/test_adetailer_panel.py (use tk_root fixture)
4. Ensure non-blocking - no direct thread joins
```

**API Backoff:**
```
Refactor client.check_api_ready() to exponential backoff:
1. Use _calculate_backoff() helper from existing SDWebUIClient
2. Add unit tests for timeout behavior in tests/test_api_client_backoff.py
3. Test with max_retries=3, backoff_factor=1.0, jitter=0.5
```

---


**Last Updated:** 2025-11-06

## 6) PR Template (enforced by Copilot and humans)
Copy lives at `.github/PULL_REQUEST_TEMPLATE.md` and is inlined here for Copilot context:

---
```

---

**Last Updated:** 2025-11-06
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


**Appendix B — Known Non‑Goals for Copilot**
- Cross‑repo refactors, major redesigns, or production‑critical auth/security changes in one PR.
- Tasks lacking acceptance criteria or reproducible steps.
