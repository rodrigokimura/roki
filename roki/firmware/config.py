from __future__ import annotations

import json
import os

from roki.firmware.keys import KeyWrapper, init


def parse_color(
    color: str | list[int | str] | tuple[int | str, int | str, int | str],
) -> tuple[int, int, int]:
    if isinstance(color, str):
        if color[0] == "#":
            color = color[1:]
        if len(color) != 6:
            raise ValueError("Invalid color")
        r = color[:2]
        g = color[2:4]
        b = color[4:]
        return int(r, 16), int(g, 16), int(b, 16)

    if isinstance(color, (list, tuple)):
        return int(color[0]), int(color[1]), int(color[2])


class Layer:
    name: str
    color: tuple[int, int, int]
    primary_keys: tuple[tuple[KeyWrapper, ...], ...]
    secondary_keys: tuple[tuple[KeyWrapper, ...], ...]
    primary_encoder_cw: KeyWrapper
    primary_encoder_ccw: KeyWrapper
    secondary_encoder_cw: KeyWrapper
    secondary_encoder_ccw: KeyWrapper

    @classmethod
    def from_dict(cls, data: dict) -> Layer:
        is_left_side = bool(os.getenv("IS_LEFT_SIDE", True))
        i = cls()
        i.name = data.get("name", "no name")
        c = data.get("color", "#000000")
        i.color = parse_color(c)
        i.primary_keys = tuple(
            tuple(reversed([KeyWrapper(k) for k in row]))
            for row in data.get(
                "primary_keys" if is_left_side else "secondary_keys", (("",),)
            )
        )
        cw, ccw = data.get("primary_encoder", ("", ""))
        i.primary_encoder_cw = KeyWrapper(cw)
        i.primary_encoder_ccw = KeyWrapper(ccw)

        i.secondary_keys = tuple(
            tuple(reversed([KeyWrapper(k) for k in row]))
            for row in data.get(
                "secondary_keys" if is_left_side else "primary_keys", (("",),)
            )
        )
        cw, ccw = data.get("primary_encoder", ("", ""))
        i.secondary_encoder_cw = KeyWrapper(cw)
        i.secondary_encoder_ccw = KeyWrapper(ccw)
        return i


class Config:
    layers: tuple[Layer, ...]
    is_left_side: bool

    def __init__(self, layers: list[dict] | None = None) -> None:
        init(self)
        self.layer_index = 0
        self.layers = tuple(Layer.from_dict(layer) for layer in layers or tuple())
        self.is_left_side = bool(os.getenv("IS_LEFT_SIDE", False))

    @property
    def layer(self):
        return self.layers[self.layer_index]

    @classmethod
    def read(cls):
        with open("config.json") as file:
            config: dict = json.load(file)
        return cls(
            layers=config.get("layers", []),
        )
