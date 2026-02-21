import logging

import typer

logger = logging.getLogger(__name__)


class LevelBasedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        log_fmt = format_by_level(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def format_by_level(level: int):
    LEVELS: dict[int, str] = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }
    COLORS: dict[int, str] = {
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
    return f"{level_part} [%(process)d] {time_part} %(name)s {message_part}"


def configure_logging(log_level: int):
    if log_level:
        handler: logging.Handler = logging.StreamHandler()
    else:
        handler: logging.Handler = logging.NullHandler()

    handler.setFormatter(LevelBasedFormatter())
    handler.setLevel(log_level)

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
    )

    logger.debug(f"Log level set to {logging.getLevelName(log_level)}")
