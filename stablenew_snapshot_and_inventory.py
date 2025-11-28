#!/usr/bin/env python
"""
StableNew Snapshot & Repo Inventory Tool
----------------------------------------
Double-clickable Python script that:
1. Creates a timestamped zip snapshot of the repo (excluding heavy/noisy folders)
2. Generates a repo_inventory.json with basic metadata for every tracked file

Usage:
- Place this file in the ROOT of your StableNew repo.
- Double-click it in Explorer, or run:
    python stablenew_snapshot_and_inventory.py
"""

import json
import os
import sys
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List


# ---- Configuration ---------------------------------------------------------

# Folders to skip when snapshotting and inventorying
DEFAULT_EXCLUDES = {
    ".git",
    ".idea",
    ".vscode",
    ".mypy_cache",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "node_modules",
    ".DS_Store",
    "snapshots",
    "archive_tmp",
}

# File extensions to skip (log files, big binaries, etc.) — tweak as needed
DEFAULT_EXCLUDED_EXTS = {
    ".log",
    ".tmp",
    ".pyc",
    ".pyo",
    ".pyd",
}


# ---- Data structures -------------------------------------------------------

@dataclass
class FileEntry:
    path: str
    size_bytes: int
    mtime_iso: str


@dataclass
class RepoInventory:
    repo_root: str
    created_at: str
    snapshot_zip: str
    file_count: int
    total_size_bytes: int
    excludes: list
    excluded_exts: list
    files: List[FileEntry]


# ---- Helpers ---------------------------------------------------------------

def is_excluded(path: Path, repo_root: Path) -> bool:
    """
    Return True if the path is in an excluded directory or has an excluded extension.
    """
    # Check directory components
    rel = path.relative_to(repo_root)
    parts = rel.parts
    for part in parts:
        if part in DEFAULT_EXCLUDES:
            return True

    # Check extension
    if path.suffix.lower() in DEFAULT_EXCLUDED_EXTS:
        return True

    return False


def gather_files(repo_root: Path) -> list[FileEntry]:
    entries: list[FileEntry] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if is_excluded(p, repo_root):
            continue

        try:
            stat = p.stat()
        except OSError:
            # Skip files we can't stat (permission issues, etc.)
            continue

        rel = p.relative_to(repo_root).as_posix()
        mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        entries.append(
            FileEntry(
                path=rel,
                size_bytes=stat.st_size,
                mtime_iso=mtime_iso,
            )
        )
    return entries


def create_snapshot_zip(repo_root: Path, snapshot_dir: Path) -> Path:
    """
    Create a timestamped zip file containing the repo contents (minus excluded paths).
    Returns the path to the created zip.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_name = f"StableNew-snapshot-{timestamp}.zip"
    zip_path = snapshot_dir / zip_name

    print(f"[INFO] Creating snapshot: {zip_path}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in repo_root.rglob("*"):
            if not p.is_file():
                continue
            if is_excluded(p, repo_root):
                continue
            rel = p.relative_to(repo_root).as_posix()
            zf.write(p, arcname=rel)

    print("[INFO] Snapshot completed.")
    return zip_path


def write_inventory(repo_root: Path, snapshot_zip: Path, entries: list[FileEntry]) -> Path:
    """
    Write repo_inventory.json alongside the snapshot.
    """
    total_size = sum(e.size_bytes for e in entries)
    inventory = RepoInventory(
        repo_root=str(repo_root),
        created_at=datetime.now().isoformat(timespec="seconds"),
        snapshot_zip=str(snapshot_zip),
        file_count=len(entries),
        total_size_bytes=total_size,
        excludes=sorted(DEFAULT_EXCLUDES),
        excluded_exts=sorted(DEFAULT_EXCLUDED_EXTS),
        files=entries,
    )

    inventory_path = snapshot_zip.with_name("repo_inventory.json")
    print(f"[INFO] Writing inventory: {inventory_path}")

    with inventory_path.open("w", encoding="utf-8") as f:
        json.dump(
            asdict(inventory),
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("[INFO] Inventory written.")
    return inventory_path


# ---- Main entrypoint -------------------------------------------------------

def main() -> int:
    # Resolve repo root as the directory containing this script
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent

    print("============================================")
    print(" StableNew Snapshot & Repo Inventory Tool")
    print("============================================")
    print(f"[INFO] Repo root: {repo_root}")
    print("[INFO] Building file list...")

    entries = gather_files(repo_root)
    print(f"[INFO] Tracked files: {len(entries)}")

    # Put snapshots inside a "snapshots" folder at repo root
    snapshot_dir = repo_root / "snapshots"
    snapshot_zip = create_snapshot_zip(repo_root, snapshot_dir)
    inventory_path = write_inventory(repo_root, snapshot_zip, entries)

    print("")
    print("[DONE] Snapshot and inventory successfully created.")
    print(f"       Snapshot:  {snapshot_zip}")
    print(f"       Inventory: {inventory_path}")
    print("")
    print("You can attach the zip + JSON to PRs, or reference them in Codex prompts.")
    print("")

    # Pause if opened via double-click on Windows console
    if os.name == "nt" and sys.stdin is None:
        os.system("pause")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
