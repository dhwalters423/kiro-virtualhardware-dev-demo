"""Main entry point for the Pi Security Cam application."""

from __future__ import annotations

import logging
import signal
import sys
import webbrowser

from src.config import AppConfig, ConfigValidationError, load_config
from src.pipeline import FramePipeline
from src.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse config, start the pipeline, and run the Flask server."""
    try:
        config = load_config()
    except ConfigValidationError as exc:
        logger.error("Invalid configuration: %s", exc)
        sys.exit(1)
    except FileNotFoundError as exc:
        logger.error("Config file not found: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Failed to load configuration: %s", exc)
        sys.exit(1)

    pipeline = FramePipeline(config)
    app = create_app(pipeline, config)

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    pipeline.start()
    url = f"http://localhost:{config.web_port}"
    logger.info("Starting web server on port %d", config.web_port)
    webbrowser.open(url)
    app.run(host="0.0.0.0", port=config.web_port, threaded=True)


if __name__ == "__main__":
    main()
