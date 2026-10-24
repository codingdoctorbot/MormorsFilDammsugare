"""Module 0: File Dump Sampler & Survey Inspector (Provtagaren).

Quickly analyzes a chaotic folder/drive dump and produces a statistical breakdown
of formats, true binary identities, size distribution, and duplicate estimates.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time

from ..core.hasher import fast_fingerprint
from ..core.sniffer import MediaCategory, SniffResult, sniff_file
from ..core.walker import walk_files


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


@dataclass
class ExtensionMismatch:
    path: Path
    actual_ext: str
    detected_format: str
    detected_ext: str
    size: int


@dataclass
class SurveyStats:
    target_path: Path
    scan_time_seconds: float = 0.0
    total_files: int = 0
    total_bytes: int = 0
    total_folders: int = 0

    # Categorization
    category_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    category_bytes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Format Breakdown
    format_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    format_bytes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Size Histogram
    size_buckets: Dict[str, int] = field(default_factory=lambda: {
        "Tiny (< 10 KB)": 0,
        "Small (10 KB - 1 MB)": 0,
        "Medium (1 MB - 25 MB)": 0,
        "Large (25 MB - 500 MB)": 0,
        "Giant (> 500 MB)": 0,
    })
    size_bucket_bytes: Dict[str, int] = field(default_factory=lambda: {
        "Tiny (< 10 KB)": 0,
        "Small (10 KB - 1 MB)": 0,
        "Medium (1 MB - 25 MB)": 0,
        "Large (25 MB - 500 MB)": 0,
        "Giant (> 500 MB)": 0,
    })

    # Mismatches & Disguised Files
    mismatches: List[ExtensionMismatch] = field(default_factory=list)
    unreadable_files: List[Tuple[Path, str]] = field(default_factory=list)
    zero_byte_files: int = 0

    # Duplicate Estimates
    estimated_duplicate_files: int = 0
    estimated_wasted_bytes: int = 0


class FileSampler:
    """The File Dump Sampler & Survey Inspector."""

    def __init__(self, check_duplicates: bool = True):
        self.check_duplicates = check_duplicates

    def survey(self, target_dir: Path, progress_callback=None) -> SurveyStats:
        start_time = time.time()
        stats = SurveyStats(target_path=target_dir)

        # Collect for duplicate analysis: size -> list of paths
        size_groups: Dict[int, List[Path]] = defaultdict(list)

        scanned = 0
        for file_path in walk_files(target_dir):
            scanned += 1
            if progress_callback and scanned % 100 == 0:
                progress_callback(scanned)

            try:
                st = file_path.stat()
                file_size = st.st_size
            except (PermissionError, FileNotFoundError, OSError):
                stats.unreadable_files.append((file_path, "Permission denied / cannot stat"))
                continue

            stats.total_files += 1
            stats.total_bytes += file_size

            # Size buckets
            if file_size == 0:
                stats.zero_byte_files += 1
                bkey = "Tiny (< 10 KB)"
            elif file_size < 10 * 1024:
                bkey = "Tiny (< 10 KB)"
            elif file_size < 1024 * 1024:
                bkey = "Small (10 KB - 1 MB)"
            elif file_size < 25 * 1024 * 1024:
                bkey = "Medium (1 MB - 25 MB)"
            elif file_size < 500 * 1024 * 1024:
                bkey = "Large (25 MB - 500 MB)"
            else:
                bkey = "Giant (> 500 MB)"

            stats.size_buckets[bkey] += 1
            stats.size_bucket_bytes[bkey] += file_size

            # Content Sniffing
            sniff_res = sniff_file(file_path)
            cat_name = sniff_res.category.value
            fmt_name = sniff_res.format_name

            stats.category_counts[cat_name] += 1
            stats.category_bytes[cat_name] += file_size
            stats.format_counts[fmt_name] += 1
            stats.format_bytes[fmt_name] += file_size

            # Check for extension mismatches (ignoring weak sniffs)
            ext = file_path.suffix.lower()
            if (
                not sniff_res.is_weak
                and sniff_res.canonical_ext
                and ext != sniff_res.canonical_ext
                and ext not in (".jpeg", ".jpe")  # common synonym
                and sniff_res.category != MediaCategory.CACHE_JUNK
            ):
                stats.mismatches.append(
                    ExtensionMismatch(
                        path=file_path,
                        actual_ext=ext,
                        detected_format=sniff_res.format_name,
                        detected_ext=sniff_res.canonical_ext,
                        size=file_size,
                    )
                )

            # Store for duplicate heuristics (only files >= 1 KB)
            if self.check_duplicates and file_size >= 1024:
                size_groups[file_size].append(file_path)

        # Duplicate estimation
        if self.check_duplicates:
            potential_dupes = {sz: paths for sz, paths in size_groups.items() if len(paths) > 1}
            for sz, paths in potential_dupes.items():
                # Hash sample fingerprints
                fingerprints = defaultdict(list)
                for p in paths:
                    fp = fast_fingerprint(p)
                    if fp:
                        fingerprints[fp].append(p)
                for fp, dupe_group in fingerprints.items():
                    if len(dupe_group) > 1:
                        redundant_count = len(dupe_group) - 1
                        stats.estimated_duplicate_files += redundant_count
                        stats.estimated_wasted_bytes += redundant_count * sz

        stats.scan_time_seconds = time.time() - start_time
        return stats
