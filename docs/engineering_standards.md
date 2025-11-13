# StableNew Engineering Standards

These standards apply to ALL agents and all code contributions.

## 1. Coding Style

- Follow Python 3.11+ idioms.
- All modules must use type hints (`from __future__ import annotations`).
- Avoid long functions (>30 lines) unless unavoidable.
- Avoid deep nesting; prefer early returns.
- No global state except constants.
- No hard-coded filesystem paths.

## 2. Directory Rules

- All GUI code lives under src/gui/.
- All service logic under src/services/.
- All utility functions under src/utils/.
- No cyclic imports between GUI → controller → utils.

## 3. Testing Standards

- All features must have tests.
- All bugfixes must start with a failing test.
- Tests must be deterministic and fast.
- GUI tests use mocks unless running a journey test.

## 4. Performance Standards

- Tkinter never blocks the UI thread.
- Long operations must be asynchronous or delegated to pipeline controller threads.
- File IO must be minimal on the main thread.

## 5. Documentation

- All user-visible behavior must be documented.
- All PRs must update the changelog.

## 6. Security / Safety

- No execution of external binaries unless explicitly intended.
- No unsafe eval.
- No deletion of user files except where explicitly intended.
