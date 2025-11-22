## Unreleased

- Refactored StableNewGUI layout wiring into AppLayoutV2 helper while preserving V2 panel structure and behavior.
- main_window.py restructured: layout delegated to AppLayoutV2, controller wiring grouped; no user-visible UI changes.
- Added learning execution runner and controller hooks (PR-LEARNING-V2-EXECUTION-001) to orchestrate learning plans without GUI dependencies.
