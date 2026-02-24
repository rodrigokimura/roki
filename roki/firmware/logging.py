import adafruit_logging as logging


def format_by_level(level: int) -> str:
    cyan = "\033[36m"
    magenta = "\033[35m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    dim = "\033[2m"
    reset = "\x1b[0m"

    names: dict[int, str] = {
        10: "debug",
        20: "info",
        30: "warning",
        40: "error",
        50: "critical",
    }

    colors: dict[int, str] = {
        10: magenta,
        20: cyan,
        30: yellow,
        40: red,
        50: bold_red,
    }

    level_part: str = colors[level] + f"[{names[level].upper():^10}]" + reset
    time_part: str = dim + "%(created)s" + reset
    message_part: str = colors[level] + "%(message)s" + reset
    return f"{level_part} {time_part} %(name)s {message_part}"


class LevelBasedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        log_fmt = format_by_level(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def getLogger(logger_name: str | None = None) -> logging.Logger:
    from roki.firmware.params import Params

    logger = logging.getLogger(logger_name)

    params = Params()

    if params.DEBUG:
        handler = logging.StreamHandler()
        handler.setLevel(params.LOG_LEVEL)
        logger.setLevel(params.LOG_LEVEL)
        handler.setFormatter(LevelBasedFormatter())
    else:
        handler = logging.NullHandler()
        handler.setLevel(0)
        logger.setLevel(0)

    logger.addHandler(handler)

    return logger
