"""Module 3: Privacy & Loaner Audit Engine (Offline NSFW Scanner).

Scans directories for explicit or sensitive media using YOLOv8 ONNX model,
generates audit reports, and provides isolation in a secure Vault.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional
import time

from ..core.hasher import full_sha256
from ..core.sniffer import MediaCategory, sniff_file
from ..core.walker import walk_files
from ..privacy.detector import ImageDetectionResult, YoloNsfwDetector
from ..privacy.vault import VaultRecord, VaultService


@dataclass
class PrivacyScannerOptions:
    source_dirs: List[Path]
    min_confidence: float = 0.50
    strict_only: bool = False
    include_suggestive: bool = False
    quarantine_flagged: bool = False
    model_name: str = "320n"  # 320n or 640m


@dataclass
class PrivacyScanStats:
    total_scanned: int = 0
    flagged_files: List[ImageDetectionResult] = field(default_factory=list)
    quarantined_records: List[VaultRecord] = field(default_factory=list)
    whitelisted_skipped: int = 0
    scan_time_seconds: float = 0.0


class PrivacyScanner:
    """The Privacy & Loaner Audit Scanner."""

    def __init__(self, options: PrivacyScannerOptions, custom_vault_dir: Optional[Path] = None):
        self.options = options
        self.detector = YoloNsfwDetector(model_name=options.model_name)
        self.vault = VaultService(vault_dir=custom_vault_dir)

    def scan(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> PrivacyScanStats:
        start_time = time.time()
        stats = PrivacyScanStats()

        for root in self.options.source_dirs:
            p_root = root.resolve()
            if not p_root.exists():
                continue

            for file_path in walk_files(p_root):
                # Only inspect image formats
                sniff_res = sniff_file(file_path)
                if sniff_res.category != MediaCategory.PHOTO:
                    continue

                stats.total_scanned += 1
                if progress_callback and stats.total_scanned % 10 == 0:
                    progress_callback(file_path.name, stats.total_scanned)

                # Skip whitelisted files
                sha = full_sha256(file_path)
                if sha and self.vault.is_whitelisted(sha):
                    stats.whitelisted_skipped += 1
                    continue

                res = self.detector.detect_image(
                    file_path,
                    min_confidence=self.options.min_confidence,
                    strict_only=self.options.strict_only,
                    include_suggestive=self.options.include_suggestive,
                )

                if res.is_flagged:
                    stats.flagged_files.append(res)
                    if self.options.quarantine_flagged:
                        record = self.vault.quarantine(
                            file_path,
                            detections=[
                                {
                                    "class": d.friendly_name,
                                    "raw_class": d.class_name,
                                    "confidence": d.confidence,
                                    "box": [d.x1, d.y1, d.x2, d.y2],
                                }
                                for d in res.detections
                            ],
                        )
                        stats.quarantined_records.append(record)

        stats.scan_time_seconds = time.time() - start_time
        return stats
