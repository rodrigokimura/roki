from typing import Literal
from enum import Enum
import logging
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
    replace_params,
)
from roki.tui.app import Configurator

_WINDOWS = os.name == "nt"

firmware_relative_tree = os.path.join("roki", "firmware")

logger = logging.getLogger(__name__)


class LogLevel(int, Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def format_by_level(level: int):
    LEVELS = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }
    COLORS = {
        logging.DEBUG: typer.colors.MAGENTA,
        logging.INFO: typer.colors.CYAN,
        logging.WARNING: typer.colors.YELLOW,
        logging.ERROR: typer.colors.RED,
        logging.CRITICAL: typer.colors.BRIGHT_RED,
    }
    level_part = f"[{LEVELS.get(level, LEVELS[logging.INFO]).upper():^10}]"
    level_part = typer.style(
        level_part,
        fg=COLORS.get(level),
        bold=True,
    )

    message_part = typer.style(
        "%(message)s",
        fg=COLORS.get(level),
        bold=True,
    )
    time_part = typer.style(
        "%(asctime)s",
        dim=True,
    )
    # return f"{level_part} {time_part} %(name)s {message_part} - %(pathname)s:%(lineno)d"
    return f"{level_part} [%(process)d] {time_part} %(name)s {message_part}"


class LevelBasedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        log_fmt = format_by_level(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def main_callback():
    handler = logging.StreamHandler()
    handler.setFormatter(LevelBasedFormatter())
    handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[handler],
    )


app = typer.Typer(
    name="roki",
    callback=main_callback,
    pretty_exceptions_short=False,
)


@app.command(name="u")
@app.command(name="upload")
def upload_code(
    side: Literal["r", "l", "right", "left"] = typer.Option(
        "left",
        case_sensitive=False,
        help="Keyboard side destination",
    ),
    libs: bool = typer.Option(
        True,
        help="Install CircuitPython libs",
    ),
    root: bool = typer.Option(
        True,
        help="Update root files",
    ),
    default_config: bool = typer.Option(
        True,
        help="Replace with default config file ('config.json')",
    ),
    default_settings: bool = typer.Option(
        True,
        help="Replace with default settings file ('settings.toml')",
    ),
):
    """Upload code and libs to device"""

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

    logger.info(f"Preparing device {chosen}")

    if _WINDOWS:
        dst = chosen
    else:
        dst = "/run/media/roki"

        logger.info(f"Creating directory for mountpoint: {dst}")
        create_tree(dst)

        create_mount_point(chosen, dst)

    logger.info("Copying files...")
    firmware_location = os.path.join(dst, firmware_relative_tree)

    extensions_to_delete: list[str] = ["py"]
    if default_settings:
        extensions_to_delete.append("toml")
    delete_files_by_extension(extensions_to_delete, dst)

    if default_config:
        delete_file(os.path.join(dst, "config.json"))
        copy_file(os.path.join(firmware_relative_tree, "config.json"), dst)
    else:
        logger.warning("Skipping config reset (config.json)")

    create_tree(firmware_location)
    copy_tree(firmware_relative_tree, firmware_location, ["py", "json"])
    create_empty_file(os.path.join(dst, "roki", "__init__.py"))

    if root:
        root_files: list[str] = [
            "boot.py",
            "code.py",
        ]
        for file in root_files:
            delete_file(os.path.join(firmware_location, file))
            copy_file(os.path.join(firmware_relative_tree, file), dst)
    else:
        logger.warning("Skipping root files update")

    if default_settings:
        settings = "settings.toml"
        with open(os.path.join(firmware_relative_tree, settings), mode="w") as f:
            f.write(
                "\n".join(
                    [
                        f"IS_LEFT_SIDE={int(is_left_side)}",
                        "DEBUG=0",
                        "LOG_LEVEL=0",
                    ]
                )
            )
        copy_file(os.path.join(firmware_relative_tree, settings), dst)
        delete_file(os.path.join(firmware_relative_tree, settings))
    else:
        logger.warning("Skipping settings reset (settings.toml)")

    if libs:
        logger.info("Installing libs...")
        python_firmware_files: list[str] = [
            "keys.py",
            "kb.py",
        ]
        for file in python_firmware_files:
            install_circuitpython_libs(dst, os.path.join(firmware_location, file))

        install_circuitpython_libs(dst, "boot.py")
        install_circuitpython_libs(dst, "code.py")
    else:
        logger.warning("Skipping installation of CircuitPython libs")

    if not _WINDOWS:
        logger.info("Unmounting...")
        unmount(dst)


@app.command(name="run")
def run(
    side: Literal["r", "l", "right", "left"] = typer.Option(
        "left",
        case_sensitive=False,
        help="Keyboard side destination",
    ),
    preprend_params: bool = typer.Option(
        True,
        help="Prepend local params",
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.DEBUG,
        help="Device's log level",
    ),
):
    """Run code.py"""

    # Local code to inject
    if preprend_params:
        with open(os.path.join("roki", "cli", "local_params.py")) as f:
            preprend_code = f.read()
            preprend_code = replace_params(
                preprend_code,
                {
                    "debug": True,
                    "log_level": log_level.value,
                    "is_left_side": side.startswith("l"),
                },
            )
            logger.debug("Prepending code: ")
            logger.debug(preprend_code)
    else:
        logger.info("No params override")
        preprend_code = ""

    files = [
        os.path.join(firmware_relative_tree, "boot.py"),
        os.path.join(firmware_relative_tree, "code.py"),
    ]
    debug_codes(files, preprend_code)


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

    logger.info("Opening configurator TUI")
    app = Configurator()
    app.run()
