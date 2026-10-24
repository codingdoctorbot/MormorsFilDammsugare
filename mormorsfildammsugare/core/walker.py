"""Fast recursive filesystem walker with smart exclusion lists."""

from pathlib import Path
from typing import Callable, Generator, Iterable, Optional, Set
import os

DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    "$recycle.bin",
    "system volume information",
    "appdata",
    ".trash",
    ".local/share/trash",
}

DEFAULT_EXCLUDED_FILES: Set[str] = {
    "thumbs.db",
    ".ds_store",
    "desktop.ini",
}


def walk_files(
    root_dir: Path,
    excluded_dirs: Optional[Set[str]] = None,
    excluded_files: Optional[Set[str]] = None,
    follow_symlinks: bool = False,
    on_error: Optional[Callable[[Path, Exception], None]] = None,
) -> Generator[Path, None, None]:
    """Recursively yields file paths under root_dir with high performance using os.scandir."""
    skip_dirs = {d.lower() for d in (excluded_dirs or DEFAULT_EXCLUDED_DIRS)}
    skip_files = {f.lower() for f in (excluded_files or DEFAULT_EXCLUDED_FILES)}

    stack = [os.fspath(root_dir)]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        # Skip symlinks if requested
                        if not follow_symlinks and entry.is_symlink():
                            continue

                        name_lower = entry.name.lower()

                        if entry.is_dir(follow_symlinks=follow_symlinks):
                            if name_lower not in skip_dirs and not name_lower.startswith("."):
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=follow_symlinks):
                            # Skip macOS resource fork files
                            if name_lower.startswith("._") or name_lower in skip_files:
                                continue
                            yield Path(entry.path)
                    except (PermissionError, FileNotFoundError, OSError) as e:
                        if on_error:
                            on_error(Path(entry.path), e)
        except (PermissionError, FileNotFoundError, OSError) as e:
            if on_error:
                on_error(Path(current_dir), e)
