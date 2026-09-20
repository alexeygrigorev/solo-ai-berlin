#!/usr/bin/env python3
"""Stamp the live landing into five cleaner workshop photo variants."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "index.html").read_text(encoding="utf-8")

BAR = """<div class="opt-bar"><strong>{label}</strong><nav>
<a href="/options/">All five</a>
<a href="/options/1">1 Room</a>
<a href="/options/2">2 Table for six</a>
<a href="/options/3">3 Studio desk</a>
<a href="/options/4">4 Evening</a>
<a href="/options/5">5 Lived-in</a>
</nav></div>
"""

THEMES = [
    {
        "slug": "1",
        "label": "Workshop 1 of 5 — Berlin room, daylight",
        "title": "Workshop 1 — Berlin room — Solo + AI Berlin",
        "hero_src": "/assets/options/w1-hero.jpg",
        "hero_alt": "A sunlit Berlin table with two closed laptops, notebooks, a plant, and four chairs.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/w1-table.jpg",
        "ticket_alt": "Closed laptop, blank notebook, mug, and a coiled cable on pale wood.",
        "blurb": "Apartment workroom, plant, four chairs.",
    },
    {
        "slug": "2",
        "label": "Workshop 2 of 5 — Table for six",
        "title": "Workshop 2 — Table for six — Solo + AI Berlin",
        "hero_src": "/assets/options/w2-hero.jpg",
        "hero_alt": "A bright meeting table set with closed laptops, notebooks, and water glasses.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/w2-table.jpg",
        "ticket_alt": "Closed laptop, keyboard, notebook and pen on a white desk.",
        "blurb": "Cleaner, more like a booked room.",
    },
    {
        "slug": "3",
        "label": "Workshop 3 of 5 — Studio desk",
        "title": "Workshop 3 — Studio desk — Solo + AI Berlin",
        "hero_src": "/assets/options/w3-hero.jpg",
        "hero_alt": "A single pale desk with a closed laptop, notebook, keyboard, and a glass of water.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/w3-table.jpg",
        "ticket_alt": "Two notebooks, a closed laptop, and a glass of water on oak.",
        "blurb": "Quieter, one-desk, lots of wall.",
    },
    {
        "slug": "4",
        "label": "Workshop 4 of 5 — Evening lamp",
        "title": "Workshop 4 — Evening lamp — Solo + AI Berlin",
        "hero_src": "/assets/options/w4-hero.jpg",
        "hero_alt": "A tidy evening table under a cone lamp, closed laptop, notebook, and tea.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/w4-table.jpg",
        "ticket_alt": "Round white table with a closed laptop and three notebooks.",
        "blurb": "After-work light, still tidy.",
    },
    {
        "slug": "5",
        "label": "Workshop 5 of 5 — Lived-in",
        "title": "Workshop 5 — Lived-in — Solo + AI Berlin",
        "hero_src": "/assets/options/w5-hero.jpg",
        "hero_alt": "A darker wood table with three closed laptops, open notebooks, and a snake plant by the window.",
        "hero_cap": "Bring the actual work",
        "ticket_src": "/assets/options/w5-table.jpg",
        "ticket_alt": "Two notebooks, a closed laptop, and a glass of water on oak.",
        "blurb": "A bit more used, still not messy.",
    },
]


def apply(html: str, theme: dict) -> str:
    html = html.replace('<html lang="en">', '<html lang="en" class="opt-page opt-workshop">')
    html = html.replace("<body>", '<body class="opt-page opt-workshop">\n' + BAR.format(label=theme["label"]))
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
    html = html.replace("/assets/hero.jpg", theme["hero_src"])
    html = html.replace(
        "A rain-wet Prenzlauer Berg street at dusk, Altbau windows lit gold, bicycles along the fence.",
        theme["hero_alt"],
    )
    html = html.replace("Prenzlauer Berg · Tuesday evenings", theme["hero_cap"])
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
