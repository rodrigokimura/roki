import json
import os
import subprocess

DEVICE_NAME = "CIRCUITPY"

_WINDOWS = os.name == "nt"


def get_devices() -> list[str]:
    if _WINDOWS:
        return get_devices_in_windows()
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
            print(port.manufacturer)
            print(port.description)
            print(port.device)
            return str(port.device)
    else:
        vendor = "Nice Keyboards"
        intf = "CircuitPython CDC control"

        if r := subprocess.check_output("rshell -l".split()):
            r = r.decode()
            print(r)
            try:
                return next(
                    d.split("@")[-1]
                    for d in r.splitlines()
                    if vendor in d and intf in d
                )
            except StopIteration:
                return ""


def debug_code(file: str):
    if SERIAL_DEVICE := get_serial_device():
        run_command(f"ampy -p {SERIAL_DEVICE} run {file}")


def debug_codes(files: list[str]):
    if SERIAL_DEVICE := get_serial_device():
        for file in files:
            run_command(f"ampy -p {SERIAL_DEVICE} run {file}")
