"""Generates the profile header SVGs (dark + light).

The village on the right is procedurally generated from a fixed seed,
in the spirit of LivingWorld: same seed, same world.

    python3 assets/generate.py
"""
import math
import random
from pathlib import Path

SEED = 19
W, H = 880, 300
TILE = 12
COLS, ROWS = 28, 20          # map size in tiles
MAP_X, MAP_Y = W - COLS * TILE - 28, 28

THEMES = {
    "dark": dict(
        bg="#0d1117", border="#30363d", text="#e6edf3", dim="#7d8590", key="#7d8590",
        accent="#7ee787", accent2="#79c0ff", prompt="#d2a8ff",
        water="#1f4b7a", water2="#2a5f94", grass="#1f3d2a", grass2="#24472f",
        tree="#2f6b3f", trunk="#3b2f22", road="#4a4136", roof="#b0573f", wall="#c9b48f",
        npc="#f0f6fc", night="#010409",
    ),
    "light": dict(
        bg="#ffffff", border="#d0d7de", text="#1f2328", dim="#656d76", key="#656d76",
        accent="#1a7f37", accent2="#0969da", prompt="#8250df",
        water="#6fa8dc", water2="#8dbde6", grass="#a8d5a2", grass2="#9ccc95",
        tree="#4f9a55", trunk="#7a5a3a", road="#d9c7a3", roof="#c4553a", wall="#f3e6c8",
        npc="#1f2328", night="#0b1b33",
    ),
}

LINES = [
    ("prompt", "$ living-world observe --npc alan --seed 19"),
    ("kv", "role", "software architect"),
    ("kv", "experience", "6+ years"),
    ("kv", "domains", "financial markets · fitness · health"),
    ("kv", "exploring", "ai · llms · agents · open source"),
    ("kv", "tooling", "developer tools &amp; simulations"),
    ("kv", "building", "waymark · living world"),
    ("status", "status", "simulating"),
]


def value_noise(rng, cols, rows, scale):
    gw, gh = cols // scale + 2, rows // scale + 2
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def smooth(t):
        return t * t * (3 - 2 * t)

    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            gx, gy = x / scale, y / scale
            x0, y0 = int(gx), int(gy)
            tx, ty = smooth(gx - x0), smooth(gy - y0)
            a = grid[y0][x0] + (grid[y0][x0 + 1] - grid[y0][x0]) * tx
            b = grid[y0 + 1][x0] + (grid[y0 + 1][x0 + 1] - grid[y0 + 1][x0]) * tx
            row.append(a + (b - a) * ty)
        out.append(row)
    return out


def build_world():
    rng = random.Random(SEED)
    n = value_noise(rng, COLS, ROWS, 6)
    tiles = [["grass"] * COLS for _ in range(ROWS)]
    for y in range(ROWS):
        for x in range(COLS):
            v = n[y][x]
            if v < 0.24:
                tiles[y][x] = "water"
            elif v < 0.28:
                tiles[y][x] = "water2"
            elif v > 0.70 and rng.random() < 0.55:
                tiles[y][x] = "tree"
            elif rng.random() < 0.25:
                tiles[y][x] = "grass2"

    # village square: find the driest spot near the center
    best, cx, cy = -1, COLS // 2, ROWS // 2
    for y in range(5, ROWS - 5):
        for x in range(6, COLS - 6):
            score = sum(n[y + dy][x + dx] for dy in (-2, 0, 2) for dx in (-3, 0, 3))
            score -= abs(x - COLS / 2) * 0.05 + abs(y - ROWS / 2) * 0.05
            if 0.38 < n[y][x] < 0.68 and score > best:
                best, cx, cy = score, x, y

    def land(x, y):
        return 0 <= x < COLS and 0 <= y < ROWS and not tiles[y][x].startswith("water")

    # roads: a cross through the square
    for x in range(COLS):
        if land(x, cy) and abs(x - cx) < 11:
            tiles[cy][x] = "road"
    for y in range(ROWS):
        if land(cx, y) and abs(y - cy) < 8:
            tiles[y][cx] = "road"

    houses = []
    for _ in range(400):
        if len(houses) >= 11:
            break
        x = cx + rng.randint(-8, 8)
        y = cy + rng.choice([-2, -1, 1, 2]) * rng.randint(1, 2)
        if all(land(x + dx, y) and tiles[y][x + dx] != "road" for dx in (0, 1)) \
                and all(abs(x - hx) > 2 or abs(y - hy) > 1 for hx, hy in houses):
            houses.append((x, y))
            tiles[y][x] = tiles[y][x + 1] = "house"
    return tiles, houses, (cx, cy), rng


def npc_paths(houses, square, rng):
    cx, cy = square
    paths = []
    for i, (hx, hy) in enumerate(houses[:7]):
        pts = [(hx, hy + (1 if hy < cy else -1))]
        # walk to the road, along it, to the square, and back
        pts += [(hx, cy), (cx + rng.randint(-1, 1), cy), (hx, cy), pts[0]]
        d = "M" + " L".join(f"{px * TILE + TILE / 2:.0f},{py * TILE + TILE / 2:.0f}" for px, py in pts)
        paths.append((d, 14 + rng.randint(0, 10), rng.random() * -20))
    return paths


def render(theme_name):
    t = THEMES[theme_name]
    tiles, houses, square, rng = build_world()
    paths = npc_paths(houses, square, rng)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'role="img" aria-label="Alan Edward, software architect. A procedurally generated village from seed {SEED}.">']
    out.append(f"""<style>
  text {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 14px; }}
  .name {{ font-size: 30px; font-weight: 700; fill: {t['text']}; letter-spacing: -0.5px; }}
  .sub {{ fill: {t['dim']}; font-size: 13px; }}
  .p {{ fill: {t['prompt']}; }} .k {{ fill: {t['key']}; }} .v {{ fill: {t['text']}; }}
  .a {{ fill: {t['accent']}; }} .b {{ fill: {t['accent2']}; }}
  .line {{ opacity: 0; animation: in .35s ease-out forwards; }}
  .cursor {{ animation: blink 1s steps(1) infinite; }}
  .night {{ animation: day 24s ease-in-out infinite; }}
  .lamp {{ animation: lamp 24s ease-in-out infinite; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @keyframes day {{ 0%, 35% {{ opacity: 0; }} 50%, 80% {{ opacity: .55; }} 95%, 100% {{ opacity: 0; }} }}
  @keyframes lamp {{ 0%, 38% {{ opacity: 0; }} 52%, 78% {{ opacity: 1; }} 92%, 100% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{
    .line {{ animation: none; opacity: 1; }} .night, .lamp, .cursor {{ animation: none; }}
  }}
</style>""")
    out.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>')

    # left: name + observe log
    out.append(f'<text x="34" y="62" class="name">Alan Edward</text>')
    out.append(f'<text x="34" y="86" class="sub">builds systems, tools and small worlds</text>')
    y = 124
    for i, line in enumerate(LINES):
        delay = 0.3 + i * 0.35
        g = f'<g class="line" style="animation-delay:{delay:.2f}s">'
        if line[0] == "prompt":
            g += f'<text x="34" y="{y}" class="p">{line[1]}</text>'
            y += 8
        elif line[0] == "kv":
            cls = "b" if line[1] == "building" else "v"
            g += f'<text x="34" y="{y}"><tspan class="k">{line[1]:<11}</tspan></text>'
            g += f'<text x="140" y="{y}" class="{cls}">{line[2]}</text>'
        else:
            g += f'<text x="34" y="{y}" class="k">{line[1]}</text>'
            g += f'<text x="140" y="{y}" class="a">● {line[2]}</text>'
            g += f'<rect class="cursor" x="244" y="{y - 12}" width="8" height="15" fill="{t["accent"]}"/>'
        out.append(g + "</g>")
        y += 21

    # right: the world
    mw, mh = COLS * TILE, ROWS * TILE
    out.append(f'<defs><clipPath id="m"><rect width="{mw}" height="{mh}" rx="6"/></clipPath></defs>')
    out.append(f'<g transform="translate({MAP_X},{MAP_Y})"><g clip-path="url(#m)">')
    for ry, row in enumerate(tiles):
        for rx, kind in enumerate(row):
            x, y = rx * TILE, ry * TILE
            base = {"water": "water", "water2": "water2", "grass2": "grass2"}.get(kind, "grass")
            if kind == "road":
                base = "road"
            out.append(f'<rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" fill="{t[base]}"/>')
            if kind == "tree":
                out.append(f'<rect x="{x + 5}" y="{y + 7}" width="2" height="4" fill="{t["trunk"]}"/>'
                           f'<rect x="{x + 2}" y="{y + 1}" width="8" height="7" rx="2" fill="{t["tree"]}"/>')
    for hx, hy in houses:
        x, y = hx * TILE, hy * TILE
        out.append(f'<rect x="{x + 1}" y="{y + 5}" width="{2 * TILE - 2}" height="{TILE - 5}" fill="{t["wall"]}"/>'
                   f'<path d="M{x},{y + 6} L{x + TILE},{y} L{x + 2 * TILE},{y + 6} Z" fill="{t["roof"]}"/>')
    for i, (d, dur, begin) in enumerate(paths):
        out.append(f'<circle r="2.6" fill="{t["npc"]}"><animateMotion dur="{dur}s" begin="{begin:.1f}s" '
                   f'repeatCount="indefinite" path="{d}"/></circle>')
    out.append(f'<rect class="night" width="{mw}" height="{mh}" fill="{t["night"]}" opacity="0"/>')
    for hx, hy in houses:
        out.append(f'<rect class="lamp" x="{hx * TILE + 10}" y="{hy * TILE + 7}" width="4" height="3" fill="#ffd866" opacity="0"/>')
    out.append('</g>')
    out.append(f'<rect x="0.5" y="0.5" width="{mw - 1}" height="{mh - 1}" rx="6" fill="none" stroke="{t["border"]}"/>')
    out.append(f'<text x="0" y="{mh + 20}" class="sub" style="font-size:11px">seed {SEED} · {len(houses)} houses · '
               f'{len(paths)} npcs · same seed, same world</text>')
    out.append("</g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    here = Path(__file__).parent
    for name in THEMES:
        (here / f"header-{name}.svg").write_text(render(name), encoding="utf-8")
        print("wrote", here / f"header-{name}.svg")
