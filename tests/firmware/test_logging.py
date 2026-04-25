import adafruit_logging as adafruit_logging_mod
import pytest

from roki.firmware import logging as firmware_logging
from roki.firmware.logging import (
    LevelBasedFormatter,
    format_by_level,
    getLogger,
)
from roki.firmware.params import Params


# ---------------------------------------------------------------------------
# Params singleton reset
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_params():
    """Reset the Params singleton so each test can configure it fresh."""
    Params._instance = None
    yield
    Params._instance = None


@pytest.fixture
def reset_logger_cache():
    """Clear adafruit_logging's internal logger cache between tests."""
    saved = dict(adafruit_logging_mod.logger_cache)
    adafruit_logging_mod.logger_cache.clear()
    yield
    adafruit_logging_mod.logger_cache.clear()
    adafruit_logging_mod.logger_cache.update(saved)


# ---------------------------------------------------------------------------
# format_by_level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "level,expected_label",
    [
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARNING"),
        (40, "ERROR"),
        (50, "CRITICAL"),
    ],
)
def test_format_by_level_contains_level_label(level: int, expected_label: str):
    fmt = format_by_level(level)

    assert expected_label in fmt
    # Logging placeholders we expect to be present
    assert "%(message)s" in fmt
    assert "%(created)s" in fmt
    assert "%(name)s" in fmt


def test_format_by_level_includes_ansi_reset():
    fmt = format_by_level(20)
    # reset code should appear to terminate colored segments
    assert "\x1b[0m" in fmt


def test_format_by_level_unknown_level_raises():
    # Implementation uses dict indexing with no default, so unknown levels fail
    with pytest.raises(KeyError):
        format_by_level(9999)


# ---------------------------------------------------------------------------
# LevelBasedFormatter
# ---------------------------------------------------------------------------


_LEVEL_NAMES = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}


def _make_record(level: int, msg: str = "hello") -> adafruit_logging_mod.LogRecord:
    return adafruit_logging_mod.LogRecord(
        name="roki.test",
        levelno=level,
        levelname=_LEVEL_NAMES[level],
        msg=msg,
        created=0.0,
        args=None,
    )


def test_level_based_formatter_includes_message_and_name():
    formatter = LevelBasedFormatter()
    record = _make_record(20, "my-message")

    output = formatter.format(record)

    assert "my-message" in output
    assert "roki.test" in output
    assert "INFO" in output  # level label present in output


def test_level_based_formatter_differs_per_level():
    formatter = LevelBasedFormatter()

    info_out = formatter.format(_make_record(20, "x"))
    error_out = formatter.format(_make_record(40, "x"))

    assert "INFO" in info_out
    assert "ERROR" in error_out
    assert info_out != error_out


# ---------------------------------------------------------------------------
# getLogger
# ---------------------------------------------------------------------------


def test_get_logger_returns_adafruit_logger(
    reset_params, reset_logger_cache,
):
    Params(debug=False, log_level=0)

    logger = getLogger("roki.test.nodebug")

    assert isinstance(logger, adafruit_logging_mod.Logger)


def test_get_logger_without_debug_uses_null_handler(
    reset_params, reset_logger_cache,
):
    Params(debug=False, log_level=0)

    logger = getLogger("roki.test.null")

    assert len(logger._handlers) >= 1
    # Last handler added by getLogger should be the NullHandler
    handler = logger._handlers[-1]
    assert isinstance(handler, adafruit_logging_mod.NullHandler)
    assert logger.getEffectiveLevel() == 0


def test_get_logger_with_debug_uses_stream_handler(
    reset_params, reset_logger_cache,
):
    Params(debug=True, log_level=20)

    logger = getLogger("roki.test.debug")

    handler = logger._handlers[-1]
    assert isinstance(handler, adafruit_logging_mod.StreamHandler)
    assert not isinstance(handler, adafruit_logging_mod.NullHandler)
    assert isinstance(handler.formatter, LevelBasedFormatter)
    assert logger.getEffectiveLevel() == 20


def test_get_logger_default_name(
    reset_params, reset_logger_cache,
):
    Params(debug=False, log_level=0)

    logger = getLogger()

    assert isinstance(logger, adafruit_logging_mod.Logger)
