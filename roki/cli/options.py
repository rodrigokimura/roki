import logging

import typer

from roki.cli.logging import configure_logging


def verbose_callback(verbose: int):
    verbose_to_log_level_mapping: dict[int, int] = {
        0: logging.NOTSET,
        1: logging.ERROR,
        2: logging.INFO,
        3: logging.DEBUG,
    }
    if verbose not in verbose_to_log_level_mapping:
        raise typer.BadParameter("Invalid verbose option")

    log_level = verbose_to_log_level_mapping[verbose]
    configure_logging(log_level)


VERBOSE_OPTION: int = typer.Option(
    0,
    "-v",
    "--verbose",
    count=True,
    callback=verbose_callback,
    help="Enable verbose output for debugging.",
)
