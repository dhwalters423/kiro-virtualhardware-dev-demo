"""YOLOE-based text-prompted zero-shot object detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single object detection result."""
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    label: str


def filter_by_confidence(
    detections: List[Detection], threshold: float
) -> List[Detection]:
    """Return only detections at or above the confidence threshold."""
    return [d for d in detections if d.confidence >= threshold]


class YOLOEDetector:
    """Wraps YOLOE inference with text-prompted detection.

    This class loads the YOLOE model and runs inference on frames.
    It is designed to run on the Raspberry Pi (ARM device) — model loading
    and inference require the ultralytics package and the model file on disk.
    """

    def __init__(
        self,
        model_path: str,
        text_prompt: str,
        confidence_threshold: float = 0.3,
    ):
        """Load YOLOE model and configure text prompt.

        Args:
            model_path: Path to the YOLOE model file.
            text_prompt: Natural language description of the target object.
            confidence_threshold: Minimum confidence to keep a detection.
        """
        self.model_path = model_path
        self.text_prompt = text_prompt
        self.confidence_threshold = confidence_threshold
        self.model = None  # Loaded lazily or on-device

        try:
            from ultralytics import YOLO

            self.model = YOLO(model_path)
            # Set the text prompt for YOLOE text-prompted detection
            self.model.set_classes([text_prompt])
            logger.info("YOLOE model loaded from %s", model_path)
        except Exception as exc:
            logger.error("Failed to load YOLOE model: %s", exc)
            raise

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run inference on a frame and return detections above threshold.

        Args:
            frame: BGR image as a numpy array (H x W x 3).

        Returns:
            List of Detection objects that meet the confidence threshold.
        """
        if self.model is None:
            logger.warning("Model not loaded, returning empty detections")
            return []

        try:
            results = self.model.predict(frame, verbose=False)
        except Exception as exc:
            logger.error("Inference failed: %s", exc)
            return []

        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                conf = float(boxes.conf[i])
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                detections.append(
                    Detection(
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=conf,
                        label=self.text_prompt,
                    )
                )

        return filter_by_confidence(detections, self.confidence_threshold)
