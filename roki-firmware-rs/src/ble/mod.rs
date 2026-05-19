/// BLE integration: SoftDevice enable, RokiService (server + client), and HID stubs.

pub mod hid_service;
pub mod roki_service;

use nrf_softdevice::{raw, Softdevice};

/// Global SoftDevice configuration for the nice!nano v2.
///
/// Single connection (inter-half), GATT server enabled for RokiService.
/// Clock source is the internal RC oscillator (nice!nano has no external LF crystal).
pub fn init_softdevice() -> &'static mut Softdevice {
    let config = nrf_softdevice::Config {
        clock: Some(raw::nrf_clock_lf_cfg_t {
            source: raw::NRF_CLOCK_LF_SRC_RC as u8,
            rc_ctiv: 16,
            rc_temp_ctiv: 2,
            accuracy: raw::NRF_CLOCK_LF_ACCURACY_250_PPM as u8,
        }),
        conn_gap: Some(raw::ble_gap_conn_cfg_t {
            conn_count: 2,
            event_length: 24,
        }),
        conn_gatt: Some(raw::ble_gatt_conn_cfg_t {
            att_mtu: raw::BLE_GATT_ATT_MTU_DEFAULT as u16,
        }),
        conn_gattc: Some(raw::ble_gattc_conn_cfg_t {
            write_cmd_tx_queue_size: 4,
        }),
        conn_gatts: Some(raw::ble_gatts_conn_cfg_t {
            hvn_tx_queue_size: 8,
        }),
        ..Default::default()
    };
    Softdevice::enable(&config)
}
