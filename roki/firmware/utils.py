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


def to_int(bools: list[bool]):
    return sum(b << i for i, b in enumerate(bools))


def from_int(i: int, size=6):
    return [bool((i >> j) & 1) for j in range(size)]


def to_bytes(bools: list[list[bool]]):
    return bytes(to_int(b) for b in bools)


def from_bytes(b: bytes):
    return [from_int(i) for i in b]


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


def diff_bitmaps(a: bytes | bytearray, b: bytes | bytearray, byte_size=6):
    for r, (x, y) in enumerate(zip(a, b)):
        for c in range(byte_size):
            if ((x >> c) & 1) != (value := ((y >> c) & 1)):
                yield (r, c), bool(value)
