"""Web view — Flask application serving MJPEG stream and status page."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Generator

from flask import Flask, Response, jsonify, render_template_string

if TYPE_CHECKING:
    from src.pipeline import FramePipeline
    from src.config import AppConfig

_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi Security Cam</title>
    <style>
        body { font-family: sans-serif; text-align: center; background: #111; color: #eee; margin: 0; padding: 20px; }
        h1 { margin-bottom: 4px; }
        p.target { font-size: 1.2em; color: #0f0; margin-bottom: 16px; }
        img { max-width: 100%; border: 2px solid #333; }
        .offline { padding: 40px; background: #222; color: #f44; font-size: 1.4em; border: 2px solid #333; display: inline-block; }
    </style>
</head>
<body>
    <h1>Pi Security Cam</h1>
    <p class="target">Looking for: {{ target_description }}</p>
    <div>
        <img src="/video_feed" alt="Live camera feed" onerror="this.style.display='none';document.getElementById('offline').style.display='inline-block';">
        <div id="offline" class="offline" style="display:none;">Camera Offline</div>
    </div>
</body>
</html>"""

_OFFLINE_PLACEHOLDER = (
    b"\xff\xd8\xff\xe0"  # minimal JPEG header bytes — not a real image
)


def _generate_frames(pipeline: "FramePipeline") -> Generator[bytes, None, None]:
    """Yield MJPEG multipart frames from the pipeline."""
    while True:
        frame = pipeline.get_latest_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


def create_app(pipeline: "FramePipeline", config: "AppConfig") -> Flask:
    """Create Flask app with MJPEG streaming and status page.

    Args:
        pipeline: The FramePipeline providing annotated JPEG frames.
        config: Application configuration (used for target description, port, etc.).

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)
    _start_time = time.time()

    @app.route("/")
    def index():
        return render_template_string(
            _INDEX_HTML, target_description=config.target_description
        )

    @app.route("/video_feed")
    def video_feed():
        return Response(
            _generate_frames(pipeline),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/status")
    def status():
        return jsonify(
            {
                "camera_active": pipeline.camera_active,
                "target_description": config.target_description,
                "uptime_seconds": round(time.time() - _start_time, 1),
            }
        )

    return app
