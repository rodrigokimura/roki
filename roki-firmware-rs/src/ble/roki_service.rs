/// Custom BLE GATT service for inter-half keyboard communication.
///
/// Matches the Python `RokiService` from `roki/firmware/service.py`.
///
/// The UUID is a vendor UUID constructed from the string "reffuBtekcaP"
/// with some byte manipulation, matching the Python implementation.

/// Base UUID bytes: "reffuBtekcaP" + "\x00\x00\xaf\xad"
/// Then bytes at index -3 and -4 are set from the 16-bit UUID.
fn roki_uuid(uuid16: u16) -> [u8; 16] {
    let mut uuid = *b"reffuBtekcaP\x00\x00\xaf\xad";
    uuid[12] = (uuid16 & 0xFF) as u8;
    uuid[13] = (uuid16 >> 8) as u8;
    uuid
}

/// Service UUID: 0x0001
pub const ROKI_SERVICE_UUID: [u8; 16] = roki_uuid(0x0001);
/// Characteristic UUID: 0x0101
pub const ROKI_CHAR_UUID: [u8; 16] = roki_uuid(0x0101);

use nrf_softdevice::ble::gatt_server::builder::ServiceBuilder;
use nrf_softdevice::ble::gatt_server::{CharacteristicHandles, RegisterError, Service};
use nrf_softdevice::ble::{AttributeMetadata, Connection, Properties, Uuid, Value};
use nrf_softdevice::{raw, Softdevice};

/// The custom RoKi inter-half service.
pub struct RokiService {
    pub packets: CharacteristicHandles,
}

impl RokiService {
    pub fn new(sd: &mut Softdevice) -> Result<Self, RegisterError> {
        let mut service_builder = ServiceBuilder::new(sd, Uuid::new_128(&ROKI_SERVICE_UUID))?;

        let attr_metadata = AttributeMetadata::read_write(
            raw::BLE_GATTS_VLOC_STACK as u8,
            raw::BLE_GATTS_AUTHORIZE_INVALID as u8,
        );
        let attr = raw::ble_gatts_attr_t {
            p_uuid: &raw::ble_uuid_t {
                uuid: 0x0101,
                type_: raw::BLE_UUID_TYPE_VENDOR_BEGIN as u8,
            } as *const _ as *mut _,
            p_attr_md: &attr_metadata,
            init_len: 4,
            init_offs: 0,
            max_len: 4,
            p_value: core::ptr::null_mut(),
        };

        let metadata = raw::ble_gatts_char_md_t {
            char_props: raw::ble_gatt_char_props_t {
                read: 1,
                write_wo_resp: 1,
                notify: 1,
                ..Default::default()
            },
            ..Default::default()
        };

        let mut handles = raw::ble_gatts_value_handles_t::default();
        let ret = unsafe {
            raw::sd_ble_gatts_characteristic_add(
                service_builder.service_handle(),
                &metadata,
                &attr,
                &mut handles,
            )
        };

        if ret != raw::NRF_SUCCESS {
            return Err(RegisterError::Raw(ret));
        }

        let _service_handle = service_builder.build();

        Ok(Self {
            packets: CharacteristicHandles {
                value_handle: handles.value_handle,
                user_desc_handle: handles.user_desc_handle,
                cccd_handle: handles.cccd_handle,
                sccd_handle: handles.sccd_handle,
            },
        })
    }

    /// Notify the connected peer with a 4-byte packet.
    pub fn notify(&self, conn: &Connection, data: &[u8; 4]) -> Result<(), nrf_softdevice::ble::gatt_server::NotifyValueError> {
        nrf_softdevice::ble::gatt_server::notify_value(
            conn,
            self.packets.value_handle,
            data,
        )
    }
}
