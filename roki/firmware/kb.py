import adafruit_ble
import board
import rotaryio  # type: ignore
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID
from roki.firmware.service import RokiService
from roki.firmware.utils import diff_bitmaps, to_bytes


class Debouncer:
    def __init__(self, initial_value: int):
        self.value = initial_value
        self.last_value = initial_value

    def update(self, value: int):
        self.last_value = self.value
        self.value = value

    @property
    def changed(self):
        return self.last_value != self.value

    @property
    def rose(self):
        return self.value > self.last_value

    @property
    def fell(self):
        return self.value < self.last_value

    @property
    def diff(self):
        return self.value - self.last_value


class Roki:
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
        self.enc = Debouncer(self.encoder.position)
        self.connection_interval = connection_interval
        self.key_matrix = KeyMatrix(
            row_pins=tuple(getattr(board, pin) for pin in row_pins),
            column_pins=tuple(getattr(board, pin) for pin in column_pins),
            columns_to_anodes=columns_to_anodes,
            interval=interval,
            max_events=max_events,
        )
        self.config = Config.read()

    def run(self):
        if self.config.is_left_side:
            print("Run as central")
            self.run_as_central()
        else:
            print("Run as peripheral")
            self.run_as_peripheral()

    def run_as_central(self):
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

        ccw = Debouncer(0)
        cw = Debouncer(0)
        buffer = bytearray(self.row_count + 2)
        curr_bitmap = bytearray(self.row_count)
        last_bitmap = bytearray(self.row_count)

        ble = adafruit_ble.BLERadio()
        ble.name = "Roki"

        disconnect(ble)

        peripheral_conn = connect_to_peripheral_side(ble, self.connection_interval)

        print("advertising")
        ble.start_advertising(advertisement, scan_response)

        while True:
            while not ble.connected:
                pass

            while ble.connected:
                event = self.key_matrix.events.get()
                if event:
                    row, col = get_coords(event.key_number, self.col_count)

                    key = self.config.layer.primary_keys[row][col]

                    if event.pressed:
                        key.press()
                    else:
                        key.release()

                self.enc.update(self.encoder.position)
                if self.enc.rose:
                    for _ in range(self.enc.diff):
                        self.config.layer.primary_encoder_cw.press()
                        self.config.layer.primary_encoder_cw.release()
                elif self.enc.fell:
                    for _ in range(-self.enc.diff):
                        self.config.layer.primary_encoder_ccw.press()
                        self.config.layer.primary_encoder_ccw.release()

                if peripheral_conn.connected:
                    service: RokiService = peripheral_conn[RokiService]  # type: ignore

                    service.readinto(buffer)
                    _cw, _ccw = buffer[self.row_count :]
                    ccw.update(_ccw)
                    cw.update(_cw)
                    if ccw.changed and ccw.value:
                        self.config.layer.secondary_encoder_cw.press()
                        self.config.layer.secondary_encoder_cw.release()
                    if cw.changed and cw.value:
                        self.config.layer.secondary_encoder_ccw.press()
                        self.config.layer.secondary_encoder_ccw.release()

                    curr_bitmap = buffer[: self.row_count]
                    for (row, col), pressed in diff_bitmaps(last_bitmap, curr_bitmap):
                        key = self.config.layer.secondary_keys[row][col]

                        if pressed:
                            key.press()
                        else:
                            key.release()

                    print(".", end="")
                    last_bitmap[:] = curr_bitmap
                else:
                    peripheral_conn = connect_to_peripheral_side(
                        ble, self.connection_interval
                    )

            ble.start_advertising(advertisement)

    def run_as_peripheral(self):
        ble = adafruit_ble.BLERadio()
        service = RokiService()
        advertisement = ProvideServicesAdvertisement(service)
        matrix_buffer = [[False] * self.col_count for _ in range(self.row_count)]
        keys_bytes = bytes(self.row_count)

        disconnect(ble)

        while True:
            print("Advertise Roki peripheral...")
            ble.stop_advertising()
            ble.start_advertising(advertisement)

            while not ble.connected:
                pass

            print("Connected")
            while ble.connected:
                self.enc.update(self.encoder.position)
                if self.enc.rose:
                    service.write(bytes(self.row_count) + bytes((self.enc.diff, 0)))
                elif self.enc.fell:
                    service.write(bytes(self.row_count) + bytes((0, -self.enc.diff)))
                else:
                    service.write(bytes(self.row_count) + bytes((0, 0)))

                if event := self.key_matrix.events.get():
                    row, col = get_coords(event.key_number, self.col_count)

                    matrix_buffer[row][col] = event.pressed

                    keys_bytes = to_bytes(matrix_buffer)
                    service.write(keys_bytes + bytes((0, 0)))

                print("Service updated.")


class Primary:
    def run(self):
        pass


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


def disconnect(ble: adafruit_ble.BLERadio):
    if ble.connected:
        print("already connected")
        for conn in ble.connections:
            if conn:
                conn.disconnect()


def connect_to_peripheral_side(
    ble: adafruit_ble.BLERadio,
    connection_interval: float,
) -> adafruit_ble.BLEConnection:
    peripheral_conn: adafruit_ble.BLEConnection | None = None
    while peripheral_conn is None:
        print("Scanning for peripheral keyboard side...")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if RokiService in adv.services:  # type: ignore
                peripheral_conn = ble.connect(adv)
                peripheral_conn.connection_interval = connection_interval
                print("Connected")
                break
        ble.stop_scan()
    return peripheral_conn
