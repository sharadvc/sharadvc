#!/usr/bin/env python3
"""Generate a live terminal-style SVG card with real merged-PR stats.

Counts PRs authored by OWNER that were merged into repos they don't own,
then renders a macOS-style terminal window as an SVG with subtle animations.
Output: dist/terminal.svg
"""
import html
import os
import subprocess
import time
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

OWNER = "sharadvc"
W = 560
PAD_X = 24
MONO = "'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace"


def fetch_merged_prs() -> Counter:
    """Fetch merged PR counts per repo, excluding OWNER's own repos."""
    q = f"search/issues?q=type:pr+author:{OWNER}+is:merged&per_page=100"
    for attempt in range(5):
        r = subprocess.run(
            ["gh", "api", q, "--paginate", "--jq", ".items[] | .repository_url"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            break
        print(f"gh api failed (attempt {attempt + 1}): {r.stderr.strip()}", flush=True)
        time.sleep(30)
    else:
        raise SystemExit("search API unavailable")

    repos = [
        line.replace("https://api.github.com/repos/", "").strip()
        for line in r.stdout.splitlines()
        if line.strip() and not line.replace("https://api.github.com/repos/", "")
        .strip().lower().startswith(f"{OWNER.lower()}/")
    ]
    return Counter(repos)


def wrap_summary(counts: Counter, max_chars: int = 68) -> list[str]:
    parts = [f"{n}×{repo.split('/', 1)[1]}" for repo, n in counts.most_common()]
    lines, cur = [], ""
    for p in parts:
        candidate = f"{cur} · {p}" if cur else p
        if len(candidate) > max_chars and cur:
            lines.append(cur)
            cur = p
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    return lines


def build_svg(total: int, counts: Counter) -> str:
    e = html.escape
    lines: list[tuple[str, str, float]] = []  # (kind, text, y)
    y = 66

    def add(kind: str, text: str) -> None:
        nonlocal y
        lines.append((kind, text, y))
        y += 24 if kind != "count" else 28

    add("cmd", "$ whoami")
    add("out", f"{OWNER} · OSS. Coffee ☕")
    add("cmd", "$ gh pr list --author {0} --state merged".format(OWNER))
    add("count", f"{total} merged into other people's repos")
    for s in wrap_summary(counts):
        add("dim", s)
    cur_y = y
    height = cur_y + 34

    colors = {
        "cmd": "#e6edf3", "out": "#c9d1d9", "dim": "#7d8590", "count": "#a371f7",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">',
        "<style>",
        ".ln{opacity:0;animation:f .45s ease forwards}",
        "@keyframes f{to{opacity:1}}",
        ".cur{animation:b 1.1s steps(2,start) infinite}",
        "@keyframes b{50%{opacity:0}}",
        "</style>",
        f'<rect width="{W}" height="{height}" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<circle cx="30" cy="30" r="6" fill="#ff5f56"/>',
        '<circle cx="50" cy="30" r="6" fill="#ffbd2e"/>',
        '<circle cx="70" cy="30" r="6" fill="#27c93f"/>',
        f'<text x="{W // 2}" y="35" text-anchor="middle" font-family={MONO_ATTR} font-size="12" fill="#7d8590">{OWNER}@github — zsh</text>',
    ]
    delay = 0.15
    for kind, text, ly in lines:
        if kind == "cmd":
            content = f'<tspan fill="#3fb950">$ </tspan><tspan fill="{colors[kind]}">{e(text[2:])}</tspan>'
            fs = 13
        elif kind == "count":
            n, rest = text.split(" ", 1)
            content = (
                f'<tspan font-size="17" font-weight="bold" fill="#a371f7">{e(n)}</tspan>'
                f'<tspan font-size="14" fill="#e6edf3"> {e(rest)}</tspan>'
            )
            fs = 15
        else:
            content = f'<tspan fill="{colors[kind]}">{e(text)}</tspan>'
            fs = 12 if kind == "dim" else 13
        parts.append(
            f'<text class="ln" x="{PAD_X}" y="{ly}" font-family={MONO_ATTR} font-size="{fs}" '
            f'style="animation-delay:{delay:.2f}s">{content}</text>'
        )
        delay += 0.25
    parts.append(
        f'<text class="cur" x="{PAD_X}" y="{cur_y}" font-family={MONO_ATTR} font-size="14" '
        f'fill="#3fb950">▊</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


MONO_ATTR = '"ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"'


def main() -> None:
    counts = fetch_merged_prs()
    total = sum(counts.values())
    svg = build_svg(total, counts)
    ElementTree.fromstring(svg)  # validate XML
    out = Path("dist/terminal.svg")
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"terminal.svg written: {total} merged PRs across {len(counts)} repos")


if __name__ == "__main__":
    main()
