"""Application configuration with JSON serialization and validation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict, fields
from typing import Any, Dict, List, Optional


class ConfigValidationError(Exception):
    """Raised when configuration values are invalid."""


@dataclass
class AppConfig:
    camera_device: int = 0
    capture_width: int = 640
    capture_height: int = 480
    detect_every_n_frames: int = 3
    confidence_threshold: float = 0.3
    target_description: str = "knight in armor"
    model_path: str = "yoloe-11s-seg.pt"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate all configuration fields."""
        errors: List[str] = []
        if not isinstance(self.camera_device, int) or self.camera_device < 0:
            errors.append(f"camera_device must be a non-negative integer, got {self.camera_device!r}")
        if not isinstance(self.capture_width, int) or self.capture_width <= 0:
            errors.append(f"capture_width must be a positive integer, got {self.capture_width!r}")
        if not isinstance(self.capture_height, int) or self.capture_height <= 0:
            errors.append(f"capture_height must be a positive integer, got {self.capture_height!r}")
        if not isinstance(self.detect_every_n_frames, int) or self.detect_every_n_frames < 1:
            errors.append(f"detect_every_n_frames must be a positive integer, got {self.detect_every_n_frames!r}")
        if not isinstance(self.confidence_threshold, (int, float)) or not (0 < self.confidence_threshold <= 1.0):
            errors.append(f"confidence_threshold must be in (0, 1.0], got {self.confidence_threshold!r}")
        if not isinstance(self.target_description, str) or not self.target_description.strip():
            errors.append("target_description must be a non-empty string")
        if not isinstance(self.model_path, str) or not self.model_path.strip():
            errors.append("model_path must be a non-empty string")
        if errors:
            raise ConfigValidationError("; ".join(errors))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        """Create from dictionary. Unknown keys are ignored."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_json(self, path: str) -> None:
        """Save config to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> AppConfig:
        """Load config from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for config file path."""
    parser = argparse.ArgumentParser(description="Pi Security Cam")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON configuration file (uses defaults if not provided)",
    )
    return parser.parse_args(argv)


def load_config(argv: Optional[List[str]] = None) -> AppConfig:
    """Load configuration from CLI args, falling back to defaults."""
    args = parse_args(argv)
    if args.config:
        return AppConfig.from_json(args.config)
    return AppConfig()
