# Recent Bugs, Fixes, and Lessons Learned

## Major Bugs Found (2025)

### 1. Tkinter Threading Violation (GUI Hang on Second Run)
- **Symptom:** GUI would hang (white screen, "not responding") after running the pipeline a second time, especially after changing model/refiner settings.
- **Root Cause:** Tkinter GUI operations (e.g., `messagebox.showerror`) were called from a worker thread instead of the main thread.
- **Fix:** All GUI operations are now marshaled to the main thread using `root.after(0, ...)`.
- **Lesson:** Never call Tkinter GUI methods from background threads. Always use `root.after` for thread-safe UI updates.

### 2. Indentation and Code Outside Methods
- **Symptom:** Syntax errors, unpredictable behavior, and failed imports due to code living at class/module scope.
- **Root Cause:** Style/theme setup and widget creation were outside methods, violating Python class structure.
- **Fix:** All setup code is now inside `__init__` or helper methods. No executable code at class/module scope.
- **Lesson:** Only constants and method definitions should be at class level. All instance setup must be inside methods.

### 3. Import Normalization and PEP 585 Typing
- **Symptom:** Lint/type errors due to missing or incorrect imports, use of `Optional` instead of `X | None`, and legacy typing.
- **Root Cause:** Outdated import patterns and type annotations.
- **Fix:** Imports are now normalized, missing modules commented out, and PEP 585 typing (`X | None`, `list[str]`, etc.) is used throughout.
- **Lesson:** Always update imports and typing to match current standards. Comment out broken imports, don't leave them half-enabled.

## What Worked
- Refactoring all setup into `__init__` and helpers.
- Using `root.after` for thread-safe GUI updates.
- Normalizing imports and using PEP 585 typing.
- Running quick compile/import tests before deeper refactors.
- Adding single logger at top-of-file for consistent diagnostics.

## What Not To Do (To Avoid Regression)
- Do **not** call Tkinter GUI methods from worker threads.
- Do **not** leave code at class/module scope (except constants/methods).
- Do **not** use half-imported modules; comment them out if missing.
- Do **not** use legacy typing (`Optional`, `Dict`, etc.)—prefer PEP 585.
- Do **not** skip compile/import tests after major refactors.

## References
- See `docs/BUG_FIX_GUI_HANG_SECOND_RUN.md` and `docs/THREADING_FIX.md` for more details.
- See `CHANGELOG.md` for a summary of recent fixes and improvements.
