
# Copilot Path Instructions — GUI Tests (Tkinter, Headless)

**Scope:** Applies to files under `tests/gui/**` and GUI-adjacent helpers in `src/gui/**` used only by tests.

**Goal:** Grow reliable, headless GUI test coverage without blocking the Tk mainloop or joining worker threads.

---

## Golden Rules
1. **Non-blocking UI:** Never block Tk's main thread. Use `after()` and queues; avoid `time.sleep()` in the UI thread.
2. **No thread joins in tests:** The controller owns `join()`. Tests must wait on controller state or events (e.g., `lifecycle_event`) with timeouts.
3. **Small, deterministic tests:** Prefer focused widget-level asserts with minimal rendering; smoke-test full windows sparingly.
4. **Headless by default:** Use markers and a headless display (`xvfb`) in CI. Local dev may run with a visible Tk window when needed.

---

## Pytest Markers
- `@pytest.mark.gui` — requires a Tk mainloop/headless display. CI runs these under `xvfb`.
- `@pytest.mark.skip_on_windows` (optional) — for known platform quirks; add a TODO and a link to the tracking issue.
- `@pytest.mark.flaky(reruns=2)` (optional) — allowed only for known race‑y third‑party behavior; add a TODO to deflake.

---

## Fixtures (recommended)
Create these in `tests/gui/conftest.py`:

```python
import tkinter as tk
import pytest
import threading
import time

@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()  # headless
    yield root
    try:
        root.destroy()
    except Exception:
        pass

@pytest.fixture
def tk_pump(tk_root):
    """Pump Tk events without blocking the main thread."""
    def pump(duration=0.2, step=0.01):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            try:
                tk_root.update()
            except Exception:
                break
            time.sleep(step)
    return pump
```

Use them like:
```python
@pytest.mark.gui
def test_log_panel_renders_and_filters(tk_root, tk_pump):
    from src.gui.log_panel import LogPanel
    w = LogPanel(tk_root)
    w.pack()
    tk_pump(0.1)
    assert w.winfo_exists()
```

---

## Waiting Patterns (no joins)
Use polling with timeouts, never `join()`:

```python
import time

def wait_until(pred, timeout=5.0, step=0.02):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(step)
    return False

def test_cancel_transitions_to_idle(controller):
    controller.start_pipeline(...)
    controller.request_cancel()
    assert controller.lifecycle_event.wait(timeout=8.0)
```

---

## Stage Chooser & Modals
- Create modals non-blocking (`transient`, `grab_set` optional, but tests must not block).
- Drive modal state via variables; close with callbacks scheduled via `after()`.
- Add a smoke test per modal that opens, sets a selection, and closes without freezing.

---

## Queue/Logging in UI
- Replace blocking `queue.get()` calls in widgets with `after()` polling loops.
- Provide a small adapter for tests (e.g., `TestLogFeeder`) that pushes messages into the widget’s queue.
- Assert the visible count/levels rather than internal buffer contents when possible.

---

## Filename Sanitization
- Centralize in `src/utils/filename_sanitizer.py` (if missing, create it).
- Tests cover invalid chars, trailing dots/spaces (Windows), very long names, and collision handling with timestamp suffix.

---

## Coverage & Skips
- Target ≥80% line coverage for `src/gui/**` gradually.
- Skip OS‑specific branches only with clear TODO + linked issue.
- Avoid snapshot testing for Tk; prefer semantic asserts (widget exists, text/values updated, state toggles).

---

## When Copilot Sees Review Feedback
- Apply changes on the same feature branch.
- Write/adjust tests first (TDD), then implementation.
- Re-run: `pre-commit run --all-files && pytest -q`
