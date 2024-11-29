import json
import minify_html
from http.server import BaseHTTPRequestHandler

from jinja2 import Environment, PackageLoader

from roki.cli.config.keys import KEYS


class WebHandler(BaseHTTPRequestHandler):
    def get_response(self):
        return Generator().get_html()

    def do_GET(self):
        if self.path != "/":
            return ""

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.get_response().encode("utf-8"))


class Generator:
    def __init__(self, minify=True) -> None:
        self.minify = minify
        self.env = Environment(
            loader=PackageLoader("roki"),
            autoescape=False,
        )

    def get_html(self):
        keys = json.dumps([k.model_dump() for k in KEYS])
        template = self.env.get_template("base.html")
        html = template.render(keys=keys)

        if self.minify:
            html = minify_html.minify(
                html,
                minify_js=True,
                minify_css=True,
                remove_processing_instructions=True,
                remove_bangs=True,
            )

        return html

    def generate_html(self):
        html = self.get_html()
        with open("index.html", mode="w+") as f:
            f.write(html)
