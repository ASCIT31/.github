#!/usr/bin/env python3
"""Generate the self-hosted SVG artwork used by profile/README.md.

Everything is rendered to paths with the brand fonts (all SIL OFL, see
profile/fonts/), so the SVGs need no external resources and survive GitHub's
image proxy. Live numbers (stars, forks, contributors, releases) are fetched from
the GitHub API and baked into the stats tiles and repo cards; the workflow in
.github/workflows/refresh-profile.yml reruns this script every day.

    python3 scripts/build_assets.py            # everything
    python3 scripts/build_assets.py --static   # skip API calls (hero, banner, sections only)
"""
import base64, json, os, random, re, sys, time, urllib.request
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / 'profile' / 'assets'
FONTS = ROOT / 'profile' / 'fonts'
DATA = ROOT / 'profile' / 'data'
ORG = 'ASCIT31'

MOMO = FONTS / 'MomoTrustDisplay-Regular.ttf'
INTER = FONTS / 'Inter_18pt-Regular.ttf'
INTER_SB = FONTS / 'Inter_18pt-SemiBold.ttf'
MONO = FONTS / 'SpaceMono-Regular.ttf'
MONO_B = FONTS / 'SpaceMono-Bold.ttf'
POPPINS = FONTS / 'Poppins-SemiBold.ttf'
POPPINS_R = FONTS / 'Poppins-Regular.ttf'

# ASC-IT brand system 2026
GREEN = '#00FF86'; GREEN_TXT_LIGHT = '#00A659'; CARBON = '#1D1D1B'; WHITE = '#FFFFFF'
# Darkmoon brand system
ROYAL = '#0A2472'; NEON = '#2667FF'; CHRYSLER = '#3B26CC'; JORDY = '#87BFFF'; URANIAN = '#ADD7F6'; ALICE = '#DCEAF4'

_fonts = {}
def font(p):
    if p not in _fonts:
        f = TTFont(p); _fonts[p] = (f, f.getGlyphSet(), f.getBestCmap(), f['head'].unitsPerEm, f['hmtx'])
    return _fonts[p]

def text_path(fp, text, size, ls=0):
    f, gs, cmap, upm, hmtx = font(fp); sc = size / upm; pen = SVGPathPen(gs, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.')); cx = 0
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None: cx += size * 0.3; continue
        gs[g].draw(TransformPen(pen, (sc, 0, 0, -sc, cx, 0))); cx += hmtx[g][0] * sc + ls
    return pen.getCommands(), cx

def text_width(fp, text, size, ls=0):
    f, gs, cmap, upm, hmtx = font(fp); sc = size / upm
    return sum((hmtx[cmap[ord(c)]][0] * sc + ls) if ord(c) in cmap else size * 0.3 for c in text)

def T(fp, text, size, x, y, fill, ls=0, opacity=1, anchor='start', extra=''):
    d, w = text_path(fp, text, size, ls)
    if anchor == 'middle': x = x - w / 2
    elif anchor == 'end': x = x - w
    return f'<path transform="translate({x:.1f} {y:.1f})" d="{d}" fill="{fill}" opacity="{opacity}" {extra}/>'

def wrap(fp, text, size, max_w):
    words = text.split(); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if text_width(fp, t, size) <= max_w: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def inner(svg):
    return re.search(r'<g id="Components">(.*)</g></svg>', Path(svg).read_text(), re.S).group(1)
def vb(svg):
    return [float(v) for v in re.search(r'viewBox="([^"]+)"', Path(svg).read_text()).group(1).split()]
def logomark(color):
    return inner(A / 'logos/asc-logomark-white.svg').replace('#fff', color).replace('#ffffff', color)
def brandmark(color):
    return inner(A / 'logos/asc-brandmark-green.svg').replace('#00ff86', color)
def b64(p):
    raw = Path(p).read_bytes(); mime = 'png' if raw[:8] == b'\x89PNG\r\n\x1a\n' else 'jpeg'
    return f'data:image/{mime};base64,' + base64.b64encode(raw).decode()

def pixels(n, w, h, color, seed, amin=0.05, amax=0.35, smin=6, smax=22, dur=(14, 30)):
    random.seed(seed); out = []
    for _ in range(n):
        s = random.randint(smin, smax); x = random.uniform(0, w); y = random.uniform(0, h); a = random.uniform(amin, amax)
        d = random.uniform(*dur); dx = random.uniform(-40, 40); dy = random.uniform(-60, -15)
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{s}" height="{s}" fill="{color}" opacity="{a:.2f}">'
                   f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx:.0f} {dy:.0f};0 0" dur="{d:.0f}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="opacity" values="{a:.2f};{a*0.3:.2f};{a:.2f}" dur="{d/2:.0f}s" repeatCount="indefinite"/></rect>')
    return ''.join(out)

def fade(content, begin=0, dur=1):
    return f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{begin}s" dur="{dur}s" fill="freeze"/>{content}</g>'

def write(name, svg):
    p = A / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(svg)
    import xml.dom.minidom; xml.dom.minidom.parseString(svg)  # fail loudly on invalid XML
    print(f'  {name}  {len(svg)//1024} KB')

# ---------------------------------------------------------------- hero
def hero(dark):
    Wd, H = 1200, 420
    bg = CARBON if dark else WHITE; fg = WHITE if dark else CARBON; sub = '#B9C0BE' if dark else '#4B4F4D'
    lw = vb(A / 'logos/asc-logomark-white.svg')[2]; sc = 330 / lw; lx = (Wd - 330) / 2; ly = 92
    grid = f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{fg}" stroke-opacity="{0.06 if dark else 0.08}"/></pattern>'
    glow = (f'<radialGradient id="glow" cx="50%" cy="35%" r="55%"><stop offset="0" stop-color="{GREEN}" stop-opacity="{0.22 if dark else 0.18}">'
            f'<animate attributeName="stop-opacity" values="{0.22 if dark else 0.18};{0.10 if dark else 0.08};{0.22 if dark else 0.18}" dur="7s" repeatCount="indefinite"/></stop>'
            f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>')
    scan = (f'<rect x="0" y="0" width="{Wd}" height="2" fill="{GREEN}" opacity="0.55"><animate attributeName="y" values="-2;{H}" dur="9s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0.6;0.6;0" keyTimes="0;0.1;0.9;1" dur="9s" repeatCount="indefinite"/></rect>')
    corner = f'<g opacity="0.35">{brandmark(GREEN)}</g>'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}" role="img" aria-label="ASC-IT — You just have to ask it.">
<defs>{grid}{glow}<clipPath id="c"><rect width="{Wd}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#c)"><rect width="{Wd}" height="{H}" fill="{bg}"/><rect width="{Wd}" height="{H}" fill="url(#grid)"/><rect width="{Wd}" height="{H}" fill="url(#glow)"/>
{pixels(46, Wd, H, GREEN, 7, amin=0.06, amax=0.30)}
<g transform="translate(40 40) scale(0.42)">{corner}</g>
<g transform="translate({Wd-40-234.78*0.42:.1f} {H-40-96.35*0.42:.1f}) scale(0.42)">{corner}</g>
{fade(f'<g transform="translate({lx:.1f} {ly}) scale({sc:.4f})">{logomark(fg)}</g>', 0, 1.2)}
{fade(T(MOMO, 'You just have to ask it.', 54, Wd/2, 300, fg, anchor='middle'), 0.5, 1)}
{fade(T(INTER, 'Offensive cybersecurity  ·  Autonomous AI pentesting  ·  Software engineering', 18, Wd/2, 345, sub, ls=0.4, anchor='middle')
      + T(MONO, 'TOULOUSE, FRANCE  —  SINCE 2021', 14, Wd/2, 382, GREEN if dark else GREEN_TXT_LIGHT, ls=1.2, anchor='middle'), 1, 1)}
{scan}<rect x="0.5" y="0.5" width="{Wd-1}" height="{H-1}" rx="18" fill="none" stroke="{GREEN}" stroke-opacity="{0.35 if dark else 0.5}"/></g></svg>'''
    write(f'hero-{"dark" if dark else "light"}.svg', svg)

# ---------------------------------------------------------------- darkmoon banner
def darkmoon_banner():
    Wd, H = 1200, 300
    grad = (f'<linearGradient id="dm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ROYAL}"><animate attributeName="stop-color" values="{ROYAL};{CHRYSLER};{ROYAL}" dur="12s" repeatCount="indefinite"/></stop>'
            f'<stop offset="0.55" stop-color="{NEON}"/><stop offset="1" stop-color="{JORDY}"><animate attributeName="stop-color" values="{JORDY};{URANIAN};{JORDY}" dur="12s" repeatCount="indefinite"/></stop></linearGradient>')
    rings = ''.join(f'<circle cx="150" cy="150" r="{r}" fill="none" stroke="{ALICE}" stroke-opacity="{0.22-i*0.03:.2f}" stroke-width="10" stroke-dasharray="3 6">'
                    f'<animateTransform attributeName="transform" type="rotate" from="0 150 150" to="{360 if i%2 else -360} 150 150" dur="{60+i*20}s" repeatCount="indefinite"/></circle>'
                    for i, r in enumerate([70, 120, 170, 220, 270]))
    lw = 560; lh = lw * 536 / 3184; x0 = Wd - lw - 70
    logo = f'<image href="{b64(A / "logos/darkmoon-logotype-alice.png")}" x="{x0}" y="52" width="{lw}" height="{lh:.1f}"/>'
    t1 = T(MONO, 'REVEAL WHAT’S HIDDEN', 22, x0, 190, ALICE, ls=2)
    sub = 'Open-source autonomous AI pentesting  ·  50 agents  ·  50+ tools  ·  Privacy Gateway'
    size = 17
    while text_width(POPPINS, sub, size) > lw: size -= 0.5
    t2 = T(POPPINS, sub, size, x0, 228, ALICE, opacity=0.9)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}" role="img" aria-label="Darkmoon by ASC-IT — reveal what's hidden">
<defs>{grad}<clipPath id="c"><rect width="{Wd}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#c)"><rect width="{Wd}" height="{H}" fill="url(#dm)"/>{rings}{pixels(40, Wd, H, ALICE, 3, amin=0.08, amax=0.45, smin=5, smax=18)}
{fade(logo, 0, 1.2)}{fade(t1 + t2, 0.6, 1)}</g></svg>'''
    write('darkmoon-banner.svg', svg)

# ---------------------------------------------------------------- section headers
def section(title, kicker, name):
    for dark in (True, False):
        Wd, H = 1200, 84; fg = WHITE if dark else CARBON
        t = T(MOMO, title, 34, 74, 56, fg); w = text_width(MOMO, title, 34)
        k = T(MONO, kicker.upper(), 12, 74, 24, GREEN if dark else GREEN_TXT_LIGHT, ls=1.5)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}" role="img" aria-label="{title}">
<rect x="0" y="0" width="14" height="{H}" fill="{GREEN}"><animate attributeName="height" values="0;{H}" dur="0.8s" fill="freeze"/></rect>{k}{t}
<path d="M{74+w+24:.0f} 48 H{Wd-10}" stroke="{fg}" stroke-opacity="0.18" stroke-dasharray="4 6"/></svg>'''
        write(f'sections/{name}-{"dark" if dark else "light"}.svg', svg)

# ---------------------------------------------------------------- live data
def gh(path):
    req = urllib.request.Request(f'https://api.github.com{path}', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'ascit31-profile'})
    tok = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if tok: req.add_header('Authorization', f'Bearer {tok}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), r.headers

def fetch_data():
    repos = ['Dark-Moon', 'darkmoon-scan-action', 'Darkmoon-Benchmarks', 'darkmoon-research', 'Dark-Moon-CI-Demo']
    out = {'generated': time.strftime('%Y-%m-%d'), 'repos': {}}
    org, _ = gh(f'/orgs/{ORG}'); out['org'] = {'followers': org.get('followers', 0), 'public_repos': org.get('public_repos', 0)}
    for r in repos:
        j, _ = gh(f'/repos/{ORG}/{r}')
        rel = {}
        try: rel, _ = gh(f'/repos/{ORG}/{r}/releases/latest')
        except Exception: pass
        contributors = 0
        try:
            _, h = gh(f'/repos/{ORG}/{r}/contributors?per_page=1&anon=0')
            m = re.search(r'page=(\d+)>; rel="last"', h.get('Link', '')); contributors = int(m.group(1)) if m else 1
        except Exception: pass
        commits = 0
        try:
            _, h = gh(f'/repos/{ORG}/{r}/commits?per_page=1')
            m = re.search(r'page=(\d+)>; rel="last"', h.get('Link', '')); commits = int(m.group(1)) if m else 1
        except Exception: pass
        out['repos'][r] = {'stars': j['stargazers_count'], 'forks': j['forks_count'], 'watchers': j.get('subscribers_count', 0),
                           'description': j.get('description') or '', 'language': j.get('language') or '', 'license': ((j.get('license') or {}).get('spdx_id') or '').replace('NOASSERTION', ''),
                           'release': rel.get('tag_name', ''), 'release_date': (rel.get('published_at') or '')[:10],
                           'contributors': contributors, 'commits': commits, 'pushed_at': (j.get('pushed_at') or '')[:10], 'open_issues': j.get('open_issues_count', 0)}
    DATA.mkdir(parents=True, exist_ok=True); (DATA / 'stats.json').write_text(json.dumps(out, indent=2))
    return out

def fmt(n):
    return f'{n/1000:.1f}k' if n >= 10000 else (f'{n:,}' if n >= 1000 else str(n))

LANG_COLORS = {'Python': '#3572A5', 'TypeScript': '#3178c6', 'Shell': '#89e051', 'HTML': '#e34c26', 'JavaScript': '#f1e05a', 'Go': '#00ADD8', 'Dockerfile': '#384d54'}

# ---------------------------------------------------------------- stats tiles
def stats_tiles(d, dark):
    dm = d['repos']['Dark-Moon']
    tiles = [(fmt(dm['stars']), 'GitHub stars', 'Dark-Moon'), (fmt(dm['forks']), 'Forks', 'Dark-Moon'), (str(dm['contributors']), 'Contributors', 'Dark-Moon'),
             (fmt(dm['commits']), 'Commits', 'master branch'), ('50', 'AI agents', 'one per technology'), ('57', 'Real vulns', 'Juice Shop · 28.5 min')]
    n = len(tiles); gap = 14; Wd = 1200; tw = (Wd - gap * (n - 1)) / n; H = 128
    bg = '#24242A' if dark else '#F4F6F5'; fg = WHITE if dark else CARBON; sub = '#9AA19E' if dark else '#5C615F'; line = GREEN
    out = []
    for i, (num, label, hint) in enumerate(tiles):
        x = i * (tw + gap)
        out.append(f'<g transform="translate({x:.1f} 0)"><rect width="{tw:.1f}" height="{H}" rx="14" fill="{bg}"/>'
                   f'<rect x="0" y="0" width="{tw:.1f}" height="4" rx="2" fill="{line}"><animate attributeName="width" values="0;{tw:.1f}" begin="{i*0.12:.2f}s" dur="0.8s" fill="freeze"/></rect>'
                   + fade(T(MOMO, num, 44, 20, 66, fg) + T(INTER_SB, label, 14, 20, 92, fg) + T(MONO, hint, 10.5, 20, 113, sub), i * 0.12, 0.7) + '</g>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}" role="img" aria-label="Key numbers">{"".join(out)}</svg>'
    write(f'stats-{"dark" if dark else "light"}.svg', svg)

# ---------------------------------------------------------------- repo cards
def repo_card(name, r, dark):
    Wd, H = 590, 190
    bg = '#24242A' if dark else '#F4F6F5'; fg = WHITE if dark else CARBON; sub = '#B9C0BE' if dark else '#4B4F4D'; dim = '#8A918E' if dark else '#6B706E'
    acc = GREEN if dark else GREEN_TXT_LIGHT
    icon = f'<g transform="translate(24 22) scale(0.14)">{brandmark(GREEN)}</g>'
    title = T(MOMO, name, 24, 66, 44, fg)
    desc = wrap(INTER, r['description'] or '', 14, Wd - 48)[:3]
    if len(wrap(INTER, r['description'] or '', 14, Wd - 48)) > 3: desc[-1] = desc[-1][:-1].rstrip() + '…'
    body = ''.join(T(INTER, l, 14, 24, 80 + i * 21, sub) for i, l in enumerate(desc))
    y = 158; x = 24; meta = ''
    if r['language']:
        meta += f'<circle cx="{x+6}" cy="{y-5}" r="6" fill="{LANG_COLORS.get(r["language"], "#999")}"/>' + T(MONO, r['language'], 12, x + 18, y, sub); x += 18 + text_width(MONO, r['language'], 12) + 22
    STAR = 'M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z'
    FORK = 'M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z'
    for ico, val in ((STAR, fmt(r['stars'])), (FORK, fmt(r['forks']))):
        meta += f'<path transform="translate({x:.1f} {y-12})" d="{ico}" fill="{sub}"/>' + T(MONO, val, 12, x + 21, y, sub); x += 21 + text_width(MONO, val, 12) + 22
    if r['release']: meta += T(MONO, r['release'], 12, x, y, acc)
    if r['license']: meta += T(MONO, r['license'], 12, Wd - 24, y, dim, anchor='end')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{H}" viewBox="0 0 {Wd} {H}" role="img" aria-label="{ORG}/{name}: {(r['description'] or '').replace('"','&quot;').replace('&','&amp;').replace('<','&lt;')}">
<rect x="0.5" y="0.5" width="{Wd-1}" height="{H-1}" rx="14" fill="{bg}" stroke="{GREEN}" stroke-opacity="{0.35 if dark else 0.6}"/>
<rect x="0" y="0" width="5" height="{H}" rx="2" fill="{GREEN}"><animate attributeName="height" values="0;{H}" dur="0.7s" fill="freeze"/></rect>
{icon}{title}{fade(body, 0.2, 0.8)}{fade(meta, 0.4, 0.8)}</svg>'''
    write(f'repos/{name}-{"dark" if dark else "light"}.svg', svg)

def main():
    static = '--static' in sys.argv
    print('hero / banner / sections')
    hero(True); hero(False); darkmoon_banner()
    for t, k, n in [('What we build', '01 — Open source', 'build'), ('By the numbers', '02 — Metrics', 'numbers'), ('What we do', '03 — Services', 'services'),
                    ('The team', '04 — People', 'team'), ('In the press', '05 — Coverage', 'press'), ('Join us', '06 — Community', 'join')]:
        section(t, k, n)
    if static: return
    print('live data')
    d = fetch_data()
    for dark in (True, False):
        stats_tiles(d, dark)
        for name, r in d['repos'].items(): repo_card(name, r, dark)
    print('done', d['generated'])

if __name__ == '__main__':
    main()
