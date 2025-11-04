---
applyTo: "tests/gui/**/*.py"
---

## GUI Test Requirements

1. Use a headless harness (xvfb in CI) and never block the Tk main loop.
2. Poll controller state/events (e.g., `lifecycle_event`), rather than joining worker threads.
3. Avoid brittle sleeps; use bounded waits with retries.
4. When adding widgets, expose stable selectors/ids to simplify tests.
