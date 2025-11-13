# StableNew Testing Strategy

## 1. Test Types

### Unit Tests
- Test individual functions/modules.
- Mock file IO, network, SDXL API.
- Live under tests/unit/ or tests/ root.

### Integration Tests
- Module-to-module interactions.
- No GUI, no real SDXL.

### GUI Tests
- Basic construction tests: ensure widgets instantiate.
- Journey tests: simulate user flows with mocking.

### Journey Test Requirements
A full journey test simulates:
- GUI launch
- Pack selection
- Config loading
- Config modifications
- Preset loading
- List loading
- Warnings on unsaved changes
- Pipeline run (mock controller)
- Exit + crash recovery

## 2. TDD Requirements

- Write failing test first.
- Then implement feature.
- Then refactor.

## 3. Test Reliability

- Tests must run in <1s each.
- Must run on Linux/Windows CI.
- Avoid fragile timing assumptions.

## 4. Mocks

Use mocks for:
- File IO
- Preferences storage
- Pipeline controller threads
- SDXL API calls
