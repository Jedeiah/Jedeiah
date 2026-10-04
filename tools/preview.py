#!/usr/bin/env python3
"""Wrap GitHub's own rendered README fragment in a faithful-looking shell so the
layout can be eyeballed locally before anything is pushed.

    python3 tools/preview.py     ->  _preview/readme.html
"""

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_preview" / "readme.html"

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin:0; font: 16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",
       Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji";
       -webkit-font-smoothing: antialiased; }
.sheet { padding: 32px 0 80px; }
.sheet.dark  { background:#0d1117; color:#e6edf3; }
.sheet.light { background:#ffffff; color:#1f2328; }
.sheet.dark  { --bd:#30363d; --code:rgba(110,118,129,.4); --link:#4493f8; }
.sheet.light { --bd:#d1d9e0; --code:rgba(175,184,193,.2); --link:#0969da; }
.col { width:1012px; margin:0 auto; }
.tag { font:600 11px/1 ui-monospace,Menlo,monospace; letter-spacing:2px;
       text-transform:uppercase; opacity:.55; margin:0 0 16px; }
.markdown-body h1,.markdown-body h2 { padding-bottom:.3em; border-bottom:1px solid var(--bd); }
.markdown-body h2 { font-size:1.5em; margin:24px 0 16px; }
.markdown-body p { margin:0 0 16px; }
.markdown-body a { color:var(--link); text-decoration:none; }
.markdown-body a:hover { text-decoration:underline; }
.markdown-body strong { font-weight:600; }
.markdown-body code { padding:.2em .4em; font-size:85%; border-radius:6px;
                      background:var(--code); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
.markdown-body table { border-collapse:collapse; display:block; width:100%;
                       overflow:auto; margin:0 0 16px; font-size:14px; }
.markdown-body th,.markdown-body td { padding:6px 13px; border:1px solid var(--bd); }
.markdown-body th { font-weight:600; }
.markdown-body tr:nth-child(2n) td { background:color-mix(in srgb, currentColor 3%, transparent); }
.markdown-body img { max-width:100%; }
.markdown-body ul { padding-left:2em; margin:0 0 16px; }
.markdown-body li { margin-top:.25em; }
.markdown-body sub { font-size:75%; }
.markdown-body center,p[align="center"] { text-align:center; }
"""


def render() -> str:
    fragment = subprocess.run(
        ["gh", "api", "--method", "POST", "/markdown", "-F", "text=@README.md", "-F", "mode=gfm"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout

    # The preview page lives one directory below the repo root, so repo-relative
    # asset links have to be lifted a level to resolve here.  <source srcset>
    # wins over the <img> fallback, so both have to be rewritten.
    fragment = (fragment
                .replace('src="assets/', 'src="../assets/')
                .replace('srcset="assets/', 'srcset="../assets/'))

    sheets = []
    for theme in ("dark", "light"):
        body = fragment
        if theme == "light":
            # prefers-color-scheme is global to the page, so the light sheet
            # cannot win the <picture> negotiation on its own.  Dropping the
            # <source> elements forces the light <img> fallback instead.
            body = re.sub(r"<source[^>]*>", "", fragment)
        sheets.append(f"""<section class="sheet {theme}">
  <div class="col">
    <p class="tag">github {theme} · 1012px</p>
    <article class="markdown-body">{body}</article>
  </div>
</section>""")

    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>profile README preview</title>
<style>{CSS}</style></head>
<body>{''.join(sheets)}</body></html>"""


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render())
    print(f"wrote {OUT.relative_to(ROOT)}")
