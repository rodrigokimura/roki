/// Custom BLE GATT service for inter-half keyboard communication.
///
/// Stub: nrf-softdevice v0.1.0 GATT server registration is TODO.
/// The actual service definition and packet read/write will be added
/// once the SoftDevice plumbing is in place.

use nrf_softdevice::ble::Connection;

/// Base UUID bytes: "reffuBtekcaP" + "\x00\x00\xaf\xad"
/// Then bytes at index -3 and -4 are set from the 16-bit UUID.
const fn roki_uuid(uuid16: u16) -> [u8; 16] {
    let mut uuid = *b"reffuBtekcaP\x00\x00\xaf\xad";
    uuid[12] = (uuid16 & 0xFF) as u8;
    uuid[13] = (uuid16 >> 8) as u8;
    uuid
}

/// Service UUID: 0x0001
pub const ROKI_SERVICE_UUID: [u8; 16] = roki_uuid(0x0001);
/// Characteristic UUID: 0x0101
pub const ROKI_CHAR_UUID: [u8; 16] = roki_uuid(0x0101);

/// Stub RoKi inter-half service.
///
/// TODO: implement full GATT server registration via nrf-softdevice macros
/// or raw SoftDevice calls once the API is better understood.
pub struct RokiService;

impl RokiService {
    pub fn new() -> Self {
        Self
    }

    /// Notify the connected peer with a 4-byte packet.
    pub fn notify(&self, _conn: &Connection, _data: &[u8; 4]) {
        // TODO
    }
}
