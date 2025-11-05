# Codex Chat Instructions — Sprint 4 (UX + Reliability)

## Goal
Polish UX, error handling, preferences, retries/backoff, docs & demo media. Prepare v1.0-rc.

## Sequence
1) Preferences persistence → save last-used settings; reload on startup.
2) Error handling & recovery → friendly alerts, retry/abort.
3) Status/Logs enhancements → levels, scroll-lock, copy.
4) API retries/backoff → exponential backoff + jitter.
5) Codex CI autopatch → codex-autofix.yml verified.
6) Docs/demo assets → GIFs/screenshots for README.

## Commands
- pre-commit run --all-files
- pytest -q
- pytest tests\gui -q

## Guardrails
- Tk main thread non-blocking; headless tests; small PRs with clear DoD.
