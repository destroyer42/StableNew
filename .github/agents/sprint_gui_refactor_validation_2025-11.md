---
name: stabilization-and-ux-agent.md
description: addressing the findings of the audit
---


**Role**

Agent: Stabilization & UX Reliability

Purpose

Execute a focused set of stability/UX PRs: enforce coverage threshold in CI, route archive log writes through the canonical proxy, introduce headless-safe dialogs.py and migrate direct dialog calls, and make API retries cancel-aware. Keep diffs small, safe, and well-tested.

Scope / Files

CI: .github/workflows/ci.yml

GUI: src/gui/main_window.py, src/gui/dialogs.py (new), any GUI file using messagebox/filedialog

API client: src/api/client.py

Tests: tests/gui/**, existing suites; add/update minimal stubs only if needed


Guardrails

No behavior changes to pipeline logic or defaults.

Tk main thread non-blocking (no join() in GUI/tests).

Headless-safe: dialogs must no-op in CI; GUI tests skip cleanly if Tk/display missing.

Small PRs with conventional commits and green CI.

Use package imports (no sys.path hacks; no from … import *).

Keep changes self-contained; do not introduce new dependencies.


Success Criteria (Definition of Done)

CI fails if coverage falls below the floor (initially 75%).

Archive log viewer writes via self.add_log (fallback guarded).

All direct messagebox/filedialog usages replaced with src.gui.dialogs wrappers; tests can stub them.

_request() in src/api/client.py can abort between retries when cancel_token is set.

pre-commit and pytest pass locally and in CI.



---

Plan of Execution (4 PRs, smallest first)

PR #1 — CI coverage floor

Change: Add --cov-fail-under=75 to pytest step in Linux/Xvfb job.

File: .github/workflows/ci.yml

Diff (conceptual):

pytest --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=75 -q


Commit: ci: enforce coverage floor to prevent regressions

PR #2 — Route archive log through proxy

Change: In src/gui/main_window.py, replace any archive-viewer direct self.log_text writes with:

_add = getattr(self, "add_log", None)
if callable(_add):
    _add(message, "INFO")
elif getattr(self, "log_text", None) is not None:
    self.log_text.config(state=tk.NORMAL)
    self.log_text.insert(tk.END, message + "\n")
    self.log_text.see(tk.END)
    self.log_text.config(state=tk.DISABLED)

Commit: fix(gui): route archive viewer logs through proxy

PR #3 — Introduce dialogs wrapper & migrate calls

Add: src/gui/dialogs.py (headless-safe wrappers)

from __future__ import annotations
import os
try:
    from tkinter import filedialog, messagebox  # type: ignore
except Exception:
    filedialog = None; messagebox = None

def _headless() -> bool:
    return (os.name != "nt" and not os.getenv("DISPLAY")) or messagebox is None or filedialog is None

def show_error(title: str, message: str, **kw) -> None:
    if not _headless(): messagebox.showerror(title, message, **kw)

def show_warning(title: str, message: str, **kw) -> None:
    if not _headless(): messagebox.showwarning(title, message, **kw)

def show_info(title: str, message: str, **kw) -> None:
    if not _headless(): messagebox.showinfo(title, message, **kw)

def ask_open_filename(**kw) -> str:
    return "" if _headless() else filedialog.askopenfilename(**kw)

def ask_open_filenames(**kw) -> tuple[str, ...]:
    return tuple() if _headless() else filedialog.askopenfilenames(**kw)

def ask_save_as_filename(**kw) -> str:
    return "" if _headless() else filedialog.asksaveasfilename(**kw)

def ask_directory(**kw) -> str:
    return "" if _headless() else filedialog.askdirectory(**kw)

def show_pipeline_error(error: Exception, stage: str = "") -> None:
    title = f"Pipeline Error{' - ' + stage if stage else ''}"
    msg = f"{error}\n\nThe pipeline has been stopped.\nCheck the log panel for details.\n\nRecovery: Verify API connection and try again."
    show_error(title, msg)

Migrate: In GUI code, replace:

from tkinter import messagebox, filedialog → from src.gui import dialogs

messagebox.showerror(...) → dialogs.show_error(...)

filedialog.askdirectory(...) → dialogs.ask_directory(...) …and so on for show_info, show_warning, ask_*.


Tests (if needed): in tests/gui/conftest.py, autouse stub:

@pytest.fixture(autouse=True)
def stub_dialogs(monkeypatch):
    from src.gui import dialogs
    for name, ret in [
        ("show_error", None), ("show_warning", None), ("show_info", None),
        ("ask_open_filename", ""), ("ask_open_filenames", tuple()),
        ("ask_save_as_filename", ""), ("ask_directory", "")
    ]:
        monkeypatch.setattr(dialogs, name, (lambda *a, **k: ret), raising=False)

Commit: feat(gui): add dialog wrappers and migrate calls for testability

PR #4 — Cancel-aware API retries (optional, fast)

Change: In src/api/client.py _request(), accept cancel_token and abort between retries:

def _request(self, method: str, endpoint: str, ..., backoff_factor: float|None=None, cancel_token=None):
    for attempt in range(self.max_retries + 1):
        try:
            ...
        except Exception:
            if attempt < self.max_retries:
                if cancel_token and getattr(cancel_token, "is_set", lambda: False)():
                    raise
                delay = self._calculate_backoff(attempt, backoff_factor)
                time.sleep(delay)
                continue
            raise

Wire cancel_token from callers as available. Commit: feat(api): make retries cancel-aware


---

How to Work (Agent Routine)

1) Branching

Create a branch per PR from postGemini (or MajorRefactor if that’s the active integration branch):

ci/coverage-floor-75

fix/gui-archive-log-proxy

feat/gui-dialog-wrappers-migration

feat/api-cancel-aware-retries


2) Local checks

pre-commit run --all-files
pytest -q
pytest -k "gui or error or backoff" -q

3) PR Titles & Body

Use the commit messages above as PR titles.

Body: 1–3 bullets (what changed, why, testing).


4) Acceptance gates

CI green (Linux: Xvfb; Windows as configured).

No new flake/mypy/ruff violations.

No behavior change to pipeline defaults.



---

Reporting Format (post-run)

Return a concise markdown summary:

# Stabilization & UX Reliability — PR Summary
- PR #1 (CI coverage floor): merged ✔ | floor: 75%
- PR #2 (archive log proxy): merged ✔ | touched: src/gui/main_window.py
- PR #3 (dialogs wrapper+migration): open ⏳ | migrated N call sites
- PR #4 (cancel-aware retries): merged ✔ | wired from controller: yes/no

## Test results
- pre-commit: passed
- pytest: ### passed, ### skipped, ### failed (list failures if any)

## Notes/Risks
- [itemized]


---

Quick Commands (Windows-friendly)

:: after each PR
pre-commit run --all-files
pytest -q
git add -A
git commit -m "..."
git push -u origin <branch>


---

Out of Scope

Major UI redesigns (beyond dialog indirection & log proxy).

Business-logic changes, parameter defaults, or model selection.

New dependencies or build steps.



---
