#!/usr/bin/env python3
"""Drive the running Hermes desktop renderer over CDP (dev probe).

Usage:
    python3 scripts/desktop_probe.py enable-table
    python3 scripts/desktop_probe.py eval "<js expression>"
    python3 scripts/desktop_probe.py click-table
    python3 scripts/desktop_probe.py shot /path.png

Requires the app launched with --remote-debugging-port=9223, and the venv's
`websockets` package. This is a development probe, not part of the plugin.
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
import urllib.request

import websockets

PORT = 9223


def page_target() -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=5) as resp:
        targets = json.load(resp)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        raise SystemExit("no page target")
    return pages[0]


async def evaluate(ws, expression: str, msg_id: int = 1) -> dict:
    await ws.send(
        json.dumps(
            {
                "id": msg_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            }
        )
    )
    while True:
        message = json.loads(await ws.recv())
        if message.get("id") == msg_id:
            return message


async def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "eval"
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    page = page_target()
    print(f"target: {page.get('title')} {page.get('url')}")
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=2**25) as ws:
        if action == "eval":
            result = await evaluate(ws, arg)
            print(json.dumps(result, indent=1)[:8000])
            return 0
        if action == "enable-table":
            before = await evaluate(ws, "localStorage.getItem('hermes.desktop.pluginDecisions.v2')", 1)
            print("before:", before.get("result", {}).get("result", {}).get("value"))
            expr = """(() => {
              const k = 'hermes.desktop.pluginDecisions.v2'
              let v = {}
              try { v = JSON.parse(localStorage.getItem(k) || '{}') } catch (e) {}
              v.table = true
              localStorage.setItem(k, JSON.stringify(v))
              return localStorage.getItem(k)
            })()"""
            after = await evaluate(ws, expr, 2)
            print("after:", after.get("result", {}).get("result", {}).get("value"))
            await ws.send(json.dumps({"id": 3, "method": "Page.reload", "params": {"ignoreCache": True}}))
            print("reloaded")
            return 0
        if action == "click-table":
            expr = """(() => {
              const candidates = [...document.querySelectorAll('a,button,[role="button"]')]
              const el = candidates.find(e => e.textContent.trim() === 'Table')
              if (!el) return 'not found'
              el.click()
              return 'clicked ' + el.tagName
            })()"""
            result = await evaluate(ws, expr, 1)
            print(result.get("result", {}).get("result", {}).get("value"))
            return 0
        if action == "shot":
            await ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == 1:
                    data = message["result"]["data"]
                    with open(arg, "wb") as handle:
                        handle.write(base64.b64decode(data))
                    print(f"wrote {arg}")
                    return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
