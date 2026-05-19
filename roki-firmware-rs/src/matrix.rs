/// Key matrix scanner using GPIO row/column multiplexing.
///
/// Ported from CircuitPython `keypad.KeyMatrix`.
/// Each row is an output, each column is an input with pull-down.
/// We drive one row high at a time and read all columns.

use embassy_nrf::gpio::{AnyPin, Input, Output, Pull};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Sender;
use embassy_time::{Duration, Instant, Timer};

use crate::keymap::KeyEvent;
use crate::logging::{debug, trace};

const ROWS: usize = 5;
const COLS: usize = 6;
const DEBOUNCE_MS: u64 = 5;

pub struct Matrix {
    rows: [Output<'static>; ROWS],
    cols: [Input<'static>; COLS],
    state: [[bool; COLS]; ROWS],
    debounce: [[Option<Instant>; COLS]; ROWS],
}

impl Matrix {
    pub fn new(row_pins: [AnyPin; ROWS], col_pins: [AnyPin; COLS]) -> Self {
        let mut rows: [Option<Output<'static>>; ROWS] = [None, None, None, None, None];
        for (i, pin) in row_pins.into_iter().enumerate() {
            let mut out = Output::new(pin, embassy_nrf::gpio::Level::Low, embassy_nrf::gpio::OutputDrive::Standard);
            out.set_low();
            rows[i] = Some(out);
        }

        let mut cols: [Option<Input<'static>>; COLS] = [None, None, None, None, None, None];
        for (i, pin) in col_pins.into_iter().enumerate() {
            cols[i] = Some(Input::new(pin, Pull::Down));
        }

        Self {
            rows: rows.map(|o| o.unwrap()),
            cols: cols.map(|o| o.unwrap()),
            state: [[false; COLS]; ROWS],
            debounce: [[None; COLS]; ROWS],
        }
    }

    /// Scan the matrix and send changed events.
    pub async fn scan(&mut self, tx: &Sender<'static, ThreadModeRawMutex, KeyEvent, 16>) {
        for r in 0..ROWS {
            // Drive row high
            self.rows[r].set_high();
            // Wait for signal to settle (5 µs is generous)
            Timer::after(Duration::from_micros(5)).await;

            for c in 0..COLS {
                let pressed = self.cols[c].is_high();
                let now = Instant::now();

                if pressed != self.state[r][c] {
                    if let Some(start) = self.debounce[r][c] {
                        if now.duration_since(start) >= Duration::from_millis(DEBOUNCE_MS) {
                            self.state[r][c] = pressed;
                            self.debounce[r][c] = None;

                            let index = (r * COLS + c) as u8;
                            let event = KeyEvent { index, pressed };
                            trace!("Key {} {}", index, if pressed { "pressed" } else { "released" });
                            let _ = tx.send(event).await;
                        }
                    } else {
                        self.debounce[r][c] = Some(now);
                    }
                } else {
                    self.debounce[r][c] = None;
                }
            }

            // Drive row low again
            self.rows[r].set_low();
        }
    }
}

#[embassy_executor::task]
pub async fn matrix_task(
    row_pins: [AnyPin; ROWS],
    col_pins: [AnyPin; COLS],
    tx: Sender<'static, ThreadModeRawMutex, KeyEvent, 16>,
) {
    let mut matrix = Matrix::new(row_pins, col_pins);
    debug!("Matrix scanner started ({}×{})", ROWS, COLS);

    loop {
        matrix.scan(&tx).await;
        // Yield briefly between scans to let other tasks run
        Timer::after(Duration::from_micros(100)).await;
    }
}
