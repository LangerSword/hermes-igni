#!/usr/bin/env python3
"""Render cover/cover.html to docs/cover.png at 1600x900."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "cover" / "cover.html"
OUT = ROOT / "docs" / "cover.png"


def main() -> int:
    OUT.parent.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        page.goto(HTML.as_uri())
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT), full_page=False)
        browser.close()
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
