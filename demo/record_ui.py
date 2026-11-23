#!/usr/bin/env python3
"""Record the real Igni table page for the 60s demo.

Starts the FastAPI demo backend in a thread, records the page through
Playwright at 1920x1080, then saves the raw WebM. The edit trims the pre-roll.
"""

from __future__ import annotations

import shutil
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

import server

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "demo" / "raw"
OUT = RAW / "ui.webm"


def wait_for_server(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not start: {url}")


def centre(page, locator):
    box = locator.bounding_box()
    if box is None:
        raise RuntimeError("locator has no box")
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def glide_click(page, locator, wait_ms: int = 900) -> None:
    # The live page has a slow camera drift, so Playwright's stability wait
    # never settles. Drive the mouse from the current box instead.
    x, y = centre(page, locator)
    page.mouse.move(x, y, steps=28)
    page.wait_for_timeout(500)
    page.mouse.down()
    page.wait_for_timeout(90)
    page.mouse.up()
    page.wait_for_timeout(wait_ms)


def glide_to(page, locator, wait_ms: int = 1000) -> None:
    x, y = centre(page, locator)
    page.mouse.move(x, y, steps=30)
    page.wait_for_timeout(wait_ms)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for old in RAW.glob("*.webm"):
        old.unlink()

    config = uvicorn.Config(server.app, host="127.0.0.1", port=8124, log_level="warning")
    httpd = uvicorn.Server(config)
    thread = threading.Thread(target=httpd.run, daemon=True)
    thread.start()
    wait_for_server("http://127.0.0.1:8124/api/plugins/igni/state")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(RAW),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8124/demo/live-harness.html", wait_until="networkidle")
        page.wait_for_selector("text=IGNI", timeout=20000)
        page.wait_for_selector("#root img", timeout=20000)
        page.wait_for_timeout(1600)
        page.screenshot(path=str(RAW / "ui-start.png"))

        spy = page.locator("button").filter(has_text="Sigismund Dijkstra").first
        glide_click(page, spy, 1200)
        page.screenshot(path=str(RAW / "ui-selected.png"))

        play = page.get_by_role("button", name="Play", exact=True)
        glide_click(page, play, 3600)
        page.screenshot(path=str(RAW / "ui-played.png"))

        opponent = page.locator("text=Opponent").first
        glide_to(page, opponent, 2200)
        opponent_score = page.locator("text=score").first
        if opponent_score.is_visible():
            glide_to(page, opponent_score, 1800)

        arena = page.get_by_role("button", name="New Arena", exact=True)
        glide_click(page, arena, 3000)
        page.wait_for_selector("text=ARENA", timeout=10000)
        page.screenshot(path=str(RAW / "ui-arena.png"))

        hand = page.locator("text=YOUR HAND").first
        glide_to(page, hand, 2200)
        page.mouse.move(1500, 820, steps=30)
        page.wait_for_timeout(2200)

        video = page.video
        context.close()
        source = Path(video.path())
        if not source.exists():
            raise RuntimeError("Playwright did not produce a video")
        shutil.copy2(source, OUT)
        browser.close()

    httpd.should_exit = True
    thread.join(timeout=5)
    print(f"recorded {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
