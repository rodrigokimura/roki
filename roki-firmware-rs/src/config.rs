/// Compile-time + runtime configuration.
///
/// The keymap JSON is embedded at build time via `include_str!`.
/// We parse it at boot with `serde-json-core` (no-std JSON parser).

use heapless::Vec;
use serde::{Deserialize, Serialize};

use crate::calibration::{CalibrationData, NormalizedCalibration};
use crate::keymap::KeyAction;
use crate::layers::LayerCommand;
use crate::logging::{debug, error, info};

// ── Layer configuration ──────────────────────────────────────────────────

/// A single layer parsed from JSON.
#[derive(Clone, Debug, Deserialize)]
pub struct Layer {
    pub name: heapless::String<32>,
    pub color: (u8, u8, u8),
    #[serde(with = "serde_utils::key_matrix")]
    pub primary_keys: [KeyAction; 30],       // 5 rows × 6 cols
    #[serde(with = "serde_utils::key_matrix")]
    pub secondary_keys: [KeyAction; 30],
    #[serde(with = "serde_utils::encoder_pair")]
    pub primary_encoder_cw: KeyAction,
    #[serde(with = "serde_utils::encoder_pair")]
    pub primary_encoder_ccw: KeyAction,
    #[serde(with = "serde_utils::encoder_pair")]
    pub secondary_encoder_cw: KeyAction,
    #[serde(with = "serde_utils::encoder_pair")]
    pub secondary_encoder_ccw: KeyAction,
}

/// The full keyboard configuration.
#[derive(Clone, Debug)]
pub struct Config {
    pub layers: Vec<Layer, 8>,
    pub calibration: NormalizedCalibration,
}

// ── JSON parsing helpers ────────────────────────────────────────

mod serde_utils {
    use serde::{Deserialize, Deserializer, Serialize};
    use crate::keymap::KeyAction;
    use heapless::Vec;

    pub mod key_matrix {
        use super::*;

        pub fn deserialize<'de, D>(deserializer: D) -> Result<[KeyAction; 30], D::Error>
        where
            D: Deserializer<'de>,
        {
            let rows: Vec<Vec<Option<heapless::String<32>>, 6>, 8> = Deserialize::deserialize(deserializer)?;
            let mut result = [KeyAction::Noop; 30];
            let mut idx = 0usize;

            for row in rows.iter().take(5) {
                for cell in row.iter().take(6) {
                    if let Some(key_str) = cell.as_ref() {
                        result[idx] = KeyAction::from_str(key_str.as_str());
                    }
                    idx += 1;
                }
            }
            Ok(result)
        }

        pub fn serialize<S>(_value: &[KeyAction; 30], _serializer: S) -> Result<S::Ok, S::Error>
        where
            S: serde::Serializer,
        {
            unreachable!()
        }
    }

    pub mod encoder_pair {
        use super::*;

        pub fn deserialize<'de, D>(deserializer: D) -> Result<KeyAction, D::Error>
        where
            D: Deserializer<'de>,
        {
            let pair: Vec<Option<heapless::String<32>>, 2> = Deserialize::deserialize(deserializer)?;
            if let Some(first) = pair.get(0) {
                if let Some(s) = first {
                    return Ok(KeyAction::from_str(s.as_str()));
                }
            }
            Ok(KeyAction::Noop)
        }

        pub fn serialize<S>(_value: &KeyAction, _serializer: S) -> Result<S::Ok, S::Error>
        where
            S: serde::Serializer,
        {
            unreachable!()
        }
    }
}

// ── Color hex parser (bridging Python str → Rust tuple) ────────

/// Parse a hex color like `"#3584e4"` into `(r, g, b)`.
fn parse_hex_color(hex: &str) -> (u8, u8, u8) {
    let s = hex.strip_prefix('#').unwrap_or(hex);
    if s.len() != 6 {
        return (0, 0, 0);
    }
    let r = u8::from_str_radix(&s[0..2], 16).unwrap_or(0);
    let g = u8::from_str_radix(&s[2..4], 16).unwrap_or(0);
    let b = u8::from_str_radix(&s[4..6], 16).unwrap_or(0);
    (r, g, b)
}

// ── Config loading ───────────────────────────────────────────────────────

/// Raw JSON structure matching the Python config.json format.
#[derive(Deserialize)]
struct RawConfig {
    pub layers: heapless::Vec<RawLayer, 8>,
}

#[derive(Deserialize)]
struct RawLayer {
    pub name: heapless::String<32>,
    pub color: heapless::String<8>,
    pub primary_keys: heapless::Vec<heapless::Vec<Option<heapless::String<32>>, 6>, 8>,
    pub secondary_keys: heapless::Vec<heapless::Vec<Option<heapless::String<32>>, 6>, 8>,
    pub primary_encoder: heapless::Vec<Option<heapless::String<32>>, 2>,
    pub secondary_encoder: heapless::Vec<Option<heapless::String<32>>, 2>,
}

impl Config {
    /// Load configuration from embedded JSON and flash calibration.
    pub fn load() -> Self {
        let json_str = include_str!("../config/default.json");
        let mut layers: Vec<Layer, 8> = Vec::new();

        match serde_json_core::from_str::<heapless::Vec<RawLayer, 8>>(json_str) {
            Ok((raw_layers, _)) => {
                for raw in raw_layers {
                    let color = parse_hex_color(raw.color.as_str());

                    let mut primary_keys = [KeyAction::Noop; 30];
                    let mut secondary_keys = [KeyAction::Noop; 30];

                    // Flatten primary_keys (5×6)
                    let mut idx = 0usize;
                    for row in raw.primary_keys.iter().take(5) {
                        for cell in row.iter().take(6) {
                            if let Some(ref s) = cell {
                                primary_keys[idx] = KeyAction::from_str(s.as_str());
                            }
                            idx += 1;
                        }
                    }

                    // Flatten secondary_keys (5×6)
                    idx = 0usize;
                    for row in raw.secondary_keys.iter().take(5) {
                        for cell in row.iter().take(6) {
                            if let Some(ref s) = cell {
                                secondary_keys[idx] = KeyAction::from_str(s.as_str());
                            }
                            idx += 1;
                        }
                    }

                    let primary_encoder_cw = raw.primary_encoder.get(0)
                        .and_then(|o| o.as_ref())
                        .map(|s| KeyAction::from_str(s.as_str()))
                        .unwrap_or(KeyAction::Noop);
                    let primary_encoder_ccw = raw.primary_encoder.get(1)
                        .and_then(|o| o.as_ref())
                        .map(|s| KeyAction::from_str(s.as_str()))
                        .unwrap_or(KeyAction::Noop);
                    let secondary_encoder_cw = raw.secondary_encoder.get(0)
                        .and_then(|o| o.as_ref())
                        .map(|s| KeyAction::from_str(s.as_str()))
                        .unwrap_or(KeyAction::Noop);
                    let secondary_encoder_ccw = raw.secondary_encoder.get(1)
                        .and_then(|o| o.as_ref())
                        .map(|s| KeyAction::from_str(s.as_str()))
                        .unwrap_or(KeyAction::Noop);

                    let layer = Layer {
                        name: raw.name,
                        color,
                        primary_keys,
                        secondary_keys,
                        primary_encoder_cw,
                        primary_encoder_ccw,
                        secondary_encoder_cw,
                        secondary_encoder_ccw,
                    };

                    let _ = layers.push(layer);
                }
                info!("Loaded {} layers from config", layers.len());
            }
            Err(e) => {
                error!("Failed to parse config.json: {}", defmt::Debug2Format(&e));
                // fallback: one empty layer
            }
        }

        // Load calibration from flash
        let calibration = CalibrationData::load()
            .map(|data| NormalizedCalibration::from_data(&data))
            .unwrap_or_else(|| {
                info!("No calibration in flash; using defaults (zero)");
                NormalizedCalibration::from_data(&CalibrationData::default())
            });

        Self { layers, calibration }
    }
}
