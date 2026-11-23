#!/usr/bin/env python3
"""Render the desktop plugin's Table page with a fixture (no live gateway)."""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "test" / "ui-fixture.json"
HARNESS = ROOT / "test" / "harness.html"
OUT = ROOT / "docs" / "desktop.png"


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 8123), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
            page.on("console", lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGEERROR: {err}"))
            page.add_init_script("window.__FIXTURE__ = " + json.dumps(fixture))
            page.goto("http://127.0.0.1:8123/test/harness.html")
            try:
                page.wait_for_selector("#root img", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(2500)
            print("ROOT:", page.locator("#root").inner_html()[:1200])
            page.screenshot(
                path=str(OUT),
                full_page=False,
                clip={"x": 0, "y": 0, "width": 1100, "height": 800},
            )
            browser.close()
    finally:
        server.shutdown()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
