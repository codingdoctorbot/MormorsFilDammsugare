"""Space Hogs & Bad Extension Fixer (Czkawka Big Files & Bad Extensions)."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import os

from ..core.sniffer import MediaCategory, sniff_file
from ..core.walker import walk_files


@dataclass
class SpaceHog:
    path: Path
    size: int
    format_name: str
    category: str


@dataclass
class BadExtension:
    path: Path
    current_ext: str
    detected_format: str
    canonical_ext: str
    size: int


def find_space_hogs(directories: List[Path], top_n: int = 50) -> List[SpaceHog]:
    """Finds the top N largest files in directories."""
    files: List[Tuple[Path, int]] = []
    for d in directories:
        for f in walk_files(d):
            try:
                files.append((f, f.stat().st_size))
            except Exception:
                continue

    files.sort(key=lambda x: x[1], reverse=True)
    results = []
    for path, sz in files[:top_n]:
        res = sniff_file(path)
        results.append(SpaceHog(path=path, size=sz, format_name=res.format_name, category=res.category.value))
    return results


def find_bad_extensions(directories: List[Path]) -> List[BadExtension]:
    """Finds files whose extension disagrees with their magic bytes."""
    mismatches = []
    for d in directories:
        for f in walk_files(d):
            res = sniff_file(f)
            ext = f.suffix.lower()
            if (
                not res.is_weak
                and res.canonical_ext
                and ext != res.canonical_ext
                and ext not in (".jpeg", ".jpe")
                and res.category != MediaCategory.CACHE_JUNK
            ):
                try:
                    sz = f.stat().st_size
                except Exception:
                    sz = 0
                mismatches.append(
                    BadExtension(
                        path=f,
                        current_ext=ext,
                        detected_format=res.format_name,
                        canonical_ext=res.canonical_ext,
                        size=sz,
                    )
                )
    return mismatches


def fix_bad_extension(item: BadExtension) -> Path:
    """Renames file to use its true canonical extension."""
    new_path = item.path.with_suffix(item.canonical_ext)
    if new_path.exists():
        counter = 2
        while new_path.exists():
            new_path = item.path.with_name(f"{item.path.stem} ({counter}){item.canonical_ext}")
            counter += 1
    item.path.rename(new_path)
    return new_path
