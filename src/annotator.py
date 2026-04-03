"""Frame annotation — draws bounding boxes and labels on video frames."""

from __future__ import annotations

from typing import List

import cv2
import numpy as np

from src.detector import Detection


class FrameAnnotator:
    """Draws bounding boxes and confidence labels on frames using OpenCV."""

    BOX_COLOR = (0, 255, 0)  # Bright green in BGR
    BOX_THICKNESS = 2
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.6
    FONT_THICKNESS = 1
    LABEL_BG_COLOR = (0, 255, 0)
    LABEL_TEXT_COLOR = (0, 0, 0)

    def annotate(
        self, frame: np.ndarray, detections: List[Detection]
    ) -> np.ndarray:
        """Draw bounding boxes and labels on the frame for each detection.

        Args:
            frame: BGR image as a numpy array (H x W x 3).
            detections: List of Detection objects to draw.

        Returns:
            The annotated frame. If detections is empty, returns the
            original frame unmodified.
        """
        if not detections:
            return frame

        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), self.BOX_COLOR, self.BOX_THICKNESS)
            # Build label text
            label = f"{det.label} {det.confidence:.0%}"
            (tw, th), baseline = cv2.getTextSize(label, self.FONT, self.FONT_SCALE, self.FONT_THICKNESS)
            # Draw label background
            cv2.rectangle(annotated, (x1, y1 - th - baseline - 4), (x1 + tw, y1), self.LABEL_BG_COLOR, cv2.FILLED)
            # Draw label text
            cv2.putText(annotated, label, (x1, y1 - baseline - 2), self.FONT, self.FONT_SCALE, self.LABEL_TEXT_COLOR, self.FONT_THICKNESS)

        return annotated
