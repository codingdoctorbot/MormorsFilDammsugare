"""Media metadata reader: EXIF, QuickTime/MP4, and date/GPS resolution.

Ported and enhanced from Mormorskopiadammsugare (PhotoSorter.Core.Metadata).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import os
import re
import struct

from PIL import ExifTags, Image

# Oldest accepted year for personal photos/videos
MIN_YEAR = 1950


@dataclass(frozen=True)
class MediaMetadata:
    date_taken: Optional[datetime]
    date_source: str  # Exif | QuickTime | FileName | FolderName | FileTime | Unknown
    latitude: Optional[float]
    longitude: Optional[float]
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None

    @property
    def year(self) -> Optional[int]:
        return self.date_taken.year if self.date_taken else None


# Date Regex Patterns
_RE_SEPARATED = re.compile(r"(?<!\d)(?P<y>(?:19|20)\d\d)[-_. ](?P<m>0[1-9]|1[0-2])[-_. ](?P<d>0[1-9]|[12]\d|3[01])(?!\d)")
_RE_COMPACT = re.compile(r"(?<!\d)(?P<y>(?:19|20)\d\d)(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])(?!\d)")
_RE_YEAR_TOKEN = re.compile(r"(?<!\d)(?:19|20)\d\d(?!\d)")
_RE_BACKUP_FOLDER = re.compile(r"back\s*-?\s*up|s[äa]kerhetskopi|time\s*machine|\bbak\b", re.IGNORECASE)


def is_plausible_year(year: int, now_year: int) -> bool:
    return MIN_YEAR <= year <= now_year


def is_plausible_metadata_date(dt: datetime, now: datetime) -> bool:
    if not is_plausible_year(dt.year, now.year) or dt > now:
        return False
    # Camera clock reset epochs
    if dt.month == 1 and dt.day == 1 and dt.year in (1904, 1970, 1980):
        return False
    if dt.month == 1 and dt.day == 1 and dt.hour == 0 and dt.minute < 10 and dt.year <= 2010:
        return False
    return True


def try_parse_filename_date(filename_no_ext: str, now: datetime) -> Optional[datetime]:
    """Parse date from common camera filename conventions."""
    for regex in (_RE_SEPARATED, _RE_COMPACT):
        for m in regex.finditer(filename_no_ext):
            try:
                y = int(m.group("y"))
                mo = int(m.group("m"))
                d = int(m.group("d"))
                dt = datetime(y, mo, d)
                if is_plausible_metadata_date(dt, now):
                    return dt
            except ValueError:
                continue
    return None


def nearest_folder_year(filepath: Path, now_year: int) -> Optional[int]:
    """Find a 4-digit year in the closest parent folder (skipping backup names)."""
    for parent in filepath.parents:
        name = parent.name
        if not name or name == "/":
            break
        if _RE_BACKUP_FOLDER.search(name):
            continue
        for m in _RE_YEAR_TOKEN.finditer(name):
            y = int(m.group(0))
            if is_plausible_year(y, now_year):
                return y
    return None


def _parse_dms(dms_tuple, ref: str) -> Optional[float]:
    """Convert EXIF degrees, minutes, seconds tuple to decimal degrees."""
    try:
        deg = float(dms_tuple[0])
        minutes = float(dms_tuple[1])
        seconds = float(dms_tuple[2])
        dec = deg + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            dec = -dec
        return dec
    except (TypeError, IndexError, ValueError, ZeroDivisionError):
        return None


def read_image_metadata(filepath: Path, now: Optional[datetime] = None) -> MediaMetadata:
    """Read EXIF metadata from photo formats using Pillow."""
    if now is None:
        now = datetime.now()

    dt_taken: Optional[datetime] = None
    date_source = "Unknown"
    lat: Optional[float] = None
    lon: Optional[float] = None
    make: Optional[str] = None
    model: Optional[str] = None

    try:
        with Image.open(filepath) as img:
            exif = img.getexif()
            if exif:
                # Basic tags
                make = exif.get(ExifTags.Base.Make)
                model = exif.get(ExifTags.Base.Model)

                # Date parsing
                # 36867 = DateTimeOriginal, 36868 = DateTimeDigitized, 306 = DateTime
                exif_dates = []
                for tag_id, src_name in ((36867, "Exif"), (36868, "Exif"), (306, "ExifModified")):
                    val = exif.get(tag_id)
                    if val and isinstance(val, str):
                        try:
                            # Format: 'YYYY:MM:DD HH:MM:SS'
                            d = datetime.strptime(val[:19], "%Y:%m:%d %H:%M:%S")
                            if is_plausible_metadata_date(d, now):
                                exif_dates.append((d, src_name))
                        except ValueError:
                            pass

                # Also inspect Exif IFD if present
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                if exif_ifd:
                    for tag_id, src_name in ((36867, "Exif"), (36868, "Exif")):
                        val = exif_ifd.get(tag_id)
                        if val and isinstance(val, str):
                            try:
                                d = datetime.strptime(val[:19], "%Y:%m:%d %H:%M:%S")
                                if is_plausible_metadata_date(d, now):
                                    exif_dates.append((d, src_name))
                            except ValueError:
                                pass

                # Select best date (Exif > ExifModified)
                exif_dates.sort(key=lambda x: 0 if x[1] == "Exif" else 1)
                if exif_dates:
                    dt_taken, date_source = exif_dates[0]

                # GPS IFD (34853)
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_ifd:
                    gps_lat = gps_ifd.get(2)
                    lat_ref = gps_ifd.get(1, "N")
                    gps_lon = gps_ifd.get(4)
                    lon_ref = gps_ifd.get(3, "E")
                    if gps_lat and gps_lon:
                        lat = _parse_dms(gps_lat, lat_ref)
                        lon = _parse_dms(gps_lon, lon_ref)
    except Exception:
        pass

    # Fallbacks if no trusted EXIF date
    if not dt_taken or date_source == "ExifModified":
        from_name = try_parse_filename_date(filepath.stem, now)
        if from_name:
            dt_taken = from_name
            date_source = "FileName"
        else:
            folder_yr = nearest_folder_year(filepath, now.year)
            if folder_yr:
                dt_taken = datetime(folder_yr, 1, 1)
                date_source = "FolderName"

    return MediaMetadata(
        date_taken=dt_taken,
        date_source=date_source,
        latitude=lat,
        longitude=lon,
        camera_make=str(make).strip() if make else None,
        camera_model=str(model).strip() if model else None,
    )


def read_video_metadata(filepath: Path, now: Optional[datetime] = None) -> MediaMetadata:
    """Read creation time and GPS from MP4/MOV atoms in pure Python."""
    if now is None:
        now = datetime.now()

    dt_taken: Optional[datetime] = None
    date_source = "Unknown"
    lat: Optional[float] = None
    lon: Optional[float] = None

    try:
        with open(filepath, "rb") as f:
            # Look for 'moov' atom in first 2MB or so
            buffer = f.read(2 * 1024 * 1024)

            # mvhd (Movie Header): contains creation_time
            idx = buffer.find(b"mvhd")
            if idx > 4:
                # 4 bytes size, 4 bytes 'mvhd', 1 byte version
                version = buffer[idx + 4]
                if version == 0:
                    creation_time = struct.unpack(">I", buffer[idx + 8 : idx + 12])[0]
                else:
                    creation_time = struct.unpack(">Q", buffer[idx + 8 : idx + 16])[0]
                # MP4 epoch is 1904-01-01
                if creation_time > 0:
                    epoch_offset = 2082844800  # seconds between 1904-01-01 and 1970-01-01
                    ts = creation_time - epoch_offset
                    if ts > 0:
                        d = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                        if is_plausible_metadata_date(d, now):
                            dt_taken = d
                            date_source = "QuickTime"

            # ISO 6709 coordinates in user data (e.g. "+59.3293+018.0686/")
            # Search for pattern: +DD.DDDD+DDD.DDDD/
            match = re.search(rb"([+-]\d{2,3}\.\d{4,})([+-]\d{2,3}\.\d{4,})", buffer)
            if match:
                try:
                    c_lat = float(match.group(1))
                    c_lon = float(match.group(2))
                    if abs(c_lat) <= 90 and abs(c_lon) <= 180 and not (abs(c_lat) < 1e-4 and abs(c_lon) < 1e-4):
                        lat, lon = c_lat, c_lon
                except ValueError:
                    pass
    except Exception:
        pass

    # Fallbacks if no video metadata
    if not dt_taken:
        from_name = try_parse_filename_date(filepath.stem, now)
        if from_name:
            dt_taken = from_name
            date_source = "FileName"
        else:
            folder_yr = nearest_folder_year(filepath, now.year)
            if folder_yr:
                dt_taken = datetime(folder_yr, 1, 1)
                date_source = "FolderName"

    return MediaMetadata(
        date_taken=dt_taken,
        date_source=date_source,
        latitude=lat,
        longitude=lon,
    )


def read_metadata(filepath: Path, is_video: bool = False, now: Optional[datetime] = None) -> MediaMetadata:
    """Unified entry point for reading media metadata."""
    if is_video or filepath.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv", ".3gp", ".m4v"):
        return read_video_metadata(filepath, now=now)
    return read_image_metadata(filepath, now=now)
