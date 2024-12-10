import pytest

rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")

encoder_pins = ("P0_17", "P0_20")


@pytest.mark.skip(reason="Add mocks")
def test_secondary():
    from roki.firmware.kb import Secondary

    s = Secondary(rows, cols, encoder_pins)
    pass
