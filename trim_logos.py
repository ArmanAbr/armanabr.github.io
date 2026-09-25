#!/usr/bin/env python3
"""
Trim transparent margins from machine/challenge logos so they all fill their
tile evenly. HackTheBox art often ships with a wide empty border, which makes
one card's logo look smaller than its neighbour's.

The image is cropped to its visible pixels, then centred on a square canvas, so
nothing is stretched. Already-tight logos are left alone; running it twice
changes nothing.

Usage:
    py trim_logos.py              # trim every logo that needs it
    py trim_logos.py --dry-run    # just report
    py trim_logos.py static/challenges/web.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent.resolve()
DEFAULT_DIRS = [ROOT / "static" / "machines", ROOT / "static" / "challenges"]
EXTS = (".png", ".webp")
ALPHA_FLOOR = 8      # ignore near-invisible pixels when measuring
SLACK = 0.02         # leave margins under 2% alone


def trim(path: Path, dry_run: bool = False) -> bool:
    im = Image.open(path)
    if im.mode not in ("RGBA", "LA"):
        return False
    im = im.convert("RGBA")
    mask = im.getchannel("A").point(lambda v: 255 if v > ALPHA_FLOOR else 0)
    box = mask.getbbox()
    if not box:
        return False

    w, h = im.size
    margin = max(box[0], box[1], w - box[2], h - box[3]) / max(w, h)
    if margin <= SLACK:
        return False

    cropped = im.crop(box)
    side = max(cropped.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))
    pct = round(margin * 100)
    print(f"  {path.relative_to(ROOT)}: {w}x{h} -> {side}x{side} (cut {pct}% margin)")
    if not dry_run:
        square.save(path, optimize=True)
    return True


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv[1:]

    targets: list[Path] = []
    if args:
        targets = [Path(a) if Path(a).is_absolute() else ROOT / a for a in args]
    else:
        for folder in DEFAULT_DIRS:
            if folder.is_dir():
                targets += [f for f in sorted(folder.iterdir())
                            if f.suffix.lower() in EXTS]

    print("Trimming logos..." + (" (dry run)" if dry_run else ""))
    changed = sum(trim(f, dry_run) for f in targets if f.is_file())
    print(f"  {changed} of {len(targets)} needed trimming")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
