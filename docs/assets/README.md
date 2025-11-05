# Demo Asset Storage

Binary walkthroughs are **not** committed to the repository. Instead, this folder documents which assets exist and how to retrieve them from the shared media drive.

- Maintain per-feature indexes (for example, `core_flows/README.md`) that describe the latest filenames and destinations.
- Store the actual `.webp`/`.gif` captures on the `/docs/media/` SharePoint library, keeping each file under 2 MB.
- When updating an asset, refresh the index so downstream docs always point to the correct filename.

Before publishing documentation, download the assets from SharePoint and bundle them with the site or release package rather than checking them into git.
