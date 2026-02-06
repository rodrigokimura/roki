import os


class Params:
    _instance = None

    IS_LEFT_SIDE: bool
    DEBUG: bool
    LOG_LEVEL: int

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_done = False
        return cls._instance

    def __init__(
        self,
        *,
        is_left_side: bool = True,
        debug: bool = False,
        log_level: int = 0,
    ):
        if not self.init_done:
            self.IS_LEFT_SIDE = is_left_side
            self.DEBUG = debug
            self.LOG_LEVEL = log_level
            self.init_done = True

    @classmethod
    def from_env(cls):
        Params(
            is_left_side=bool(int(os.getenv("IS_LEFT_SIDE", 1))),
            debug=bool(int(os.getenv("DEBUG", 0))),
            log_level=bool(int(os.getenv("LOG_LEVEL", 0))),
        )
