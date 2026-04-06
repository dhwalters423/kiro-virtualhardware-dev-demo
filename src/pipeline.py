"""Frame pipeline — orchestrates capture, detection, annotation, and display.

The pipeline runs in the main thread (required by OpenCV GUI) and wires
together the Detector, Annotator, and DisplayWindow components.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import cv2
import numpy as np

from src.annotator import FrameAnnotator
from src.config import AppConfig
from src.detector import YOLOEDetector
from src.display import DisplayWindow

logger = logging.getLogger(__name__)

_CAMERA_RETRY_INTERVAL = 5  # seconds


class FramePipeline:
    """End-to-end processing chain: capture → detect → annotate → display.

    The pipeline runs in the main thread so that OpenCV GUI calls
    (imshow / waitKey) work correctly.
    """

    def __init__(self, config: AppConfig, display: DisplayWindow) -> None:
        self._config = config
        self._display = display
        self._detector = YOLOEDetector(
            model_path=config.model_path,
            text_prompt=config.target_description,
            confidence_threshold=config.confidence_threshold,
        )
        self._annotator = FrameAnnotator()
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_count = 0
        self._last_detections: list = []

    def start(self) -> None:
        """Run the camera capture, processing, and display loop.

        This method blocks until the user presses 'q' or stop() is called.
        It runs in the main thread as required by OpenCV's GUI.
        """
        self._running = True
        logger.info("Frame pipeline started")

        try:
            while self._running:
                # Attempt to open camera if not connected
                if self._cap is None or not self._cap.isOpened():
                    self._cap = self._open_camera()
                    if self._cap is None:
                        self._display.show_offline()
                        if self._display.check_quit():
                            break
                        time.sleep(_CAMERA_RETRY_INTERVAL)
                        continue

                ret, frame = self._cap.read()
                if not ret:
                    logger.error("Failed to read frame, reconnecting...")
                    self._cap.release()
                    self._cap = None
                    self._display.show_offline()
                    if self._display.check_quit():
                        break
                    time.sleep(_CAMERA_RETRY_INTERVAL)
                    continue

                annotated = self._process_frame(frame)
                self._display.show_frame(annotated)

                if self._display.check_quit():
                    break
        finally:
            self._release_camera()
            self._running = False
            logger.info("Frame pipeline stopped")

    def stop(self) -> None:
        """Signal the pipeline loop to exit and release resources."""
        self._running = False

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Downscale, detect (with frame skipping), and annotate a single frame."""
        h, w = frame.shape[:2]
        target_w = self._config.capture_width
        target_h = self._config.capture_height
        if w != target_w or h != target_h:
            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

        self._frame_count += 1
        if self._frame_count % self._config.detect_every_n_frames == 0:
            self._last_detections = self._detector.detect(frame)

        return self._annotator.annotate(frame, self._last_detections)

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """Try to open the camera device, return None on failure."""
        device = self._config.camera_device
        logger.info("Attempting to open camera device: %s", device)
        cap = cv2.VideoCapture(device)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.capture_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.capture_height)
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info("Camera opened successfully: %s (%dx%d)", device, actual_w, actual_h)
            return cap
        cap.release()
        logger.error("Camera device %s unavailable", device)
        return None

    def _release_camera(self) -> None:
        """Release the camera if it is open."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
