# StableNew GUI Overview

The GUI is a Tkinter-based application with a dark ASWF theme.

## 1. Architecture Overview

StableNewGUI (main_window.py)
 ├── Theme (theme.py)
 ├── PromptPackPanel
 ├── PipelineControlsPanel
 ├── RandomizationPanel
 ├── AdvancedPromptEditor
 ├── LogPanel
 └── Mediator (pack selection → config context)

## 2. Theming Rules

- All colors come from src/gui/theme.py.
- No hard-coded colors elsewhere.
- Use ASWF blacks and greys for backgrounds.
- Use ASWF gold for high-contrast text.
- Buttons:
  - Primary: gold or green on dark background.
  - Danger: red on dark background.

## 3. Layout Rules

- Every tab must have consistent padding and background.
- Controls must be arranged in a grid/pack with:
  - Minimum padding (4–8px).
  - Stretch/resizing enabled where appropriate.
- Scrollbars required for:
  - Randomization panel.
  - Advanced prompt editor.
  - Panels that exceed height.

## 4. Behavior Constraints

- Never block the main thread.
- Load configurations on explicit user action (no autoload).
- Show warnings for unsaved changes.
- Ensure that selecting packs does NOT modify the config editor implicitly.

## 5. Resilience

- GUI logs maintain last 20 lines.
- Crash detection on startup.
- Cleanup routine runs if improper shutdown detected.
