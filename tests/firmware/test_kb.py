from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
from itertools import cycle

from roki.firmware.messages import ENCODER, KEY, THUMB_STICK

if TYPE_CHECKING:
    from roki.firmware.calibration import BaseCalibration
    from roki.firmware.kb import Primary, Secondary


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


@pytest.fixture
def roki_params():
    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    buzzer_pin = "P0_06"
    encoder_pins = ("P0_17", "P0_20")
    thumb_stick_pins = ("P0_22", "AIN7", "AIN5")
    return rows, cols, buzzer_pin, thumb_stick_pins, encoder_pins


@pytest.fixture
def mocked_calibration():
    from roki.firmware.calibration import BaseCalibration

    class MockedCalibration(BaseCalibration):
        pass

    MockedCalibration._get_normalized_x = MagicMock()
    MockedCalibration._get_normalized_x.side_effect = cycle([0.0, 1.0])
    MockedCalibration._get_normalized_y = MagicMock()
    MockedCalibration._get_normalized_y.side_effect = cycle([0.0, 1.0])

    return MockedCalibration


@pytest.fixture
def main_loop_max_iter(request):
    return int(getattr(request, "param", 1))


@pytest.fixture
def ble_max_iter(request):
    return int(getattr(request, "param", 1))


@pytest.fixture
def primary(
    roki_params,
    mocked_calibration: type["BaseCalibration"],
    main_loop_max_iter: int,
    ble_max_iter: int,
):
    from roki.firmware.kb import Primary, Roki

    primary = Primary(
        *roki_params,
        calibration_class=mocked_calibration,
        max_iterations_main_loop=main_loop_max_iter,
        max_iterations_ble=ble_max_iter,
    )
    assert isinstance(primary, Roki)
    return primary


@pytest.fixture
def secondary(
    roki_params,
    mocked_calibration: type["BaseCalibration"],
    main_loop_max_iter: int,
    ble_max_iter: int,
):
    from roki.firmware.kb import Roki, Secondary

    secondary = Secondary(
        *roki_params,
        calibration_class=mocked_calibration,
        max_iterations_main_loop=main_loop_max_iter,
        max_iterations_ble=ble_max_iter,
    )
    assert isinstance(secondary, Roki)
    return secondary


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
def mock_received_message():
    m = MagicMock()
    m.return_value = (0, KEY, 0, 0)
    return m


@pytest.fixture
def mocked_roki_service(mock_received_message: MagicMock):
    m = MagicMock()
    m.write = lambda _: None
    m.readinto = mock_received_message
    return m


@pytest.fixture
def mock_roki_service(mocked_roki_service: MagicMock):
    with patch("roki.firmware.kb.RokiService") as m:
        m.return_value = mocked_roki_service
        yield mocked_roki_service


@pytest.fixture
def mock_ble_radio_connected():
    from roki.firmware.kb import BLERadio

    with patch.object(
        BLERadio, "connected", new_callable=PropertyMock
    ) as mock_connected:
        mock_connected.return_value = True
        yield mock_connected


@pytest.fixture
def ble_connection(
    mocked_roki_service: MagicMock,
):
    connection = MagicMock()
    connection.__getitem__ = lambda *_: mocked_roki_service
    connection.connected = True
    return connection


@pytest.fixture
def mock_ble_radio_start_scan(
    ble_connection: MagicMock,
):
    from roki.firmware.kb import BLERadio
    from roki.firmware.service import RokiService

    with (
        patch.object(BLERadio, "start_scan") as mock_start_scan,
        patch.object(BLERadio, "connect") as mock_connect,
        patch.object(
            BLERadio, "connections", new_callable=PropertyMock
        ) as mock_connections,
        patch.object(
            BLERadio, "connected", new_callable=PropertyMock
        ) as mock_connected,
    ):
        advertisement = MagicMock()
        advertisement.services = [RokiService]
        mock_start_scan.return_value = [advertisement]
        mock_connect.return_value = ble_connection
        mock_connected.return_value = True
        mock_connections.return_value = [MagicMock()]
        yield mock_connect, mock_connected


@pytest.fixture
def mock_debouncer():
    from roki.firmware.kb import Debouncer

    with (
        patch.object(Debouncer, "rose", new_callable=PropertyMock) as mock_rose,
        patch.object(Debouncer, "fell", new_callable=PropertyMock) as mock_fell,
        patch.object(Debouncer, "diff", new_callable=PropertyMock) as mock_diff,
    ):
        mock_rose.return_value = False
        mock_fell.return_value = False
        mock_diff.return_value = 0
        yield (mock_rose, mock_fell, mock_diff)


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


def test_factory_method(roki_params):
    from roki.firmware.kb import Roki

    roki = Roki.build(*roki_params)
    assert isinstance(roki, Roki)


@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
def test_primary_run_with_disconnection(
    mock_ble_radio_start_scan: tuple[MagicMock, MagicMock],
    ble_connection: MagicMock,
    primary: "Primary",
):
    _, connected = mock_ble_radio_start_scan
    ble_connection.connected = False
    connected.side_effect = cycle(
        [
            False,
            False,
            True,
            True,
        ]
    )
    primary.run()


@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
)
def test_primary_run_with_local_key_press(
    primary: "Primary",
    mock_key_events: MagicMock,
):
    event = MagicMock()
    event.key_number = 1
    event.pressed.side_effect = cycle([False, True])
    mock_key_events.return_value = event
    with patch.object(
        primary, "_process_key_wrapper", wraps=primary._process_key_wrapper
    ) as m:
        primary.run()
        m.assert_called()


@pytest.mark.parametrize("ble_max_iter", [2], indirect=True)
@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
def test_primary_run_with_local_encoder(
    primary: "Primary",
    mock_debouncer: tuple[MagicMock, MagicMock, MagicMock],
):
    rose, fell, diff = mock_debouncer
    rose.side_effect = cycle([False, True])
    fell.side_effect = cycle([True, False])
    diff.side_effect = cycle([-1, 1])
    with (
        patch.object(
            primary, "_process_encoder_cw", wraps=primary._process_encoder_cw
        ) as m_cw,
        patch.object(
            primary, "_process_encoder_ccw", wraps=primary._process_encoder_ccw
        ) as m_ccw,
    ):
        primary.run()
        m_cw.assert_called()
        m_ccw.assert_called()


@pytest.mark.parametrize("ble_max_iter", [2], indirect=True)
@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
def test_primary_run_with_remote_key_press(
    primary: "Primary",
    mock_received_message: MagicMock,
):
    mock_received_message.side_effect = cycle(
        [
            (1, KEY, 1, 0),
            (2, KEY, 1, 1),
        ]
    )
    with patch.object(primary, "_handle_message", wraps=primary._handle_message) as m:
        primary.run()

        assert call(KEY, 1, 0) in m.call_args_list
        assert call(KEY, 1, 1) in m.call_args_list


@pytest.mark.parametrize("ble_max_iter", [2], indirect=True)
@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
def test_primary_run_with_remote_thumb_stick_tilt(
    primary: "Primary",
    mock_received_message: MagicMock,
):
    mock_received_message.side_effect = cycle(
        [
            (1, THUMB_STICK, 0, 0),
            (2, THUMB_STICK, 1, 1),
        ]
    )
    with patch.object(primary, "_handle_message", wraps=primary._handle_message) as m:
        primary.run()

        assert call(THUMB_STICK, 0, 0) in m.call_args_list
        assert call(THUMB_STICK, 1, 1) in m.call_args_list


@pytest.mark.usefixtures(
    "mock_device_info_service",
    "mock_provide_services_advertisement",
    "mock_ble_radio_start_scan",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
)
def test_primary_run_with_remote_encoder(
    primary: "Primary",
    mock_received_message: MagicMock,
):
    mock_received_message.return_value = (99, ENCODER, 1, 1)
    with patch.object(primary, "_handle_message", wraps=primary._handle_message) as m:
        primary.run()
        m.assert_called_with(ENCODER, 1, 1)


@pytest.mark.usefixtures(
    "mock_provide_services_advertisement",
    "mock_debouncer",
    "mock_roki_service",
)
def test_secondary_run(secondary: "Secondary"):
    secondary.run()


@pytest.mark.usefixtures(
    "mock_provide_services_advertisement",
    "mock_debouncer",
    "mock_mouse",
    "mock_key_events",
    "mock_roki_service",
)
def test_secondary_run_with_disconnection(
    mock_ble_radio_start_scan: tuple[MagicMock, MagicMock],
    ble_connection: MagicMock,
    secondary: "Secondary",
):
    _, connected = mock_ble_radio_start_scan
    ble_connection.connected = False
    connected.side_effect = cycle(
        [
            False,
            False,
            True,
            True,
        ]
    )
    secondary.run()


@pytest.mark.parametrize("ble_max_iter", [2], indirect=True)
@pytest.mark.parametrize("main_loop_max_iter", [2], indirect=True)
@pytest.mark.usefixtures(
    "mock_provide_services_advertisement",
    "mock_mouse",
    "mock_key_events",
    "mock_roki_service",
)
def test_secondary_run_with_encoder(
    secondary: "Secondary", mock_debouncer: tuple[MagicMock, MagicMock, MagicMock]
):
    rose, fell, diff = mock_debouncer
    rose.side_effect = cycle([True, False])
    fell.side_effect = cycle([False, True])
    diff.side_effect = cycle([1, -1])
    with patch.object(secondary, "send_message", wraps=secondary.send_message) as m:
        secondary.run()
        assert call(2, (1, 0)) in m.call_args_list
        assert call(3, (127, 127)) in m.call_args_list
        assert call(3, (0, 0)) in m.call_args_list


@pytest.mark.parametrize("ble_max_iter", [2], indirect=True)
@pytest.mark.usefixtures(
    "mock_provide_services_advertisement",
    "mock_debouncer",
    "mock_mouse",
    "mock_roki_service",
)
def test_secondary_run_with_key_press(
    secondary: "Secondary",
    mock_key_events: MagicMock,
):
    event_pressed = MagicMock()
    event_pressed.key_number = 1
    event_pressed.pressed = True
    event_released = MagicMock()
    event_released.key_number = 1
    event_released.pressed = False
    mock_key_events.side_effect = cycle([event_pressed, event_released])
    with patch.object(secondary, "send_message", wraps=secondary.send_message) as m:
        secondary.run()
        assert call(KEY, (1, 1)) in m.call_args_list
        assert call(KEY, (1, 0)) in m.call_args_list
