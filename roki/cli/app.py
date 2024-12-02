from http.server import HTTPServer

import typer

from roki.cli.file_management import (
    copy_file,
    copy_tree,
    create_empty_file,
    create_tree,
    delete_file,
    delete_files_by_extension,
)
from roki.cli.html_generator import Generator, WebHandler
from roki.cli.utils import (
    create_mount_point,
    debug_code,
    get_devices,
    install_circuitpython_libs,
    unmount,
)
from tui.app import Configurator

firmware_relative_tree = "roki/firmware"

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
    elif len(options) == 1:
        chosen = devices[0]
    else:
        chosen = None
    if not chosen:
        raise typer.Abort()

    print(f"Mounting device {chosen}")

    mountpoint_path = "/run/media/roki"

    print(f"Creating directory for mountpoint: {mountpoint_path}")
    create_tree(mountpoint_path)

    create_mount_point(chosen, mountpoint_path)

    print("Copying files...")
    firmware_location = f"{mountpoint_path}/{firmware_relative_tree}"
    delete_files_by_extension(["py", "json", "toml"], mountpoint_path)
    create_tree(firmware_location)
    copy_tree(firmware_relative_tree, firmware_location)
    create_empty_file(f"{mountpoint_path}/roki/__init__.py")

    root_files = [
        "code.py",
        "config.json",
    ]
    for file in root_files:
        delete_file(f"{firmware_location}/{file}")
        copy_file(f"{firmware_relative_tree}/{file}", mountpoint_path)

    settings = "settings.toml"
    with open(f"{firmware_relative_tree}/{settings}", mode="w") as f:
        f.write(f"IS_LEFT_SIDE={int(left)}")
    copy_file(f"{firmware_relative_tree}/{settings}", mountpoint_path)
    delete_file(f"{firmware_relative_tree}/{settings}")

    print("Installing libs...")
    python_firmware_files = [
        "keys.py",
        "kb.py",
    ]
    for file in python_firmware_files:
        install_circuitpython_libs(mountpoint_path, f"{firmware_location}/{file}")

    print("Unmounting...")
    unmount(mountpoint_path)


@app.command()
def run():
    """Run code.py"""

    debug_code(f"{firmware_relative_tree}/code.py")


@app.command()
def serve():
    """Run configuration server"""

    server = HTTPServer(("0.0.0.0", 8000), WebHandler)
    server.serve_forever()


@app.command()
def generate():
    """Generate html file"""

    Generator().generate_html()


@app.command()
def config():
    """Open configurator TUI"""

    print("Opening configurator TUI")
    app = Configurator()
    app.run()
