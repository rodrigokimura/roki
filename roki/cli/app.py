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

firmware_relative_tree = "roki/firmware"

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

    print(f"Mounting device {chosen}")

    mountpoint_path = "/run/media/roki"

    print(f"Creating directory for mountpoint: {mountpoint_path}")
    create_tree(mountpoint_path)

    create_mount_point(chosen, mountpoint_path)

    print("Copying files...")
    firmware_location = f"{mountpoint_path}/{firmware_relative_tree}"

    # TODO: remove installed libs
    # delete_files_by_extension(["*"], f"{mountpoint_path}/lib")

    delete_files_by_extension(["py", "toml"], mountpoint_path)
    delete_file(f"{mountpoint_path}/config.json")

    create_tree(firmware_location)
    copy_tree(firmware_relative_tree, firmware_location, ["py", "json"])
    create_empty_file(f"{mountpoint_path}/roki/__init__.py")

    root_files = [
        "boot.py",
        "code.py",
        "config.json",
    ]
    for file in root_files:
        delete_file(f"{firmware_location}/{file}")
        copy_file(f"{firmware_relative_tree}/{file}", mountpoint_path)

    settings = "settings.toml"
    with open(f"{firmware_relative_tree}/{settings}", mode="w") as f:
        f.write(f"IS_LEFT_SIDE={int(is_left_side)}")
    copy_file(f"{firmware_relative_tree}/{settings}", mountpoint_path)
    delete_file(f"{firmware_relative_tree}/{settings}")

    print("Installing libs...")
    python_firmware_files = [
        "keys.py",
        "kb.py",
        "calibration.py",
        "utils.py",
    ]
    for file in python_firmware_files:
        install_circuitpython_libs(mountpoint_path, f"{firmware_location}/{file}")

    install_circuitpython_libs(mountpoint_path, "boot.py")
    install_circuitpython_libs(mountpoint_path, "code.py")

    print("Unmounting...")
    unmount(mountpoint_path)


@app.command()
def run():
    """Run code.py"""
    files = [f"{firmware_relative_tree}/boot.py", f"{firmware_relative_tree}/code.py"]
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
