#!/usr/bin/env bash
# Build the Rust firmware and convert the ELF to UF2 for nice!nano v2.
set -euo pipefail

TARGET="thumbv7em-none-eabihf"
BINARY="roki-firmware"
RELEASE_DIR="target/${TARGET}/release"

echo "==> Building release ELF..."
cargo build --release

echo "==> Converting to UF2..."
elf2uf2-rs "${RELEASE_DIR}/${BINARY}" "${BINARY}.uf2"

echo "==> Done: ${BINARY}.uf2 ($(stat -c%s "${BINARY}.uf2" 2>/dev/null || stat -f%z "${BINARY}.uf2") bytes)"
