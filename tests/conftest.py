"""Shared fixtures for pi-security-cam tests."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--on-device",
        action="store_true",
        default=False,
        help="Run tests that require the Raspberry Pi hardware/environment",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--on-device"):
        return
    skip_on_device = pytest.mark.skip(reason="needs --on-device flag (run via scripts/test.sh on the Pi)")
    for item in items:
        if "on_device" in item.keywords:
            item.add_marker(skip_on_device)
