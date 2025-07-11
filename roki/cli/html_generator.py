import json


from roki.cli.config.keys import KEYS


class Generator:
    def __init__(self, minify=True) -> None:
        from jinja2 import Environment, PackageLoader

        self.minify = minify
        self.env = Environment(
            loader=PackageLoader("roki"),
            autoescape=False,
        )

    def get_html(self):
        try:
            import minify_html
        except ImportError:
            self.minify = False

        keys = json.dumps([k.model_dump() for k in KEYS], separators=(",", ":"))
        template = self.env.get_template("base.html")
        html = template.render(keys=keys)

        if self.minify:
            html = minify_html.minify(
                html,
                minify_js=True,
                minify_css=True,
            )

        return html

    def generate_html(self):
        html = self.get_html()
        with open("index.html", mode="w+") as f:
            f.write(html)
