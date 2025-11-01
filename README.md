# StableNew - Stable Diffusion WebUI Automation

A Python 3.11 application that automates the complete image generation pipeline using the Stable Diffusion WebUI API.

### Overview

This project automates the full creative pipeline using the **Stable Diffusion WebUI (A1111) API**:
1. **Prompt → Image (txt2img)**
2. **Image cleanup (img2img)**
3. **Upscaling (extras/single-image)**
4. **Sequence → Video (FFmpeg)**

It provides a **Tkinter GUI** that lets users run these steps individually or as a one-click pipeline.
Everything is designed to be **reproducible, inspectable, and testable** — no “black box” magic.

---

### Core Intent

To build a modular, testable system that transforms written prompts into cinematic video clips using Stable Diffusion, with full transparency of inputs, parameters, and outputs.

The architecture emphasizes:
- **Automation** – zero manual folder edits or renaming.
- **Integrity** – no accidental overwrites, full provenance tracking.
- **Extensibility** – new models, stages, or tools can drop in easily.
- **Explainability** – logs, manifests, and CSV summaries for every run.
- **Cross-compatibility** – works cleanly on Windows, Linux, or macOS.

---


## Features

### Core Pipeline
```

### Core Pipeline

- **Automated Workflow**: txt2img → img2img cleanup → upscale → video creation
- **SDXL Support**: Optimized presets and configurations for SDXL models
- **Advanced Integrations**: Embeddings, LORAs, and custom model support
- **Global NSFW Prevention**: Automatic negative prompt enhancement for all generations

### User Interface

- **Modern GUI**: Dark-themed Tkinter interface with tabbed configuration
- **Interactive Config**: Real-time configuration editing with pack-specific overrides
- **Pack Management**: Dynamic prompt pack selection with status indicators
- **Configuration Override**: Apply current settings across multiple packs
- **Smart Sampler Handling**: Proper sampler/scheduler separation (no more warnings!)

### Technical Features

- **API Integration**: Built-in readiness checks and auto-discovery for SD WebUI API
- **Structured Logging**: JSON manifests per image and CSV rollup summaries
- **UTF-8 Support**: Full international character support for prompts and filenames
- **Modular Architecture**: Clean separation for easy maintenance and expansion
- **Comprehensive Testing**: `pytest` suite with journey tests for full validation

### Content Creation

- **Prompt Packs**: Organized collections with embeddings and LORAs integration
- **Preset System**: SDXL-optimized and specialized configurations
- **Heroes Pack**: Professional hero portraits with quality embeddings
- **Clean Output**: Timestamped directories with complete metadata tracking

## Requirements

- Python 3.11+
- Stable Diffusion WebUI running with API enabled
- FFmpeg (for video creation)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Desktop Launcher (Recommended)

For the easiest experience, create a desktop shortcut:

```bash
powershell -ExecutionPolicy Bypass -File "scripts/create_shortcuts.ps1"
```

Then double-click the "StableNew" icon on your desktop to launch the GUI.

### GUI Mode

```bash
python -m src.main
```

The GUI provides an intuitive interface with:

- **Pack Management Panel**: Multi-select prompt packs from the `packs/` directory with persistent selection
- **Pack Status Display**: Shows currently loaded packs with "✓" indicators
- **Configuration Tabs**:
  - **Display Tab**: View current settings (defaults + pack overrides)
  - **Edit Tab**: Modify configurations with override checkboxes for pack-specific customization
- **Prompt Display**: Shows both positive and negative prompts from selected packs
- **Live Log Console**: Real-time pipeline status and API connectivity feedback
- **Loop Controls**: Configure execution patterns (single runs, batch processing, cross-stage loops)

**Key Features:**

- Override system allows pack-specific configuration without affecting defaults
- Pack selection persists across configuration changes
- Automatic WebUI detection and API readiness checking
- Dark theme with modern styling and clear visual feedback

### CLI Mode

```bash
python -m src.cli --prompt "your prompt here" --preset default
```

## Project Structure

```
StableNew/
├── src/              # Core application code
│   ├── api/          # API client and utilities
│   ├── pipeline/     # Pipeline stages (txt2img, img2img, upscale, video)
│   ├── gui/          # Tkinter GUI components
│   ├── utils/        # Logging, config, file I/O utilities
│   └── main.py       # Main application entry point
├── tests/            # Complete test suite (pytest + validation)
├── docs/             # Documentation and guides
├── scripts/          # Launch scripts and utilities
├── archive/          # Archived/old files (suffixed with _OLD)
├── presets/          # Configuration presets
├── packs/            # User prompt packs (.txt or .tsv)
├── output/           # Generated images and videos
└── tmp/              # Temporary files
```

## Documentation

Additional documentation is available in the [`docs/`](docs/) directory:

- **[Configuration Testing Guide](docs/CONFIGURATION_TESTING_GUIDE.md)** - Detailed guide for maintaining configuration integrity and validation testing
- **[Launchers Guide](docs/LAUNCHERS.md)** - Information about desktop shortcuts and launch scripts

**Scripts available in [`scripts/`](scripts/) directory:**

- `create_shortcuts.ps1` - Create desktop shortcuts (recommended)
- `launch_stablenew.bat` - Direct launcher for Windows
- `launch_webui.py` - WebUI management script

## External File dependencies

- "C:\Users\rober\stable-diffusion-webui\webui-user.bat" -location of file that launches WebUI and opens a webpage for stable-diffusion
- (potential) symlink from StableNew (either root or src) pointing to "C:\Users\rober\stable-diffusion-webui"

## Example Prompt Pack format

- <embedding:stable_yogis_pdxl_positives> <embedding:stable_yogis_realism_positives_v1>
- (masterpiece, best quality, 8k, HDR) character portrait, natural skin, realistic hands, clean lighting, subtle pores
- young shieldmaiden, matte steel, cloak clasp, hand resting on rim, steady gaze, 3/4 angle
- <lora:add-detail-xl:0.7> <lora:CinematicStyle_v1:0.55> <lora:DetailedEyes_V3:1.0>
- neg: <embedding:ac_neg1> <embedding:negative_hands> <embedding:sdxl_cyberrealistic_simpleneg-neg> <embedding:stable_yogis_pdxl_negatives2-neg>
- <embedding:stable_yogis_anatomy_negatives_v1-neg>
- deformed hands, extra digits, fused fingers, twisted wrists, asymmetrical eyes, melted faces, rubber skin, plastic speculars, face mush, double pupils

## Recommended Prompt Pack Format

For optimal parsing and organization, structure your `.txt` prompt packs using blank lines to separate individual prompts. Each prompt block can span multiple lines that will be concatenated with spaces:

```text
# Complex character with embeddings and LoRA
<embedding:character_base> <embedding:quality_boost>
detailed character portrait, professional lighting, natural skin texture
young warrior, confident expression, detailed armor and weapons
<lora:character_detail:0.7> <lora:lighting_enhance:0.5>
neg: <embedding:bad_anatomy> <embedding:low_quality-neg>
neg: deformed hands, ugly face, blurry, low quality

# Landscape with style enhancement  
beautiful mountain landscape at golden hour, dramatic clouds
majestic peaks, crystal clear lake reflection, cinematic composition
<lora:landscape_realism:0.8> <lora:dramatic_sky:0.6>
neg: <embedding:negative_base> oversaturated, cartoon style, artificial

# Simple portrait without embeddings
professional headshot, studio lighting, clean background
business attire, confident pose, sharp focus
neg: ugly, distorted, amateur lighting, low resolution
```

**Key formatting rules:**

- Use `# comments` for organization (ignored during parsing)
- Separate different prompts with blank lines
- Multiple positive lines are joined with spaces
- Use `neg:` prefix for negative prompt lines
- Embeddings: `<embedding:name>` or `<embedding:name-neg>`
- LoRAs: `<lora:name:weight>` with decimal weights (0.1-1.5)
- UTF-8 characters fully supported for international content

## Testing

```bash
pytest tests/
```

## License

MIT

### Technical Highlights

- **API readiness probe:** checks `/internal/system-info` and `/sdapi/v1/sd-models` before execution.
- **UTF-8 text discipline:** no literal "\n" corruption; cross-platform newline normalization.
- **Clean folder boundaries:** generated vs. upscaled vs. archived runs never overlap.
- **Run manifests:** every image has a JSON sidecar with generation parameters.
- **Rollup summarization:** merges manifests into a single structured file + CSVs.
- **Video generation:** FFmpeg auto-assembles ordered frames into an MP4.
- **Live console:** real-time logs displayed in the GUI for traceability.

---

### Why It Exists

Stable Diffusion’s default batch modes are powerful but fragmented.
This project unifies them into a single controllable workflow — a framework for creators, testers, and AI agents to build on.
Each run can be replicated, audited, and extended by humans **or** automated scripts without losing context or data integrity.

---

### Future Extensions

- Integrate AnimateDiff or Deforum for advanced motion.
- Add async job queue + progress estimation.
- Add cloud upload hooks or Foundry/Vantage dataset export.
- Add style transfer or LoRA-based theming modules.

---

### Developer Notes

- Code must follow **PEP8**, use **type hints**, and be fully **documented**.
- All runs produce logs and manifests in **`manifests/`**.
- Tests must pass via `pytest -q`.
- Never overwrite user data; always write to new timestamped folders.
- Always assume the WebUI API is external — **fail gracefully** if it's not reachable.

#### Configuration Change Requirements

**CRITICAL**: When modifying configuration-related code, always run the validation test:

```bash
python tests/test_config_passthrough.py
```

This test ensures that configuration parameters properly flow from the GUI forms through the pipeline to the WebUI API. It validates:

- Parameter pass-through accuracy (should be 90-100%)
- Proper handling of all txt2img, img2img, and upscale parameters
- Detection of configuration drift or missing parameters

**When adding new configuration parameters:**

1. Update `src/utils/config.py` with the new parameter in `get_default_config()`
2. Add corresponding GUI controls in `src/gui/main_window.py`
3. Update pipeline methods in `src/pipeline/executor.py` to include the new parameter
4. **Update the validation test** `tests/test_config_passthrough.py`:
   - Add expected parameter names to `EXPECTED_TXT2IMG_PARAMS`, `EXPECTED_IMG2IMG_PARAMS`, or `EXPECTED_UPSCALE_PARAMS`
   - Update any preset-specific validation logic if needed
5. Run the validation test to ensure 90-100% pass-through accuracy
6. Update presets in `presets/` directory if the new parameter should have non-default values

**Parameter integrity is critical** - the validation test prevents silent configuration drift that could cause unexpected generation results.

For detailed maintenance instructions, see: [`docs/CONFIGURATION_TESTING_GUIDE.md`](docs/CONFIGURATION_TESTING_GUIDE.md)

---

### Example One-Click Flow

1. User selects a prompt pack (`packs/SDXL_batch_prompts_castles.txt`).
2. GUI launches generation (txt2img).
3. Each image is cleaned (img2img), upscaled, and saved with JSON sidecars.
4. Manifest + CSV rollups are generated.
5. Optionally, the image sequence is turned into a video.

### Mission Statement

> Build an open, modular, and verifiable creative pipeline that unites AI-assisted generation with human-directed artistry — reproducible, inspectable, and future-proof.
