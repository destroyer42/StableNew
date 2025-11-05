---
name: "S4-E Retries/backoff for API"
about: "Robust API retries with backoff"
title: "S4-E: Retries/backoff for API calls"
labels: [sprint-4, stability, api]
assignees: ""
---
## Goal
Improve robustness of SD WebUI calls.
## DoD
- Retries with exponential backoff + jitter.
- Configurable limits; unit tests.
```
pytest -k backoff -q
```
