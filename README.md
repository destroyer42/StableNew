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

- **Automated Pipeline**: txt2img → img2img cleanup → upscale → video creation
- **GUI Interface**: Tkinter-based UI for easy prompt selection and preset management
- **One-Click Execution**: Run complete pipelines with a single click
- **Structured Logging**: JSON manifests per image and CSV rollup summaries
- **Modular Design**: Clean separation of concerns for easy maintenance and expansion
- **API Integration**: Built-in readiness checks for Stable Diffusion WebUI API, Interact with `/sdapi/v1/txt2img`, `/img2img`, and `/extra-single-image`.
- **UTF-8 Support**: Full UTF-8 file I/O for international character support
- **Clean Output**: Organized folder structure for reproducible runs
- **Testing**; `pytest` suite validates endpoints, file integrity, and manifest structure
- **Global_NEG**; prevents any NSFW material or content being created, is appended to negative prompt for every generation of image

## Requirements

- Python 3.11+
- Stable Diffusion WebUI running with API enabled
- FFmpeg (for video creation)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode

```bash
python -m src.main
```

### CLI Mode

```bash
python -m src.cli --prompt "your prompt here" --preset default
```

## Project Structure

```
StableNew/
├── src/
│   ├── api/          # API client and utilities
│   ├── pipeline/     # Pipeline stages (txt2img, img2img, upscale, video)
│   ├── gui/          # Tkinter GUI components
│   ├── utils/        # Logging, config, file I/O utilities
│   └── main.py       # Main application entry point
├── tests/            # pytest test suite
├── presets/          # Configuration presets
├── output/           # Generated images and videos
├── packs/                # user prompt packs (.txt or .tsv)
├── manifests/            # rollup JSONs + CSV summaries
└─── logs/                 # runtime logs
```

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
- Always assume the WebUI API is external — **fail gracefully** if it’s not reachable.

---

### Example One-Click Flow

1. User selects a prompt pack (`packs/SDXL_batch_prompts_castles.txt`).
2. GUI launches generation (txt2img).
3. Each image is cleaned (img2img), upscaled, and saved with JSON sidecars.
4. Manifest + CSV rollups are generated.
5. Optionally, the image sequence is turned into a video.

### Mission Statement

> Build an open, modular, and verifiable creative pipeline that unites AI-assisted generation with human-directed artistry — reproducible, inspectable, and future-proof.
