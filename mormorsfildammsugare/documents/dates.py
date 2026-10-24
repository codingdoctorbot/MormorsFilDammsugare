"""Document year resolver.

Ported from Arkivslukaren (DateResolver.cs).
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import os
import re

from .categories import is_backup_folder
from .metadata import DocumentMetadata

MIN_VALID_YEAR = 1970
MAX_VALID_YEAR = datetime.now().year + 1

_RE_DATE_PATTERN = re.compile(
    r"(?:(?<=\D)|^)(199\d|20[0-3]\d)(?:[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01]))?(?=\D|$)"
)


def is_valid_year(year: int) -> bool:
    return MIN_VALID_YEAR <= year <= MAX_VALID_YEAR


def resolve_document_year(
    filepath: Path,
    metadata: DocumentMetadata,
    trust_file_times: bool = False,
    source_root: Optional[Path] = None,
) -> Tuple[Optional[int], str]:
    """Resolve creation year for a document.

    Returns: (year, rule_source)
    """
    # 1. Internal document metadata date
    if metadata.created_date:
        yr = metadata.created_date.year
        if is_valid_year(yr):
            return yr, "Metadata"

    # 2. Filename date pattern
    m = _RE_DATE_PATTERN.search(filepath.stem)
    if m:
        try:
            yr = int(m.group(1))
            if is_valid_year(yr):
                return yr, "Filename"
        except ValueError:
            pass

    # 3. Parent folder path
    curr = filepath.parent
    while curr and curr != curr.parent:
        if source_root and curr == source_root:
            break
        name = curr.name
        if not is_backup_folder(name):
            m = _RE_DATE_PATTERN.search(name)
            if m:
                try:
                    yr = int(m.group(1))
                    if is_valid_year(yr):
                        return yr, "ParentFolder"
                except ValueError:
                    pass
        curr = curr.parent

    # 4. Filesystem timestamps (optional)
    if trust_file_times:
        try:
            st = filepath.stat()
            oldest_ts = min(st.st_ctime, st.st_mtime)
            dt = datetime.fromtimestamp(oldest_ts)
            if is_valid_year(dt.year):
                return dt.year, "FileSystem"
        except Exception:
            pass

    return None, "Unknown"
