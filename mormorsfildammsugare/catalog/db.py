"""SQLite Catalog & Run History with Undo / Restore support.

Stored at <Destination>/_MormorsFilDammsugare/catalog.db.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sqlite3


@dataclass
class CatalogItem:
    sha256: str
    size: int
    dest_path: str
    category: str
    format_name: str
    date_taken: Optional[str]
    date_source: str
    latitude: Optional[float]
    longitude: Optional[float]
    continent: Optional[str]
    country: Optional[str]
    region: Optional[str]


class CatalogDb:
    """Embedded SQLite database for MormorsFilDammsugare."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA foreign_keys = ON;")

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_type TEXT NOT NULL,
                    source_dir TEXT NOT NULL,
                    dest_dir TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    is_move INTEGER NOT NULL DEFAULT 0,
                    files_processed INTEGER NOT NULL DEFAULT 0,
                    duplicates_skipped INTEGER NOT NULL DEFAULT 0
                );
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sha256 TEXT NOT NULL UNIQUE,
                    size INTEGER NOT NULL,
                    dest_path TEXT NOT NULL,
                    category TEXT NOT NULL,
                    format_name TEXT NOT NULL,
                    date_taken TEXT,
                    date_source TEXT,
                    latitude REAL,
                    longitude REAL,
                    continent TEXT,
                    country TEXT,
                    region TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_id INTEGER NOT NULL REFERENCES media(id),
                    source_path TEXT NOT NULL UNIQUE,
                    mtime_utc TEXT NOT NULL
                );
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS removed_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES runs(id),
                    source_path TEXT NOT NULL,
                    dest_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_utc TEXT NOT NULL,
                    removed_at TEXT NOT NULL
                );
            """)

            # Indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media(sha256);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_path ON sources(source_path);")

    def start_run(self, run_type: str, source_dir: str, dest_dir: str, is_move: bool = False) -> int:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO runs (run_type, source_dir, dest_dir, started_at, is_move) VALUES (?, ?, ?, ?, ?)",
                (run_type, source_dir, dest_dir, now_str, 1 if is_move else 0),
            )
            return cursor.lastrowid

    def finish_run(self, run_id: int, files_processed: int, duplicates_skipped: int):
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                "UPDATE runs SET ended_at = ?, files_processed = ?, duplicates_skipped = ? WHERE id = ?",
                (now_str, files_processed, duplicates_skipped, run_id),
            )

    def get_existing_by_sha256(self, sha256: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM media WHERE sha256 = ?", (sha256,))
        return cur.fetchone()

    def add_media(self, item: CatalogItem, source_path: str, mtime_utc: str) -> int:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO media (sha256, size, dest_path, category, format_name, date_taken, date_source,
                                   latitude, longitude, continent, country, region, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.sha256,
                    item.size,
                    item.dest_path,
                    item.category,
                    item.format_name,
                    item.date_taken,
                    item.date_source,
                    item.latitude,
                    item.longitude,
                    item.continent,
                    item.country,
                    item.region,
                    now_str,
                ),
            )
            media_id = cur.lastrowid
            self.conn.execute(
                "INSERT OR REPLACE INTO sources (media_id, source_path, mtime_utc) VALUES (?, ?, ?)",
                (media_id, source_path, mtime_utc),
            )
            return media_id

    def record_removed_source(
        self, run_id: int, source_path: str, dest_path: str, sha256: str, size: int, mtime_utc: str
    ):
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO removed_sources (run_id, source_path, dest_path, sha256, size, mtime_utc, removed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, source_path, dest_path, sha256, size, mtime_utc, now_str),
            )

    def get_removals_for_restore(self, run_id: Optional[int] = None) -> List[sqlite3.Row]:
        if run_id:
            cur = self.conn.execute("SELECT * FROM removed_sources WHERE run_id = ?", (run_id,))
        else:
            cur = self.conn.execute("SELECT * FROM removed_sources ORDER BY id DESC")
        return cur.fetchall()

    def close(self):
        self.conn.close()
