from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .keys import KEYS

app = FastAPI()


@app.get("/keys")
def get_keys():
    return KEYS


app.mount(
    "/",
    StaticFiles(directory=Path.cwd() / "src" / "config" / "static", html=True),
    name="static",
)
