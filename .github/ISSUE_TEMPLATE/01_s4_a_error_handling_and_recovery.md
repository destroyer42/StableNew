---
name: "S4-A Error handling & recovery"
about: "Graceful errors, alerts, retry/abort"
title: "S4-A: Error handling & recovery"
labels: [sprint-4, ux, stability]
assignees: ""
---
## Goal
Handle pipeline/API failures gracefully; inform users; offer retry/abort.
## DoD
- Friendly message on failure; error logged.
- Cancel returns UI to Idle with clear status.
- Tests cover simulated failures.
## Test
```
pytest -k "error or recovery" -q
```
