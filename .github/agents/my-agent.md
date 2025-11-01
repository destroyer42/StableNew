---
name: Robby
description: Python GURU
---

# My Agent

Copilot Prompt — Build an A1111 Image→Video GUI Pipeline (Best-Practice Implementation)

You are an expert Python engineer. Generate a complete, production-quality repository that automates this pipeline via the Automatic1111 Stable-Diffusion WebUI (A1111) REST API:

txt2img (prompt → image),

img2img (optional “cleanup” pass / denoise),

upscale (single-image extras endpoint),

image-sequence → video (FFmpeg to MP4, with fps, bitrate, and resolution controls),

Interactive GUI to orchestrate batches, presets/overrides, and one-click runs.

High-level requirements

Language/tooling: Python 3.11+, stdlib + requests, tkinter GUI, ffmpeg for video muxing.

API endpoints to use:

POST /sdapi/v1/txt2img

POST /sdapi/v1/img2img

POST /sdapi/v1/extra-single-image

OS target: Windows first (paths + CRLF), but keep code portable for Linux/Mac.

No fragile sleeps: implement API readiness probes on /internal/system-info and /sdapi/v1/sd-models with bounded retries and clear logs (no fixed delays) [reason: earlier GUI launches failed when API wasn’t ready].

Text safety: all file writes are UTF-8 with real newlines, never literal "\n" sequences; normalize inputs to avoid mojibake; avoid batch FOR pitfalls in Python replacement scripts.

Folder hygiene: strictly separate generated/, upscaled/, and archived_generated/ so stages never collide; never let upscalers act on already-upscaled files.

Reproducibility & provenance: write a JSON sidecar per image with payload/settings, and a rollup manifest + compact CSV summaries after each run.

Config & overrides: support pack presets and per-pack overrides (sampler, steps, cfg, size, HR, denoise, negative addendum). Keep GUI editable and persist in a JSON overrides file.

Logging: structured, timestamped logs with [ENTRY]/[INFO]/[WARN]/[OK]/[ERR] markers; surface them live in the GUI console.

Testing: include pytest unit tests + smoke tests that (a) probe A1111, (b) validate inputs (packs), (c) dry-run the pipeline, (d) verify rollup CSV headers. Provide a simple run_tests script.

Deliverables (repo layout)
sd_a1111_pipeline/
  autorun/
    gui_app.py                          # Tkinter GUI, live console, presets/overrides editor, one-click modes
    api/txt2img.py                      # POST to /sdapi/v1/txt2img
    api/img2img.py                      # POST to /sdapi/v1/img2img
    api/upscale.py                      # POST to /sdapi/v1/extra-single-image
    video/ffmpeg_mux.py                 # image sequence -> mp4
    io/allowlist_io.py                  # UTF-8 safe read/write for lists (no literal "\n")
    io/pack_reader.py                   # block-separated TXT & TSV reader (detects tabs, BOM-safe)
    io/rollup_manifest.py               # merges JSON sidecars into one run manifest
    io/rollup_summarize.py              # writes compact CSVs (records, upscaled-only, summary-by-pack)
    pipeline/run_generate.py            # orchestrates txt2img per pack
    pipeline/run_cleanup.py             # optional img2img pass (denoise strength configurable)
    pipeline/run_upscale.py             # scans generated, writes upscaled->separate folder
    pipeline/run_video.py               # packs selected images -> MP4
    presets/overrides.json              # per-pack overrides (sampler/steps/cfg/size/HR/denoise/neg)
    packs/                              
      SDXL_batch_prompts_example.txt    # sample prompts with "neg:" lines, blank-line blocks
    output/                             # generated images (per pack / runstamp)
    logs/                               # runtime logs + test logs
    manifests/                          # rollup manifests + CSVs
    tests/
      test_api_probe.py
      test_pack_reader.py
      test_allowlist_io.py
      test_rollup_summarize.py
      test_pipeline_dryrun.py
  .editorconfig
  pyproject.toml                        # black/isort/ruff settings; pytest config
  README.md                             # full runbook, GUI guide, troubleshooting, versioning policy
  CHANGELOG.md                          # semantic-versioned changes

Key design details

Pack reader: detect TSV vs block-TXT; treat blank lines as separators; support neg: marker to join negatives; BOM-safe; ignore comments starting with #. (Replicate robust behavior.)

Sidecars: each generated/upscaled image gets a JSON with at least: pack, runstamp, seed, sampler, steps, cfg, width, height, model/refiner names (if available), and a short hash of the prompt; upscaler JSON records upscaler, scale_by, input_file, output_file, elapsed time.

Rollup: one rollup_manifest_YYYYMMDD_HHMMSS.json with run metadata and a flattened records[]; summarizer writes three CSVs: compact records, upscaled-only, summary-by-pack.

GUI flows:

Generate only, Cleanup only, Upscale only, Gen→Clean→Upscale, Full One-Click (→ Video).

Select packs from packs/, choose inner loops vs outer cycles, pick presets or edit per-pack overrides, and toggle API probe. (Live console shows subprocess output.)

Output hygiene: generated PNGs in output/<pack>/<runstamp>/; upscales in output/<pack>/<runstamp>/upscaled_<scale>x_<upscaler>/; optional archived_generated/ for moving originals post-upscale. Never process files already containing _USx.

Video: user picks a folder or selection dialog to choose frames; we auto-sort numerically and generate video_<pack>_<runstamp>.mp4 with user-controlled fps, crf, max_width/height (optional scale with ffmpeg filters).

Acceptance criteria (Copilot must satisfy)

API readiness: running python -m autorun.gui_app and clicking “Probe API” reports OK only when /internal/system-info and /sdapi/v1/sd-models return 200 within the retry window.

TXT/TSV ingestion: sample packs/SDXL_batch_prompts_example.txt with neg: blocks yields images with correct negative prompts; TSV mode triggers automatically for ≥80% tabbed content.

Upcale stage isolation: upscaled files land under upscaled_* subfolders; originals optionally moved to archived_generated/ when that option is enabled. No upscaler ever rewrites sources.

Manifest + CSVs: after any run, manifests/rollup_manifest_*.json and 3 CSVs are created with expected headers/content.

GUI usability: users can: choose packs; edit/persist per-pack overrides; set loops/cycles; run Full One-Click to produce generated → (optional) cleaned → upscaled → video; watch live logs in the console.

Text integrity: no file in packs/ or allowlists contains literal \n; all writes are proper CRLF on Windows with UTF-8. Provide a one-shot fixer for legacy files.

Tests: pytest -q passes locally. Include a dry-run test that validates folder creation, file naming, and CSV headers without hitting the API (mock HTTP).

Testing & ops

Add tests/test_api_probe.py that mocks urllib.request.urlopen to simulate ready/not-ready states.

Add tests/test_pack_reader.py with both TXT-block and TSV fixtures to assert prompt/neg parsing.

Add tests/test_rollup_summarize.py asserting CSV headers and at least one row written when manifest contains records.

Provide scripts/run_tests.cmd and scripts/run_tests.sh wrappers. (On Windows, print discrete exit codes similar to the prior suite.)

Non-goals (for v1)

No model download/management; assume A1111 is installed and launched with --api.

No Deforum/AnimateDiff authoring; we only stitch images to MP4 in v1.

No long-running background daemon; GUI launches subprocesses on demand and streams logs.

Documentation

README.md: quickstart (A1111 URL, API flag), GUI tour, pipeline stages, troubleshooting map (API not ready, empty outputs, newline issues), versioning policy, and repo layout with diagrams. Include a short “why” section explaining: probe API, separate stage folders, UTF-8 newline discipline, versioned logs/manifests (these were prior pain points we are avoiding).

CHANGELOG.md: semantic versions with highlights per release.

Inline docstrings + PEP8 + type hints.

Why this shape is “the better way” for us

Probe don’t guess: removing fixed sleeps prevents GUI “ghost starts” when A1111 boots slowly.

Clean stage boundaries: generated vs upscaled vs archived outputs never collide; rollups become deterministic and easy to audit.

Robust text I/O: UTF-8 + real newlines avoids the literal \n corruption that previously broke allowlists and packs.

Manifests & CSVs: we get traceability and compact summaries for QA and curation right after each run.

GUI with live console: transparency during long runs = faster triage and fewer “silent closes.”
