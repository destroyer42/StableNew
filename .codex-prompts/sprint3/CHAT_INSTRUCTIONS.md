# Codex Chat Instructions — Sprint 3 (Stabilization & CI)

## Goal
Autonomously verify what S3 delivered and complete what remains with small, TDD-first PRs.

## Sequence
1) Audit S3 status → read AGENTS.md and S3 templates, run pre-commit & pytest.
2) Implement S3-B (progress/ETA) with ttk.Progressbar + ETA callbacks; tests under tests/gui/test_progress_eta.py.
3) Fix S3-A (legacy tests): update or remove obsolete tests; keep coverage.
4) Finalize S3-C (CI): ensure ci.yml runs ruff/black/mypy/pytest with Xvfb; PR must require checks.

## Commands
- pre-commit run --all-files
- pytest -q
- pytest -k progress -q
- pytest tests\gui -q

## Guardrails
- Tk main thread non-blocking; never join worker threads in GUI/tests.
- Keep changes minimal; update docs/CHANGELOG for visible changes.
