#!/usr/bin/env python3
"""Render the SVG assets for the Jedeiah profile README.

Aesthetic: CRT terminal / neon HUD.  Everything is drawn locally from live
GitHub data, so the profile carries no third-party widget dependency.

Outputs, per theme:

    assets/banner-{dark,light}.svg    terminal-window masthead
    assets/stack-{dark,light}.svg     technology chips
    assets/activity-{dark,light}.svg  contribution grid + scope trace

Usage:
    python3 tools/build.py            # fetch live data, render, write assets
    python3 tools/build.py --cached   # render from data/profile.json only
"""

from __future__ import annotations

import argparse
import html
import json
import pathlib
import subprocess
import sys
from datetime import date, datetime, timezone
from xml.etree import ElementTree

LOGIN = "Jedeiah"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data" / "profile.json"
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


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

QUERY = """
query($login: String!) {
  user(login: $login) {
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
    cal = raw["contributionsCollection"]["contributionCalendar"]

    weeks = []
    for wk in cal["weeks"]:
        days = sorted(wk["contributionDays"], key=lambda d: d["weekday"])
        weeks.append([{"d": d["date"], "n": d["contributionCount"], "w": d["weekday"]}
                      for d in days])

    return {
        "total_contrib": cal["totalContributions"],
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
# shared chrome
# --------------------------------------------------------------------------

def corner(x: float, y: float, dx: float, dy: float, arm: float = 16) -> str:
    """One L-shaped HUD bracket; dx/dy pick which corner and which way it opens."""
    ox, oy = (arm * dx, arm * dy)
    return (f'M {x} {y + oy} L {x} {y} L {x + ox} {y}')


def chrome(t: dict, h: int, extra: str = "") -> str:
    """Panel shell: inset background, HUD brackets, scanlines, neon hairline."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img">
<defs>
<clipPath id="card"><rect width="{W}" height="{h}" rx="{RADIUS}"/></clipPath>
<linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['cyan']}" stop-opacity="0"/>
  <stop offset="0.5" stop-color="{t['cyan']}" stop-opacity="0.9"/>
  <stop offset="1" stop-color="{t['magenta']}" stop-opacity="0"/>
  <animate attributeName="x1" values="-0.5;1" dur="7.5s" repeatCount="indefinite"/>
  <animate attributeName="x2" values="0;1.5" dur="7.5s" repeatCount="indefinite"/>
</linearGradient>
<linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{t['cyan']}"/>
  <stop offset="1" stop-color="{t['magenta']}"/>
</linearGradient>
<pattern id="field" width="48" height="48" patternUnits="userSpaceOnUse">
  <path d="M 48 0 V 48 M 0 48 H 48" stroke="{t['grid']}" stroke-width="1" fill="none"/>
</pattern>
<pattern id="scan" width="4" height="12" patternUnits="userSpaceOnUse">
  <rect width="4" height="2" fill="{t['scan']}" opacity="{t['scan_op']}"/>
</pattern>
<filter id="soft" x="-15%" y="-15%" width="130%" height="130%">
  <feGaussianBlur stdDeviation="7"/>
</filter>
<filter id="tight" x="-60%" y="-60%" width="220%" height="220%">
  <feGaussianBlur stdDeviation="2.4"/>
</filter>
{extra}
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{h}" fill="{t['panel']}"/>
<rect width="{W}" height="{h}" fill="url(#field)" opacity="0.55"/>
<rect width="{W}" height="{h}" fill="url(#scan)"/>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="{RADIUS}" fill="none"
      stroke="{t['border']}" stroke-width="1"/>
{''.join(f'<path d="{corner(x, y, dx, dy)}" stroke="{t["cyan"]}" stroke-opacity="0.55" '
         f'stroke-width="1.5" fill="none"/>'
         for x, y, dx, dy in ((1, 1, 1, 1), (W - 1, 1, -1, 1),
                              (1, h - 1, 1, -1), (W - 1, h - 1, -1, -1)))}
<rect x="0" y="{h - 2.5}" width="{W}" height="1.5" fill="url(#hair)"/>
"""


# --------------------------------------------------------------------------
# banner
# --------------------------------------------------------------------------

NAME = "JEDEIAH"
NAME_X, NAME_Y, NAME_SIZE = 56, 168, 84

ROLES = [
    "plugins that make coding agents actually useful",
    "local-first desktop apps · rust / tauri / egui",
    "network plumbing · proxies, protocols, packets",
    "automation · browsers, pipelines, data",
]
CYCLE = 20.0
PROMPT = "~ $ "
TYPE_X, TYPE_Y, TYPE_SIZE = 58, 216, 19

FOCUS = ["AGENTS", "DESKTOP", "NETWORK", "SECURITY", "AUTOMATION"]


def glitch_name(t: dict) -> str:
    """Chromatic-aberration wordmark: cyan and magenta plates that jitter."""
    common = (f'font-family="{MONO}" font-size="{NAME_SIZE}" font-weight="700" '
              f'letter-spacing="5"')
    plates = []
    for tone, dx, dy, dur, phase in (("cyan", -3.4, -2, 5.3, 0),
                                     ("magenta", 3.4, 2, 4.1, 1.7)):
        plates.append(
            f'<g opacity="0.85"><animateTransform attributeName="transform" '
            f'type="translate" dur="{dur}s" begin="{-phase}s" repeatCount="indefinite" '
            f'calcMode="discrete" values="0 0;0 0;0 0;0 0;0 0;{-dx * 2:.1f} {-dy:.1f};'
            f'0 0;0 0;{dx:.1f} {dy:.1f};0 0;0 0;0 0" '
            f'keyTimes="0;0.18;0.36;0.54;0.66;0.70;0.74;0.80;0.84;0.88;0.94;1"/>'
            f'<text x="{NAME_X + dx:.1f}" y="{NAME_Y + dy:.1f}" {common} '
            f'fill="{t[tone]}">{NAME}</text></g>'
        )
    return (f'<g filter="url(#soft)" opacity="{t["glow_op"]}">'
            f'<text x="{NAME_X}" y="{NAME_Y}" {common} fill="{t["cyan"]}">{NAME}</text></g>'
            + "".join(plates)
            + f'<text x="{NAME_X}" y="{NAME_Y}" {common} fill="{t["ink_hi"]}">{NAME}</text>')


def typing_line(t: dict) -> str:
    """One line that retypes a different focus phrase every 5 seconds."""
    slot = CYCLE / len(ROLES)
    out = []
    for idx, text in enumerate(ROLES):
        a = idx * slot
        t_start = (a + 0.25) / CYCLE
        t_end = (a + 1.75) / CYCLE
        hold = (a + slot - 0.35) / CYCLE
        fade = (a + slot - 0.05) / CYCLE

        n = max(len(text), 1)
        chars = []
        for i, ch in enumerate(text):
            frac = t_start + (t_end - t_start) * (i / n)
            chars.append(
                f'<tspan opacity="0">{"&#160;" if ch == " " else esc(ch)}'
                f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
                f'values="0;0;1;1;0;0" keyTimes="0;{frac:.5f};{frac + 0.002:.5f};'
                f'{hold:.5f};{fade:.5f};1"/></tspan>'
            )
        # The block cursor sits at the end of the line, so it only appears once
        # the line has finished typing — otherwise it hangs in the gap ahead of
        # the revealed characters.
        caret = (f'<tspan fill="{t["cyan"]}">'
                 f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
                 f'values="0;0;0;1;1;0;0" keyTimes="0;{t_end:.5f};{t_end + 0.004:.5f};'
                 f'{t_end + 0.008:.5f};{hold:.5f};{fade:.5f};1"/>'
                 f'<tspan opacity="1">\u258A<animate attributeName="opacity" dur="1.02s" '
                 f'repeatCount="indefinite" values="1;1;0;0" keyTimes="0;0.5;0.51;1"/>'
                 f'</tspan></tspan>')
        out.append(f'<text x="{TYPE_X}" y="{TYPE_Y}" font-family="{MONO}" '
                   f'font-size="{TYPE_SIZE}" fill="{t["muted"]}" xml:space="preserve">'
                   f'{esc(PROMPT)}<tspan fill="{t["cyan"]}">{"".join(chars)}</tspan>'
                   f'{caret}</text>')
    return "\n".join(out)


def monitor(t: dict) -> str:
    """Neon level meters, one per focus area."""
    x, bar_x, bar_w = 742, 900, 320
    rows = []
    rows.append(f'<text x="{x}" y="112" font-family="{MONO}" font-size="13" '
                f'letter-spacing="2.6" fill="{t["muted"]}">// FOCUS</text>')
    for i, label in enumerate(FOCUS):
        y = 148 + i * 30
        pulses = [0.62, 0.86, 0.74, 0.95, 0.68, 0.90, 0.62]
        vals = ";".join(f"{bar_w * pulses[(i * 2 + k) % len(pulses)]:.0f}" for k in range(len(pulses)))
        rows.append(
            f'<text x="{x}" y="{y + 10}" font-family="{MONO}" font-size="14.5" '
            f'fill="{t["cyan"]}" letter-spacing="1.4">{label}</text>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{bar_w}" height="7" rx="3.5" '
            f'fill="{t["grid"]}"/>'
            f'<rect x="{bar_x}" y="{y + 2}" width="{bar_w * 0.7:.0f}" height="7" rx="3.5" '
            f'fill="url(#neon)" opacity="0.9">'
            f'<animate attributeName="width" dur="{5.5 + i * 0.7:.1f}s" '
            f'repeatCount="indefinite" values="{vals}" '
            f'keyTimes="0;0.16;0.32;0.48;0.64;0.82;1"/></rect>'
            f'<rect x="{bar_x + bar_w - 3}" y="{y + 2}" width="3" height="7" rx="1.5" '
            f'fill="{t["cyan"]}" opacity="0.5"/>'
        )
    return "\n".join(rows)


def banner(theme: str) -> str:
    t = THEMES[theme]
    h = 352
    svg = [chrome(t, h)]
    svg.append(f'<g clip-path="url(#card)">')
    # title bar
    svg.append(f'<rect width="{W}" height="38" fill="{t["inset"]}" opacity="0.7"/>'
               f'<path d="M 0 38 H {W}" stroke="{t["border"]}" stroke-width="1" fill="none"/>')
    for i, tone in enumerate(("magenta", "amber", "cyan")):
        svg.append(f'<circle cx="{26 + i * 21}" cy="19" r="4.6" fill="{t[tone]}" '
                   f'opacity="0.85"/>')
    svg.append(f'<text x="{110}" y="24" font-family="{MONO}" font-size="13" '
               f'fill="{t["muted"]}">jedeiah@github&#160;—&#160;~</text>')
    svg.append(f'<text x="{W - 26}" y="24" font-family="{MONO}" font-size="13" '
               f'fill="{t["dim"]}" text-anchor="end">zsh</text>')
    svg.append('</g>')

    svg.append(glitch_name(t))
    svg.append(typing_line(t))
    svg.append(f'<text x="{TYPE_X}" y="256" font-family="{SANS}" font-size="16.5" '
               f'fill="{t["muted"]}">protocols&#160;&#160;·&#160;&#160;proxies'
               f'&#160;&#160;·&#160;&#160;agents&#160;&#160;·&#160;&#160;automation</text>')

    svg.append(f'<path d="M 706 88 V 296" stroke="{t["border"]}" stroke-width="1" fill="none"/>')
    svg.append(monitor(t))

    # terminal status bar, the way a real prompt would close out
    svg.append(f'<path d="M 0 308 H {W}" stroke="{t["border"]}" stroke-width="1" fill="none"/>'
               f'<text x="{TYPE_X}" y="332" font-family="{MONO}" font-size="13" '
               f'fill="{t["dim"]}">~/profile&#160;&#160;&#160;main</text>'
               f'<text x="{W - 26}" y="332" font-family="{MONO}" font-size="12" '
               f'fill="{t["dim"]}" text-anchor="end">UTF-8&#160;&#160;·&#160;&#160;LF'
               f'&#160;&#160;·&#160;&#160;100%</text>')
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
    t = THEMES[theme]
    h = 168
    svg = [chrome(t, h)]
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
                f'<rect x="{x:.1f}" y="{y}" width="3" height="{CHIP_H}" rx="1.5" '
                f'fill="{t["cyan"]}" opacity="0.75"/>'
                + icon_markup(icons, slug, x + CHIP_PAD, y + (CHIP_H - ICON) / 2, t["cyan"])
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
# activity panel
# --------------------------------------------------------------------------

GRID_X, GRID_Y = 56, 92
PITCH, CELL = 16, 12
SCOPE_Y, SCOPE_H = 246, 54
WEEKDAYS = ["", "Mon", "", "Wed", "", "Fri", ""]


def level(n: int, top: int) -> int:
    if n <= 0:
        return 0
    if top <= 1:
        return 4
    q = n / top
    return 1 if q <= 0.25 else 2 if q <= 0.5 else 3 if q <= 0.75 else 4


def heatmap(t: dict, data: dict) -> tuple[str, str, float]:
    weeks = data["weeks"]
    top = max((d["n"] for wk in weeks for d in wk), default=1)
    grid_w, grid_h = len(weeks) * PITCH, 7 * PITCH

    defs = (f'<pattern id="cell" width="{PITCH}" height="{PITCH}" patternUnits="userSpaceOnUse">'
            f'<rect width="{CELL}" height="{CELL}" rx="2.6" fill="{t["cell0"]}"/></pattern>'
            f'<clipPath id="gclip"><rect x="{GRID_X}" y="{GRID_Y}" width="{grid_w}" '
            f'height="{grid_h}"/></clipPath>'
            f'<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{t["cyan"]}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{t["cyan"]}" stop-opacity="{t["beam_op"]}"/>'
            f'<stop offset="1" stop-color="{t["cyan"]}" stop-opacity="0"/></linearGradient>')

    body = [f'<rect x="{GRID_X}" y="{GRID_Y}" width="{grid_w}" height="{grid_h}" '
            f'fill="url(#cell)"/>']

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
                body.append(f'<text x="{x}" y="{GRID_Y - 12}" font-family="{MONO}" '
                            f'font-size="12" fill="{t["muted"]}">{d.strftime("%b")}</text>')

    lit, halos = [], []
    for wi, wk in enumerate(weeks):
        for d in wk:
            if d["n"] <= 0:
                continue
            x, y = GRID_X + wi * PITCH, GRID_Y + d["w"] * PITCH
            colour = t["cells"][level(d["n"], top) - 1]
            lit.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.6" '
                       f'fill="{colour}"/>')
            halos.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.6" '
                         f'fill="{colour}"/>')
    body.append(f'<g filter="url(#tight)" opacity="0.7">{"".join(halos)}</g>')
    body.append("".join(lit))

    # newest day gets a pulsing reticle
    newest = max((d for wk in weeks for d in wk), key=lambda d: d["d"], default=None)
    if newest:
        wi = next(i for i, wk in enumerate(weeks) if any(d["d"] == newest["d"] for d in wk))
        x, y = GRID_X + wi * PITCH, GRID_Y + newest["w"] * PITCH
        body.append(f'<rect x="{x - 3}" y="{y - 3}" width="{CELL + 6}" height="{CELL + 6}" '
                    f'rx="4" fill="none" stroke="{t["cyan"]}" stroke-width="1.2">'
                    f'<animate attributeName="opacity" dur="2.2s" repeatCount="indefinite" '
                    f'values="0.2;1;0.2"/></rect>')

    for i, label in enumerate(WEEKDAYS):
        if label:
            body.append(f'<text x="{GRID_X - 10}" y="{GRID_Y + i * PITCH + 9.5}" '
                        f'font-family="{MONO}" font-size="11.5" fill="{t["muted"]}" '
                        f'text-anchor="end">{label}</text>')

    # sweeping scan beam, clipped to the grid
    body.append(f'<g clip-path="url(#gclip)">'
                f'<rect x="-140" y="{GRID_Y - 6}" width="140" height="{grid_h + 12}" '
                f'fill="url(#beam)">'
                f'<animate attributeName="x" values="-140;{grid_w + 40}" dur="6.8s" '
                f'repeatCount="indefinite"/></rect></g>')

    # legend sits directly under the grid; the scope labels live on their own row
    lx, ly = GRID_X + grid_w, GRID_Y + grid_h + 8
    body.append(f'<text x="{lx - 114}" y="{ly + 9.5}" font-family="{MONO}" font-size="11" '
                f'fill="{t["muted"]}" text-anchor="end">less</text>')
    for i in range(5):
        fill = t["cell0"] if i == 0 else t["cells"][i - 1]
        body.append(f'<rect x="{lx - 108 + i * (CELL + 4)}" y="{ly}" width="{CELL}" '
                    f'height="{CELL}" rx="2.6" fill="{fill}"/>')
    body.append(f'<text x="{lx}" y="{ly + 9.5}" font-family="{MONO}" font-size="11" '
                f'fill="{t["muted"]}" text-anchor="end">more</text>')

    return defs, "\n".join(body), grid_w


def scope_trace(t: dict, data: dict, x: float, w: float) -> str:
    """Oscilloscope trace of daily volume: filled envelope plus self-drawing line.

    Daily rather than weekly — a year of weekly totals is mostly flat zeroes and
    reads as a straight line.
    """
    series = [d["n"] for wk in data["weeks"] for d in wk]
    peak = max(series) or 1
    step = w / max(len(series) - 1, 1)
    base = SCOPE_Y + SCOPE_H
    pts = [(x + i * step, base - 5 - (v / peak) * (SCOPE_H - 14)) for i, v in enumerate(series)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{x:.1f},{base} " + line + f" {x + w:.1f},{base}"
    length = 3400

    return (
        f'<path d="M {x} {base} H {x + w}" stroke="{t["grid"]}" stroke-width="1" fill="none"/>'
        f'<polygon points="{area}" fill="url(#scopeFill)"/>'
        f'<g filter="url(#tight)" opacity="{t["glow_op"]}">'
        f'<polyline points="{line}" fill="none" stroke="{t["cyan"]}" stroke-width="2.4" '
        f'stroke-linejoin="round" stroke-linecap="round"/></g>'
        f'<polyline points="{line}" fill="none" stroke="{t["cyan"]}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="{length}" '
        f'stroke-dashoffset="{length}">'
        f'<animate attributeName="stroke-dashoffset" from="{length}" to="0" dur="2.8s" '
        f'fill="freeze"/></polyline>'
        f'<text x="{x}" y="{SCOPE_Y - 6}" font-family="{MONO}" font-size="11.5" '
        f'fill="{t["dim"]}" letter-spacing="1.8">DAILY&#160;VOLUME</text>'
        f'<text x="{x + w}" y="{SCOPE_Y - 6}" font-family="{MONO}" font-size="11.5" '
        f'fill="{t["dim"]}" text-anchor="end" letter-spacing="1.2">MAX&#160;{peak}</text>'
    )


def activity(theme: str, data: dict) -> str:
    t = THEMES[theme]
    h = 330
    defs, grid, grid_w = heatmap(t, data)

    divider_x = GRID_X + grid_w + 36
    block_r = W - 56

    extra = defs + (
        f'<linearGradient id="vline" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t["border"]}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{t["border"]}"/>'
        f'<stop offset="1" stop-color="{t["border"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="scopeFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t["cyan"]}" stop-opacity="0.34"/>'
        f'<stop offset="1" stop-color="{t["cyan"]}" stop-opacity="0.02"/></linearGradient>')

    svg = [chrome(t, h, extra), grid]
    svg.append(scope_trace(t, data, GRID_X, grid_w))
    svg.append(f'<path d="M {divider_x} 72 V 288" stroke="url(#vline)" stroke-width="1" fill="none"/>')

    newest = max((d for wk in data["weeks"] for d in wk), key=lambda d: d["n"], default=None)
    svg.append(f"""<text x="{block_r}" y="170" font-family="{MONO}" font-size="66" font-weight="700"
      fill="url(#neon)" text-anchor="end">{data['total_contrib']:,}</text>
<text x="{block_r}" y="196" font-family="{MONO}" font-size="13" fill="{t['muted']}"
      text-anchor="end" letter-spacing="1.4">CONTRIBUTIONS / 12 MO</text>
<path d="M {divider_x + 26} 220 H {block_r}" stroke="{t['border']}" stroke-width="1" fill="none"/>
<text x="{block_r}" y="248" font-family="{MONO}" font-size="13" fill="{t['dim']}"
      text-anchor="end" letter-spacing="1.2">PEAK DAY</text>
<text x="{block_r}" y="272" font-family="{MONO}" font-size="15.5" fill="{t['cyan']}"
      text-anchor="end">{newest['n'] if newest else 0} commits · {newest['d'] if newest else '—'}</text>""")

    svg.append(f"""<text x="{GRID_X}" y="48" font-family="{MONO}" font-size="13"
      letter-spacing="2.6" fill="{t['muted']}">// ACTIVITY</text>
<circle cx="{GRID_X + 132}" cy="44" r="4" fill="{t['magenta']}">
  <animate attributeName="opacity" dur="1.6s" repeatCount="indefinite" values="1;0.15;1"/>
</circle>
<text x="{GRID_X + 144}" y="48" font-family="{MONO}" font-size="11.5" fill="{t['dim']}"
      letter-spacing="1.6">LIVE</text>
<text x="{block_r}" y="48" font-family="{MONO}" font-size="11.5" fill="{t['dim']}"
      text-anchor="end">updated {data['fetched']}</text>""")

    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="render from data/profile.json")
    args = ap.parse_args()

    data = load(args.cached)
    icons = json.loads(ICONS.read_text()) if ICONS.exists() else {}
    if not icons:
        print("warning: data/icons.json missing, chips will render without glyphs",
              file=sys.stderr)

    ASSETS.mkdir(parents=True, exist_ok=True)
    for key in ("dark", "light"):
        for name, svg in (("banner", banner(key)),
                          ("stack", stack(key, icons)),
                          ("activity", activity(key, data))):
            try:
                ElementTree.fromstring(svg)
            except ElementTree.ParseError as exc:
                print(f"ERROR: {name}-{key}.svg is not valid XML: {exc}", file=sys.stderr)
                return 1
            (ASSETS / f"{name}-{key}.svg").write_text(svg)
            print(f"wrote {name}-{key}.svg")
    print(f"data: {data['total_contrib']} contributions · {data['fetched']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
