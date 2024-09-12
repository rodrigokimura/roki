import pathlib
import toml

import typer

from roki.cli.file_management import (
    copy_tree,
    create_empty_file,
    create_tree,
    delete_files_by_extension,
)
from roki.cli.utils import (
    create_mount_point,
    get_devices,
    get_serial_device,
    run_command,
    unmount,
)

app = typer.Typer(name="roki")


@app.command(name="list")
def list_devices(left: bool = True):
    """List available devices"""

    devices = get_devices()
    options = {n: dev for n, dev in enumerate(devices, start=1)}
    for n, d in options.items():
        print(f"{n} - {d}")

    if len(options) > 1:
        index = typer.prompt("Select a number")
        chosen = options.get(index)
    else:
        chosen = devices[0]
    if not chosen:
        raise typer.Abort()

    print(f"Mounting device {chosen}")

    mountpoint_path = "/run/media/roki"
    print(f"Creating directory for mountpoint: {mountpoint_path}")
    p = pathlib.Path(mountpoint_path)
    run_command(f"sudo mkdir {mountpoint_path} -p")

    create_mount_point(chosen, p)

    print("Copying files...")
    firmware_relative_tree = "roki_firmware"
    firmware_location = f"{mountpoint_path}/{firmware_relative_tree}"
    delete_files_by_extension(["py", "json", "toml"], mountpoint_path)
    create_tree(firmware_location)
    copy_tree(firmware_relative_tree, firmware_location)
    create_empty_file(f"{mountpoint_path}/roki/__init__.py")

    run_command(f"sudo rm {mountpoint_path}/roki/firmware/code.py -vf", shell=True)
    run_command(f"sudo rm {mountpoint_path}/roki/firmware/config.json -vf", shell=True)
    run_command(
        f"sudo rm {mountpoint_path}/roki/firmware/settings.toml -vf", shell=True
    )
    run_command(
        f"sudo cp roki/firmware/code.py {mountpoint_path}/code.py -vf", shell=True
    )
    run_command(
        f"sudo cp roki/firmware/config.json {mountpoint_path}/config.json -vf",
        shell=True,
    )

    with open("roki/firmware/settings.toml", mode="w") as f:
        toml.dump({"IS_LEFT_SIDE": int(left), "ENABLE_SERIAL": 0}, f)
    run_command(
        f"sudo cp roki/firmware/settings.toml {mountpoint_path}/settings.toml -vf",
        shell=True,
    )

    print("Installing libs...")

    cmd = f"circup --path {mountpoint_path} install --auto"
    run_command(cmd)
    cmd = f"circup --path {mountpoint_path} install --auto-file {mountpoint_path}/roki/firmware/keys.py"
    run_command(cmd)

    print("Unmounting...")
    unmount(p)


@app.command()
def run():
    """Run code.py"""

    if SERIAL_DEVICE := get_serial_device():
        run_command(f"ampy -p {SERIAL_DEVICE} run roki/firmware/code.py")
