from roki.firmware.utils import Cycle, Debouncer, get_coords
import pytest


@pytest.fixture
def cycle():
    return Cycle()


@pytest.fixture
def debouncer():
    return Debouncer(0)


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
