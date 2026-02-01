import os

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from roki.cli.file_management import (
    copy_file,
    copy_tree,
    create_empty_file,
    create_tree,
    delete_file,
    delete_files_by_extension,
)
from roki.cli.html_generator import Generator
from roki.cli.utils import (
    create_mount_point,
    debug_codes,
    get_devices,
    install_circuitpython_libs,
    unmount,
)
from roki.tui.app import Configurator

_WINDOWS = os.name == "nt"

firmware_relative_tree = os.path.join("roki", "firmware")

app = typer.Typer(name="roki")


@app.command(name="u")
@app.command(name="upload")
def upload_code(side: str = typer.Option("r")):
    """Upload code and libs to device"""

    side = side.lower()
    if side not in ("r", "l", "right", "left"):
        print("Invalid option: side must be 'r' or 'l'")
        raise typer.Abort()
    is_left_side = side in ("l", "left")

    devices = get_devices()
    options = {n: dev for n, dev in enumerate(devices, start=1)}
    for n, d in options.items():
        print(f"{n} - {d}")

    if len(options) > 1:
        index = typer.prompt("Select a number")
        try:
            chosen = options[int(index)]
        except ValueError:
            print("Not a number!")
            raise typer.Abort()
        except KeyError:
            print("Not an option!")
            raise typer.Abort()
    elif len(options) == 1:
        chosen = devices[0]
    else:
        print("No devices found.")
        chosen = None
    if not chosen:
        raise typer.Abort()

    print(f"Preparing device {chosen}")

    if _WINDOWS:
        dst = chosen
    else:
        dst = "/run/media/roki"

        print(f"Creating directory for mountpoint: {dst}")
        create_tree(dst)

        create_mount_point(chosen, dst)

    print("Copying files...")
    firmware_location = os.path.join(dst, firmware_relative_tree)

    delete_files_by_extension(["py", "toml"], dst)
    delete_file(os.path.join(dst, "config.json"))

    create_tree(firmware_location)
    copy_tree(firmware_relative_tree, firmware_location, ["py", "json"])
    create_empty_file(os.path.join(dst, "roki", "__init__.py"))

    root_files = [
        "boot.py",
        "code.py",
        "config.json",
    ]
    for file in root_files:
        delete_file(os.path.join(firmware_location, file))
        copy_file(os.path.join(firmware_relative_tree, file), dst)

    settings = "settings.toml"
    with open(os.path.join(firmware_relative_tree, settings), mode="w") as f:
        f.write(f"IS_LEFT_SIDE={int(is_left_side)}")
    copy_file(os.path.join(firmware_relative_tree, settings), dst)
    delete_file(os.path.join(firmware_relative_tree, settings))

    print("Installing libs...")
    python_firmware_files: list[str] = [
        "keys.py",
        "kb.py",
    ]
    for file in python_firmware_files:
        install_circuitpython_libs(dst, os.path.join(firmware_location, file))

    install_circuitpython_libs(dst, "boot.py")
    install_circuitpython_libs(dst, "code.py")

    if not _WINDOWS:
        print("Unmounting...")
        unmount(dst)


@app.command()
def run():
    """Run code.py"""

    files = [
        os.path.join(firmware_relative_tree, "boot.py"),
        os.path.join(firmware_relative_tree, "code.py"),
    ]
    debug_codes(files)


@app.command()
def serve():
    """Run configuration server"""

    generate()

    password = typer.prompt("SSL keyfile password", hide_input=True)

    app = FastAPI()
    app.mount("", StaticFiles(directory=".", html=True), name="static")

    uvicorn.run(
        app,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem",
        ssl_keyfile_password=password,
    )


@app.command(name="g")
@app.command(name="generate")
def generate():
    """Generate html file"""

    Generator().generate_html()


@app.command()
def config():
    """Open configurator TUI"""

    print("Opening configurator TUI")
    app = Configurator()
    app.run()
