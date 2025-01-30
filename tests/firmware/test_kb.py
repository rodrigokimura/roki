from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.calibration import BaseCalibration
    from roki.firmware.kb import Primary, Secondary


@pytest.fixture(autouse=True)
def mock_config_json():
    with open("roki/firmware/config.json") as f:
        config = f.read()
    with patch("builtins.open", mock_open(read_data=config)) as mock_file:
        yield mock_file


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


@pytest.fixture
def roki_params():
    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    encoder_pins = ("P0_17", "P0_20")
    thumb_stick_pins = ("P0_22", "AIN7", "AIN5")
    return rows, cols, thumb_stick_pins, encoder_pins


@pytest.fixture
def mocked_calibration():
    from roki.firmware.calibration import BaseCalibration

    class MockedCalibration(BaseCalibration):
        def _get_normalized_x(self, x: int) -> float:
            return 0.0

        def _get_normalized_y(self, y: int) -> float:
            return 0.0

    return MockedCalibration


@pytest.fixture
def primary(
    roki_params,
    mocked_calibration: type["BaseCalibration"],
):
    from roki.firmware.kb import Primary, Roki

    p = Primary(
        *roki_params,
        calibration_class=mocked_calibration,
        max_iterations_main_loop=1,
        max_iterations_ble=1,
    )

    assert isinstance(p, Roki)

    return p


@pytest.fixture
def secondary(
    roki_params,
    mocked_calibration: type["BaseCalibration"],
):
    from roki.firmware.kb import Roki, Secondary

    s = Secondary(
        *roki_params,
        calibration_class=mocked_calibration,
        max_iterations_main_loop=1,
        max_iterations_ble=1,
    )

    assert isinstance(s, Roki)

    return s


def test_factory_method(roki_params):
    from roki.firmware.kb import Roki

    r = Roki.build(*roki_params)

    assert isinstance(r, Roki)


@pytest.fixture
def mock_device_info_service():
    with patch("roki.firmware.kb.DeviceInfoService") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_provide_services_advertisement():
    with patch("roki.firmware.kb.ProvideServicesAdvertisement") as m:
        yield m


@pytest.fixture
def mock_ble_radio_start_scan():
    from roki.firmware.kb import BLERadio
    from roki.firmware.service import RokiService

    with (
        patch.object(BLERadio, "start_scan") as mock_start_scan,
        patch.object(BLERadio, "connect") as mock_connect,
    ):
        mm = MagicMock()
        mm.services = [RokiService]
        mock_start_scan.return_value = [mm]
        mock_connect.return_value = MagicMock()
        yield mock_connect


@pytest.fixture
def mock_debouncer():
    from roki.firmware.utils import (
        Debouncer,
    )

    with (
        patch.object(Debouncer, "rose") as mock_rose,
        patch.object(Debouncer, "fell") as mock_fell,
    ):
        mock_rose.return_value = False
        mock_fell.return_value = False
        yield (mock_rose, mock_fell)


@pytest.fixture
def mock_mouse():
    with patch("roki.firmware.keys.mouse", MagicMock()) as m:
        yield m


@pytest.fixture
def mock_key_events():
    from keypad import EventQueue

    with patch.object(EventQueue, "get") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_roki_service():
    from roki.firmware.service import RokiService

    with patch.object(RokiService, "write") as m:
        m.return_value = ""
        yield m


@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
async def test_primary_run(primary: "Primary"):
    await primary.run()


@pytest.mark.usefixtures(
    "mock_provide_services_advertisement",
    "mock_debouncer",
    "mock_roki_service",
)
async def test_secondary_run(secondary: "Secondary"):
    await secondary.run()
