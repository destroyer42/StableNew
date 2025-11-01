# StableNew - Stable Diffusion WebUI Automation

A Python 3.11 application that automates the complete image generation pipeline using the Stable Diffusion WebUI API.

## Features

- **Automated Pipeline**: txt2img → img2img cleanup → upscale → video creation
- **GUI Interface**: Tkinter-based UI for easy prompt selection and preset management
- **One-Click Execution**: Run complete pipelines with a single click
- **Structured Logging**: JSON manifests per image and CSV rollup summaries
- **Modular Design**: Clean separation of concerns for easy maintenance and expansion
- **API Integration**: Built-in readiness checks for Stable Diffusion WebUI API
- **UTF-8 Support**: Full UTF-8 file I/O for international character support
- **Clean Output**: Organized folder structure for reproducible runs

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
└── output/           # Generated images and videos
```

## Testing

```bash
pytest tests/
```

## License

MIT
