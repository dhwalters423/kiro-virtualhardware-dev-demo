"""Unit tests for main.py entry point."""

from __future__ import annotations

import signal
from unittest.mock import patch, MagicMock, call

import pytest

from src.config import ConfigValidationError


# ---------------------------------------------------------------------------
# main() — config loading
# ---------------------------------------------------------------------------

class TestMainConfigLoading:
    @patch("src.main.FramePipeline")
    @patch("src.main.DisplayWindow")
    @patch("src.main.load_config")
    def test_loads_config_and_creates_display_and_pipeline(
        self, mock_load_config, mock_display_cls, mock_pipeline_cls
    ):
        """main() should load config, create DisplayWindow and FramePipeline."""
        from src.main import main

        mock_config = MagicMock()
        mock_config.target_description = "knight in armor"
        mock_load_config.return_value = mock_config

        mock_display = MagicMock()
        mock_display_cls.return_value = mock_display

        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        main()

        mock_load_config.assert_called_once()
        mock_display_cls.assert_called_once_with("knight in armor")
        mock_pipeline_cls.assert_called_once_with(mock_config, mock_display)
        mock_pipeline.start.assert_called_once()
        mock_display.close.assert_called_once()

    @patch("src.main.load_config", side_effect=ConfigValidationError("bad config"))
    def test_exits_on_invalid_config(self, mock_load_config):
        """main() should exit with code 1 on invalid configuration."""
        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("src.main.load_config", side_effect=FileNotFoundError("no file"))
    def test_exits_on_missing_config_file(self, mock_load_config):
        """main() should exit with code 1 when config file is not found."""
        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("src.main.load_config", side_effect=RuntimeError("unexpected"))
    def test_exits_on_unexpected_error(self, mock_load_config):
        """main() should exit with code 1 on unexpected config errors."""
        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# main() — signal handling
# ---------------------------------------------------------------------------

class TestMainSignalHandling:
    @patch("src.main.FramePipeline")
    @patch("src.main.DisplayWindow")
    @patch("src.main.load_config")
    @patch("src.main.signal.signal")
    def test_registers_signal_handlers(
        self, mock_signal, mock_load_config, mock_display_cls, mock_pipeline_cls
    ):
        """main() should register SIGINT and SIGTERM handlers."""
        from src.main import main

        mock_config = MagicMock()
        mock_config.target_description = "test"
        mock_load_config.return_value = mock_config
        mock_display_cls.return_value = MagicMock()
        mock_pipeline_cls.return_value = MagicMock()

        main()

        signal_calls = [c[0][0] for c in mock_signal.call_args_list]
        assert signal.SIGINT in signal_calls
        assert signal.SIGTERM in signal_calls

    @patch("src.main.FramePipeline")
    @patch("src.main.DisplayWindow")
    @patch("src.main.load_config")
    def test_signal_handler_calls_pipeline_stop(
        self, mock_load_config, mock_display_cls, mock_pipeline_cls
    ):
        """The signal handler should call pipeline.stop()."""
        from src.main import main

        mock_config = MagicMock()
        mock_config.target_description = "test"
        mock_load_config.return_value = mock_config
        mock_display_cls.return_value = MagicMock()

        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        captured_handler = None

        def capture_signal(signum, handler):
            nonlocal captured_handler
            if signum == signal.SIGINT:
                captured_handler = handler

        with patch("src.main.signal.signal", side_effect=capture_signal):
            main()

        assert captured_handler is not None
        captured_handler(signal.SIGINT, None)
        mock_pipeline.stop.assert_called_once()


# ---------------------------------------------------------------------------
# main() — graceful shutdown (display.close in finally)
# ---------------------------------------------------------------------------

class TestMainGracefulShutdown:
    @patch("src.main.FramePipeline")
    @patch("src.main.DisplayWindow")
    @patch("src.main.load_config")
    def test_display_close_called_on_normal_exit(
        self, mock_load_config, mock_display_cls, mock_pipeline_cls
    ):
        """display.close() should be called after pipeline.start() returns."""
        from src.main import main

        mock_config = MagicMock()
        mock_config.target_description = "test"
        mock_load_config.return_value = mock_config

        mock_display = MagicMock()
        mock_display_cls.return_value = mock_display
        mock_pipeline_cls.return_value = MagicMock()

        main()

        mock_display.close.assert_called_once()

    @patch("src.main.FramePipeline")
    @patch("src.main.DisplayWindow")
    @patch("src.main.load_config")
    def test_display_close_called_on_pipeline_exception(
        self, mock_load_config, mock_display_cls, mock_pipeline_cls
    ):
        """display.close() should be called even if pipeline.start() raises."""
        from src.main import main

        mock_config = MagicMock()
        mock_config.target_description = "test"
        mock_load_config.return_value = mock_config

        mock_display = MagicMock()
        mock_display_cls.return_value = mock_display

        mock_pipeline = MagicMock()
        mock_pipeline.start.side_effect = RuntimeError("camera exploded")
        mock_pipeline_cls.return_value = mock_pipeline

        with pytest.raises(RuntimeError, match="camera exploded"):
            main()

        mock_display.close.assert_called_once()
