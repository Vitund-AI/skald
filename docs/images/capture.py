#!/usr/bin/env python3
"""Capture the README board and story screenshots from a served project.

    docs/images/make-demo.sh /tmp/wireguard-overlay
    (cd /tmp/wireguard-overlay && skald server start)
    pip install playwright && playwright install chromium
    python3 docs/images/capture.py wireguard-overlay docs/images

Board captures are 1640x560 at device pixel ratio 2, light and dark by the OS colour
scheme the page follows; the story capture is 1640x1080 with one story's dialog open. The
board loads Tailwind and marked from CDNs; where the browser cannot reach them, put copies
at tailwind.js and marked.js beside this script and they are served from disk.
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
    url = f"http://127.0.0.1:{port}/?project={project}#key={token}"
    local = {name: (HERE / f"{name}.js").read_bytes() for name in ("tailwind", "marked") if (HERE / f"{name}.js").exists()}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        for scheme in ("light", "dark"):
            for name, size in (("board", (1640, 560)), ("story", (1640, 1080))):
                if name == "story" and scheme == "dark":
                    continue
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=2, color_scheme=scheme)
                page = ctx.new_page()
                if "tailwind" in local:
                    page.route("https://cdn.tailwindcss.com*", lambda r: r.fulfill(body=local["tailwind"], content_type="text/javascript"))
                if "marked" in local:
                    page.route("https://cdnjs.cloudflare.com/**", lambda r: r.fulfill(body=local["marked"], content_type="text/javascript"))
                page.goto(url)
                page.wait_for_selector(".card", timeout=20000)
                page.wait_for_function("typeof tailwind === 'object'", timeout=20000)
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
