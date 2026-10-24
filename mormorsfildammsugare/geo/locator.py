"""Offline GPS -> country -> continent lookup over Natural Earth polygons.

Ported from Mormorskopiadammsugare (PhotoSorter.Core.Geo.ContinentLocator).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gzip
import math
import struct


@dataclass(frozen=True)
class GeoMatch:
    continent: str
    country_code: str
    country_name: str
    distance_km: float = 0.0
    region_code: Optional[str] = None
    region: Optional[str] = None


class _Part:
    __slots__ = (
        "country_code",
        "country_name",
        "continent",
        "rings",
        "min_lon",
        "max_lon",
        "min_lat",
        "max_lat",
    )

    def __init__(self, code: str, name: str, continent: str, rings: List[List[float]]):
        self.country_code = code
        self.country_name = name
        self.continent = continent
        self.rings = rings
        min_lon = min_lat = float("inf")
        max_lon = max_lat = float("-inf")
        for ring in rings:
            for i in range(0, len(ring), 2):
                lon, lat = ring[i], ring[i + 1]
                if lon < min_lon:
                    min_lon = lon
                if lon > max_lon:
                    max_lon = lon
                if lat < min_lat:
                    min_lat = lat
                if lat > max_lat:
                    max_lat = lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.min_lat = min_lat
        self.max_lat = max_lat

    def box_contains(self, lon: float, lat: float) -> bool:
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat

    def contains(self, lon: float, lat: float) -> bool:
        """Even-odd ray casting over interleaved (lon, lat) pairs."""
        inside = False
        for ring in self.rings:
            n = len(ring) // 2
            j = n - 1
            for i in range(n):
                xi, yi = ring[2 * i], ring[2 * i + 1]
                xj, yj = ring[2 * j], ring[2 * j + 1]
                if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
        return inside


class ContinentLocator:
    """Offline GPS to Continent / Country / Region locator."""

    COASTAL_TOLERANCE_KM = 200.0

    _instance: Optional["ContinentLocator"] = None

    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = Path(__file__).parent / "countries.gz"

        self.parts: List[_Part] = []
        self.regions: Dict[str, List[_Part]] = {}
        self._load(data_path)
        # Sort small boxes first for faster early exits
        self.parts.sort(key=lambda p: (p.max_lon - p.min_lon) * (p.max_lat - p.min_lat))

    @classmethod
    def get_default(cls) -> "ContinentLocator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self, path: Path):
        with gzip.open(path, "rb") as f:
            magic = f.read(6)
            if magic != b"PSGEO3":
                raise ValueError(f"Invalid geo file signature: {magic}")

            def read_str() -> str:
                b = f.read(1)[0]
                length = b & 0x7F
                shift = 7
                while b & 0x80:
                    b = f.read(1)[0]
                    length |= (b & 0x7F) << shift
                    shift += 7
                return f.read(length).decode("utf-8", errors="replace")

            def read_rings() -> List[List[float]]:
                ring_count = struct.unpack("<i", f.read(4))[0]
                rings = []
                for _ in range(ring_count):
                    pt_count = struct.unpack("<i", f.read(4))[0]
                    floats = struct.unpack(f"<{pt_count * 2}f", f.read(pt_count * 8))
                    rings.append(list(floats))
                return rings

            n_continents = struct.unpack("<i", f.read(4))[0]
            continents = [read_str() for _ in range(n_continents)]

            n_countries = struct.unpack("<i", f.read(4))[0]
            for _ in range(n_countries):
                country_code = read_str()
                country_name = read_str()
                n_parts = struct.unpack("<i", f.read(4))[0]
                for _ in range(n_parts):
                    cont_idx = f.read(1)[0]
                    continent = continents[cont_idx]
                    part_code = read_str()
                    part_name = read_str()
                    rings = read_rings()
                    code = part_code if part_code else country_code
                    name = part_name if part_name else country_name
                    self.parts.append(_Part(code, name, continent, rings))

            n_regions = struct.unpack("<i", f.read(4))[0]
            for _ in range(n_regions):
                country_code = read_str()
                region_code = read_str()
                region_name = read_str()
                n_parts = struct.unpack("<i", f.read(4))[0]
                for _ in range(n_parts):
                    rings = read_rings()
                    part = _Part(region_code, region_name, "", rings)
                    if country_code not in self.regions:
                        self.regions[country_code] = []
                    self.regions[country_code].append(part)

    def locate(self, lat: float, lon: float) -> Optional[GeoMatch]:
        """Locates continent and country for given coordinates."""
        if math.isnan(lat) or math.isnan(lon) or abs(lat) > 90 or abs(lon) > 180:
            return None
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:
            # (0, 0) is "no fix" written as zeros
            return None

        # 1. Exact polygon check
        for part in self.parts:
            if part.box_contains(lon, lat) and part.contains(lon, lat):
                return self._build_match(part, lat, lon, distance_km=0.0)

        # 2. Coastal tolerance check (points slightly off the coast)
        margin_lat = self.COASTAL_TOLERANCE_KM / 110.574
        margin_lon = min(180.0, margin_lat / max(math.cos(math.radians(lat)), 0.01))

        nearest_part = None
        best_dist = float("inf")

        for part in self.parts:
            if (
                lat >= part.min_lat - margin_lat
                and lat <= part.max_lat + margin_lat
                and lon >= part.min_lon - margin_lon
                and lon <= part.max_lon + margin_lon
            ):
                dist = self._approx_dist_to_part(part, lat, lon)
                if dist < best_dist and dist <= self.COASTAL_TOLERANCE_KM:
                    best_dist = dist
                    nearest_part = part

        if nearest_part:
            return self._build_match(nearest_part, lat, lon, distance_km=best_dist)

        return None

    def _approx_dist_to_part(self, part: _Part, lat: float, lon: float) -> float:
        """Approximates distance from point to polygon bounding box."""
        dlat = max(0.0, part.min_lat - lat, lat - part.max_lat) * 110.574
        mid_lat = (part.min_lat + part.max_lat) / 2
        dlon = max(0.0, part.min_lon - lon, lon - part.max_lon) * 111.320 * math.cos(math.radians(mid_lat))
        return math.hypot(dlat, dlon)

    def _build_match(self, part: _Part, lat: float, lon: float, distance_km: float) -> GeoMatch:
        continent = part.continent

        # European Turkey check (East Thrace)
        if part.country_code == "TUR":
            if 25.0 <= lon <= 29.2 and 39.8 <= lat <= 42.5:
                continent = "Europe"

        # Check sub-regions (e.g. Swedish län)
        reg_code = None
        reg_name = None
        if part.country_code in self.regions:
            for rpart in self.regions[part.country_code]:
                if rpart.box_contains(lon, lat) and rpart.contains(lon, lat):
                    reg_code = rpart.country_code
                    reg_name = rpart.country_name
                    break

        return GeoMatch(
            continent=continent,
            country_code=part.country_code,
            country_name=part.country_name,
            distance_km=distance_km,
            region_code=reg_code,
            region=reg_name,
        )
