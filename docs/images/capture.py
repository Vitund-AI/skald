#!/usr/bin/env python3
"""Capture the README board and story screenshots from a served project.

    docs/images/make-demo.sh /tmp/wireguard-overlay
    (cd /tmp/wireguard-overlay && skald server start)
    pip install playwright && playwright install chromium
    python3 docs/images/capture.py wireguard-overlay docs/images

Board captures are 1640x560 at device pixel ratio 2, once per theme (the theme is set
through the board's own localStorage key); the story capture is 1640x1080 in the dark
theme with one story's dialog open. The board loads Tailwind and marked from CDNs and its
fonts from Google Fonts; where the browser cannot reach them, put copies at tailwind.js and
marked.js beside this script, and a fonts/ directory holding the Google Fonts stylesheet as
fonts.css with its font files beside it, referenced as http://127.0.0.1:1/NAME.woff2, and
they are served from disk.
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
STORY = "Implement WireGuard overlay"


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
        for scheme in ("light", "dark"):
            for name, size in (("board", (1640, 560)), ("story", (1640, 1080))):
                if name == "story" and scheme == "light":
                    continue
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=2, color_scheme=scheme)
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
                if name == "story":
                    page.click(f".card:has-text('{STORY}')")
                    page.wait_for_selector("#modal:not(.hidden)", timeout=10000)
                    page.wait_for_timeout(500)
                    target = out / "story.png"
                else:
                    target = out / f"board-{scheme}.png"
                page.screenshot(path=str(target))
                print("wrote", target)
                ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
