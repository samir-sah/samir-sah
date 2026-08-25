#!/usr/bin/env python3
"""
radar.py — skill + language radar charts

Usage:
  python radar.py --data assets/skills.json -o assets/radar
  python radar.py --github samir-sah -o assets/radar-langs --limit 7 --values --curve 0.4 --exclude "shell,html,css,dockerfile,makefile,batchfile,procfile"
"""

import argparse
from html import escape
import json
import math
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

DARK_BG = "#0d1117"
LIGHT_BG = "#ffffff"
DARK_GRID = "#30363d"
LIGHT_GRID = "#d0d7de"
DARK_TEXT = "#e6edf3"
LIGHT_TEXT = "#24292f"
DARK_AXIS = "#8b949e"
LIGHT_AXIS = "#656d76"
ACCENT = "#58a6ff"
ACCENT_FILL_DARK = "rgba(88, 166, 255, 0.25)"
ACCENT_FILL_LIGHT = "rgba(88, 166, 255, 0.15)"


def positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def svg_text(value):
    return escape(str(value), quote=False)

def parse_args():
    p = argparse.ArgumentParser(description="Generate radar chart SVGs")
    p.add_argument("--data", help="Path to skills.json for self-rated radar")
    p.add_argument("--github", help="GitHub username for language radar")
    p.add_argument("-o", "--output", required=True, help="Output base path (will write -dark.svg and -light.svg)")
    p.add_argument("--limit", type=positive_int, default=7, help="Max languages to show (language radar)")
    p.add_argument("--values", action="store_true", help="Show values at each axis")
    p.add_argument("--curve", type=float, default=0.4, help="Power curve for language bytes (0.3-0.5)")
    p.add_argument("--exclude", type=str, default="", help="Comma-separated languages to exclude")
    p.add_argument("--title", type=str, default="", help="Override chart title")
    p.add_argument("--size", type=positive_int, default=400, help="SVG size (width/height)")
    return p.parse_args()

def fetch_github_languages(username):
    """Fetch language stats across all public repos for a user."""
    url = f"https://api.github.com/users/{username}/repos?per_page=100&type=public"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    all_langs = {}
    page = 1
    while True:
        paged_url = f"{url}&page={page}"
        req.full_url = paged_url
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                repos = json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"Error fetching repositories: {e}", file=sys.stderr)
            break
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            lang_url = repo["languages_url"]
            lang_req = urllib.request.Request(lang_url, headers={"Accept": "application/vnd.github.v3+json"})
            if token:
                lang_req.add_header("Authorization", f"Bearer {token}")
            try:
                with urllib.request.urlopen(lang_req, timeout=10) as resp:
                    langs = json.load(resp)
                for lang, bytes_count in langs.items():
                    all_langs[lang] = all_langs.get(lang, 0) + bytes_count
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                print(f"Error fetching languages for {repo.get('name', 'repository')}: {e}", file=sys.stderr)
        page += 1
        if page > 10:
            break
    return all_langs

def apply_curve(values, curve):
    """Apply power curve to normalize skewed distribution."""
    if curve <= 0 or curve >= 1:
        return values
    max_v = max(values.values()) if values else 1
    max_v = max_v or 1
    return {k: (v / max_v) ** curve * 100 for k, v in values.items()}

def normalize_to_100(values):
    """Scale values so max is 100."""
    max_v = max(values.values()) if values else 1
    max_v = max_v or 1
    return {k: (v / max_v) * 100 for k, v in values.items()}

def generate_radar_svg(axes, title, size, show_values, dark=True):
    """Generate radar chart SVG."""
    cx = cy = size / 2
    radius = size * 0.42
    n = len(axes)
    if n < 3:
        return ""
    
    bg = DARK_BG if dark else LIGHT_BG
    grid_color = DARK_GRID if dark else LIGHT_GRID
    text_color = DARK_TEXT if dark else LIGHT_TEXT
    axis_color = DARK_AXIS if dark else LIGHT_AXIS
    fill_color = ACCENT_FILL_DARK if dark else ACCENT_FILL_LIGHT
    stroke_color = ACCENT
    
    angle_step = 2 * math.pi / n
    start_angle = -math.pi / 2
    
    grid_levels = 4
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">')
    svg.append(f'<rect width="{size}" height="{size}" fill="{bg}"/>')
    
    # Grid polygons
    for level in range(1, grid_levels + 1):
        r = radius * level / grid_levels
        points = []
        for i in range(n):
            angle = start_angle + i * angle_step
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        svg.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="{grid_color}" stroke-width="1"/>')
    
    # Axis lines
    for i in range(n):
        angle = start_angle + i * angle_step
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{axis_color}" stroke-width="1"/>')
    
    # Data polygon
    points = []
    for i, axis in enumerate(axes):
        angle = start_angle + i * angle_step
        r = radius * axis["value"] / 100
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")
    svg.append(f'<polygon points="{" ".join(points)}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2"/>')
    
    # Axis labels
    label_radius = radius * 1.15
    for i, axis in enumerate(axes):
        angle = start_angle + i * angle_step
        x = cx + label_radius * math.cos(angle)
        y = cy + label_radius * math.sin(angle)
        dx = math.cos(angle)
        dy = math.sin(angle)
        anchor = "middle"
        if dx > 0.3:
            anchor = "start"
        elif dx < -0.3:
            anchor = "end"
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" font-size="{size*0.035}" fill="{text_color}" font-family="system-ui, sans-serif">{svg_text(axis["label"])}</text>')
    
    # Values at axes
    if show_values:
        for i, axis in enumerate(axes):
            angle = start_angle + i * angle_step
            r = radius * axis["value"] / 100
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            svg.append(f'<text x="{x:.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="{size*0.03}" fill="{stroke_color}" font-family="system-ui, sans-serif" font-weight="600">{axis["value"]}</text>')
    
    # Title
    if title:
        svg.append(f'<text x="{cx}" y="{size*0.06}" text-anchor="middle" font-size="{size*0.05}" fill="{text_color}" font-family="system-ui, sans-serif" font-weight="600">{svg_text(title)}</text>')
    
    svg.append('</svg>')
    return "".join(svg)

def main():
    args = parse_args()
    
    if args.data:
        with open(args.data) as f:
            data = json.load(f)
        axes = data["axes"]
        try:
            axes = [
                {"label": str(axis["label"]), "value": float(axis["value"])}
                for axis in axes
            ]
        except (KeyError, TypeError, ValueError):
            print("Each radar axis must include a label and numeric value", file=sys.stderr)
            sys.exit(1)
        if any(not 0 <= axis["value"] <= 100 for axis in axes):
            print("Radar values must be between 0 and 100", file=sys.stderr)
            sys.exit(1)
        title = args.title or data.get("title", "Skill Radar")
    elif args.github:
        print(f"Fetching language stats for {args.github}...", file=sys.stderr)
        langs = fetch_github_languages(args.github)
        exclude = set(args.exclude.lower().split(",")) if args.exclude else set()
        filtered = {k: v for k, v in langs.items() if k.lower() not in exclude}
        if not filtered:
            print("No languages found after exclusions", file=sys.stderr)
            sys.exit(1)
        curved = apply_curve(filtered, args.curve)
        normalized = normalize_to_100(curved)
        sorted_langs = sorted(normalized.items(), key=lambda x: -x[1])[:args.limit]
        axes = [{"label": k, "value": round(v)} for k, v in sorted_langs]
        title = args.title or "Language Radar"
    else:
        print("Either --data or --github required", file=sys.stderr)
        sys.exit(1)

    if len(axes) < 3:
        print("Radar charts require at least three axes", file=sys.stderr)
        sys.exit(1)
    
    dark_svg = generate_radar_svg(axes, title, args.size, args.values, dark=True)
    light_svg = generate_radar_svg(axes, title, args.size, args.values, dark=False)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.with_name(f"{output_path.name}-dark.svg").write_text(dark_svg, encoding="utf-8")
    output_path.with_name(f"{output_path.name}-light.svg").write_text(light_svg, encoding="utf-8")
    print(f"Generated {args.output}-dark.svg and {args.output}-light.svg")

if __name__ == "__main__":
    main()
