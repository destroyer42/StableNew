# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project infrastructure with `pyproject.toml` for build and tool configuration
- Pre-commit hooks for automated code quality checks (black, ruff, mypy)
- EditorConfig for consistent coding styles across editors
- Contributing guidelines in `CONTRIBUTING.md`
- Changelog file following semantic versioning
- Architecture documentation with pipeline diagrams and state machine
- GUI state management system with `GUIState` enum and `StateManager` class
- Thread-safe `CancelToken` for cooperative cancellation
- `PipelineController` for async pipeline execution with cancellation support
- Dead code archiver tool (`tools/archive_unused.py`) with:
  - AST-based import graph analysis
  - Automatic detection of unused Python files
  - Timestamped archive directories with manifest
  - Restore capability with `--undo` option
  - Dry-run mode for safe previewing
- **Optional pipeline stages**: img2img and upscale stages can now be skipped via configuration
  - Set `pipeline.img2img_enabled: false` to skip img2img stage
  - Set `pipeline.upscale_enabled: false` to skip upscale stage
  - Pipeline automatically uses output from previous stage when skipping
- **GUI Component Architecture (Mediator Pattern)**:
  - `PromptPackPanel` - Modular prompt pack selection and list management
  - `PipelineControlsPanel` - Stage toggles, loop configuration, and batch settings
  - `ConfigPanel` - Configuration tabs with validation and enhanced features
  - `APIStatusPanel` - Color-coded API connection status display
  - `LogPanel` - Thread-safe live log viewer with Python logging integration
- **Enhanced Configuration Features**:
  - **Hires Fix Steps**: New `hires_steps` parameter for controlling second-pass steps separately
  - **Expanded Dimensions**: Width/Height bounds raised to 2260px with validation warnings
  - **Face Restoration**: Optional GFPGAN/CodeFormer integration with weight control
    - Toggle-based UI with show/hide controls
    - Supports both GFPGAN and CodeFormer models
    - Adjustable restoration weight (0.0-1.0)
- Comprehensive test suite:
  - 27 tests for state management and controller
  - 14 tests for archiver tool
  - 14 tests for pipeline journey scenarios
  - 15 tests for ConfigPanel features
  - 13 tests for APIStatusPanel and LogPanel
  - All tests passing (143 total)

### Changed
- Updated `.gitignore` to exclude build artifacts, cache files, and tool outputs
- Updated `README.md` to reference new documentation
- Refactored `src/gui/__init__.py` to avoid tkinter dependency in tests
- Improved test organization and coverage
- **Enhanced `run_full_pipeline()` method** to support optional stages with clear logging
- **Improved manifest directory creation** - manifests directory created automatically when saving
- Updated pipeline summary to track which stages were completed
- **GUI Architecture**: Transitioned to component-based architecture with mediator pattern
  - Main window now acts as coordinator for panel components
  - Each panel has clear API boundaries (get/set/validate methods)
  - Improved separation of concerns and testability

### Fixed
- `PromptPackListManager.get_list_names()` now returns sorted list for consistent ordering
- Path separator handling in archive tests (cross-platform compatibility)
- Prompt parser correctly handles interleaved positive and negative prompts

### Fixed
- Import structure to allow testing without GUI dependencies
- Manifest directory creation in StructuredLogger
- Pipeline stage directory creation - now created on-demand for better efficiency

## [1.0.0] - 2024-11-02

### Added
- Initial stable release
- Full pipeline automation: txt2img → img2img → upscale → video
- Modern dark-themed Tkinter GUI
- Configuration management with preset system
- Pack-specific configuration overrides
- Prompt pack support (.txt and .tsv formats)
- Structured logging with JSON manifests
- CSV rollup summaries
- UTF-8 support for international characters
- API readiness checking with auto-discovery
- Desktop launcher scripts
- Comprehensive test suite with pytest
- Configuration validation testing
- SDXL-optimized presets
- Global NSFW prevention system
- Smart sampler/scheduler handling
- Journey test packs for validation

### Fixed
- Configuration pass-through validation
- Sampler deprecation warnings
- Pack selection persistence
- UTF-8 handling in file I/O

### Documentation
- Complete README with usage guide
- Configuration testing guide
- Launcher documentation
- Project reorganization summary

---

## Version History Format

### Categories
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Version Numbers
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

[Unreleased]: https://github.com/destroyer42/StableNew/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/destroyer42/StableNew/releases/tag/v1.0.0
