"""Frame pipeline — orchestrates capture, detection, annotation, and JPEG encoding."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from src.annotator import FrameAnnotator
from src.config import AppConfig
from src.detector import YOLOEDetector

logger = logging.getLogger(__name__)

_CAMERA_RETRY_INTERVAL = 5  # seconds


class FramePipeline:
    """End-to-end processing chain: capture → detect → annotate → encode JPEG.

    The pipeline runs in a background thread so the Flask server can serve
    frames concurrently.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._detector = YOLOEDetector(
            model_path=config.model_path,
            text_prompt=config.target_description,
            confidence_threshold=config.confidence_threshold,
        )
        self._annotator = FrameAnnotator()
        self._latest_frame: Optional[bytes] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._camera_active = False

    @property
    def camera_active(self) -> bool:
        """Whether the camera is currently providing frames."""
        return self._camera_active

    def get_latest_frame(self) -> Optional[bytes]:
        """Return the latest JPEG-encoded annotated frame, or None."""
        with self._lock:
            return self._latest_frame

    def start(self) -> None:
        """Start the capture/processing loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Frame pipeline started")

    def stop(self) -> None:
        """Stop the pipeline and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Frame pipeline stopped")

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """Try to open the camera device, return None on failure."""
        source = self._config.camera_source
        logger.info("Attempting to open camera: %s", source)
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            logger.info("Camera opened successfully: %s", source)
            return cap
        cap.release()
        logger.warning("Camera %s failed, trying fallback devices...", source)

        # Try common video devices as fallback
        for fallback in ["/dev/video0", "/dev/video1", 0, 1]:
            if str(fallback) == str(source):
                continue
            logger.info("Trying fallback camera: %s", fallback)
            cap = cv2.VideoCapture(fallback)
            if cap.isOpened():
                logger.info("Camera opened on fallback: %s", fallback)
                return cap
            cap.release()

        logger.error("No camera device available")
        return None

    def _run(self) -> None:
        """Main processing loop — runs in a background thread."""
        cap: Optional[cv2.VideoCapture] = None

        while self._running:
            # Attempt to open camera if not connected
            if cap is None or not cap.isOpened():
                self._camera_active = False
                cap = self._open_camera()
                if cap is None:
                    time.sleep(_CAMERA_RETRY_INTERVAL)
                    continue

            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame, reconnecting...")
                cap.release()
                cap = None
                self._camera_active = False
                time.sleep(_CAMERA_RETRY_INTERVAL)
                continue

            self._camera_active = True
            annotated = self._process_frame(frame)

            # Encode to JPEG
            ok, buf = cv2.imencode(".jpg", annotated)
            if ok:
                with self._lock:
                    self._latest_frame = buf.tobytes()

        # Cleanup
        if cap is not None:
            cap.release()
        self._camera_active = False

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Run detection and annotation on a single frame."""
        detections = self._detector.detect(frame)
        return self._annotator.annotate(frame, detections)
