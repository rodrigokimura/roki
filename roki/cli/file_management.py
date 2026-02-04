import glob
import logging
import os
import shutil
from pathlib import Path

from roki.cli.utils import run_command

_WINDOWS = os.name == "nt"

logger = logging.getLogger(__name__)


def delete_files_by_extension(extensions: list[str], location: str):
    for ext in extensions:
        if _WINDOWS:
            for f in glob.glob(os.path.join(location, "*." + ext), recursive=True):
                delete_file(f)
        else:
            run_command(f"sudo rm {location}/*.{ext} -vf", shell=True)


def create_tree(path: str):
    if _WINDOWS:
        os.makedirs(path, exist_ok=True)
    else:
        run_command(f"sudo mkdir {path} -p", shell=True)


def copy_tree(
    source: str | Path, target: str | Path, extensions: list[str] | None = None
):
    if _WINDOWS:

        def copy(src, dst, **kw):
            if str(src).split(".")[-1] in (extensions or []):
                shutil.copy2(src, dst, **kw)

        os.makedirs(target, exist_ok=True)

        logger.debug("Executting copytree...")
        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            copy_function=copy,
        )
    else:
        if extensions:
            for extension in extensions:
                run_command(
                    f"sudo cp {source}/*.{extension} {target} -rpvf", shell=True
                )
        else:
            run_command(f"sudo cp {source}/* {target} -rpvf", shell=True)


def copy_file(file: str | Path, location: str | Path):
    if _WINDOWS:
        shutil.copy2(file, location)
    else:
        run_command(f"sudo cp {file} {location}/ -vf", shell=True)


def create_empty_file(file: str | Path):
    if _WINDOWS:
        with open(file, "w"):
            pass
    else:
        run_command(f"sudo touch {file}", shell=True)


def delete_file(file: str):
    if _WINDOWS:
        os.remove(file)
    else:
        run_command(f"sudo rm {file} -vf", shell=True)
