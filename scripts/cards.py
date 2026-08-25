#!/usr/bin/env python3
"""
cards.py — self-hosted stats and project cards

Usage:
  python cards.py --user samir-sah --out assets
  python cards.py --user samir-sah --out assets --token ghp_xxx
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

DARK_BG = "#0d1117"
LIGHT_BG = "#ffffff"
DARK_BORDER = "#30363d"
LIGHT_BORDER = "#d0d7de"
DARK_TEXT = "#e6edf3"
LIGHT_TEXT = "#24292f"
DARK_MUTED = "#8b949e"
LIGHT_MUTED = "#656d76"
ACCENT = "#58a6ff"
ACCENT_DARK = "#79c0ff"
LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#2b7489", "Python": "#3572A5",
    "Java": "#b07219", "HTML": "#e34c26", "CSS": "#563d7c",
    "Go": "#00ADD8", "Rust": "#dea584", "C++": "#f34b7d",
    "C": "#555555", "Shell": "#89e051", "Vue": "#41b883",
    "PHP": "#4F5D95", "Ruby": "#701516", "Swift": "#ffac45",
    "Kotlin": "#A97BFF", "Dart": "#00B4AB", "Scala": "#c22d40",
}

def parse_args():
    p = argparse.ArgumentParser(description="Generate stat and project card SVGs")
    p.add_argument("--user", required=True, help="GitHub username")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--token", help="GitHub token (optional, for higher rate limits + private stats)")
    return p.parse_args()

def fetch_json(url, token=None):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def fetch_user_stats(username, token):
    user = fetch_json(f"https://api.github.com/users/{username}", token)
    if not user:
        return None
    
    repos = []
    page = 1
    while True:
        page_repos = fetch_json(f"https://api.github.com/users/{username}/repos?per_page=100&page={page}&type=public", token)
        if not page_repos:
            break
        repos.extend(page_repos)
        if len(page_repos) < 100:
            break
        page += 1
    
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)
    
    lang_bytes = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        langs = fetch_json(repo["languages_url"], token)
        if langs:
            for lang, bytes_count in langs.items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + bytes_count
    
    top_lang = max(lang_bytes.items(), key=lambda x: x[1])[0] if lang_bytes else "—"
    
    contributions = None
    streak = None
    if token:
        try:
            query = """
            query($login: String!) {
              user(login: $login) {
                contributionsCollection {
                  totalCommitContributions
                  contributionCalendar {
                    totalContributions
                  }
                }
              }
            }
            """
            data = {"query": query, "variables": {"login": username}}
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=json.dumps(data).encode(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.load(resp)
            if "data" in result and result["data"]["user"]:
                cc = result["data"]["user"]["contributionsCollection"]
                contributions = cc.get("totalCommitContributions")
                streak = cc.get("contributionCalendar", {}).get("totalContributions")
        except Exception:
            pass
    
    return {
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "top_language": top_lang,
        "contributions": contributions,
        "streak": streak,
    }

def fetch_repo_details(username, repo_name, token):
    """Fetch details for a specific repo."""
    return fetch_json(f"https://api.github.com/repos/{username}/{repo_name}", token)

def generate_stat_card(stats, token, dark=True):
    """Generate stats card SVG."""
    bg = DARK_BG if dark else LIGHT_BG
    border = DARK_BORDER if dark else LIGHT_BORDER
    text = DARK_TEXT if dark else LIGHT_TEXT
    muted = DARK_MUTED if dark else LIGHT_MUTED
    accent = ACCENT_DARK if dark else ACCENT
    
    has_token = token is not None
    cols = 6 if has_token else 3
    card_w = 160 * cols + 24
    card_h = 120
    
    stat_items = [
        ("Repositories", stats["public_repos"], "📦"),
        ("Followers", stats["followers"], "👥"),
        ("Following", stats["following"], "👤"),
    ]
    if has_token:
        stat_items.extend([
            ("Stars", stats["total_stars"], "⭐"),
            ("Forks", stats["total_forks"], "🍴"),
            ("Contributions", stats["contributions"] or "—", "📈"),
        ])
    else:
        stat_items.extend([
            ("Stars", stats["total_stars"], "⭐"),
            ("Forks", stats["total_forks"], "🍴"),
            ("Top Language", stats["top_language"], "💻"),
        ])
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {card_w} {card_h}" width="{card_w}" height="{card_h}">')
    svg.append(f'<rect width="{card_w}" height="{card_h}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>')
    
    col_w = card_w / cols
    for i, (label, value, icon) in enumerate(stat_items):
        x = 12 + i * col_w
        col_center = x + col_w / 2
        
        svg.append(f'<text x="{col_center}" y="32" text-anchor="middle" font-size="20" fill="{text}" font-family="system-ui, sans-serif">{icon}</text>')
        svg.append(f'<text x="{col_center}" y="60" text-anchor="middle" font-size="24" fill="{text}" font-family="system-ui, sans-serif" font-weight="600">{value}</text>')
        svg.append(f'<text x="{col_center}" y="86" text-anchor="middle" font-size="11" fill="{muted}" font-family="system-ui, sans-serif">{label}</text>')
        
        if i < cols - 1:
            line_x = x + col_w
            svg.append(f'<line x1="{line_x}" y1="20" x2="{line_x}" y2="100" stroke="{border}" stroke-width="1"/>')
    
    svg.append('</svg>')
    return "".join(svg)

def generate_project_card(repo_data, description, dark=True):
    """Generate project card SVG."""
    bg = DARK_BG if dark else LIGHT_BG
    border = DARK_BORDER if dark else LIGHT_BORDER
    text = DARK_TEXT if dark else LIGHT_TEXT
    muted = DARK_MUTED if dark else LIGHT_MUTED
    accent = ACCENT_DARK if dark else ACCENT
    
    card_w = 380
    card_h = 180
    
    name = repo_data.get("name", "Unknown")
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    lang = repo_data.get("language") or "—"
    lang_color = LANG_COLORS.get(lang, ACCENT)
    updated = repo_data.get("updated_at", "")
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            updated_str = dt.strftime("%b %Y")
        except:
            updated_str = ""
    else:
        updated_str = ""
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {card_w} {card_h}" width="{card_w}" height="{card_h}">')
    svg.append(f'<rect width="{card_w}" height="{card_h}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>')
    svg.append(f'<rect x="0" y="0" width="4" height="{card_h}" rx="8" ry="0" fill="{accent}"/>')
    
    # Title
    svg.append(f'<text x="16" y="28" font-size="16" fill="{text}" font-family="system-ui, sans-serif" font-weight="600">{name}</text>')
    
    # Description
    desc_lines = wrap_text(description, 48)
    for j, line in enumerate(desc_lines[:3]):
        svg.append(f'<text x="16" y="{48 + j * 18}" font-size="12" fill="{muted}" font-family="system-ui, sans-serif">{line}</text>')
    
    # Stats row
    y_stats = 130
    svg.append(f'<text x="16" y="{y_stats}" font-size="11" fill="{muted}" font-family="system-ui, sans-serif">⭐ {stars}</text>')
    svg.append(f'<text x="100" y="{y_stats}" font-size="11" fill="{muted}" font-family="system-ui, sans-serif">🍴 {forks}</text>')
    
    # Language dot
    dot_x = card_w - 80
    svg.append(f'<circle cx="{dot_x}" cy="{y_stats - 4}" r="5" fill="{lang_color}"/>')
    svg.append(f'<text x="{dot_x + 10}" y="{y_stats}" font-size="11" fill="{muted}" font-family="system-ui, sans-serif">{lang}</text>')
    
    if updated_str:
        svg.append(f'<text x="{card_w - 16}" y="{card_h - 12}" text-anchor="end" font-size="10" fill="{muted}" font-family="system-ui, sans-serif">Updated {updated_str}</text>')
    
    svg.append('</svg>')
    return "".join(svg)

def wrap_text(text, max_chars):
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + 1
    if current:
        lines.append(" ".join(current))
    return lines

def main():
    args = parse_args()
    token = args.token or os.environ.get("GITHUB_TOKEN")
    
    print(f"Fetching stats for {args.user}...", file=sys.stderr)
    stats = fetch_user_stats(args.user, token)
    if not stats:
        print("Failed to fetch user stats", file=sys.stderr)
        sys.exit(1)
    
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Stat cards
    for theme, suffix in [(True, "dark"), (False, "light")]:
        svg = generate_stat_card(stats, token, dark=theme)
        (out_dir / f"card-stats-{suffix}.svg").write_text(svg, encoding="utf-8")
    
    # Project cards
    with open("assets/projects.json") as f:
        projects = json.load(f)["projects"]
    
    for proj in projects[:4]:
        repo_slug = proj["repo"]
        if "/" in repo_slug:
            owner, repo_name = repo_slug.split("/", 1)
        else:
            owner, repo_name = args.user, repo_slug
        
        print(f"Fetching {repo_slug}...", file=sys.stderr)
        repo_data = fetch_repo_details(owner, repo_name, token)
        if not repo_data:
            repo_data = {"name": repo_name, "stargazers_count": 0, "forks_count": 0, "language": None, "updated_at": ""}
        
        for theme, suffix in [(True, "dark"), (False, "light")]:
            svg = generate_project_card(repo_data, proj["description"], dark=theme)
            safe_name = repo_name.replace("/", "-")
            (out_dir / f"card-project-{safe_name}-{suffix}.svg").write_text(svg, encoding="utf-8")
    
    print(f"Generated cards in {out_dir}")

if __name__ == "__main__":
    main()