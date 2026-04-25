import sys
from importlib import import_module
from unittest.mock import MagicMock, patch

import pytest

from roki.firmware.params import Params


@pytest.fixture
def mock_params_from_env():
    with patch.object(Params, "from_env") as m:
        yield m


@pytest.fixture
def mock_board():
    board = MagicMock()
    board.P0_22 = "P0_22_PIN"
    with patch.dict(sys.modules, {"board": board}):
        yield board


@pytest.fixture
def mock_digitalio():
    digitalio = MagicMock()
    digitalio.Direction.INPUT = "INPUT"
    digitalio.Pull.UP = "UP"
    # Fresh switch per test
    digitalio.DigitalInOut.return_value = MagicMock()
    with patch.dict(sys.modules, {"digitalio": digitalio}):
        yield digitalio


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    with patch.dict(sys.modules, {"storage": storage}):
        yield storage


@pytest.fixture(autouse=True)
def reload_boot():
    """Ensure boot.py is re-executed on every import_module call."""
    sys.modules.pop("roki.firmware.boot", None)
    yield
    sys.modules.pop("roki.firmware.boot", None)


def _run_boot():
    import_module("roki.firmware.boot")


def test_boot_calls_params_from_env(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    _run_boot()

    mock_params_from_env.assert_called_once()


def test_boot_configures_switch_pin(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    _run_boot()

    mock_digitalio.DigitalInOut.assert_called_once_with("P0_22_PIN")
    switch = mock_digitalio.DigitalInOut.return_value
    assert switch.direction == "INPUT"
    assert switch.pull == "UP"


def test_boot_remounts_readonly_when_switch_high(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = True  # switch open -> pulled up

    _run_boot()

    mock_storage.remount.assert_called_once_with("/", readonly=True)


def test_boot_remounts_writable_when_switch_low(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = False  # switch pressed to GND

    _run_boot()

    mock_storage.remount.assert_called_once_with("/", readonly=False)


def test_boot_handles_remount_runtime_error(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = True
    mock_storage.remount.side_effect = RuntimeError("cannot remount")

    with patch("roki.firmware.logging.getLogger") as mock_get_logger:
        logger = MagicMock()
        mock_get_logger.return_value = logger

        _run_boot()

        logger.error.assert_called_once_with("cannot remount")


def test_boot_deinits_switch_even_on_error(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = True
    mock_storage.remount.side_effect = RuntimeError("boom")

    _run_boot()

    switch.deinit.assert_called_once()


def test_boot_deinits_switch(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = True

    _run_boot()

    switch.deinit.assert_called_once()


def test_boot_logs_switch_state(
    mock_params_from_env: MagicMock,
    mock_board: MagicMock,
    mock_digitalio: MagicMock,
    mock_storage: MagicMock,
):
    switch = mock_digitalio.DigitalInOut.return_value
    switch.value = True

    with patch("roki.firmware.logging.getLogger") as mock_get_logger:
        logger = MagicMock()
        mock_get_logger.return_value = logger

        _run_boot()

        logger.debug.assert_called_once()
        msg = logger.debug.call_args.args[0]
        assert "P0_22" in msg
        assert "True" in msg
