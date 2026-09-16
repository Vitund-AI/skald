#!/usr/bin/env python3
"""Capture the README and docs screenshots from a served demo project.

    docs/images/make-demo.sh /tmp/wireguard-overlay
    (cd /tmp/wireguard-overlay && skald server start)
    pip install playwright && playwright install chromium
    python3 docs/images/capture.py wireguard-overlay docs/images

Shots are declared in SHOTS below. To showcase a new feature: add it to the
demo in make-demo.sh, then add a shot here with a `setup` that drives the board
to the view, and re-run. Each shot is captured at device pixel ratio 2 in its
theme; `setup(page)` runs after the board has loaded and before the screenshot.

The board loads Tailwind and marked from CDNs and its fonts from Google Fonts;
where the browser cannot reach them (a sandbox behind a proxy), put copies at
tailwind.js and marked.js beside this script, and a fonts/ directory holding the
Google Fonts stylesheet as fonts.css with its font files beside it, referenced
as http://127.0.0.1:1/NAME.woff2, and they are served from disk. Those copies
are ignored by git.
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORY = "Implement WireGuard overlay"


def open_story(page):
    """The story dialog in view mode."""
    page.click(f".card:has-text('{STORY}')")
    page.wait_for_selector("#modal:not(.hidden)", timeout=10000)
    page.wait_for_timeout(500)


def swimlanes(page):
    """The board split into one lane per `area:` facet value, with per-lane progress."""
    page.select_option("#group-by", "area")
    page.wait_for_timeout(500)


# Each shot: a name (the PNG stem), a viewport size, a theme, an optional
# setup(page) that reaches the view, and full_page for shots taller than the
# viewport (the swimlanes stack).
SHOTS = [
    {"name": "board-dark", "size": (1640, 560), "theme": "dark"},
    {"name": "board-light", "size": (1640, 560), "theme": "light"},
    {"name": "story", "size": (1640, 1080), "theme": "dark", "setup": open_story},
    {"name": "swimlanes", "size": (1640, 900), "theme": "dark", "setup": swimlanes, "full_page": True},
]


def main() -> int:
    project, out = sys.argv[1], Path(sys.argv[2])
    home = Path(os.environ.get("SKALD_HOME") or (Path.home() / ".config" / "skald"))
    token = (home / "token").read_text().strip()
    port = json.loads((home / "server.json").read_text())["port"]
    fonts = HERE / "fonts"
    url = f"http://127.0.0.1:{port}/?project={project}#key={token}"
    local = {name: (HERE / f"{name}.js").read_bytes() for name in ("tailwind", "marked") if (HERE / f"{name}.js").exists()}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        for shot in SHOTS:
            width, height = shot["size"]
            scheme = shot["theme"]
            ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2, color_scheme=scheme)
            ctx.add_init_script(f"try {{ localStorage.setItem('skald.theme', '{scheme}'); }} catch (e) {{}}")
            page = ctx.new_page()
            if (fonts / "fonts.css").exists():
                page.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(body=(fonts / "fonts.css").read_bytes(), content_type="text/css"))
                page.route("http://127.0.0.1:1/**", lambda r: r.fulfill(body=(fonts / r.request.url.rsplit("/", 1)[1]).read_bytes(), content_type="font/woff2"))
            if "tailwind" in local:
                page.route("https://cdn.tailwindcss.com*", lambda r: r.fulfill(body=local["tailwind"], content_type="text/javascript"))
            if "marked" in local:
                page.route("https://cdnjs.cloudflare.com/**", lambda r: r.fulfill(body=local["marked"], content_type="text/javascript"))
            page.goto(url)
            page.wait_for_selector(".card", timeout=20000)
            page.wait_for_function("typeof tailwind === 'object'", timeout=20000)
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=20000)
            page.wait_for_timeout(1000)
            if shot.get("setup"):
                shot["setup"](page)
            target = out / f"{shot['name']}.png"
            page.screenshot(path=str(target), full_page=shot.get("full_page", False))
            print("wrote", target)
            ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
