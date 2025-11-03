# GUI Stage Chooser + Editor Polish + ADetailer Integration Agent

**Scope:** Continue after ConfigPanel/APIStatusPanel/LogPanel merge. Finish PRs F→H, improve GUI responsiveness, polish UX, and prepare for release merge to `main`.

---

## Objectives

1. **PR F — Stage Chooser (High Priority)**
   - Implement per-image non-blocking modal:
     - Preview of current output.
     - Choices: `img2img`, `ADetailer`, `upscale`, `none`.
     - “Re-tune settings” link and “Always do this for this batch” checkbox.
   - Save user choice per image in pipeline context.
   - Modal must not freeze main UI (use separate Toplevel + event queue).
   - Add cancel and auto-advance options.
   - Tests: simulate multi-image workflow; verify chosen stages.

2. **PR G — Editor Fixes & UX Polish**
   - Fix `status_text` AttributeError.
   - Allow `<` and `>` in prompts (escape before save, unescape on load).
   - Auto-populate pack name field.
   - Global negative visible and saved properly.
   - Add `name:` metadata prefix to filename output (e.g. `Hero_2025-11-03_1357.png`).
   - Improve layout scaling for long pack names.
   - Tests: load→edit→save→reload; ensure prompt fields persist correctly.

3. **PR H — ADetailer Stage Integration**
   - Add ADetailer configuration tab under ConfigPanel (Model, Confidence, Mask feather, Sampler, Denoise, CFG, Pos/Neg prompts).
   - Integrate ADetailer into pipeline after txt2img (alternative to img2img).
   - Respect CancelToken at every cooperative checkpoint.
   - Add `adetailer_enabled` flag to config schema.
   - Tests: config defaulting, validation, mocked API payload verification.

---

## Quality Requirements
- PEP8 + typing for all new modules.
- All GUI updates occur via `after()` or queued callbacks.
- Extend pytest suite:
  - GUI smoke test for Stage Chooser modal.
  - Editor field persistence test.
  - ADetailer mock integration test.
- Update CHANGELOG + README for each PR.
- Keep diffs small but progress through **PR F→H sequentially** this sprint.
- Merge to `main` when all tests are green.

---

## Performance & Aesthetic Improvements
- Optimize scroll-heavy panels (use `.update_idletasks()` batching).
- Introduce consistent font scaling across tabs.
- Optional light/dark toggle persisted to `user_settings.json`.
- Refactor color constants to `theme.py`.
- Limit log updates to 10Hz (batch queue flush) to reduce flicker.

---

## Post-Completion Tasks
- Run full pytest suite (headless).
- Generate updated `/docs/SPRINT_SUMMARY_PR_F-H.md`.
- Update `/docs/_toc.md` and `/docs/ARCHITECTURE.md` with Stage Chooser and ADetailer diagrams.
- Tag release candidate: `v1.6.0-rc1`.

---

**Definition of Done**
- Stage Chooser functional, non-blocking, and cancel-safe.
- Editor stable and user-friendly.
- ADetailer fully integrated, configurable, and test-covered.
- Docs and CHANGELOG updated.
- All tests passing (`pytest -q`).
- Branch merged to `main`.
