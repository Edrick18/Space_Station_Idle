# -*- coding: utf-8 -*-
"""
Space Station Idle — Chain Editor
Browser-based tool for adding/editing/deleting materials and buildings.

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

# Sentinel comments that mark insertion points inside space_station_idle.py
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


# ── sentinel insertion ────────────────────────────────────────────────────────
def ensure_markers():
    """Add END_MATERIALS and END_BUILDINGS markers if missing."""
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
    inputs   = [i.strip() for i in d["inputs"] if str(i).strip()]
    mat_costs = {k.strip(): int(v) for k, v in d["materials"].items() if k.strip()}
    mats_py  = ("{" + ", ".join(f'"{k}": {v}' for k, v in mat_costs.items()) + "}"
                if mat_costs else "{}")
    return (f'    "{d["name"]}": {{"output": "{d["output"]}", "inputs": {repr(inputs)}, '
            f'"credits": {int(d["credits"])}, "materials": {mats_py}, '
            f'"extraction": {bool(d.get("extraction", False))}}},\n')


# ── write / update / delete ───────────────────────────────────────────────────
def write_material(d):
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    if f'"{d["name"]}":' in src:
        raise ValueError(f'"{d["name"]}" already exists')
    if MAT_MARKER not in src:
        raise RuntimeError("Marker missing — reopen the editor to fix it")
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src.replace(MAT_MARKER, _mat_line(d) + MAT_MARKER))


def update_material(d):
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    pat = re.compile(rf'^    "{re.escape(d["name"])}"[^\n]*\n', re.MULTILINE)
    if not pat.search(src):
        raise ValueError(f'"{d["name"]}" not found')
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(pat.sub(_mat_line(d), src, count=1))


def delete_material(name):
    g = load_game()
    if name not in g.MATERIALS:
        raise ValueError(f'"{name}" not found')
    consumers = [c for c in g.CONSUMERS.get(name, []) if c in g.BUILDINGS]
    if consumers:
        raise ValueError(f'Cannot delete — still used by: {", ".join(consumers)}')
    producer = g.PRODUCER.get(name)
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    src = re.sub(rf'^    "{re.escape(name)}"[^\n]*\n', "", src, flags=re.MULTILINE)
    if producer:
        src = re.sub(rf'^    "{re.escape(producer)}"[^\n]*\n', "", src, flags=re.MULTILINE)
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src)


def write_building(d):
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    if f'"{d["name"]}":' in src:
        raise ValueError(f'"{d["name"]}" already exists')
    if BLD_MARKER not in src:
        raise RuntimeError("Marker missing — reopen the editor to fix it")
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src.replace(BLD_MARKER, _bld_line(d) + BLD_MARKER))


def update_building(d):
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    pat = re.compile(rf'^    "{re.escape(d["name"])}"[^\n]*\n', re.MULTILINE)
    if not pat.search(src):
        raise ValueError(f'"{d["name"]}" not found')
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(pat.sub(_bld_line(d), src, count=1))


def delete_building(name):
    g = load_game()
    if name not in g.BUILDINGS:
        raise ValueError(f'"{name}" not found')
    output    = g.BUILDINGS[name]["output"]
    consumers = [c for c in g.CONSUMERS.get(output, []) if c != name]
    if consumers:
        raise ValueError(f'Cannot delete — output "{output}" is used by: {", ".join(consumers)}')
    with open(GAME_FILE, "r", encoding="utf-8") as f:
        src = f.read()
    src = re.sub(rf'^    "{re.escape(name)}"[^\n]*\n', "", src, flags=re.MULTILINE)
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        f.write(src)


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


# ── SVG overview (no tiers) ───────────────────────────────────────────────────
def build_svg():
    g = load_game()
    NW, NH = 235, 96

    def esc(s):
        return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    xs = [i["pos"][0] for i in g.MATERIALS.values()]
    ys = [i["pos"][1] for i in g.MATERIALS.values()]
    W  = max(xs) + NW + 80
    H  = max(ys) + NH + 80

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
            col = g.MATERIALS[inp]["color"]
            x1, y1 = ix + NW/2, iy + NH
            x2, y2 = ox + NW/2, oy
            parts.append(
                f'<path d="M {x1} {y1} C {x1} {y1+55},{x2} {y2-55},{x2} {y2-4}" '
                f'fill="none" stroke="{col}" stroke-width="2.5" opacity="0.65" '
                f'marker-end="url(#{mk[col]})">'
                f'<title>{esc(inp)} → {esc(bname)} → {esc(out)}</title></path>')

    for mat, info in g.MATERIALS.items():
        x, y   = info["pos"]
        col    = info["color"]
        bname  = g.PRODUCER.get(mat)
        b      = g.BUILDINGS.get(bname, {})
        used   = g.CONSUMERS.get(mat, [])
        ep     = not used and not b.get("extraction", False)
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


# ── embedded HTML ─────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Space Station Idle — Chain Editor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0f1a;color:#e8eefc;font-family:'Segoe UI',sans-serif;
     height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:#0e1426;padding:12px 24px;border-bottom:1px solid #1e2d50;
       display:flex;align-items:center;gap:12px;flex-shrink:0}
header h1{font-size:15px;font-weight:600}
.badge{background:#1e2d50;color:#8fa3c8;padding:2px 10px;border-radius:99px;font-size:12px}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:360px;min-width:260px;background:#0e1426;border-right:1px solid #1e2d50;
         display:flex;flex-direction:column;overflow-y:auto}
.sec{padding:14px 16px;border-bottom:1px solid #1a2440}
.sec h2{font-size:11px;text-transform:uppercase;color:#8fa3c8;letter-spacing:.08em;
        margin-bottom:10px;display:flex;align-items:center;justify-content:space-between}
.ilist{display:flex;flex-direction:column;gap:5px}
.irow{display:flex;align-items:center;background:#151d33;border-radius:8px;
      padding:7px 10px;gap:7px;font-size:13px}
.irow .nm{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.irow .pr{color:#fbbf24;font-size:12px;white-space:nowrap}
.irow .act{display:flex;gap:5px;flex-shrink:0}
.bi{background:none;border:1px solid #22315c;color:#8fa3c8;border-radius:6px;
    padding:3px 8px;cursor:pointer;font-size:11px;transition:all .15s;font-family:inherit}
.bi:hover{background:#1a2440;color:#e8eefc}
.bi.del:hover{border-color:#f87171;color:#f87171}
.badd{display:flex;align-items:center;gap:6px;background:#1e2d50;border:1px dashed #334466;
      color:#8fa3c8;border-radius:8px;padding:8px 12px;cursor:pointer;font-size:13px;
      width:100%;margin-top:8px;transition:all .15s;font-family:inherit}
.badd:hover{background:#243358;color:#e8eefc}
.svgpane{flex:1;overflow:auto;padding:20px;background:#0b0f1a}
/* modal */
.mbg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:100;
     align-items:center;justify-content:center}
.mbg.on{display:flex}
.modal{background:#0e1526;border:1px solid #1e2d50;border-radius:16px;padding:26px;
       width:480px;max-height:90vh;overflow-y:auto}
.modal h2{font-size:15px;margin-bottom:18px}
.fr{margin-bottom:13px}
.fr label{display:block;font-size:12px;color:#8fa3c8;margin-bottom:5px}
.fr input,.fr select{width:100%;background:#151d33;border:1px solid #22315c;
  border-radius:8px;color:#e8eefc;padding:8px 12px;font-size:13px;outline:none;
  font-family:inherit}
.fr input:focus,.fr select:focus{border-color:#60a5fa}
.fr.row{display:flex;gap:10px}
.fr.row .fr{margin-bottom:0;flex:1}
.hint{font-size:11px;color:#556b8f;margin-top:4px}
.mfoot{display:flex;justify-content:flex-end;gap:10px;margin-top:22px}
.btn{padding:9px 20px;border-radius:9px;font-size:13px;cursor:pointer;border:none;
     font-family:inherit;transition:all .15s}
.bc{background:#151d33;color:#8fa3c8;border:1px solid #22315c}
.bc:hover{background:#1a2440;color:#e8eefc}
.bp{background:#2563eb;color:#fff}
.bp:hover{background:#1d4ed8}
.ipair{display:flex;gap:8px;align-items:center;margin-bottom:7px}
.ipair select{flex:1}
.ipair input{width:76px}
.ipair span{font-size:12px;color:#8fa3c8;white-space:nowrap}
/* toast */
.toast{position:fixed;bottom:22px;right:22px;background:#1a2e1a;border:1px solid #4ade80;
       color:#4ade80;padding:11px 18px;border-radius:10px;font-size:13px;z-index:200;
       opacity:0;transform:translateY(14px);transition:all .25s;pointer-events:none}
.toast.err{background:#2d1414;border-color:#f87171;color:#f87171}
.toast.on{opacity:1;transform:none}
</style></head><body>
<header>
  <span>🚀</span>
  <h1>Space Station Idle — Chain Editor</h1>
  <span class="badge" id="vbadge">v?</span>
  <span class="badge" id="cbadge">loading…</span>
</header>
<div class="main">
  <div class="sidebar">
    <div class="sec">
      <h2>Materials</h2>
      <div class="ilist" id="mlist"></div>
      <button class="badd" onclick="openMat()">＋ Add Material</button>
    </div>
    <div class="sec">
      <h2>Buildings</h2>
      <div class="ilist" id="blist"></div>
      <button class="badd" onclick="openBld()">＋ Add Building</button>
    </div>
  </div>
  <div class="svgpane" id="svgpane"><div style="color:#8fa3c8;font-size:13px">Loading…</div></div>
</div>

<!-- Material modal -->
<div class="mbg" id="mmod">
 <div class="modal">
  <h2 id="mtitle">New Material</h2>
  <input type="hidden" id="mmode" value="add">
  <div class="fr"><label>Name</label>
    <input id="mname" placeholder="e.g. Titanium Ingot"></div>
  <div class="fr row">
    <div class="fr"><label>Emoji</label>
      <input id="memoji" placeholder="🔩" style="width:80px"></div>
    <div class="fr"><label>Chain Color</label>
      <select id="mcolor"></select></div>
  </div>
  <div class="fr"><label>Sell Price (credits)</label>
    <input id="mprice" type="number" min="1" placeholder="42">
    <div class="hint" id="mphint"></div></div>
  <div class="fr row">
    <div class="fr"><label>Position X</label>
      <input id="mx" type="number" placeholder="500"></div>
    <div class="fr"><label>Position Y</label>
      <input id="my" type="number" placeholder="820"></div>
  </div>
  <div class="fr">
    <button class="bi" onclick="suggestPos()" style="margin-top:2px">
      ↙ Suggest position from chain</button>
    <div class="hint">Y increases downward. Spacing between rows: ~190px.</div>
  </div>
  <div class="mfoot">
    <button class="btn bc" onclick="closeM('mmod')">Cancel</button>
    <button class="btn bp" id="msubmit" onclick="submitMat()">Add to Game</button>
  </div>
 </div>
</div>

<!-- Building modal -->
<div class="mbg" id="bmod">
 <div class="modal">
  <h2 id="btitle">New Building</h2>
  <input type="hidden" id="bmode" value="add">
  <div class="fr"><label>Building Name</label>
    <input id="bname" placeholder="e.g. Titanium Smelter"></div>
  <div class="fr"><label>Output Material</label>
    <select id="boutput" onchange="onOutChange()">
      <option value="">— select material —</option></select></div>
  <div class="fr"><label>Inputs (leave blank for extraction / raw resource)</label>
    <div id="binputs">
      <div class="ipair"><select class="inm"><option value="">— none —</option></select>
        <span>cost</span><input class="inc" type="number" value="20" min="1"></div>
      <div class="ipair"><select class="inm"><option value="">— none —</option></select>
        <span>cost</span><input class="inc" type="number" value="20" min="1"></div>
      <div class="ipair"><select class="inm"><option value="">— none —</option></select>
        <span>cost</span><input class="inc" type="number" value="20" min="1"></div>
    </div></div>
  <div class="fr"><label>Credits cost to build</label>
    <input id="bcredits" type="number" min="50" placeholder="1000">
    <div class="hint" id="bchint"></div></div>
  <div class="fr"><label>
    <input type="checkbox" id="bextract" style="width:auto;margin-right:6px">
    Extraction building (raw resource — no inputs needed)</label></div>
  <div class="mfoot">
    <button class="btn bc" onclick="closeM('bmod')">Cancel</button>
    <button class="btn bp" id="bsubmit" onclick="submitBld()">Add to Game</button>
  </div>
 </div>
</div>

<div class="toast" id="toast"></div>
<script>
let D={};

async function init(){await reload(); await reloadSvg();}

async function reload(){
  const r=await fetch('/api/data'); D=await r.json();
  document.getElementById('vbadge').textContent='v'+D.version;
  const mc=Object.keys(D.materials).length, bc=Object.keys(D.buildings).length;
  document.getElementById('cbadge').textContent=mc+' materials · '+bc+' buildings';
  renderLists(); fillSelects();
}

async function reloadSvg(){
  const r=await fetch('/api/svg');
  document.getElementById('svgpane').innerHTML=await r.text();
}

function renderLists(){
  const ml=document.getElementById('mlist'); ml.innerHTML='';
  for(const[n,i]of Object.entries(D.materials)){
    const d=document.createElement('div'); d.className='irow';
    d.innerHTML=`<span style="color:${i.color}">${i.emoji}</span>
      <span class="nm">${n}</span>
      <span class="pr">${i.price} Cr</span>
      <div class="act">
        <button class="bi" onclick="editMat(${JSON.stringify(n)})">edit</button>
        <button class="bi del" onclick="delMat(${JSON.stringify(n)})">del</button>
      </div>`;
    ml.appendChild(d);
  }
  const bl=document.getElementById('blist'); bl.innerHTML='';
  for(const[n,b]of Object.entries(D.buildings)){
    const d=document.createElement('div'); d.className='irow';
    d.innerHTML=`<span class="nm" style="font-size:12px">${n}</span>
      <span class="pr" style="font-size:11px">→ ${b.output}</span>
      <div class="act">
        <button class="bi" onclick="editBld(${JSON.stringify(n)})">edit</button>
        <button class="bi del" onclick="delBld(${JSON.stringify(n)})">del</button>
      </div>`;
    bl.appendChild(d);
  }
}

function fillSelects(){
  // chain color select
  const cs=document.getElementById('mcolor'); cs.innerHTML='';
  for(const[label,cconst]of Object.entries(D.chain_colors)){
    const o=document.createElement('option');
    o.value=cconst; o.textContent=label;
    o.style.color=D.color_values[cconst]; cs.appendChild(o);
  }
  // output select
  const os=document.getElementById('boutput');
  const cur=os.value;
  os.innerHTML='<option value="">— select material —</option>';
  for(const n of Object.keys(D.materials)){
    const o=document.createElement('option');
    o.value=n; o.textContent=n;
    if(n===cur) o.selected=true;
    os.appendChild(o);
  }
  // input selects
  for(const sel of document.querySelectorAll('.inm')){
    const cv=sel.value;
    sel.innerHTML='<option value="">— none —</option>';
    for(const n of Object.keys(D.materials)){
      const o=document.createElement('option');
      o.value=n; o.textContent=n;
      if(n===cv) o.selected=true;
      sel.appendChild(o);
    }
  }
}

// ── Material modal ────────────────────────────────────────────────────────────
function openMat(ed){
  document.getElementById('mtitle').textContent=ed?'Edit Material':'New Material';
  document.getElementById('mmode').value=ed?'edit':'add';
  document.getElementById('msubmit').textContent=ed?'Save Changes':'Add to Game';
  const ni=document.getElementById('mname');
  if(ed){
    ni.value=ed.name; ni.readOnly=true;
    document.getElementById('memoji').value=ed.emoji;
    document.getElementById('mprice').value=ed.price;
    document.getElementById('mx').value=ed.x;
    document.getElementById('my').value=ed.y;
    document.getElementById('mcolor').value=ed.color_const;
  } else {
    ni.value=''; ni.readOnly=false;
    document.getElementById('memoji').value='';
    document.getElementById('mprice').value='';
    document.getElementById('mx').value='';
    document.getElementById('my').value='';
  }
  document.getElementById('mmod').classList.add('on');
}

function editMat(n){ openMat({name:n,...D.materials[n]}); }

async function delMat(n){
  if(!confirm(`Delete material "${n}"?\nThis also removes its producer building.`)) return;
  const r=await post('/api/delete_material',{name:n});
  r.ok ? (toast('Deleted: '+n), await reload(), await reloadSvg()) : toast(r.error,true);
}

function suggestPos(){
  const cc=document.getElementById('mcolor').value;
  const same=Object.values(D.materials).filter(i=>i.color_const===cc);
  if(!same.length){
    document.getElementById('mx').value=500;
    document.getElementById('my').value=250;
    return;
  }
  const maxY=Math.max(...same.map(i=>i.y));
  const avgX=Math.round(same.reduce((s,i)=>s+i.x,0)/same.length);
  document.getElementById('mx').value=avgX;
  document.getElementById('my').value=maxY+190;
}

async function submitMat(){
  const mode=document.getElementById('mmode').value;
  const d={
    name:document.getElementById('mname').value.trim(),
    emoji:document.getElementById('memoji').value.trim(),
    price:document.getElementById('mprice').value,
    x:document.getElementById('mx').value||500,
    y:document.getElementById('my').value||250,
    color_const:document.getElementById('mcolor').value,
  };
  if(!d.name||!d.emoji||!d.price){toast('Name, emoji and price are required',true);return;}
  const ep=mode==='edit'?'/api/update_material':'/api/add_material';
  const r=await post(ep,d);
  if(r.ok){
    toast((mode==='edit'?'Updated: ':'Added: ')+d.name);
    closeM('mmod'); await reload(); await reloadSvg();
  } else toast(r.error,true);
}

// ── Building modal ────────────────────────────────────────────────────────────
function openBld(ed){
  document.getElementById('btitle').textContent=ed?'Edit Building':'New Building';
  document.getElementById('bmode').value=ed?'edit':'add';
  document.getElementById('bsubmit').textContent=ed?'Save Changes':'Add to Game';
  const ni=document.getElementById('bname');
  if(ed){
    ni.value=ed.name; ni.readOnly=true;
    document.getElementById('boutput').value=ed.output;
    document.getElementById('bcredits').value=ed.credits;
    document.getElementById('bextract').checked=ed.extraction;
    const pairs=document.querySelectorAll('.ipair');
    for(let i=0;i<3;i++){
      const nm=ed.inputs[i]||'';
      pairs[i].querySelector('.inm').value=nm;
      pairs[i].querySelector('.inc').value=nm?(ed.materials[nm]||20):20;
    }
  } else {
    ni.value=''; ni.readOnly=false;
    document.getElementById('boutput').value='';
    document.getElementById('bcredits').value='';
    document.getElementById('bextract').checked=false;
    for(const p of document.querySelectorAll('.ipair')){
      p.querySelector('.inm').value='';
      p.querySelector('.inc').value=20;
    }
  }
  document.getElementById('bmod').classList.add('on');
}

function editBld(n){ openBld({name:n,...D.buildings[n]}); }

async function delBld(n){
  if(!confirm(`Delete building "${n}"?`)) return;
  const r=await post('/api/delete_building',{name:n});
  r.ok ? (toast('Deleted: '+n), await reload(), await reloadSvg()) : toast(r.error,true);
}

function onOutChange(){
  const out=document.getElementById('boutput').value;
  if(out&&D.materials[out])
    document.getElementById('bchint').textContent=
      'Auto-suggest: ~'+Math.round(D.materials[out].price*30)+' credits';
}

async function submitBld(){
  const mode=document.getElementById('bmode').value;
  const inputs=[],mats={};
  for(const p of document.querySelectorAll('.ipair')){
    const nm=p.querySelector('.inm').value;
    const co=parseInt(p.querySelector('.inc').value)||20;
    if(nm){inputs.push(nm);mats[nm]=co;}
  }
  const d={
    name:document.getElementById('bname').value.trim(),
    output:document.getElementById('boutput').value,
    inputs,credits:document.getElementById('bcredits').value||1000,
    materials:mats,extraction:document.getElementById('bextract').checked,
  };
  if(!d.name||!d.output){toast('Name and output material are required',true);return;}
  const ep=mode==='edit'?'/api/update_building':'/api/add_building';
  const r=await post(ep,d);
  if(r.ok){
    toast((mode==='edit'?'Updated: ':'Added: ')+d.name);
    closeM('bmod'); await reload(); await reloadSvg();
  } else toast(r.error,true);
}

// ── utilities ─────────────────────────────────────────────────────────────────
async function post(url,data){
  const r=await fetch(url,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return r.json();
}

function closeM(id){document.getElementById(id).classList.remove('on');}

function toast(msg,err){
  const el=document.getElementById('toast');
  el.textContent=(err?'⚠ ':'✓ ')+msg;
  el.className='toast'+(err?' err':'')+' on';
  clearTimeout(el._t);
  el._t=setTimeout(()=>el.classList.remove('on'),3200);
}

document.querySelectorAll('.mbg').forEach(bg=>
  bg.addEventListener('click',e=>{if(e.target===bg)bg.classList.remove('on');}));

init();
</script>
</body></html>"""


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence request log

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
                self._send(build_svg(), "text/html; charset=utf-8")
            else:
                self.send_response(404); self.end_headers()
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            d = self._body()
            if   p == "/api/add_material":    write_material(d)
            elif p == "/api/update_material":  update_material(d)
            elif p == "/api/delete_material":  delete_material(d["name"])
            elif p == "/api/add_building":     write_building(d)
            elif p == "/api/update_building":  update_building(d)
            elif p == "/api/delete_building":  delete_building(d["name"])
            else:
                self.send_response(404); self.end_headers(); return
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    ensure_markers()
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Chain Editor running at  {url}")
    print("Press Ctrl+C to stop.\n")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEditor stopped.")


if __name__ == "__main__":
    main()
