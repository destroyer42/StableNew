# Contributing to StableNew

Thank you for your interest in contributing to StableNew! This document provides guidelines and instructions for contributing to the project.
 
 
 ### AI-Assisted Development

  StableNew uses GitHub Copilot / Codex + ChatGPT under a documented process:

  - [Codex Integration SOP](.github/CODEX_SOP.md)
  - [Codex Autopilot Workflow v1](docs/dev/Codex_Autopilot_Workflow_v1.md)

  Please read these before using AI tools to modify this repo.
  
  
## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Coding Standards](#coding-standards)
- [How to Contribute](#how-to-contribute)
- [Adding New Features](#adding-new-features)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)

## Development Environment Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Stable Diffusion WebUI with API enabled
- FFmpeg (for video generation)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/destroyer42/StableNew.git
   cd StableNew
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install development dependencies
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Running the Application

- **GUI Mode:** `python -m src.main`
- **CLI Mode:** `python -m src.cli --prompt "your prompt" --preset default`

## Coding Standards

### Code Style

We use automated tools to maintain consistent code style:

- **Black** - Code formatting (line length: 100)
- **Ruff** - Fast Python linter
- **isort** - Import sorting
- **mypy** - Type checking

All of these run automatically via pre-commit hooks.

### Manual Linting

```bash
# Format code
black src/ tests/

# Run linter
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Code Organization

- **src/api/** - API client and utilities
- **src/pipeline/** - Pipeline stages (txt2img, img2img, upscale, video)
- **src/gui/** - GUI components (split into MVC pattern)
- **src/utils/** - Logging, config, file I/O utilities
- **tests/** - All test files

### Writing Good Code

1. **Type Hints:** Use type hints for all function signatures
   ```python
   def process_image(image_path: str, scale: float = 2.0) -> dict[str, Any]:
       ...
   ```

2. **Docstrings:** Use clear docstrings for public functions
   ```python
   def create_video(frames: list[str], output_path: str, fps: int = 30) -> bool:
       """Create video from image frames using FFmpeg.

       Args:
           frames: List of image file paths in sequence order
           output_path: Path where video should be saved
           fps: Frames per second (default: 30)

       Returns:
           True if video creation succeeded, False otherwise
       """
       ...
   ```

3. **Error Handling:** Always handle errors gracefully
   ```python
   try:
       result = api_call()
   except requests.RequestException as e:
       logger.error(f"API call failed: {e}")
       return None
   ```

4. **Logging:** Use structured logging
   ```python
   logger.info(f"Processing image {image_name}")
   logger.warning(f"Slow response: {elapsed:.2f}s")
   logger.error(f"Failed to upscale: {error}")
   ```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/destroyer42/StableNew/issues)
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, SD WebUI version)
   - Relevant logs from `logs/` directory

### Suggesting Features

1. Check existing feature requests in Issues
2. Create a new issue with:
   - Clear use case and benefits
   - Proposed implementation approach (if applicable)
   - Any mockups or examples

## Adding New Features

### Adding a New Pipeline Stage

1. Create the stage module in `src/pipeline/`
2. Add corresponding configuration in `src/utils/config.py`
3. Update `src/pipeline/executor.py` to integrate the stage
4. Add GUI controls in `src/gui/`
5. Write tests in `tests/`
6. Update documentation

### Adding a New UI Panel

1. Create panel component in `src/gui/`
2. Follow MVC pattern:
   - **Model:** Data in `src/gui/state.py`
   - **View:** UI widgets in panel file
   - **Controller:** Logic in `src/gui/controller.py`
3. Integrate with main window
4. Add keyboard shortcuts if applicable
5. Write GUI unit tests

### Configuration Changes

**CRITICAL:** When modifying configuration-related code:

1. Update `src/utils/config.py` with new parameters in `get_default_config()`
2. Add GUI controls in `src/gui/main_window.py`
3. Update pipeline methods in `src/pipeline/executor.py`
4. **Update validation test** in `tests/test_config_passthrough.py`:
   - Add parameter to expected lists
   - Update preset-specific validation
5. Run validation: `python tests/test_config_passthrough.py`
6. Ensure 90-100% pass-through accuracy
7. Update presets in `presets/` directory

See [Configuration Testing Guide](docs/CONFIGURATION_TESTING_GUIDE.md) for details.

## Testing Guidelines
- GUI tests must be headless-safe. Use `tests/gui/conftest.py` fixtures; do not create additional Tk roots or call blocking dialogs directly.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run tests matching pattern
pytest -k "test_config"

# Skip slow/integration tests
pytest -m "not slow and not integration"
```

### Writing Tests

1. **Unit Tests:** Test individual functions in isolation
   ```python
   def test_parse_prompt():
       result = parse_prompt("test <lora:model:0.7>")
       assert "lora" in result
       assert result["lora"]["model"] == 0.7
   ```

2. **Integration Tests:** Test component interactions (mark with `@pytest.mark.integration`)
   ```python
   @pytest.mark.integration
   def test_full_pipeline(mock_api):
       pipeline = Pipeline(mock_api)
       result = pipeline.run_full_pipeline("test prompt", config)
       assert result["success"]
   ```

3. **GUI Tests:** Test GUI logic without display (mark with `@pytest.mark.gui`)
   ```python
   @pytest.mark.gui
   def test_state_machine():
       state = GUIState()
       state.transition_to(State.RUNNING)
       assert state.current == State.RUNNING
   ```

### Test Coverage

- Aim for 80%+ coverage on new code
- Critical paths (API, pipeline) should have 90%+ coverage
- GUI display code can have lower coverage (hard to test)

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow coding standards
   - Write/update tests
   - Update documentation

3. **Run tests locally:**
   ```bash
   pytest
   black src/ tests/
   ruff check src/ tests/
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting)
   - `refactor:` - Code refactoring
   - `test:` - Test additions/changes
   - `chore:` - Maintenance tasks

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub

6. **PR Requirements:**
   - Clear description of changes
   - Link to related issues
   - All tests passing
   - No merge conflicts
   - Code review approved

### PR Review Process

1. Automated checks run (linting, tests)
2. Maintainer reviews code
3. Address review feedback
4. Once approved, PR is merged

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers and help them get started
- Focus on what's best for the project
- Accept constructive criticism gracefully

## Questions?

- Open an issue for general questions
- Check existing documentation
- Review closed issues and PRs for similar questions

---

Thank you for contributing to StableNew! 🎨
