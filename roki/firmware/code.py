import adafruit_ble
import board
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID
from roki.firmware.service import RokiService

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


def run_as_peripheral(key_matrix: KeyMatrix, config: Config):
    ble = adafruit_ble.BLERadio()
    service = RokiService()
    advertisement = ProvideServicesAdvertisement(service)

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
                service.row = row
                service.column = col
                service.state = int(event.pressed)
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

    per_conn: adafruit_ble.BLEConnection | None = None

    ble = adafruit_ble.BLERadio()
    ble.name = "Roki"
    if ble.connected:
        print("already connected")
        for conn in ble.connections:
            if conn:
                conn.disconnect()

    if not per_conn:
        print("Scanning for peripheral keyboard side...")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if RokiService in adv.services:  # type: ignore
                per_conn = ble.connect(adv)
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
                print(key.key_names)

                if event.pressed:
                    key.press()
                else:
                    key.release()
            if per_conn and per_conn.connected:
                s: RokiService = per_conn[RokiService]  # type: ignore
                print(s.row, s.column)

        ble.start_advertising(advertisement)


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


if __name__ == "__main__":
    main()
