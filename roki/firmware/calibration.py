import board
from digitalio import DigitalInOut, Direction


class Calibration:
    def __init__(self, button_pin: str = "P0_22"):
        self.button_pin = button_pin
        self.button = DigitalInOut(getattr(board, button_pin))  # type: ignore
        self.button.direction = Direction.INPUT

    def __enter__(self):
        print("entering calibration mode")

    def __exit__(self, exc_type, exc_value, traceback):
        print("exiting calibration mode")
        self.button.deinit()


def calibrate_thumb_stick():
    pass
