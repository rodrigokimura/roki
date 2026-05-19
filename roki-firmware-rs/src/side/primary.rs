use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};

use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, HidState, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::{info, trace};

/// Global shared HID state (primary side only).
/// Must be static since the HID server callbacks reference it.
use embassy_sync::mutex::Mutex;

static HID_STATE: Mutex<ThreadModeRawMutex, HidState> = Mutex::new(HidState::new_const());
static LAYER_HANDLER: Mutex<ThreadModeRawMutex, LayerHandler<8>> = Mutex::new(LayerHandler::new());

#[embassy_executor::task]
pub async fn primary_task(
    config: Config,
    key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
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

    let mut hid_state = HidState::new();
    let mut layer = LayerHandler::<8>::new();
    let mouse_speed: i8 = 10;

    loop {
        // Poll all three channels with a short timeout to avoid blocking
        // indefinitely on any single input source.
        if let Ok(event) = key_rx.try_receive() {
            let current_layer = config.layers.get(layer.current()).unwrap();
            let key = current_layer.primary_keys[event.index as usize];

            if event.pressed {
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

        if let Ok(event) = encoder_rx.try_receive() {
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

        if let Ok(event) = thumb_rx.try_receive() {
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

        // TODO: Send reports via BLE HID
        // if let Some(conn) = host_connection {
        //     send_keyboard_report(conn, &hid_state.keyboard).await;
        //     send_mouse_report(conn, &hid_state.mouse).await;
        //     send_consumer_report(conn, &hid_state.consumer).await;
        // }

        Timer::after(Duration::from_micros(500)).await;
    }
}
