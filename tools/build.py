#!/usr/bin/env python3
"""Render the SVG assets for the Jedeiah profile README.

Aesthetic: flat editorial.  Type and hairlines on paper, one warm accent.
Every graphic is drawn locally, so the profile carries no third-party
widget dependency.

Outputs, per theme:

    assets/banner-{dark,light}.svg    masthead
    assets/stack-{dark,light}.svg     technology chips

Usage:
    python3 tools/build.py
"""

from __future__ import annotations

import html
import json
import pathlib
import sys
from xml.etree import ElementTree

LOGIN = "Jedeiah"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ROOT / "data" / "icons.json"

SANS = ("ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "'Helvetica Neue', Arial, sans-serif")
MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', 'Courier New', monospace")

W = 1280
RADIUS = 14

# --------------------------------------------------------------------------
# themes
# --------------------------------------------------------------------------

DARK = {
    "key": "dark",
    "bg": "#05070D",
    "panel": "#080B14",
    "inset": "#0B111C",
    "border": "#16233A",
    "grid": "#0D1626",
    "ink": "#CFEFFF",
    "ink_hi": "#EAFBFF",
    "muted": "#5D7C93",
    "dim": "#33465A",
    "cyan": "#22E1FF",
    "magenta": "#FF3D9A",
    "lime": "#A8FF3D",
    "amber": "#FFC53D",
    "violet": "#9B6BFF",
    "cell0": "#101B27",
    "cells": ["#0A3F52", "#0C6C86", "#14A6C4", "#4DE7FF"],
    "scan": "#000000",
    "scan_op": 0.30,
    "glow_op": 0.60,
    "beam_op": 0.18,
}

LIGHT = {
    "key": "light",
    "bg": "#F4F7FB",
    "panel": "#FFFFFF",
    "inset": "#F5F8FC",
    "border": "#D6DFEA",
    "grid": "#E4EBF3",
    "ink": "#0A1622",
    "ink_hi": "#050C14",
    "muted": "#5C6E80",
    "dim": "#A7B4C2",
    "cyan": "#0089AD",
    "magenta": "#D0287C",
    "lime": "#4E9600",
    "amber": "#A86A00",
    "violet": "#6A3FD1",
    "cell0": "#E3E9F1",
    "cells": ["#B6E4F0", "#63C6DE", "#1A9DBE", "#00708F"],
    "scan": "#94A9BE",
    "scan_op": 0.10,
    "glow_op": 0.22,
    "beam_op": 0.13,
}

THEMES = {"dark": DARK, "light": LIGHT}

# Editorial palette: the same keys, flattened to paper + a single warm accent.
# Everything that used to glow is now ink; the heatmap becomes a neutral ramp.
def _paper(base: dict) -> dict:
    p = dict(base)
    if base["key"] == "light":
        p.update({
            "panel": "#FDFDFC", "inset": "#F7F5F0", "border": "#E3E0D8",
            "grid": "#F0EEE8", "ink": "#141414", "ink_hi": "#0A0A0A",
            "muted": "#6B6560", "dim": "#A9A29A",
            "cyan": "#9A3412", "magenta": "#9A3412", "accent": "#9A3412",
            "cell0": "#F0EEE8",
            "cells": ["#E4DFD6", "#CDBFAC", "#A8845F", "#7A4A2B"],
            "scan_op": 0.0, "glow_op": 0.0, "beam_op": 0.0,
        })
    else:
        p.update({
            "panel": "#0B0F14", "inset": "#121820", "border": "#1E2836",
            "grid": "#141B24", "ink": "#E8EDF3", "ink_hi": "#F7FAFD",
            "muted": "#8B98A8", "dim": "#55616F",
            "cyan": "#FF8A5B", "magenta": "#FF8A5B", "accent": "#FF8A5B",
            "cell0": "#141B24",
            "cells": ["#1B2532", "#2C3D50", "#4A6A86", "#7FA6C4"],
            "scan_op": 0.0, "glow_op": 0.0, "beam_op": 0.0,
        })
    return p


PAPER = {k: _paper(v) for k, v in THEMES.items()}


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
# shared chrome
# --------------------------------------------------------------------------

def corner(x: float, y: float, dx: float, dy: float, arm: float = 16) -> str:
    """One L-shaped HUD bracket; dx/dy pick which corner and which way it opens."""
    ox, oy = (arm * dx, arm * dy)
    return (f'M {x} {y + oy} L {x} {y} L {x + ox} {y}')


def chrome_flat(t: dict, h: int, extra: str = "") -> str:
    """Editorial shell: paper ground, hairline frame. No brackets, no scanlines."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<defs>
<clipPath id="card"><rect width="{W}" height="{h}" rx="{RADIUS}"/></clipPath>
<linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['cyan']}"/>
  <stop offset="1" stop-color="{t['magenta']}"/>
</linearGradient>
<linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['border']}"/>
  <stop offset="1" stop-color="{t['border']}"/>
</linearGradient>
{extra}
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{h}" fill="{t['panel']}"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="{RADIUS}" fill="none"
      stroke="{t['border']}" stroke-width="1"/>
"""


# --------------------------------------------------------------------------
# banner
# --------------------------------------------------------------------------

def banner(theme: str) -> str:
    """Masthead: one wordmark, one rule, three columns of facts."""
    t = PAPER[theme]
    h = 232
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
           f'viewBox="0 0 {W} {h}" role="img">']

    svg.append(f'<text x="0" y="92" font-family="{SANS}" font-size="92" '
               f'font-weight="700" letter-spacing="-3.4" fill="{t["ink"]}">Jedeiah</text>')
    svg.append(f'<rect x="0" y="120" width="{W}" height="1" fill="{t["border"]}"/>'
               f'<rect x="0" y="119" width="96" height="3" fill="{t["accent"]}"/>')

    cols = (
        ("FOCUS", "agent tooling &#183; network plumbing"),
        ("STACK", "rust &#183; typescript &#183; python"),
        ("ON GITHUB", "since 2018"),
    )
    for i, (label, value) in enumerate(cols):
        x = i * 440
        svg.append(f'<text x="{x}" y="152" font-family="{MONO}" font-size="12" '
                   f'letter-spacing="2.4" fill="{t["muted"]}">{label}</text>')
        svg.append(f'<text x="{x}" y="178" font-family="{SANS}" font-size="16" '
                   f'fill="{t["ink"]}">{value}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------
# stack chips
# --------------------------------------------------------------------------

STACK_ROWS = [
    [("rust", "RUST"), ("python", "PYTHON"), ("typescript", "TYPESCRIPT"),
     ("javascript", "JAVASCRIPT"), ("go", "GO"), ("openjdk", "JAVA")],
    [("tauri", "TAURI"), ("react", "REACT"), ("vuedotjs", "VUE"),
     ("postgresql", "POSTGRES"), ("sqlite", "SQLITE"), ("redis", "REDIS")],
]

CHIP_H, CHIP_GAP, CHIP_PAD, ICON = 40, 14, 16, 18
LABEL_SIZE, LABEL_ADV = 15.0, 0.6


def chip_width(label: str) -> float:
    return CHIP_PAD * 2 + ICON + 10 + len(label) * LABEL_SIZE * LABEL_ADV


def icon_markup(icons: dict, slug: str, x: float, y: float, tone: str) -> str:
    path = (icons.get(slug) or {}).get("path")
    if not path:
        return ""
    s = ICON / 24.0
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.5f})">'
            f'<path d="{path}" fill="{tone}"/></g>')


def stack(theme: str, icons: dict) -> str:
    t = PAPER[theme]
    h = 168
    svg = [chrome_flat(t, h)]
    top = 30
    for r, row in enumerate(STACK_ROWS):
        widths = [chip_width(lbl) for _, lbl in row]
        total = sum(widths) + CHIP_GAP * (len(row) - 1)
        x = (W - total) / 2
        y = top + r * (CHIP_H + 18)
        for (slug, label), cw in zip(row, widths):
            svg.append(
                f'<rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="{CHIP_H}" rx="9" '
                f'fill="{t["inset"]}" stroke="{t["border"]}" stroke-width="1"/>'
                + icon_markup(icons, slug, x + CHIP_PAD, y + (CHIP_H - ICON) / 2, t["ink"])
                + f'<text x="{x + CHIP_PAD + ICON + 10:.1f}" y="{y + 25.5}" '
                  f'font-family="{MONO}" font-size="{LABEL_SIZE}" letter-spacing="1.2" '
                  f'fill="{t["ink"]}">{label}</text>'
            )
            x += cw + CHIP_GAP
    svg.append(f'<text x="{W / 2}" y="152" font-family="{MONO}" font-size="13" '
               f'fill="{t["muted"]}" text-anchor="middle" letter-spacing="1.6">'
               f'AI / LLM&#160;integration&#160;&#160;·&#160;&#160;browser automation'
               f'&#160;&#160;·&#160;&#160;network &amp; proxies'
               f'&#160;&#160;·&#160;&#160;data engineering</text>')
    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------

def main() -> int:
    icons = json.loads(ICONS.read_text()) if ICONS.exists() else {}
    if not icons:
        print("warning: data/icons.json missing, chips will render without glyphs",
              file=sys.stderr)

    ASSETS.mkdir(parents=True, exist_ok=True)
    for key in ("dark", "light"):
        for name, svg in (("banner", banner(key)), ("stack", stack(key, icons))):
            try:
                ElementTree.fromstring(svg)
            except ElementTree.ParseError as exc:
                print(f"ERROR: {name}-{key}.svg is not valid XML: {exc}", file=sys.stderr)
                return 1
            (ASSETS / f"{name}-{key}.svg").write_text(svg)
            print(f"wrote {name}-{key}.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
