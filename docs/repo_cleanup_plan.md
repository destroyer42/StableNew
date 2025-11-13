# StableNew Repository Cleanup Plan (MajorRefactor)

## Goals

- Consolidate and modernize documentation.
- Reduce clutter at the repo root.
- Make it clear which docs are authoritative.
- Prepare the repo for multi-agent, multi-PR workflows.

## 1. Documentation Consolidation

### Actions

- Create/maintain docs/ as the single home for documentation.
- Ensure:
  - docs/engineering_standards.md captures coding rules.
  - docs/testing_strategy.md captures testing rules.
  - docs/gui_overview.md captures GUI layout and UX rules.
- Move older root docs into docs/legacy/:
  - ARCHITECTURE.md
  - AUDIT_REPORT_S3_S4_READINESS.md
  - GUI_ENHANCEMENTS.md
  - ISSUE_ANALYSIS.md
  - OPEN_ISSUES_RECOMMENDATIONS.md
- Update README.md to:
  - Point to docs/ as the canonical docs location.
  - Add an AI-agent note pointing to the standards docs.

## 2. Root-Level File Cleanup

Target candidates at repo root that are clearly debug or exploratory scripts:

- _tmp_check.py
- temp_ppp_test.py
- temp_ppp_test2.py
- temp_tk_test.py
- simple_debug.py
- debug_batch.py
- test_advanced_features.py
- test_gui_enhancements.py

Actions:

- Move debug scripts to archive/root_experiments/.
- Move root-level test files into tests/legacy/ (if they are still useful) or archive/root_experiments/ (if fully superseded by new tests).

## 3. Tests Reorganization

Planned structure:

- tests/unit/
- tests/gui/
- tests/integration/
- tests/journey/

Actions:

- Move GUI-focused tests to tests/gui/.
- Move pipeline integration tests to tests/integration/.
- Place new full-journey GUI tests into tests/journey/.
- Keep existing test names, but adjust imports if necessary.

## 4. CODEOWNERS and Responsibility

Add .github/CODEOWNERS:

- src/gui/* → GUI specialist (or team)
- tests/** → test specialist
- docs/** → docs specialist
- fallback: @destroyer42 as overall owner

## 5. Process

- Start with a dry-run using scripts/reorg_repo.py.
- Confirm all moves in git status.
- Run full test suite.
- Only then commit and open a PR named:
  - "Repo Cleanup: Docs Consolidation & Root File Reorg"

This PR should not change behavior—only files locations, imports, and documentation.
