/// Inter-half message protocol constants.
///
/// These match the Python firmware (roki/firmware/messages.py) bit-for-bit
/// so that the CircuitPython secondary half can still talk to the Rust primary
/// during a partial migration, and vice-versa.

/// Key matrix event forwarded from the secondary half.
pub const KEY: u8 = 1;

/// Rotary encoder event forwarded from the secondary half.
pub const ENCODER: u8 = 2;

/// Analog thumbstick event forwarded from the secondary half.
pub const THUMB_STICK: u8 = 3;

/// Encode a float in `[-1.0, 1.0]` to a single `u8` in `[0, 255]`.
///
/// Encoding: sign bit (bit 7) + 7-bit magnitude.
/// Zero is `0b0000_0000`; `-1.0` is `0b1000_0000`; `+1.0` is `0b0111_1111`.
#[inline]
pub fn encode_float(value: f32) -> u8 {
    let negative = if value < 0.0 { 1u8 } else { 0u8 };
    let magnitude = (value.abs() * 127.0 + 0.5) as u8;
    (negative << 7) | (magnitude & 0x7F)
}

/// Decode a `u8` produced by [`encode_float`] back to `f32` in `[-1.0, 1.0]`.
#[inline]
pub fn decode_float(value: u8) -> f32 {
    let negative = (value >> 7) & 1;
    let magnitude = (value & 0x7F) as f32;
    let sign = if negative == 1 { -1.0 } else { 1.0 };
    sign * (magnitude / 127.0)
}

/// Pack an inter-half packet into a 4-byte payload.
///
/// `payload` is `(payload_1, payload_2)` — both must already be encoded
/// (abs value for integers, [`encode_float`] for thumbstick axes).
#[inline]
pub fn pack_packet(counter: u8, msg_id: u8, payload: (u8, u8)) -> [u8; 4] {
    [counter, msg_id, payload.0, payload.1]
}

/// Unpack a 4-byte inter-half packet.
#[inline]
pub fn unpack_packet(packet: [u8; 4]) -> (u8, u8, u8, u8) {
    (packet[0], packet[1], packet[2], packet[3])
}
