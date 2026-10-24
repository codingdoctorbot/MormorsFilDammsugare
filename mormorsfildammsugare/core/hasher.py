"""High-performance stream and partial hashing utilities."""

from pathlib import Path
from typing import Optional
import hashlib

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk


def full_sha256(filepath: Path) -> Optional[str]:
    """Calculate full SHA-256 hash of a file with streaming chunks."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def fast_fingerprint(filepath: Path, head_size: int = 65536) -> Optional[str]:
    """Calculate a quick fingerprint from (size + first 64KB + last 64KB).

    Used by the Sampler for rapid duplicate estimation without reading entire files.
    """
    try:
        size = filepath.stat().st_size
        if size <= head_size * 2:
            return full_sha256(filepath)

        h = hashlib.sha256()
        h.update(f"size:{size}:".encode("ascii"))
        with open(filepath, "rb") as f:
            h.update(f.read(head_size))
            f.seek(max(0, size - head_size))
            h.update(f.read(head_size))
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None
