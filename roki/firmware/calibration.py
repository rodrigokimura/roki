import json
import time

from adafruit_ticks import ticks_ms
from analogio import AnalogIn
from digitalio import DigitalInOut

from roki.firmware.utils import Loop, blink_led


class BaseCalibration:
    def __init__(
        self,
        button: DigitalInOut,
        thumb_stick_x: AnalogIn,
        thumb_stick_y: AnalogIn,
        release_time: float = 5.0,
        mid_time: float = 5.0,
        max_iterations: int | None = None,
    ):
        self.button = button
        self.thumb_stick_x = thumb_stick_x
        self.thumb_stick_y = thumb_stick_y
        self.max_x = -float("inf")
        self.min_x = float("inf")
        self.mid_x = 0.0
        self.lower_mid_x = 0.0
        self.upper_mid_x = 0.0
        self.lower_mid_y = 0.0
        self.upper_mid_y = 0.0
        self.max_y = -float("inf")
        self.mid_y = 0.0
        self.min_y = float("inf")
        self.release_time = release_time
        self.mid_time = mid_time

        self.running = True
        self._read = False
        self._limit = 0.05
        self.max_iterations = max_iterations

    def start(self) -> None:
        print("Starting calibration...")

        if not self._startup_condition():
            return

        self._notify()

        # allow user to release the button
        time.sleep(self.release_time)

        self._get_mid_values()
        self._notify()

        for _ in Loop(self.max_iterations, lambda: not self.running).iterate():
            self.max_x = max(self.max_x, self.thumb_stick_x.value)
            self.min_x = min(self.min_x, self.thumb_stick_x.value)

            self.max_y = max(self.max_y, self.thumb_stick_y.value)
            self.min_y = min(self.min_y, self.thumb_stick_y.value)

            self._check_for_stop_criteria()

        self._write_config()

    def _startup_condition(self) -> bool: ...

    def _get_mid_values(self) -> None: ...

    def _notify(self) -> None: ...

    def _check_for_stop_criteria(self) -> None: ...

    def _write_config(self) -> None: ...

    def read(self): ...

    def get_normalized(self, x: int, y: int) -> tuple[float, float]:
        if self._read is False:
            self.read()

        return self._get_normalized_x(x), self._get_normalized_y(y)

    def _get_normalized_x(self, x: int) -> float:
        if x < self.lower_mid_x:
            return -max(
                min((self.lower_mid_x - x) / (self.lower_mid_x - self.min_x), 1.0), 0.0
            )
        if x > self.upper_mid_x:
            return max(
                min((x - self.upper_mid_x) / (self.max_x - self.upper_mid_x), 1.0), 0.0
            )
        return 0.0

    def _get_normalized_y(self, y: int) -> float:
        if y < self.lower_mid_y:
            return -max(
                min((self.lower_mid_y - y) / (self.lower_mid_y - self.min_y), 1.0), 0.0
            )
        if y > self.upper_mid_y:
            return max(
                min((y - self.upper_mid_y) / (self.max_y - self.upper_mid_y), 1.0), 0.0
            )
        return 0.0


class Calibration(BaseCalibration):
    def _startup_condition(self) -> bool:
        return not self.button.value

    def _notify(self) -> None:
        blink_led()

    def _get_mid_values(self):
        start = ticks_ms()
        current = 0

        while current < start + self.mid_time * 1000:
            self.mid_x = self.thumb_stick_x.value
            self.mid_y = self.thumb_stick_y.value
            current = ticks_ms()

    def _check_for_stop_criteria(self) -> None:
        if self._startup_condition():
            self.running = False

    def _write_config(self) -> None:
        data = {
            "min_x": self.min_x,
            "mid_x": self.mid_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "mid_y": self.mid_y,
            "max_y": self.max_y,
        }

        try:
            self._notify()
            with open("calibration.json", mode="w") as file:
                json.dump(data, file)
            self._notify()
        except OSError:
            pass

    def read(self) -> None:
        with open("calibration.json", mode="r") as file:
            data = json.load(file)

        self.min_x = float(data["min_x"])
        self.mid_x = float(data["mid_x"])
        self.max_x = float(data["max_x"])
        self.min_y = float(data["min_y"])
        self.mid_y = float(data["mid_y"])
        self.max_y = float(data["max_y"])

        delta = (self.max_x - self.mid_x) * self._limit
        self.upper_mid_x = self.mid_x + delta

        delta = (self.mid_x - self.min_x) * self._limit
        self.lower_mid_x = self.mid_x - delta

        delta = (self.max_y - self.mid_y) * self._limit
        self.upper_mid_y = self.mid_y + delta

        delta = (self.mid_y - self.min_y) * self._limit
        self.lower_mid_y = self.mid_y - delta

        del self.mid_x
        del self.mid_y
