from roki.cli.utils import run_command


def delete_files_by_extension(extensions: list[str], location: str):
    for ext in extensions:
        run_command(f"sudo rm {location}/*.{ext} -vf", shell=True)


def create_tree(path: str):
    run_command(f"sudo mkdir {path} -p", shell=True)


def copy_tree(source: str, target: str, extensions: list[str] | None = None):
    if extensions:
        for extension in extensions:
            run_command(f"sudo cp {source}/*.{extension} {target} -rpvf", shell=True)
    else:
        run_command(f"sudo cp {source}/* {target} -rpvf", shell=True)


def copy_file(file: str, location: str):
    run_command(f"sudo cp {file} {location}/ -vf", shell=True)


def create_empty_file(file: str):
    run_command(f"sudo touch {file}", shell=True)


def delete_file(file: str):
    run_command(f"sudo rm {file} -vf", shell=True)
