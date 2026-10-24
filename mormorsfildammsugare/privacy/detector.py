"""YOLOv8 NSFW / Privacy Detector using local ONNX Runtime on Linux.

Ported and enhanced from offline-nsfw-scanner (YoloNsfwDetector.cs).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import ast
import json
import math

import numpy as np
from PIL import Image
import onnxruntime as ort


# Categorization of detection classes
STRICT_NSFW = {
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_EXPOSED",
}

EXTENDED_NSFW = STRICT_NSFW | {
    "MALE_BREAST_EXPOSED",
    "BELLY_EXPOSED",
}

SUGGESTIVE_NSFW = {
    "FEMALE_GENITALIA_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
    "ANUS_COVERED",
}


@dataclass
class DetectionBox:
    class_id: int
    class_name: str
    friendly_name: str
    confidence: float
    # Coordinates in original image pixels: [x1, y1, x2, y2]
    x1: float
    y1: float
    x2: float
    y2: float
    is_strict: bool
    is_suggestive: bool


@dataclass
class ImageDetectionResult:
    filepath: Path
    is_flagged: bool
    max_confidence: float
    detections: List[DetectionBox]
    source_width: int
    source_height: int
    scanned_frames: int = 1


def friendly_class_name(name: str) -> str:
    mapping = {
        "FEMALE_GENITALIA_EXPOSED": "Exposed Genitalia (F)",
        "MALE_GENITALIA_EXPOSED": "Exposed Genitalia (M)",
        "FEMALE_BREAST_EXPOSED": "Exposed Breast (F)",
        "MALE_BREAST_EXPOSED": "Exposed Chest (M)",
        "BUTTOCKS_EXPOSED": "Exposed Buttocks",
        "ANUS_EXPOSED": "Exposed Anus",
        "BELLY_EXPOSED": "Exposed Belly",
        "FEMALE_GENITALIA_COVERED": "Covered Genitalia",
        "FEMALE_BREAST_COVERED": "Covered Breast",
        "BUTTOCKS_COVERED": "Covered Buttocks",
        "ANUS_COVERED": "Covered Anus",
    }
    return mapping.get(name, name.replace("_", " ").title())


class YoloNsfwDetector:
    """Offline computer vision detector running YOLOv8 ONNX model."""

    IOU_THRESHOLD = 0.45

    def __init__(self, model_name: str = "320n", model_path: Optional[Path] = None):
        if model_path is None:
            models_dir = Path(__file__).parent / "models"
            model_path = models_dir / f"{model_name}.onnx"
            if not model_path.exists():
                model_path = models_dir / "320n.onnx"

        self.model_path = model_path
        self.input_size = 640 if "640m" in str(model_path) else 320

        # Create session
        opts = ort.SessionOptions()
        opts.enable_mem_pattern = True
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(self.model_path), sess_options=opts)

        # Extract class names from ONNX metadata
        meta = self.session.get_modelmeta().custom_metadata_map
        names_raw = meta.get("names", "{}")
        try:
            self.class_names: Dict[int, str] = ast.literal_eval(names_raw)
        except Exception:
            self.class_names = {}

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def _letterbox(self, img: Image.Image) -> Tuple[np.ndarray, float, int, int]:
        """Resizes image keeping aspect ratio and pads to (input_size, input_size)."""
        w, h = img.size
        scale = min(self.input_size / w, self.input_size / h)
        nw, nh = int(round(w * scale)), int(round(h * scale))

        resized = img.resize((nw, nh), Image.Resampling.BILINEAR)
        pad_x = (self.input_size - nw) // 2
        pad_y = (self.input_size - nh) // 2

        new_img = Image.new("RGB", (self.input_size, self.input_size), (114, 114, 114))
        new_img.paste(resized, (pad_x, pad_y))

        arr = np.array(new_img, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))  # HWC -> CHW
        tensor = np.expand_dims(arr, axis=0)  # (1, 3, H, W)
        return tensor, scale, pad_x, pad_y

    def _nms(self, boxes: List[DetectionBox]) -> List[DetectionBox]:
        """Class-aware Non-Maximum Suppression."""
        if not boxes:
            return []
        boxes.sort(key=lambda b: b.confidence, reverse=True)
        kept = []
        for box in boxes:
            suppress = False
            for k in kept:
                if k.class_id == box.class_id:
                    # IoU
                    inter_x1 = max(box.x1, k.x1)
                    inter_y1 = max(box.y1, k.y1)
                    inter_x2 = min(box.x2, k.x2)
                    inter_y2 = min(box.y2, k.y2)
                    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
                    area_box = (box.x2 - box.x1) * (box.y2 - box.y1)
                    area_k = (k.x2 - k.x1) * (k.y2 - k.y1)
                    union_area = area_box + area_k - inter_area
                    iou = inter_area / union_area if union_area > 0 else 0
                    if iou > self.IOU_THRESHOLD:
                        suppress = True
                        break
            if not suppress:
                kept.append(box)
        return kept

    def detect_image(
        self,
        filepath: Path,
        min_confidence: float = 0.50,
        strict_only: bool = False,
        include_suggestive: bool = False,
    ) -> ImageDetectionResult:
        """Runs detection on an image file."""
        try:
            with Image.open(filepath) as img:
                img = img.convert("RGB")
                orig_w, orig_h = img.size
                tensor, scale, pad_x, pad_y = self._letterbox(img)
        except Exception:
            return ImageDetectionResult(filepath, False, 0.0, [], 0, 0)

        out = self.session.run([self.output_name], {self.input_name: tensor})[0]
        # Shape: (1, 4 + classes, anchors)
        output = out[0]
        num_classes = len(self.class_names)
        num_anchors = output.shape[1]

        candidates = []
        for i in range(num_anchors):
            # Best class score for this anchor
            class_scores = output[4 : 4 + num_classes, i]
            best_idx = int(np.argmax(class_scores))
            best_score = float(class_scores[best_idx])

            if best_score < min_confidence:
                continue

            class_name = self.class_names.get(best_idx, f"CLASS_{best_idx}")

            # Filter by mode
            is_strict = class_name in STRICT_NSFW
            is_suggestive = class_name in SUGGESTIVE_NSFW
            is_extended = class_name in EXTENDED_NSFW

            if strict_only and not is_strict:
                continue
            if not include_suggestive and is_suggestive:
                continue
            if not strict_only and not include_suggestive and not is_extended:
                continue

            cx, cy, w, h = output[0:4, i]
            # Convert letterboxed box to unpadded coordinates
            x1 = (cx - w / 2 - pad_x) / scale
            y1 = (cy - h / 2 - pad_y) / scale
            x2 = (cx + w / 2 - pad_x) / scale
            y2 = (cy + h / 2 - pad_y) / scale

            # Clamp to image boundaries
            x1 = max(0.0, min(float(orig_w), x1))
            y1 = max(0.0, min(float(orig_h), y1))
            x2 = max(0.0, min(float(orig_w), x2))
            y2 = max(0.0, min(float(orig_h), y2))

            candidates.append(
                DetectionBox(
                    class_id=best_idx,
                    class_name=class_name,
                    friendly_name=friendly_class_name(class_name),
                    confidence=best_score,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    is_strict=is_strict,
                    is_suggestive=is_suggestive,
                )
            )

        detections = self._nms(candidates)
        max_conf = max((d.confidence for d in detections), default=0.0)
        is_flagged = len(detections) > 0

        return ImageDetectionResult(
            filepath=filepath,
            is_flagged=is_flagged,
            max_confidence=max_conf,
            detections=detections,
            source_width=orig_w,
            source_height=orig_h,
        )
