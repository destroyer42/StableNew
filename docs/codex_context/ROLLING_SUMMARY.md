# ROLLING_SUMMARY

> Short, cumulative summary of major changes.
> Keep this file brief: aim for bullet points, not essays.

---

## 2025-11-22 (v1 bootstrap)

- Established `docs/codex_context/` as the single source of truth for AI assistants.
- Defined v2 architecture: GUI → controller → pipeline → api → learning.
- Formalized pipeline rules (stages, adetailer as explicit stage, upscale invariants).
- Summarized Learning v2: builder + JSONL writer + execution runner/controller.

---

## How To Update

After each major PR or refactor, add 3–6 bullets:
- What changed
- Which modules were touched
- Any new invariants or rules

Keep old snapshots in `docs/codex_context/ARCHIVE/` when this file grows too large.
