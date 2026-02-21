from typing import Generator
from roki.firmware import logging

try:
    from typing import Callable
except ImportError:
    pass

logger = logging.getLogger(__name__)


def count():
    i = 0
    while True:
        yield i
        i += 1


class Loop:
    __slots__ = (
        "max_iterations",
        "sentinel",
    )

    def __init__(
        self,
        max_iterations: int = 0,
        stop_when: "Callable[[], bool]" = lambda: False,
    ) -> None:
        self.max_iterations = max_iterations
        self.sentinel = stop_when

    def iterate(self):
        for i in count():
            logger.debug(f"Iteration: {i}")

            if (0 < self.max_iterations <= i) or self.sentinel():
                break

            yield i


class WeightedLoop(Loop):
    __slots__ = (
        "max_iterations",
        "sentinel",
        "total_weight",
    )

    def __init__(
        self,
        max_iterations: int = 0,
        stop_when: "Callable[[], bool]" = lambda: False,
    ) -> None:
        super().__init__(max_iterations, stop_when)
        self.total_weight = 0

    def iterate(self) -> Generator["Iteration", None, None]:
        for i in count():
            logger.debug(f"Iteration: {i}")

            if (0 < self.max_iterations <= i) or self.sentinel():
                break

            yield Iteration(self, i)


class Iteration:
    __slots__ = (
        "iteration",
        "loop",
        "weight",
    )

    iteration: int
    loop: WeightedLoop
    weight: int

    def __init__(self, loop: WeightedLoop, iteration: int):
        self.loop = loop
        self.iteration = iteration

    def for_weight(self, w: int):
        if self.iteration == 0:
            self.loop.total_weight += w

        # self.loop.iterate
        # pass
        return self

    def __enter__(self):
        if self.iteration % self.weight == 1:
            pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class Cycle:
    def __init__(self, initial_value: int = 0, limit: int = 100) -> None:
        self.value = initial_value
        self.limit = limit

    def increment(self):
        self.value += 1
        if self.value >= self.limit:
            self.value = 0


class Debouncer:
    __slots__ = (
        "value",
        "last_value",
    )

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
    import time

    import board
    from digitalio import DigitalInOut, Direction

    logger.debug("Blinking LED")
    led = DigitalInOut(getattr(board, led_pin))
    led.direction = Direction.OUTPUT
    led.switch_to_output(value=False)
    led.value = False
    for _ in range(times):
        led.value = not led.value
        time.sleep(delay)
    led.deinit()
