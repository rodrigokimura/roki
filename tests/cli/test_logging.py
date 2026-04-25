import logging
from unittest.mock import MagicMock, patch

import pytest

from roki.cli.logging import (
    LevelBasedFormatter,
    configure_logging,
    format_by_level,
)

# ---------------------------------------------------------------------------
# format_by_level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "level,expected_label",
    [
        (logging.DEBUG, "DEBUG"),
        (logging.INFO, "INFO"),
        (logging.WARNING, "WARNING"),
        (logging.ERROR, "ERROR"),
        (logging.CRITICAL, "CRITICAL"),
    ],
)
def test_format_by_level_contains_level_label(level: int, expected_label: str):
    fmt = format_by_level(level)

    assert expected_label in fmt
    # Format string must contain the standard logging placeholders
    assert "%(message)s" in fmt
    assert "%(asctime)s" in fmt
    assert "%(name)s" in fmt
    assert "%(process)d" in fmt


def test_format_by_level_unknown_level_falls_back_to_info():
    fmt_unknown = format_by_level(9999)
    fmt_info = format_by_level(logging.INFO)

    # The level label block should match the INFO one
    assert "INFO" in fmt_unknown
    # And structurally it should look like the INFO format
    assert fmt_unknown.count("%(message)s") == fmt_info.count("%(message)s")


# ---------------------------------------------------------------------------
# LevelBasedFormatter
# ---------------------------------------------------------------------------


def _make_record(level: int, msg: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(
        name="roki.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )


def test_level_based_formatter_formats_record_with_message():
    formatter = LevelBasedFormatter()
    record = _make_record(logging.INFO, "my-message")

    output = formatter.format(record)

    assert "my-message" in output
    assert "INFO" in output
    assert "roki.test" in output


def test_level_based_formatter_uses_level_specific_format():
    formatter = LevelBasedFormatter()

    info_out = formatter.format(_make_record(logging.INFO, "x"))
    error_out = formatter.format(_make_record(logging.ERROR, "x"))

    assert "INFO" in info_out
    assert "ERROR" in error_out
    assert info_out != error_out


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_basic_config():
    with patch("roki.cli.logging.logging.basicConfig") as m:
        yield m


def test_configure_logging_with_level_uses_stream_handler(
    mock_basic_config: MagicMock,
):
    configure_logging(logging.DEBUG)

    mock_basic_config.assert_called_once()
    kwargs = mock_basic_config.call_args.kwargs

    assert kwargs["level"] == logging.DEBUG
    handlers = kwargs["handlers"]
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)
    assert not isinstance(handlers[0], logging.NullHandler)
    assert isinstance(handlers[0].formatter, LevelBasedFormatter)
    assert handlers[0].level == logging.DEBUG


def test_configure_logging_without_level_uses_null_handler(
    mock_basic_config: MagicMock,
):
    configure_logging(0)

    mock_basic_config.assert_called_once()
    kwargs = mock_basic_config.call_args.kwargs

    assert kwargs["level"] == 0
    handlers = kwargs["handlers"]
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.NullHandler)
    assert isinstance(handlers[0].formatter, LevelBasedFormatter)


def test_configure_logging_emits_debug_message(mock_basic_config: MagicMock):
    with patch("roki.cli.logging.logger") as mock_logger:
        configure_logging(logging.WARNING)

        mock_logger.debug.assert_called_once()
        msg = mock_logger.debug.call_args.args[0]
        assert "WARNING" in msg
