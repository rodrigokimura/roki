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


def map_range():
    pass


def blink_led(led_pin: str = "LED", delay: float = 0.1, times: int = 10):
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
