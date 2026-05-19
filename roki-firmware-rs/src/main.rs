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
use embassy_nrf::gpio::Pin;
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Channel;
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

pub static KEY_EVENTS: Channel<ThreadModeRawMutex, KeyEvent, 16> = Channel::new();
pub static ENCODER_EVENTS: Channel<ThreadModeRawMutex, EncoderEvent, 4> = Channel::new();
pub static THUMB_EVENTS: Channel<ThreadModeRawMutex, ThumbstickEvent, 4> = Channel::new();

/// Channel for inter-half packets (secondary → primary).
/// Populated by the BLE notification handler task on the primary side.
pub static INTER_HALF_PACKETS: Channel<ThreadModeRawMutex, [u8; 4], 8> = Channel::new();

// ── Main entry point ─────────────────────────────────────────────────────

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    defmt::info!("RoKi firmware starting...");

    let p = embassy_nrf::init(Default::default());

    let is_left = cfg!(feature = "left-side");
    defmt::info!("Side detected: {}", if is_left { "LEFT (primary)" } else { "RIGHT (secondary)" });

    let config = Config::load();
    defmt::debug!("Loaded {} layers", config.layers.len());

    // ── Spawn buzzer task ─────────────────────────────────────────────────
    let buzzer = Buzzer::new(p.PWM0, p.P0_06.into());
    spawner.must_spawn(buzzer::buzzer_task(buzzer));
    Buzzer::queue_startup_tone().await;

    // ── Spawn input device tasks ──────────────────────────────────────────
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
        p.P0_17.into(),
        p.P0_20.into(),
        ENCODER_EVENTS.sender(),
    ));
    spawner.must_spawn(thumbstick_task(
        p.SAADC,
        p.P0_31,
        p.P0_29,
        p.P0_22,
        config.calibration.clone(),
        THUMB_EVENTS.sender(),
    ));

    // ── Spawn side-specific BLE + HID task ────────────────────────────────
    if is_left {
        spawner.must_spawn(primary_task(
            spawner,
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
}
