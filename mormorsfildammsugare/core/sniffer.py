"""MIME and content sniffing engine ported and enhanced from PhotoSorter & Arkivslukaren.

Identifies true file types by header bytes (magic numbers) without trusting
unreliable file extensions.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
import zipfile


class MediaCategory(str, Enum):
    PHOTO = "Photo"
    VIDEO = "Video"
    DOCUMENT = "Document"
    ARCHIVE = "Archive"
    AUDIO = "Audio"
    EXECUTABLE = "Executable / Binary"
    CACHE_JUNK = "Cache / Junk"
    OTHER = "Other / Unknown"


@dataclass(frozen=True)
class SniffResult:
    format_name: str
    category: MediaCategory
    canonical_ext: str
    is_weak: bool = False
    details: str = ""


# Header signatures
_JPEG_SIG = b"\xFF\xD8\xFF"
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_GIF87A = b"GIF87a"
_GIF89A = b"GIF89a"
_TIFF_LE = b"II*\x00"
_TIFF_BE = b"MM\x00*"
_RW2_SIG = b"IIU\x00"
_EBML_SIG = b"\x1A\x45\xDF\xA3"  # MKV / WebM
_ASF_SIG = b"\x30\x26\xB2\x75\x8E\x66\xCF\x11"  # WMV / WMA
_MPEG_PS = b"\x00\x00\x01\xBA"
_FLV_SIG = b"FLV\x01"
_PSD_SIG = b"8BPS"
_PDF_SIG = b"%PDF-"
_RTF_SIG = b"{\\rtf"
_ZIP_SIG = b"PK\x03\x04"
_OLE2_SIG = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"  # Legacy DOC, XLS, PPT, MSG
_7Z_SIG = b"7z\xBC\xAF\x27\x1C"
_RAR_SIG = b"Rar!\x1A\x07"
_GZ_SIG = b"\x1F\x8B"
_SQLITE_SIG = b"SQLite format 3\x00"
_ELF_SIG = b"\x7FELF"
_PE_SIG = b"MZ"
_FLAC_SIG = b"fLaC"
_OGG_SIG = b"OggS"


def _sniff_ftyp(header: bytes) -> Optional[SniffResult]:
    """Parse ISO Base Media File Format (ftyp box at offset 4..8)."""
    if len(header) < 12:
        return None
    brand = header[8:12].decode("latin-1", errors="replace").lower()

    # HEIC / AVIF images
    if brand in ("heic", "heix", "heim", "heis", "mif1", "msf1"):
        return SniffResult("HEIC", MediaCategory.PHOTO, ".heic", details=f"brand:{brand}")
    if brand in ("avif", "avis"):
        return SniffResult("AVIF", MediaCategory.PHOTO, ".avif", details=f"brand:{brand}")
    if brand.startswith("crx"):
        return SniffResult("Canon RAW 3", MediaCategory.PHOTO, ".cr3")

    # Audio
    if brand in ("m4a ", "m4b "):
        return SniffResult("M4A Audio", MediaCategory.AUDIO, ".m4a")

    # Videos
    if brand in ("qt  ", "moov"):
        return SniffResult("QuickTime", MediaCategory.VIDEO, ".mov")
    if brand.startswith("3gp"):
        return SniffResult("3GP Video", MediaCategory.VIDEO, ".3gp")
    if brand in ("mp41", "mp42", "isom", "iso2", "m4v ", "dash"):
        return SniffResult("MP4", MediaCategory.VIDEO, ".mp4")

    # Default MP4 container fallback
    return SniffResult("MP4 Container", MediaCategory.VIDEO, ".mp4", is_weak=True, details=f"brand:{brand}")


def _sniff_zip_content(filepath: Path) -> Optional[SniffResult]:
    """Inspect inside a ZIP container to identify OOXML / ODF / EPUB."""
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            names = set(zf.namelist()[:30])

            # Modern Microsoft Office
            if "word/document.xml" in names:
                return SniffResult("Word Document", MediaCategory.DOCUMENT, ".docx")
            if "xl/workbook.xml" in names:
                return SniffResult("Excel Spreadsheet", MediaCategory.DOCUMENT, ".xlsx")
            if "ppt/presentation.xml" in names:
                return SniffResult("PowerPoint Presentation", MediaCategory.DOCUMENT, ".pptx")

            # OpenDocument
            if "mimetype" in names:
                try:
                    with zf.open("mimetype") as mf:
                        mime = mf.read(128).decode("ascii", errors="ignore").strip()
                        if "opendocument.text" in mime:
                            return SniffResult("OpenDocument Text", MediaCategory.DOCUMENT, ".odt")
                        if "opendocument.spreadsheet" in mime:
                            return SniffResult("OpenDocument Spreadsheet", MediaCategory.DOCUMENT, ".ods")
                        if "opendocument.presentation" in mime:
                            return SniffResult("OpenDocument Presentation", MediaCategory.DOCUMENT, ".odp")
                        if "epub" in mime:
                            return SniffResult("EPUB E-Book", MediaCategory.DOCUMENT, ".epub")
                except Exception:
                    pass

            # Anki flashcard deck
            if "collection.anki2" in names or "collection.anki21" in names:
                return SniffResult("Anki Deck", MediaCategory.DOCUMENT, ".apkg")

            return SniffResult("ZIP Archive", MediaCategory.ARCHIVE, ".zip")
    except Exception:
        return SniffResult("ZIP Archive", MediaCategory.ARCHIVE, ".zip")


def sniff_bytes(header: bytes, ext_hint: str = "") -> Optional[SniffResult]:
    """Sniff file type from the leading 512 bytes."""
    if not header:
        return None

    # Photos
    if header.startswith(_JPEG_SIG):
        return SniffResult("JPEG", MediaCategory.PHOTO, ".jpg")
    if header.startswith(_PNG_SIG):
        return SniffResult("PNG", MediaCategory.PHOTO, ".png")
    if header.startswith(_GIF87A) or header.startswith(_GIF89A):
        return SniffResult("GIF", MediaCategory.PHOTO, ".gif")
    if header.startswith(b"BM") and len(header) >= 14:
        return SniffResult("BMP", MediaCategory.PHOTO, ".bmp")
    if header.startswith(_PSD_SIG):
        return SniffResult("Photoshop PSD", MediaCategory.PHOTO, ".psd")

    # TIFF and RAW
    if header.startswith(_TIFF_LE) or header.startswith(_TIFF_BE):
        if len(header) >= 10 and header[8:10] == b"CR":
            return SniffResult("Canon RAW 2", MediaCategory.PHOTO, ".cr2")
        return SniffResult("TIFF", MediaCategory.PHOTO, ".tif")

    if header.startswith((b"IIRO", b"IIRS", b"MMOR")):
        return SniffResult("Olympus RAW", MediaCategory.PHOTO, ".orf")
    if header.startswith(_RW2_SIG):
        return SniffResult("Panasonic RAW", MediaCategory.PHOTO, ".rw2")
    if header.startswith(b"FUJIFILMCCD-RAW"):
        return SniffResult("Fuji RAW", MediaCategory.PHOTO, ".raf")
    if len(header) >= 14 and header[6:14] == b"HEAPCCDR":
        return SniffResult("Canon CRW", MediaCategory.PHOTO, ".crw")
    if header.startswith(b"FOVb"):
        return SniffResult("Sigma RAW", MediaCategory.PHOTO, ".x3f")

    # RIFF formats (WebP, AVI, WAV)
    if header.startswith(b"RIFF") and len(header) >= 12:
        form = header[8:12]
        if form == b"WEBP":
            return SniffResult("WebP", MediaCategory.PHOTO, ".webp")
        if form == b"AVI ":
            return SniffResult("AVI Video", MediaCategory.VIDEO, ".avi")
        if form == b"WAVE":
            return SniffResult("WAV Audio", MediaCategory.AUDIO, ".wav")

    # ISO Base Media File Format (MP4 / MOV / HEIC)
    if len(header) >= 12 and header[4:8] == b"ftyp":
        res = _sniff_ftyp(header)
        if res:
            return res

    # Other Videos
    if header.startswith(_EBML_SIG):
        return SniffResult("MKV / WebM", MediaCategory.VIDEO, ".mkv")
    if header.startswith(_ASF_SIG):
        return SniffResult("WMV Video", MediaCategory.VIDEO, ".wmv")
    if header.startswith(_MPEG_PS):
        return SniffResult("MPEG-PS", MediaCategory.VIDEO, ".mpg")
    if header.startswith(_FLV_SIG):
        return SniffResult("Flash Video", MediaCategory.VIDEO, ".flv")

    # Audio
    if header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
        return SniffResult("MP3 Audio", MediaCategory.AUDIO, ".mp3", is_weak=header.startswith(b"\xFF"))
    if header.startswith(_FLAC_SIG):
        return SniffResult("FLAC Audio", MediaCategory.AUDIO, ".flac")
    if header.startswith(_OGG_SIG):
        return SniffResult("Ogg Media", MediaCategory.AUDIO, ".ogg")

    # Documents
    if header.startswith(_PDF_SIG):
        return SniffResult("PDF Document", MediaCategory.DOCUMENT, ".pdf")
    if header.startswith(_RTF_SIG):
        return SniffResult("RTF Document", MediaCategory.DOCUMENT, ".rtf")

    # OLE2 (Compound File Binary: Legacy Office doc/xls/ppt/msg)
    if header.startswith(_OLE2_SIG):
        hint = ext_hint.lower().lstrip(".")
        if hint == "xls":
            return SniffResult("Legacy Excel", MediaCategory.DOCUMENT, ".xls")
        if hint == "ppt":
            return SniffResult("Legacy PowerPoint", MediaCategory.DOCUMENT, ".ppt")
        if hint == "msg":
            return SniffResult("Outlook Message", MediaCategory.DOCUMENT, ".msg")
        return SniffResult("Legacy Word Document", MediaCategory.DOCUMENT, ".doc")

    # Archives
    if header.startswith(_7Z_SIG):
        return SniffResult("7-Zip Archive", MediaCategory.ARCHIVE, ".7z")
    if header.startswith(_RAR_SIG):
        return SniffResult("RAR Archive", MediaCategory.ARCHIVE, ".rar")
    if header.startswith(_GZ_SIG):
        return SniffResult("GZip Archive", MediaCategory.ARCHIVE, ".gz")

    # Binaries / System
    if header.startswith(_ELF_SIG):
        return SniffResult("Linux ELF Binary", MediaCategory.EXECUTABLE, "")
    if header.startswith(_PE_SIG):
        return SniffResult("Windows Executable", MediaCategory.EXECUTABLE, ".exe")
    if header.startswith(_SQLITE_SIG):
        return SniffResult("SQLite Database", MediaCategory.DOCUMENT, ".db")

    # Plain Text check (ASCII / UTF-8 text with no null bytes in first 512 bytes)
    if b"\x00" not in header[:256]:
        try:
            header[:256].decode("utf-8")
            hint = ext_hint.lower()
            if hint in (".txt", ".csv", ".tsv", ".md", ".json", ".xml", ".yaml", ".yml", ".html", ".css", ".js", ".py", ".sh"):
                return SniffResult("Text Document", MediaCategory.DOCUMENT, hint)
            if hint in (".eml",):
                return SniffResult("Email Message", MediaCategory.DOCUMENT, ".eml")
            return SniffResult("Plain Text", MediaCategory.DOCUMENT, ".txt", is_weak=True)
        except UnicodeDecodeError:
            pass

    return None


def sniff_file(filepath: Path) -> SniffResult:
    """Sniff file content by opening and reading the leading header."""
    ext = filepath.suffix.lower()

    # Fast junk check
    fname = filepath.name.lower()
    if fname in ("thumbs.db", ".ds_store", "desktop.ini") or fname.startswith("._"):
        return SniffResult("System Cache Junk", MediaCategory.CACHE_JUNK, ext)

    try:
        with open(filepath, "rb") as f:
            header = f.read(512)
    except (PermissionError, FileNotFoundError, OSError) as e:
        return SniffResult("Unreadable", MediaCategory.OTHER, ext, details=str(e))

    if not header:
        return SniffResult("Empty File (0 Bytes)", MediaCategory.OTHER, ext)

    # Special handling for ZIP-based formats (need to check table of contents)
    if header.startswith(_ZIP_SIG):
        return _sniff_zip_content(filepath)

    result = sniff_bytes(header, ext_hint=ext)
    if result:
        return result

    # Fallback by extension if binary sniff was inconclusive
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".tif", ".tiff"):
        return SniffResult(f"Image ({ext.upper()})", MediaCategory.PHOTO, ext, is_weak=True)
    if ext in (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".m4v", ".flv"):
        return SniffResult(f"Video ({ext.upper()})", MediaCategory.VIDEO, ext, is_weak=True)
    if ext in (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".md", ".odt", ".ods", ".rtf", ".eml", ".msg"):
        return SniffResult(f"Document ({ext.upper()})", MediaCategory.DOCUMENT, ext, is_weak=True)
    if ext in (".cs", ".py", ".sh", ".json", ".xml", ".yaml", ".yml", ".toml", ".sln", ".slnx", ".props", ".csproj", ".js", ".ts", ".html", ".css", ".lua"):
        return SniffResult(f"Source Code / Config ({ext.upper()})", MediaCategory.DOCUMENT, ext, is_weak=True)
    if ext in (".onnx", ".pt", ".bin", ".tflite", ".gguf"):
        return SniffResult(f"AI Model / Weights ({ext.upper()})", MediaCategory.EXECUTABLE, ext, is_weak=True)
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".dmg"):
        return SniffResult(f"Archive ({ext.upper()})", MediaCategory.ARCHIVE, ext, is_weak=True)
    if ext in (".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus"):
        return SniffResult(f"Audio ({ext.upper()})", MediaCategory.AUDIO, ext, is_weak=True)
    if ext in (".exe", ".dll", ".so", ".dylib"):
        return SniffResult(f"Binary ({ext.upper()})", MediaCategory.EXECUTABLE, ext, is_weak=True)
    if ext in (".tmp", ".bak", ".swp", ".cache", ".chk"):
        return SniffResult("Temporary File", MediaCategory.CACHE_JUNK, ext, is_weak=True)

    return SniffResult("Unknown / Unclassified", MediaCategory.OTHER, ext)
