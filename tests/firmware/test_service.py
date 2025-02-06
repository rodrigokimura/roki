from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.service import RokiService


@pytest.fixture
def roki_service():
    from roki.firmware.service import RokiService

    service = RokiService()

    assert isinstance(service, RokiService)

    return service


@pytest.fixture
def mock_packet_buffer_characteristic():
    from roki.firmware.service import PacketBufferCharacteristic

    with patch.object(PacketBufferCharacteristic, "bind") as m:
        yield m


def test_roki_service_read(
    roki_service: "RokiService",
    mock_packet_buffer_characteristic: MagicMock,
):
    b = bytearray(4)
    r = roki_service.readinto(b)

    assert r == (0, 0, 0, 0)
    mock_packet_buffer_characteristic.assert_called()


def test_roki_service_read_no_value(
    roki_service: "RokiService",
    mock_packet_buffer_characteristic: MagicMock,
):
    with patch.object(roki_service, "packets") as m:
        m.readinto.return_value = None
        b = bytearray(4)
        r = roki_service.readinto(b)

    assert r == (0, 0, 0, 0)
    mock_packet_buffer_characteristic.assert_called()


def test_roki_service_write(
    roki_service: "RokiService",
    mock_packet_buffer_characteristic: MagicMock,
):
    roki_service.write(bytes((1, 2, 3, 4)))

    mock_packet_buffer_characteristic.assert_called()
