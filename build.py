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

ROOT = Path(__file__).parent.resolve()
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

# Machine logos: drop a file in static/machines/ and reference it in a writeup's
# frontmatter as `image: <name>` (extension optional).
MACHINE_IMG_DIR = STATIC / "machines"
MACHINE_IMG_EXTS = (".png", ".svg", ".webp", ".jpg", ".jpeg", ".gif", ".avif")

# Each content type lives in content/<dir>/ and gets an index page at /<dir>/.
COLLECTIONS = [
    {
        "key": "writeups",
        "dir": "writeups",
        "title": "Writeups",
        "singular": "Writeup",
        "blurb": "Machine and challenge walkthroughs — enumeration, foothold, "
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

DIFFICULTY_ORDER = {"very easy": 0, "easy": 1, "medium": 2, "hard": 3, "insane": 4}


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
    # Exact filename (with extension) that exists — use it directly.
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

def make_markdown() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=[
            "extra",          # tables, fenced code, attr_list, footnotes, def lists
            "sane_lists",
            "admonition",
            "meta",
            CodeHiliteExtension(guess_lang=False, linenums=False,
                                css_class="codehilite"),
            TocExtension(permalink="#", toc_depth="2-4", anchorlink=False),
        ],
    )


def render_markdown(md: markdown.Markdown, body: str) -> tuple[str, str]:
    md.reset()
    rendered = md.convert(body)
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

    raw_tags = meta.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    tags = []
    seen = set()
    for t in raw_tags:
        s = slugify(t)
        if s and s not in seen:
            seen.add(s)
            tags.append({"slug": s, "name": str(t).strip()})

    body_html, toc = render_markdown(md, body)
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", body_html)))

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
        "platform": str(meta.get("platform") or ""),
        "difficulty": str(meta.get("difficulty") or ""),
        "os": str(meta.get("os") or ""),
        "points": meta.get("points") or "",
        "image": resolve_machine_image(meta.get("image"), path.name),
        "html": body_html,
        "toc": toc,
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


def doc_row(doc: dict, root: str) -> str:
    """A compact one-line entry, used on the home page and tag pages."""
    return f"""<li class="row">
  <time class="row-date" datetime="{iso_date(doc['date'])}">{human_date(doc['date']) or '—'}</time>
  <div class="row-body">
    <a class="row-title" href="{root}{doc['url']}">{e(doc['title'])}</a>
    <span class="row-kind">{e(doc['collection_singular'])}</span>
    {tag_pills(doc['tags'], root, limit=4)}
  </div>
</li>"""


def section_header(title: str, blurb: str = "", count: str = "") -> str:
    count_html = f'<span class="count">{e(count)}</span>' if count else ""
    blurb_html = f'<p class="lede">{e(blurb)}</p>' if blurb else ""
    return f"""<header class="page-head">
  <h1 class="page-title">{e(title)}{count_html}</h1>
  {blurb_html}
</header>"""


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

class Site:
    def __init__(self, config: dict, docs: list[dict], tags: dict):
        self.config = config
        self.docs = docs
        self.tags = tags
        self.base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
        self.pages_written = 0

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
              current: str = "", body_class: str = "") -> None:
        """Render base.html around `content` and write it to dist/<url>index.html."""
        root = "../" * depth_of(url)
        full_title = title if url == "" else f"{title} · {self.config['site_name']}"
        page = (self.base
                .replace("{{root}}", root)
                .replace("{{home}}", root or "./")
                .replace("{{lang}}", "en")
                .replace("{{title}}", e(full_title))
                .replace("{{description}}", e(description or self.config["description"]))
                .replace("{{site_name}}", e(self.config["site_name"]))
                .replace("{{site_short}}", e(self.config["site_short"]))
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

        top_tags = sorted(self.tags.values(), key=lambda t: (-t["count"], t["slug"]))[:14]
        tag_cloud = "".join(
            f'<a class="pill" href="tags/{t["slug"]}/">{e(t["name"])}'
            f'<span class="pill-count">{t["count"]}</span></a>'
            for t in top_tags
        )

        stats = [
            ("Writeups", len(writeups)),
            ("Posts", len([d for d in self.docs if d["collection"] == "blog"])),
            ("Cheatsheets", len([d for d in self.docs if d["collection"] == "cheatsheets"])),
            ("Tags", len(self.tags)),
        ]
        stats_html = "".join(
            f'<div class="stat"><span class="stat-num">{n}</span>'
            f'<span class="stat-label">{e(label)}</span></div>'
            for label, n in stats
        )

        def block(heading, items, more_url, more_label):
            if not items:
                return ""
            rows = "".join(doc_row(d, root) for d in items)
            return f"""<section class="home-block">
  <div class="block-head">
    <h2 class="block-title">{e(heading)}</h2>
    <a class="block-more" href="{more_url}">{e(more_label)} <span aria-hidden="true">&rarr;</span></a>
  </div>
  <ul class="rows">{rows}</ul>
</section>"""

        content = f"""<section class="hero">
  <p class="hero-kicker">{e(cfg['tagline'])}</p>
  <h1 class="hero-title">{e(cfg['hero_intro'])}</h1>
  <p class="hero-blurb">{e(cfg['hero_blurb'])}</p>
  <div class="hero-actions">
    <a class="btn btn-primary" href="writeups/">Read the writeups</a>
    <a class="btn" href="resume/">View resume</a>
  </div>
</section>

<section class="stats">{stats_html}</section>

{block("Latest writeups", writeups[:cfg.get('home_writeup_count', 5)], "writeups/", "All writeups")}
{block("Recent writing", posts[:cfg.get('home_post_count', 4)], "blog/", "All posts")}

<section class="home-block">
  <div class="block-head">
    <h2 class="block-title">Browse by tag</h2>
    <a class="block-more" href="tags/">All tags <span aria-hidden="true">&rarr;</span></a>
  </div>
  <div class="pills pills-lg">{tag_cloud}</div>
</section>"""
        self.write("", cfg["site_name"], content, description=cfg["description"],
                   current="", body_class="page-home")

    def build_collection(self, col: dict) -> None:
        docs = [d for d in self.docs if d["collection"] == col["key"]]
        root = "../"

        # Tag filter chips for client-side filtering of this list.
        used_tags = {}
        for d in docs:
            for t in d["tags"]:
                used_tags[t["slug"]] = used_tags.get(t["slug"], 0) + 1
        chips = "".join(
            f'<button class="chip" data-tag="{e(slug)}" type="button">'
            f'{e(next(t["name"] for d in docs for t in d["tags"] if t["slug"] == slug))}'
            f'<span class="pill-count">{n}</span></button>'
            for slug, n in sorted(used_tags.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        filter_bar = f"""<div class="filter-bar" data-filter-target="#doc-list">
  <div class="filter-row">
    <input class="filter-input" type="search" placeholder="Filter {col['title'].lower()}…"
           aria-label="Filter {e(col['title'])}" autocomplete="off">
    <button class="chip chip-reset" type="button" data-reset>Clear</button>
  </div>
  <div class="chips">{chips}</div>
</div>""" if docs else ""

        if docs:
            cards = "".join(
                f'<div class="card-wrap" data-title="{e(d["title"].lower())}" '
                f'data-tags="{e(" ".join(t["slug"] for t in d["tags"]))}">'
                f'{doc_card(d, root)}</div>'
                for d in docs
            )
            listing = f'<div class="cards" id="doc-list">{cards}</div>'
            empty = '<p class="empty" data-empty hidden>No matches. Try a different filter.</p>'
        else:
            listing = ('<p class="empty">Nothing here yet — drop a Markdown file in '
                       f'<code>content/{col["dir"]}/</code> and rebuild.</p>')
            empty = ""

        content = (section_header(col["title"], col["blurb"], f"{len(docs)}")
                   + filter_bar + listing + empty)
        self.write(f"{col['dir']}/", col["title"], content,
                   description=col["blurb"], current=col["dir"])

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

        toc_html = ""
        if doc["toc"] and doc["toc"].count("<li") >= 3:
            toc_html = (f'<aside class="toc"><p class="toc-title">On this page</p>'
                        f'{doc["toc"]}</aside>')

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

        logo_html = ""
        if doc["image"]:
            logo_html = (
                f'<img class="machine-logo" src="{root}static/machines/{e(doc["image"])}" '
                f'alt="{e(doc["title"])} logo" width="96" height="96" loading="lazy">'
            )

        content = f"""<article class="doc">
  <nav class="crumbs"><a href="{root}{col['dir']}/">{e(col['title'])}</a>
    <span aria-hidden="true">/</span> <span>{e(doc['title'])}</span></nav>
  <header class="doc-head">
    <div class="doc-head-top">
      {logo_html}
      <div class="doc-head-titles">
        <h1 class="doc-title">{e(doc['title'])}{difficulty_badge(doc['difficulty'])}</h1>
        <div class="doc-meta">{meta_html}</div>
      </div>
    </div>
    {desc}
    {tag_pills(doc['tags'], root)}
    {facts_html}
  </header>
  {toc_html}
  <div class="prose">{doc['html']}</div>
</article>
{pagenav}
{related_html}"""

        self.write(doc["url"], doc["title"], content,
                   description=doc["description"] or f"{col['singular']} — {doc['title']}",
                   current=col["dir"], body_class="page-doc")

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
            for col in COLLECTIONS:
                group = [d for d in docs if d["collection"] == col["key"]]
                if not group:
                    continue
                rows = "".join(doc_row(d, root) for d in group)
                sections.append(
                    f'<section class="home-block"><div class="block-head">'
                    f'<h2 class="block-title">{e(col["title"])}'
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

        content = f"""<div class="doc doc-wide">
  <header class="doc-head">
    <h1 class="doc-title">{e(title)}</h1>
    {f'<p class="lede">{e(meta["description"])}</p>' if meta.get("description") else ""}
    {actions}
  </header>
  <div class="prose prose-resume">{body_html}</div>
</div>"""
        self.write(url, title, content,
                   description=str(meta.get("description") or ""),
                   current=current, body_class=body_class)

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
        page_root = ""
        root = ""
        full = (self.base
                .replace("{{root}}", "/")
                .replace("{{home}}", "/")
                .replace("{{lang}}", "en")
                .replace("{{title}}", e(f"404 · {self.config['site_name']}"))
                .replace("{{description}}", "Page not found")
                .replace("{{site_name}}", e(self.config["site_name"]))
                .replace("{{site_short}}", e(self.config["site_short"]))
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
        """Small JSON index — powers the filter boxes and any future search UI."""
        data = [{
            "title": d["title"],
            "url": d["url"],
            "kind": d["collection"],
            "date": iso_date(d["date"]),
            "tags": [t["name"] for t in d["tags"]],
            "description": d["description"],
        } for d in self.docs]
        (DIST / "index.json").write_text(json.dumps(data, indent=1), encoding="utf-8")


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
        "/* Generated by build.py — do not edit; change the Pygments style instead. */\n"
        + formatter.get_style_defs(".codehilite"),
        encoding="utf-8",
    )

    # Tell GitHub Pages to serve the files as-is instead of running Jekyll.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    include_drafts = "--drafts" in args

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    md = make_markdown()
    print("Loading content…")
    docs = load_documents(md, include_drafts)
    tags = build_tag_index(docs)

    site = Site(config, docs, tags)
    print("Rendering pages…")
    site.build_home()
    for col in COLLECTIONS:
        site.build_collection(col)
    for i, doc in enumerate(docs):
        site.build_doc(doc, i)
    site.build_tags_index()
    site.build_tag_pages()
    site.build_markdown_page(CONTENT / "pages" / "resume.md", "resume/", md, "resume")
    site.build_404()
    site.build_sitemap()
    site.build_search_index()
    copy_static()

    print(f"\n  {len(docs)} documents · {len(tags)} tags · "
          f"{site.pages_written} pages → {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
