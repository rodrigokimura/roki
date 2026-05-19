/// Lightweight logging wrapper that bridges to `defmt`.
///
/// All firmware modules use these macros so that we can swap backends
/// (e.g. to a no-op logger in release builds) from a single place.

pub use defmt::{debug, error, info, trace, warn, unwrap, assert, panic};

/// Re-export `defmt::Format` so modules can derive it without importing defmt directly.
pub use defmt::Format;
