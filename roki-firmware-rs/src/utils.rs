/// Small utilities extracted from `roki/firmware/utils.py`.

/// A saturating counter that wraps at `limit`.
pub struct Cycle {
    value: u8,
    limit: u8,
}

impl Cycle {
    pub const fn new(initial: u8, limit: u8) -> Self {
        Self { value: initial, limit }
    }

    #[inline]
    pub fn increment(&mut self) {
        self.value += 1;
        if self.value >= self.limit {
            self.value = 0;
        }
    }

    #[inline]
    pub fn value(&self) -> u8 {
        self.value
    }
}

/// Debouncer for an integer signal (e.g. encoder position).
#[derive(Clone, Copy)]
pub struct Debouncer {
    value: i32,
    last_value: i32,
}

impl Debouncer {
    pub const fn new(initial: i32) -> Self {
        Self {
            value: initial,
            last_value: initial,
        }
    }

    #[inline]
    pub fn update(&mut self, value: i32) {
        self.last_value = self.value;
        self.value = value;
    }

    #[inline]
    pub fn changed(&self) -> bool {
        self.last_value != self.value
    }

    #[inline]
    pub fn rose(&self) -> bool {
        self.value > self.last_value
    }

    #[inline]
    pub fn fell(&self) -> bool {
        self.value < self.last_value
    }

    #[inline]
    pub fn diff(&self) -> i32 {
        self.value - self.last_value
    }
}

/// Convert a flat key index into (row, col) coordinates.
#[inline]
pub const fn get_coords(index: usize, col_count: usize) -> (usize, usize) {
    (index / col_count, index % col_count)
}
