"""High-performance Exact Duplicate Finder (Czkawka Exact Duplicates).

Uses Czkawka's 3-stage duplicate hunting pipeline:
1. Exact File Size Match (O(1) filter)
2. Fast Head/Tail Fingerprint Probe (64KB start + 64KB end)
3. Full SHA-256 Hash on verified candidates
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
import os
import re

import send2trash

from ..core.hasher import fast_fingerprint, full_sha256
from ..core.walker import walk_files


@dataclass
class DuplicateGroup:
    sha256: str
    size: int
    files: List[Path]


# Copy markers and recovery patterns for 'cleanest' path selection
_RE_COPY_MARKER = re.compile(
    r"(?:\s*\(\d+\)|\s*-\s*(?:copy|kopia)(?:\s*\(\d+\))?|\s*\((?:copy|kopia)\)|[\s_]copy(?:\s*\d+)?)$",
    re.IGNORECASE,
)
_RE_RECOVERED_NAME = re.compile(r"^(?:file|f)\d+$|^\d{6,}(?:_[a-z])?$", re.IGNORECASE)


def calculate_name_penalty(path: Path) -> int:
    stem = path.stem
    penalty = 0
    if _RE_RECOVERED_NAME.match(stem):
        penalty += 10
    if _RE_COPY_MARKER.search(stem):
        penalty += 5
    # Penalize deeper nested paths slightly
    penalty += len(path.parts)
    return penalty


def pick_keeper(files: List[Path], strategy: str = "cleanest") -> Tuple[Path, List[Path]]:
    """Selects which file to keep according to strategy, returning (keeper, to_remove)."""
    if not files:
        raise ValueError("Empty file list")

    if strategy == "cleanest":
        # Lowest penalty wins
        keeper = min(files, key=calculate_name_penalty)
    elif strategy == "oldest":
        keeper = min(files, key=lambda p: p.stat().st_mtime)
    elif strategy == "newest":
        keeper = max(files, key=lambda p: p.stat().st_mtime)
    elif strategy == "shortest_path":
        keeper = min(files, key=lambda p: len(str(p)))
    else:
        keeper = files[0]

    to_remove = [f for f in files if f != keeper]
    return keeper, to_remove


def find_duplicates(
    directories: List[Path],
    min_size: int = 1,  # ignore 0-byte files in duplicate finder
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> List[DuplicateGroup]:
    """Finds exact duplicates across given directories using 3-stage filtering."""
    # Stage 1: Size grouping
    size_groups: Dict[int, List[Path]] = defaultdict(list)
    scanned = 0

    for d in directories:
        for f in walk_files(d):
            scanned += 1
            if progress_callback and scanned % 100 == 0:
                progress_callback(f"Cataloging: {f.name}", scanned)
            try:
                sz = f.stat().st_size
                if sz >= min_size:
                    size_groups[sz].append(f)
            except Exception:
                continue

    # Filter out unique sizes
    candidate_sizes = {sz: paths for sz, paths in size_groups.items() if len(paths) > 1}

    # Stage 2: Fast head/tail fingerprint
    fp_groups: Dict[Tuple[int, str], List[Path]] = defaultdict(list)
    fp_count = 0
    for sz, paths in candidate_sizes.items():
        for p in paths:
            fp_count += 1
            if progress_callback and fp_count % 50 == 0:
                progress_callback(f"Probing: {p.name}", fp_count)
            fp = fast_fingerprint(p)
            if fp:
                fp_groups[(sz, fp)].append(p)

    candidate_fps = {k: paths for k, paths in fp_groups.items() if len(paths) > 1}

    # Stage 3: Full SHA-256 confirmation
    hash_groups: Dict[Tuple[int, str], List[Path]] = defaultdict(list)
    hash_count = 0
    for (sz, _), paths in candidate_fps.items():
        for p in paths:
            hash_count += 1
            if progress_callback and hash_count % 20 == 0:
                progress_callback(f"Hashing: {p.name}", hash_count)
            sha = full_sha256(p)
            if sha:
                hash_groups[(sz, sha)].append(p)

    dupe_groups = []
    for (sz, sha), paths in hash_groups.items():
        if len(paths) > 1:
            dupe_groups.append(DuplicateGroup(sha256=sha, size=sz, files=paths))

    # Sort largest wasted space first
    dupe_groups.sort(key=lambda g: g.size * (len(g.files) - 1), reverse=True)
    return dupe_groups


def delete_duplicates(
    dupe_groups: List[DuplicateGroup],
    strategy: str = "cleanest",
    use_trash: bool = True,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Prunes duplicate files according to strategy.

    Returns: (removed_count, freed_bytes)
    """
    removed_count = 0
    freed_bytes = 0

    for group in dupe_groups:
        keeper, to_remove = pick_keeper(group.files, strategy=strategy)
        for f in to_remove:
            if not dry_run:
                try:
                    if use_trash:
                        send2trash.send2trash(str(f))
                    else:
                        f.unlink()
                except Exception:
                    continue
            removed_count += 1
            freed_bytes += group.size

    return removed_count, freed_bytes
