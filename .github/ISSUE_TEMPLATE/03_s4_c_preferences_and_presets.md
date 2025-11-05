---
name: "S4-C Preferences & presets"
about: "Persist last-used settings"
title: "S4-C: Preferences & presets"
labels: [sprint-4, feature, config]
assignees: ""
---
## Goal
Persist last-used settings and restore on startup.
## DoD
- Save on exit; load on start.
- Backward compatible configs.
```
pytest -k preferences -q
```
