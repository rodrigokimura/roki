import json
import time

import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction


class Calibration:
    def __init__(
        self,
        button_pin: str = "P0_22",
        thumb_stick_x_pin: str = "AIN7",
        thumb_stick_y_pin: str = "AIN5",
    ):
        x, y = thumb_stick_x_pin, thumb_stick_y_pin
        self.button_pin = button_pin
        self.button = DigitalInOut(getattr(board, button_pin))  # type: ignore
        self.button.direction = Direction.INPUT
        self.thumb_stick_x = AnalogIn(getattr(board, x))
        self.thumb_stick_y = AnalogIn(getattr(board, y))
        self.max_x = -float("inf")
        self.min_x = float("inf")
        self.max_y = -float("inf")
        self.min_y = float("inf")

        self.running = True

    def start(self) -> None:
        if not self._startup_condition():
            return

        self._notify()

        # allow user to release the button
        time.sleep(1)

        while self.running:
            self.max_x = max(self.max_x, self.thumb_stick_x.value)
            self.min_x = min(self.min_x, self.thumb_stick_x.value)

            self.max_y = max(self.max_y, self.thumb_stick_y.value)
            self.min_y = min(self.min_y, self.thumb_stick_y.value)

            self._check_for_stop_criteria()

        self._write_config()

    def _startup_condition(self) -> bool:
        return self.button.value

    def _notify(self) -> None:
        pass

    def _check_for_stop_criteria(self) -> None:
        if self._startup_condition():
            self.running = False

    def _check_data(self):
        return (
            self.max_x != -float("inf")
            and self.max_y != -float("inf")
            and self.min_x != float("inf")
            and self.min_y != float("inf")
        )

    def _write_config(self) -> None:
        if not self._check_data():
            return

        data = {
            "max_x": self.max_x,
            "min_x": self.min_x,
            "max_y": self.max_y,
            "min_y": self.min_y,
        }

        with open("calibration.json", mode="w") as file:
            json.dump(data, file)

    def read(self):
        with open("calibration.json", mode="r") as file:
            data = json.load(file)

        self.max_x = float(data["max_x"])
        self.min_x = float(data["min_x"])
        self.max_y = float(data["max_y"])
        self.min_y = float(data["min_y"])
