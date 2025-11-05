# Core Flow Media Index

No binary assets are checked into the repository. This index documents the canonical media that illustrate StableNew's GUI flows and where to fetch them when preparing release materials.

## Available Walkthroughs

| Flow | Filename | Description | Storage Location |
|------|----------|-------------|------------------|
| End-to-end pipeline overview | `txt2img_pipeline.webp` | Demonstrates txt2img → img2img → upscale orchestration with status updates. | Publish to shared asset drive (`/docs/media/core_flows/` on the team SharePoint) |
| Prompt pack management highlights | `prompt_pack_management.webp` | Shows pack selection, validation, and override workflow. | Publish to shared asset drive (`/docs/media/core_flows/` on the team SharePoint) |

Download the assets from the storage location above before embedding them in documentation or release notes. Compress new captures to <2 MB each, prefer `.webp`/`.gif`, and update this index if filenames change.

## Usage Guidance

- Embed walkthroughs in Markdown using relative links (for example, `![Prompt packs](docs/assets/core_flows/prompt_pack_management.webp)`), but ensure the binary itself is delivered out-of-band (for example, via release bundle or CDN).
- When publishing documentation, copy the referenced assets into the documentation site or release package; do **not** commit them to the repository.
- Keep filenames stable to avoid broken references in downstream portals.

