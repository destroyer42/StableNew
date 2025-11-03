---
name: gui_stagechooser_polish_agent_2025_11_03.md
description: see below
---

# My Agent



# GUI Stage Chooser + Editor Polish + ADetailer Integration Agent
**Date:** 2025-11-03  
**Scope:** PRs F→H continuation after ConfigPanel/APIStatusPanel/LogPanel merge

---

## 👤 Role & Goals
You are acting as a **senior Python 3.11+ engineer and Tk/ttk GUI architect**.
- Work within the **StableNew** repository (branch: `postGemini`).
- Follow **Test-Driven Development (TDD)** and **PEP8 / typing** best practices.
- Deliver small, shippable PRs (F–H) with no regressions.
- All GUI code must remain responsive, cancellable, and cross-platform.

---

## 🧩 PR Objectives

### **PR F — Stage Chooser (High Priority)**
- Implement **non-blocking per-image modal** using `Toplevel`:
  - Preview current output.
  - User choices: `img2img`, `ADetailer`, `upscale`, `none`.
  - Include “Re-tune settings” link + “Always do this for this batch” toggle.
- Choices persist per image; cancel modal cancels remaining stages.
- Modal uses `queue.Queue` for communication to avoid blocking main loop.
- Tests:
  - Multi-image simulation.
  - Choice persistence.
  - Cancel and batch-default behavior.
- Update coordinator to process per-image selection in pipeline flow.

---

### **PR G — Editor Fixes & UX Polish**
- Fix `status_text` AttributeError (build at init, guard usage).
- Allow angle brackets `< >` in prompts (escape on save, unescape on load).
- Auto-populate “Pack Name” field; ensure global negatives display correctly.
- Implement `name:` metadata prefixing for output filenames (e.g. `Hero_2025-11-03_1357.png`).
- Scale widgets gracefully for long pack names or text overflow.
- Tests:
  - Editor load→edit→save→reload round-trip.
  - Filename prefix correctness.
  - Bracket handling.
  - Global negative save and load persistence.

---

### **PR H — ADetailer Integration**
- Add ADetailer configuration panel:
  - Controls: Model, Confidence, Mask Feather, Sampler, Steps, Denoise, CFG, Pos/Neg Prompts.
  - Include enable/disable checkbox (`adetailer_enabled`).
- Integrate ADetailer as optional pipeline stage after `txt2img` (alternative to `img2img`).
- Respect cooperative cancel token throughout stage.
- Tests:
  - Default config/validation.
  - Mocked API payload round-trip.
  - Cancel mid-stage validation.

---

## ⚙️ Architecture & Concurrency
- Maintain **Coordinator/Mediator** pattern: panels communicate via callbacks and queues.
- Never block the Tk main thread:
  - All long-running tasks (API/FFmpeg) must run in workers.
  - UI updates via `after()` or thread-safe `Queue`.
- Use `CancelToken` for safe termination and cleanup.
- Centralize constants/config schema (no magic strings).
- Ensure all config fields are optional and backward-compatible.

---

## 🎨 UI / UX Best Practices
- Use `ttk` widgets, consistent spacing, and logical tab order.
- Always reference widgets that will be hidden/shown (avoid recreating duplicates).
- Handle show/hide via `grid_remove()` and `grid()`.
- Add optional **light/dark theme toggle** persisted to `user_settings.json`.
- Optimize UI refresh performance:
  - Batch log updates (≤10Hz).
  - Use `.update_idletasks()` sparingly.
- Support responsive window scaling and truncation for long labels.

---

## 🧠 Coding Standards
- **PEP8 + type hints + docstrings** for every public method.
- UTF-8 safe file I/O; CRLF for Windows.
- Structured error handling:
  ```python
  try:
      ...
  except Exception as e:
      logger.exception("Error updating status: %s", e)
Remove unused imports and dead code.

No bare except: blocks.

Run-time validation for configuration fields and dimension limits.

🧪 Testing Standards (pytest)
TDD-first: write/extend tests under tests/gui before implementing.

All GUI tests headless-safe (pytest.importorskip("tkinter")).

No sleep() calls; rely on after() or polling utilities.

New tests for:

Stage Chooser workflow (multi-image, modal persistence).

Editor persistence + validation edge cases.

ADetailer configuration + cooperative cancel mid-stage.

Ensure test suite:

css
Copy code
pytest -q
pytest tests/gui -q
pytest -k "stagechooser or editor or adetailer" -q
returns all green.

🧾 Documentation & Changelog
Update README, ARCHITECTURE, Help, and CHANGELOG after each PR.

Add /docs/SPRINT_SUMMARY_PR_F-H.md with:

Features completed.

Test coverage stats.

Deferred work (if any).

Update /docs/_toc.md and /docs/ARCHITECTURE.md diagrams:

Stage Chooser flow.

ADetailer insertion point.

💡 Performance & Aesthetic Enhancements
Batch scroll-log inserts to reduce flicker.

Add consistent font scaling across tabs.

Use theme.py for central color constants.

Limit LogPanel to 1000 lines or 10k chars.

Maintain frame alignment and uniform paddings.

Prefer non-modal tooltips and inline help icons over popups.

✅ Definition of Done (Each PR)
New tests added and passing.

No regressions (all existing tests green).

GUI responsive under all operations.

CancelToken works mid-stage with no zombie threads.

Code typed, documented, and lint-clean (ruff, black, mypy).

CHANGELOG and docs updated.

PR merged cleanly into main.

🔁 Integration & Merge Plan
After Copilot completes work for PR F–H:

Open PR titled:
“GUI StageChooser + Editor Polish + ADetailer Integration”

Ensure CI (pytest + pre-commit) all green.

Conduct automated + manual code review.

Merge into main.

Tag as v1.6.0-rc1.

🧭 Operational Guidance
Assume full context of prior panels (PromptPackPanel, PipelineControlsPanel, ConfigPanel, APIStatusPanel, LogPanel).

Maintain compatibility with StableNewGUI, PipelineController, and GUIState.

Follow consistent naming conventions:

Panels → *_panel.py

Tests → test_*_panel.py

Docs → SPRINT_SUMMARY_*

Apply incremental TDD per PR:

Write test → 2. Implement → 3. Refactor → 4. Commit.

Prefer dependency injection over globals for configuration access.

Keep diff small but commit through PR H sequentially.

End of Instructions
