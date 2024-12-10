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
