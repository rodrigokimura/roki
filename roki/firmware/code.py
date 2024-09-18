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

ROWS = ["P0_24", "P1_00", "P0_11", "P1_04", "P1_06"]
COLS = ["P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02"]
COLUMNS_TO_ANODES = False
INTERVAL = 0.01
MAX_EVENTS = 30


def main():
    key_matrix = KeyMatrix(
        row_pins=tuple(getattr(board, pin) for pin in ROWS),
        column_pins=tuple(getattr(board, pin) for pin in COLS),
        columns_to_anodes=COLUMNS_TO_ANODES,
        interval=INTERVAL,
        max_events=MAX_EVENTS,
    )

    config = Config.read()
    if config.is_left_side:
        print("Run as central")
        run_as_central(key_matrix, config)
    else:
        print("Run as peripheral")
        run_as_peripheral(key_matrix, config)


def run_as_peripheral(key_matrix: KeyMatrix, _: Config):
    ble = adafruit_ble.BLERadio()
    service = RokiService()
    advertisement = ProvideServicesAdvertisement(service)
    matrix_buffer = [[False] * len(COLS) for _ in ROWS]

    while True:
        print("Advertise Roki peripheral...")
        ble.stop_advertising()
        ble.start_advertising(advertisement)

        while not ble.connected:
            pass

        print("Connected")
        while ble.connected:
            if event := key_matrix.events.get():
                row, col = get_coords(event.key_number, len(COLS))

                matrix_buffer[row][col] = event.pressed

                service.write(to_bytes(matrix_buffer))

                print("Service updated.")


def run_as_central(key_matrix: KeyMatrix, config: Config):
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

    curr_bitmap = bytearray(len(ROWS))
    last_bitmap = bytearray(len(ROWS))

    peripheral_conn: adafruit_ble.BLEConnection | None = None

    ble = adafruit_ble.BLERadio()
    ble.name = "Roki"
    if ble.connected:
        print("already connected")
        for conn in ble.connections:
            if conn:
                conn.disconnect()

    if not peripheral_conn:
        print("Scanning for peripheral keyboard side...")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if RokiService in adv.services:  # type: ignore
                peripheral_conn = ble.connect(adv)
                print("Connected")
                break
        ble.stop_scan()

    print("advertising")
    ble.start_advertising(advertisement, scan_response)

    while True:
        while not ble.connected:
            pass

        while ble.connected:
            event = key_matrix.events.get()
            if event:
                row, col = get_coords(event.key_number, len(COLS))

                key = config.layer.primary_keys[row][col]

                if event.pressed:
                    key.press()
                else:
                    key.release()

            if peripheral_conn and peripheral_conn.connected:
                service: RokiService = peripheral_conn[RokiService]  # type: ignore

                service.readinto(curr_bitmap)

                for (row, col), pressed in diff_bitmaps(last_bitmap, curr_bitmap):
                    key = config.layer.secondary_keys[row][col]

                    if pressed:
                        key.press()
                    else:
                        key.release()

                last_bitmap[:] = curr_bitmap

        ble.start_advertising(advertisement)


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


if __name__ == "__main__":
    main()
