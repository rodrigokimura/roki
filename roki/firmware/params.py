class Params:
    __slots__ = (
        "_instance",
        "IS_LEFT_SIDE",
        "DEBUG",
        "init_done",
    )
    _instance = None

    IS_LEFT_SIDE: bool
    DEBUG: bool

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_done = False
        return cls._instance

    def __init__(
        self,
        is_left_side: bool = True,
        debug: bool = False,
    ):
        if not self.init_done:
            self.IS_LEFT_SIDE = is_left_side
            self.DEBUG = debug
            self.init_done = True
