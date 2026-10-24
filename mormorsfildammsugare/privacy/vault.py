"""Vault and Whitelist management for Offline Privacy Scanner.

Ported from offline-nsfw-scanner (VaultService.cs & WhitelistService.cs).
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import json
import shutil
import uuid

from ..core.hasher import full_sha256


@dataclass
class VaultRecord:
    id: str
    original_path: str
    filename: str
    size: int
    sha256: str
    mtime_utc: str
    quarantined_at: str
    detections: List[Dict]


class VaultService:
    """Manages isolated quarantine vault and false-positive whitelist."""

    def __init__(self, vault_dir: Optional[Path] = None):
        if vault_dir is None:
            base = Path.home() / ".local" / "share" / "MormorsFilDammsugare"
            vault_dir = base / "vault"
            self.whitelist_file = base / "whitelist.json"
        else:
            self.whitelist_file = vault_dir.parent / "whitelist.json"

        self.vault_dir = vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.whitelist: Dict[str, str] = self._load_whitelist()

    def _load_whitelist(self) -> Dict[str, str]:
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_whitelist(self):
        self.whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.whitelist_file, "w", encoding="utf-8") as f:
            json.dump(self.whitelist, f, indent=2)

    def is_whitelisted(self, sha256: str) -> bool:
        return sha256 in self.whitelist

    def whitelist(self, sha256: str, original_path: str):
        self.whitelist[sha256] = original_path
        self._save_whitelist()

    def quarantine(self, filepath: Path, detections: List[Dict]) -> VaultRecord:
        """Move sensitive file into the vault as {id}.bin with an accompanying {id}.json record."""
        filepath = filepath.resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        st = filepath.stat()
        sha = full_sha256(filepath) or ""
        item_id = uuid.uuid4().hex
        now_str = datetime.now(timezone.utc).isoformat()
        mtime_str = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

        record = VaultRecord(
            id=item_id,
            original_path=str(filepath),
            filename=filepath.name,
            size=st.st_size,
            sha256=sha,
            mtime_utc=mtime_str,
            quarantined_at=now_str,
            detections=detections,
        )

        bin_path = self.vault_dir / f"{item_id}.bin"
        json_path = self.vault_dir / f"{item_id}.json"

        # Write record first
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(record), f, indent=2)

        # Move payload into vault
        shutil.move(filepath, bin_path)
        return record

    def list_entries(self) -> List[VaultRecord]:
        """List all items currently stored in the vault."""
        entries = []
        for json_file in self.vault_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entries.append(VaultRecord(**data))
            except Exception:
                continue
        entries.sort(key=lambda x: x.quarantined_at, reverse=True)
        return entries

    def restore(self, item_id: str) -> Optional[Path]:
        """Restore quarantined file back to its original location."""
        json_path = self.vault_dir / f"{item_id}.json"
        bin_path = self.vault_dir / f"{item_id}.bin"

        if not json_path.exists() or not bin_path.exists():
            return None

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        orig_path = Path(data["original_path"])
        orig_path.parent.mkdir(parents=True, exist_ok=True)

        target = orig_path
        if target.exists():
            # If original path is occupied, rename safely
            counter = 2
            while target.exists():
                target = orig_path.with_name(f"{orig_path.stem} ({counter}){orig_path.suffix}")
                counter += 1

        shutil.move(bin_path, target)

        # Restore timestamps
        try:
            mtime_dt = datetime.fromisoformat(data["mtime_utc"])
            ts = mtime_dt.timestamp()
            os.utime(target, (ts, ts))
        except Exception:
            pass

        json_path.unlink(missing_ok=True)
        return target

    def purge(self, item_id: str) -> bool:
        """Permanently delete file from vault."""
        json_path = self.vault_dir / f"{item_id}.json"
        bin_path = self.vault_dir / f"{item_id}.bin"
        success = False
        if bin_path.exists():
            bin_path.unlink()
            success = True
        if json_path.exists():
            json_path.unlink()
            success = True
        return success
