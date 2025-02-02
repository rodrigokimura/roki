import board
import rotaryio
from adafruit_ble import BLEConnection, BLERadio
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull
from keypad import KeyMatrix

from roki.firmware.calibration import BaseCalibration, Calibration
from roki.firmware.config import Config
from roki.firmware.keys import HID, KeyWrapper
from roki.firmware.messages import ENCODER, KEY, THUMB_STICK
from roki.firmware.service import RokiService
from roki.firmware.utils import (
    Cycle,
    Debouncer,
    Loop,
    decode_float,
    encode_float,
    get_coords,
)


class Roki:
    @classmethod
    def build(
        cls,
        row_pins: tuple[str, ...],
        column_pins: tuple[str, ...],
        thumb_stick_pins: tuple[str, str, str],
        encoder_pins: tuple[str, str],
        encoder_divisor: int = 4,
        columns_to_anodes: bool = False,
        interval: float = 0.001,
        max_events: int = 5,
        connection_interval: float = 7.5,
        calibration_class: type[BaseCalibration] = Calibration,
        max_iterations_main_loop: int | None = None,
        max_iterations_ble: int | None = None,
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
            calibration_class,
            max_iterations_main_loop,
            max_iterations_ble,
        )

    def __init__(
        self,
        row_pins: tuple[str, ...],
        column_pins: tuple[str, ...],
        thumb_stick_pins: tuple[str, str, str],
        encoder_pins: tuple[str, str],
        encoder_divisor: int = 4,
        columns_to_anodes: bool = False,
        interval: float = 0.01,
        max_events: int = 5,
        connection_interval: float = 7.5,
        calibration_class: type[BaseCalibration] = Calibration,
        max_iterations_main_loop: int | None = None,
        max_iterations_ble: int | None = None,
    ):
        self.row_count = len(row_pins)
        self.col_count = len(column_pins)
        a, b = encoder_pins
        self.encoder = rotaryio.IncrementalEncoder(
            getattr(board, a), getattr(board, b), encoder_divisor
        )

        b, x, y = thumb_stick_pins

        thumb_stick_button = DigitalInOut(getattr(board, b))
        thumb_stick_button.direction = Direction.INPUT
        thumb_stick_button.pull = Pull.UP

        self.thumb_stick_x = AnalogIn(getattr(board, x))
        self.thumb_stick_y = AnalogIn(getattr(board, y))

        self.calibration = calibration_class(
            thumb_stick_button, self.thumb_stick_x, self.thumb_stick_y
        )

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
        self.ble = BLERadio()
        self.mouse_speed = 10
        self.max_iterations_main_loop = max_iterations_main_loop
        self.max_iterations_ble = max_iterations_ble

    async def run(self):
        print("Preparing...")
        self.start_calibration()

        print("Running...")
        await self.run_main_loop()

    async def run_main_loop(self): ...

    def start_calibration(self):
        self.calibration.start()

    def disconnect(self):
        if self.ble.connected:
            print("Already connected. Disconnecting...")
            for conn in self.ble.connections:
                if conn:
                    conn.disconnect()


class Primary(Roki):
    async def run_main_loop(self):
        DeviceInfoService(
            software_revision="0.1.0",
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
        self.buffer = bytearray(4)
        self.current_counter = 0

        for _ in Loop(self.max_iterations_main_loop).iterate():
            for _ in Loop(
                self.max_iterations_ble,
                lambda: self.ble.connected,
            ).iterate():
                pass

            for _ in Loop(
                self.max_iterations_ble,
                lambda: not self.ble.connected,
            ).iterate():
                await self.process_primary_keys()
                await self.process_primary_encoder()
                await self.process_primary_thumb_stick()

                if self.peripheral_conn.connected:
                    counter, message_id, payload_1, payload_2 = self.get_message()

                    if self.current_counter != counter:
                        self.current_counter = counter
                        self._handle_message(message_id, payload_1, payload_2)
                else:
                    self.peripheral_conn = self.connect_to_peripheral_side(
                        self.connection_interval
                    )

            self.ble.start_advertising(advertisement)

    def get_message(self):
        service: RokiService = self.peripheral_conn[RokiService]  # type: ignore
        return service.readinto(self.buffer)

    def _handle_message(self, message_id: int, payload_1: int, payload_2: int):
        if message_id == KEY:
            row, col = get_coords(payload_1)
            key = self.config.layer.secondary_keys[row][col]
            self._process_key_wrapper(key, bool(payload_2))
        elif message_id == ENCODER:
            for _ in range(payload_1):
                self.config.layer.secondary_encoder_cw.press()
                self.config.layer.secondary_encoder_cw.release()
            for _ in range(payload_2):
                self.config.layer.secondary_encoder_ccw.press()
                self.config.layer.secondary_encoder_ccw.release()
        elif message_id == THUMB_STICK:
            self._process_thumb_stick(decode_float(payload_1), decode_float(payload_2))

    async def process_primary_thumb_stick(self):
        x, y = self.calibration.get_normalized(
            self.thumb_stick_x.value, self.thumb_stick_y.value
        )
        self._process_thumb_stick(x, y)

    def _process_thumb_stick(self, x: float, y: float):
        from .keys import mouse

        if mouse is None:  # pragma: no cover
            return

        if x != 0 or y != 0:
            mouse.move(int(x * self.mouse_speed), int(y * self.mouse_speed))

    async def process_primary_encoder(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            for _ in range(self.encoder_position.diff):
                await self._process_encoder_cw()
        elif self.encoder_position.fell:
            for _ in range(-self.encoder_position.diff):
                await self._process_encoder_ccw()

    async def _process_encoder_cw(self):
        self.config.layer.primary_encoder_cw.press()
        self.config.layer.primary_encoder_cw.release()

    async def _process_encoder_ccw(self):
        self.config.layer.primary_encoder_ccw.press()
        self.config.layer.primary_encoder_ccw.release()

    async def process_primary_keys(self):
        if event := self.key_matrix.events.get():
            print(event.key_number)

            row, col = get_coords(event.key_number, self.col_count)

            key = self.config.layer.primary_keys[row][col]
            self._process_key_wrapper(key, event.pressed)

    def _process_key_wrapper(self, key: KeyWrapper, pressed: bool):
        if pressed:
            key.press()
        else:
            key.release()

    def connect_to_peripheral_side(self, connection_interval: float) -> BLEConnection:
        peripheral_conn: BLEConnection | None = None
        while peripheral_conn is None:
            print("Scanning for peripheral keyboard side...")
            for adv in self.ble.start_scan(
                ProvideServicesAdvertisement,  # type: ignore
                buffer_size=256,
            ):
                if RokiService in adv.services:  # type: ignore
                    peripheral_conn = self.ble.connect(adv)
                    peripheral_conn.connection_interval = connection_interval
                    print("Connected")
                    break
            self.ble.stop_scan()
        return peripheral_conn


class Secondary(Roki):
    async def run_main_loop(self):
        self.service = RokiService()
        advertisement = ProvideServicesAdvertisement(self.service)

        self.disconnect()

        self.counter = Cycle()
        self.send_thumb_stick_message = False

        for _ in Loop(self.max_iterations_main_loop).iterate():
            print("Advertise Roki peripheral...")
            self.ble.stop_advertising()
            self.ble.start_advertising(advertisement)

            for _ in Loop(
                self.max_iterations_ble,
                lambda: self.ble.connected,
            ).iterate():
                pass

            print("Connected")
            for _ in Loop(
                self.max_iterations_ble,
                lambda: not self.ble.connected,
            ).iterate():
                await self.process_encoder()
                await self.process_keys()
                await self.process_thumb_stick()

    async def process_encoder(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            message_id = ENCODER
            payload = self.encoder_position.diff
            await self.send_message(message_id, (payload, 0))
        elif self.encoder_position.fell:
            message_id = ENCODER
            payload = -self.encoder_position.diff
            await self.send_message(message_id, (0, payload))

    async def process_keys(self):
        if event := self.key_matrix.events.get():
            message_id = KEY
            payload = int(event.pressed)
            await self.send_message(message_id, (event.key_number, payload))

    async def process_thumb_stick(self):
        x, y = self.calibration.get_normalized(
            self.thumb_stick_x.value, self.thumb_stick_y.value
        )
        message_id = THUMB_STICK
        if x != 0 or y != 0:
            await self.send_message(message_id, (encode_float(x), encode_float(y)))
            self.send_thumb_stick_message = True
        elif self.send_thumb_stick_message:
            await self.send_message(message_id, (0, 0))
            self.send_thumb_stick_message = False

    async def send_message(self, message_id: int, payload: tuple[int, int]):
        self.counter.increment()
        payload_1, payload_2 = payload
        self.service.write(
            bytes((self.counter.value, message_id, abs(payload_1), abs(payload_2)))
        )
