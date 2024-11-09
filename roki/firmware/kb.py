import adafruit_ble
import board
import rotaryio  # type: ignore
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID, KeyWrapper
from roki.firmware.service import RokiService
from roki.firmware.utils import Debouncer, diff_bitmaps, get_coords, to_bytes


class Roki:
    @classmethod
    def build(
        cls,
        row_pins: tuple[str, ...],
        column_pins: tuple[str, ...],
        encoder_pins: tuple[str, ...],
        encoder_divisor: int = 4,
        columns_to_anodes: bool = False,
        interval: float = 0.01,
        max_events: int = 5,
        connection_interval: float = 7.5,
    ):
        config = Config.read()
        return (Primary if config.is_left_side else Secondary)(
            row_pins,
            column_pins,
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
        encoder_pins: tuple[str, ...],
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

    def run(self):
        pass

    def disconnect(self):
        if self.ble.connected:
            print("already connected")
            for conn in self.ble.connections:
                if conn:
                    conn.disconnect()


class Primary(Roki):
    def run(self):
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

        self.secondary_encoder_ccw_bumps = Debouncer(0)
        self.secondary_encoder_cw_bumps = Debouncer(0)
        last_bitmap = bytearray(self.row_count)

        self.ble.name = "Roki"

        self.disconnect()

        self.peripheral_conn = self.connect_to_peripheral_side(self.connection_interval)

        print("advertising")
        self.ble.start_advertising(advertisement, scan_response)

        while True:
            while not self.ble.connected:
                pass

            while self.ble.connected:
                self.process_primary_keys()
                self.process_primary_encoder()

                if self.peripheral_conn.connected:
                    keys_state, encoder_state = self.get_secondary_state()
                    self.process_secondary_encoder(*encoder_state)
                    self.process_secondary_keys(last_bitmap, keys_state)
                    print(".", end="")
                else:
                    self.peripheral_conn = self.connect_to_peripheral_side(
                        self.connection_interval
                    )

            self.ble.start_advertising(advertisement)

    def get_secondary_state(self):
        buffer = bytearray(self.row_count + 2)
        service: RokiService = self.peripheral_conn[RokiService]  # type: ignore
        service.readinto(buffer)
        return buffer[: self.row_count], buffer[self.row_count :]

    def process_primary_encoder(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            for _ in range(self.encoder_position.diff):
                self.config.layer.primary_encoder_cw.press()
                self.config.layer.primary_encoder_cw.release()
        elif self.encoder_position.fell:
            for _ in range(-self.encoder_position.diff):
                self.config.layer.primary_encoder_ccw.press()
                self.config.layer.primary_encoder_ccw.release()

    def process_secondary_encoder(self, cw_bumps: int, ccw_bumps: int):
        self.secondary_encoder_ccw_bumps.update(ccw_bumps)
        self.secondary_encoder_cw_bumps.update(cw_bumps)
        if (
            self.secondary_encoder_ccw_bumps.changed
            and self.secondary_encoder_ccw_bumps.value
        ):
            self.config.layer.secondary_encoder_cw.press()
            self.config.layer.secondary_encoder_cw.release()
        if (
            self.secondary_encoder_cw_bumps.changed
            and self.secondary_encoder_cw_bumps.value
        ):
            self.config.layer.secondary_encoder_ccw.press()
            self.config.layer.secondary_encoder_ccw.release()

    def process_primary_keys(self):
        event = self.key_matrix.events.get()
        if event:
            row, col = get_coords(event.key_number, self.col_count)

            key = self.config.layer.primary_keys[row][col]
            self.process_key(key, event.pressed)

    def process_secondary_keys(
        self, last_bitmap: bytearray, curr_bitmap: bytes | bytearray
    ):
        for (row, col), pressed in diff_bitmaps(last_bitmap, curr_bitmap):
            key = self.config.layer.secondary_keys[row][col]
            self.process_key(key, pressed)
        last_bitmap[:] = curr_bitmap

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
                ProvideServicesAdvertisement, buffer_size=256
            ):
                if RokiService in adv.services:  # type: ignore
                    peripheral_conn = self.ble.connect(adv)
                    peripheral_conn.connection_interval = connection_interval
                    print("Connected")
                    break
            self.ble.stop_scan()
        return peripheral_conn


class Secondary(Roki):
    def run(self):
        self.service = RokiService()
        advertisement = ProvideServicesAdvertisement(self.service)
        self.matrix_buffer = [[False] * self.col_count for _ in range(self.row_count)]

        self.disconnect()

        while True:
            print("Advertise Roki peripheral...")
            self.ble.stop_advertising()
            self.ble.start_advertising(advertisement)

            while not self.ble.connected:
                pass

            print("Connected")
            while self.ble.connected:
                self.send_encoder_bumps()

                if event := self.key_matrix.events.get():
                    row, col = get_coords(event.key_number, self.col_count)

                    self.matrix_buffer[row][col] = event.pressed
                    self.send_keys()

                print("Service updated.")

    def send_encoder_bumps(self):
        self.encoder_position.update(self.encoder.position)
        if self.encoder_position.rose:
            self.service.write(
                bytes(self.row_count) + bytes((self.encoder_position.diff, 0))
            )
        elif self.encoder_position.fell:
            self.service.write(
                bytes(self.row_count) + bytes((0, -self.encoder_position.diff))
            )
        else:
            self.service.write(bytes(self.row_count) + bytes((0, 0)))

    def send_keys(self):
        keys_bytes = to_bytes(self.matrix_buffer)
        self.service.write(keys_bytes + bytes((0, 0)))
