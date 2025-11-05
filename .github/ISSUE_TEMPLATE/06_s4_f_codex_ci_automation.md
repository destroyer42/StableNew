---
name: "S4-F Codex CI automation"
about: "Enable Codex autofix workflow on PRs"
title: "S4-F: Codex CI automation"
labels: [sprint-4, ci, codex]
assignees: ""
---
## Goal
Codex proposes fixes when CI fails on PRs.
## DoD
- Workflow added and documented; behavior confirmed on a failing PR.
```
pytest -q
```
