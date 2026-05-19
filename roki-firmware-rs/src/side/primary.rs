use embassy_executor::Spawner;
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::blocking_mutex::Mutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};
use nrf_softdevice::ble::central::{self, ConnectConfig, ScanConfig};
use nrf_softdevice::ble::gatt_client;
use nrf_softdevice::ble::peripheral::{self, advertise_connectable, ConnectableAdvertisement};
use nrf_softdevice::ble::{Address};
use nrf_softdevice::raw;

use core::cell::RefCell;

use crate::ble::hid_service::HidServer;
use crate::ble::roki_service::{RokiClient, RokiClientEvent, ROKI_UUID_128};
use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, HidState, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::LayerHandler;
use crate::logging::{info, trace};

// ── Cross-task shared host connection ────────────────────────────────────

static HOST_CONN: Mutex<ThreadModeRawMutex, RefCell<Option<nrf_softdevice::ble::Connection>>> =
    Mutex::new(RefCell::new(None));

/// Dedicated task that runs the GATT client event loop for inter-half packets.
#[embassy_executor::task]
async fn ble_packet_handler_task(
    conn: nrf_softdevice::ble::Connection,
    client: RokiClient,
) {
    gatt_client::run(&conn, &client, |evt| {
        let RokiClientEvent::Packet(pkt) = evt;
        trace!("RX inter-half packet: {:?}", pkt);
        let _ = crate::INTER_HALF_PACKETS.try_send(pkt);
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

    // ── Enable SoftDevice ────────────────────────────────────────────────
    let sd = crate::ble::init_softdevice();

    // ── Scan for and connect to secondary ────────────────────────────────
    let peer_addr = loop {
        let result = nrf_softdevice::ble::central::scan(
            sd,
            &ScanConfig::default(),
            |report| {
                let data = unsafe {
                    core::slice::from_raw_parts(report.data.p_data, report.data.len as usize)
                };
                if ad_contains_uuid_128(data, &ROKI_UUID_128) {
                    Some(Address::from_raw(report.peer_addr))
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

    let secondary_conn = {
        let peer_ref = &peer_addr;
        let whitelist_arr = [peer_ref];
        let cfg = ConnectConfig {
            scan_config: ScanConfig {
                whitelist: Some(&whitelist_arr[..]),
                ..Default::default()
            },
            conn_params: raw::ble_gap_conn_params_t {
                min_conn_interval: 6,
                max_conn_interval: 12,
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

    // ── Discover RokiService on secondary ────────────────────────────────
    let client: RokiClient = match gatt_client::discover(&secondary_conn).await {
        Ok(c) => c,
        Err(e) => {
            info!("Service discovery failed: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    if let Err(e) = client.enable_notifications(&secondary_conn).await {
        info!("Failed to enable notifications: {}", defmt::Debug2Format(&e));
        return;
    }
    info!("Notifications enabled on RokiService");

    spawner.must_spawn(ble_packet_handler_task(secondary_conn, client));

    // ── Register HID service and advertise to host ─────────────────────────
    let hid_server = match HidServer::register(sd) {
        Ok(h) => h,
        Err(e) => {
            info!("HID service registration failed: {}", defmt::Debug2Format(&e));
            return;
        }
    };
    let hid_ref: &'static HidServer = {
        #[allow(static_mut_refs)]
        unsafe {
            static mut HID_STATIC: Option<HidServer> = None;
            HID_STATIC = Some(hid_server);
            HID_STATIC.as_ref().unwrap()
        }
    };

    use nrf_softdevice::ble::advertisement_builder::{AdvertisementBuilder, Flag, ServiceList, ServiceUuid16};
    let adv_data = AdvertisementBuilder::<31>::new()
        .flags(&[Flag::GeneralDiscovery, Flag::LE_Only])
        .services_16(ServiceList::Complete, &[ServiceUuid16::HUMAN_INTERFACE_DEVICE])
        .short_name("Roki")
        .build();
    let scan_data = &[];

    info!("Advertising HID service to host...");
    let host_conn = match advertise_connectable(
        sd,
        ConnectableAdvertisement::ScannableUndirected {
            adv_data: adv_data.as_ref(),
            scan_data,
        },
        &peripheral::Config::default(),
    )
    .await
    {
        Ok(c) => {
            info!("Host connected: {:x}", c.peer_address().bytes());
            Buzzer::queue_host_connected_tone().await;
            c
        }
        Err(e) => {
            info!("Host advertise failed: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    HOST_CONN.lock(|cell| {
        *cell.borrow_mut() = Some(host_conn);
    });
    info!("HID reports active — keyboard + mouse + consumer");

    // ── Main keyboard loop ───────────────────────────────────────────────
    let mut hid_state = HidState::new();
    let mut layer = LayerHandler::<8>::new();
    let mouse_speed: i8 = 10;
    let mut last_keys: [u8; 6] = [0; 6];
    let mut last_mods: u8 = 0;
    let mut last_mouse_x: i8 = 0;
    let mut last_mouse_y: i8 = 0;

    let mut last_consumer: u16 = 0;

    loop {
        let mut changed = false;

        // ── Local keys ──
        if let Ok(event) = key_rx.try_receive() {
            let current_layer = config.layers.get(layer.current()).unwrap();
            let key = current_layer.primary_keys[event.index as usize];
            if event.pressed {
                if let KeyAction::Layer(cmd) = key {
                    let lc = layer.on_press(cmd);
                    if lc {
                        hid_state.release_all();
                        changed = true;
                    }
                } else {
                    hid_state.press(key);
                    changed = true;
                }
            } else {
                if let KeyAction::Layer(cmd) = key {
                    let lc = layer.on_release(cmd);
                    if lc {
                        hid_state.release_all();
                        changed = true;
                    }
                } else {
                    hid_state.release(key);
                    changed = true;
                }
            }
        }

        // ── Encoder ──
        if let Ok(event) = encoder_rx.try_receive() {
            if layer.extras {
                let current_layer = config.layers.get(layer.current()).unwrap();
                if event.delta > 0 {
                    for _ in 0..event.delta {
                        hid_state.press(current_layer.primary_encoder_cw);
                        hid_state.release(current_layer.primary_encoder_cw);
                    }
                    changed = true;
                } else {
                    for _ in 0..(-event.delta) {
                        hid_state.press(current_layer.primary_encoder_ccw);
                        hid_state.release(current_layer.primary_encoder_ccw);
                    }
                    changed = true;
                }
            }
        }

        // ── Thumbstick ──
        if let Ok(event) = thumb_rx.try_receive() {
            if layer.extras {
                if event.x != 0.0 || event.y != 0.0 {
                    hid_state.mouse.x = (event.x * mouse_speed as f32) as i8;
                    hid_state.mouse.y = (event.y * mouse_speed as f32) as i8;
                } else {
                    hid_state.mouse.x = 0;
                    hid_state.mouse.y = 0;
                }
                changed = true;
            }
        }

        // ── Inter-half packets from secondary ──
        if let Ok(pkt) = crate::INTER_HALF_PACKETS.try_receive() {
            let (_counter, msg_id, p1, p2) = crate::protocol::unpack_packet(pkt);
            match msg_id {
                crate::protocol::KEY => {
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
                    changed = true;
                }
                crate::protocol::ENCODER => {
                    let current_layer = config.layers.get(layer.current()).unwrap();
                    for _ in 0..p1 {
                        hid_state.press(current_layer.secondary_encoder_cw);
                        hid_state.release(current_layer.secondary_encoder_cw);
                        changed = true;
                    }
                    for _ in 0..p2 {
                        hid_state.press(current_layer.secondary_encoder_ccw);
                        hid_state.release(current_layer.secondary_encoder_ccw);
                        changed = true;
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
                    changed = true;
                }
                _ => {}
            }
        }

        // ── Send HID reports to host if we have a connection ──
        HOST_CONN.lock(|cell| {
            if let Some(ref host_conn) = *cell.borrow() {
                let (keys, mods) = hid_state.keyboard_report();
                let (mx, my) = (hid_state.mouse.x, hid_state.mouse.y);

                // Keyboard report (only emit on change to save airtime)
                if changed || keys != last_keys || mods != last_mods {
                    hid_ref.send_keyboard(host_conn, mods, keys);
                    last_keys = keys;
                    last_mods = mods;
                }

                // Consumer report (media keys)
                let consumer = hid_state.consumer_report();
                if consumer != last_consumer {
                    hid_ref.send_consumer(host_conn, consumer);
                    last_consumer = consumer;
                }

                // Mouse report (emit every frame while moving)
                if mx != 0 || my != 0 || mx != last_mouse_x || my != last_mouse_y {
                    hid_ref.send_mouse(host_conn, 0, mx, my, 0);
                    last_mouse_x = mx;
                    last_mouse_y = my;
                }
            }
        });

        Timer::after(Duration::from_micros(500)).await;
    }
}
