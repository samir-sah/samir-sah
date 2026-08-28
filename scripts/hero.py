#!/usr/bin/env python3
"""Build the light and dark profile hero SVGs from the local portrait."""

import argparse
import base64
from html import escape
from pathlib import Path

THEMES = {
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d",
        "text": "#f0f6fc", "muted": "#8b949e", "accent": "#58a6ff",
        "grid": "#21262d",
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de",
        "text": "#1f2328", "muted": "#656d76", "accent": "#0969da",
        "grid": "#d8dee4",
    },
}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo", nargs="?", default="photo.png")
    parser.add_argument("--out", default="assets")
    return parser.parse_args()


def render(photo_uri, theme):
    c = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 360" role="img" aria-labelledby="title desc">
<title id="title">Samir Sah — full-stack engineering profile</title>
<desc id="desc">Portrait of Samir Sah beside a concise introduction and engineering focus.</desc>
<defs>
  <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="{c['grid']}" stroke-width="1"/></pattern>
  <clipPath id="portrait"><rect x="646" y="30" width="274" height="300" rx="28"/></clipPath>
  <linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{c['bg']}" stop-opacity=".08"/><stop offset="1" stop-color="{c['accent']}" stop-opacity=".20"/></linearGradient>
</defs>
<rect width="960" height="360" rx="24" fill="{c['bg']}"/>
<rect x="1" y="1" width="958" height="358" rx="23" fill="none" stroke="{c['border']}"/>
<path d="M590 1H936a23 23 0 0 1 23 23v312a23 23 0 0 1-23 23H540z" fill="url(#grid)" opacity=".62"/>
<circle cx="54" cy="57" r="5" fill="{c['accent']}"/><text x="70" y="63" fill="{c['muted']}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="15" letter-spacing="1.5">HELLO, I'M</text>
<text x="48" y="132" fill="{c['text']}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="54" font-weight="700">Samir Sah</text>
<text x="50" y="173" fill="{c['accent']}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="23" font-weight="600">Full-stack engineering · APIs · product systems</text>
<text x="50" y="218" fill="{c['muted']}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="17">Information Science Engineering at JSSATE Bengaluru</text>
<text x="50" y="246" fill="{c['muted']}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="17">B.E. · graduating May 2027</text>
<g font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14">
  <rect x="50" y="282" width="116" height="34" rx="17" fill="{c['panel']}" stroke="{c['border']}"/><text x="108" y="304" text-anchor="middle" fill="{c['text']}">MERN</text>
  <rect x="178" y="282" width="116" height="34" rx="17" fill="{c['panel']}" stroke="{c['border']}"/><text x="236" y="304" text-anchor="middle" fill="{c['text']}">Next.js</text>
  <rect x="306" y="282" width="116" height="34" rx="17" fill="{c['panel']}" stroke="{c['border']}"/><text x="364" y="304" text-anchor="middle" fill="{c['text']}">REST APIs</text>
</g>
<g clip-path="url(#portrait)"><image href="{escape(photo_uri, quote=True)}" x="646" y="30" width="274" height="345" preserveAspectRatio="xMidYMid slice"/><rect x="646" y="30" width="274" height="300" fill="url(#fade)"/></g>
<rect x="646" y="30" width="274" height="300" rx="28" fill="none" stroke="{c['accent']}" stroke-width="2"/>
<path d="M621 77h38M640 58v38M895 310h38M914 291v38" stroke="{c['accent']}" stroke-width="2" stroke-linecap="round"/>
</svg>'''


def main():
    args = arguments()
    photo = Path(args.photo)
    out = Path(args.out)
    if not photo.is_file():
        raise SystemExit(f"Portrait not found: {photo}")
    photo_bytes = photo.read_bytes()
    if photo_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif photo_bytes.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        raise SystemExit("Portrait must be a PNG or JPEG image")
    photo_uri = f"data:{mime};base64,{base64.b64encode(photo_bytes).decode('ascii')}"
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (out / f"hero-{theme}.svg").write_text(render(photo_uri, theme), encoding="utf-8", newline="\n")
        print(f"wrote {out / f'hero-{theme}.svg'}")


if __name__ == "__main__":
    main()
