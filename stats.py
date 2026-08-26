#!/usr/bin/env python3
"""Erzeugt die Profil-Karten (SVG) aus allen eigenen Repos, auch privaten.
Braucht nur ein eingeloggtes `gh`. Aufruf: python3 stats.py"""
import json, subprocess, collections, datetime

USER = "sami-mag07"

def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout

def graphql(query):
    return json.loads(gh("api", "graphql", "-f", f"query={query}"))["data"]

# Repos ohne Forks
repos = [r["name"] for r in json.loads(gh("repo", "list", USER, "--limit", "100", "--json", "name,isFork")) if not r["isFork"]]

# Sprachen nach Bytes ueber alle Repos
langs = collections.Counter()
for r in repos:
    try:
        for k, v in json.loads(gh("api", f"repos/{USER}/{r}/languages")).items():
            langs[k] += v
    except subprocess.CalledProcessError:
        pass
total_bytes = sum(langs.values()) or 1
top = langs.most_common(5)

# Beitraege dieses Jahr und eigene Commits ueber alle Repos
viewer = graphql("{ viewer { id } }")["viewer"]["id"]
cal = graphql("{ viewer { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { contributionCount } } } } } }")
cal = cal["viewer"]["contributionsCollection"]["contributionCalendar"]
contributions = cal["totalContributions"]
active_days = sum(1 for w in cal["weeks"] for d in w["contributionDays"] if d["contributionCount"] > 0)
parts = " ".join(
    f'r{i}: repository(owner:"{USER}", name:"{r}") {{ defaultBranchRef {{ target {{ ... on Commit {{ history(author:{{id:"{viewer}"}}) {{ totalCount }} }} }} }} }}'
    for i, r in enumerate(repos))
hist = graphql("{ " + parts + " }")
commits = sum((v or {}).get("defaultBranchRef", {}).get("target", {}).get("history", {}).get("totalCount", 0) for v in hist.values() if v and v.get("defaultBranchRef"))

COLORS = {"TypeScript": "#3178c6", "Python": "#3572A5", "JavaScript": "#f1e05a", "HTML": "#e34c26",
          "CSS": "#663399", "Shell": "#89e051", "Dockerfile": "#384d54", "Astro": "#ff5a03"}
THEMES = {
    "dark":  {"bg": "#0d1117", "border": "#30363d", "title": "#58a6ff", "text": "#c9d1d9", "muted": "#8b949e", "track": "#21262d"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "title": "#0969da", "text": "#24292f", "muted": "#57606a", "track": "#eaeef2"},
}
FONT = "font-family='-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif'"

def card(theme, title, body):
    t = THEMES[theme]
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='420' height='190' viewBox='0 0 420 190' {FONT}>"
            f"<rect x='0.5' y='0.5' width='419' height='189' rx='8' fill='{t['bg']}' stroke='{t['border']}'/>"
            f"<text x='24' y='38' font-size='18' font-weight='600' fill='{t['title']}'>{title}</text>{body}</svg>")

def langs_svg(theme):
    t = THEMES[theme]
    x, width, body = 24, 372, ""
    for name, b in top:  # gestapelter Balken
        w = width * b / total_bytes
        body += f"<rect x='{x:.1f}' y='56' width='{w:.1f}' height='10' fill='{COLORS.get(name, t['muted'])}'/>"
        x += w
    body += f"<rect x='24' y='56' width='372' height='10' rx='5' fill='none' stroke='{t['bg']}' stroke-width='3'/>"
    for i, (name, b) in enumerate(top):  # Legende in zwei Spalten
        cx, cy = 24 + (i % 2) * 190, 96 + (i // 2) * 30
        pct = 100 * b / total_bytes
        body += (f"<circle cx='{cx + 6}' cy='{cy - 4}' r='6' fill='{COLORS.get(name, t['muted'])}'/>"
                 f"<text x='{cx + 20}' y='{cy}' font-size='14' fill='{t['text']}'>{name}</text>"
                 f"<text x='{cx + 150}' y='{cy}' font-size='14' fill='{t['muted']}' text-anchor='end'>{pct:.0f}%</text>")
    return card(theme, "Languages across all repos", body)

def stats_svg(theme):
    t = THEMES[theme]
    year = datetime.date.today().year
    rows = [(f"Contributions {year}", contributions), ("Active days", active_days), ("Repositories", len(repos)), ("Languages", len(langs))]
    body = ""
    for i, (label, val) in enumerate(rows):
        y = 74 + i * 30
        body += (f"<text x='24' y='{y}' font-size='14' fill='{t['text']}'>{label}</text>"
                 f"<text x='396' y='{y}' font-size='14' font-weight='600' fill='{t['text']}' text-anchor='end'>{val:,}</text>".replace(",", "."))
    return card(theme, "Stats, private repos included", body)

for theme in THEMES:
    open(f"langs-{theme}.svg", "w").write(langs_svg(theme))
    open(f"stats-{theme}.svg", "w").write(stats_svg(theme))
print(f"repos={len(repos)} commits={commits} contributions={contributions} active_days={active_days}")
print(" ".join(f"{n}={100*b/total_bytes:.0f}%" for n, b in top))
