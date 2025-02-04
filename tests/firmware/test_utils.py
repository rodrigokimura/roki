from unittest.mock import MagicMock, patch

import pytest

from roki.firmware.utils import (
    Cycle,
    Debouncer,
    Loop,
    decode_float,
    decode_vector,
    encode_float,
    encode_vector,
    get_coords,
)


@pytest.fixture
def cycle():
    return Cycle()


@pytest.fixture
def debouncer():
    return Debouncer(0)


@pytest.fixture
def mock_sleep():
    with patch("time.sleep") as m:
        yield m


def test_encode_vector():
    result = encode_vector(5, 7)
    assert result == 87


def test_decode_vector():
    result = decode_vector(87)
    assert result == (5, 7)


def test_encode_float():
    assert encode_float(-1) == 255
    assert encode_float(1) == 127
    assert encode_float(0) == 0


def test_decode_float():
    assert decode_float(0) == 0
    assert decode_float(127) == 1
    assert decode_float(255) == -1


def test_loop():
    loop = Loop(5)
    i = 0
    for i in loop.iterate():
        i += 1

    assert i == 5


def test_cycle(cycle: Cycle):
    assert cycle.value == 0
    cycle.increment()
    assert cycle.value == 1
    cycle.value = 99
    cycle.increment()
    assert cycle.value == 0


def test_debouncer(debouncer: Debouncer):
    debouncer.update(1)
    assert debouncer.changed is True
    assert debouncer.rose is True
    assert debouncer.fell is False
    assert debouncer.diff == 1


def test_get_coords():
    row, col = get_coords(18)
    assert row == 3
    assert col == 0


def test_blink_led(mock_sleep: MagicMock):
    from roki.firmware.utils import blink_led

    blink_led()

    mock_sleep.assert_called()
