# -*- coding: utf-8 -*-
"""
Space Station Idle — Chain Editor
Building-focused browser UI for managing the production chain.

Usage:  python chain_editor.py
        Opens http://localhost:7331 automatically.
        All changes write directly to space_station_idle.py.
"""

import importlib
import json
import os
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ── paths ─────────────────────────────────────────────────────────────────────
HERE      = os.path.dirname(os.path.abspath(__file__))
GAME_FILE = os.path.join(HERE, "space_station_idle.py")
PORT      = 7331

MAT_MARKER = "    # END_MATERIALS"
BLD_MARKER = "    # END_BUILDINGS"

CHAIN_COLORS = {
    "Metal (blue)":       "C_METAL",
    "Coal (gray)":        "C_COAL",
    "Copper (orange)":    "C_COPPER",
    "Silicon (green)":    "C_SILICON",
    "Oil (yellow)":       "C_OIL",
    "Mechanics (purple)": "C_MECH",
    "Robotics (pink)":    "C_ROBOT",
}


# ── game module ───────────────────────────────────────────────────────────────
def load_game():
    mod = "space_station_idle"
    if mod in sys.modules:
        return importlib.reload(sys.modules[mod])
    import space_station_idle
    return space_station_idle


# ── markers ───────────────────────────────────────────────────────────────────
def ensure_markers():
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    changed = False
    if MAT_MARKER not in src:
        src = src.replace(
            "}\n\n# Buildings in production order",
            f"{MAT_MARKER}\n}}\n\n# Buildings in production order",
        )
        changed = True
    if BLD_MARKER not in src:
        src = src.replace(
            "}\n\nBUILDING_ORDER",
            f"{BLD_MARKER}\n}}\n\nBUILDING_ORDER",
        )
        changed = True
    if changed:
        with open(GAME_FILE, "w", encoding="utf-8") as f:
            f.write(src)


# ── line builders ─────────────────────────────────────────────────────────────
def _mat_line(d):
    return (f'    "{d["name"]}": {{"emoji": "{d["emoji"]}", '
            f'"price": {int(d["price"])}, '
            f'"pos": ({int(d["x"])}, {int(d["y"])}), '
            f'"color": {d["color_const"]}}},\n')


def _bld_line(d):
    inputs    = [i.strip() for i in d["inputs"] if str(i).strip()]
    mat_costs = {k.strip(): int(v) for k, v in d["materials"].items() if k.strip()}
    mats_py   = ("{" + ", ".join(f'"{k}": {v}' for k, v in mat_costs.items()) + "}"
                 if mat_costs else "{}")
    return (f'    "{d["name"]}": {{"output": "{d["output"]}", "inputs": {repr(inputs)}, '
            f'"credits": {int(d["credits"])}, "materials": {mats_py}, '
            f'"extraction": {bool(d.get("extraction", False))}}},\n')


# ── atomic save (building + optional new/updated material) ────────────────────
def save_building(d):
    """Add or update a building, optionally creating/updating its output material."""
    mode     = d.get("mode", "add")
    bld      = d["building"]
    new_mat  = d.get("new_material")   # set when output is a brand-new material
    mat_edit = d.get("mat_edit")       # set when editing an existing material's props

    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()

    bname = bld["name"]

    if mode == "add":
        if f'"{bname}":' in src:
            raise ValueError(f'Building "{bname}" already exists')
        if new_mat:
            mname = new_mat["name"]
            if f'"{mname}":' in src:
                raise ValueError(f'Material "{mname}" already exists')
            src = src.replace(MAT_MARKER, _mat_line(new_mat) + MAT_MARKER)
        src = src.replace(BLD_MARKER, _bld_line(bld) + BLD_MARKER)
    else:  # edit
        pat = re.compile(rf'^    "{re.escape(bname)}"[^\n]*\n', re.MULTILINE)
        if not pat.search(src):
            raise ValueError(f'Building "{bname}" not found')
        src = pat.sub(_bld_line(bld), src, count=1)
        if mat_edit:
            mp = re.compile(rf'^    "{re.escape(mat_edit["name"])}"[^\n]*\n', re.MULTILINE)
            if mp.search(src):
                src = mp.sub(_mat_line(mat_edit), src, count=1)

    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src)


# ── delete building + its material ────────────────────────────────────────────
def delete_building_full(name):
    g = load_game()
    if name not in g.BUILDINGS:
        raise ValueError(f'"{name}" not found')
    output     = g.BUILDINGS[name]["output"]
    other_uses = [c for c in g.CONSUMERS.get(output, []) if c != name]
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    src = re.sub(rf'^    "{re.escape(name)}"[^\n]*\n',   "", src, flags=re.MULTILINE)
    if not other_uses:
        src = re.sub(rf'^    "{re.escape(output)}"[^\n]*\n', "", src, flags=re.MULTILINE)
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src)
    return {"mat_deleted": not bool(other_uses), "mat": output}


# ── data for the browser ──────────────────────────────────────────────────────
def get_data():
    g = load_game()
    const_of = {getattr(g, c): c
                for c in ["C_METAL", "C_COAL", "C_COPPER",
                          "C_SILICON", "C_OIL", "C_MECH", "C_ROBOT"]}
    materials = {
        name: {
            "emoji":       info["emoji"],
            "price":       info["price"],
            "x":           info["pos"][0],
            "y":           info["pos"][1],
            "color":       info["color"],
            "color_const": const_of.get(info["color"], "C_METAL"),
        }
        for name, info in g.MATERIALS.items()
    }
    buildings = {
        name: {
            "output":     b["output"],
            "inputs":     b["inputs"],
            "credits":    b["credits"],
            "materials":  b["materials"],
            "extraction": b["extraction"],
        }
        for name, b in g.BUILDINGS.items()
    }
    return {
        "materials":    materials,
        "buildings":    buildings,
        "chain_colors": CHAIN_COLORS,
        "color_values": {c: getattr(g, c) for c in CHAIN_COLORS.values()},
        "version":      g.VERSION,
    }


# ── SVG ───────────────────────────────────────────────────────────────────────
def build_svg():
    g = load_game()
    NW, NH = 235, 96

    def esc(s):
        return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    xs = [i["pos"][0] for i in g.MATERIALS.values()]
    ys = [i["pos"][1] for i in g.MATERIALS.values()]
    W, H = max(xs) + NW + 80, max(ys) + NH + 80

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
             f'style="width:100%;height:auto;background:#0b0f1a;border-radius:12px">']

    colors = sorted({i["color"] for i in g.MATERIALS.values()})
    parts.append("<defs>")
    for idx, col in enumerate(colors):
        parts.append(
            f'<marker id="a{idx}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    parts.append("</defs>")
    mk = {col: f"a{idx}" for idx, col in enumerate(colors)}

    for bname, b in g.BUILDINGS.items():
        out = b["output"]
        if out not in g.MATERIALS:
            continue
        ox, oy = g.MATERIALS[out]["pos"]
        for inp in b["inputs"]:
            if inp not in g.MATERIALS:
                continue
            ix, iy = g.MATERIALS[inp]["pos"]
            col    = g.MATERIALS[inp]["color"]
            x1, y1 = ix + NW/2, iy + NH
            x2, y2 = ox + NW/2, oy
            parts.append(
                f'<path d="M {x1} {y1} C {x1} {y1+55},{x2} {y2-55},{x2} {y2-4}" '
                f'fill="none" stroke="{col}" stroke-width="2.5" opacity="0.65" '
                f'marker-end="url(#{mk[col]})">'
                f'<title>{esc(inp)} → {esc(bname)} → {esc(out)}</title></path>')

    for mat, info in g.MATERIALS.items():
        x, y  = info["pos"]
        col   = info["color"]
        bname = g.PRODUCER.get(mat)
        b     = g.BUILDINGS.get(bname, {})
        used  = g.CONSUMERS.get(mat, [])
        ep    = not used and not b.get("extraction", False)
        stroke = "#fbbf24" if ep else col
        dash   = ' stroke-dasharray="6 4"' if ep else ""
        tip    = (f"{esc(mat)}\nPrice: {info['price']} Cr"
                  f"\nProduced by: {esc(bname) if bname else '— none —'}"
                  + (f"\nInputs: {', '.join(b['inputs'])}" if b.get("inputs") else "")
                  + (f"\nUsed by: {', '.join(used)}" if used else "\nEndpoint"))
        parts.append(
            f'<g><title>{tip}</title>'
            f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" '
            f'rx="14" fill="#151d33" stroke="{stroke}" stroke-width="2"{dash}/>'
            f'<text x="{x+14}" y="{y+30}" fill="{col}" '
            f'font-size="15" font-weight="bold" font-family="Segoe UI">'
            f'{esc(info["emoji"])} {esc(mat)}</text>'
            f'<text x="{x+14}" y="{y+56}" fill="#fbbf24" font-size="12" '
            f'font-family="Segoe UI">{info["price"]} Cr</text>'
            f'<text x="{x+14}" y="{y+78}" fill="#8fa3c8" font-size="12" '
            f'font-family="Segoe UI">{esc(bname) if bname else "no building"}'
            f'{"  (raw)" if b.get("extraction") else ""}</text></g>')

    parts.append("</svg>")
    return "".join(parts)


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Space Station Idle — Chain Editor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0f1a;color:#e8eefc;font-family:'Segoe UI',sans-serif;
     height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:#0e1426;padding:11px 22px;border-bottom:1px solid #1e2d50;
       display:flex;align-items:center;gap:10px;flex-shrink:0}
header h1{font-size:15px;font-weight:600}
.badge{background:#1e2d50;color:#8fa3c8;padding:2px 10px;border-radius:99px;font-size:12px}
.main{display:flex;flex:1;overflow:hidden}

/* sidebar */
.sidebar{width:400px;min-width:280px;display:flex;flex-direction:column;
         background:#0e1426;border-right:1px solid #1e2d50}
.stoolbar{display:flex;align-items:center;justify-content:space-between;
          padding:12px 16px;border-bottom:1px solid #1a2440;flex-shrink:0}
.stoolbar h2{font-size:12px;text-transform:uppercase;color:#8fa3c8;letter-spacing:.08em}
.btn-add{background:#2563eb;color:#fff;border:none;border-radius:8px;
         padding:7px 14px;font-size:12px;cursor:pointer;font-family:inherit;
         transition:background .15s}
.btn-add:hover{background:#1d4ed8}
.blist{flex:1;overflow-y:auto;padding:10px 12px;display:flex;flex-direction:column;gap:5px}
.brow{display:flex;align-items:center;gap:8px;background:#151d33;border-radius:9px;
      padding:9px 11px;font-size:13px;cursor:default}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.bname{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1}
.barrow{color:#556b8f;flex-shrink:0}
.bout{color:#fbbf24;font-size:12px;white-space:nowrap;flex-shrink:0}
.binp{color:#556b8f;font-size:11px;white-space:nowrap;overflow:hidden;
      text-overflow:ellipsis;min-width:0;flex:1}
.bact{display:flex;gap:5px;flex-shrink:0;margin-left:4px}
.bi{background:none;border:1px solid #22315c;color:#8fa3c8;border-radius:6px;
    padding:3px 8px;cursor:pointer;font-size:11px;font-family:inherit;transition:all .15s}
.bi:hover{background:#1a2440;color:#e8eefc}
.bi.del:hover{border-color:#f87171;color:#f87171}

/* SVG pane */
.svgpane{flex:1;overflow:auto;padding:20px;background:#0b0f1a}

/* modal */
.mbg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:100;
     align-items:flex-start;justify-content:center;padding-top:30px;overflow-y:auto}
.mbg.on{display:flex}
.modal{background:#0e1526;border:1px solid #1e2d50;border-radius:16px;
       padding:26px;width:500px;margin-bottom:30px}
.modal h2{font-size:15px;margin-bottom:20px}

/* form elements */
.sec{font-size:11px;text-transform:uppercase;color:#8fa3c8;letter-spacing:.07em;
     margin:18px 0 8px;padding-bottom:6px;border-bottom:1px solid #1a2440}
.sec:first-of-type{margin-top:0}
.fr{margin-bottom:11px}
.fr label{display:block;font-size:12px;color:#8fa3c8;margin-bottom:4px}
.fr input,.fr select{width:100%;background:#151d33;border:1px solid #22315c;
  border-radius:8px;color:#e8eefc;padding:8px 11px;font-size:13px;outline:none;
  font-family:inherit}
.fr input:focus,.fr select:focus{border-color:#60a5fa}
.fr input[readonly]{color:#556b8f;cursor:default}
.row{display:flex;gap:10px}
.row .fr{flex:1;margin-bottom:0}
.hint{font-size:11px;color:#556b8f;margin-top:3px}
.new-mat-box{background:#0b1020;border:1px solid #1e2d50;border-radius:10px;
             padding:14px;margin-top:8px}
.inps-row{display:flex;gap:8px}
.inps-row .fr{flex:1;margin-bottom:0}
.cost-row{display:flex;gap:8px;align-items:center;margin-bottom:7px}
.cost-row .fr{flex:1;margin-bottom:0}
.cost-row .amt{width:80px!important;flex:none}
.add-row-btn{background:none;border:1px dashed #22315c;color:#556b8f;border-radius:7px;
             padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit;
             width:100%;margin-top:4px;transition:all .15s}
.add-row-btn:hover{border-color:#60a5fa;color:#8fa3c8}
.cb-row{display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer}
.cb-row input{width:auto!important;margin:0}
.mfoot{display:flex;justify-content:flex-end;gap:10px;margin-top:22px}
.btn{padding:9px 20px;border-radius:9px;font-size:13px;cursor:pointer;border:none;
     font-family:inherit;transition:all .15s}
.bc{background:#151d33;color:#8fa3c8;border:1px solid #22315c}
.bc:hover{background:#1a2440;color:#e8eefc}
.bp{background:#2563eb;color:#fff}
.bp:hover{background:#1d4ed8}

/* toast */
.toast{position:fixed;bottom:22px;right:22px;background:#1a2e1a;border:1px solid #4ade80;
       color:#4ade80;padding:11px 18px;border-radius:10px;font-size:13px;z-index:200;
       opacity:0;transform:translateY(14px);transition:all .25s;pointer-events:none}
.toast.err{background:#2d1414;border-color:#f87171;color:#f87171}
.toast.on{opacity:1;transform:none}
</style></head>
<body>
<header>
  <span>🚀</span>
  <h1>Space Station Idle — Chain Editor</h1>
  <span class="badge" id="vbadge">v?</span>
  <span class="badge" id="cbadge">…</span>
</header>

<div class="main">
  <div class="sidebar">
    <div class="stoolbar">
      <h2>Buildings</h2>
      <button class="btn-add" onclick="openModal()">＋ New Building</button>
    </div>
    <div class="blist" id="blist"></div>
  </div>
  <div class="svgpane" id="svgpane">
    <div style="color:#8fa3c8;font-size:13px">Loading…</div>
  </div>
</div>

<!-- Building Modal -->
<div class="mbg" id="modal">
 <div class="modal">
  <h2 id="modal-title">New Building</h2>
  <input type="hidden" id="mode" value="add">

  <div class="sec">Building Name</div>
  <div class="fr">
    <input id="bname" placeholder="e.g. Iron Smelter">
  </div>

  <div class="sec">Produces</div>
  <div class="fr">
    <label>Output Material</label>
    <select id="output" onchange="onOutputChange()">
      <option value="">— select —</option>
    </select>
  </div>
  <!-- New material inline form -->
  <div id="new-mat-box" class="new-mat-box" style="display:none">
    <div class="row">
      <div class="fr"><label>Material Name</label>
        <input id="mat-name" placeholder="e.g. Iron Ingot"></div>
      <div class="fr" style="max-width:72px"><label>Emoji</label>
        <input id="mat-emoji" placeholder="🧱"></div>
    </div>
    <div class="row">
      <div class="fr"><label>Sell Price (Cr)</label>
        <input id="mat-price" type="number" min="1" placeholder="6"></div>
      <div class="fr"><label>Chain Color</label>
        <select id="mat-color"></select></div>
    </div>
    <div class="hint">Position is calculated automatically from inputs.</div>
  </div>
  <!-- Existing material edit (edit mode) -->
  <div id="mat-edit-box" style="display:none">
    <div class="row">
      <div class="fr" style="max-width:72px"><label>Emoji</label>
        <input id="mat-edit-emoji" placeholder="🧱"></div>
      <div class="fr"><label>Sell Price (Cr)</label>
        <input id="mat-edit-price" type="number" min="1"></div>
      <div class="fr"><label>Chain Color</label>
        <select id="mat-edit-color"></select></div>
    </div>
  </div>

  <div class="sec">Consumes to produce <span style="color:#556b8f;font-size:10px">(3× each per cycle)</span></div>
  <div class="inps-row" id="inps-row">
    <div class="fr"><label>Input 1</label>
      <select class="inp" onchange="onInputChange()"><option value="">— none —</option></select></div>
    <div class="fr"><label>Input 2</label>
      <select class="inp" onchange="onInputChange()"><option value="">— none —</option></select></div>
    <div class="fr"><label>Input 3</label>
      <select class="inp" onchange="onInputChange()"><option value="">— none —</option></select></div>
  </div>
  <div class="fr">
    <label class="cb-row">
      <input type="checkbox" id="extraction" onchange="onExtractionChange()">
      Raw resource — no inputs needed
    </label>
  </div>

  <div class="sec">Build Cost</div>
  <div class="row">
    <div class="fr"><label>Credits</label>
      <input id="credits" type="number" min="50" placeholder="100">
      <div class="hint" id="credits-hint"></div></div>
  </div>
  <div class="fr">
    <label>Materials needed in warehouse</label>
    <div id="cost-rows"></div>
    <button class="add-row-btn" onclick="addCostRow()">＋ Add material row</button>
  </div>

  <div class="mfoot">
    <button class="btn bc" onclick="closeModal()">Cancel</button>
    <button class="btn bp" id="save-btn" onclick="saveBuilding()">Save Building</button>
  </div>
 </div>
</div>

<div class="toast" id="toast"></div>

<script>
let D = {};

async function init() { await reload(); await reloadSvg(); }

async function reload() {
  const r = await fetch('/api/data'); D = await r.json();
  document.getElementById('vbadge').textContent = 'v' + D.version;
  const nc = Object.keys(D.buildings).length;
  document.getElementById('cbadge').textContent = nc + ' buildings';
  renderList();
  fillColorSelects();
}

async function reloadSvg() {
  const r = await fetch('/api/svg');
  document.getElementById('svgpane').innerHTML = await r.text();
}

// ── building list ─────────────────────────────────────────────────────────────
function renderList() {
  const el = document.getElementById('blist');
  el.innerHTML = '';
  for (const [name, b] of Object.entries(D.buildings)) {
    const mat   = D.materials[b.output] || {};
    const color = mat.color || '#8fa3c8';
    const emoji = mat.emoji || '';
    const inpTxt = b.inputs.length ? b.inputs.join(' + ') : '(raw resource)';
    const row = document.createElement('div');
    row.className = 'brow';
    row.innerHTML =
      `<span class="dot" style="background:${color}"></span>
       <span class="bname">${name}</span>
       <span class="barrow">→</span>
       <span class="bout">${emoji} ${b.output}</span>
       <span class="binp">${inpTxt}</span>
       <div class="bact">
         <button class="bi" onclick='editBuilding(${JSON.stringify(name)})'>Edit</button>
         <button class="bi del" onclick='deleteBuilding(${JSON.stringify(name)})'>Del</button>
       </div>`;
    el.appendChild(row);
  }
}

// ── modal helpers ─────────────────────────────────────────────────────────────
function fillColorSelects() {
  for (const id of ['mat-color','mat-edit-color']) {
    const sel = document.getElementById(id);
    const cur = sel.value;
    sel.innerHTML = '';
    for (const [label, cconst] of Object.entries(D.chain_colors)) {
      const o = document.createElement('option');
      o.value = cconst; o.textContent = label;
      o.style.color = D.color_values[cconst];
      if (cconst === cur) o.selected = true;
      sel.appendChild(o);
    }
  }
}

function fillOutputSelect(selectedValue) {
  const sel = document.getElementById('output');
  sel.innerHTML = '<option value="">— select —</option>';
  for (const name of Object.keys(D.materials)) {
    const o = document.createElement('option');
    o.value = name; o.textContent = (D.materials[name].emoji||'') + ' ' + name;
    if (name === selectedValue) o.selected = true;
    sel.appendChild(o);
  }
  const newOpt = document.createElement('option');
  newOpt.value = '__new__'; newOpt.textContent = '＋ New material…';
  if (selectedValue === '__new__') newOpt.selected = true;
  sel.appendChild(newOpt);
}

function fillInputSelects(values) {
  for (const sel of document.querySelectorAll('.inp')) {
    const cur = sel.getAttribute('data-val') || '';
    sel.innerHTML = '<option value="">— none —</option>';
    for (const name of Object.keys(D.materials)) {
      const o = document.createElement('option');
      o.value = name; o.textContent = name;
      if (name === cur) o.selected = true;
      sel.appendChild(o);
    }
  }
  if (values) {
    const sels = document.querySelectorAll('.inp');
    for (let i = 0; i < 3; i++)
      if (values[i]) sels[i].value = values[i];
  }
}

function buildCostRows(mats) {
  const container = document.getElementById('cost-rows');
  container.innerHTML = '';
  if (mats && Object.keys(mats).length) {
    for (const [mat, amt] of Object.entries(mats))
      addCostRow(mat, amt);
  }
}

function addCostRow(mat, amt) {
  const container = document.getElementById('cost-rows');
  const row = document.createElement('div');
  row.className = 'cost-row';
  let opts = '<option value="">— none —</option>';
  for (const name of Object.keys(D.materials)) {
    const sel = name === mat ? ' selected' : '';
    opts += `<option value="${name}"${sel}>${name}</option>`;
  }
  row.innerHTML =
    `<div class="fr"><select class="cost-mat">${opts}</select></div>
     <input class="amt" type="number" min="1" value="${amt||10}" placeholder="10">
     <button class="bi del" onclick="this.parentElement.remove()">×</button>`;
  container.appendChild(row);
}

// ── open / close modal ────────────────────────────────────────────────────────
function openModal(editData) {
  const isEdit = !!editData;
  document.getElementById('modal-title').textContent = isEdit ? 'Edit Building' : 'New Building';
  document.getElementById('mode').value = isEdit ? 'edit' : 'add';
  document.getElementById('save-btn').textContent = isEdit ? 'Save Changes' : 'Save Building';

  const bname = document.getElementById('bname');
  bname.value = isEdit ? editData.name : '';
  bname.readOnly = isEdit;
  bname.style.color = isEdit ? '#556b8f' : '';

  fillOutputSelect(isEdit ? editData.output : '');

  document.getElementById('new-mat-box').style.display = 'none';
  document.getElementById('mat-edit-box').style.display = isEdit ? 'block' : 'none';

  if (isEdit) {
    const m = D.materials[editData.output] || {};
    document.getElementById('mat-edit-emoji').value = m.emoji || '';
    document.getElementById('mat-edit-price').value = m.price || '';
    document.getElementById('mat-edit-color').value = m.color_const || 'C_METAL';
  }

  fillInputSelects(isEdit ? editData.inputs : null);
  document.getElementById('extraction').checked = isEdit ? editData.extraction : false;
  document.getElementById('credits').value = isEdit ? editData.credits : '';
  document.getElementById('credits-hint').textContent = '';
  buildCostRows(isEdit ? editData.materials : null);

  onOutputChange();
  onExtractionChange();
  document.getElementById('modal').classList.add('on');
}

function closeModal() {
  document.getElementById('modal').classList.remove('on');
}

function editBuilding(name) {
  openModal({ name, ...D.buildings[name] });
}

// ── form events ───────────────────────────────────────────────────────────────
function onOutputChange() {
  const val = document.getElementById('output').value;
  document.getElementById('new-mat-box').style.display =
    val === '__new__' ? 'block' : 'none';

  // hint for credits
  if (val && val !== '__new__' && D.materials[val]) {
    const p = D.materials[val].price;
    document.getElementById('credits-hint').textContent =
      'Suggested: ~' + Math.round(p * 30) + ' Cr';
  } else {
    document.getElementById('credits-hint').textContent = '';
  }
}

function onInputChange() {
  // auto-calculate position for new material
  if (document.getElementById('output').value !== '__new__') return;
  const inputs = [...document.querySelectorAll('.inp')]
    .map(s => s.value).filter(Boolean);
  const pos = calcPos(inputs);
  // store as data attrs (used in saveBuilding)
  document.getElementById('new-mat-box').dataset.x = pos.x;
  document.getElementById('new-mat-box').dataset.y = pos.y;
}

function onExtractionChange() {
  const ext = document.getElementById('extraction').checked;
  document.getElementById('inps-row').style.opacity = ext ? '0.35' : '1';
  document.getElementById('inps-row').style.pointerEvents = ext ? 'none' : '';
}

function calcPos(inputNames) {
  if (!inputNames.length) {
    const raws = Object.values(D.materials).filter(m => m.y < 120);
    const maxX = raws.length ? Math.max(...raws.map(m => m.x)) : 0;
    return { x: maxX + 270, y: 60 };
  }
  const mats = inputNames.map(n => D.materials[n]).filter(Boolean);
  if (!mats.length) return { x: 500, y: 250 };
  return {
    x: Math.round(mats.reduce((s, m) => s + m.x, 0) / mats.length),
    y: Math.max(...mats.map(m => m.y)) + 190
  };
}

// ── save ──────────────────────────────────────────────────────────────────────
async function saveBuilding() {
  const mode = document.getElementById('mode').value;
  const bname = document.getElementById('bname').value.trim();
  const output = document.getElementById('output').value;
  if (!bname) { toast('Building name is required', true); return; }
  if (!output) { toast('Output material is required', true); return; }

  const inputs = [...document.querySelectorAll('.inp')]
    .map(s => s.value).filter(Boolean);
  const extraction = document.getElementById('extraction').checked;
  const credits = document.getElementById('credits').value || 100;

  const matCosts = {};
  for (const row of document.querySelectorAll('.cost-row')) {
    const m = row.querySelector('.cost-mat').value;
    const a = parseInt(row.querySelector('.amt').value) || 0;
    if (m && a > 0) matCosts[m] = a;
  }

  const bld = {
    name: bname, output: output === '__new__'
      ? document.getElementById('mat-name').value.trim()
      : output,
    inputs: extraction ? [] : inputs,
    credits: parseInt(credits),
    materials: matCosts,
    extraction,
  };

  if (!bld.output) { toast('Material name is required', true); return; }

  const payload = { mode, building: bld };

  if (output === '__new__') {
    const box = document.getElementById('new-mat-box');
    const autoPos = calcPos(inputs);
    payload.new_material = {
      name:        bld.output,
      emoji:       document.getElementById('mat-emoji').value.trim() || '❓',
      price:       parseInt(document.getElementById('mat-price').value) || 1,
      color_const: document.getElementById('mat-color').value,
      x:           parseInt(box.dataset.x) || autoPos.x,
      y:           parseInt(box.dataset.y) || autoPos.y,
    };
    if (!payload.new_material.emoji)
      { toast('Emoji is required for the new material', true); return; }
  }

  if (mode === 'edit') {
    const m = D.materials[output];
    if (m) {
      payload.mat_edit = {
        name:        output,
        emoji:       document.getElementById('mat-edit-emoji').value.trim() || m.emoji,
        price:       parseInt(document.getElementById('mat-edit-price').value) || m.price,
        color_const: document.getElementById('mat-edit-color').value,
        x: m.x, y: m.y,
      };
    }
  }

  const r = await post('/api/save_building', payload);
  if (r.ok) {
    toast((mode === 'edit' ? 'Updated: ' : 'Added: ') + bname);
    closeModal();
    await reload();
    await reloadSvg();
  } else {
    toast(r.error, true);
  }
}

// ── delete ────────────────────────────────────────────────────────────────────
async function deleteBuilding(name) {
  const b   = D.buildings[name];
  const mat = b ? b.output : '';
  if (!confirm(`Delete building "${name}"?\n\nIts output material "${mat}" will also be removed if nothing else uses it.`))
    return;
  const r = await post('/api/delete_building', { name });
  if (r.ok) {
    const msg = r.mat_deleted
      ? `Deleted: ${name} + material ${r.mat}`
      : `Deleted: ${name} (material ${r.mat} kept)`;
    toast(msg);
    await reload();
    await reloadSvg();
  } else {
    toast(r.error, true);
  }
}

// ── utilities ─────────────────────────────────────────────────────────────────
async function post(url, data) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

function toast(msg, err) {
  const el = document.getElementById('toast');
  el.textContent = (err ? '⚠ ' : '✓ ') + msg;
  el.className = 'toast' + (err ? ' err' : '') + ' on';
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('on'), 3500);
}

document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});

init();
</script>
</body></html>"""


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", status=200):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, data, status=200):
        self._send(json.dumps(data, ensure_ascii=False),
                   "application/json; charset=utf-8", status)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def do_GET(self):
        p = urlparse(self.path).path
        try:
            if p in ("/", "/index.html"):
                self._send(HTML)
            elif p == "/api/data":
                self._json(get_data())
            elif p == "/api/svg":
                self._send(build_svg())
            else:
                self.send_response(404); self.end_headers()
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            d = self._body()
            if p == "/api/save_building":
                save_building(d)
                self._json({"ok": True})
            elif p == "/api/delete_building":
                info = delete_building_full(d["name"])
                self._json({"ok": True, **info})
            else:
                self.send_response(404); self.end_headers()
        except Exception as e:
            self._json({"ok": False, "error": str(e)})


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    ensure_markers()
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Chain Editor  →  {url}")
    print("Ctrl+C to stop.\n")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
