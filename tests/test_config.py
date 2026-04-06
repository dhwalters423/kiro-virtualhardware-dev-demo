"""Unit tests for AppConfig dataclass — serialization, validation, and CLI parsing."""

import json
import os
import pytest

from src.config import AppConfig, ConfigValidationError, parse_args, load_config


class TestAppConfigDefaults:
    """Test default values match the design spec."""

    def test_default_camera_device(self):
        cfg = AppConfig()
        assert cfg.camera_device == 0

    def test_default_confidence_threshold(self):
        cfg = AppConfig()
        assert cfg.confidence_threshold == 0.3

    def test_default_target_description(self):
        cfg = AppConfig()
        assert cfg.target_description == "knight in armor"

    def test_default_model_path(self):
        cfg = AppConfig()
        assert cfg.model_path == "yoloe-11s-seg.pt"


class TestAppConfigValidation:
    """Test validation rejects invalid values."""

    def test_negative_camera_device(self):
        with pytest.raises(ConfigValidationError, match="camera_device"):
            AppConfig(camera_device=-1)

    def test_non_int_camera_device(self):
        with pytest.raises(ConfigValidationError, match="camera_device"):
            AppConfig(camera_device="0")  # type: ignore

    def test_confidence_threshold_zero(self):
        with pytest.raises(ConfigValidationError, match="confidence_threshold"):
            AppConfig(confidence_threshold=0.0)

    def test_confidence_threshold_above_one(self):
        with pytest.raises(ConfigValidationError, match="confidence_threshold"):
            AppConfig(confidence_threshold=1.1)

    def test_confidence_threshold_negative(self):
        with pytest.raises(ConfigValidationError, match="confidence_threshold"):
            AppConfig(confidence_threshold=-0.5)

    def test_empty_target_description(self):
        with pytest.raises(ConfigValidationError, match="target_description"):
            AppConfig(target_description="")

    def test_whitespace_target_description(self):
        with pytest.raises(ConfigValidationError, match="target_description"):
            AppConfig(target_description="   ")

    def test_empty_model_path(self):
        with pytest.raises(ConfigValidationError, match="model_path"):
            AppConfig(model_path="")

    def test_whitespace_model_path(self):
        with pytest.raises(ConfigValidationError, match="model_path"):
            AppConfig(model_path="   ")

    def test_valid_boundary_confidence_one(self):
        cfg = AppConfig(confidence_threshold=1.0)
        assert cfg.confidence_threshold == 1.0

    def test_valid_small_confidence(self):
        cfg = AppConfig(confidence_threshold=0.01)
        assert cfg.confidence_threshold == 0.01

    def test_multiple_errors_reported(self):
        with pytest.raises(ConfigValidationError) as exc_info:
            AppConfig(camera_device=-1, confidence_threshold=0.0)
        msg = str(exc_info.value)
        assert "camera_device" in msg
        assert "confidence_threshold" in msg


class TestAppConfigSerialization:
    """Test to_dict / from_dict and to_json / from_json."""

    def test_to_dict(self):
        cfg = AppConfig()
        d = cfg.to_dict()
        assert d == {
            "camera_device": 0,
            "capture_width": 640,
            "capture_height": 480,
            "detect_every_n_frames": 3,
            "confidence_threshold": 0.3,
            "target_description": "knight in armor",
            "model_path": "yoloe-11s-seg.pt",
        }

    def test_from_dict(self):
        d = {
            "camera_device": 1,
            "confidence_threshold": 0.5,
            "target_description": "person",
            "model_path": "custom.pt",
        }
        cfg = AppConfig.from_dict(d)
        assert cfg.camera_device == 1
        assert cfg.confidence_threshold == 0.5
        assert cfg.target_description == "person"
        assert cfg.model_path == "custom.pt"

    def test_from_dict_ignores_unknown_keys(self):
        d = {
            "camera_device": 0,
            "confidence_threshold": 0.3,
            "target_description": "knight in armor",
            "model_path": "yoloe-11s-seg.pt",
            "unknown_key": "should be ignored",
        }
        cfg = AppConfig.from_dict(d)
        assert cfg.camera_device == 0
        assert not hasattr(cfg, "unknown_key")

    def test_round_trip_dict(self):
        original = AppConfig(camera_device=2, confidence_threshold=0.7, target_description="dog", model_path="m.pt")
        restored = AppConfig.from_dict(original.to_dict())
        assert restored == original

    def test_to_json_and_from_json(self, tmp_path):
        path = str(tmp_path / "cfg.json")
        original = AppConfig(camera_device=3, confidence_threshold=0.9, target_description="cat", model_path="x.pt")
        original.to_json(path)
        restored = AppConfig.from_json(path)
        assert restored == original

    def test_json_file_content(self, tmp_path):
        path = str(tmp_path / "cfg.json")
        cfg = AppConfig()
        cfg.to_json(path)
        with open(path) as f:
            data = json.load(f)
        assert data["camera_device"] == 0
        assert data["confidence_threshold"] == 0.3

    def test_from_dict_with_invalid_values_raises(self):
        with pytest.raises(ConfigValidationError):
            AppConfig.from_dict({"camera_device": -5})


class TestCLIParsing:
    """Test parse_args and load_config."""

    def test_parse_args_no_args(self):
        ns = parse_args([])
        assert ns.config is None

    def test_parse_args_with_config(self):
        ns = parse_args(["--config", "my_config.json"])
        assert ns.config == "my_config.json"

    def test_load_config_defaults(self):
        cfg = load_config([])
        assert cfg == AppConfig()

    def test_load_config_from_file(self, tmp_path):
        path = str(tmp_path / "test.json")
        data = {
            "camera_device": 2,
            "confidence_threshold": 0.8,
            "target_description": "helmet",
            "model_path": "model.pt",
        }
        with open(path, "w") as f:
            json.dump(data, f)
        cfg = load_config(["--config", path])
        assert cfg.camera_device == 2
        assert cfg.confidence_threshold == 0.8
        assert cfg.target_description == "helmet"
        assert cfg.model_path == "model.pt"
