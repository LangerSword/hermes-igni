#!/usr/bin/env python3
"""Render the cover artifacts: docs/cover.png (1600x900) and docs/banner.png (1200x600).

The banner is the Hermes plugin-catalog card image, which the catalog spec requires to be
2:1 on a GitHub host. Both are rendered from real HTML with real type; nothing here is
generated lettering.

Rendering prefers Playwright. When Playwright is not installed it falls back to a headless
Chromium/Chrome binary, so the artifacts can be rebuilt from a bare checkout.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (html, out, width, height, device_scale_factor)
JOBS = (
    ("cover/cover.html", "docs/cover.png", 1600, 900, 1),
    ("cover/catalog.html", "docs/banner.png", 1200, 600, 2),
)


def _chromium_binary() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        Path.home() / ".local" / "bin" / "chromium",
        Path("/usr/bin/chromium"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _render_with_playwright(html: Path, out: Path, width: int, height: int, scale: int) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
        page.goto(html.as_uri())
        page.wait_for_timeout(900)
        page.screenshot(path=str(out), full_page=False)
        browser.close()


def _render_with_chromium(html: Path, out: Path, width: int, height: int, scale: int) -> None:
    binary = _chromium_binary()
    if binary is None:
        raise RuntimeError("no Playwright and no Chromium/Chrome binary found")
    cmd = [
        binary,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--force-device-scale-factor={scale}",
        f"--window-size={width},{height}",
        "--default-background-color=ff0b0a08",
        "--virtual-time-budget=3000",
        f"--screenshot={out}",
        str(html),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=180)


def _postprocess(out: Path, width: int, height: int, scale: int) -> None:
    """Downscale a 2x render to the target size and index it, when ImageMagick is present.

    A 1200x600 truecolor PNG of a halftone poster is ~900 KB; indexed to 256 colours it is
    ~225 KB at under 1% RMSE, which is what a catalog card should download.
    """
    if scale == 1:
        return
    magick = shutil.which("magick") or shutil.which("convert")
    if magick is None:
        return
    tmp = out.with_suffix(".raw.png")
    out.rename(tmp)
    subprocess.run(
        [magick, str(tmp), "-resize", f"{width}x{height}", "-strip", "-colors", "256",
         "-define", "png:compression-level=9", f"PNG8:{out}"],
        check=True, capture_output=True, timeout=120,
    )
    tmp.unlink(missing_ok=True)


def main() -> int:
    try:
        import playwright  # noqa: F401
        mode = "playwright"
    except ImportError:
        mode = "chromium"

    for rel_html, rel_out, width, height, scale in JOBS:
        html = ROOT / rel_html
        out = ROOT / rel_out
        if not html.exists():
            print(f"skip {rel_html}: missing", file=sys.stderr)
            continue
        out.parent.mkdir(exist_ok=True)
        if mode == "playwright":
            _render_with_playwright(html, out, width, height, scale)
        else:
            _render_with_chromium(html, out, width, height, scale)
        _postprocess(out, width, height, scale)
        size = out.stat().st_size if out.exists() else 0
        print(f"wrote {rel_out} ({width}x{height}, {size} bytes) via {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
