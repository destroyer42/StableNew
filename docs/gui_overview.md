GUI Overview

This document outlines the top-level layout of the StableNew desktop GUI after PR‑1 (Layout Cleanup & Component De‑duplication).

Tabs & Panels

- Left Sidebar: Prompt Pack list and selection
- Center Notebook (Dark.TNotebook)
  - Pipeline: Configuration editor for txt2img, img2img, upscale, and related summaries
  - Randomization: Prompt randomizer tools (S/R rules, wildcards, matrix)
  - General: Global run behavior and Pipeline Controls (looping, batch, stages)
- Bottom: Action buttons and Log output

Layout Diagram

```
+---------------------------------------------------------------+
| Using: <Config Source>                                        |
+---------------------------------------------------------------+
| Packs        |                Center Notebook                 |
| (list)       |  [ Pipeline ] [ Randomization ] [ General ]    |
|              |                                               |
|              |  Pipeline: config editor + summary            |
|              |  Randomization: S/R, wildcards, matrix        |
|              |  General: Pipeline Controls + API settings    |
+---------------------------------------------------------------+
| Run buttons | Logs                                           |
+---------------------------------------------------------------+
```

Key Notes

- Pipeline controls live only inside the center notebook under the "General" tab. They are not duplicated elsewhere.
- Tab content containers use the dark theme styles (Dark.TFrame, Dark.TLabel, etc.) for visual consistency.
- Randomization tab is always present and wired to the prompt randomizer utilities.

