"""Empty Folder Pruner (Czkawka Empty Folders).

Recursively discovers and cleans empty directory trees left behind after
file reorganizations or failed backups.
"""

from pathlib import Path
from typing import List, Set, Tuple
import os

_IGNORABLE_FILES: Set[str] = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}


def find_empty_folders(target_dir: Path, ignore_junk_files: bool = True) -> List[Path]:
    """Finds all empty folders bottom-up."""
    empty_dirs: List[Path] = []
    target_dir = target_dir.resolve()

    for root, dirs, files in os.walk(target_dir, topdown=False):
        p_root = Path(root)
        if p_root == target_dir:
            continue

        # Check files
        if ignore_junk_files:
            real_files = [f for f in files if f.lower() not in _IGNORABLE_FILES]
        else:
            real_files = files

        # Check if dir is currently empty
        try:
            entries = list(os.scandir(p_root))
            has_subdirs = any(e.is_dir() for e in entries)
            if not has_subdirs and not real_files:
                empty_dirs.append(p_root)
        except (PermissionError, FileNotFoundError, OSError):
            continue

    return empty_dirs


def delete_empty_folders(empty_dirs: List[Path], dry_run: bool = False) -> int:
    """Removes empty directories bottom-up."""
    removed = 0
    for d in empty_dirs:
        if not dry_run:
            try:
                # Remove junk files inside if any
                for item in d.iterdir():
                    if item.is_file() and item.name.lower() in _IGNORABLE_FILES:
                        item.unlink()
                d.rmdir()
                removed += 1
            except Exception:
                continue
        else:
            removed += 1
    return removed
