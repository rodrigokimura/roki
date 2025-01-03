import adafruit_ble
import board
import rotaryio  # type: ignore
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from analogio import AnalogIn
from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID, KeyWrapper
from roki.firmware.service import RokiService
from roki.firmware.utils import (
    Cycle,
    Debouncer,
    decode_vector,
    encode_vector,
    get_coords,
)


class Roki:
    @classmethod
    def build(
        cls,
        row_pins: tuple[str, ...],
        column_pins: tuple[str, ...],
        thumb_stick_pins: tuple[str, str],
        encoder_pins: tuple[str, str],
        encoder_divisor: int = 4,
        columns_to_anodes: bool = False,
        interval: float = 0.001,
        max_events: int = 5,
        connection_interval: float = 7.5,
    ):
        config = Config.read()
        return (Primary if config.is_left_side else Secondary)(
            row_pins,
            column_pins,
            thumb_stick_pins,
            encoder_pins,
            encoder_divisor,
            columns_to_anodes,
            interval,
            max_events,
            connection_interval,
        )

    def __init__(
        self,
        row_pins: tuple[str, ...],
        column_pins: tuple[str, ...],
        thumb_stick_pins: tuple[str, str],
        encoder_pins: tuple[str, str],
        encoder_divisor: int = 4,
        columns_to_anodes: bool = False,
        interval: float = 0.01,
        max_events: int = 5,
        connection_interval: float = 7.5,
    ):
        self.row_count = len(row_pins)
        self.col_count = len(column_pins)
        a, b = encoder_pins
        self.encoder = rotaryio.IncrementalEncoder(
            getattr(board, a), getattr(board, b), encoder_divisor
        )

        x, y = thumb_stick_pins
        self.thumb_stick_x = AnalogIn(getattr(board, x))
        self.thumb_stick_y = AnalogIn(getattr(board, y))

        self.encoder_position = Debouncer(self.encoder.position)
        self.connection_interval = connection_interval
        self.key_matrix = KeyMatrix(
            row_pins=tuple(getattr(board, pin) for pin in row_pins),
            column_pins=tuple(getattr(board, pin) for pin in column_pins),
            columns_to_anodes=columns_to_anodes,
            interval=interval,
            max_events=max_events,
        )
        self.config = Config.read()
        self.ble = adafruit_ble.BLERadio()

    async def run(self):
        pass

    def disconnect(self):
        if self.ble.connected:
            print("already connected")
            for conn in self.ble.connections:
                if conn:
                    conn.disconnect()


class Primary(Roki):
    async def run(self):
        DeviceInfoService(
            software_revision=adafruit_ble.__version__,
            manufacturer="Adafruit Industries",
        )
        advertisement = ProvideServicesAdvertisement(HID)
        # Advertise as "Keyboard" (0x03C1) icon when pairing
        # https://www.bluetooth.com/specifications/assigned-numbers/
        advertisement.appearance = 961
        scan_response = Advertisement()
        scan_response.complete_name = "Roki"

        self.ble.name = "Roki"

        self.disconnect()

        self.peripheral_conn = self.connect_to_peripheral_side(self.connection_interval)

        print("advertising")
        self.ble.start_advertising(advertisement, scan_response)
        self.buffer = bytearray(3)
        self.current_counter = 0

        while True:
            while not self.ble.connected:
                pass

            while self.ble.connected:
                await self.process_primary_keys()
                await self.process_primary_encoder()
                await self.process_primary_thumb_stick()

                if self.peripheral_conn.connected:
                    counter, message_id, payload = self.get_message()
                    if self.current_counter != counter:
                        self.current_counter = counter
                        if message_id < 30:
                            row, col = get_coords(message_id)
                            key = self.config.layer.secondary_keys[row][col]
                            self.process_key(key, bool(payload))
                        elif message_id == 30:
                            for _ in range(payload):
                                self.config.layer.secondary_encoder_cw.press()
                                self.config.layer.secondary_encoder_cw.release()
                        elif message_id == 31:
                            for _ in range(payload):
                                self.config.layer.secondary_encoder_ccw.press()
                                self.config.layer.secondary_encoder_ccw.release()
                        elif message_id == 32:
                            x, y = decode_vector(payload)
                            x -= 7.5
                            y -= 7.5
                            self._process_thumb_stick(x, y)

                else:
                    self.peripheral_conn = self.connect_to_peripheral_side(
                        self.connection_interval
                    )

            self.ble.start_advertising(advertisement)

    def get_message(self):
        service: RokiService = self.peripheral_conn[RokiService]  # type: ignore
        service.readinto(self.buffer)
        return self.buffer[0], self.buffer[1], self.buffer[2]

    async def process_primary_thumb_stick(self):
        x = self.thumb_stick_x.value // 4096 - 7.5
        y = self.thumb_stick_y.value // 4096 - 7.5
        self._process_thumb_stick(x, y)

    def _process_thumb_stick(self, x: float, y: float):
        from .keys import mouse

        mouse.move(int(x), int(y))

    async def process_primary_encoder(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            for _ in range(self.encoder_position.diff):
                self.config.layer.primary_encoder_cw.press()
                self.config.layer.primary_encoder_cw.release()
        elif self.encoder_position.fell:
            for _ in range(-self.encoder_position.diff):
                self.config.layer.primary_encoder_ccw.press()
                self.config.layer.primary_encoder_ccw.release()

    async def process_primary_keys(self):
        event = self.key_matrix.events.get()
        if event:
            row, col = get_coords(event.key_number, self.col_count)

            key = self.config.layer.primary_keys[row][col]
            self.process_key(key, event.pressed)

    def process_key(self, key: KeyWrapper, pressed: bool):
        if pressed:
            key.press()
        else:
            key.release()

    def connect_to_peripheral_side(
        self, connection_interval: float
    ) -> adafruit_ble.BLEConnection:
        peripheral_conn: adafruit_ble.BLEConnection | None = None
        while peripheral_conn is None:
            print("Scanning for peripheral keyboard side...")
            for adv in self.ble.start_scan(
                ProvideServicesAdvertisement, buffer_size=256  # type: ignore
            ):
                if RokiService in adv.services:  # type: ignore
                    peripheral_conn = self.ble.connect(adv)
                    peripheral_conn.connection_interval = connection_interval
                    print("Connected")
                    break
            self.ble.stop_scan()
        return peripheral_conn


class Secondary(Roki):
    async def run(self):
        self.service = RokiService()
        advertisement = ProvideServicesAdvertisement(self.service)

        self.disconnect()

        self.counter = Cycle()
        self.send_thumb_stick_message = False

        while True:
            print("Advertise Roki peripheral...")
            self.ble.stop_advertising()
            self.ble.start_advertising(advertisement)

            while not self.ble.connected:
                pass

            print("Connected")
            while self.ble.connected:
                await self.process_encoder()
                await self.process_keys()
                await self.process_thumb_stick()

    async def process_encoder(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            message_id = 30
            payload = self.encoder_position.diff
            await self.send_message(message_id, payload)
        elif self.encoder_position.fell:
            message_id = 31
            payload = -self.encoder_position.diff
            await self.send_message(message_id, payload)

    async def process_keys(self):
        if event := self.key_matrix.events.get():
            message_id = event.key_number
            payload = int(event.pressed)
            await self.send_message(message_id, payload)

    async def process_thumb_stick(self):
        x = self.thumb_stick_x.value // 4096
        y = self.thumb_stick_y.value // 4096
        message_id = 32
        if x > 0 or y > 0:
            payload = encode_vector(x, y)
            await self.send_message(message_id, payload)
            self.send_thumb_stick_message = True
        elif self.send_thumb_stick_message:
            payload = encode_vector(x, y)
            await self.send_message(message_id, payload)
            self.send_thumb_stick_message = False

    async def send_message(self, message_id: int, payload: int):
        self.counter.increment()
        self.service.write(bytes((self.counter.value, message_id, payload)))
