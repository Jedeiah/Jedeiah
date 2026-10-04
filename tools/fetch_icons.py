#!/usr/bin/env python3
"""Cache the simple-icons path data used by the stack chips.

Icons are fetched once and committed to data/icons.json so that asset builds
stay offline-reproducible.
"""

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "icons.json"

SLUGS = ["rust", "python", "typescript", "javascript", "go", "openjdk",
         "tauri", "react", "vuedotjs", "postgresql", "sqlite", "redis"]

PATH_RE = re.compile(r'<path d="([^"]+)"')


def main() -> int:
    icons = {}
    for slug in SLUGS:
        # The CDN drops urllib connections, so fetch through curl.
        svg = subprocess.run(
            ["curl", "-fsSL", f"https://cdn.simpleicons.org/{slug}"],
            capture_output=True, text=True, check=True,
        ).stdout
        match = PATH_RE.search(svg)
        if not match:
            print(f"!! no path in {slug}")
            continue
        icons[slug] = {"path": match.group(1)}
        print(f"{slug:<12} {len(match.group(1)):>6} bytes")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(icons, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)} ({len(icons)} icons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
