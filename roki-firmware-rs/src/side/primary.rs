use embassy_executor::Spawner;
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};
use nrf_softdevice::ble::central::{self, ConnectConfig, ScanConfig};
use nrf_softdevice::ble::gatt_client;
use nrf_softdevice::ble::PhySet;
use nrf_softdevice::raw;

use crate::ble::roki_service::{RokiClient, RokiClientEvent, ROKI_UUID_128};
use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, HidState, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::LayerHandler;
use crate::logging::{info, trace};

/// Dedicated task that runs the GATT client event loop for inter-half packets.
#[embassy_executor::task]
async fn ble_packet_handler_task(conn: nrf_softdevice::ble::Connection, client: RokiClient) {
    gatt_client::run(&conn, &client, |evt| {
        if let RokiClientEvent::Packet(pkt) = evt {
            trace!("RX inter-half packet: {:?}", pkt);
            let _ = crate::INTER_HALF_PACKETS.try_send(pkt);
        }
    })
    .await;
    info!("Secondary disconnected");
}

/// Walk advertisement data and check if it contains the given 128-bit UUID.
fn ad_contains_uuid_128(data: &[u8], uuid: &[u8; 16]) -> bool {
    let mut i = 0usize;
    while i + 1 < data.len() {
        let len = data[i] as usize;
        if len == 0 || i + 1 + len > data.len() {
            break;
        }
        let ad_type = data[i + 1];
        let ad_data = &data[i + 2..i + 1 + len];
        // 0x06 = Incomplete List of 128-bit Service UUIDs
        // 0x07 = Complete List of 128-bit Service UUIDs
        if (ad_type == 0x06 || ad_type == 0x07) && ad_data.len() >= 16 {
            for chunk in ad_data.chunks_exact(16) {
                if chunk == uuid {
                    return true;
                }
            }
        }
        i += 1 + len;
    }
    false
}

#[embassy_executor::task]
pub async fn primary_task(
    spawner: Spawner,
    config: Config,
    key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    info!("Primary (left) side starting");

    // ── Enable SoftDevice and scan for secondary ─────────────────────────
    let sd = crate::ble::init_softdevice();

    // Scan until we find the secondary advertising RokiService
    let peer_addr = loop {
        let result = nrf_softdevice::ble::central::scan(
            sd,
            &ScanConfig::default(),
            |report| {
                let data = unsafe {
                    core::slice::from_raw_parts(report.data.p_data, report.data.len as usize)
                };
                if ad_contains_uuid_128(data, &ROKI_UUID_128) {
                    Some(nrf_softdevice::ble::Address::from_raw(report.peer_addr))
                } else {
                    None
                }
            },
        )
        .await;

        match result {
            Ok(addr) => break addr,
            Err(_) => {
                info!("Scan timeout, retrying...");
                Timer::after(Duration::from_secs(1)).await;
            }
        }
    };
    info!("Found secondary at address {:x}", peer_addr.bytes());

    // Connect using the discovered address in the whitelist
    let conn = {
        let peer_ref = &peer_addr;
        let whitelist_arr = [peer_ref];
        let cfg = ConnectConfig {
            scan_config: ScanConfig {
                whitelist: Some(&whitelist_arr[..]),
                ..Default::default()
            },
            conn_params: raw::ble_gap_conn_params_t {
                min_conn_interval: 6,  // 7.5 ms
                max_conn_interval: 12, // 15 ms
                slave_latency: 0,
                conn_sup_timeout: 400,
            },
            att_mtu: None,
        };
        match central::connect(sd, &cfg).await {
            Ok(c) => {
                info!("Connected to secondary {:x}", c.peer_address().bytes());
                Buzzer::queue_peripheral_connected_tone().await;
                c
            }
            Err(e) => {
                info!("Connection failed: {}", defmt::Debug2Format(&e));
                return;
            }
        }
    };

    // ── Discover the RokiService ─────────────────────────────────────────
    let client: RokiClient = match gatt_client::discover(&conn).await {
        Ok(c) => c,
        Err(e) => {
            info!("Service discovery failed: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    if let Err(e) = client.enable_notifications(&conn).await {
        info!("Failed to enable notifications: {}", defmt::Debug2Format(&e));
        return;
    }
    info!("Notifications enabled on RokiService");

    // ── Spawn BLE event handler (receives notifications) ─────────────────
    spawner.must_spawn(ble_packet_handler_task(conn, client));

    // ── Main loop: process local key events + inter-half packets ─────────
    let mut hid_state = HidState::new();
    let mut layer = LayerHandler::<8>::new();
    let mouse_speed: i8 = 10;

    loop {
        // Local keys
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

        // Inter-half packets from secondary
        if let Ok(pkt) = crate::INTER_HALF_PACKETS.try_receive() {
            let (counter, msg_id, p1, p2) = crate::protocol::unpack_packet(pkt);
            trace!("Process inter-half counter={} msg={} p1={} p2={}", counter, msg_id, p1, p2);
            match msg_id {
                crate::protocol::KEY => {
                    // p1 = key index, p2 = pressed bool
                    let key = if p2 != 0 {
                        let current_layer = config.layers.get(layer.current()).unwrap();
                        current_layer.secondary_keys[p1 as usize]
                    } else {
                        KeyAction::Noop
                    };
                    if p2 != 0 {
                        hid_state.press(key);
                    } else {
                        hid_state.release(key);
                    }
                }
                crate::protocol::ENCODER => {
                    // p1 = cw delta, p2 = ccw delta
                    let current_layer = config.layers.get(layer.current()).unwrap();
                    for _ in 0..p1 {
                        hid_state.press(current_layer.secondary_encoder_cw);
                        hid_state.release(current_layer.secondary_encoder_cw);
                    }
                    for _ in 0..p2 {
                        hid_state.press(current_layer.secondary_encoder_ccw);
                        hid_state.release(current_layer.secondary_encoder_ccw);
                    }
                }
                crate::protocol::THUMB_STICK => {
                    if p1 != 0 || p2 != 0 {
                        hid_state.mouse.x = (crate::protocol::decode_float(p1) * mouse_speed as f32) as i8;
                        hid_state.mouse.y = (crate::protocol::decode_float(p2) * mouse_speed as f32) as i8;
                    } else {
                        hid_state.mouse.x = 0;
                        hid_state.mouse.y = 0;
                    }
                }
                _ => {}
            }
        }

        // TODO: Send HID reports to host computer via HOGP (M5)

        Timer::after(Duration::from_micros(500)).await;
    }
}
