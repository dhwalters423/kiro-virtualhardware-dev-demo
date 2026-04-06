"""Unit tests for FramePipeline — camera capture, retry logic, and display integration."""

from __future__ import annotations

from unittest.mock import patch, MagicMock, PropertyMock, call
import numpy as np
import pytest

from src.config import AppConfig
from src.pipeline import FramePipeline, _CAMERA_RETRY_INTERVAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(h: int = 480, w: int = 640) -> np.ndarray:
    """Return a plain grey BGR frame."""
    return np.full((h, w, 3), 128, dtype=np.uint8)


def _mock_display():
    """Create a mock DisplayWindow."""
    display = MagicMock()
    display.show_frame = MagicMock()
    display.show_offline = MagicMock()
    display.check_quit = MagicMock(return_value=False)
    display.close = MagicMock()
    return display


# We need to patch the YOLOEDetector so tests don't require the model file.
@pytest.fixture()
def pipeline_deps():
    """Provide a pipeline with mocked detector and display."""
    config = AppConfig(
        camera_device=0,
        confidence_threshold=0.3,
        target_description="knight in armor",
        model_path="fake_model.pt",
    )
    display = _mock_display()

    with patch("src.pipeline.YOLOEDetector") as MockDetector:
        mock_detector_instance = MagicMock()
        mock_detector_instance.detect.return_value = []
        MockDetector.return_value = mock_detector_instance

        pipeline = FramePipeline(config, display)
        pipeline._mock_detector = mock_detector_instance
        pipeline._mock_display = display
        yield pipeline


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_pipeline_creates_detector(self):
        """Pipeline should instantiate a YOLOEDetector with config values."""
        config = AppConfig(
            confidence_threshold=0.5,
            target_description="person",
            model_path="test.pt",
        )
        display = _mock_display()
        with patch("src.pipeline.YOLOEDetector") as MockDetector:
            MockDetector.return_value = MagicMock()
            pipeline = FramePipeline(config, display)
            MockDetector.assert_called_once_with(
                model_path="test.pt",
                text_prompt="person",
                confidence_threshold=0.5,
            )

    def test_pipeline_stores_display(self):
        """Pipeline should store the display reference."""
        config = AppConfig(model_path="test.pt")
        display = _mock_display()
        with patch("src.pipeline.YOLOEDetector") as MockDetector:
            MockDetector.return_value = MagicMock()
            pipeline = FramePipeline(config, display)
            assert pipeline._display is display

    def test_pipeline_not_running_initially(self, pipeline_deps):
        assert pipeline_deps._running is False


# ---------------------------------------------------------------------------
# _process_frame
# ---------------------------------------------------------------------------

class TestProcessFrame:
    def test_calls_detector_on_nth_frame(self, pipeline_deps):
        """_process_frame should call detect every N frames (default 3)."""
        frame = _make_frame()
        pipeline_deps._mock_detector.detect.return_value = []
        # Frames 1 and 2 skip detection
        pipeline_deps._process_frame(frame)
        pipeline_deps._process_frame(frame)
        pipeline_deps._mock_detector.detect.assert_not_called()
        # Frame 3 triggers detection
        pipeline_deps._process_frame(frame)
        pipeline_deps._mock_detector.detect.assert_called_once_with(frame)

    def test_reuses_last_detections_between_runs(self, pipeline_deps):
        """Frames between detection runs should use cached detections."""
        frame = _make_frame()
        pipeline_deps._mock_detector.detect.return_value = []
        # Run 3 frames to trigger detection, then 2 more that skip
        for _ in range(5):
            result = pipeline_deps._process_frame(frame)
        # detect called once (on frame 3), not on 4 or 5
        pipeline_deps._mock_detector.detect.assert_called_once()


# ---------------------------------------------------------------------------
# start — main loop behavior
# ---------------------------------------------------------------------------

class TestStartLoop:
    def test_captures_and_displays_frame(self, pipeline_deps):
        """Pipeline should capture a frame, process it, and display it."""
        frame = _make_frame()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, frame)

        # Quit immediately after first frame is displayed
        pipeline_deps._mock_display.check_quit.side_effect = [True]

        with patch("cv2.VideoCapture", return_value=mock_cap):
            pipeline_deps.start()

        pipeline_deps._mock_display.show_frame.assert_called_once()
        mock_cap.release.assert_called()

    def test_shows_offline_when_camera_unavailable(self, pipeline_deps):
        """Pipeline should show offline frame when camera can't be opened."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        # Quit on the check_quit after show_offline
        pipeline_deps._mock_display.check_quit.side_effect = [True]

        with patch("cv2.VideoCapture", return_value=mock_cap), \
             patch("time.sleep") as mock_sleep:
            pipeline_deps.start()

        pipeline_deps._mock_display.show_offline.assert_called()

    def test_retries_camera_on_failure(self, pipeline_deps):
        """Pipeline should retry camera connection after failure."""
        mock_cap_fail = MagicMock()
        mock_cap_fail.isOpened.return_value = False

        mock_cap_ok = MagicMock()
        mock_cap_ok.isOpened.return_value = True
        mock_cap_ok.read.return_value = (True, _make_frame())

        call_count = [0]

        def video_capture_side_effect(device):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_cap_fail
            return mock_cap_ok

        # First iteration: camera fails, show offline, sleep, retry
        # Second iteration: camera works, process frame, quit
        quit_sequence = [False, False, True]
        pipeline_deps._mock_display.check_quit.side_effect = quit_sequence

        with patch("cv2.VideoCapture", side_effect=video_capture_side_effect), \
             patch("time.sleep") as mock_sleep:
            pipeline_deps.start()

        mock_sleep.assert_called_with(_CAMERA_RETRY_INTERVAL)
        pipeline_deps._mock_display.show_offline.assert_called()
        pipeline_deps._mock_display.show_frame.assert_called()

    def test_retries_on_read_failure(self, pipeline_deps):
        """Pipeline should retry when frame read fails."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)

        # Quit after the offline display
        pipeline_deps._mock_display.check_quit.side_effect = [True]

        with patch("cv2.VideoCapture", return_value=mock_cap), \
             patch("time.sleep") as mock_sleep:
            pipeline_deps.start()

        pipeline_deps._mock_display.show_offline.assert_called()
        mock_cap.release.assert_called()

    def test_quit_exits_loop(self, pipeline_deps):
        """Pipeline should exit when check_quit returns True."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, _make_frame())

        pipeline_deps._mock_display.check_quit.return_value = True

        with patch("cv2.VideoCapture", return_value=mock_cap):
            pipeline_deps.start()

        assert pipeline_deps._running is False


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------

class TestStop:
    def test_stop_sets_running_false(self, pipeline_deps):
        """stop() should set _running to False."""
        pipeline_deps._running = True
        pipeline_deps.stop()
        assert pipeline_deps._running is False

    def test_stop_before_start(self, pipeline_deps):
        """stop() should be safe to call even if start() was never called."""
        pipeline_deps.stop()
        assert pipeline_deps._running is False


# ---------------------------------------------------------------------------
# _open_camera
# ---------------------------------------------------------------------------

class TestOpenCamera:
    def test_returns_capture_on_success(self, pipeline_deps):
        """_open_camera should return a VideoCapture when device opens."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True

        with patch("cv2.VideoCapture", return_value=mock_cap):
            result = pipeline_deps._open_camera()

        assert result is mock_cap

    def test_returns_none_on_failure(self, pipeline_deps):
        """_open_camera should return None when device fails to open."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        with patch("cv2.VideoCapture", return_value=mock_cap):
            result = pipeline_deps._open_camera()

        assert result is None
        mock_cap.release.assert_called_once()

    def test_uses_config_camera_device(self, pipeline_deps):
        """_open_camera should use the camera_device from config."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True

        with patch("cv2.VideoCapture", return_value=mock_cap) as mock_vc:
            pipeline_deps._open_camera()

        mock_vc.assert_called_once_with(0)
