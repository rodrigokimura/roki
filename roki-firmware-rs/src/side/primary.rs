use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_sync::mutex::Mutex;
use embassy_time::{Duration, Timer};
use heapless::Vec;

use nrf_softdevice::ble::advertisement_builder::Flag;
use nrf_softdevice::ble::peripheral::Advertisement;
use nrf_softdevice::ble::{gatt_server, peripheral, Connection};
use nrf_softdevice::{raw, Softdevice};

use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, HidState, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::{error, info, trace, warn};
use crate::protocol;

/// Global shared HID state (primary side only).
/// Must be static since the HID server callbacks reference it.
pub static HID_STATE: Mutex<ThreadModeRawMutex, HidState> = Mutex::new(HidState::new_const());
static LAYER_HANDLER: Mutex<ThreadModeRawMutex, LayerHandler<8>> = Mutex::new(LayerHandler::new());

/// Global extras flag shared between tasks.
static EXTRAS: Mutex<ThreadModeRawMutex, bool> = Mutex::new(false);

#[embassy_executor::task]
pub async fn primary_task(
    mut config: Config,
    mut key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    mut encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    mut thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    info!("Primary (left) side starting");

    // TODO: Initialize SoftDevice, register HOGP, start advertising.
    // For the MVP, we drive HID state from input events and will wire
    // up the actual BLE HID transport once SoftDevice plumbing is done.

    // Play startup jingle
    Buzzer::queue_startup_tone().await;

    // TODO: Scan for secondary and connect
    // let peripheral_conn = connect_to_secondary().await;
    // Buzzer::queue_peripheral_connected_tone().await;

    let mut mouse_speed: i8 = 10;
    let mut hid_state = HidState::new();
    let mut layer = LayerHandler::<8>::new();

    loop {
        // Simple polled-event loop with select-like behavior via futures::select
        // Embassy does not have a built-in `select!` macro in core; we use
        // `futures::select` or `embassy-futures::select`.
        use embassy_futures::select::{select3, Either3};

        match select3(key_rx.receive(), encoder_rx.receive(), thumb_rx.receive()).await {
            Either3::First(event) => {
                let current_layer = config.layers.get(layer.current()).unwrap();
                let key = current_layer.primary_keys[event.index as usize];

                if event.pressed {
                    // Check for layer commands before HID dispatch
                    if let KeyAction::Layer(cmd) = key {
                        let changed = layer.on_press(cmd);
                        if changed {
                            hid_state.release_all();
                        }
                    } else {
                        hid_state.press(key);
                    }
                } else {
                    if let KeyAction::Layer(cmd) = key {
                        let changed = layer.on_release(cmd);
                        if changed {
                            hid_state.release_all();
                        }
                    } else {
                        hid_state.release(key);
                    }
                }

                trace!("HID state keys={:?} mods={:?}", hid_state.keyboard.keys, hid_state.keyboard.modifiers);
            }

            Either3::Second(event) => {
                if !layer.extras {
                    continue;
                }
                let current_layer = config.layers.get(layer.current()).unwrap();
                if event.delta > 0 {
                    for _ in 0..event.delta {
                        hid_state.press(current_layer.primary_encoder_cw);
                        hid_state.release(current_layer.primary_encoder_cw);
                    }
                } else {
                    for _ in 0..(-event.delta) {
                        hid_state.press(current_layer.primary_encoder_ccw);
                        hid_state.release(current_layer.primary_encoder_ccw);
                    }
                }
            }

            Either3::Third(event) => {
                if !layer.extras {
                    continue;
                }
                if event.x != 0.0 || event.y != 0.0 {
                    hid_state.mouse.x = (event.x * mouse_speed as f32) as i8;
                    hid_state.mouse.y = (event.y * mouse_speed as f32) as i8;
                } else {
                    hid_state.mouse.x = 0;
                    hid_state.mouse.y = 0;
                }
            }
        }

        // TODO: Send reports via BLE HID
        // if let Some(conn) = host_connection {
        //     send_keyboard_report(conn, &hid_state.keyboard).await;
        //     send_mouse_report(conn, &hid_state.mouse).await;
        //     send_consumer_report(conn, &hid_state.consumer).await;
        // }
    }
}

/// TODO: Scan for the secondary half advertising `RokiService` and connect.
async fn _connect_to_secondary() {
    // placeholder
}
