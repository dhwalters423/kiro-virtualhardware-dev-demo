"""Unit tests for DisplayWindow — overlay rendering, offline frame, and quit logic."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import numpy as np
import cv2
import pytest

from src.display import DisplayWindow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(h: int = 480, w: int = 640) -> np.ndarray:
    """Return a plain grey BGR frame."""
    return np.full((h, w, 3), 128, dtype=np.uint8)


# We patch the cv2 GUI functions that need a display server so the tests
# can run headlessly.  Drawing functions (putText, rectangle) are NOT
# patched — they operate on numpy arrays and work fine without a display.

GUI_PATCHES = {
    "cv2.namedWindow": MagicMock(),
    "cv2.imshow": MagicMock(),
    "cv2.destroyWindow": MagicMock(),
}


@pytest.fixture()
def display_window():
    """Create a DisplayWindow with GUI calls mocked out."""
    with patch("cv2.namedWindow") as mock_nw, \
         patch("cv2.imshow") as mock_imshow, \
         patch("cv2.destroyWindow") as mock_destroy:
        dw = DisplayWindow("knight in armor")
        dw._mock_nw = mock_nw
        dw._mock_imshow = mock_imshow
        dw._mock_destroy = mock_destroy
        yield dw


# ---------------------------------------------------------------------------
# Window creation
# ---------------------------------------------------------------------------

class TestWindowCreation:
    def test_named_window_called(self, display_window: DisplayWindow):
        display_window._mock_nw.assert_called_once_with(
            "Pi Security Cam", cv2.WINDOW_AUTOSIZE
        )

    def test_window_title_constant(self):
        assert DisplayWindow.WINDOW_TITLE == "Pi Security Cam"

    def test_overlay_text_format(self, display_window: DisplayWindow):
        assert display_window._overlay_text == "Looking for: Knight In Armor"


# ---------------------------------------------------------------------------
# show_frame — overlay modifies the frame
# ---------------------------------------------------------------------------

class TestShowFrame:
    def test_show_frame_calls_imshow(self, display_window: DisplayWindow):
        frame = _make_frame()
        display_window.show_frame(frame)
        display_window._mock_imshow.assert_called_once()
        call_args = display_window._mock_imshow.call_args
        assert call_args[0][0] == "Pi Security Cam"

    def test_overlay_modifies_frame(self, display_window: DisplayWindow):
        """The displayed frame should differ from the original (text drawn)."""
        frame = _make_frame()
        original = frame.copy()
        display_window.show_frame(frame)
        # The frame passed to imshow is a copy with overlay drawn
        displayed = display_window._mock_imshow.call_args[0][1]
        assert not np.array_equal(displayed, original)

    def test_original_frame_not_mutated(self, display_window: DisplayWindow):
        """show_frame should not modify the caller's frame in-place."""
        frame = _make_frame()
        original = frame.copy()
        display_window.show_frame(frame)
        np.testing.assert_array_equal(frame, original)


# ---------------------------------------------------------------------------
# show_offline — black frame with "Camera Offline"
# ---------------------------------------------------------------------------

class TestShowOffline:
    def test_show_offline_calls_imshow(self, display_window: DisplayWindow):
        display_window.show_offline()
        display_window._mock_imshow.assert_called_once()

    def test_offline_frame_is_mostly_black(self, display_window: DisplayWindow):
        display_window.show_offline()
        shown_frame = display_window._mock_imshow.call_args[0][1]
        # Most pixels should be black (0); text occupies a small area
        black_ratio = np.sum(shown_frame == 0) / shown_frame.size
        assert black_ratio > 0.9

    def test_offline_frame_has_some_white_text(self, display_window: DisplayWindow):
        display_window.show_offline()
        shown_frame = display_window._mock_imshow.call_args[0][1]
        # There should be some non-zero pixels from the text
        assert np.any(shown_frame > 0)


# ---------------------------------------------------------------------------
# check_quit
# ---------------------------------------------------------------------------

class TestCheckQuit:
    def test_returns_true_on_q(self, display_window: DisplayWindow):
        with patch("cv2.waitKey", return_value=ord("q")):
            assert display_window.check_quit() is True

    def test_returns_false_on_other_key(self, display_window: DisplayWindow):
        with patch("cv2.waitKey", return_value=ord("a")):
            assert display_window.check_quit() is False

    def test_returns_false_on_no_key(self, display_window: DisplayWindow):
        with patch("cv2.waitKey", return_value=-1):
            assert display_window.check_quit() is False


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_destroys_window(self, display_window: DisplayWindow):
        display_window.close()
        display_window._mock_destroy.assert_called_once_with("Pi Security Cam")
