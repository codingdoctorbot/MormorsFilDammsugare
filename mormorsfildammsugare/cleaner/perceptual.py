"""Perceptual Image Hashing & Similarity Finder (Czkawka Similar Images).

Computes 128-bit perceptual hash (64-bit dHash + 64-bit aHash) to detect
resized, recompressed, slightly cropped, and burst-shot similar photos.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math

import numpy as np
from PIL import Image


@dataclass
class ImageHashEntry:
    path: Path
    hash_val: int  # 128-bit integer
    size: int
    width: int
    height: int


@dataclass
class SimilarImageGroup:
    base_image: ImageHashEntry
    similar_images: List[Tuple[ImageHashEntry, int]]  # (entry, hamming_distance)


def compute_perceptual_hash(image_path: Path, hash_size: int = 8) -> Optional[ImageHashEntry]:
    """Computes a 128-bit perceptual hash combining dHash (gradient) and aHash (mean luminosity)."""
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            st_size = image_path.stat().st_size
            gray = img.convert("L")

            # 1. dHash (Difference Hash, 64-bit): captures horizontal gradients
            resized_d = gray.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            arr_d = np.array(resized_d, dtype=np.int32)
            diff_d = arr_d[:, :-1] > arr_d[:, 1:]
            val_d = 0
            for bit in diff_d.flatten():
                val_d = (val_d << 1) | int(bit)

            # 2. aHash (Average Hash, 64-bit): captures average light/dark distribution
            resized_a = gray.resize((hash_size, hash_size), Image.Resampling.LANCZOS)
            arr_a = np.array(resized_a, dtype=np.float32)
            avg = arr_a.mean()
            diff_a = arr_a > avg
            val_a = 0
            for bit in diff_a.flatten():
                val_a = (val_a << 1) | int(bit)

            # Combine into 128-bit integer
            combined_hash = (val_d << 64) | val_a
            return ImageHashEntry(path=image_path, hash_val=combined_hash, size=st_size, width=w, height=h)
    except Exception:
        return None


def hamming_distance(h1: int, h2: int) -> int:
    """Computes the Hamming distance (number of differing bits) between two 128-bit hashes."""
    return bin(h1 ^ h2).count("1")


def find_similar_images(
    image_paths: List[Path],
    max_distance: int = 5,
    progress_callback=None,
) -> List[SimilarImageGroup]:
    """Scans images and clusters them by visual similarity."""
    entries: List[ImageHashEntry] = []

    for i, p in enumerate(image_paths):
        if progress_callback and i % 20 == 0:
            progress_callback(f"Hashing {p.name}", i)
        entry = compute_perceptual_hash(p)
        if entry:
            entries.append(entry)

    groups: List[SimilarImageGroup] = []
    visited = set()

    for i, base in enumerate(entries):
        if base.path in visited:
            continue

        similar = []
        for other in entries[i + 1 :]:
            if other.path in visited:
                continue
            dist = hamming_distance(base.hash_val, other.hash_val)
            if dist <= max_distance:
                similar.append((other, dist))
                visited.add(other.path)

        if similar:
            visited.add(base.path)
            # Sort similar images by closest distance first
            similar.sort(key=lambda x: x[1])
            groups.append(SimilarImageGroup(base_image=base, similar_images=similar))

    return groups
