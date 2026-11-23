#!/usr/bin/env python3
"""Build the card art: 1K Krea output -> 256px, 24-colour pure pixel art.

The committed `art/*.webp` files are the deliverable; this script is kept so
the deck can be rebuilt from the same raw generations. Raw files are not in the
repo (they live in the Hermes image cache).

Usage:
    python3 scripts/build_card_art.py --source-dir ~/.hermes/cache/generated/images
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "art"
DOCS_DIR = ROOT / "docs"

# name -> raw filename produced by the Krea batch
SOURCES = {
    "gwent_infantry": "krea_krea-3_20261124_001004_5f02d624.png",
    "gwent_archer": "krea_krea-3_20261124_001144_a8338bf0.png",
    "gwent_siege": "krea_krea-3_20261124_001139_bf026812.png",
    "gwent_hero_ash": "krea_krea-3_20261124_001148_1bcb841a.png",
    "gwent_hero_lady": "krea_krea-3_20261124_001144_f54b23f1.png",
    "gwent_hero_obsidian": "krea_krea-3_20261124_001208_86275dca.png",
    "gwent_spy": "krea_krea-3_20261124_001207_9798b21e.png",
    "weather_frost": "krea_krea-3_20261124_001208_08672b4b.png",
    "weather_fog": "krea_krea-3_20261124_001212_7489bf39.png",
    "weather_rain": "krea_krea-3_20261124_001231_5379f7ed.png",
    "weather_clear": "krea_krea-3_20261124_001533_4f95887e.png",
    "gwent_horn": "krea_krea-3_20261124_001230_4de993b9.png",
    "gwent_scorch": "krea_krea-3_20261124_001227_c900343a.png",
    "arena_guard": "krea_krea-3_20261124_001226_ff4c377e.png",
    "arena_duelist": "krea_krea-3_20261124_001258_ca2415ff.png",
    "arena_mage": "krea_krea-3_20261124_001258_d0322f0e.png",
    "arena_giant": "krea_krea-3_20261124_001257_705fb1d7.png",
    "spell_bolt": "krea_krea-3_20261124_001303_f3210a35.png",
    "spell_draw": "krea_krea-3_20261124_001325_3e26f948.png",
    "spell_heal": "krea_krea-3_20261124_001325_59034006.png",
    "card_back": "krea_krea-3_20261124_001325_75155dda.png",
}

SIZE = 256
COLORS = 24


def build(raw: Path) -> Image.Image:
    image = Image.open(raw).convert("RGB")
    image = image.resize((SIZE, SIZE), Image.LANCZOS)
    image = image.quantize(colors=COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    return image.convert("RGB")


def contact_sheet(images: dict[str, Image.Image]) -> None:
    columns = 5
    cell = SIZE + 26
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * cell), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    for index, (name, image) in enumerate(images.items()):
        x = (index % columns) * cell
        y = (index // columns) * cell
        sheet.paste(image, (x, y))
        draw.text((x + 2, y + SIZE + 4), name, fill=(226, 220, 204), font=font)
    DOCS_DIR.mkdir(exist_ok=True)
    sheet.save(DOCS_DIR / "card-art-grid.png")
    print(f"contact sheet -> {DOCS_DIR / 'card-art-grid.png'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="~/.hermes/cache/generated/images")
    args = parser.parse_args()
    source = Path(args.source_dir).expanduser()
    ART_DIR.mkdir(exist_ok=True)
    built: dict[str, Image.Image] = {}
    for name, filename in SOURCES.items():
        raw = source / filename
        if not raw.exists():
            print(f"MISSING {raw}")
            continue
        image = build(raw)
        image.save(ART_DIR / f"{name}.webp", "WEBP", quality=92, method=6)
        built[name] = image
        print(f"{name}: {raw.name} -> art/{name}.webp")
    if built:
        contact_sheet(built)
    return 0 if len(built) == len(SOURCES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
