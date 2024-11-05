import adafruit_ble
import board
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID
from roki.firmware.service import RokiService
from roki.firmware.utils import diff_bitmaps, to_bytes


class Roki:
    def __init__(
        self,
        rows: tuple[str, ...],
        cols: tuple[str, ...],
        columns_to_anodes: bool = False,
        interval: float = 0.01,
        max_events: int = 5,
        connection_interval: float = 7.5,
    ):
        self.rows = rows
        self.cols = cols
        self.connection_interval = connection_interval
        self.key_matrix = KeyMatrix(
            row_pins=tuple(getattr(board, pin) for pin in rows),
            column_pins=tuple(getattr(board, pin) for pin in cols),
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

        curr_bitmap = bytearray(len(self.rows))
        last_bitmap = bytearray(len(self.rows))

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
                    row, col = get_coords(event.key_number, len(self.cols))

                    key = self.config.layer.primary_keys[row][col]

                    if event.pressed:
                        key.press()
                    else:
                        key.release()

                if peripheral_conn.connected:
                    service: RokiService = peripheral_conn[RokiService]  # type: ignore

                    service.readinto(curr_bitmap)

                    for (row, col), pressed in diff_bitmaps(last_bitmap, curr_bitmap):
                        key = self.config.layer.secondary_keys[row][col]

                        if pressed:
                            key.press()
                        else:
                            key.release()

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
        matrix_buffer = [[False] * len(self.cols) for _ in self.rows]

        disconnect(ble)

        while True:
            print("Advertise Roki peripheral...")
            ble.stop_advertising()
            ble.start_advertising(advertisement)

            while not ble.connected:
                pass

            print("Connected")
            while ble.connected:
                if event := self.key_matrix.events.get():
                    row, col = get_coords(event.key_number, len(self.cols))

                    matrix_buffer[row][col] = event.pressed

                    service.write(to_bytes(matrix_buffer))

                    print("Service updated.")


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
