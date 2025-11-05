---
name: "S4-D Self-test runner"
about: "One-click diagnostics from GUI"
title: "S4-D: Self-test runner"
labels: [sprint-4, test, dx]
assignees: ""
---
## Goal
Expose a GUI command to run a minimal test set and show summary.
## DoD
- Button/menu triggers pytest subset non-blocking; summary dialog.
```
pytest -k smoke -q
```
