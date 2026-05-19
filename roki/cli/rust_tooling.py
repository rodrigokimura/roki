"""Host tooling for the Rust + Embassy firmware (M8).

Commands:
    roki flash    — build and flash UF2 to nice!nano via bootloader
    roki build    — compile firmware without flashing
    roki logs     — stream RTT debug logs via probe-rs
    roki check    — run cargo check

The nice!nano v2 enters bootloader mode when you double-tap the reset button.
In this mode it exposes a mass-storage drive named NICENANO (or similar).
Copying a .uf2 file to this drive flashes the firmware automatically.
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Literal

import typer

from roki.cli.options import VERBOSE_OPTION

logger = logging.getLogger(__name__)

_WINDOWS = os.name == "nt"

# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIRMWARE_CRATE = REPO_ROOT / "roki-firmware-rs"
TARGET = "thumbv7em-none-eabihf"
RELEASE_DIR = FIRMWARE_CRATE / "target" / TARGET / "release"
BINARY_NAME = "roki-firmware"

# ── Platform-specific drive detection ────────────────────────────────────

def get_bootloader_drives() -> list[Path]:
    """Find all mounted NICENANO UF2 bootloader drives."""
    if _WINDOWS:
        return _get_windows_drives()
    return _get_unix_drives()


def _get_windows_drives() -> list[Path]:
    """On Windows, iterate drive letters and check volume labels."""
    import ctypes
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"
        if not os.path.exists(drive):
            continue
        vol_name_buf = ctypes.create_unicode_buffer(1024)
        fs_name_buf = ctypes.create_unicode_buffer(1024)
        result = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive),
            vol_name_buf, ctypes.sizeof(vol_name_buf),
            None, None, None,
            fs_name_buf, ctypes.sizeof(fs_name_buf),
        )
        if result and "NICENANO" in str(vol_name_buf.value):
            drives.append(Path(drive))
    return drives


def _get_unix_drives() -> list[Path]:
    """On Linux/macOS, scan common mount points for a NICENANO directory."""
    candidates: list[Path] = []
    # Linux systemd/udisks2 paths
    user = os.environ.get("USER", "")
    for base in [
        Path(f"/run/media/{user}"),
        Path(f"/media/{user}"),
        Path("/Volumes"),
    ]:
        if not base.exists():
            continue
        for entry in base.iterdir():
            if entry.is_dir() and "NICENANO" in entry.name.upper():
                candidates.append(entry)
    return candidates


# ── Build helpers ────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path, desc: str) -> None:
    logger.info(f"{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        logger.info(result.stdout)
    if result.stderr:
        # cargo prints progress to stderr
        logger.info(result.stderr)
    if result.returncode != 0:
        logger.error(f"{desc} failed with exit code {result.returncode}")
        raise typer.Exit(1)


def _build(side: Literal["right", "left"]) -> Path:
    """Build firmware for one side and return the UF2 path."""
    features = ["left-side"] if side == "left" else []
    cargo_args = ["cargo", "build", "--release", "--target", TARGET]
    if features:
        cargo_args += ["--features", ",".join(features)]

    logger.info(f"Building {side} half...")
    _run(cargo_args, FIRMWARE_CRATE, f"cargo build ({side})")

    elf = RELEASE_DIR / BINARY_NAME
    uf2 = FIRMWARE_CRATE / f"{BINARY_NAME}_{side}.uf2"

    logger.info(f"Converting ELF → UF2 for {side}...")
    _run(["elf2uf2-rs", str(elf), str(uf2)], FIRMWARE_CRATE, f"elf2uf2 ({side})")

    logger.info(f"Created {uf2.name} ({uf2.stat().st_size} bytes)")
    return uf2


# ── Flash helpers ────────────────────────────────────────────────────────

def _wait_for_drive(timeout: int = 60) -> Path:
    """Poll for a NICENANO drive to appear."""
    logger.info("Waiting for nice!nano bootloader (double-tap reset)...")
    for i in range(timeout):
        drives = get_bootloader_drives()
        if drives:
            drive = drives[0]
            logger.info(f"Detected bootloader drive: {drive}")
            return drive
        if i % 5 == 0 and i > 0:
            logger.info(f"  … still waiting ({i}s)")
        time.sleep(1)
    logger.error("No NICENANO drive detected. Double-tap the reset button.")
    raise typer.Exit(1)


def _flash_file(uf2: Path, drive: Path) -> None:
    """Copy UF2 to bootloader drive and wait for unmount."""
    dest = drive / uf2.name
    logger.info(f"Copying {uf2.name} → {drive} ...")
    # shutil.copy2 preserves metadata; simple copy is fine here
    import shutil
    shutil.copy2(uf2, dest)
    logger.info("Copy complete — waiting for device to reboot...")
    # Poll until drive disappears (indicates flash + reboot)
    for _ in range(30):
        if not drive.exists():
            logger.info("Device rebooted successfully.")
            return
        time.sleep(1)
    logger.warning("Drive still present after 30s — may need manual eject.")


# ── Typer commands ───────────────────────────────────────────────────────

app = typer.Typer(help="Rust firmware host tooling")


@app.command()
def build(
    side: Literal["right", "left", "both"] = typer.Option(
        "both",
        "--side",
        "-s",
        help="Which half to build: left, right, or both",
    ),
    _: int = VERBOSE_OPTION,
):
    """Compile the Rust firmware without flashing."""
    sides = ["left", "right"] if side == "both" else [side]
    for s in sides:
        _build(s)  # type: ignore[arg-type]
    logger.info("Build complete.")


@app.command()
def check(
    side: Literal["right", "left", "both"] = typer.Option(
        "both",
        "--side",
        "-s",
        help="Which half to check",
    ),
    _: int = VERBOSE_OPTION,
):
    """Run cargo check for the firmware."""
    features: list[str] = []
    if side == "left":
        features = ["left-side"]
    elif side == "both":
        features = ["left-side"]  # check both in one pass isn't possible; default to left

    cmd = ["cargo", "check", "--target", TARGET]
    if features:
        cmd += ["--features", ",".join(features)]

    logger.info("Running cargo check...")
    _run(cmd, FIRMWARE_CRATE, "cargo check")
    logger.info("Check passed.")


@app.command()
def flash(
    side: Literal["right", "left", "both"] = typer.Option(
        "both",
        "--side",
        "-s",
        help="Which half to flash",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Prompt to press Enter between halves (interactive mode)",
    ),
    _: int = VERBOSE_OPTION,
):
    """Build and flash firmware to the nice!nano via UF2 bootloader.

    For each half:
      1. Build release ELF
      2. Convert to UF2 with elf2uf2-rs
      3. Wait for the NICENANO bootloader drive to appear
      4. Copy the UF2 file
      5. Wait for the device to reboot

    If --side=both, you will be prompted to switch halves between flashes.
    """
    sides: list[Literal["right", "left"]] = (
        ["left", "right"] if side == "both" else [side]  # type: ignore[list-item]
    )

    for i, s in enumerate(sides):
        if i > 0 and wait:
            typer.prompt(
                f"{'=' * 40}\n"
                f"  Now flash the {s.upper()} half.\n"
                f"  Double-tap reset on the {s.upper()} nice!nano, then press Enter",
                default="",
                show_default=False,
            )

        uf2 = _build(s)
        drive = _wait_for_drive()
        _flash_file(uf2, drive)
        logger.info(f"{s.upper()} half flashed successfully.")

    logger.info("All halves flashed. Enjoy your RoKi!")


@app.command()
def logs(
    side: Literal["right", "left"] = typer.Option(
        "left",
        "--side",
        "-s",
        help="Which half to attach probe-rs to (default: left/primary)",
    ),
    level: Literal["error", "warn", "info", "debug", "trace"] = typer.Option(
        "info",
        "--level",
        "-l",
        help="defmt log level",
    ),
    _: int = VERBOSE_OPTION,
):
    """Stream RTT debug logs from the firmware via probe-rs.

    Requires a debug probe (J-Link, CMSIS-DAP, Raspberry Pi Debug Probe)
    connected to the SWD header.
    """
    features = ["left-side"] if side == "left" else []
    env = os.environ.copy()
    env["DEFMT_LOG"] = level

    cmd = ["cargo", "run", "--release", "--target", TARGET]
    if features:
        cmd += ["--features", ",".join(features)]

    logger.info(f"Attaching probe-rs to {side} half (DEFMT_LOG={level})...")
    logger.info("  Connect SWDIO/SWCLK/GND and press Ctrl-C to exit.")
    subprocess.run(cmd, cwd=FIRMWARE_CRATE, env=env)
