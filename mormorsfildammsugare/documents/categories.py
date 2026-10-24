"""Document categorization engine.

Ported from Arkivslukaren (CategoryResolver.cs & PathHints.cs).
"""

from pathlib import Path
from typing import List, Optional, Set, Tuple
import re

from .metadata import DocumentMetadata

# Category folder names
CAT_ECONOMY = "Economy & Finance"
CAT_AGREEMENTS = "Agreements & Legal"
CAT_CAREER = "Personal & Career"
CAT_WORK = "Work & Projects"
CAT_MANUALS = "Manuals & Documentation"
CAT_GENERAL = "General"

_ECONOMY_KW: Set[str] = {
    "faktura", "invoice", "kvitto", "receipt", "deklaration", "moms", "vat", "budget", "lön",
    "salary", "payslip", "kontoutdrag", "bank", "saldo", "kostnad", "expense", "räkning",
    "bokföring", "verifikat", "årsredovisning", "skatteverket", "tax", "kalkyl"
}

_AGREEMENTS_KW: Set[str] = {
    "avtal", "agreement", "kontrakt", "contract", "fullmakt", "intyg", "policy", "sekretess",
    "nda", "terms", "villkor", "lease", "hyresavtal", "köpeavtal", "anställningsavtal",
    "testamente", "licens", "license"
}

_CAREER_KW: Set[str] = {
    "cv", "resume", "meritförteckning", "personligt brev", "betyg", "diploma", "certifikat",
    "certificate", "pass", "körkort", "personbevis", "vaccin"
}

_WORK_KW: Set[str] = {
    "rapport", "report", "protokoll", "minutes", "projektplan", "project", "specifikation",
    "presentation", "offert", "quote", "mötesanteckningar", "agenda", "roadmap"
}

_MANUALS_KW: Set[str] = {
    "manual", "handbok", "handbook", "guide", "bruksanvisning", "instruktion", "instruction",
    "dokumentation", "documentation", "tutorial", "quickstart"
}

_GENERIC_FOLDERS: Set[str] = {
    "desktop", "documents", "dokument", "files", "filer", "backup", "säkerhetskopia",
    "new folder", "ny mapp", "download", "downloads", "c", "d", "e", "f", "users",
    "användare", "documents and settings", "my documents", "mina dokument", "data", "temp"
}

_BACKUP_MARKERS: List[str] = [
    "backup", "back-up", "säkerhetskopi", "sakerhetskopi", "kopia", "copy", "restore", "återställ"
]

_RE_YEAR_ONLY = re.compile(r"^\d{4}([-_. ]\d{1,2}){0,2}$")
_RE_TOKENS = re.compile(r"[ \t\r\n_\-.,;:/\(\)\[\]\"'!\\?]+")


def is_backup_folder(name: str) -> bool:
    name_l = name.lower()
    return any(marker in name_l for marker in _BACKUP_MARKERS)


def sanitize_category_folder(folder: str, max_len: int = 40) -> str:
    """Sanitize contextual folder hint for use as a folder name."""
    invalid_chars = '<>:"/\\|?*\0'
    cleaned = "".join("_" if c in invalid_chars or ord(c) < 32 else c for c in folder)
    cleaned = cleaned.strip().rstrip(". ")
    return cleaned[:max_len].strip()


def match_token(token: str) -> Optional[str]:
    t = token.lower()
    if t in _ECONOMY_KW:
        return CAT_ECONOMY
    if t in _AGREEMENTS_KW:
        return CAT_AGREEMENTS
    if t in _CAREER_KW:
        return CAT_CAREER
    if t in _WORK_KW:
        return CAT_WORK
    if t in _MANUALS_KW:
        return CAT_MANUALS
    return None


def match_text(text: str) -> Optional[str]:
    for token in _RE_TOKENS.split(text):
        if not token:
            continue
        cat = match_token(token)
        if cat:
            return cat
    return None


def resolve_category(filepath: Path, metadata: DocumentMetadata, source_root: Optional[Path] = None) -> Tuple[str, str]:
    """Resolve subcategory folder name and rule source.

    Returns: (category_folder_name, source_rule)
    """
    # 1. Metadata title
    if metadata.title:
        cat = match_text(metadata.title)
        if cat:
            return cat, "MetadataTitle"

    # 2. Metadata subject
    if metadata.subject:
        cat = match_text(metadata.subject)
        if cat:
            return cat, "MetadataSubject"

    # 3. Metadata keywords
    for kw in metadata.keywords:
        cat = match_token(kw)
        if cat:
            return cat, "MetadataKeywords"

    # 4. Sheet names (spreadsheets)
    for sheet in metadata.sheet_names:
        cat = match_text(sheet)
        if cat:
            return cat, "SheetName"

    # 5. Filename
    cat = match_text(filepath.stem)
    if cat:
        return cat, "Filename"

    # 6. Text content sample
    if metadata.text_sample:
        cat = match_text(metadata.text_sample)
        if cat:
            return cat, "ContentText"

    # 7. Parent folder hints below source_root (up to depth 2)
    parents = []
    curr = filepath.parent
    while curr and curr != curr.parent:
        if source_root and curr == source_root:
            break
        parents.append(curr.name)
        curr = curr.parent

    for seg in parents[:2]:
        s = seg.strip()
        s_l = s.lower()
        if not s or len(s) <= 1 or s_l in _GENERIC_FOLDERS or is_backup_folder(s) or _RE_YEAR_ONLY.match(s):
            continue

        # Check if folder name contains category keywords
        cat = match_text(s)
        if cat:
            return cat, "FolderKeyword"

        # Otherwise, preserve the folder name as contextual subcategory
        sanitized = sanitize_category_folder(s)
        if sanitized:
            return sanitized, "FolderHint"

    # 8. Fallback
    return CAT_GENERAL, "Default"
