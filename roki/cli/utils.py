import json
import logging
import os
import subprocess

DEVICE_NAME = "CIRCUITPY"

_WINDOWS = os.name == "nt"

logger = logging.getLogger(__name__)


def get_devices() -> list[str]:
    if _WINDOWS:
        logger.debug("Get devices for Windows")
        return get_devices_in_windows()
    logger.debug("Get devices for Linux")
    return get_devices_in_linux()


def get_devices_in_windows() -> list[str]:
    drives: list[str] = os.listdrives()  # type: ignore
    return [drive for drive in drives if get_volume_name(drive) == DEVICE_NAME]


def get_volume_name(disk_name: str) -> str:
    import ctypes

    vol_name_buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetVolumeInformationW(  # type: ignore
        ctypes.c_wchar_p(disk_name),
        vol_name_buf,
        ctypes.sizeof(vol_name_buf),
        None,
        None,
        None,
        None,
        0,
    )
    return str(vol_name_buf.value)


def get_devices_in_linux() -> list[str]:
    columns = [
        "label",
        "vendor",
        "model",
        "mountpoint",
        "name",
    ]
    cmd = f"lsblk -o {','.join(columns)} -J"
    output = subprocess.check_output(cmd.split())

    result = json.loads(output)

    block_devices = result["blockdevices"]
    filtered_model_and_vendor = [
        dev
        for dev in block_devices
        if dev["model"] == "nice!nano" and dev["vendor"] == "Nice Key"
    ]
    filtered_by_label = [
        child
        for device in filtered_model_and_vendor
        for child in device["children"]
        if child["label"] == DEVICE_NAME
    ]
    return [device["name"] for device in filtered_by_label]


def run_command(cmd: str, shell=False):
    if shell:
        subprocess.call(cmd, shell=True, umask=0)
    else:
        subprocess.call(cmd.split(), umask=0)


def install_circuitpython_libs(path: str, file: str):
    cmd = f"circup --path {path} install --auto-file {file}"
    run_command(cmd)


def create_mount_point(device: str, path: str):
    cmd = f"sudo mount -o uid=1000,gid=1000 /dev/{device} {path}"
    run_command(cmd)


def unmount(path: str):
    run_command(f"sudo umount {path}")


def get_serial_device():
    from adafruit_board_toolkit import circuitpython_serial as cps

    if _WINDOWS:
        for port in cps.comports():
            logger.debug(port.manufacturer)
            logger.debug(port.description)
            logger.debug(port.device)
            return str(port.device)
    else:
        vendor = "Nice Keyboards"
        intf = "CircuitPython CDC control"

        if r := subprocess.check_output("rshell -l".split()):
            r = r.decode()
            logger.debug(r)
            try:
                return next(
                    d.split("@")[-1]
                    for d in r.splitlines()
                    if vendor in d and intf in d
                )
            except StopIteration:
                return ""


def replace_params(code: str, params: dict[str, bool | int]) -> str:
    # identify pattern
    lines = code.splitlines()
    new_code_lines: list[str] = []
    for line_no, line in enumerate(lines):
        for param_name, param_value in params.items():
            if param_name in line and "=" in line and "," in line:
                logger.debug("Line with param found: ")
                logger.debug(line)

                param_position = line.find(param_name)
                equals_position = line.find("=", param_position)
                end_position = line.find(",", equals_position)
                if end_position == -1:
                    end_position = line.find(")", equals_position)

                logger.info(f"Replacing param {param_name} to {param_value}")

                line = (
                    line[: equals_position + 1] + str(param_value) + line[end_position:]
                )
        new_code_lines.append(line)
    new_code = "\n".join(new_code_lines)

    logger.debug(new_code)

    return new_code


def debug_codes(files: list[str], prepend_code: str = ""):
    if SERIAL_DEVICE := get_serial_device():
        for file in files:
            with open(file) as f:
                content = f.read()
                if prepend_code:
                    content = prepend_code + "\n" + content

            run_code(content, SERIAL_DEVICE)
    else:
        logger.error("No device found!")


def run_code(
    code: str,
    port: str,
    timeout: int | None = None,
    no_output: bool = False,
):
    from ampy import files, pyboard

    class CustomPyboard(pyboard.Pyboard):
        def exec_(self, command, stream_output=False):
            data_consumer = None
            if stream_output:
                data_consumer = pyboard.stdout_write_bytes
            ret, ret_err = self.exec_raw(
                command,
                timeout=timeout,
                data_consumer=data_consumer,
            )
            if ret_err:
                raise pyboard.PyboardError("exception", ret, ret_err)
            return ret

        def execfile(self, filename, stream_output=False):
            import io

            with io.StringIO(filename) as f:
                pyfile = f.read()
            return self.exec_(pyfile, stream_output=stream_output)

    baud = 115200
    _board = CustomPyboard(port, baudrate=baud, rawdelay=0)
    board_files = files.Files(_board)
    try:
        output = board_files.run(
            code,
            not no_output,
            not no_output,
        )
        if output is not None:
            print(output.decode("utf-8"), end="")
    except IOError:
        logger.error("IO Error")
    except pyboard.PyboardError as e:
        logger.error("Pyboard Error")
        logger.error(e)
    except KeyboardInterrupt as e:
        logger.info("Exiting...")
        raise e from e
