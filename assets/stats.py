"""Generates the stats card SVGs (dark + light) in the same style as the header.

Runs in GitHub Actions (see .github/workflows/stats.yml) with GITHUB_TOKEN.

    GITHUB_TOKEN=... python3 assets/stats.py [login]
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

from generate import THEMES

W, H = 880, 196

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}
"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    u = body["data"]["user"]
    repos = u["repositories"]
    cc = u["contributionsCollection"]

    langs = {}
    for repo in repos["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name in ("Jupyter Notebook", "HTML", "CSS", "SCSS", "Dockerfile", "Shell", "PowerShell", "Batchfile"):
                continue
            cur = langs.setdefault(name, [0, e["node"]["color"] or "#8b949e"])
            cur[0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": cc["totalPullRequestContributions"],
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "weeks": [sum(d["contributionCount"] for d in w["contributionDays"])
                  for w in cc["contributionCalendar"]["weeks"]][-52:],
        "languages": [(n, v[0] / total, v[1]) for n, v in top],
    }


def render(data, theme_name):
    t = THEMES[theme_name]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="{data["contributions"]} contributions in the last year, {data["repos"]} public repositories, '
           f'{data["stars"]} stars.">']
    out.append(f"""<style>
  text {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 13px; }}
  .p {{ fill: {t['prompt']}; }} .k {{ fill: {t['key']}; }} .v {{ fill: {t['text']}; }} .s {{ fill: {t['dim']}; font-size: 11px; }}
  .bar {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(0); animation: grow .6s ease-out forwards; }}
  @keyframes grow {{ to {{ transform: scaleY(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ .bar {{ animation: none; transform: none; }} }}
</style>""")
    out.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>')
    out.append(f'<text x="34" y="40" class="p">$ living-world stats --npc alan</text>')

    rows = [
        ("contributions", f'{data["contributions"]:,}', "last 12 months"),
        ("commits", f'{data["commits"]:,}', ""),
        ("pull requests", f'{data["prs"]:,}', ""),
        ("public repos", f'{data["repos"]:,}', f'{data["stars"]:,} stars'),
    ]
    y = 66
    for k, v, note in rows:
        out.append(f'<text x="34" y="{y}" class="k">{k}</text><text x="160" y="{y}" class="v">{v}</text>')
        if note:
            out.append(f'<text x="{160 + 9 * len(v) + 10}" y="{y}" class="s">{note}</text>')
        y += 20

    # weekly contributions, last 52 weeks
    bx, by, bw, bh = 470, 34, 376, 74
    peak = max(data["weeks"] or [1]) or 1
    step = bw / max(len(data["weeks"]), 1)
    for i, c in enumerate(data["weeks"]):
        h = max(2, c / peak * bh) if c else 1
        op = 0.25 if c == 0 else 0.45 + 0.55 * c / peak
        out.append(f'<rect class="bar" style="animation-delay:{i * 0.012:.3f}s" x="{bx + i * step:.1f}" y="{by + bh - h:.1f}" '
                   f'width="{step - 2:.1f}" height="{h:.1f}" rx="1" fill="{t["accent"]}" opacity="{op:.2f}"/>')
    out.append(f'<text x="{bx}" y="{by + bh + 18}" class="s">weekly activity · last 52 weeks</text>')

    # languages: one thin stacked bar + legend
    lx, ly, lw = 34, 176, W - 68
    x = lx
    total = sum(p for _, p, _ in data["languages"]) or 1
    out.append(f'<clipPath id="lb"><rect x="{lx}" y="{ly - 24}" width="{lw}" height="6" rx="3"/></clipPath><g clip-path="url(#lb)">')
    for name, p, color in data["languages"]:
        w = lw * p / total
        out.append(f'<rect x="{x:.1f}" y="{ly - 24}" width="{w:.1f}" height="6" fill="{color}" opacity=".85"/>')
        x += w
    out.append("</g>")
    x = lx
    for name, p, color in data["languages"]:
        label = f"{name} {p * 100:.0f}%"
        out.append(f'<circle cx="{x + 4}" cy="{ly - 4}" r="4" fill="{color}" opacity=".85"/>'
                   f'<text x="{x + 14}" y="{ly}" class="s">{label}</text>')
        x += 14 + 7 * len(label) + 22
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    login = sys.argv[1] if len(sys.argv) > 1 else "AlanEdward19"
    data = fetch(login, os.environ["GITHUB_TOKEN"])
    here = Path(__file__).parent
    for name in THEMES:
        (here / f"stats-{name}.svg").write_text(render(data, name), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "weeks"}, indent=2))
