import json
import pathlib
import subprocess


def get_devices() -> list[str]:
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
        if child["label"] == "CIRCUITPY"
    ]
    return [device["name"] for device in filtered_by_label]


def run_command(cmd: str, shell=False):
    if shell:
        subprocess.call(cmd, shell=True, umask=0)
    else:
        subprocess.call(cmd.split(), umask=0)


def create_mount_point(device: str, path: pathlib.Path):
    # options = "rw,nosuid,nodev,uid=1000,gid=1000,shortname=mixed,dmask=0077,utf8=1,showexec,flush,uhelper=udisks2"
    # cmd = f"sudo mount -o options={options} /dev/{device} {path}"
    cmd = f"sudo mount -o uid=1000,gid=1000 /dev/{device} {path}"
    run_command(cmd)


def unmount(path: pathlib.Path):
    run_command(f"sudo umount {path}")


def get_serial_device():
    vendor = "Nice Keyboards"
    intf = "CircuitPython CDC control"

    if r := subprocess.check_output("rshell -l".split()):
        r = r.decode()
        print(r)
        try:
            return next(
                d.split("@")[-1] for d in r.splitlines() if vendor in d and intf in d
            )
        except StopIteration:
            ...
