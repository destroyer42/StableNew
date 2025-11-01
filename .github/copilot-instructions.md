# StableNew - Copilot Instructions

This is a **Stable Diffusion WebUI automation pipeline** that orchestrates txt2img → img2img → upscale → video creation through both GUI and CLI interfaces.

## Architecture Overview

**Core Pipeline Flow**: `src/pipeline/executor.py` orchestrates the 4-stage pipeline:
1. `txt2img` - Generate from prompt via `/sdapi/v1/txt2img`
2. `img2img` - Optional cleanup/refinement via `/sdapi/v1/img2img` 
3. `upscale` - Enhancement via `/sdapi/v1/extra-single-image`
4. `video` - FFmpeg sequence assembly via `src/pipeline/video.py`

**API Client**: `src/api/client.py` handles all SD WebUI communication with built-in readiness checks and timeout handling. Always check `client.check_api_ready()` before pipeline operations.

**Configuration System**: JSON presets in `presets/` directory with hierarchical structure (txt2img/img2img/upscale/video/api sections). Use `ConfigManager.load_preset()` for runtime config.

## Key Patterns

**Structured Logging**: All operations generate JSON manifests per image AND CSV rollups via `StructuredLogger`. Every image gets metadata tracking prompt, config, timestamps, and file paths.

**UTF-8 Safety**: All file I/O uses explicit `encoding='utf-8'` and `ensure_ascii=False` for international character support. Never assume system defaults.

**Directory Structure**: Each run creates timestamped subdirs: `output/run_YYYYMMDD_HHMMSS/{txt2img,img2img,upscaled,video,manifests}/`

**Global NSFW Prevention**: The `global_neg` system automatically appends safety prompts to all negative prompts to prevent inappropriate content.

**Error Handling Pattern**: Use try-catch with structured logging. Always log failures with context and continue pipeline where possible. Check `client.check_api_ready()` before any API calls.

## Critical Implementation Details

**API Readiness**: SD WebUI API must be running on `http://127.0.0.1:7860` (configurable). Use exponential backoff in `check_api_ready()` - no hardcoded sleeps.

**Base64 Handling**: Images flow as base64 between API calls. Use `utils/file_io.py` helpers `save_image_from_base64()` and `load_image_to_base64()` consistently.

**Prompt Pack Format**: Supports both `.txt` (line-based) and `.tsv` (tab-separated) with `neg:` prefix for negative prompts. See README example for embedding syntax.

**Entry Points**: 
- GUI: `python -m src.main` 
- CLI: `python -m src.cli --prompt "text" --preset default`

**Configuration Hierarchy**: Default config → Preset overrides → Pack-specific overrides → Runtime parameters. Always preserve this precedence order.

**Windows-Specific Paths**: External dependency on `C:\Users\rober\stable-diffusion-webui\webui-user.bat`. Consider symlink from project root for portability.

## GUI Design Specifications

**Startup Flow**: Main entry auto-launches `webui-user.bat`, pings API at `http://127.0.0.1:7860`, then opens GUI with dark theme.

**Visual Design**: Modern dark theme with rounded corners, well-labeled buttons, informative tooltips, attention-grabbing CTAs, and clear affordances for user guidance.

**Layout Structure**:
- **Live Log Panel** (bottom): Real-time status updates, API connection success/failure messages
- **Prompt Pack Selector** (left): Multi-select window showing `.txt` files from `packs/` directory
- **List Management Dropdown**: Load/save/edit/delete custom prompt pack lists with persistent storage
- **Tabbed Configuration** (center): 
  - Display mode: Shows current settings (default + pack-specific overrides)
  - Edit mode: Allows modification of default configs and per-pack overrides
- **Pipeline Controls** (right): Loop configuration for different execution patterns

**Pipeline Execution Patterns**:
- Single pack vs multiple packs vs custom list selection
- Stage-specific loops: `(generate, clean, upscale) x N` 
- Cross-stage loops: `generate x N, then upscale x N`
- Mixed patterns: `((generate, clean, upscale) x 3)` vs individual stage repetition

**Graceful Shutdown**: Close button triggers log finalization, manifest updates, and result output before exit.

## Development Workflows

**Running the Application**:
```bash
# Start SD WebUI first (required)
C:\Users\rober\stable-diffusion-webui\webui-user.bat --api

# Then launch StableNew
python -m src.main  # GUI mode
python -m src.cli --prompt "test" --preset default  # CLI mode
```

**Testing Strategy**: Run `pytest tests/` - covers API connectivity, file integrity, manifest structure, UTF-8 handling.

**Debugging API Issues**: Check `logs/` directory for structured JSON logs. Use `client.check_api_ready()` to diagnose SD WebUI connectivity.

## External Dependencies

**Required**: Stable Diffusion WebUI running with `--api` flag
**Video**: FFmpeg in PATH for video creation
**Platform**: Windows-first design but cross-platform compatible

When modifying pipeline stages, always update both the metadata tracking and ensure proper error handling with structured logging.