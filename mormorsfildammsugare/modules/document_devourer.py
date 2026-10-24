"""Module 2: Document Devourer (Arkivslukaren Engine).

Extracts unique documents, ebooks, emails, and archives from backup piles,
deduplicates via SHA-256, and organizes them into:
<Destination> / <FileFormat> / <YearCreated> / <Category> / <Filename>
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
from ..documents.categories import resolve_category
from ..documents.dates import resolve_document_year
from ..documents.metadata import extract_document_metadata
from .photo_sorter import resolve_unique_dest_path

STANDARD_DOC_EXTENSIONS: Set[str] = {
    ".pdf",
    ".docx", ".doc",
    ".xlsx", ".xls",
    ".pptx", ".ppt",
    ".odt", ".ods", ".odp",
    ".rtf",
    ".txt", ".csv", ".tsv", ".md",
    ".eml", ".msg",
    ".docm", ".dotx", ".dotm", ".xlsm", ".xlsb", ".xltx", ".xltm", ".pptm", ".potx", ".ppsx",
    ".pages", ".numbers", ".key",
    ".epub", ".mobi", ".azw", ".azw3",
    ".apkg", ".colpkg",
    ".zip", ".dmg",
}


@dataclass
class DocumentDevourerOptions:
    source_dirs: List[Path]
    dest_dir: Path
    extract_all_formats: bool = False
    trust_file_times: bool = False
    is_move: bool = False
    dry_run: bool = False


@dataclass
class DocumentDevourerStats:
    total_scanned: int = 0
    documents_processed: int = 0
    duplicates_skipped: int = 0
    bytes_transferred: int = 0
    originals_removed: int = 0
    category_counts: Dict[str, int] = None
    format_counts: Dict[str, int] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.category_counts is None:
            self.category_counts = {}
        if self.format_counts is None:
            self.format_counts = {}
        if self.errors is None:
            self.errors = []


class DocumentDevourer:
    """The Document Devourer Engine."""

    def __init__(self, options: DocumentDevourerOptions):
        self.options = options

    def devour(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> DocumentDevourerStats:
        dest_dir = self.options.dest_dir.resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        catalog_path = dest_dir / "_MormorsFilDammsugare" / "catalog.db"
        catalog = CatalogDb(catalog_path)

        run_id = catalog.start_run(
            run_type="docs",
            source_dir=";".join(str(s) for s in self.options.source_dirs),
            dest_dir=str(dest_dir),
            is_move=self.options.is_move,
        )

        stats = DocumentDevourerStats()
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

                ext = file_path.suffix.lower()
                sniff_res = sniff_file(file_path)

                # Filter documents / archives
                is_standard = ext in STANDARD_DOC_EXTENSIONS or sniff_res.category in (
                    MediaCategory.DOCUMENT,
                    MediaCategory.ARCHIVE,
                )
                if not is_standard and not self.options.extract_all_formats:
                    continue

                # Skip obvious media/binaries/caches unless specifically sniffing as a doc
                if sniff_res.category in (MediaCategory.PHOTO, MediaCategory.VIDEO, MediaCategory.EXECUTABLE, MediaCategory.CACHE_JUNK):
                    continue

                # Deduplication via SHA-256
                sha = full_sha256(file_path)
                if not sha:
                    stats.errors.append(f"Failed to hash: {file_path}")
                    continue

                existing_record = catalog.get_existing_by_sha256(sha)
                if sha in seen_hashes or existing_record is not None:
                    stats.duplicates_skipped += 1
                    if self.options.is_move and not self.options.dry_run:
                        try:
                            st = file_path.stat()
                            file_size = st.st_size
                            mtime_utc = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
                            dest_p = existing_record["dest_path"] if existing_record else "already_extracted"
                            file_path.unlink()
                            catalog.record_removed_source(run_id, str(file_path), dest_p, sha, file_size, mtime_utc)
                            stats.originals_removed += 1
                        except Exception as e:
                            stats.errors.append(f"Failed to remove duplicate original {file_path}: {e}")
                    continue

                seen_hashes.add(sha)
                try:
                    st = file_path.stat()
                    file_size = st.st_size
                    src_mtime = st.st_mtime
                except Exception:
                    continue

                # Extract document metadata
                meta = extract_document_metadata(file_path)

                # 1. Format Tier (Uppercase extension)
                canonical_ext = sniff_res.canonical_ext or ext
                format_tier = canonical_ext.lstrip(".").upper() if canonical_ext else "OTHER"

                # 2. Year Tier
                year, year_source = resolve_document_year(
                    file_path,
                    meta,
                    trust_file_times=self.options.trust_file_times,
                    source_root=src_path,
                )
                year_tier = str(year) if year else "_Unknown year"

                # 3. Category Tier
                cat_tier, cat_source = resolve_category(file_path, meta, source_root=src_path)

                # Target directory
                target_folder = dest_dir / format_tier / year_tier / cat_tier
                target_folder.mkdir(parents=True, exist_ok=True)

                final_dest_path = resolve_unique_dest_path(target_folder, file_path.stem, canonical_ext)

                if not self.options.dry_run:
                    partial_path = final_dest_path.with_suffix(final_dest_path.suffix + ".partial")
                    try:
                        shutil.copy2(file_path, partial_path)
                        copy_sha = full_sha256(partial_path)
                        if copy_sha != sha:
                            partial_path.unlink(missing_ok=True)
                            stats.errors.append(f"Corrupt copy during transfer: {file_path}")
                            continue

                        partial_path.rename(final_dest_path)
                        os.utime(final_dest_path, (src_mtime, src_mtime))

                        cat_item = CatalogItem(
                            sha256=sha,
                            size=file_size,
                            dest_path=str(final_dest_path),
                            category=cat_tier,
                            format_name=format_tier,
                            date_taken=str(year) if year else None,
                            date_source=year_source,
                            latitude=None,
                            longitude=None,
                            continent=None,
                            country=None,
                            region=None,
                        )
                        catalog.add_media(
                            cat_item,
                            source_path=str(file_path),
                            mtime_utc=datetime.fromtimestamp(src_mtime, tz=timezone.utc).isoformat(),
                        )

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
                stats.documents_processed += 1
                stats.category_counts[cat_tier] = stats.category_counts.get(cat_tier, 0) + 1
                stats.format_counts[format_tier] = stats.format_counts.get(format_tier, 0) + 1

        catalog.finish_run(
            run_id=run_id,
            files_processed=stats.documents_processed,
            duplicates_skipped=stats.duplicates_skipped,
        )
        catalog.close()
        return stats
