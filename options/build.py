#!/usr/bin/env python3
"""Stamp the live landing into five style options. Copy stays the same."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "index.html").read_text(encoding="utf-8")

BAR = """<div class="opt-bar"><strong>{label}</strong><nav>
<a href="/options/">All five</a>
<a href="/options/daylight">1 Daylight</a>
<a href="/options/workshop">2 Workshop</a>
<a href="/options/type">3 Type</a>
<a href="/options/circle">4 Circle</a>
<a href="/options/later">5 Later</a>
<a href="/">Live site</a>
</nav></div>
"""

HEAD = """<meta name="robots" content="noindex,nofollow" id="robots-meta">
<link rel="stylesheet" href="/assets/options/themes.css">
<title>{title}</title>
"""

CIRCLE = """<div class="circle-graphic"><img src="/assets/options/circle.svg" width="320" height="320" alt="Twelve seats around a table."></div>"""
SLOT = """<div class="photo-slot">Photographs from the first sessions.<br>November 2026.</div>"""

THEMES = [
    {
        "slug": "daylight",
        "class": "opt-page opt-daylight",
        "label": "Option 1 of 5 — Daylight workroom",
        "title": "Daylight workroom — Solo + AI Berlin",
        "hero_src": "/assets/options/daylight-hero.jpg",
        "hero_alt": "A sunlit Berlin work table with closed laptops, notebooks, and coffee.",
        "hero_cap": "A room in Berlin · two Tuesdays",
        "ticket_src": "/assets/options/daylight-table.jpg",
        "ticket_alt": "Notebook, stickies, and a closed laptop on a daylight table.",
    },
    {
        "slug": "workshop",
        "class": "opt-page opt-workshop",
        "label": "Option 2 of 5 — Builder / workshop",
        "title": "Builder workshop — Solo + AI Berlin",
        "hero_src": "/assets/options/workshop-hero.jpg",
        "hero_alt": "A used Berlin work desk: cables, keyboard, whiteboard, coffee rings.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/workshop-desk.jpg",
        "ticket_alt": "Closed laptop, cables, highlighter, and a coffee cup on a desk.",
    },
    {
        "slug": "type",
        "class": "opt-page opt-type",
        "label": "Option 3 of 5 — Type-first",
        "title": "Type-first — Solo + AI Berlin",
        "drop_bleed": True,
        "drop_ticket_photo": True,
    },
    {
        "slug": "circle",
        "class": "opt-page opt-circle",
        "label": "Option 4 of 5 — Small-circle graphic",
        "title": "Circle graphic — Solo + AI Berlin",
        "drop_bleed": True,
        "ticket_html": CIRCLE,
    },
    {
        "slug": "later",
        "class": "opt-page opt-later",
        "label": "Option 5 of 5 — Documentary, later",
        "title": "Documentary later — Solo + AI Berlin",
        "drop_bleed": True,
        "ticket_html": SLOT,
    },
]


def apply(html: str, theme: dict) -> str:
    html = html.replace('<html lang="en">', f'<html lang="en" class="{theme["class"]}">')
    html = html.replace("<body>", f"<body class=\"{theme['class']}\">\n" + BAR.format(label=theme["label"]))
    html = html.replace(
        '<meta name="robots" content="index,follow" id="robots-meta">',
        '<meta name="robots" content="noindex,nofollow" id="robots-meta">',
    )
    html = html.replace(
        '<title>Solo + AI Berlin — Build your business with AI. Not alone.</title>',
        f'<title>{theme["title"]}</title>\n<link rel="stylesheet" href="/assets/options/themes.css">',
    )
    html = html.replace(
        '<link rel="canonical" href="https://aiberlin.dtcdev.click/">',
        f'<link rel="canonical" href="https://aiberlin.dtcdev.click/options/{theme["slug"]}">',
    )
    if theme.get("drop_bleed"):
        html = html.replace(
            """<section class="hero-bleed">
  <img src="/assets/hero.jpg" width="2400" height="1350" alt="A rain-wet Prenzlauer Berg street at dusk, Altbau windows lit gold, bicycles along the fence.">
  <p class="hero-bleed-caption">Prenzlauer Berg · Tuesday evenings</p>
</section>
""",
            "",
        )
    elif "hero_src" in theme:
        html = html.replace("/assets/hero.jpg", theme["hero_src"])
        html = html.replace(
            "A rain-wet Prenzlauer Berg street at dusk, Altbau windows lit gold, bicycles along the fence.",
            theme["hero_alt"],
        )
        html = html.replace("Prenzlauer Berg · Tuesday evenings", theme["hero_cap"])
    if theme.get("drop_ticket_photo"):
        html = html.replace(
            '<div class="ticket-photo"><img src="/assets/table.jpg" width="800" height="533" alt="A round table of notebooks and empty chairs by a rain-wet Berlin window."><span class="motif-note">A circle, not an audience.</span></div>',
            "",
        )
    elif theme.get("ticket_html"):
        html = html.replace(
            '<div class="ticket-photo"><img src="/assets/table.jpg" width="800" height="533" alt="A round table of notebooks and empty chairs by a rain-wet Berlin window."><span class="motif-note">A circle, not an audience.</span></div>',
            theme["ticket_html"],
        )
    elif "ticket_src" in theme:
        html = html.replace("/assets/table.jpg", theme["ticket_src"])
        html = html.replace(
            "A round table of notebooks and empty chairs by a rain-wet Berlin window.",
            theme["ticket_alt"],
        )
    return html


def main() -> None:
    out = ROOT / "options"
    out.mkdir(exist_ok=True)
    for theme in THEMES:
        (out / f"{theme['slug']}.html").write_text(apply(SRC, theme), encoding="utf-8")
        print("wrote", theme["slug"])


if __name__ == "__main__":
    main()
