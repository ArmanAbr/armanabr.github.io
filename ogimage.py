#!/usr/bin/env python3
"""
Open Graph card generator.

Renders a 1200x630 PNG "social card" for each page so that links shared on
LinkedIn, X, Slack, Discord, etc. show a branded preview instead of a bare
text link. Called from build.py; no network access, pure Pillow.

Fonts are resolved at runtime from a candidate list: bundled fonts in
static/fonts/ win, then DejaVu (present on the GitHub Actions Ubuntu runner),
then common Windows/macOS system fonts, then Pillow's built-in fallback. This
means local previews use whatever good font you have, and the *published* cards
(always rebuilt in CI) render identically for every visitor.
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except Exception:                                        # pragma: no cover
    PIL_OK = False


# 1200x630 is the canonical OG size; LinkedIn/X both crop toward the centre.
W, H = 1200, 630
PAD = 80

# Palette — a dark, branded card that looks sharp in any feed regardless of the
# viewer's theme. Kept in sync with the teal accent used across the site.
BG_TOP = (13, 20, 30)
BG_BOT = (8, 12, 18)
ACCENT = (45, 212, 191)          # teal-400
FG_STRONG = (243, 247, 250)
FG = (208, 216, 226)
FG_MUTED = (139, 152, 168)
FG_DIM = (99, 112, 127)
LINE = (32, 42, 54)

DIFF_COLORS = {
    "very easy": (74, 222, 128), "easy": (74, 222, 128),
    "medium": (251, 191, 36), "hard": (248, 113, 113),
    "insane": (167, 139, 250),
}

# Font candidates, in priority order. First existing file wins.
_SANS_REG = [
    "static/fonts/Inter-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_SANS_BOLD = [
    "static/fonts/Inter-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_MONO = [
    "static/fonts/JetBrainsMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]

_font_cache: dict = {}


def _first_existing(paths: list[str], root: Path) -> str | None:
    for p in paths:
        cand = (root / p) if not Path(p).is_absolute() else Path(p)
        if cand.is_file():
            return str(cand)
    return None


def _font(root: Path, kind: str, size: int):
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    table = {"reg": _SANS_REG, "bold": _SANS_BOLD, "mono": _MONO}[kind]
    path = _first_existing(table, root)
    try:
        font = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _text_w(draw, text, font) -> int:
    return int(draw.textlength(text, font=font))


def _wrap(draw, text, font, max_w: int, max_lines: int) -> list[str]:
    words = str(text).split()
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if _text_w(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    # Ellipsise if we ran out of room.
    if len(lines) == max_lines and words:
        joined = " ".join(lines)
        if len(joined.split()) < len(words):
            while lines and _text_w(draw, lines[-1] + "…", font) > max_w:
                lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
            lines[-1] = lines[-1] + "…"
    return lines


def _fit(draw, root: Path, kind: str, text: str, max_size: int, min_size: int,
         max_w: int, max_lines: int):
    """Largest font size at which `text` wraps within max_lines and max_w with
    no word dropped. Returns (font, lines, size). Makes the layout robust to
    the font differing between local (Segoe/Arial) and CI (DejaVu, wider)."""
    want = len(str(text).split())
    for size in range(max_size, min_size - 1, -2):
        f = _font(root, kind, size)
        lines = _wrap(draw, text, f, max_w, max_lines)
        got = sum(len(l.split()) for l in lines)
        no_ellipsis = all(not l.endswith("…") for l in lines)
        width_ok = all(_text_w(draw, l, f) <= max_w for l in lines)
        if got >= want and no_ellipsis and width_ok:
            return f, lines, size
    f = _font(root, kind, min_size)
    return f, _wrap(draw, text, f, max_w, max_lines), min_size


def _gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_BOT)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = round(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = round(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = round(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def _rounded(draw, box, radius, **kw):
    draw.rounded_rectangle(box, radius=radius, **kw)


def _brand_row(draw, root, site_short):
    # Accent mark + wordmark, top-left.
    mx, my = PAD, PAD
    _rounded(draw, [mx, my, mx + 34, my + 34], 8, outline=ACCENT, width=3)
    _rounded(draw, [mx + 9, my + 9, mx + 25, my + 25], 3, fill=ACCENT)
    f = _font(root, "mono", 30)
    draw.text((mx + 50, my + 1), site_short, font=f, fill=FG_STRONG)


def _accent_footer(draw, site_url):
    # thin accent strip + url, bottom.
    draw.rectangle([0, H - 8, W, H], fill=ACCENT)


def _paste_logo(img, root: Path, logo_path: str):
    if not logo_path:
        return
    p = root / logo_path
    if not p.is_file():
        return
    try:
        logo = Image.open(p).convert("RGBA")
    except Exception:
        return
    size = 150
    logo.thumbnail((size, size), Image.LANCZOS)
    # rounded backing panel
    panel = Image.new("RGBA", (size + 36, size + 36), (21, 28, 37, 255))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle([0, 0, panel.width - 1, panel.height - 1],
                           radius=20, outline=(45, 212, 191, 90), width=2)
    px = W - PAD - panel.width
    py = PAD - 4
    img.paste(panel, (px, py), panel)
    lx = px + (panel.width - logo.width) // 2
    ly = py + (panel.height - logo.height) // 2
    img.paste(logo, (lx, ly), logo)


def generate_card(out_path: Path, root: Path, *, title: str, kind: str = "",
                  date_str: str = "", tags: list[str] | None = None,
                  difficulty: str = "", logo_path: str = "",
                  site_short: str = "", site_url: str = "") -> bool:
    """Render one content card. Returns True on success."""
    if not PIL_OK:
        return False
    tags = tags or []
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)

    _brand_row(draw, root, site_short)
    _paste_logo(img, root, logo_path)

    # Kind + date eyebrow.
    eyebrow_parts = [p for p in (kind.upper() if kind else "", date_str) if p]
    y = 210
    if eyebrow_parts:
        f = _font(root, "mono", 24)
        eb = "   ·   ".join(eyebrow_parts)
        draw.text((PAD, y), eb, font=f, fill=ACCENT)
        y += 46

    # Title — auto-sized so it fits within 2 lines without overflowing.
    title_font, lines, tsize = _fit(draw, root, "bold", title, 68, 44,
                                    W - 2 * PAD, max_lines=2)
    line_h = int(tsize * 1.24)
    for line in lines:
        draw.text((PAD, y), line, font=title_font, fill=FG_STRONG)
        y += line_h

    # Difficulty chip (writeups).
    y = min(y + 10, H - 170)
    if difficulty:
        dc = DIFF_COLORS.get(difficulty.lower(), FG_MUTED)
        f = _font(root, "mono", 22)
        label = difficulty.upper()
        tw = _text_w(draw, label, f)
        _rounded(draw, [PAD, y, PAD + tw + 34, y + 40], 20, outline=dc, width=2)
        draw.text((PAD + 17, y + 8), label, font=f, fill=dc)

    # Tags row along the bottom.
    if tags:
        f = _font(root, "mono", 24)
        tx, ty = PAD, H - 120
        for tag in tags[:6]:
            label = "#" + tag
            tw = _text_w(draw, label, f)
            if tx + tw + 34 > W - PAD:
                break
            _rounded(draw, [tx, ty, tx + tw + 30, ty + 44], 10,
                     fill=(20, 27, 36), outline=LINE, width=1)
            draw.text((tx + 15, ty + 9), label, font=f, fill=FG_MUTED)
            tx += tw + 30 + 12

    # Footer: url.
    f = _font(root, "mono", 24)
    draw.text((PAD, H - 62), site_url.replace("https://", "").replace("http://", ""),
              font=f, fill=FG_DIM)
    _accent_footer(draw, site_url)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return True


def generate_default(out_path: Path, root: Path, *, title: str, subtitle: str = "",
                     eyebrow: str = "SECURITY WRITEUPS · RESEARCH · CHEATSHEETS",
                     site_short: str = "", site_url: str = "") -> bool:
    """Render the fallback card used for the home page and index pages."""
    if not PIL_OK:
        return False
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    _brand_row(draw, root, site_short)

    maxw = W - 2 * PAD
    f_eye = _font(root, "mono", 30)
    draw.text((PAD, 244), eyebrow, font=f_eye, fill=ACCENT)

    # Name on a single line, auto-sized so it can never wrap/overflow.
    title_font, tlines, tsize = _fit(draw, root, "bold", title, 96, 56, maxw, 1)
    line_h = int(tsize * 1.14)
    y = 302
    for line in tlines:
        draw.text((PAD, y), line, font=title_font, fill=FG_STRONG)
        y += line_h

    if subtitle:
        sf, slines, ssize = _fit(draw, root, "reg", subtitle, 34, 22, maxw, 1)
        y += 8
        for line in slines:
            draw.text((PAD, y), line, font=sf, fill=FG)
            y += int(ssize * 1.35)

    f = _font(root, "mono", 24)
    draw.text((PAD, H - 62), site_url.replace("https://", "").replace("http://", ""),
              font=f, fill=FG_DIM)
    draw.rectangle([0, H - 8, W, H], fill=ACCENT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return True
