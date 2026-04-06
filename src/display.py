"""Display window module for native OpenCV video display.

Provides the DisplayWindow class that shows annotated frames
with a target description overlay using cv2.imshow.
"""

from __future__ import annotations

import numpy as np
import cv2


class DisplayWindow:
    """Native OpenCV display window for the security camera feed.

    Opens a window titled "Pi Security Cam", overlays the target description
    on each frame, and handles keyboard-driven quit via the 'q' key.
    """

    WINDOW_TITLE = "Pi Security Cam"
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.7
    FONT_THICKNESS = 2
    OVERLAY_COLOR = (255, 255, 255)  # White text
    OVERLAY_BG_COLOR = (0, 0, 0)  # Black background for readability
    OFFLINE_FRAME_SIZE = (480, 640, 3)  # H x W x C

    def __init__(self, target_description: str) -> None:
        """Create the named OpenCV window.

        Args:
            target_description: The object being searched for (e.g. "knight in armor").
        """
        self._target_description = target_description
        self._overlay_text = f"Looking for: {target_description.title()}"
        cv2.namedWindow(self.WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)

    def show_frame(self, frame: np.ndarray) -> None:
        """Overlay target description text and display the frame.

        Draws the target description (e.g. "Looking for: Knight In Armor")
        at the top-left of the frame, then shows it in the OpenCV window.

        Args:
            frame: BGR image as a numpy array (H x W x 3).
        """
        display = frame.copy()
        self._draw_overlay_text(display, self._overlay_text)
        cv2.imshow(self.WINDOW_TITLE, display)

    def show_offline(self) -> None:
        """Display a black placeholder frame with 'Camera Offline' text."""
        black_frame = np.zeros(self.OFFLINE_FRAME_SIZE, dtype=np.uint8)
        offline_text = "Camera Offline"

        # Center the text on the frame
        (tw, th), _ = cv2.getTextSize(
            offline_text, self.FONT, self.FONT_SCALE, self.FONT_THICKNESS
        )
        h, w = black_frame.shape[:2]
        x = (w - tw) // 2
        y = (h + th) // 2

        cv2.putText(
            black_frame, offline_text, (x, y),
            self.FONT, self.FONT_SCALE, self.OVERLAY_COLOR, self.FONT_THICKNESS,
        )
        cv2.imshow(self.WINDOW_TITLE, black_frame)

    def check_quit(self) -> bool:
        """Process cv2.waitKey and return True if 'q' was pressed.

        Returns:
            True if the user pressed 'q', False otherwise.
        """
        key = cv2.waitKey(1) & 0xFF
        return key == ord("q")

    def close(self) -> None:
        """Destroy the OpenCV window."""
        cv2.destroyWindow(self.WINDOW_TITLE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _draw_overlay_text(self, frame: np.ndarray, text: str) -> None:
        """Draw text with a semi-transparent background at the top-left."""
        (tw, th), baseline = cv2.getTextSize(
            text, self.FONT, self.FONT_SCALE, self.FONT_THICKNESS
        )
        padding = 6
        x, y = padding, th + padding + baseline

        # Draw background rectangle for readability
        cv2.rectangle(
            frame,
            (0, 0),
            (tw + padding * 2, th + baseline + padding * 2),
            self.OVERLAY_BG_COLOR,
            cv2.FILLED,
        )
        # Draw the text
        cv2.putText(
            frame, text, (x, y),
            self.FONT, self.FONT_SCALE, self.OVERLAY_COLOR, self.FONT_THICKNESS,
        )
