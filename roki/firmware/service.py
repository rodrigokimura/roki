import _bleio
from adafruit_ble.attributes import Attribute
from adafruit_ble.characteristics import Characteristic, ComplexCharacteristic
from adafruit_ble.services import Service
from adafruit_ble.uuid import VendorUUID

from roki.firmware.keys import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from circuitpython_typing import ReadableBuffer, WriteableBuffer

BUFFER_SIZE = 4


class PacketBufferUUID(VendorUUID):
    def __init__(self, uuid16):
        uuid128 = bytearray("reffuBtekcaP".encode("utf-8") + b"\x00\x00\xaf\xad")
        uuid128[-3] = uuid16 >> 8
        uuid128[-4] = uuid16 & 0xFF
        super().__init__(uuid128)


class PacketBufferCharacteristic(ComplexCharacteristic):
    def __init__(
        self,
        *,
        uuid=None,
        buffer_size=4,
        properties=Characteristic.WRITE_NO_RESPONSE
        | Characteristic.NOTIFY
        | Characteristic.READ,
        read_perm=Attribute.OPEN,
        write_perm=Attribute.OPEN,
    ):
        self.buffer_size = buffer_size
        super().__init__(
            uuid=uuid,
            properties=properties,
            read_perm=read_perm,
            write_perm=write_perm,
            max_length=BUFFER_SIZE,
            fixed_length=False,
        )

    def bind(self, service: Service):  # type: ignore
        bound_characteristic = super().bind(service)
        return _bleio.PacketBuffer(
            bound_characteristic,
            buffer_size=self.buffer_size,
            max_packet_size=BUFFER_SIZE,
        )


class RokiService(Service):
    uuid = PacketBufferUUID(0x0001)

    packets = PacketBufferCharacteristic(uuid=PacketBufferUUID(0x0101))

    def readinto(self, buf: "WriteableBuffer") -> int:
        return self.packets.readinto(buf)  # type: ignore

    def write(self, buf: "ReadableBuffer", *, header: bytes | None = None) -> int:
        return self.packets.write(buf, header=header)  # type: ignore
