# -*- coding: utf-8 -*-
"""Developer tool: generates an interactive HTML overview of all materials
and their production-chain connections, straight from the game data.

Usage:  python chain_overview.py        (writes + opens chain_overview.html)

The page always reflects the current state of space_station_idle.py, so it
stays up to date automatically when new materials or buildings are added.
"""

import os
import webbrowser

import space_station_idle as game

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "chain_overview.html")

NODE_W, NODE_H = 235, 96

CHAIN_NAMES = {
    game.C_METAL: "Iron / Steel",
    game.C_COAL: "Coal",
    game.C_COPPER: "Copper / Cables",
    game.C_SILICON: "Silicon / Electronics",
    game.C_OIL: "Oil / Plastic",
    game.C_MECH: "Mechanics",
    game.C_ROBOT: "Robotics",
}


def tier_of(mat, _cache={}):
    if mat in _cache:
        return _cache[mat]
    inputs = game.BUILDINGS[game.PRODUCER[mat]]["inputs"]
    t = 0 if not inputs else 1 + max(tier_of(i) for i in inputs)
    _cache[mat] = t
    return t


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_svg():
    xs = [info["pos"][0] for info in game.MATERIALS.values()]
    ys = [info["pos"][1] for info in game.MATERIALS.values()]
    width = max(xs) + NODE_W + 60
    height = max(ys) + NODE_H + 60

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             f'xmlns="http://www.w3.org/2000/svg" '
             f'style="width:100%;height:auto;background:#0b0f1a;'
             f'border-radius:12px">']

    # One arrowhead marker per chain color
    colors = sorted({info["color"] for info in game.MATERIALS.values()})
    parts.append("<defs>")
    for i, col in enumerate(colors):
        parts.append(
            f'<marker id="arrow{i}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    parts.append("</defs>")
    marker_of = {col: f"arrow{i}" for i, col in enumerate(colors)}

    # Edges (input -> output), colored by the input's chain
    for bname, b in game.BUILDINGS.items():
        out = b["output"]
        ox, oy = game.MATERIALS[out]["pos"]
        for inp in b["inputs"]:
            ix, iy = game.MATERIALS[inp]["pos"]
            col = game.MATERIALS[inp]["color"]
            x1, y1 = ix + NODE_W / 2, iy + NODE_H
            x2, y2 = ox + NODE_W / 2, oy
            parts.append(
                f'<path d="M {x1} {y1} C {x1} {y1 + 55}, {x2} {y2 - 55}, '
                f'{x2} {y2 - 4}" fill="none" stroke="{col}" '
                f'stroke-width="2.5" opacity="0.65" '
                f'marker-end="url(#{marker_of[col]})">'
                f'<title>{esc(inp)} → {esc(bname)} → {esc(out)}</title></path>')

    # Nodes
    for mat, info in game.MATERIALS.items():
        x, y = info["pos"]
        col = info["color"]
        bname = game.PRODUCER[mat]
        b = game.BUILDINGS[bname]
        used_by = game.CONSUMERS[mat]
        tooltip = (f"{mat} (Tier {tier_of(mat)})\n"
                   f"Price: {info['price']} Cr\n"
                   f"Produced by: {bname}"
                   + (f"\nInputs: {', '.join(b['inputs'])}" if b["inputs"] else "")
                   + (f"\nUsed by: {', '.join(used_by)}" if used_by
                      else "\nUsed by: — (endpoint)"))
        endpoint = not used_by and not b["extraction"]
        stroke = "#fbbf24" if endpoint else col
        dash = ' stroke-dasharray="6 4"' if endpoint else ""
        parts.append(
            f'<g><title>{esc(tooltip)}</title>'
            f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" '
            f'rx="14" fill="#151d33" stroke="{stroke}" stroke-width="2"{dash}/>'
            f'<text x="{x + 14}" y="{y + 26}" fill="{col}" '
            f'font-size="15" font-weight="bold" font-family="Segoe UI">'
            f'{esc(info["emoji"])} {esc(mat)}</text>'
            f'<text x="{x + 14}" y="{y + 50}" fill="#fbbf24" font-size="12" '
            f'font-family="Segoe UI">{info["price"]} Cr  ·  Tier {tier_of(mat)}</text>'
            f'<text x="{x + 14}" y="{y + 72}" fill="#8fa3c8" font-size="12" '
            f'font-family="Segoe UI">{esc(bname)}'
            f'{" (raw)" if b["extraction"] else ""}</text></g>')

    parts.append("</svg>")
    return "".join(parts)


def build_table():
    rows = []
    mats = sorted(game.MATERIALS, key=lambda m: (tier_of(m), m))
    for mat in mats:
        info = game.MATERIALS[mat]
        bname = game.PRODUCER[mat]
        b = game.BUILDINGS[bname]
        used_by = game.CONSUMERS[mat]
        used = ", ".join(f"{game.BUILDINGS[c]['output']} ({c})" for c in used_by) \
            if used_by else '<span class="endpoint">— endpoint</span>'
        inputs = ", ".join(b["inputs"]) if b["inputs"] else "—"
        rows.append(
            f"<tr><td><span style='color:{info['color']}'>{esc(info['emoji'])} "
            f"<b>{esc(mat)}</b></span></td><td>{tier_of(mat)}</td>"
            f"<td>{info['price']} Cr</td><td>{esc(bname)}</td>"
            f"<td>{esc(inputs)}</td><td>{used}</td></tr>")
    return "\n".join(rows)


def build_notes():
    endpoints = [m for m in game.MATERIALS
                 if not game.CONSUMERS[m]
                 and not game.BUILDINGS[game.PRODUCER[m]]["extraction"]]
    usage = sorted(((m, len(game.CONSUMERS[m])) for m in game.MATERIALS),
                   key=lambda kv: -kv[1])
    hubs = [f"{m} ({n}×)" for m, n in usage[:5] if n > 0]
    max_tier = max(tier_of(m) for m in game.MATERIALS)
    return f"""
    <ul>
      <li><b>{len(game.MATERIALS)}</b> materials, <b>{len(game.BUILDINGS)}</b>
          buildings, deepest tier: <b>{max_tier}</b></li>
      <li><b>Endpoints</b> (produced but never consumed — natural docking
          points for new chains): <b>{esc(', '.join(endpoints) or '—')}</b></li>
      <li><b>Most-used inputs</b>: {esc(', '.join(hubs))}</li>
      <li>Every new building needs: an <b>output material</b> (emoji, price,
          position, chain color) in <code>MATERIALS</code> and a recipe in
          <code>BUILDINGS</code>. Rule of thumb for prices:
          <b>sum of input prices × 2</b>.</li>
      <li>Unlock logic is automatic: a building appears once all its input
          materials have been produced at least once.</li>
    </ul>"""


def legend():
    items = "".join(
        f'<span class="chip" style="border-color:{col};color:{col}">'
        f'{esc(name)}</span>' for col, name in CHAIN_NAMES.items())
    return (items + '<span class="chip" style="border-color:#fbbf24;'
            'color:#fbbf24;border-style:dashed">endpoint (free)</span>')


def main():
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Space Station Idle — Chain Overview (v{game.VERSION})</title>
<style>
  body {{ background:#0e1426; color:#e8eefc; font-family:'Segoe UI',sans-serif;
         margin:0; padding:24px 32px; }}
  h1 {{ font-size:22px; }} h2 {{ font-size:16px; margin-top:32px; }}
  .dim {{ color:#8fa3c8; }}
  .chip {{ display:inline-block; border:1.5px solid; border-radius:99px;
          padding:2px 12px; margin:0 8px 8px 0; font-size:12px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th, td {{ text-align:left; padding:7px 12px;
           border-bottom:1px solid #22315c; }}
  th {{ color:#8fa3c8; font-size:11px; text-transform:uppercase; }}
  tr:hover td {{ background:#151d33; }}
  .endpoint {{ color:#fbbf24; }}
  code {{ background:#151d33; padding:1px 6px; border-radius:6px; }}
</style></head><body>
<h1>🚀 Space Station Idle — Production Chain Overview
    <span class="dim">v{game.VERSION}</span></h1>
<p class="dim">Generated from the live game data — rerun
<code>python chain_overview.py</code> after changes. Hover nodes and lines
for details.</p>
<div>{legend()}</div>
{build_svg()}
<h2>Extension notes</h2>
{build_notes()}
<h2>All materials</h2>
<table>
<tr><th>Material</th><th>Tier</th><th>Price</th><th>Produced by</th>
<th>Inputs</th><th>Used by</th></tr>
{build_table()}
</table>
</body></html>"""
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written: {OUT_FILE}")
    webbrowser.open(OUT_FILE)


if __name__ == "__main__":
    main()
