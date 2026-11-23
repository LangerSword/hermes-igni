#!/usr/bin/env python3
"""Preview stills and record the kinetic film and end card."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "demo" / "raw"
RAW.mkdir(parents=True, exist_ok=True)


def record(page, duration_ms: int, out: Path) -> None:
    page.wait_for_function("window.__filmReady === true", timeout=20000)
    page.evaluate("window.__startFilm()")
    page.wait_for_timeout(duration_ms)
    context = page.context
    video = page.video
    context.close()
    source = Path(video.path())
    shutil.copy2(source, out)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


def main() -> int:
    stills = "--stills" in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--allow-file-access-from-files", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        for name, html, duration in (
            ("kinetic", "kinetic.html", 27200),
            ("endcard", "endcard.html", 8300),
        ):
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=str(RAW),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.goto((ROOT / "demo" / html).as_uri(), wait_until="load")
            page.wait_for_function("window.__filmReady === true", timeout=20000)
            if stills:
                for t in (1, 4.8, 9.2, 13.6, 19.0, 23.5):
                    page.evaluate("t => window.__render(t)", t)
                    page.wait_for_timeout(80)
                    page.screenshot(path=str(RAW / f"still-{name}-{t}.png"))
                context.close()
                continue
            page.evaluate("window.__startFilm()")
            page.wait_for_timeout(duration)
            video = page.video
            context.close()
            source = Path(video.path())
            out = RAW / f"{name}.webm"
            shutil.copy2(source, out)
            print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
