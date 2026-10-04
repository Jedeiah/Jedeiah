#!/usr/bin/env python3
"""Build the SVG assets used by the Jedeiah profile README.

Everything is rendered locally from live GitHub data, so the profile carries no
third-party widget dependency.  Outputs, for each theme:

    assets/banner-{dark,light}.svg     hero header
    assets/overview-{dark,light}.svg   contribution heatmap + counters

Usage:
    python3 tools/build.py            # fetch live data, render, write assets
    python3 tools/build.py --cached   # render from data/profile.json only
"""

from __future__ import annotations

import argparse
import html
import json
import math
import pathlib
import subprocess
import sys
from datetime import date, datetime, timezone
from xml.etree import ElementTree

LOGIN = "Jedeiah"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data" / "profile.json"

SANS = ("ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "'Helvetica Neue', Arial, 'PingFang SC', 'Hiragino Sans GB', "
        "'Microsoft YaHei', sans-serif")
MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', 'Courier New', monospace")

W = 1280                      # every panel shares this width
BANNER_H = 320
OVERVIEW_H = 250
RADIUS = 18

# --------------------------------------------------------------------------
# themes
# --------------------------------------------------------------------------

DARK = {
    "surface": "#0B0F17",
    "surface_hi": "#111827",
    "border": "#1C2534",
    "edge": "#8FA3BF",
    "fg": "#E6EDF3",
    "fg_strong": "#F5F9FF",
    "muted": "#7D8794",
    "dim": "#4C5666",
    "cy": "#22D3EE",
    "vi": "#A78BFA",
    "pk": "#F472B6",
    "blob": [("cy", 0.20), ("vi", 0.24), ("cy", 0.10)],
    "dots": 0.085,
    "cell0": "#151C28",
    "cells": ["#0E3A46", "#116E7E", "#17A2B8", "#3BE0F5"],
    "grid_line": "#1C2534",
    "sweep": "#FFFFFF",
}

LIGHT = {
    "surface": "#FFFFFF",
    "surface_hi": "#F6F8FA",
    "border": "#D8DEE6",
    "edge": "#FFFFFF",
    "fg": "#1F2328",
    "fg_strong": "#0B0F17",
    "muted": "#59636E",
    "dim": "#AFB8C1",
    "cy": "#0891B2",
    "vi": "#7C3AED",
    "pk": "#DB2777",
    "blob": [("cy", 0.10), ("vi", 0.10), ("cy", 0.05)],
    "dots": 0.055,
    "cell0": "#E4E8ED",
    "cells": ["#C3E9F3", "#7FD3E6", "#2FA8C6", "#0B7A96"],
    "grid_line": "#D8DEE6",
    "sweep": "#FFFFFF",
}

THEMES = {"dark": DARK, "light": LIGHT}


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    followers { totalCount }
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { name stargazerCount forkCount primaryLanguage { name color } }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def fetch() -> dict:
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"],
        capture_output=True, text=True, check=True,
    )
    raw = json.loads(out.stdout)["data"]["user"]

    langs: dict[str, int] = {}
    for node in raw["repositories"]["nodes"]:
        lang = (node.get("primaryLanguage") or {}).get("name")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1

    weeks = []
    for wk in raw["contributionsCollection"]["contributionCalendar"]["weeks"]:
        days = sorted(wk["contributionDays"], key=lambda d: d["weekday"])
        weeks.append([
            {"d": d["date"], "n": d["contributionCount"], "w": d["weekday"]}
            for d in days
        ])

    return {
        "login": LOGIN,
        "name": raw.get("name") or LOGIN,
        "created": raw["createdAt"][:10],
        "followers": raw["followers"]["totalCount"],
        "repos": raw["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in raw["repositories"]["nodes"]),
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "total_contrib": raw["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "weeks": weeks,
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def load(cached: bool) -> dict:
    if cached and DATA.exists():
        return json.loads(DATA.read_text())
    data = fetch()
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


# --------------------------------------------------------------------------
# shared svg fragments
# --------------------------------------------------------------------------

def card_open(t: dict, h: int, theme_key: str, extra_defs: str = "",
              drift: bool = False) -> str:
    """Rounded surface panel with a glass top edge and theme-following backdrop."""
    def blob(cx: float, cy: float, rx: float, ry: float, ref: str, i: int) -> str:
        if not drift:
            return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{ref})"/>'
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{ref})">'
                f'<animateTransform attributeName="transform" type="translate" '
                f'dur="{26 + i * 9}s" begin="{-i * 4}s" repeatCount="indefinite" '
                f'values="0 0;{18 + i * 10} {12 - i * 6};0 0"/></ellipse>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<defs>
<clipPath id="card"><rect x="0" y="0" width="{W}" height="{h}" rx="{RADIUS}"/></clipPath>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['edge']}" stop-opacity="0"/>
  <stop offset="0.45" stop-color="{t['edge']}" stop-opacity="{0.22 if theme_key == 'dark' else 0.9}"/>
  <stop offset="1" stop-color="{t['edge']}" stop-opacity="0"/>
</linearGradient>
<linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['cy']}" stop-opacity="0"/>
  <stop offset="0.5" stop-color="{t['cy']}" stop-opacity="0.85"/>
  <stop offset="1" stop-color="{t['vi']}" stop-opacity="0"/>
  <animate attributeName="x1" values="-0.4;1" dur="9s" repeatCount="indefinite"/>
  <animate attributeName="x2" values="0;1.4" dur="9s" repeatCount="indefinite"/>
</linearGradient>
<radialGradient id="b1" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="{t['cy']}" stop-opacity="{t['blob'][0][1]}"/>
  <stop offset="1" stop-color="{t['cy']}" stop-opacity="0"/>
</radialGradient>
<radialGradient id="b2" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="{t['vi']}" stop-opacity="{t['blob'][1][1]}"/>
  <stop offset="1" stop-color="{t['vi']}" stop-opacity="0"/>
</radialGradient>
<pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
  <circle cx="1.1" cy="1.1" r="1.1" fill="{t['fg']}" opacity="{t['dots']}"/>
</pattern>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/>
  <stop offset="0.18" stop-color="#fff" stop-opacity="1"/>
  <stop offset="0.82" stop-color="#fff" stop-opacity="1"/>
  <stop offset="1" stop-color="#fff" stop-opacity="0"/>
</linearGradient>
<mask id="dotmask"><rect x="0" y="0" width="{W}" height="{h}" fill="url(#fade)"/></mask>
{extra_defs}
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{h}" fill="{t['surface']}"/>
{blob(215, 30, 560, 330, "b1", 0)}
{blob(1105, h, 600, 360, "b2", 1)}
<rect width="{W}" height="{h}" fill="url(#dots)" mask="url(#dotmask)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="{RADIUS}" fill="none"
      stroke="{t['border']}" stroke-width="1"/>
<path d="M {RADIUS} 0.5 H {W - RADIUS}" stroke="url(#edge)" stroke-width="1" fill="none"/>
"""


FRAGMENT_BUDGET = None  # generated svgs are small; no clipping needed


# --------------------------------------------------------------------------
# banner
# --------------------------------------------------------------------------

CYCLE = 15.0          # seconds for one full role rotation
ROLES = [
    "agent tooling · claude-code / codex / dsh",
    "rust desktop · tauri / egui",
    "python automation · playwright / asyncio",
]
PROMPT = "~ $ "
NAME_X = 196
ROLE_Y = 212
MONO_ROLE_SIZE = 17.0
MONO_ADVANCE = 0.6    # advance width per char, in em, for ui-monospace family


def typing_group(role_idx: int, t: dict) -> str:
    """One role line, revealed character by character, then fading as a block."""
    slot = CYCLE / len(ROLES)
    a = role_idx * slot
    t_start = (a + 0.35) / CYCLE
    t_end = (a + 1.55) / CYCLE
    hold_end = (a + slot - 0.45) / CYCLE
    fade_end = (a + slot - 0.15) / CYCLE

    text = ROLES[role_idx]
    n = max(len(text), 1)
    tspans = []
    for i, ch in enumerate(text):
        frac = t_start + (t_end - t_start) * (i / n)
        kt = f"0;{frac:.5f};{frac + 0.002:.5f};{hold_end:.5f};{fade_end:.5f};1"
        body = "&#160;" if ch == " " else esc(ch)
        tspans.append(
            f'<tspan opacity="0">{body}'
            f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" keyTimes="{kt}"/></tspan>'
        )

    # Block cursor travels with the text instead of being positioned by an
    # assumed mono advance width, so it stays glued to the last glyph on every
    # platform's font stack.
    caret = (f'<tspan fill="{t["cy"]}">'
             f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
             f'values="0;0;1;1;0;0" keyTimes="0;{t_start:.5f};{t_start + 0.004:.5f};'
             f'{hold_end:.5f};{fade_end:.5f};1"/>'
             f'<tspan opacity="1">\u2588'
             f'<animate attributeName="opacity" dur="1.06s" repeatCount="indefinite" '
             f'values="1;1;0;0" keyTimes="0;0.5;0.51;1"/></tspan></tspan>')

    return (f'<text x="{NAME_X}" y="{ROLE_Y}" font-family="{MONO}" '
            f'font-size="{MONO_ROLE_SIZE}" fill="{t["muted"]}" xml:space="preserve">'
            f'{esc(PROMPT)}<tspan fill="{t["cy"]}">{"".join(tspans)}</tspan>{caret}</text>')


def tree_block(t: dict) -> str:
    """File-tree motif. Keys and values use fixed columns rather than padded
    spaces, so the values stay aligned whatever the viewer's mono font is."""
    x, col, y0 = 736, 856, 130.0
    lines = [
        None,
        ("├─ agents", "claude-code · codex · dsh", "cy"),
        ("├─ desktop", "tauri · egui · wasm", "vi"),
        ("└─ automation", "playwright · asyncio · camoufox", "pk"),
    ]
    rows = [
        f'<text x="{x}" y="{y0}" font-family="{MONO}" font-size="14" '
        f'fill="{t["dim"]}">jedeiah@github</text>'
    ]
    for i, row in enumerate(lines[1:], start=1):
        key, val, tone = row
        y = y0 + i * 28
        rows.append(f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="14" '
                    f'fill="{t["dim"]}">{esc(key)}</text>')
        rows.append(f'<text x="{col}" y="{y}" font-family="{MONO}" font-size="14" '
                    f'fill="{t[tone]}">{esc(val)}</text>')
    return "\n".join(rows)


def particles(t: dict) -> str:
    """A few slow drifting motes; deterministic so builds stay stable."""
    out = []
    seeds = [(168, 66, 3.0, 11), (410, 246, 2.2, 15), (612, 74, 1.8, 9),
             (905, 268, 2.6, 13), (1204, 96, 2.0, 17), (500, 300, 1.6, 12),
             (1050, 178, 2.4, 14)]
    for i, (px, py, r, dur) in enumerate(seeds):
        delay = -(i * 1.7)
        out.append(
            f'<circle cx="{px}" cy="{py}" r="{r}" fill="{t["cy"]}" opacity="0.0">'
            f'<animate attributeName="opacity" dur="{dur}s" begin="{delay}s" '
            f'repeatCount="indefinite" values="0;0.34;0" keyTimes="0;0.5;1"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'dur="{dur + 6}s" begin="{delay}s" repeatCount="indefinite" '
            f'values="0 0;0 -26;0 0"/></circle>'
        )
    return "\n".join(out)


def banner(theme_key: str) -> str:
    t = THEMES[theme_key]
    h = BANNER_H
    sweep_hi = 0.85 if theme_key == "dark" else 0.0
    name_grad = f"""<linearGradient id="nameFill" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['fg_strong']}"/>
  <stop offset="0.42" stop-color="{t['fg_strong']}"/>
  <stop offset="0.5" stop-color="{t['cy']}"/>
  <stop offset="0.58" stop-color="{t['fg_strong']}"/>
  <stop offset="1" stop-color="{t['fg_strong']}"/>
  <animate attributeName="x1" values="-1.2;1" dur="6.5s" repeatCount="indefinite"/>
  <animate attributeName="x2" values="-0.2;2" dur="6.5s" repeatCount="indefinite"/>
</linearGradient>
<linearGradient id="mono" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{t['cy']}" stop-opacity="{0.90 if theme_key == 'dark' else 1.0}"/>
  <stop offset="1" stop-color="{t['vi']}" stop-opacity="{0.95 if theme_key == 'dark' else 1.0}"/>
</linearGradient>
<linearGradient id="monoStroke" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{t['cy']}" stop-opacity="0.65"/>
  <stop offset="1" stop-color="{t['vi']}" stop-opacity="0.55"/>
</linearGradient>
<linearGradient id="divline" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{t['border']}" stop-opacity="0"/>
  <stop offset="0.5" stop-color="{t['border']}"/>
  <stop offset="1" stop-color="{t['border']}" stop-opacity="0"/>
</linearGradient>"""

    svg = [card_open(t, h, theme_key, name_grad, drift=True)]
    svg.append(particles(t))

    # monogram tile
    svg.append(f"""<rect x="64" y="104" width="104" height="104" rx="27" fill="url(#mono)"/>
<rect x="64.5" y="104.5" width="103" height="103" rx="26.5" fill="none"
      stroke="url(#monoStroke)" stroke-width="1"/>
<text x="116" y="176" font-family="{SANS}" font-size="54" font-weight="700"
      fill="#FFFFFF" text-anchor="middle" opacity="0.97">J</text>""")

    # name with animated sheen
    svg.append(f"""<text x="{NAME_X}" y="170" font-family="{SANS}" font-size="60" font-weight="700"
      letter-spacing="-1.2" fill="url(#nameFill)">Jedeiah</text>""")

    for idx in range(len(ROLES)):
        svg.append(typing_group(idx, t))

    svg.append(f"""<text x="{NAME_X}" y="248" font-family="{SANS}" font-size="14.5"
      fill="{t['muted']}">since 2018  ·  zh / en  ·  building agents that ship</text>""")

    svg.append(f'<path d="M 706 100 V 216" stroke="url(#divline)" stroke-width="1" fill="none"/>')
    svg.append(tree_block(t))

    svg.append(f'<rect x="0" y="{h - 3}" width="{W}" height="2.5" fill="url(#hair)" opacity="0.55"/>')
    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------
# overview panel
# --------------------------------------------------------------------------

# Grid origin must stay on a multiple of PITCH so the shared cell pattern lines
# up with the individually drawn active cells.
GRID_X, GRID_Y = 64, 80
PITCH, CELL = 16, 12
WEEKDAYS = ["", "Mon", "", "Wed", "", "Fri", ""]


def level(n: int, top: int) -> int:
    if n <= 0:
        return 0
    if top <= 1:
        return 4
    q = n / top
    if q <= 0.25:
        return 1
    if q <= 0.5:
        return 2
    if q <= 0.75:
        return 3
    return 4


def heatmap(t: dict, data: dict) -> tuple[str, str, int]:
    """Contribution heatmap: (defs, body, grid width)."""
    weeks = data["weeks"]
    counts = [d["n"] for wk in weeks for d in wk]
    top = max(counts) if counts else 1
    grid_w, grid_h = len(weeks) * PITCH, 7 * PITCH

    defs = (f'<pattern id="cell" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse">'
            f'<rect width="{CELL}" height="{CELL}" rx="3.2" fill="{t["cell0"]}"/></pattern>')

    body = [f'<rect x="{GRID_X}" y="{GRID_Y}" width="{grid_w}" height="{grid_h}" fill="url(#cell)"/>']

    # month labels, thinned so they never collide
    seen, last_x = None, -999.0
    for wi, wk in enumerate(weeks):
        if not wk:
            continue
        d = date.fromisoformat(wk[0]["d"])
        if d.month != seen:
            seen = d.month
            x = GRID_X + wi * PITCH
            if x - last_x >= PITCH * 3:
                last_x = x
                body.append(f'<text x="{x}" y="{GRID_Y - 14}" font-family="{MONO}" '
                            f'font-size="11" fill="{t["muted"]}">{d.strftime("%b")}</text>')

    # active cells reveal in a diagonal wave, newest day pulses
    newest = None
    for wi, wk in enumerate(weeks):
        for d in wk:
            if d["n"] <= 0:
                continue
            x, y = GRID_X + wi * PITCH, GRID_Y + d["w"] * PITCH
            begin = round(0.25 + (wi + d["w"] * 1.6) * 0.032, 3)
            body.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3.2" '
                f'fill="{t["cells"][level(d["n"], top) - 1]}" opacity="0">'
                f'<animate attributeName="opacity" values="0;1" dur="0.45s" '
                f'begin="{begin}s" fill="freeze"/></rect>'
            )
            if newest is None or d["d"] > newest[0]:
                newest = (d["d"], x, y)

    if newest:
        _, x, y = newest
        body.append(
            f'<rect x="{x - 1.6}" y="{y - 1.6}" width="{CELL + 3.2}" height="{CELL + 3.2}" '
            f'rx="4.6" fill="none" stroke="{t["cells"][3]}" stroke-width="1.2">'
            f'<animate attributeName="opacity" dur="2.6s" repeatCount="indefinite" '
            f'values="0.15;0.95;0.15"/></rect>'
        )

    for i, name in enumerate(WEEKDAYS):
        if name:
            body.append(f'<text x="{GRID_X - 10}" y="{GRID_Y + i * PITCH + 9.5}" '
                        f'font-family="{MONO}" font-size="10.5" fill="{t["muted"]}" '
                        f'text-anchor="end">{name}</text>')

    # legend, right-aligned to the grid's right edge
    ly, lx = GRID_Y + grid_h + 18, GRID_X + grid_w
    body.append(f'<text x="{lx - 114}" y="{ly + 9.5}" font-family="{MONO}" font-size="11" '
                f'fill="{t["muted"]}" text-anchor="end">less</text>')
    for i in range(5):
        fill = t["cell0"] if i == 0 else t["cells"][i - 1]
        body.append(f'<rect x="{lx - 108 + i * (CELL + 4)}" y="{ly}" width="{CELL}" '
                    f'height="{CELL}" rx="3.2" fill="{fill}"/>')
    body.append(f'<text x="{lx}" y="{ly + 9.5}" font-family="{MONO}" font-size="11" '
                f'fill="{t["muted"]}" text-anchor="end">more</text>')

    return defs, "\n".join(body), grid_w


def lang_bar(t: dict, data: dict, x: int, y: int, w: int) -> str:
    langs = data["langs"][:3]
    if not langs:
        return ""
    palette = [t["cy"], t["vi"], t["pk"]]
    total = sum(c for _, c in langs) or 1
    out, cx = [], x
    for i, (_, c) in enumerate(langs):
        seg = w * (c / total)
        out.append(f'<rect x="{cx:.1f}" y="{y}" width="{max(seg - 4, 3):.1f}" height="6" rx="3" '
                   f'fill="{palette[i]}"/>')
        cx += seg
    legend = " · ".join(f"{esc(n)} {round(c / total * 100)}%" for n, c in langs)
    out.append(f'<text x="{x + w}" y="{y + 22}" font-family="{MONO}" font-size="10.5" '
               f'fill="{t["muted"]}" text-anchor="end">{legend}</text>')
    return "\n".join(out)


def overview(theme_key: str, data: dict) -> str:
    t = THEMES[theme_key]
    h = OVERVIEW_H
    defs, grid, grid_w = heatmap(t, data)

    divider_x = GRID_X + grid_w + 32
    block_l, block_r = divider_x + 26, W - 64

    extra = (f'<linearGradient id="bignum" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{t["cy"]}"/>'
             f'<stop offset="1" stop-color="{t["vi"]}"/></linearGradient>'
             f'<linearGradient id="vline" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{t["border"]}" stop-opacity="0"/>'
             f'<stop offset="0.5" stop-color="{t["border"]}"/>'
             f'<stop offset="1" stop-color="{t["border"]}" stop-opacity="0"/></linearGradient>'
             + defs)

    svg = [card_open(t, h, theme_key, extra)]
    svg.append(grid)
    svg.append(f'<path d="M {divider_x} 56 V 216" stroke="url(#vline)" stroke-width="1" fill="none"/>')

    svg.append(f"""<text x="{block_r}" y="104" font-family="{SANS}" font-size="42" font-weight="700"
      fill="url(#bignum)" text-anchor="end">{data['total_contrib']:,}</text>
<text x="{block_r}" y="128" font-family="{MONO}" font-size="11.5" fill="{t['muted']}"
      text-anchor="end">contributions · last 12 months</text>
<path d="M {block_l} 148 H {block_r}" stroke="{t['border']}" stroke-width="1" fill="none"/>
<text x="{block_r}" y="176" font-family="{MONO}" font-size="12" fill="{t['fg']}"
      text-anchor="end">{data['repos']} repos · {data['stars']} stars · {data['followers']} followers</text>""")

    svg.append(lang_bar(t, data, block_l, 194, block_r - block_l))

    svg.append(f"""<text x="{GRID_X}" y="42" font-family="{MONO}" font-size="11.5"
      letter-spacing="2.4" fill="{t['muted']}">ACTIVITY</text>
<text x="{block_r}" y="42" font-family="{MONO}" font-size="11.5" fill="{t['dim']}"
      text-anchor="end">updated {data['fetched']}</text>""")

    svg.append(f'<rect x="0" y="{h - 3}" width="{W}" height="2.5" fill="url(#hair)" opacity="0.4"/>')
    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="render from data/profile.json")
    args = ap.parse_args()

    data = load(args.cached)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for key in ("dark", "light"):
        for name, svg in (("banner", banner(key)), ("overview", overview(key, data))):
            try:
                ElementTree.fromstring(svg)
            except ElementTree.ParseError as exc:
                print(f"ERROR: {name}-{key}.svg is not valid XML: {exc}", file=sys.stderr)
                return 1
            (ASSETS / f"{name}-{key}.svg").write_text(svg)
            print(f"wrote {name}-{key}.svg")
    print(f"data: {data['repos']} repos · {data['stars']} stars · "
          f"{data['total_contrib']} contributions · top lang {data['langs'][:1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
