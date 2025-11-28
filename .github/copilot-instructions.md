# StableNew – GitHub Copilot Repository Instructions (V2/V2.5) (11/26/2025-1519)

These instructions tell GitHub Copilot how to work effectively in this repository.  
They are **repository-wide**, not task-specific. Copilot should trust these over ad-hoc guesses and only explore when something is missing or clearly outdated.

---

## 1. High-Level Overview

**What this repo is**

- StableNew is a **Stable Diffusion WebUI automation pipeline** with a **Tk/Ttk desktop GUI**.
- It orchestrates text-to-image / image-to-image / upscaling pipelines, randomization, and (increasingly) learning-driven defaults.
- The focus in this repo is **V2+**, with **V1 classified as legacy** and being migrated into an `archive/` area. Copilot must treat `archive/` and `*_OLD` files as **read-only reference**, not active code.

**Tech stack**

- Language: **Python 3.11+** (see `pyproject.toml` → `requires-python = ">=3.11"` and target version `py311`).
- GUI: `tkinter`, `ttk`, `ttkbootstrap`, plus custom V2 panels.
- Tests: `pytest` (+ `pytest-xvfb` in CI for GUI tests).
- Linting: `ruff` (see CI workflow).
- Packaging/build: `setuptools` via `pyproject.toml`.
- Some JS/Node tooling exists (`package-lock.json`) but is not the main execution path.

**Scaled-down mental model**

- User runs a **Tkinter GUI**.
- GUI talks to **controllers**.
- Controllers orchestrate **pipelines** and **learning/randomizer** logic.
- Pipelines talk to **api** layer, workers, disk, etc.
- Tests verify each layer separately; CI runs lint + tests on push/PR.

---

## 2. Build, Run, and Test Instructions

Copilot should **assume these commands are canonical**.  
Only search the repo for alternatives if these clearly fail.

### 2.1 Environment setup

Always assume:

1. Python 3.11+ installed.
2. A virtualenv is recommended:

   - POSIX:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
If editable install is needed (less common):

bash
Copy code
pip install -e .
2.2 Running the app
For manual verification of GUI-related changes:

bash
Copy code
python -m src.main
Copilot should not change the entrypoint module (currently src/main.py) unless a human request explicitly asks for that.

2.3 Tests
Default local test run:

bash
Copy code
pytest -q
For more detail (or to mirror CI):

bash
Copy code
pytest -vv --maxfail=1 --disable-warnings --showlocals
On CI, tests are wrapped in xvfb for GUI; locally on a desktop machine, just running pytest is sufficient.

Copilot should treat “tests pass locally” as a hard requirement before concluding a change is “complete” (even if CI workflow uses || true).

2.4 Linting
Primary lint command (mirrors CI):

bash
Copy code
ruff check src
Copilot should fix lint findings in touched files rather than disabling rules or modifying the CI workflow.

2.5 Repo tooling
There are helper tools under tools/. One important one:

bash
Copy code
python -m tools.inventory_repo
This regenerates:

repo_inventory.json

docs/ACTIVE_MODULES.md

docs/LEGACY_CANDIDATES.md

Copilot should not rewrite these tools or the generated docs unless explicitly requested; they define the current understanding of active vs legacy modules.

3. Project Layout and Architectural Rules
Copilot should respect this layout and avoid cross-layer violations.

3.1 Root layout
Important paths in the repo root:

pyproject.toml – Python package metadata; target Python version; formatting config.

requirements.txt – runtime + dev requirements.

README.md – high-level overview and contributor notes.

docs/ – architecture, roadmap, journey tests, and other design docs.

src/ – main application code.

tests/ – pytest suite, structured roughly in parallel to src/.

tools/ – helper/maintenance scripts (inventory, migration, etc.).

archive/ – legacy/V1; read-only; do not add new logic here.

3.2 src/ architecture
Within src/, the key directories:

src/gui/
Tk/Ttk GUI layer (windows, panels, stage cards).
Must only depend on controller, utils, and well-defined adapters.
Prefer V2 files such as *_v2.py and panels_v2/.
Do not re-introduce V1 layouts or mix legacy stage cards back into core flows.

src/controller/
Application and pipeline controllers (AppController, pipeline orchestration, config assembly, cancel tokens, learning hooks).
May call into pipeline, learning, api, and utils, but not into GUI.

src/pipeline/
Pipeline definitions, config objects, and stage execution logic.
Pure / deterministic logic where possible. No Tk imports here.

src/learning/
Learning system (learning records, datasets, JSONL writers, learning plans).
Should not import GUI. Minor controller coupling via contracts is acceptable.

src/api/
Process manager, WebUI client, health checks. Responsible for dealing with external Stable Diffusion / WebUI processes.

src/utils/
Logging, config helpers, generic utilities. GUI and controllers may depend on this, but avoid creating new circular dependencies.

src/ai/, src/cluster/, src/queue/, src/services/
Additional layers for settings generation, worker registry, future distributed features.
Treat these as pure Python logic with clear boundaries; no Tk imports.

Rule for Copilot:

Never make GUI modules depend on pipeline/learning directly.
GUI → controller → pipeline/learning/api, not the other way around.

Prefer modifying V2 modules listed in docs/ACTIVE_MODULES.md.
Do not add new behavior to archived / legacy files.

3.3 tests/ layout
tests/ai_v2/, tests/api/, tests/controller/, tests/pipeline/, tests/gui_v2/, etc.
Mirror the src/ structure; new tests should follow this pattern.

Some tests/**/legacy or tests/gui_v1_legacy directories may exist: these are for reference only and should not be extended for new features.

Rule for Copilot:

For every non-trivial change in src/, either:

Update existing tests that cover the changed behavior, or

Add new tests in the corresponding tests/<layer>/ directory.

Do not delete tests simply because they fail; fix the code or, if the test is truly obsolete, clearly mark it as such in a minimal change.

4. Behavioral Expectations for Copilot
These are general, non task-specific rules that apply to all changes Copilot proposes:

Small, focused changes

Keep modifications scoped to a single subsystem (e.g., GUI only, or controller only) unless the architecture clearly requires touching both.

Avoid broad refactors or repo-wide search-and-replace.

Respect existing patterns

Before adding a new helper or module, briefly search for similar existing functions/classes and reuse the pattern.

Follow the layering rules: do not introduce new cross-layer dependencies.

Syntax and correctness

When editing a file, ensure the final code is syntactically valid.
Avoid leaving partial blocks, unresolved merge markers, or unused imports.

Prefer changes that keep type/usage consistent with existing code; avoid introducing obvious type mismatches.

Tests and lint before “done”

Assume the human will run at least:

ruff check src

pytest -q

Propose changes that are very likely to pass both. Do not rely on changing CI config to “make things green.”

Legacy awareness

Treat archive/ and any (OLD) or legacy-marked files as read-only, used only as references when porting behavior into V2.

New logic should land in V2 modules and follow ARCHITECTURE_v2 and other docs under docs/.

Documentation and naming

When adding new design/PR helper docs under docs/ or src/docs/, prefer including a V2.5 + date/time suffix in the filename when consistent with existing docs (e.g., *_V2.5_2025-11-26.md).

For code files, follow the existing naming patterns (*_v2.py for new GUI components, etc.) rather than inventing new suffixes.

5. How Copilot Should Use These Instructions
Trust this file first.
Use these commands, layouts, and rules as ground truth.

Only run additional repo searches (e.g., scanning for build steps, hunting for entrypoints) if:

A command here fails in a way that indicates the instructions are outdated, or

The human explicitly says the instructions are wrong.

When in doubt about where to place new code:

Prefer V2 modules in src/ that match the layer you’re working in.

Mirror the structure in tests/ for any new tests.

If these instructions ever conflict with a future, clearly-marked architecture doc in docs/, that doc takes precedence – but Copilot should assume this file is current unless told otherwise.