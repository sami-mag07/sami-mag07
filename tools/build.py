import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT_DIR = Path(__file__).resolve().parent / ".fonts"
GF = "https://raw.githubusercontent.com/google/fonts/main/"

SITE = "https://spaeti.5.45.109.195.sslip.io"
LINKEDIN = "https://www.linkedin.com/in/sami-magdouli-35b0393a1"
MAIL = "mailto:Sami-mag@web.de"
GH = "https://github.com/sami-mag07/"

FONTS = {
    "anton": ("ofl/anton/Anton-Regular.ttf", None),
    "plex": ("ofl/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf", {"wght": 400, "wdth": 100}),
    "plexb": ("ofl/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf", {"wght": 600, "wdth": 100}),
    "neon": ("apache/yellowtail/Yellowtail-Regular.ttf", None),
}

THEMES = {
    "light": {
        "card": "#ffffff", "line": "#d0d7de", "ink": "#1f2328", "ink2": "#3d444d", "muted": "#59636e",
        "facade": "#e4ded3", "facade2": "#d6cfc2", "board": "#1c1c1f", "boardline": "#34343a",
        "shutter": "#a9adb3", "slat": "#8e9399", "housing": "#7d8288", "walk": "#bdb5a8", "curb": "#a39b8e",
        "interior": ("#3b342c", "#262220"), "glow": 0.35, "spill": 0.0, "glass": 0.10,
        "empty": "#eff1f3",
    },
    "dark": {
        "card": "#151b23", "line": "#3d444d", "ink": "#f0f6fc", "ink2": "#d1d7e0", "muted": "#9198a1",
        "facade": "#18181b", "facade2": "#0f0f11", "board": "#0c0c0d", "boardline": "#26262b",
        "shutter": "#3b3e43", "slat": "#2c2e32", "housing": "#26282c", "walk": "#0b0b0c", "curb": "#1d1d20",
        "interior": ("#3a2b1b", "#1d1610"), "glow": 0.7, "spill": 0.16, "glass": 0.05,
        "empty": "#212830",
    },
}

YELLOW = "#ffd60a"
ORANGE = "#ff5b24"
RED = "#e3262e"
PINK = "#ff4f9a"
BLACK = "#111111"


def font_path(key):
    url, axes = FONTS[key]
    FONT_DIR.mkdir(exist_ok=True)
    raw = FONT_DIR / url.split("/")[-1].replace("%5B", "[").replace("%5D", "]")
    if not raw.exists():
        urllib.request.urlretrieve(GF + url, raw)
    if not axes:
        return raw
    out = FONT_DIR / f"{key}.ttf"
    if not out.exists():
        instancer.instantiateVariableFont(TTFont(raw), axes).save(out)
    return out


class Font:
    def __init__(self, key):
        self.key = key
        self.path = font_path(key)
        self.tt = TTFont(self.path)
        self.upm = self.tt["head"].unitsPerEm
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(self.path))))
        self.paths = {}

    def shape(self, s):
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True, "calt": True})
        return [(i.codepoint, p.x_advance, p.x_offset, p.y_offset) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def width(self, s, size, spacing=0):
        g = self.shape(s)
        return sum(a for _, a, _, _ in g) * size / self.upm + spacing * max(len(g) - 1, 0)

    def fit(self, s, max_w, start, spacing=0):
        size = start
        while size > 8 and self.width(s, size, spacing) > max_w:
            size -= 0.5
        return size

    def wrap(self, s, size, max_w):
        lines, cur = [], ""
        for word in s.split():
            test = f"{cur} {word}".strip()
            if cur and self.width(test, size) > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = test
        if cur:
            lines.append(cur)
        return lines

    def outline(self, gid):
        if gid not in self.paths:
            pen = SVGPathPen(self.glyphs)
            self.glyphs[self.order[gid]].draw(pen)
            self.paths[gid] = pen.getCommands()
        return self.paths[gid]


F = {k: Font(k) for k in FONTS}


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.parts, self.defs, self.css = [], [], []
        self.used = set()

    def add(self, s):
        self.parts.append(s)

    def run(self, x, y, s, font, size, fill, anchor="start", spacing=0, attrs="", stroke=None, sw=0):
        f = F[font]
        k = size / f.upm
        w = f.width(s, size, spacing)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        uses, pen = [], 0
        for gid, adv, xo, yo in f.shape(s):
            if f.outline(gid):
                self.used.add((font, gid))
                uses.append(f'<use href="#{font}{gid}" x="{pen + xo:.0f}" y="{yo}"/>')
            pen += adv + spacing / k
        st = f' stroke="{stroke}" stroke-width="{sw / k:.1f}" stroke-linejoin="round"' if stroke else ""
        return f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.5f} {-k:.5f})" fill="{fill}"{st} {attrs}>{"".join(uses)}</g>'

    def text(self, *a, **kw):
        self.parts.append(self.run(*a, **kw))

    def render(self):
        glyphs = "".join(f'<path id="{font}{gid}" d="{F[font].outline(gid)}"/>' for font, gid in sorted(self.used))
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img">'
            f"<title>{escape(self.title)}</title><style>{''.join(self.css)}</style><defs>{glyphs}{''.join(self.defs)}</defs>"
            + "".join(self.parts)
            + "</svg>"
        )


def header(t, mode):
    W, H = 1200, 470
    s = Svg(W, H, "Samis Späti: a Berlin late-night shop front. The neon sign switches on, the shutter rolls up, and the poster in the window reads Sami Magdouli, software engineer in Berlin.")
    ix, iy, iw, ih = 48, 184, 1104, 246
    s.defs.append(
        f'<linearGradient id="fa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["facade"]}"/><stop offset="1" stop-color="{t["facade2"]}"/></linearGradient>'
        f'<linearGradient id="in" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["interior"][0]}"/><stop offset="1" stop-color="{t["interior"][1]}"/></linearGradient>'
        f'<radialGradient id="sp" cx="0.5" cy="0.2" r="0.6"><stop offset="0" stop-color="{PINK}" stop-opacity="{t["spill"]}"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="fr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7fcff"/><stop offset="1" stop-color="#cfe6f7"/></linearGradient>'
        '<radialGradient id="fg" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#dff1ff" stop-opacity="0.35"/><stop offset="1" stop-color="#dff1ff" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="gl" x1="0" y1="0" x2="1" y2="1"><stop offset="0.35" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="#fff" stop-opacity="{t["glass"]}"/><stop offset="0.62" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="win"><rect x="{ix}" y="{iy}" width="{iw}" height="{ih}"/></clipPath>'
        '<filter id="glow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>'
        '<filter id="glow2" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>'
    )
    s.css.append(
        ".shutter{animation:up 1.5s cubic-bezier(.55,0,.2,1) .9s both}"
        f"@keyframes up{{to{{transform:translateY(-{ih + 4}px)}}}}"
        ".neon{animation:on 1.4s linear .15s both}"
        "@keyframes on{0%{opacity:0}6%{opacity:1}9%{opacity:.1}16%{opacity:1}19%{opacity:.25}24%{opacity:1}100%{opacity:1}}"
        ".buzz{animation:buzz 9s linear 3s infinite}"
        "@keyframes buzz{0%,93%,95.5%,100%{opacity:1}94%{opacity:.35}95%{opacity:.8}}"
        "@media (prefers-reduced-motion:reduce){.shutter{animation:none;transform:translateY(-250px)}.neon,.buzz{animation:none}}"
    )
    s.add(f'<rect width="{W}" height="{H}" fill="url(#fa)"/>')
    s.add(f'<rect width="{W}" height="300" fill="url(#sp)"/>')

    s.add(f'<rect x="36" y="26" width="1128" height="124" rx="6" fill="{t["board"]}" stroke="{t["boardline"]}" stroke-width="2"/>')
    s.text(76, 104, "SPÄTKAUF", "anton", 34, "#e8e4dc", spacing=3)
    s.text(1124, 104, "BERLIN", "anton", 34, "#e8e4dc", "end", spacing=3)
    neon, size = "Samis Späti", 96
    s.text(600, 116, neon, "neon", size, "#3a1a27", "middle")
    s.add('<g class="neon"><g class="buzz">')
    s.add(f'<g filter="url(#glow)" opacity="{t["glow"]}">' + s.run(600, 116, neon, "neon", size, PINK, "middle") + "</g>")
    s.add('<g filter="url(#glow2)" opacity="0.9">' + s.run(600, 116, neon, "neon", size, "none", "middle", stroke=PINK, sw=5) + "</g>")
    s.add(s.run(600, 116, neon, "neon", size, "#ffe4ef", "middle", stroke=PINK, sw=1.6))
    s.add("</g></g>")

    s.add(f'<rect x="36" y="150" width="1128" height="34" fill="{t["board"]}"/>')
    s.add(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="url(#in)"/>')

    fx, fy, fw, fh = 846, 198, 282, 230
    s.add(f'<ellipse cx="{fx + fw / 2}" cy="{fy + fh / 2}" rx="260" ry="190" fill="url(#fg)"/>')
    s.add(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="6" fill="#c3c9d0"/>')
    s.add(f'<rect x="{fx + 12}" y="{fy + 10}" width="{fw - 24}" height="{fh - 22}" rx="3" fill="url(#fr)"/>')
    colors = [ORANGE, YELLOW, PINK, "#19b37b", "#2f6fed", "#f4f4f4", BLACK, ORANGE, "#19b37b", YELLOW]
    shelf_y = [fy + 60, fy + 110, fy + 160, fy + 210]
    k = 0
    for row, sy in enumerate(shelf_y):
        x = fx + 22
        while x < fx + fw - 40:
            c = colors[(k * 7 + row * 3) % len(colors)]
            tall = 40 if (k + row) % 3 else 46
            s.add(f'<rect x="{x}" y="{sy - tall}" width="22" height="{tall}" rx="3" fill="{c}"/>')
            s.add(f'<rect x="{x + 3}" y="{sy - tall + 4}" width="4" height="{tall - 8}" rx="2" fill="#fff" opacity="0.35"/>')
            x += 28
            k += 1
        s.add(f'<rect x="{fx + 12}" y="{sy}" width="{fw - 24}" height="4" fill="#9fb3c2"/>')
    s.add(f'<rect x="{fx + fw - 24}" y="{fy + 70}" width="5" height="70" rx="2" fill="#8e979f"/>')

    px, py, pw, ph = 92, 204, 600, 206
    s.add(f'<g transform="rotate(-1.2 {px + pw / 2} {py + ph / 2})">')
    s.add(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="{ORANGE}"/>')
    name = "SAMI MAGDOULI"
    ns = F["anton"].fit(name, pw - 64, 120, 1)
    s.text(px + 32, py + 128, name, "anton", ns, BLACK, spacing=1)
    s.text(px + 34, py + 178, "Software engineer in Berlin", "plexb", 32, BLACK)
    s.add("</g>")
    s.add(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="url(#gl)"/>')

    s.add(f'<g clip-path="url(#win)"><g class="shutter">')
    s.add(f'<rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="{t["shutter"]}"/>')
    for yy in range(iy + 10, iy + ih, 11):
        s.add(f'<rect x="{ix}" y="{yy}" width="{iw}" height="2" fill="{t["slat"]}"/>')
    s.add(f'<rect x="{ix}" y="{iy + ih - 12}" width="{iw}" height="12" fill="{t["housing"]}"/>')
    s.add(f'<rect x="{ix + iw / 2 - 40}" y="{iy + ih - 9}" width="80" height="5" rx="2" fill="{t["slat"]}"/>')
    s.add("</g></g>")
    s.add(f'<rect x="36" y="172" width="1128" height="270" fill="none" stroke="{t["board"]}" stroke-width="12"/>')
    s.add(f'<rect x="0" y="442" width="{W}" height="28" fill="{t["walk"]}"/>')
    s.add(f'<rect x="0" y="442" width="{W}" height="3" fill="{t["curb"]}"/>')
    return s.render()


def barcode(s, x, y, w, h, seed, color):
    import hashlib
    bits = "".join(f"{b:08b}" for b in hashlib.sha1(seed.encode()).digest())
    xx, i = x, 0
    while xx < x + w - 2:
        bw = 1 + int(bits[i % len(bits)]) + int(bits[(i + 7) % len(bits)])
        if i % 2 == 0:
            s.add(f'<rect x="{xx:.1f}" y="{y}" width="{bw}" height="{h}" fill="{color}"/>')
        xx += bw + 0.6
        i += 1


def tag(t, p):
    W, H = 420, 196
    s = Svg(W, H, f"{p['name']}: {p['desc']} {p['price']} {p['unit']}. {p['foot']}")
    s.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>')
    s.text(22, 42, p["name"], "plexb", 22, t["ink"])
    lines = F["plex"].wrap(p["desc"], 14.5, 236)[:4]
    for i, ln in enumerate(lines):
        s.text(22, 70 + i * 21, ln, "plex", 14.5, t["ink2"])
    s.text(22, 176, p["foot"], "plex", 13, t["muted"])

    bx, by, bw, bh = 280, 14, 126, 124
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="{YELLOW}"/>')
    ps = F["anton"].fit(p["price"], bw - 20, 56)
    s.text(bx + bw / 2, by + 72, p["price"], "anton", ps, BLACK, "middle")
    ul = F["plexb"].wrap(p["unit"], 12, bw - 16)[:2]
    for i, ln in enumerate(ul):
        s.text(bx + bw / 2, by + 96 + i * 15, ln, "plexb", 12, BLACK, "middle")
    barcode(s, bx + 8, 152, bw - 16, 26, p["name"], t["muted"])
    return s.render()


def wins(t):
    W, H = 420, 352
    rows = [
        ("1st", "CODE Hackathon", "Berlin 2026, with Malek Hassan"),
        ("2nd", "Google Accessibility Hackathon", "Berlin 2026, with Malek Hassan"),
        ("2nd", "Schule der Löwen", "pitch competition, solo, in German"),
        ("3rd", "OpenAI Hackathon", "2026"),
        ("3rd", "Cursor Hackathon at Taxfix", "Berlin 2026"),
        ("4th", "SummerUP at CODE University", "of 120 teams"),
    ]
    s = Svg(W, H, "Winning tickets sold here: " + "; ".join(f"{a} {b}, {c}" for a, b, c in rows))
    s.defs.append(f'<clipPath id="c"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12"/></clipPath>')
    s.add(f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="#fffdf6"/>')
    s.add(f'<rect width="{W}" height="94" fill="{RED}"/></g>')
    s.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{t["line"]}"/>')
    s.text(W / 2, 52, "WINNING TICKETS", "anton", F["anton"].fit("WINNING TICKETS", 360, 40, 2), "#ffffff", "middle", spacing=2)
    s.text(W / 2, 80, "SOLD HERE", "anton", 20, YELLOW, "middle", spacing=5)
    y = 106
    for i, (place, event, detail) in enumerate(rows):
        s.text(24, y + 26, place, "anton", 28, RED)
        s.text(84, y + 16, event, "plexb", 15, BLACK)
        s.text(84, y + 33, detail, "plex", 12.5, "#5b5b5b")
        if i < len(rows) - 1:
            s.add(f'<line x1="24" y1="{y + 38.5}" x2="{W - 24}" y2="{y + 38.5}" stroke="#e7e1cf" stroke-dasharray="4 4"/>')
        y += 38
    return s.render()


def am_pm(h):
    h %= 24
    if h == 0:
        return "midnight"
    if h == 12:
        return "noon"
    return f"{h} am" if h < 12 else f"{h - 12} pm"


def hours(t, grid, since):
    W, H = 420, 352
    by_hour = [sum(grid[d][h] for d in range(7)) for h in range(24)]
    top = max(by_hour)
    open_h = [h for h in range(24) if by_hour[h] >= top * 0.2]
    start = min(h for h in open_h if h >= 5)
    end = max((h + 1) % 24 for h in open_h if h < 5) if any(h < 5 for h in open_h) else max(open_h) + 1
    line = f"Daily, {am_pm(start)} to {am_pm(end)}"
    s = Svg(W, H, f"Opening hours: {line}. A grid of weekdays and hours shows when my commits land.")
    s.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>')
    s.text(24, 46, "Opening hours", "plexb", 20, t["ink"])
    s.text(24, 96, line, "anton", F["anton"].fit(line, W - 48, 40), t["ink"])
    cells = sorted(v for row in grid for v in row if v)
    q = [cells[int(len(cells) * f)] for f in (0.25, 0.5, 0.75)]
    ramp = ["#fff1a8", "#ffe14d", YELLOW, "#f2a900"] if t is THEMES["light"] else ["#4d4216", "#8a7414", "#d1ad0a", YELLOW]
    x0, y0, c, ch, g = 56, 120, 12, 16, 2.5
    for d, lab in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
        s.text(24, y0 + d * (ch + g) + 12.5, lab, "plex", 11.5, t["muted"])
        for h in range(24):
            v = grid[d][h]
            fill = t["empty"] if not v else ramp[sum(v > x for x in q)]
            s.add(f'<rect x="{x0 + h * (c + g):.1f}" y="{y0 + d * (ch + g):.1f}" width="{c}" height="{ch}" rx="2.5" fill="{fill}"/>')
    for h in (0, 6, 12, 18):
        s.text(x0 + h * (c + g), y0 + 7 * (ch + g) + 14, f"{h:02d}", "plex", 11.5, t["muted"])
    s.text(24, 312, "Read from my commit history", "plex", 13, t["ink2"])
    s.text(24, 332, f"since {since}, Berlin time.", "plex", 13, t["ink2"])
    return s.render()


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)


def refresh_hours():
    tz = ZoneInfo("Europe/Berlin")
    me = gh_json("api", "graphql", "-f", "query=query{viewer{id}}")["data"]["viewer"]["id"]
    repos = gh_json("repo", "list", "sami-mag07", "--limit", "300", "--json", "name,isFork")
    stamps = []
    q = ("query($n:String!,$a:ID!,$c:String){viewer{repository(name:$n){defaultBranchRef{target{... on Commit{"
         "history(first:100,after:$c,author:{id:$a}){pageInfo{hasNextPage endCursor} nodes{authoredDate}}}}}}}}")
    for r in repos:
        if r["isFork"]:
            continue
        cur = None
        while True:
            args = ["api", "graphql", "-f", f"query={q}", "-f", f"n={r['name']}", "-f", f"a={me}"]
            if cur:
                args += ["-f", f"c={cur}"]
            try:
                ref = gh_json(*args)["data"]["viewer"]["repository"]["defaultBranchRef"]
            except subprocess.CalledProcessError:
                break
            if not ref:
                break
            hist = ref["target"]["history"]
            stamps += [n["authoredDate"] for n in hist["nodes"]]
            if not hist["pageInfo"]["hasNextPage"]:
                break
            cur = hist["pageInfo"]["endCursor"]
    now = datetime.now(tz)
    grid = [[0] * 24 for _ in range(7)]
    first = None
    for st in stamps:
        d = datetime.fromisoformat(st.replace("Z", "+00:00")).astimezone(tz)
        if d < now - timedelta(days=365):
            continue
        grid[d.weekday()][d.hour] += 1
        first = d if first is None or d < first else first
    data = {"grid": grid, "since": first.strftime("%B %Y"), "built": now.strftime("%Y-%m-%d")}
    (ASSETS / "hours.json").write_text(json.dumps(data))
    return data


def stars(repo):
    try:
        return gh_json("api", f"repos/sami-mag07/{repo}")["stargazers_count"]
    except subprocess.CalledProcessError:
        return None


def projects():
    s1, s2 = stars("searchify"), stars("ultimate-scraper-agent")
    return [
        {"slug": "searchify", "name": "Searchify", "url": GH + "searchify",
         "desc": "Web search for AI agents on your own machine. No API key.",
         "price": "84%", "unit": "extraction F1, Firecrawl gets 73%", "foot": f"Python · on PyPI · {s1} stars"},
        {"slug": "hoopergpt", "name": "HooperGPT", "url": "https://github.com/Malek1414/code-hackathon-project",
         "desc": "Follows players, jersey numbers and shots through a basketball game video.",
         "price": "1st", "unit": "CODE Hackathon", "foot": "Python · YOLO · OCR · with Malek Hassan"},
        {"slug": "emil", "name": "Emil", "url": None,
         "desc": "My assistant on WhatsApp. An orchestrator with specialist agents that sorts my mail, plans my week and calls me.",
         "price": "9", "unit": "specialist agents", "foot": "Python · runs 24/7 on my own server"},
        {"slug": "research-agent", "name": "Research Agent", "url": GH + "ultimate-scraper-agent",
         "desc": "Research skill for Claude Code. Several search engines, parallel agent waves, no citation without a verbatim quote.",
         "price": str(s2), "unit": "GitHub stars", "foot": "Python · zero dependencies · MIT"},
        {"slug": "tapntax", "name": "Tap n' tax", "url": GH + "tapntax",
         "desc": "A card payment turns into one question on your phone. One tap files the expense.",
         "price": "3rd", "unit": "Cursor Hackathon at Taxfix", "foot": "Python · no dependencies"},
        {"slug": "parkit", "name": "ParkIt", "url": GH + "ParkIt",
         "desc": "What parking in Berlin really costs right now, across all 102 official zones.",
         "price": "€0.00", "unit": "parking in Mitte after 22:01", "foot": "React Native · Expo · live demo"},
    ]


def pic(base, alt, width=None):
    w = f' width="{width}"' if width else ' width="100%"'
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{base}-dark.svg">'
            f'<img alt="{escape(alt)}" src="assets/{base}-light.svg"{w}></picture>')


def readme(ps, hours_alt, wins_alt):
    def item(p):
        img = pic("tags/" + p["slug"], p["name"] + ": " + p["desc"], 400)
        return f'<a href="{p["url"]}">{img}</a>' if p["url"] else img

    shelf = "\n".join(item(p) for p in ps)
    return f"""<a href="{SITE}">{pic("header", "Samis Späti: a Berlin late-night shop. The neon sign switches on, the shutter rolls up, and the poster in the window reads Sami Magdouli, software engineer in Berlin.")}</a>

<p align="center">
  <a href="{SITE}"><b>Website</b></a> &nbsp;·&nbsp;
  <a href="{LINKEDIN}"><b>LinkedIn</b></a> &nbsp;·&nbsp;
  <a href="{MAIL}"><b>Email</b></a>
</p>

I build AI agents and the tools under them: web search, extraction, research and computer vision. Technical researcher at a stealth startup in San Francisco. Coding since 2020.

## Projects

<p align="center">
{shelf}
</p>

<p align="center">
{pic("wins", wins_alt, 400)}
{pic("hours", hours_alt, 400)}
</p>
"""


def main():
    if "--refresh" in sys.argv or not (ASSETS / "hours.json").exists():
        hd = refresh_hours()
    else:
        hd = json.loads((ASSETS / "hours.json").read_text())
    ps = projects()
    (ASSETS / "tags").mkdir(parents=True, exist_ok=True)
    for mode, t in THEMES.items():
        (ASSETS / f"header-{mode}.svg").write_text(header(t, mode))
        (ASSETS / f"wins-{mode}.svg").write_text(wins(t))
        (ASSETS / f"hours-{mode}.svg").write_text(hours(t, hd["grid"], hd["since"]))
        for p in ps:
            (ASSETS / "tags" / f"{p['slug']}-{mode}.svg").write_text(tag(t, p))
    wins_alt = "Winning tickets sold here: 1st CODE Hackathon, 2nd Google Accessibility Hackathon, 2nd Schule der Löwen pitch competition, 3rd OpenAI Hackathon, 3rd Cursor Hackathon at Taxfix, 4th SummerUP of 120 teams"
    hours_alt = "Opening hours read from my commit history: a grid of weekdays and hours, busy every day from morning to past midnight"
    (ROOT / "README.md").write_text(readme(ps, hours_alt, wins_alt))
    print("ok", len(ps), "tags")


if __name__ == "__main__":
    main()
