#![no_std]
#![no_main]

pub mod ble;
pub mod buzzer;
pub mod calibration;
pub mod config;
pub mod encoder;
pub mod keymap;
pub mod layers;
pub mod logging;
pub mod matrix;
pub mod protocol;
pub mod side;
pub mod thumbstick;
pub mod utils;

use defmt_rtt as _;
use embassy_executor::Spawner;
use embassy_time::Timer;
use panic_probe as _;

use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::encoder::encoder_task;
use crate::keymap::{EncoderEvent, KeyEvent, ThumbstickEvent};
use crate::matrix::matrix_task;
use crate::side::primary::primary_task;
use crate::side::secondary::secondary_task;
use crate::thumbstick::thumbstick_task;

// ── Shared channels ──────────────────────────────────────────────────────

// We use embassy_sync channels for inter-task communication.
// Capacity tuned for expected event rates:
//   - Keys: ~16 events (5×6 matrix, max 2-key rollover in a burst)
//   - Encoder: 4 events (one per detent × direction)
//   - Thumbstick: 4 events (XY updates)

use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Channel;

pub static KEY_EVENTS: Channel<ThreadModeRawMutex, KeyEvent, 16> = Channel::new();
pub static ENCODER_EVENTS: Channel<ThreadModeRawMutex, EncoderEvent, 4> = Channel::new();
pub static THUMB_EVENTS: Channel<ThreadModeRawMutex, ThumbstickEvent, 4> = Channel::new();

// ── Main entry point ─────────────────────────────────────────────────────

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    defmt::info!("RoKi firmware starting...");

    // Initialize nRF52840 peripherals via embassy
    let p = embassy_nrf::init(Default::default());

    // ── Detect which side this is ─────────────────────────────────────────
    // In the Python firmware this was selected via the `IS_LEFT_SIDE`
    // environment variable. For the Rust build we use a compile-time
    // feature flag (`left-side`) so the same firmware binary does NOT
    // need a GPIO at boot. If you want runtime detection, bridge a
    // different GPIO to GND and read it here.
    let is_left = cfg!(feature = "left-side");

    defmt::info!("Side detected: {}", if is_left { "LEFT (primary)" } else { "RIGHT (secondary)" });

    // ── Shared config ─────────────────────────────────────────────────────
    let config = Config::load();
    defmt::debug!("Loaded {} layers", config.layers.len());

    // ── Spawn buzzer task ─────────────────────────────────────────────────
    let buzzer = Buzzer::new(p.PWM0, p.P0_06);
    spawner.must_spawn(buzzer::buzzer_task(buzzer));

    // Play startup tone
    Buzzer::queue_startup_tone().await;

    // ── Spawn input device tasks ──────────────────────────────────────────
    // Pin lists for the matrix scanner
    let rows = [
        p.P0_24.degrade(),
        p.P1_00.degrade(),
        p.P0_11.degrade(),
        p.P1_04.degrade(),
        p.P1_06.degrade(),
    ];
    let cols = [
        p.P0_09.degrade(),
        p.P0_10.degrade(),
        p.P1_11.degrade(),
        p.P1_13.degrade(),
        p.P1_15.degrade(),
        p.P0_02.degrade(),
    ];

    spawner.must_spawn(matrix_task(rows, cols, KEY_EVENTS.sender()));
    spawner.must_spawn(encoder_task(
        p.QDEC,
        p.P0_17.degrade(),
        p.P0_20.degrade(),
        ENCODER_EVENTS.sender(),
    ));
    spawner.must_spawn(thumbstick_task(
        p.SAADC,
        p.P0_31.degrade(),
        p.P0_29.degrade(),
        p.P0_22.degrade(),
        config.calibration.clone(),
        THUMB_EVENTS.sender(),
    ));

    // ── Spawn side-specific task ──────────────────────────────────────────
    if is_left {
        spawner.must_spawn(primary_task(
            config,
            KEY_EVENTS.receiver(),
            ENCODER_EVENTS.receiver(),
            THUMB_EVENTS.receiver(),
        ));
    } else {
        spawner.must_spawn(secondary_task(
            config,
            KEY_EVENTS.receiver(),
            ENCODER_EVENTS.receiver(),
            THUMB_EVENTS.receiver(),
        ));
    }

    // Main task drops to idle; all work is in spawned tasks.
    // We could join the Buzzer task if we want clean shutdown, but there
    // is none on an MCU.
}
