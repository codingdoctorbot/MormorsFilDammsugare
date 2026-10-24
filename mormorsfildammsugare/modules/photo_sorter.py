"""Module 1: Photo & Video Organizer (Mormorskopiadammsugare Engine).

Extracts unique photos and videos from backup piles, deduplicates via SHA-256,
resolves GPS to Continent/Country/Region, and organizes into a structured directory tree.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
import os
import shutil

from ..catalog.db import CatalogDb, CatalogItem
from ..core.hasher import full_sha256
from ..core.sniffer import MediaCategory, sniff_file
from ..core.walker import walk_files
from ..geo.locator import ContinentLocator, GeoMatch
from ..media.metadata import read_metadata


@dataclass
class PhotoSorterOptions:
    source_dirs: List[Path]
    dest_dir: Path
    layout: str = "continent_year"  # continent_year | country_year | region_year
    is_move: bool = False
    dry_run: bool = False
    use_file_times: bool = False


@dataclass
class PhotoSorterStats:
    total_scanned: int = 0
    photos_processed: int = 0
    videos_processed: int = 0
    duplicates_skipped: int = 0
    bytes_transferred: int = 0
    originals_removed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def sanitize_filename(base_name: str, max_len: int = 120) -> str:
    """Sanitize base file name for safe filesystem usage."""
    invalid_chars = '<>:"/\\|?*\0'
    cleaned = "".join("_" if c in invalid_chars or ord(c) < 32 else c for c in base_name)
    cleaned = cleaned.strip().rstrip(".")
    if not cleaned:
        cleaned = "unnamed"
    return cleaned[:max_len].strip()


def resolve_unique_dest_path(dest_folder: Path, base_name: str, ext: str) -> Path:
    """Find a non-colliding destination path: name.ext, name (2).ext, etc."""
    safe_base = sanitize_filename(base_name)
    target = dest_folder / f"{safe_base}{ext}"
    if not target.exists():
        return target

    counter = 2
    while True:
        target = dest_folder / f"{safe_base} ({counter}){ext}"
        if not target.exists():
            return target
        counter += 1


class PhotoSorter:
    """The Photo & Video Sorter Engine."""

    def __init__(self, options: PhotoSorterOptions):
        self.options = options
        self.geo = ContinentLocator.get_default()

    def organize(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> PhotoSorterStats:
        dest_dir = self.options.dest_dir.resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        catalog_path = dest_dir / "_MormorsFilDammsugare" / "catalog.db"
        catalog = CatalogDb(catalog_path)

        run_id = catalog.start_run(
            run_type="photos",
            source_dir=";".join(str(s) for s in self.options.source_dirs),
            dest_dir=str(dest_dir),
            is_move=self.options.is_move,
        )

        stats = PhotoSorterStats()
        now = datetime.now()

        # Track existing SHA-256 within the run and catalog
        seen_hashes: Set[str] = set()

        for source_root in self.options.source_dirs:
            src_path = source_root.resolve()
            if not src_path.exists():
                continue

            for file_path in walk_files(src_path):
                # Never scan destination if it lives inside source
                try:
                    if file_path.is_relative_to(dest_dir):
                        continue
                except ValueError:
                    pass

                stats.total_scanned += 1
                if progress_callback and stats.total_scanned % 50 == 0:
                    progress_callback(file_path.name, stats.total_scanned)

                # Check format
                sniff_res = sniff_file(file_path)
                if sniff_res.category not in (MediaCategory.PHOTO, MediaCategory.VIDEO):
                    continue

                is_video = sniff_res.category == MediaCategory.VIDEO

                # Calculate SHA-256 for true deduplication
                sha = full_sha256(file_path)
                if not sha:
                    stats.errors.append(f"Failed to hash: {file_path}")
                    continue

                # Deduplication check
                existing_record = catalog.get_existing_by_sha256(sha)
                if sha in seen_hashes or existing_record is not None:
                    stats.duplicates_skipped += 1
                    # In move mode: remove redundant duplicate original if safely kept
                    if self.options.is_move and not self.options.dry_run:
                        try:
                            st = file_path.stat()
                            file_size = st.st_size
                            mtime_utc = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                            dest_path = existing_record["dest_path"] if existing_record else "already_extracted"
                            file_path.unlink()
                            catalog.record_removed_source(run_id, str(file_path), dest_path, sha, file_size, mtime_utc)
                            stats.originals_removed += 1
                        except Exception as e:
                            stats.errors.append(f"Failed to remove duplicate original {file_path}: {e}")
                    continue

                # First time seeing this content
                seen_hashes.add(sha)
                try:
                    st = file_path.stat()
                    file_size = st.st_size
                    src_mtime = st.st_mtime
                except Exception:
                    continue

                # Read EXIF & GPS
                meta = read_metadata(file_path, is_video=is_video, now=now)

                # Resolve GPS to Location
                geo_match: Optional[GeoMatch] = None
                if meta.latitude is not None and meta.longitude is not None:
                    geo_match = self.geo.locate(meta.latitude, meta.longitude)

                # Resolve Directory Layout
                # 1. Location Tier
                if geo_match:
                    continent = geo_match.continent
                    if self.options.layout == "country_year" and geo_match.country_name:
                        loc_folder = Path(continent) / geo_match.country_name
                    elif self.options.layout == "region_year" and geo_match.country_name:
                        if geo_match.region:
                            loc_folder = Path(continent) / geo_match.country_name / geo_match.region
                        else:
                            loc_folder = Path(continent) / geo_match.country_name
                    else:
                        loc_folder = Path(continent)
                else:
                    loc_folder = Path("_Unknown location")

                # 2. Year Tier
                if meta.year:
                    year_folder = str(meta.year)
                else:
                    year_folder = "_Unknown year"

                target_folder = dest_dir / loc_folder / year_folder
                target_folder.mkdir(parents=True, exist_ok=True)

                canonical_ext = sniff_res.canonical_ext or file_path.suffix.lower()
                final_dest_path = resolve_unique_dest_path(target_folder, file_path.stem, canonical_ext)

                if not self.options.dry_run:
                    # Atomic transfer via .partial
                    partial_path = final_dest_path.with_suffix(final_dest_path.suffix + ".partial")
                    try:
                        shutil.copy2(file_path, partial_path)
                        # Verify copied bytes
                        copy_sha = full_sha256(partial_path)
                        if copy_sha != sha:
                            partial_path.unlink(missing_ok=True)
                            stats.errors.append(f"Corrupt copy during transfer: {file_path}")
                            continue

                        partial_path.rename(final_dest_path)
                        # Preserve source mtime
                        os.utime(final_dest_path, (src_mtime, src_mtime))

                        # Record in catalog
                        cat_item = CatalogItem(
                            sha256=sha,
                            size=file_size,
                            dest_path=str(final_dest_path),
                            category=sniff_res.category.value,
                            format_name=sniff_res.format_name,
                            date_taken=meta.date_taken.isoformat() if meta.date_taken else None,
                            date_source=meta.date_source,
                            latitude=meta.latitude,
                            longitude=meta.longitude,
                            continent=geo_match.continent if geo_match else None,
                            country=geo_match.country_name if geo_match else None,
                            region=geo_match.region if geo_match else None,
                        )
                        catalog.add_media(
                            cat_item,
                            source_path=str(file_path),
                            mtime_utc=datetime.fromtimestamp(src_mtime, tz=timezone.utc).isoformat(),
                        )

                        # Move mode: remove original now that copy is verified
                        if self.options.is_move:
                            file_path.unlink()
                            catalog.record_removed_source(
                                run_id,
                                str(file_path),
                                str(final_dest_path),
                                sha,
                                file_size,
                                datetime.fromtimestamp(src_mtime, tz=timezone.utc).isoformat(),
                            )
                            stats.originals_removed += 1
                    except Exception as e:
                        partial_path.unlink(missing_ok=True)
                        stats.errors.append(f"Error copying {file_path}: {e}")
                        continue

                stats.bytes_transferred += file_size
                if is_video:
                    stats.videos_processed += 1
                else:
                    stats.photos_processed += 1

        catalog.finish_run(
            run_id=run_id,
            files_processed=stats.photos_processed + stats.videos_processed,
            duplicates_skipped=stats.duplicates_skipped,
        )
        catalog.close()
        return stats

    @staticmethod
    def restore_originals(dest_dir: Path, progress_callback=None) -> int:
        """Restores removed originals back to their source paths using the catalog."""
        catalog_path = dest_dir / "_MormorsFilDammsugare" / "catalog.db"
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog not found at {catalog_path}")

        catalog = CatalogDb(catalog_path)
        removals = catalog.get_removals_for_restore()

        restored_count = 0
        for row in removals:
            src = Path(row["source_path"])
            dest = Path(row["dest_path"])

            if not dest.exists():
                continue

            src.parent.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                shutil.copy2(dest, src)
                # Restore mtime
                try:
                    mtime_dt = datetime.fromisoformat(row["mtime_utc"])
                    ts = mtime_dt.timestamp()
                    os.utime(src, (ts, ts))
                except Exception:
                    pass
                restored_count += 1
                if progress_callback:
                    progress_callback(src.name, restored_count)

        catalog.close()
        return restored_count
