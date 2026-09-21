#!/usr/bin/env python3
"""
Static site generator for a cybersecurity portfolio + blog.

Reads Markdown from content/, renders it with templates/base.html and the
styles in static/, and writes a fully static site to dist/ that can be served
by GitHub Pages (or any web server, or straight off the filesystem).

Usage:
    py build.py            # build into dist/
    py build.py --clean    # wipe dist/ first
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter

import ogimage

ROOT = Path(__file__).parent.resolve()
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

# Machine logos: drop a file in static/machines/ and reference it in a writeup's
# frontmatter as `image: <name>` (extension optional).
MACHINE_IMG_DIR = STATIC / "machines"
MACHINE_IMG_EXTS = (".png", ".svg", ".webp", ".jpg", ".jpeg", ".gif", ".avif")


def _build_version() -> str:
    """Short hash of the files that determine the OG cards + meta, used to
    version OG image URLs so social caches refetch when the card changes."""
    h = hashlib.md5()
    for rel in ("config.json", "ogimage.py", "static/css/style.css",
                "static/js/site.js", "templates/base.html"):
        fp = ROOT / rel
        if fp.exists():
            h.update(fp.read_bytes())
    return h.hexdigest()[:8]


BUILD_VERSION = _build_version()

# Each content type lives in content/<dir>/ and gets an index page at /<dir>/.
COLLECTIONS = [
    {
        "key": "writeups",
        "dir": "writeups",
        "title": "Writeups",
        "singular": "Writeup",
        "blurb": "Machine and challenge walkthroughs - enumeration, foothold, "
                 "privilege escalation, and what I took away from each box.",
    },
    {
        "key": "blog",
        "dir": "blog",
        "title": "Blog",
        "singular": "Post",
        "blurb": "Longer-form notes on tooling, techniques and things I broke "
                 "while learning them.",
    },
    {
        "key": "cheatsheets",
        "dir": "cheatsheets",
        "title": "Cheatsheets",
        "singular": "Cheatsheet",
        "blurb": "Condensed command references I keep open in a second monitor. "
                 "Copy, paste, adapt.",
    },
]
COLLECTION_BY_KEY = {c["key"]: c for c in COLLECTIONS}

DIFFICULTY_ORDER = {"intro": 0, "very easy": 1, "easy": 2, "medium": 3,
                    "hard": 4, "insane": 5}

# CTF walkthroughs: content/ctf/<event>/<Category>/<challenge>.md, with an
# event.md per CTF holding its metadata and a logo in static/ctf/.
CTF_DIR = CONTENT / "ctf"
CTF_IMG_DIR = STATIC / "ctf"
CTF_BLURB = ("Capture-the-Flag walkthroughs, grouped by event. Each challenge is a "
             "short, reproducible writeup - how I found the bug and pulled the flag.")
CATEGORY_ORDER = {
    "reverse engineering": 0, "reversing": 0, "reverse": 0, "rev": 0,
    "web": 1,
    "pwn": 2, "binary exploitation": 2,
    "crypto": 3, "cryptography": 3,
    "misc": 4,
    "forensics": 5,
    "game hacking": 6, "game-hacking": 6,
    "osint": 7, "hardware": 8, "mobile": 9, "blockchain": 10,
}

# Canonical display casing for categories (folders/frontmatter may vary).
CATEGORY_DISPLAY = {
    "reverse engineering": "Reverse Engineering", "reversing": "Reverse Engineering",
    "reverse": "Reverse Engineering", "rev": "Reverse Engineering",
    "web": "Web", "pwn": "Pwn", "binary exploitation": "Pwn",
    "crypto": "Crypto", "cryptography": "Crypto",
    "misc": "Misc", "forensics": "Forensics",
    "game hacking": "Game Hacking", "game-hacking": "Game Hacking",
    "osint": "OSINT", "hardware": "Hardware", "mobile": "Mobile",
    "blockchain": "Blockchain",
}


# Tags describe techniques and topics. Facts that have their own frontmatter
# field (difficulty, box status, platform) or add nothing (a year) are pulled
# out of the tag list, so filters, related posts and the tag cloud work on real
# topics. Their old /tags/<slug>/ pages become redirects (see build_tag_redirects).
DIFFICULTY_TAGS = {"intro": "Intro", "very-easy": "Very Easy", "easy": "Easy",
                   "medium": "Medium", "hard": "Hard", "insane": "Insane"}
STATUS_TAGS = {"active": "Active", "retired": "Retired"}
PLATFORM_TAGS = {"hackthebox": "HackTheBox", "htb": "HackTheBox",
                 "tryhackme": "TryHackMe", "thm": "TryHackMe"}
TAG_ALIASES = {"homelab": "home-lab", "privesc": "privilege-escalation",
               "ad": "active-directory"}

# slug -> site-relative URL that the retired tag page should redirect to.
RETIRED_TAGS: dict[str, str] = {}


def split_tags(raw) -> tuple[list[dict], dict]:
    """Normalise a tags value into topic tags + the facts pulled out of it."""
    if isinstance(raw, str):
        raw = [t.strip() for t in raw.split(",") if t.strip()]
    tags, facts, seen = [], {}, set()
    for t in raw or []:
        s = slugify(t)
        if not s:
            continue
        if s in TAG_ALIASES:
            RETIRED_TAGS[s] = f"tags/{TAG_ALIASES[s]}/"
            s = TAG_ALIASES[s]
        if s in DIFFICULTY_TAGS:
            facts.setdefault("difficulty", DIFFICULTY_TAGS[s])
            RETIRED_TAGS[s] = f"writeups/?difficulty={s}"
        elif s in STATUS_TAGS:
            facts.setdefault("status", STATUS_TAGS[s])
            RETIRED_TAGS[s] = f"writeups/?status={s}"
        elif s in PLATFORM_TAGS:
            facts.setdefault("platform", PLATFORM_TAGS[s])
            RETIRED_TAGS[s] = "writeups/"
        elif re.fullmatch(r"\d{4}", s):
            RETIRED_TAGS[s] = "blog/"
        elif s not in seen:
            seen.add(s)
            tags.append({"slug": s, "name": s})
    return tags, facts


def canon_category(name) -> str:
    n = str(name).strip()
    return CATEGORY_DISPLAY.get(n.lower(), n)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def slugify(value: str) -> str:
    """'CVE-2007-2447' -> 'cve-2007-2447', 'Active Directory' -> 'active-directory'."""
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-")


def e(value) -> str:
    """Escape a value for safe insertion into HTML."""
    return html.escape(str(value), quote=True)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Parse a small, predictable subset of YAML frontmatter.

    Supports:  key: value  |  key: [a, b]  |  key:\\n  - a\\n  - b
    Values may be quoted; true/false/numbers are converted.
    """
    if not text.lstrip().startswith("---"):
        return {}, text

    lines = text.lstrip().splitlines()
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text

    meta: dict = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        # A list item belonging to the previous key.
        if raw.lstrip().startswith("- ") and key:
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(_coerce(raw.lstrip()[2:].strip()))
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if value == "":
            meta[key] = []              # expecting a block list underneath
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            meta[key] = [_coerce(p.strip()) for p in inner.split(",") if p.strip()]
        else:
            meta[key] = _coerce(value)

    body = "\n".join(lines[end + 1:])
    return meta, body


def _coerce(value: str):
    """Strip quotes and convert obvious booleans / integers."""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def human_date(d: date | None) -> str:
    return d.strftime("%b %d, %Y") if d else ""


def human_date_range(start: date | None, end: date | None) -> str:
    """'Sep 19-20, 2026' for a multi-day event; single date otherwise."""
    if not start:
        return human_date(end)
    if not end or end == start:
        return human_date(start)
    if start.year == end.year and start.month == end.month:
        return f"{start:%b %d}-{end:%d}, {start:%Y}"
    if start.year == end.year:
        return f"{start:%b %d} - {end:%b %d}, {start:%Y}"
    return f"{human_date(start)} - {human_date(end)}"


def iso_date(d: date | None) -> str:
    return d.isoformat() if d else ""


def depth_of(url: str) -> int:
    """'' -> 0, 'writeups/' -> 1, 'writeups/htb-lame/' -> 2"""
    return len([p for p in url.split("/") if p])


def resolve_machine_image(value, doc_name: str = "") -> str:
    """
    Turn a frontmatter `image:` value into a filename in static/machines/.

    `image: lame`      -> finds lame.png / lame.svg / ... (any known extension)
    `image: lame.png`  -> used as-is if that file exists
    Returns "" when nothing is set, or warns when a name was given but missing.
    """
    if not value:
        return ""
    name = str(value).strip()
    if not name:
        return ""

    given = Path(name)
    # Exact filename (with extension) that exists - use it directly.
    if given.suffix and (MACHINE_IMG_DIR / name).is_file():
        return name

    # Otherwise match <stem>.<known-ext>, case-insensitively.
    stem = given.stem if given.suffix else name
    if MACHINE_IMG_DIR.is_dir():
        for f in sorted(MACHINE_IMG_DIR.iterdir()):
            if (f.is_file() and f.suffix.lower() in MACHINE_IMG_EXTS
                    and f.stem.lower() == stem.lower()):
                return f.name

    where = f" (in {doc_name})" if doc_name else ""
    print(f"  ! image '{value}' not found in static/machines/{where}")
    return ""


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

def make_markdown(baselevel: int = 1) -> markdown.Markdown:
    return markdown.Markdown(
        extensions=[
            "extra",          # tables, fenced code, attr_list, footnotes, def lists
            "sane_lists",
            "admonition",
            "meta",
            CodeHiliteExtension(guess_lang=False, linenums=False,
                                css_class="codehilite"),
            TocExtension(permalink="#", toc_depth="2-4", anchorlink=False,
                         baselevel=baselevel),
        ],
    )


_FENCE = re.compile(r"^\s*(```|~~~)")
_SHIFTED_MD: markdown.Markdown | None = None


def uses_h1(body: str) -> bool:
    """True if the Markdown has a top-level `# Heading` outside code fences."""
    fence = None
    for line in body.splitlines():
        m = _FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            continue
        if fence is None and re.match(r"#\s+\S", line):
            return True
    return False


# Obsidian-style callouts (`> [!note] Title`) -> Python-Markdown admonitions.
_CALLOUT = re.compile(r"^>\s*\[!(\w+)\][+-]?\s*(.*)$")
CALLOUT_KINDS = {
    "note": "note", "info": "note", "abstract": "note", "summary": "note",
    "example": "note", "quote": "note", "question": "note",
    "tip": "tip", "hint": "tip", "success": "tip", "important": "tip",
    "warning": "warning", "caution": "warning", "attention": "warning",
    "danger": "danger", "error": "danger", "failure": "danger", "bug": "danger",
}


def convert_callouts(body: str) -> str:
    out: list[str] = []
    lines = body.splitlines()
    fence = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
        elif fence is None and (c := _CALLOUT.match(line)):
            kind = CALLOUT_KINDS.get(c.group(1).lower(), "note")
            title = (c.group(2).strip() or c.group(1).capitalize()).replace('"', "'")
            out += ["", f'!!! {kind} "{title}"']
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                out.append("    " + re.sub(r"^>\s?", "", lines[i]))
                i += 1
            out.append("")
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def render_markdown(md: markdown.Markdown, body: str) -> tuple[str, str]:
    # The page title is the only <h1>. Posts written with `# Section` headings
    # are rendered one level down (# -> h2, ## -> h3, ...) so the outline and
    # the "On this page" box keep their top-level sections.
    global _SHIFTED_MD
    if uses_h1(body):
        if _SHIFTED_MD is None:
            _SHIFTED_MD = make_markdown(baselevel=2)
        md = _SHIFTED_MD
    md.reset()
    rendered = md.convert(convert_callouts(body))
    # Screenshots load lazily so long writeups stay fast.
    rendered = re.sub(r"<img (?![^>]*\bloading=)", '<img loading="lazy" decoding="async" ',
                      rendered)
    toc = getattr(md, "toc", "") or ""
    return rendered, toc


# --------------------------------------------------------------------------
# Loading content
# --------------------------------------------------------------------------

def load_documents(md: markdown.Markdown, include_drafts: bool) -> list[dict]:
    docs: list[dict] = []
    for col in COLLECTIONS:
        folder = CONTENT / col["dir"]
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            doc = load_document(path, col, md)
            if doc["draft"] and not include_drafts:
                print(f"  skip (draft): {path.name}")
                continue
            docs.append(doc)
    docs.sort(key=lambda d: (d["date"] or date.min, d["title"]), reverse=True)
    return docs


def load_document(path: Path, col: dict, md: markdown.Markdown) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)

    title = meta.get("title") or path.stem.replace("-", " ").title()
    slug = slugify(meta.get("slug") or path.stem)

    tags, tag_facts = split_tags(meta.get("tags"))

    body_html, toc = render_markdown(md, body)
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_html)).strip()
    words = len(re.findall(r"\w+", plain))
    image = resolve_machine_image(meta.get("image"), path.name)

    return {
        "path": path,
        "collection": col["key"],
        "collection_title": col["title"],
        "collection_singular": col["singular"],
        "title": str(title),
        "slug": slug,
        "url": f"{col['dir']}/{slug}/",
        "date": parse_date(meta.get("date")),
        "updated": parse_date(meta.get("updated")),
        "tags": tags,
        "description": str(meta.get("description") or meta.get("summary") or ""),
        "draft": bool(meta.get("draft", False)),
        "featured": bool(meta.get("featured", False)),
        "platform": str(meta.get("platform") or tag_facts.get("platform", "")),
        "difficulty": str(meta.get("difficulty") or tag_facts.get("difficulty", "")),
        "os": str(meta.get("os") or ""),
        "status": str(meta.get("status") or tag_facts.get("status", "")),
        # Writeups are HackTheBox machines or Sherlocks (DFIR); used as a filter.
        "kind": "Sherlock" if any(t["slug"] == "sherlock" for t in tags) else "Machine",
        "headings": heading_texts(body_html),
        "points": meta.get("points") or "",
        "path_steps": [str(x) for x in (meta.get("path") or []) if str(x).strip()],
        "image": image,
        "logo_path": f"static/machines/{image}" if image else "",
        "html": body_html,
        "toc": toc,
        "text": plain[:1200],
        "og_image": f"og/{col['key']}-{slug}.png",
        "words": words,
        "reading_time": max(1, round(words / 200)),
    }


def build_tag_index(docs: list[dict]) -> dict[str, dict]:
    tags: dict[str, dict] = {}
    for doc in docs:
        for tag in doc["tags"]:
            entry = tags.setdefault(tag["slug"], {
                "slug": tag["slug"], "name": tag["name"], "docs": []
            })
            entry["docs"].append(doc)
    for entry in tags.values():
        entry["count"] = len(entry["docs"])
        entry["url"] = f"tags/{entry['slug']}/"
    return dict(sorted(tags.items(), key=lambda kv: kv[0]))


# --------------------------------------------------------------------------
# CTF walkthroughs
# --------------------------------------------------------------------------

def tag_dicts(raw) -> list[dict]:
    """Normalise a tags value (list or comma string) into {slug, name} dicts."""
    return split_tags(raw)[0]


def heading_texts(body_html: str) -> list[str]:
    """Section headings of a rendered post, for the search index."""
    out = []
    for h in re.findall(r"<h[2-4][^>]*>(.*?)</h[2-4]>", body_html, re.S):
        text = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r'<a class="headerlink".*?</a>', "", h)))
        if text.strip():
            out.append(text.strip())
    return out


def natural_key(value: str):
    """Sort 'Intro to Web 2' before 'Intro to Web 10'."""
    return [int(p) if p.isdigit() else p.lower()
            for p in re.split(r"(\d+)", str(value))]


def resolve_ctf_logo(value, slug: str) -> str:
    """Find a CTF logo in static/ctf/ by explicit name or by event slug."""
    for name in [str(value or "").strip(), slug]:
        if not name:
            continue
        given = Path(name)
        if given.suffix and (CTF_IMG_DIR / name).is_file():
            return name
        stem = given.stem if given.suffix else name
        if CTF_IMG_DIR.is_dir():
            for f in sorted(CTF_IMG_DIR.iterdir()):
                if (f.is_file() and f.suffix.lower() in MACHINE_IMG_EXTS
                        and f.stem.lower() == stem.lower()):
                    return f.name
    return ""


def load_ctf_challenge(path: Path, category: str, event: dict,
                       md: markdown.Markdown) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)

    title = str(meta.get("title") or path.stem)
    slug = slugify(meta.get("slug") or path.stem)

    # Categories: `categories: [a, b]` (list/comma string) or single `category`,
    # falling back to the folder name. First one is the primary (used for grouping).
    raw_cats = meta.get("categories")
    if raw_cats is None:
        raw_cats = [meta.get("category") or category or "Misc"]
    elif isinstance(raw_cats, str):
        raw_cats = [c.strip() for c in raw_cats.split(",") if c.strip()]
    categories, seen = [], set()
    for c in raw_cats:
        cc = canon_category(c)
        if cc and cc.lower() not in seen:
            seen.add(cc.lower())
            categories.append(cc)
    if not categories:
        categories = [canon_category(category or "Misc")]
    primary = categories[0]

    # Authors: `authors: [a, b]` or single `author`.
    raw_auth = meta.get("authors")
    if raw_auth is None:
        a = meta.get("author")
        raw_auth = [a] if a else []
    elif isinstance(raw_auth, str):
        raw_auth = [x.strip() for x in raw_auth.split(",") if x.strip()]
    authors = [str(a).strip() for a in raw_auth if str(a).strip()]

    body_html, toc = render_markdown(md, body)
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body_html)).strip()
    words = len(re.findall(r"\w+", plain))

    # A challenge is "solved" (gets its own page + link) when it has a body,
    # unless explicitly marked otherwise. Unsolved stubs render greyed-out.
    solved = bool(body.strip())
    if meta.get("solved") is False or str(meta.get("status", "")).lower() == "unsolved":
        solved = False
    if meta.get("draft"):
        solved = False

    desc = str(meta.get("description") or "")
    if not desc and plain:
        ex = plain
        if ex.lower().startswith("description "):
            ex = ex[len("description "):]
        desc = (ex[:157].rsplit(" ", 1)[0] + "…") if len(ex) > 160 else ex

    ev_slug = event["slug"]
    return {
        "collection": "ctf",
        "collection_title": "CTF Walkthroughs",
        "collection_singular": "Challenge",
        "title": title,
        "slug": slug,
        "url": f"ctf/{ev_slug}/{slug}/",
        "date": event["date"],
        "updated": parse_date(meta.get("updated")),
        "tags": tag_dicts(categories + (meta.get("tags") or [])),
        "description": desc,
        "category": primary,
        "categories": categories,
        "authors": authors,
        "points": meta.get("points") or "",
        "difficulty": str(meta.get("difficulty") or ""),
        "solved": solved,
        "event_slug": ev_slug,
        "event_title": event["title"],
        "event_url": event["url"],
        "headings": heading_texts(body_html),
        "html": body_html,
        "toc": toc,
        "text": plain[:1200],
        "image": "",
        "platform": "",
        "os": "",
        "logo_path": f"static/ctf/{event['logo']}" if event["logo"] else "",
        "og_image": f"og/ctf-{ev_slug}-{slug}.png",
        "words": words,
        "reading_time": max(1, round(words / 200)),
        "featured": False,
        "draft": False,
    }


def load_ctf(md: markdown.Markdown) -> tuple[list[dict], list[dict]]:
    """Load CTF events and their challenges. Returns (events, solved_docs)."""
    events: list[dict] = []
    if not CTF_DIR.is_dir():
        return [], []

    for event_dir in sorted(CTF_DIR.iterdir()):
        if not event_dir.is_dir():
            continue
        meta, body = {}, ""
        event_md = event_dir / "event.md"
        if event_md.is_file():
            meta, body = parse_frontmatter(event_md.read_text(encoding="utf-8"))

        ev_slug = slugify(meta.get("slug") or event_dir.name)
        intro_html = render_markdown(md, body)[0] if body.strip() else ""
        event = {
            "slug": ev_slug,
            "title": str(meta.get("title") or event_dir.name),
            "date": parse_date(meta.get("date")),
            "date_end": parse_date(meta.get("date_end")),
            "logo": resolve_ctf_logo(meta.get("logo"), ev_slug),
            "description": str(meta.get("description") or ""),
            "tags": tag_dicts(meta.get("tags")),
            "place": str(meta.get("place") or ""),
            "team": str(meta.get("team") or ""),
            "url_ext": str(meta.get("url") or ""),
            "intro_html": intro_html,
            "url": f"ctf/{ev_slug}/",
            "challenges": [],
        }

        chals: list[dict] = []
        for sub in sorted(event_dir.iterdir()):
            if sub.is_dir():
                for p in sorted(sub.glob("*.md")):
                    chals.append(load_ctf_challenge(p, sub.name, event, md))
        for p in sorted(event_dir.glob("*.md")):
            if p.name.lower() != "event.md":
                chals.append(load_ctf_challenge(p, "", event, md))

        chals.sort(key=lambda c: (CATEGORY_ORDER.get(c["category"].lower(), 90),
                                  c["category"].lower(),
                                  DIFFICULTY_ORDER.get(c["difficulty"].lower(), 50),
                                  natural_key(c["title"])))
        event["challenges"] = chals
        events.append(event)

    events.sort(key=lambda ev: (ev["date"] or date.min, ev["title"]), reverse=True)
    solved_docs = [c for ev in events for c in ev["challenges"] if c["solved"]]
    return events, solved_docs


# --------------------------------------------------------------------------
# HTML components
# --------------------------------------------------------------------------

def tag_pills(tags: list[dict], root: str, limit: int | None = None) -> str:
    if not tags:
        return ""
    shown = tags[:limit] if limit else tags
    out = "".join(
        f'<a class="pill" href="{root}tags/{t["slug"]}/">{e(t["name"])}</a>'
        for t in shown
    )
    extra = len(tags) - len(shown)
    if extra > 0:
        out += f'<span class="pill pill-muted">+{extra}</span>'
    return f'<div class="pills">{out}</div>'


def difficulty_badge(value: str) -> str:
    if not value:
        return ""
    return (f'<span class="badge badge-{slugify(value)}">{e(value)}</span>')


def doc_card(doc: dict, root: str) -> str:
    """A single entry in a listing page."""
    meta_bits = []
    if doc["date"]:
        meta_bits.append(
            f'<time datetime="{iso_date(doc["date"])}">{human_date(doc["date"])}</time>'
        )
    if doc["collection"] == "writeups":
        if doc["platform"]:
            meta_bits.append(e(doc["platform"]))
        if doc["os"]:
            meta_bits.append(e(doc["os"]))
    meta_bits.append(f'{doc["reading_time"]} min read')
    meta = '<span class="dot">·</span>'.join(meta_bits)

    desc = f'<p class="card-desc">{e(doc["description"])}</p>' if doc["description"] else ""

    logo = ""
    if doc["image"]:
        logo = (f'<img class="card-logo" src="{root}static/machines/{e(doc["image"])}" '
                f'alt="" width="30" height="30" loading="lazy">')

    return f"""<article class="card">
  <div class="card-head">
    <div class="card-head-main">
      {logo}
      <h3 class="card-title"><a href="{root}{doc['url']}">{e(doc['title'])}</a></h3>
    </div>
    {difficulty_badge(doc['difficulty'])}
  </div>
  <div class="card-meta">{meta}</div>
  {desc}
  {tag_pills(doc['tags'], root, limit=6)}
</article>"""


FACET_TAGS = {"windows", "linux", "sherlock"}


def writeup_label(doc: dict) -> str:
    """'HackTheBox machine' / 'HackTheBox Sherlock' - shown with the title."""
    kind = "Sherlock" if doc.get("kind") == "Sherlock" else "machine"
    return f'{doc["platform"]} {kind}'.strip() if doc["platform"] else kind.capitalize()


def writeup_seo_title(doc: dict) -> str:
    """Page <title> keeps the words people search for: 'HTB Support writeup'."""
    short = {"HackTheBox": "HTB", "TryHackMe": "THM"}.get(doc["platform"], doc["platform"])
    kind = " Sherlock" if doc.get("kind") == "Sherlock" else ""
    return f"{short}{kind} {doc['title']} writeup".strip()


def writeup_card(doc: dict, root: str) -> str:
    """A mid-size writeup entry: logo, title, key facts, two-line summary."""
    if doc["image"]:
        logo = (f'<img class="wcard-logo" src="{root}static/machines/{e(doc["image"])}" '
                f'alt="" width="44" height="44" loading="lazy">')
    else:
        logo = '<span class="wcard-logo" aria-hidden="true"></span>'
    facts = [x for x in ("Sherlock" if doc.get("kind") == "Sherlock" else "", doc["os"]) if x]
    meta = '<span class="dot">·</span>'.join(
        [e(x) for x in facts]
        + [f'<time datetime="{iso_date(doc["date"])}">{human_date(doc["date"])}</time>'])
    desc = f'<p class="wcard-desc">{e(doc["description"])}</p>' if doc["description"] else ""
    topics = [t for t in doc["tags"] if t["slug"] not in FACET_TAGS]
    return f"""<article class="wcard">
  <div class="wcard-head">
    {logo}
    <div class="wcard-titles">
      <h3 class="wcard-title"><a href="{root}{doc['url']}">{e(doc['title'])}</a></h3>
      <div class="wcard-meta">{meta}</div>
    </div>
    {difficulty_badge(doc['difficulty'])}
  </div>
  {desc}
  {tag_pills(topics, root, limit=3)}
</article>"""


def doc_row(doc: dict, root: str, show_kind: bool = True, tags: int = 3) -> str:
    """A compact one-line entry, used on the home page and tag pages."""
    kind = (f'<span class="row-kind">{e(doc["collection_singular"])}</span>'
            if show_kind else "")
    return f"""<li class="row">
  <time class="row-date" datetime="{iso_date(doc['date'])}">{human_date(doc['date']) or '-'}</time>
  <div class="row-body">
    <a class="row-title" href="{root}{doc['url']}">{e(doc['title'])}</a>
    {kind}
    {tag_pills(doc['tags'], root, limit=tags) if tags else ""}
  </div>
</li>"""


def section_header(title: str, blurb: str = "", count: str = "") -> str:
    count_html = f'<span class="count">{e(count)}</span>' if count else ""
    blurb_html = f'<p class="lede">{e(blurb)}</p>' if blurb else ""
    return f"""<header class="page-head">
  <h1 class="page-title">{e(title)}{count_html}</h1>
  {blurb_html}
</header>"""


def toc_block(toc: str) -> str:
    """'On this page': a sticky sidebar on wide screens, collapsed on phones."""
    if not toc or toc.count("<li") < 3:
        return ""
    return ('<aside class="toc" aria-label="On this page">'
            '<details class="toc-details" open><summary class="toc-title">On this page</summary>'
            f'{toc}</details></aside>'
            # Collapse before first paint on narrow screens (no layout jump).
            '<script>(function(a){if(!matchMedia("(min-width: 1100px)").matches)'
            'a.querySelector("details").removeAttribute("open")})'
            '(document.currentScript.previousElementSibling)</script>')


def attack_path_html(steps: list[str]) -> str:
    """Frontmatter `path:` list, rendered as a numbered chain above the post."""
    if not steps:
        return ""
    items = "".join(
        "<li>" + re.sub(r"`([^`]+)`", r"<code>\1</code>", e(s)) + "</li>" for s in steps)
    return ('<section class="attack-path" aria-label="Attack path">'
            f'<p class="attack-path-title">Attack path</p><ol class="chain">{items}</ol></section>')


def doc_tags_html(tags: list[dict], root: str) -> str:
    if not tags:
        return ""
    return (f'<footer class="doc-tags"><span class="doc-tags-label">Tags</span>'
            f'{tag_pills(tags, root)}</footer>')


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

class Site:
    def __init__(self, config: dict, docs: list[dict], tags: dict,
                 ctf_events: list[dict] | None = None):
        self.config = config
        self.docs = docs
        self.tags = tags
        self.ctf_events = ctf_events or []
        self.base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
        self.pages_written = 0
        self.base_url = config.get("url", "").rstrip("/")

        # Twitter/X site meta, derived from the configured profile URL.
        handle = ""
        tw = (config.get("social") or {}).get("twitter", "")
        if tw:
            handle = "@" + tw.rstrip("/").rsplit("/", 1)[-1].lstrip("@")
        self.twitter_meta = (
            f'<meta name="twitter:site" content="{e(handle)}">'
            f'<meta name="twitter:creator" content="{e(handle)}">' if handle else ""
        )

    def canonical_for(self, url: str) -> str:
        return f"{self.base_url}/{url}" if url else f"{self.base_url}/"

    def og_url_for(self, rel: str) -> str:
        # Version the OG image URL so social scrapers (LinkedIn especially) that
        # cache images by URL are forced to refetch when the card changes,
        # instead of showing a stale copy of /og/<name>.png.
        sep = "&" if "?" in rel else "?"
        return f"{self.base_url}/{rel}{sep}v={BUILD_VERSION}"

    def person_ld(self) -> dict:
        cfg = self.config
        same = [u for u in (cfg.get("social") or {}).values() if u]
        person = {
            "@type": "Person",
            "name": cfg["site_name"],
            "url": self.base_url + "/",
            "jobTitle": "Cybersecurity student / penetration testing",
        }
        if same:
            person["sameAs"] = same
        if cfg.get("email"):
            person["email"] = f"mailto:{cfg['email']}"
        return person

    def jsonld(self, obj: dict) -> str:
        return ('<script type="application/ld+json">'
                + json.dumps(obj, ensure_ascii=False) + "</script>")

    # -- rendering shell ---------------------------------------------------

    def nav_html(self, root: str, current: str) -> str:
        items = []
        for item in self.config["nav"]:
            active = " active" if item["url"].strip("/") == current.strip("/") else ""
            items.append(
                f'<a class="nav-link{active}" href="{root}{item["url"]}">{e(item["label"])}</a>'
            )
        return "".join(items)

    def social_html(self, root: str) -> str:
        labels = {
            "github": "GitHub",
            "linkedin": "LinkedIn",
            "hackthebox": "HackTheBox",
            "tryhackme": "TryHackMe",
            "twitter": "X",
        }
        links = []
        for key, label in labels.items():
            url = (self.config.get("social") or {}).get(key)
            if url:
                links.append(
                    f'<a class="social-link" href="{e(url)}" rel="me noopener" '
                    f'target="_blank">{label}</a>'
                )
        if self.config.get("email"):
            links.append(
                f'<a class="social-link" href="mailto:{e(self.config["email"])}">Email</a>'
            )
        return "".join(links)

    def write(self, url: str, title: str, content: str, *, description: str = "",
              current: str = "", body_class: str = "", og_image: str = "og/default.png",
              og_type: str = "website", head_extra: str = "",
              canonical: str | None = None) -> None:
        """Render base.html around `content` and write it to dist/<url>index.html."""
        root = "../" * depth_of(url)
        full_title = title if url == "" else f"{title} · {self.config['site_name']}"
        page = (self.base
                .replace("{{root}}", root)
                .replace("{{version}}", BUILD_VERSION)
                .replace("{{home}}", root or "./")
                .replace("{{lang}}", "en")
                .replace("{{title}}", e(full_title))
                .replace("{{description}}", e(description or self.config["description"]))
                .replace("{{site_name}}", e(self.config["site_name"]))
                .replace("{{site_short}}", e(self.config["site_short"]))
                .replace("{{canonical}}", e(canonical or self.canonical_for(url)))
                .replace("{{og_type}}", e(og_type))
                .replace("{{og_image}}", e(self.og_url_for(og_image)))
                .replace("{{twitter_handle}}", self.twitter_meta)
                .replace("{{head_extra}}", head_extra)
                .replace("{{nav}}", self.nav_html(root, current))
                .replace("{{social}}", self.social_html(root))
                .replace("{{footer_note}}", e(self.config.get("footer_note", "")))
                .replace("{{year}}", str(date.today().year))
                .replace("{{body_class}}", body_class)
                .replace("{{content}}", content))

        out = DIST / url / "index.html" if url else DIST / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        self.pages_written += 1

    # -- individual pages --------------------------------------------------

    def build_home(self) -> None:
        cfg = self.config
        root = ""
        writeups = [d for d in self.docs if d["collection"] == "writeups"]
        posts = [d for d in self.docs if d["collection"] in ("blog", "cheatsheets")]

        # Hand-picked writeups (frontmatter `featured: true`) lead; the newest
        # fill any remaining slots.
        n_writeups = cfg.get("home_writeup_count", 5)
        picked = [d for d in writeups if d["featured"]][:n_writeups]
        picked += [d for d in writeups if d not in picked][:n_writeups - len(picked)]

        top_tags = sorted(self.tags.values(), key=lambda t: (-t["count"], t["slug"]))[:14]
        tag_cloud = "".join(
            f'<a class="pill" href="tags/{t["slug"]}/">{e(t["name"])}'
            f'<span class="pill-count">{t["count"]}</span></a>'
            for t in top_tags
        )

        # Proof strip: achievements from config.json, not page counts.
        def proof_item(p: dict) -> str:
            tag = "a" if p.get("url") else "div"
            href = f' href="{e(p["url"])}"' if p.get("url") else ""
            ext = ' rel="noopener" target="_blank"' if str(p.get("url", "")).startswith("http") else ""
            detail = f'<span class="proof-detail">{e(p["detail"])}</span>' if p.get("detail") else ""
            return (f'<{tag} class="proof-item"{href}{ext}>'
                    f'<span class="proof-value">{e(p["value"])}</span>'
                    f'<span class="proof-label">{e(p["label"])}</span>{detail}</{tag}>')
        proof = cfg.get("proof") or []
        proof_html = (f'<div class="proof" aria-label="Highlights">'
                      f'{"".join(proof_item(p) for p in proof)}</div>' if proof else "")

        def block(heading, body, more_url, more_label, anchor=""):
            if not body:
                return ""
            more = (f'<a class="block-more" href="{more_url}">{e(more_label)} '
                    f'<span aria-hidden="true">&rarr;</span></a>' if more_url else "")
            anchor_attr = f' id="{anchor}"' if anchor else ""
            return f"""<section class="home-block"{anchor_attr}>
  <div class="block-head">
    <h2 class="block-title">{e(heading)}</h2>
    {more}
  </div>
  {body}
</section>"""

        def rows(items, show_kind=True):
            if not items:
                return ""
            return f'<ul class="rows">{"".join(doc_row(d, root, show_kind, tags=0) for d in items)}</ul>'

        projects = cfg.get("projects") or []
        projects_html = ""
        if projects:
            cards = "".join(
                f"""<article class="card project-card">
  <h3 class="card-title"><a href="{e(p['url'])}" rel="noopener" target="_blank">{e(p['name'])}</a></h3>
  <p class="card-desc">{e(p['summary'])}</p>
  <div class="project-stack">{"".join(f'<span>{e(t)}</span>' for t in p.get("stack", []))}</div>
</article>""" for p in projects)
            projects_html = f'<div class="cards cards-3">{cards}</div>'
        github = (cfg.get("social") or {}).get("github", "")

        # CTF events (not individual intro challenges) represent the CTF work.
        ctf_rows = ""
        if self.ctf_events:
            items = []
            for ev in self.ctf_events[:cfg.get("home_ctf_count", 3)]:
                total = len(ev["challenges"])
                solved = sum(1 for c in ev["challenges"] if c["solved"])
                items.append(f"""<li class="row">
  <time class="row-date" datetime="{iso_date(ev['date'])}">{human_date(ev['date']) or '-'}</time>
  <div class="row-body">
    <a class="row-title" href="{root}{ev['url']}">{e(ev['title'])}</a>
    <span class="row-kind">{solved} / {total} solved</span>
  </div>
</li>""")
            ctf_rows = f'<ul class="rows">{"".join(items)}</ul>'

        social = cfg.get("social") or {}
        links = [(label, social.get(key)) for key, label in
                 (("linkedin", "LinkedIn"), ("github", "GitHub"), ("hackthebox", "HackTheBox"))]
        if cfg.get("email"):
            links.append(("Email", f'mailto:{cfg["email"]}'))
        links_html = "".join(
            f'<a href="{e(url)}"' + ('' if url.startswith("mailto:") else ' rel="me noopener" target="_blank"')
            + f'>{label}</a>'
            for label, url in links if url
        )

        badge = (f'<p class="hero-badge">{e(cfg["availability"])}</p>'
                 if cfg.get("availability") else "")
        contact = (f'<a class="btn" href="mailto:{e(cfg["email"])}">Get in touch</a>'
                   if cfg.get("email") else "")
        content = f"""<section class="hero hero-split">
  <div class="hero-main">
    {badge}
    <p class="hero-kicker">{e(cfg['tagline'])}</p>
    <h1 class="hero-title">{e(cfg['hero_intro'])}</h1>
    <p class="hero-blurb">{e(cfg['hero_blurb'])}</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="resume/">View resume</a>
      <a class="btn" href="writeups/">Read the writeups</a>
      {contact}
    </div>
    <nav class="hero-links" aria-label="Profiles">{links_html}</nav>
  </div>
  {proof_html}
</section>

{block("Projects", projects_html, github, "GitHub", anchor="projects")}
{block("Featured writeups", f'<div class="wcards">{"".join(writeup_card(d, root) for d in picked)}</div>' if picked else "", "writeups/", "All writeups")}
{block("CTF walkthroughs", ctf_rows, "ctf/", "All CTFs")}
{block("Recent writing", rows(posts[:cfg.get('home_post_count', 4)]), "blog/", "All posts")}
{block("Browse by tag", f'<div class="pills pills-lg">{tag_cloud}</div>', "tags/", "All tags")}"""
        website_ld = self.jsonld({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": cfg["site_name"],
            "url": self.base_url + "/",
            "description": cfg["description"],
            "author": self.person_ld(),
            "potentialAction": {
                "@type": "SearchAction",
                "target": self.base_url + "/?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        })
        person_ld = self.jsonld({"@context": "https://schema.org", **self.person_ld()})
        self.write("", cfg["site_name"], content, description=cfg["description"],
                   current="", body_class="page-home",
                   head_extra=website_ld + person_ld)

    # Filters built from frontmatter fields (writeups only), in display order.
    FACETS = [("kind", "Type"), ("os", "OS"), ("difficulty", "Difficulty"),
              ("status", "Status")]
    TOP_TAG_CHIPS = 12

    def build_collection(self, col: dict) -> None:
        docs = [d for d in self.docs if d["collection"] == col["key"]]
        root = "../"
        is_writeups = col["key"] == "writeups"

        def chip(attr: str, value: str, label: str, n: int) -> str:
            return (f'<button class="chip" {attr}="{e(value)}" type="button">'
                    f'{e(label)}<span class="pill-count">{n}</span></button>')

        # Field filters: one row per field that actually varies.
        facet_rows = ""
        if is_writeups:
            for key, label in self.FACETS:
                counts: dict[str, list] = {}
                for d in docs:
                    if d[key]:
                        counts.setdefault(slugify(d[key]), [d[key], 0])[1] += 1
                if len(counts) < 2:
                    continue
                order = sorted(counts.items(), key=lambda kv: (
                    DIFFICULTY_ORDER.get(kv[1][0].lower(), 50) if key == "difficulty" else 0,
                    -kv[1][1], kv[0]))
                chips = "".join(
                    f'<button class="chip" data-facet="{key}" data-value="{e(v)}" type="button">'
                    f'{e(name)}<span class="pill-count">{n}</span></button>'
                    for v, (name, n) in order)
                facet_rows += (f'<div class="facet"><span class="facet-label">{e(label)}</span>'
                               f'<div class="chips">{chips}</div></div>')

        # Topic tags: the most used up front, the long tail folded away.
        # (Topics that duplicate a field filter, like "windows", are left out.)
        facet_values = ({slugify(d[k]) for d in docs for k, _ in self.FACETS if d[k]}
                        if is_writeups else set())
        used: dict[str, int] = {}
        for d in docs:
            for t in d["tags"]:
                if t["slug"] not in facet_values:
                    used[t["slug"]] = used.get(t["slug"], 0) + 1
        ranked = sorted(used.items(), key=lambda kv: (-kv[1], kv[0]))
        top = "".join(chip("data-tag", slug, slug, n) for slug, n in ranked[:self.TOP_TAG_CHIPS])
        rest = ranked[self.TOP_TAG_CHIPS:]
        more = ""
        if rest:
            more = (f'<details class="more-chips"><summary>All {len(ranked)} topics</summary>'
                    f'<div class="chips">{"".join(chip("data-tag", s_, s_, n) for s_, n in rest)}'
                    '</div></details>')
        topic_row = (f'<div class="facet"><span class="facet-label">Topic</span>'
                     f'<div class="facet-body"><div class="chips">{top}</div>{more}</div></div>'
                     if ranked else "")

        filter_bar = f"""<div class="filter-bar" data-filter-target="#doc-list" data-sync-url>
  <div class="filter-row">
    <input class="filter-input" type="search" placeholder="Filter {col['title'].lower()}…"
           aria-label="Filter {e(col['title'])}" autocomplete="off">
    <button class="chip chip-reset" type="button" data-reset>Clear</button>
  </div>
  <details class="facets-wrap" open>
    <summary>Filters</summary>
    <div class="facets">{facet_rows}{topic_row}</div>
  </details>
  <script>(function(d){{if(!matchMedia("(min-width: 761px)").matches&&!location.search)d.removeAttribute("open")}})(document.currentScript.previousElementSibling)</script>
</div>""" if docs else ""

        def attrs(d: dict) -> str:
            text = f'{d["title"]} {d["description"]}'.lower()
            out = (f'data-title="{e(text)}" '
                   f'data-tags="{e(" ".join(t["slug"] for t in d["tags"]))}"')
            if is_writeups:
                out += "".join(f' data-f-{key}="{e(slugify(d[key]))}"'
                               for key, _ in self.FACETS if d[key])
            return out

        if docs:
            if is_writeups:
                items = "".join(f'<div class="card-wrap" {attrs(d)}>{writeup_card(d, root)}</div>'
                                for d in docs)
                listing = f'<div class="wcards" id="doc-list">{items}</div>'
            else:
                items = "".join(f'<div class="card-wrap" {attrs(d)}>{doc_card(d, root)}</div>'
                                for d in docs)
                listing = f'<div class="cards" id="doc-list">{items}</div>'
            empty = '<p class="empty" data-empty hidden>No matches. Try a different filter.</p>'
        else:
            listing = ('<p class="empty">Nothing here yet - drop a Markdown file in '
                       f'<code>content/{col["dir"]}/</code> and rebuild.</p>')
            empty = ""

        content = (section_header(col["title"], col["blurb"], f"{len(docs)}")
                   + filter_bar + listing + empty)
        self.write(f"{col['dir']}/", col["title"], content,
                   description=col["blurb"], current=col["dir"])

    def build_tag_redirects(self) -> None:
        """Keep old /tags/<slug>/ URLs working for tags that were folded into
        fields (easy, active, hackthebox...) or renamed by an alias."""
        for slug, target in sorted(RETIRED_TAGS.items()):
            if slug in self.tags:
                continue
            url = f"tags/{slug}/"
            rel = "../" * depth_of(url) + target
            page = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
                    f'<title>Moved</title><meta name="robots" content="noindex">'
                    f'<link rel="canonical" href="{e(self.canonical_for(target))}">'
                    f'<meta http-equiv="refresh" content="0; url={e(rel)}"></head>'
                    f'<body><p>Moved to <a href="{e(rel)}">{e(target)}</a>.</p></body></html>')
            out = DIST / url / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(page, encoding="utf-8")

    def build_doc(self, doc: dict, index: int) -> None:
        root = "../" * depth_of(doc["url"])
        col = COLLECTION_BY_KEY[doc["collection"]]

        meta_bits = []
        if doc["date"]:
            meta_bits.append(
                f'<time datetime="{iso_date(doc["date"])}">{human_date(doc["date"])}</time>'
            )
        if doc["updated"]:
            meta_bits.append(f'updated {human_date(doc["updated"])}')
        meta_bits.append(f'{doc["reading_time"]} min read')
        meta_html = '<span class="dot">·</span>'.join(meta_bits)

        # Writeup-specific fact table.
        facts = []
        for label, value in (("Platform", doc["platform"]), ("OS", doc["os"]),
                             ("Difficulty", doc["difficulty"]), ("Points", doc["points"])):
            if value:
                facts.append(f'<div class="fact"><dt>{label}</dt><dd>{e(value)}</dd></div>')
        facts_html = f'<dl class="facts">{"".join(facts)}</dl>' if facts else ""

        toc_html = toc_block(doc["toc"])

        # Related = most tag overlap, same-or-any collection.
        related = []
        if doc["tags"]:
            mine = {t["slug"] for t in doc["tags"]}
            scored = []
            for other in self.docs:
                if other["url"] == doc["url"]:
                    continue
                shared = len(mine & {t["slug"] for t in other["tags"]})
                if shared:
                    scored.append((shared, other["date"] or date.min, other))
            scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
            related = [s[2] for s in scored[:4]]
        related_html = ""
        if related:
            related_html = (
                '<section class="related"><h2 class="block-title">Related</h2>'
                f'<ul class="rows">{"".join(doc_row(r, root) for r in related)}</ul></section>'
            )

        # Previous / next within the same collection.
        siblings = [d for d in self.docs if d["collection"] == doc["collection"]]
        pos = siblings.index(doc)
        newer = siblings[pos - 1] if pos > 0 else None
        older = siblings[pos + 1] if pos + 1 < len(siblings) else None
        nav_parts = []
        if newer:
            nav_parts.append(f'<a class="pagenav-item" href="{root}{newer["url"]}">'
                             f'<span class="pagenav-label">← Newer</span>'
                             f'<span class="pagenav-title">{e(newer["title"])}</span></a>')
        else:
            nav_parts.append('<span class="pagenav-item pagenav-empty"></span>')
        if older:
            nav_parts.append(f'<a class="pagenav-item pagenav-next" href="{root}{older["url"]}">'
                             f'<span class="pagenav-label">Older →</span>'
                             f'<span class="pagenav-title">{e(older["title"])}</span></a>')
        pagenav = f'<nav class="pagenav">{"".join(nav_parts)}</nav>'

        desc = f'<p class="lede">{e(doc["description"])}</p>' if doc["description"] else ""
        is_writeup = doc["collection"] == "writeups"
        kicker = (f'<p class="doc-kicker">{e(writeup_label(doc))}</p>' if is_writeup else "")
        page_title = writeup_seo_title(doc) if is_writeup else doc["title"]

        logo_html = ""
        if doc["image"]:
            logo_html = (
                f'<img class="machine-logo" src="{root}static/machines/{e(doc["image"])}" '
                f'alt="{e(doc["title"])} logo" width="96" height="96" loading="lazy">'
            )

        content = f"""<article class="doc{' has-toc' if toc_html else ''}">
  <nav class="crumbs"><a href="{root}{col['dir']}/">{e(col['title'])}</a>
    <span aria-hidden="true">/</span> <span>{e(doc['title'])}</span></nav>
  <header class="doc-head">
    <div class="doc-head-top">
      {logo_html}
      <div class="doc-head-titles">
        {kicker}<h1 class="doc-title">{e(doc['title'])}{difficulty_badge(doc['difficulty'])}</h1>
        <div class="doc-meta">{meta_html}</div>
      </div>
    </div>
    {desc}
    {facts_html}
  </header>
  {attack_path_html(doc["path_steps"])}
  <div class="doc-body">
    {toc_html}
    <div class="prose">{doc['html']}</div>
  </div>
  {doc_tags_html(doc['tags'], root)}
</article>
{pagenav}
{related_html}"""

        art_type = "TechArticle" if doc["collection"] == "cheatsheets" else "BlogPosting"
        ld = {
            "@context": "https://schema.org",
            "@type": art_type,
            "headline": page_title,
            "url": self.canonical_for(doc["url"]),
            "mainEntityOfPage": self.canonical_for(doc["url"]),
            "image": self.og_url_for(doc["og_image"]),
            "author": self.person_ld(),
            "publisher": self.person_ld(),
            "description": doc["description"] or f"{col['singular']} - {doc['title']}",
        }
        if doc["date"]:
            ld["datePublished"] = iso_date(doc["date"])
        if doc["updated"] or doc["date"]:
            ld["dateModified"] = iso_date(doc["updated"] or doc["date"])
        if doc["tags"]:
            ld["keywords"] = ", ".join(t["name"] for t in doc["tags"])

        self.write(doc["url"], page_title, content,
                   description=doc["description"] or f"{col['singular']} - {doc['title']}",
                   current=col["dir"], body_class="page-doc",
                   og_image=doc["og_image"], og_type="article",
                   head_extra=self.jsonld(ld))

    def build_tags_index(self) -> None:
        root = "../"
        tags = list(self.tags.values())
        if not tags:
            content = (section_header("Tags", "Every topic across the site.")
                       + '<p class="empty">No tags yet.</p>')
            self.write("tags/", "Tags", content, current="tags")
            return

        counts = [t["count"] for t in tags]
        lo, hi = min(counts), max(counts)
        by_count = sorted(tags, key=lambda t: (-t["count"], t["slug"]))

        def weight(count: int) -> int:
            if hi == lo:
                return 3
            return 1 + round((count - lo) / (hi - lo) * 4)  # 1..5

        cloud = "".join(
            f'<a class="cloud-tag w{weight(t["count"])}" href="{root}tags/{t["slug"]}/" '
            f'data-name="{e(t["name"].lower())}">{e(t["name"])}'
            f'<span class="pill-count">{t["count"]}</span></a>'
            for t in by_count
        )

        # Alphabetical directory, grouped by first character.
        groups: dict[str, list] = {}
        for t in sorted(tags, key=lambda t: t["name"].lower()):
            letter = t["name"][0].upper()
            if not letter.isalpha():
                letter = "#"
            groups.setdefault(letter, []).append(t)

        listing = "".join(
            f'<section class="tag-group" data-letter="{e(letter)}">'
            f'<h2 class="tag-letter">{e(letter)}</h2><ul class="tag-list">'
            + "".join(
                f'<li data-name="{e(t["name"].lower())}">'
                f'<a href="{root}tags/{t["slug"]}/">{e(t["name"])}</a>'
                f'<span class="tag-count">{t["count"]} '
                f'{"entry" if t["count"] == 1 else "entries"}</span></li>'
                for t in items
            )
            + "</ul></section>"
            for letter, items in sorted(groups.items())
        )

        content = f"""{section_header("Tags",
            "Every topic covered on this site. Click any tag to see the writeups, "
            "posts and cheatsheets filed under it.", str(len(tags)))}
<div class="filter-bar" data-filter-target="#tag-cloud,#tag-directory">
  <div class="filter-row">
    <input class="filter-input" type="search" placeholder="Search tags…"
           aria-label="Search tags" autocomplete="off">
    <button class="chip chip-reset" type="button" data-reset>Clear</button>
  </div>
</div>
<div class="cloud" id="tag-cloud">{cloud}</div>
<div class="tag-directory" id="tag-directory">{listing}</div>
<p class="empty" data-empty hidden>No tags match that search.</p>"""
        self.write("tags/", "Tags", content,
                   description="Browse all content by topic.", current="tags")

    def build_tag_pages(self) -> None:
        root = "../../"
        for tag in self.tags.values():
            docs = sorted(tag["docs"],
                          key=lambda d: (d["date"] or date.min, d["title"]), reverse=True)
            sections = []
            group_specs = ([(c["key"], c["title"]) for c in COLLECTIONS]
                           + [("ctf", "CTF Walkthroughs")])
            for key, group_title in group_specs:
                group = [d for d in docs if d["collection"] == key]
                if not group:
                    continue
                rows = "".join(doc_row(d, root) for d in group)
                sections.append(
                    f'<section class="home-block"><div class="block-head">'
                    f'<h2 class="block-title">{e(group_title)}'
                    f'<span class="count">{len(group)}</span></h2></div>'
                    f'<ul class="rows">{rows}</ul></section>'
                )

            # Tags that frequently appear alongside this one.
            co: dict[str, int] = {}
            for d in docs:
                for t in d["tags"]:
                    if t["slug"] != tag["slug"]:
                        co[t["slug"]] = co.get(t["slug"], 0) + 1
            related_tags = sorted(co.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            related_html = ""
            if related_tags:
                pills = "".join(
                    f'<a class="pill" href="{root}tags/{s}/">'
                    f'{e(self.tags[s]["name"])}<span class="pill-count">{n}</span></a>'
                    for s, n in related_tags
                )
                related_html = ('<section class="home-block"><h2 class="block-title">'
                                f'Often paired with</h2><div class="pills pills-lg">{pills}</div>'
                                "</section>")

            noun = "entry" if tag["count"] == 1 else "entries"
            content = f"""<nav class="crumbs"><a href="{root}tags/">Tags</a>
  <span aria-hidden="true">/</span> <span>{e(tag['name'])}</span></nav>
{section_header(tag['name'], f"{tag['count']} {noun} tagged with “{tag['name']}”.")}
{''.join(sections)}
{related_html}"""
            self.write(tag["url"], f"Tag: {tag['name']}", content,
                       description=f"All content tagged {tag['name']}.", current="tags")

    def build_markdown_page(self, source: Path, url: str, md: markdown.Markdown,
                            current: str, body_class: str = "page-doc") -> None:
        if not source.exists():
            return
        meta, body = parse_frontmatter(source.read_text(encoding="utf-8"))
        body_html, _ = render_markdown(md, body)
        title = str(meta.get("title") or source.stem.title())
        root = "../" * depth_of(url)

        actions = ""
        if meta.get("pdf"):
            actions = (f'<div class="hero-actions"><a class="btn btn-primary" '
                       f'href="{root}{e(meta["pdf"])}" download>Download PDF</a></div>')

        # `heading:` overrides the on-page <h1> (e.g. the resume shows the name
        # while the tab title and nav still say "Resume").
        heading = str(meta.get("heading") or title)
        content = f"""<div class="doc doc-wide">
  <header class="doc-head">
    <h1 class="doc-title">{e(heading)}</h1>
    {f'<p class="lede">{e(meta["description"])}</p>' if meta.get("description") else ""}
    {actions}
  </header>
  <div class="prose prose-resume">{body_html}</div>
</div>"""
        head_extra = ""
        if current == "resume":
            head_extra = self.jsonld({"@context": "https://schema.org", **self.person_ld()})
        self.write(url, title, content,
                   description=str(meta.get("description") or ""),
                   current=current, body_class=body_class, head_extra=head_extra)
        if current == "resume":
            self.build_resume_print(url, heading, meta, body_html)

    def build_resume_print(self, url: str, heading: str, meta: dict, body_html: str) -> None:
        """A document-style copy of the resume at /resume/print/, which
        resume_pdf.py turns into the downloadable PDF."""
        tpl = (TEMPLATES / "resume_print.html").read_text(encoding="utf-8")
        m = re.search(r'<p class="resume-contact">.*?</p>', body_html, re.S)
        contact = m.group(0) if m else ""
        body = body_html.replace(contact, "", 1) if contact else body_html
        page = (tpl.replace("{{title}}", e(f"{heading} - Resume"))
                   .replace("{{heading}}", e(heading))
                   .replace("{{headline}}", e(meta.get("description") or ""))
                   .replace("{{contact}}", contact)
                   .replace("{{body}}", body))
        out = DIST / url / "print" / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")

    # -- CTF walkthroughs --------------------------------------------------

    @staticmethod
    def _initials(title: str) -> str:
        for tok in re.split(r"\s+", str(title)):
            letters = re.sub(r"[^A-Za-z0-9]", "", tok)
            if re.search(r"[A-Za-z]", letters):
                return letters[:4].upper()
        return (str(title)[:2] or "CTF").upper()

    def ctf_logo_html(self, event: dict, root: str, cls: str, size: int) -> str:
        if event["logo"]:
            return (f'<img class="{cls}" src="{root}static/ctf/{e(event["logo"])}" '
                    f'alt="{e(event["title"])} logo" width="{size}" height="{size}" '
                    f'loading="lazy">')
        return (f'<span class="{cls} ctf-badge" aria-hidden="true">'
                f'{e(self._initials(event["title"]))}</span>')

    def _challenge_item(self, chal: dict, root: str, section: str = "") -> str:
        # Show every category the challenge belongs to as a pill, so each row
        # carries its full category set. The one repeating the section heading
        # is marked so phones can hide it.
        cat_pills = "".join(
            f'<span class="chal-cat{" is-section" if c == section else ""}">{e(c)}</span>'
            for c in chal["categories"])
        author = (f'<span class="chal-author">by {e(", ".join(chal["authors"]))}</span>'
                  if chal["authors"] else "")

        badges = list(cat_pills and [cat_pills] or [])
        if chal["difficulty"]:
            badges.append(difficulty_badge(chal["difficulty"]))
        if chal["points"] not in ("", None):
            badges.append(f'<span class="chal-points">{e(str(chal["points"]))} pts</span>')
        badges_html = f'<div class="chal-badges">{"".join(badges)}</div>' if badges else ""

        if chal["solved"]:
            name = f'<a class="chal-name" href="{root}{chal["url"]}">{e(chal["title"])}</a>'
            lock = ""
        else:
            name = f'<span class="chal-name">{e(chal["title"])}</span>'
            lock = '<span class="chal-lock">unsolved</span>'
        cls = "chal" if chal["solved"] else "chal is-locked"
        return f"""<li class="{cls}">
  <div class="chal-left">{name}{lock}{author}</div>
  {badges_html}
</li>"""

    def build_ctf_index(self) -> None:
        root = "../"
        events = self.ctf_events
        if not events:
            content = (section_header("CTF Walkthroughs", CTF_BLURB)
                       + '<p class="empty">No CTFs here yet.</p>')
            self.write("ctf/", "CTF Walkthroughs", content,
                       description=CTF_BLURB, current="ctf")
            return

        cards = []
        for ev in events:
            total = len(ev["challenges"])
            solved = sum(1 for c in ev["challenges"] if c["solved"])
            cats = sorted({c["category"] for c in ev["challenges"]},
                          key=lambda x: (CATEGORY_ORDER.get(x.lower(), 90), x.lower()))
            cat_pills = "".join(f'<span class="pill pill-plain">{e(c)}</span>' for c in cats)

            meta_bits = []
            if ev["date"]:
                meta_bits.append(
                    f'<time datetime="{iso_date(ev["date"])}">'
                    f'{human_date_range(ev["date"], ev["date_end"])}</time>')
            meta_bits.append(f"{solved} solved" + (f" / {total}" if total != solved else ""))
            if ev["place"]:
                meta_bits.append(e(ev["place"]))
            meta = '<span class="dot">·</span>'.join(meta_bits)
            desc = f'<p class="card-desc">{e(ev["description"])}</p>' if ev["description"] else ""

            cards.append(f"""<article class="card ctf-card">
  <div class="ctf-card-head">
    {self.ctf_logo_html(ev, root, "ctf-logo", 56)}
    <div class="ctf-card-titles">
      <h3 class="card-title"><a href="{root}{ev['url']}">{e(ev['title'])}</a></h3>
      <div class="card-meta">{meta}</div>
    </div>
  </div>
  {desc}
  <div class="pills">{cat_pills}</div>
</article>""")

        listing = f'<div class="cards">{"".join(cards)}</div>'
        content = section_header("CTF Walkthroughs", CTF_BLURB, str(len(events))) + listing
        self.write("ctf/", "CTF Walkthroughs", content,
                   description=CTF_BLURB, current="ctf")

    def build_ctf_event(self, event: dict) -> None:
        root = "../../"
        total = len(event["challenges"])
        solved = sum(1 for c in event["challenges"] if c["solved"])

        # Group challenges under their primary category, in canonical order.
        # Each row still carries its full category pills.
        groups: dict[str, list] = {}
        for c in event["challenges"]:
            groups.setdefault(c["category"], []).append(c)
        ordered = sorted(groups, key=lambda x: (CATEGORY_ORDER.get(x.lower(), 90), x.lower()))
        sections = ""
        for cat in ordered:
            items = groups[cat]
            rows = "".join(self._challenge_item(c, root, cat) for c in items)
            solved_n = sum(1 for c in items if c["solved"])
            count = f"{solved_n}/{len(items)}" if solved_n != len(items) else f"{len(items)}"
            sections += (f'<section class="ctf-cat"><h2 class="block-title">{e(cat)}'
                         f'<span class="count">{count}</span></h2>'
                         f'<ul class="chal-list">{rows}</ul></section>')

        meta_bits = []
        if event["date"]:
            meta_bits.append(
                f'<time datetime="{iso_date(event["date"])}">'
                f'{human_date_range(event["date"], event["date_end"])}</time>')
        meta_bits.append(f"{solved} of {total} solved")
        meta = '<span class="dot">·</span>'.join(meta_bits)

        facts = []
        for label, value in (("Place", event["place"]), ("Team", event["team"])):
            if value:
                facts.append(f'<div class="fact"><dt>{label}</dt><dd>{e(value)}</dd></div>')
        if event["url_ext"]:
            facts.append('<div class="fact"><dt>Event</dt><dd>'
                         f'<a href="{e(event["url_ext"])}" rel="noopener" target="_blank">'
                         'Official site ↗</a></dd></div>')
        facts_html = f'<dl class="facts">{"".join(facts)}</dl>' if facts else ""
        intro = f'<div class="prose ctf-intro">{event["intro_html"]}</div>' if event["intro_html"] else ""

        content = f"""<nav class="crumbs"><a href="{root}ctf/">CTF Walkthroughs</a>
  <span aria-hidden="true">/</span> <span>{e(event['title'])}</span></nav>
<header class="doc-head ctf-event-head">
  <div class="doc-head-top">
    {self.ctf_logo_html(event, root, "ctf-hero-logo", 84)}
    <div class="doc-head-titles">
      <h1 class="doc-title">{e(event['title'])}</h1>
      <div class="doc-meta">{meta}</div>
    </div>
  </div>
  {f'<p class="lede">{e(event["description"])}</p>' if event["description"] and not event["intro_html"] else ""}
  {tag_pills([t for t in event['tags'] if t['slug'] in self.tags], root)}
  {facts_html}
</header>
{intro}
{sections}"""
        self.write(event["url"], event["title"], content,
                   description=event["description"] or f"CTF walkthroughs - {event['title']}",
                   current="ctf", body_class="page-doc")

    def build_ctf_challenge(self, chal: dict, event: dict) -> None:
        root = "../" * depth_of(chal["url"])

        cats_str = ", ".join(chal["categories"])
        authors_str = ", ".join(chal["authors"])

        meta_bits = [e(cats_str)]
        if chal["points"] not in ("", None):
            meta_bits.append(f'{e(str(chal["points"]))} pts')
        meta_bits.append(f'{chal["reading_time"]} min read')
        meta_html = '<span class="dot">·</span>'.join(meta_bits)

        cat_label = "Categories" if len(chal["categories"]) > 1 else "Category"
        facts = [f'<div class="fact"><dt>{cat_label}</dt><dd>{e(cats_str)}</dd></div>']
        if chal["difficulty"]:
            facts.append(f'<div class="fact"><dt>Difficulty</dt><dd>{e(chal["difficulty"])}</dd></div>')
        if authors_str:
            auth_label = "Authors" if len(chal["authors"]) > 1 else "Author"
            facts.append(f'<div class="fact"><dt>{auth_label}</dt><dd>{e(authors_str)}</dd></div>')
        if chal["points"] not in ("", None):
            facts.append(f'<div class="fact"><dt>Points</dt><dd>{e(str(chal["points"]))}</dd></div>')
        facts.append('<div class="fact"><dt>CTF</dt><dd>'
                     f'<a href="{root}{event["url"]}">{e(event["title"])}</a></dd></div>')
        facts_html = f'<dl class="facts">{"".join(facts)}</dl>'

        toc_html = toc_block(chal["toc"])

        # Prev / next within the event's solved challenges.
        sibs = [c for c in event["challenges"] if c["solved"]]
        pos = next((i for i, c in enumerate(sibs) if c["url"] == chal["url"]), 0)
        parts = []
        prev_c = sibs[pos - 1] if pos > 0 else None
        next_c = sibs[pos + 1] if pos + 1 < len(sibs) else None
        if prev_c:
            parts.append(f'<a class="pagenav-item" href="{root}{prev_c["url"]}">'
                         f'<span class="pagenav-label">← Previous</span>'
                         f'<span class="pagenav-title">{e(prev_c["title"])}</span></a>')
        else:
            parts.append('<span class="pagenav-item pagenav-empty"></span>')
        if next_c:
            parts.append(f'<a class="pagenav-item pagenav-next" href="{root}{next_c["url"]}">'
                         f'<span class="pagenav-label">Next →</span>'
                         f'<span class="pagenav-title">{e(next_c["title"])}</span></a>')
        else:
            parts.append('<span class="pagenav-item pagenav-empty"></span>')
        pagenav = f'<nav class="pagenav">{"".join(parts)}</nav>'

        content = f"""<article class="doc{' has-toc' if toc_html else ''}">
  <nav class="crumbs"><a href="{root}ctf/">CTF Walkthroughs</a>
    <span aria-hidden="true">/</span> <a href="{root}{event['url']}">{e(event['title'])}</a>
    <span aria-hidden="true">/</span> <span>{e(chal['title'])}</span></nav>
  <header class="doc-head">
    <h1 class="doc-title">{e(chal['title'])}{difficulty_badge(chal['difficulty'])}</h1>
    <div class="doc-meta">{meta_html}</div>
    {facts_html}
  </header>
  <div class="doc-body">
    {toc_html}
    <div class="prose">{chal['html']}</div>
  </div>
  {doc_tags_html(chal['tags'], root)}
</article>
{pagenav}"""

        ld = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": chal["title"],
            "url": self.canonical_for(chal["url"]),
            "mainEntityOfPage": self.canonical_for(chal["url"]),
            "image": self.og_url_for(chal["og_image"]),
            "author": self.person_ld(),
            "publisher": self.person_ld(),
            "description": chal["description"] or f"CTF walkthrough - {chal['title']}",
            "isPartOf": {"@type": "CreativeWork", "name": event["title"]},
        }
        if chal["date"]:
            ld["datePublished"] = iso_date(chal["date"])
        if chal["tags"]:
            ld["keywords"] = ", ".join(t["name"] for t in chal["tags"])

        self.write(chal["url"], chal["title"], content,
                   description=chal["description"] or f"CTF walkthrough - {chal['title']}",
                   current="ctf", body_class="page-doc",
                   og_image=chal["og_image"], og_type="article",
                   head_extra=self.jsonld(ld))

    def build_404(self) -> None:
        content = """<section class="hero hero-404">
  <p class="hero-kicker">404</p>
  <h1 class="hero-title">This path doesn't resolve.</h1>
  <p class="hero-blurb">The page you're after has moved, been renamed, or never existed.
    Try the writeups index or browse by tag.</p>
  <div class="hero-actions">
    <a class="btn btn-primary" href="/writeups/">Writeups</a>
    <a class="btn" href="/tags/">Tags</a>
  </div>
</section>"""
        full = (self.base
                .replace("{{root}}", "/")
                .replace("{{version}}", BUILD_VERSION)
                .replace("{{home}}", "/")
                .replace("{{lang}}", "en")
                .replace("{{title}}", e(f"404 · {self.config['site_name']}"))
                .replace("{{description}}", "Page not found")
                .replace("{{site_name}}", e(self.config["site_name"]))
                .replace("{{site_short}}", e(self.config["site_short"]))
                .replace("{{canonical}}", e(self.canonical_for("404.html")))
                .replace("{{og_type}}", "website")
                .replace("{{og_image}}", e(self.og_url_for("og/default.png")))
                .replace("{{twitter_handle}}", self.twitter_meta)
                .replace("{{head_extra}}", "")
                .replace("{{nav}}", self.nav_html("/", ""))
                .replace("{{social}}", self.social_html("/"))
                .replace("{{footer_note}}", e(self.config.get("footer_note", "")))
                .replace("{{year}}", str(date.today().year))
                .replace("{{body_class}}", "page-404")
                .replace("{{content}}", content))
        (DIST / "404.html").write_text(full, encoding="utf-8")
        self.pages_written += 1

    def build_sitemap(self) -> None:
        base = self.config.get("url", "").rstrip("/")
        urls = [""] + [f"{c['dir']}/" for c in COLLECTIONS] + ["tags/", "resume/"]
        if self.ctf_events:
            urls.append("ctf/")
            urls += [ev["url"] for ev in self.ctf_events]
        urls += [d["url"] for d in self.docs]
        urls += [t["url"] for t in self.tags.values()]
        entries = "".join(
            f"<url><loc>{base}/{u}</loc></url>" for u in dict.fromkeys(urls)
        )
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{entries}</urlset>",
            encoding="utf-8",
        )

    def build_search_index(self) -> None:
        """JSON index that powers the header search overlay and filter boxes."""
        data = [{
            "title": d["title"],
            "url": d["url"],
            "kind": d["collection"],
            "date": iso_date(d["date"]),
            "tags": [t["name"] for t in d["tags"]],
            "description": d["description"],
            "headings": d.get("headings", []),
            "text": d["text"],
        } for d in self.docs]
        (DIST / "index.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")

    def build_og_images(self) -> None:
        """Render a social-preview PNG per document plus a default site card."""
        cfg = self.config
        short = cfg.get("site_short", "")
        site = self.base_url or cfg.get("url", "")
        ok = ogimage.generate_default(
            DIST / "og" / "default.png", ROOT,
            title=cfg["site_name"],
            subtitle="HackTheBox writeups · Active Directory · web exploitation · privesc",
            eyebrow=cfg.get("tagline", "").upper(),
            site_short=short, site_url=site)
        if not ok:
            print("  ! Pillow unavailable - skipping OG images (using favicon fallback)")
            return
        made = 1
        for d in self.docs:
            ogimage.generate_card(
                DIST / d["og_image"], ROOT,
                title=d["title"],
                kind=(writeup_label(d) + " writeup") if d["collection"] == "writeups"
                else d["collection_singular"],
                date_str=human_date(d["date"]),
                tags=[t["name"] for t in d["tags"]],
                difficulty=d["difficulty"], logo_path=d.get("logo_path", ""),
                site_short=short, site_url=site)
            made += 1
        print(f"  {made} social cards → {DIST / 'og'}")

    def build_feed(self) -> None:
        """Atom feed of the most recent content across all collections."""
        base = self.base_url
        updated = max((d["date"] for d in self.docs if d["date"]), default=date.today())
        entries = []
        for d in self.docs[:20]:
            url = self.canonical_for(d["url"])
            when = iso_date(d["date"]) or date.today().isoformat()
            summary = d["description"] or (d["text"][:200] + "…")
            entries.append(
                f"<entry><title>{e(d['title'])}</title>"
                f'<link href="{e(url)}"/><id>{e(url)}</id>'
                f"<updated>{when}T00:00:00Z</updated>"
                f"<category term=\"{e(d['collection'])}\"/>"
                f"<summary>{e(summary)}</summary></entry>"
            )
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            f"<title>{e(self.config['site_name'])}</title>"
            f'<link href="{e(base)}/"/>'
            f'<link rel="self" href="{e(base)}/feed.xml"/>'
            f"<id>{e(base)}/</id>"
            f"<updated>{updated.isoformat()}T00:00:00Z</updated>"
            f"<author><name>{e(self.config['site_name'])}</name></author>"
            f"<subtitle>{e(self.config['description'])}</subtitle>"
            + "".join(entries) + "</feed>"
        )
        (DIST / "feed.xml").write_text(feed, encoding="utf-8")


# --------------------------------------------------------------------------
# Static assets
# --------------------------------------------------------------------------

def copy_static() -> None:
    if STATIC.is_dir():
        shutil.copytree(STATIC, DIST / "static", dirs_exist_ok=True)

    # Pygments theme, generated to match the site palette.
    css_dir = DIST / "static" / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    formatter = HtmlFormatter(style="one-dark")
    (css_dir / "syntax.css").write_text(
        "/* Generated by build.py - do not edit; change the Pygments style instead. */\n"
        + formatter.get_style_defs(".codehilite"),
        encoding="utf-8",
    )

    # Tell GitHub Pages to serve the files as-is instead of running Jekyll.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> int:
    # Keep console output UTF-8 even when stdout is redirected to a non-UTF-8
    # codepage (e.g. Windows cp1252), so the arrows/bullets we print never crash.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = sys.argv[1:]
    include_drafts = "--drafts" in args

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    md = make_markdown()
    print("Loading content…")
    docs = load_documents(md, include_drafts)
    ctf_events, ctf_docs = load_ctf(md)

    # CTF challenges join the shared index so tags, search and the feed include
    # them, but they render through their own builders (not build_collection).
    all_docs = docs + ctf_docs
    all_docs.sort(key=lambda d: (d["date"] or date.min, d["title"]), reverse=True)
    tags = build_tag_index(all_docs)

    site = Site(config, all_docs, tags, ctf_events=ctf_events)
    print("Rendering pages…")
    site.build_home()
    for col in COLLECTIONS:
        site.build_collection(col)
    for i, doc in enumerate(docs):
        site.build_doc(doc, i)
    site.build_ctf_index()
    for ev in ctf_events:
        site.build_ctf_event(ev)
        for chal in ev["challenges"]:
            if chal["solved"]:
                site.build_ctf_challenge(chal, ev)
    site.build_tags_index()
    site.build_tag_pages()
    site.build_tag_redirects()
    site.build_markdown_page(CONTENT / "pages" / "resume.md", "resume/", md, "resume",
                             body_class="page-doc page-resume")
    site.build_404()
    site.build_sitemap()
    site.build_search_index()
    site.build_feed()
    copy_static()
    print("Rendering social cards…")
    site.build_og_images()

    print(f"\n  {len(docs)} documents · {len(ctf_docs)} CTF walkthroughs · "
          f"{len(ctf_events)} CTFs · {len(tags)} tags · "
          f"{site.pages_written} pages → {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
