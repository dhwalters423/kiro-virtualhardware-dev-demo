"""Main entry point for the Pi Security Cam application."""

from __future__ import annotations

import logging
import signal
import sys

from src.config import ConfigValidationError, load_config
from src.display import DisplayWindow
from src.pipeline import FramePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Parse config, initialize display and pipeline, and run the main loop."""
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

    display = DisplayWindow(config.target_description)
    pipeline = FramePipeline(config, display)

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        pipeline.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        pipeline.start()
    finally:
        display.close()


if __name__ == "__main__":
    main()
