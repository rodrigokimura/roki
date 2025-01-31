try:
    from typing import TYPE_CHECKING as __t

    TYPE_CHECKING = __t
except ImportError:  # pragma: no cover
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable


class Loop:
    def __init__(
        self,
        max_iterations: int | None = None,
        stop_when: "Callable[[], bool]" = lambda: False,
    ) -> None:
        self.max_iterations = max_iterations
        self.sentinel = stop_when

    def iterate(self):
        from adafruit_itertools import count

        for i in count():
            if i >= self.max_iterations or self.sentinel():
                break
            yield i


class Cycle:
    def __init__(self, initial_value: int = 0, limit: int = 100) -> None:
        self.value = initial_value
        self.limit = limit

    def increment(self):
        self.value += 1
        if self.value >= self.limit:
            self.value = 0


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


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


def encode_vector(x: int, y: int):
    return (x << 4) + y


def decode_vector(i: int):
    x = i >> 4
    return x, i - (x << 4)


def encode_float(value: float):
    """
    [-1.0; 1.0] -> [0; 255]
    """
    negative = int(value < 0)
    value = round(abs(value) * (2**7 - 1))
    return (negative << 7) + value


def decode_float(value: int):
    """
    [0; 255] -> [-1.0; 1.0]
    """
    negative = value >> 7
    value -= negative << 7
    return (1, -1)[negative] * (value / (2**7 - 1))


def blink_led(led_pin: str = "LED", delay: float = 0.3, times: int = 10):
    print("Blinking LED")
    import time

    import board
    from digitalio import DigitalInOut, Direction

    led = DigitalInOut(getattr(board, led_pin))
    led.direction = Direction.OUTPUT
    led.switch_to_output(value=False)
    led.value = False
    for _ in range(times):
        led.value = not led.value
        time.sleep(delay)
    led.deinit()
