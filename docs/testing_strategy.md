# StableNew Testing Strategy

## 1. Test Types

### Unit Tests
- Test individual functions or modules.
- Mock file IO, network interactions, and external SDXL APIs.
- Live under `tests/unit/` or the root of `tests/` when legacy.

### Integration Tests
- Validate interactions between multiple modules (e.g., pipeline stages working together).
- Should not depend on actual GUI rendering or real SDXL.
- Live under `tests/integration/`.

### GUI Tests
- Verify that GUI components construct without error.
- Use mocks or headless environments for Tkinter.
- Avoid timing-based assertions when possible.
- Live under `tests/gui/`.

### Journey Tests
- Simulate realistic user flows:
  - GUI launch
  - Pack selection
  - Config loading and modifications
  - Preset loading
  - List operations
  - Pipeline run (with a mocked controller)
- Live under `tests/journey/`.

## 2. TDD Requirements

- When adding new behavior, write a failing test first.
- Implement the minimal code to make the test pass.
- Refactor while keeping tests green.
- Every bugfix should have at least one test that fails before the fix and passes after.

## 3. Test Reliability

- Tests must run in a few seconds total, and each test ideally under one second.
- Tests must be deterministic and not rely on external timing or randomness.
- Tests must run on supported CI environments (e.g., Linux runners with xvfb for GUI).

## 4. Mocks

Use mocks for:
- File IO that modifies user data.
- Preferences storage (JSON configs, etc.).
- Pipeline controller threads and background workers.
- SDXL API calls or WebUI HTTP endpoints.

Prefer pytest fixtures and context managers to keep mock lifetimes clear and explicit.
