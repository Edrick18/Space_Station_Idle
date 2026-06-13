# -*- coding: utf-8 -*-
"""Space Station Idle — an idle/incremental game about production chains.

Runs fully offline with Python + tkinter.
Progress is saved automatically to savegame.json (same folder).
"""

import json
import math
import os
import random
import re
import subprocess
import sys
import threading
import time
import tkinter as tk

# When packaged as an exe (PyInstaller), __file__ points into a temp folder —
# the save file and updates must live next to the exe instead.
IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = os.path.dirname(sys.executable if IS_FROZEN
                           else os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "savegame.json")

VERSION = "1.2.0"

# --- Auto-update via GitHub (optional — fails silently) ---
# On startup a background thread checks whether a newer version exists.
# Running as .py:  compares version.json in the repo, downloads the script.
# Running as .exe: compares the latest GitHub release tag, downloads the exe
#                  and swaps it in on the next launch.
# Without internet, without an update, or on any error the game simply keeps
# running — updates are never mandatory.
UPDATE_USER = "Edrick18"
UPDATE_REPO = "Space_Station_Idle"
UPDATE_BRANCH = "main"
UPDATE_FILE = "space_station_idle.py"
EXE_NAME = "SpaceStationIdle.exe"

INTERVAL = 5.0              # seconds per production cycle
INPUT_RATIO = 3             # units of each input consumed per 1 output produced
OFFLINE_CAP = 24 * 3600     # offline production capped at 24 hours
AUTOSAVE_SECONDS = 30.0
COST_GROWTH = 1.2           # credit cost rises per building purchased
FRAME_MS = 40               # ~25 FPS

RAWS = ["Iron Ore", "Coal", "Copper Ore", "Silicon Sand", "Crude Oil"]

# ----- Colors -----
BG = "#0b0f1a"
CARD = "#151d33"
CARD_HOVER = "#1a2440"
CARD_SELECTED = "#1d2848"
SHADOW = "#070b15"
PANEL_BG = "#0e1526"
PANEL_CARD = "#16203a"
HEADER_BG = "#0e1426"
TEXT_MAIN = "#e8eefc"
TEXT_DIM = "#8fa3c8"
GOLD = "#fbbf24"
GREEN = "#4ade80"
RED = "#f87171"

PANEL_W = 320

# Accent colors per production chain
C_METAL = "#60a5fa"     # iron / steel
C_COAL = "#9ca3af"
C_COPPER = "#fb923c"    # copper / cables
C_SILICON = "#4ade80"   # silicon / electronics
C_OIL = "#facc15"       # oil / plastic
C_MECH = "#a78bfa"
C_ROBOT = "#f472b6"

# Material: emoji, sell price, position (x, y), accent color
MATERIALS = {
    # Tier 0 — raw resources
    "Iron Ore":        {"emoji": "🔩", "price": 1,    "pos": (150, 60),    "color": C_METAL},
    "Coal":            {"emoji": "⚫", "price": 1,    "pos": (420, 60),    "color": C_COAL},
    "Copper Ore":      {"emoji": "🟠", "price": 1,    "pos": (690, 60),    "color": C_COPPER},
    "Silicon Sand":    {"emoji": "🏜️", "price": 1,    "pos": (960, 60),    "color": C_SILICON},
    "Crude Oil":       {"emoji": "🛢️", "price": 1,    "pos": (1230, 60),   "color": C_OIL},
    # Tier 1 — first processing
    "Iron Ingot":      {"emoji": "🧱", "price": 2,    "pos": (150, 250),   "color": C_METAL},
    "Copper Ingot":    {"emoji": "🟧", "price": 2,    "pos": (690, 250),   "color": C_COPPER},
    "Raw Silicon":     {"emoji": "💎", "price": 2,    "pos": (960, 250),   "color": C_SILICON},
    "Plastic":         {"emoji": "🧪", "price": 2,    "pos": (1230, 250),  "color": C_OIL},
    # Tier 2
    "Steel Ingot":     {"emoji": "⚒️", "price": 6,    "pos": (280, 440),   "color": C_METAL},
    "Copper Wire":     {"emoji": "🧵", "price": 6,    "pos": (690, 440),   "color": C_COPPER},
    "Silicon Wafer":   {"emoji": "💿", "price": 8,    "pos": (960, 440),   "color": C_SILICON},
    # Tier 3
    "Iron Plate":      {"emoji": "🟫", "price": 16,   "pos": (150, 630),   "color": C_METAL},
    "Steel Sheet":     {"emoji": "🪨", "price": 14,   "pos": (420, 630),   "color": C_METAL},
    "Copper Cable":    {"emoji": "🪢", "price": 16,   "pos": (690, 630),   "color": C_COPPER},
    "Microchip":       {"emoji": "🔲", "price": 28,   "pos": (960, 630),   "color": C_SILICON},
    # Tier 4
    "Steel Beam":      {"emoji": "🏗️", "price": 60,   "pos": (280, 820),   "color": C_METAL},
    "Insulated Cable": {"emoji": "🔌", "price": 36,   "pos": (690, 820),   "color": C_COPPER},
    # Tier 5
    "Coil":            {"emoji": "🧲", "price": 76,   "pos": (500, 1010),  "color": C_COPPER},
    "Circuit Board":   {"emoji": "💻", "price": 128,  "pos": (830, 1010),  "color": C_SILICON},
    # Tier 6
    "Machine Frame":   {"emoji": "🛠️", "price": 272,  "pos": (420, 1200),  "color": C_MECH},
    # Tier 7
    "Motor":           {"emoji": "⚙️", "price": 572,  "pos": (420, 1390),  "color": C_MECH},
    # Tier 8
    "Basic Robot":     {"emoji": "🤖", "price": 1520, "pos": (650, 1580),  "color": C_ROBOT},
    # END_MATERIALS
}

# Buildings in production order (raw resources first so chains flow
# cleanly within a single cycle)
BUILDINGS = {
    # Extraction
    "Iron Mine":      {"output": "Iron Ore",     "inputs": [], "credits": 50,  "materials": {}, "extraction": True},
    "Coal Mine":      {"output": "Coal",         "inputs": [], "credits": 50,  "materials": {}, "extraction": True},
    "Copper Mine":    {"output": "Copper Ore",   "inputs": [], "credits": 60,  "materials": {}, "extraction": True},
    "Silicon Quarry": {"output": "Silicon Sand", "inputs": [], "credits": 60,  "materials": {}, "extraction": True},
    "Oil Pump":       {"output": "Crude Oil",    "inputs": [], "credits": 80,  "materials": {}, "extraction": True},
    # First processing
    "Iron Smelter":    {"output": "Iron Ingot",   "inputs": ["Iron Ore"],     "credits": 100, "materials": {"Iron Ore": 50},     "extraction": False},
    "Copper Smelter":  {"output": "Copper Ingot", "inputs": ["Copper Ore"],   "credits": 100, "materials": {"Copper Ore": 50},   "extraction": False},
    "Silicon Furnace": {"output": "Raw Silicon",  "inputs": ["Silicon Sand"], "credits": 100, "materials": {"Silicon Sand": 50}, "extraction": False},
    "Refinery":        {"output": "Plastic",      "inputs": ["Crude Oil"],    "credits": 120, "materials": {"Crude Oil": 50},    "extraction": False},
    # Metal chain
    "Blast Furnace": {"output": "Steel Ingot", "inputs": ["Iron Ingot", "Coal"],        "credits": 300,  "materials": {"Iron Ingot": 30, "Coal": 30},        "extraction": False},
    "Rolling Mill":  {"output": "Iron Plate",  "inputs": ["Iron Ingot", "Steel Ingot"], "credits": 600,  "materials": {"Iron Ingot": 30, "Steel Ingot": 20}, "extraction": False},
    "Steel Mill":    {"output": "Steel Sheet", "inputs": ["Steel Ingot", "Coal"],       "credits": 500,  "materials": {"Steel Ingot": 25, "Coal": 40},       "extraction": False},
    "Press Works":   {"output": "Steel Beam",  "inputs": ["Steel Sheet", "Iron Plate"], "credits": 1500, "materials": {"Steel Sheet": 20, "Iron Plate": 20}, "extraction": False},
    # Cable chain
    "Wire Mill":        {"output": "Copper Wire",     "inputs": ["Copper Ingot", "Coal"],           "credits": 300,  "materials": {"Copper Ingot": 30, "Coal": 30},         "extraction": False},
    "Cable Works":      {"output": "Copper Cable",    "inputs": ["Copper Wire", "Copper Ingot"],    "credits": 600,  "materials": {"Copper Wire": 25, "Copper Ingot": 25},  "extraction": False},
    "Insulation Plant": {"output": "Insulated Cable", "inputs": ["Copper Cable", "Plastic"],        "credits": 1200, "materials": {"Copper Cable": 20, "Plastic": 30},      "extraction": False},
    "Coil Factory":     {"output": "Coil",            "inputs": ["Insulated Cable", "Iron Ingot"],  "credits": 2500, "materials": {"Insulated Cable": 15, "Iron Ingot": 30}, "extraction": False},
    # Electronics chain
    "Wafer Plant":           {"output": "Silicon Wafer", "inputs": ["Raw Silicon", "Copper Ingot"],     "credits": 500,  "materials": {"Raw Silicon": 30, "Copper Ingot": 25},  "extraction": False},
    "Chip Factory":          {"output": "Microchip",     "inputs": ["Silicon Wafer", "Copper Wire"],    "credits": 1500, "materials": {"Silicon Wafer": 20, "Copper Wire": 30}, "extraction": False},
    "Circuit Board Factory": {"output": "Circuit Board", "inputs": ["Microchip", "Insulated Cable"],    "credits": 4000, "materials": {"Microchip": 15, "Insulated Cable": 15}, "extraction": False},
    # Mechanics
    "Machine Works": {"output": "Machine Frame", "inputs": ["Steel Beam", "Coil"],            "credits": 8000,  "materials": {"Steel Beam": 10, "Coil": 10},           "extraction": False},
    "Motor Factory": {"output": "Motor",         "inputs": ["Machine Frame", "Steel Sheet"],  "credits": 15000, "materials": {"Machine Frame": 5, "Steel Sheet": 20},  "extraction": False},
    # Robotics
    "Robot Factory": {"output": "Basic Robot", "inputs": ["Motor", "Circuit Board", "Steel Beam"], "credits": 40000, "materials": {"Motor": 5, "Circuit Board": 5, "Steel Beam": 10}, "extraction": False},
    # END_BUILDINGS
}

BUILDING_ORDER = list(BUILDINGS.keys())

# Material -> building that produces it
PRODUCER = {b["output"]: name for name, b in BUILDINGS.items()}
# Material -> buildings that consume it
CONSUMERS = {m: [] for m in MATERIALS}
for _name, _b in BUILDINGS.items():
    for _inp in _b["inputs"]:
        CONSUMERS[_inp].append(_name)

# Material cost for the 2nd+ purchase of an extraction building
EXTRACTION_MATERIAL_COST = 25

NODE_W = 235
NODE_H = 118

# Old German save files (game was originally written in German) are
# migrated transparently on load so no progress is ever lost.
LEGACY_NAMES = {
    # Materials
    "Eisenerz": "Iron Ore", "Kohle": "Coal", "Kupfererz": "Copper Ore",
    "Siliziumsand": "Silicon Sand", "Rohöl": "Crude Oil",
    "Eisenbarren": "Iron Ingot", "Kupferbarren": "Copper Ingot",
    "Rohsilizium": "Raw Silicon", "Kunststoff": "Plastic",
    "Stahlbarren": "Steel Ingot", "Kupferdraht": "Copper Wire",
    "Siliziumwafer": "Silicon Wafer", "Eisenplatte": "Iron Plate",
    "Stahlblech": "Steel Sheet", "Kupferkabel": "Copper Cable",
    "Mikrochip": "Microchip", "Stahlträger": "Steel Beam",
    "Isoliertes Kabel": "Insulated Cable", "Spule": "Coil",
    "Platine": "Circuit Board", "Maschinenrahmen": "Machine Frame",
    "Basisroboter": "Basic Robot",
    # Buildings
    "Eisenmine": "Iron Mine", "Kohlemine": "Coal Mine",
    "Kupfermine": "Copper Mine", "Siliziumbruch": "Silicon Quarry",
    "Ölpumpe": "Oil Pump", "Schmelzofen": "Iron Smelter",
    "Kupferschmelze": "Copper Smelter", "Siliziumofen": "Silicon Furnace",
    "Raffinerie": "Refinery", "Hochofen": "Blast Furnace",
    "Walzwerk": "Rolling Mill", "Stahlwerk": "Steel Mill",
    "Presswerk": "Press Works", "Drahtziehwerk": "Wire Mill",
    "Kabelwerk": "Cable Works", "Isolierwerk": "Insulation Plant",
    "Spulenwerk": "Coil Factory", "Waferwerk": "Wafer Plant",
    "Chipfabrik": "Chip Factory", "Platinenwerk": "Circuit Board Factory",
    "Maschinenwerk": "Machine Works", "Motorenfabrik": "Motor Factory",
    "Roboterwerk": "Robot Factory",
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def fmt(n):
    """Integer with thousands separators."""
    return f"{int(n):,}"


def fmt_rate(r):
    return f"{r:.1f}"


def blend(c1, c2, t):
    """Blend two hex colors: t=0 -> c1, t=1 -> c2."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#%02x%02x%02x" % (round(r1 + (r2 - r1) * t),
                              round(g1 + (g2 - g1) * t),
                              round(b1 + (b2 - b1) * t))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def round_rect_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Rounded rectangle as a smoothed polygon."""
    return canvas.create_polygon(round_rect_points(x1, y1, x2, y2, r),
                                 smooth=True, **kw)


def bezier_point(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]
    return x, y


def connection_curve(inp, out):
    """Bezier control points for the line from input node to output node."""
    ix, iy = MATERIALS[inp]["pos"]
    ox, oy = MATERIALS[out]["pos"]
    p0 = (ix + NODE_W / 2, iy + NODE_H)
    p3 = (ox + NODE_W / 2, oy)
    p1 = (p0[0], p0[1] + 55)
    p2 = (p3[0], p3[1] - 55)
    return p0, p1, p2, p3


def version_tuple(s):
    """'1.2.3' -> (1, 2, 3) for version comparisons."""
    nums = re.findall(r"\d+", str(s))
    return tuple(int(n) for n in nums[:4]) if nums else (0,)


def check_for_update(result):
    """Checks GitHub whether a newer version exists (no download yet).

    Runs in a background thread. Every error (no internet, repository
    unreachable, ...) is swallowed — the game then simply keeps running
    with the current version. `result` is filled with:
      status: "unconfigured" | "up-to-date" | "update-available" | "offline"
      version: the new version number (only when "update-available")
      url:     exe download url (exe mode only)
    """
    if "DEIN-GITHUB" in UPDATE_USER or not UPDATE_USER:
        result["status"] = "unconfigured"
        return
    try:
        if IS_FROZEN:
            _check_exe_update(result)
        else:
            _check_script_update(result)
    except Exception:
        result["status"] = "offline"


def _check_script_update(result):
    """Running from source: compare against version.json in the repo."""
    import urllib.request
    base = (f"https://raw.githubusercontent.com/"
            f"{UPDATE_USER}/{UPDATE_REPO}/{UPDATE_BRANCH}/")
    with urllib.request.urlopen(base + "version.json", timeout=6) as r:
        info = json.loads(r.read().decode("utf-8"))
    remote = str(info.get("version", "0"))
    if version_tuple(remote) <= version_tuple(VERSION):
        result["status"] = "up-to-date"
        return
    result["version"] = remote
    result["status"] = "update-available"


def _check_exe_update(result):
    """Running as exe: compare against the latest GitHub release tag."""
    import urllib.request
    api = (f"https://api.github.com/repos/"
           f"{UPDATE_USER}/{UPDATE_REPO}/releases/latest")
    req = urllib.request.Request(api, headers={"User-Agent": EXE_NAME})
    with urllib.request.urlopen(req, timeout=6) as r:
        info = json.loads(r.read().decode("utf-8"))
    remote = str(info.get("tag_name", "0"))
    if version_tuple(remote) <= version_tuple(VERSION):
        result["status"] = "up-to-date"
        return
    for asset in info.get("assets", []):
        if asset.get("name") == EXE_NAME:
            result["version"] = remote.lstrip("v")
            result["url"] = asset.get("browser_download_url")
            result["status"] = "update-available"
            return
    result["status"] = "up-to-date"  # release without exe -> nothing to do


def download_update(info):
    """Downloads the accepted update. Sets status to 'downloaded' on
    success, 'download-failed' otherwise. Runs in a background thread."""
    import urllib.request
    try:
        if IS_FROZEN:
            req = urllib.request.Request(info["url"],
                                         headers={"User-Agent": EXE_NAME})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            # Sanity check: must be a Windows executable of plausible size
            if len(data) < 1_000_000 or not data.startswith(b"MZ"):
                info["status"] = "download-failed"
                return
            new_path = sys.executable + ".new"
            part = new_path + ".part"
            with open(part, "wb") as f:
                f.write(data)
            os.replace(part, new_path)
        else:
            base = (f"https://raw.githubusercontent.com/"
                    f"{UPDATE_USER}/{UPDATE_REPO}/{UPDATE_BRANCH}/")
            with urllib.request.urlopen(base + UPDATE_FILE, timeout=20) as r:
                code = r.read()
            text = code.decode("utf-8")
            # Sanity check so a broken file is never installed
            if "class Game" not in text or "VERSION" not in text or len(text) < 5000:
                info["status"] = "download-failed"
                return
            target = os.path.join(BASE_DIR, UPDATE_FILE)
            tmp = target + ".dl"
            with open(tmp, "wb") as f:
                f.write(code)
            os.replace(tmp, target)
        info["status"] = "downloaded"
    except Exception:
        info["status"] = "download-failed"


def restart_into_update():
    """Relaunches the game on the freshly downloaded version.

    Returns False if the restart could not be performed (the game then
    simply keeps running on the current version).
    """
    try:
        if IS_FROZEN:
            # A running exe cannot overwrite itself, but it CAN be renamed:
            # move the running exe aside, put the update in its place.
            exe = sys.executable
            old, new = exe + ".old", exe + ".new"
            try:
                if os.path.exists(old):
                    os.remove(old)
            except OSError:
                pass
            os.rename(exe, old)
            os.rename(new, exe)
            subprocess.Popen([exe], close_fds=True)
        else:
            target = os.path.join(BASE_DIR, UPDATE_FILE)
            subprocess.Popen([sys.executable, target], close_fds=True)
    except OSError:
        return False
    os._exit(0)


def apply_pending_exe_update():
    """Startup safety net (exe mode only): cleans up leftover '.old' files
    and swaps in a '.new' exe that was downloaded but never applied
    (e.g. after a crash). On any error the game simply starts normally."""
    if not IS_FROZEN:
        return
    exe = sys.executable
    old, new = exe + ".old", exe + ".new"
    try:
        if os.path.exists(old):
            os.remove(old)  # leftover from a previous update
    except OSError:
        pass
    if not os.path.exists(new):
        return
    try:
        os.rename(exe, old)
        os.rename(new, exe)
    except OSError:
        return  # try again next launch
    try:
        subprocess.Popen([exe], close_fds=True)
        os._exit(0)
    except OSError:
        pass  # keep running the old version this one time


def add_nebula(canvas, cx, cy, rx, ry, color):
    """Soft nebula blob made of layered stippled ovals."""
    for scale, stipple in ((1.0, "gray12"), (0.7, "gray12"), (0.45, "gray25")):
        canvas.create_oval(cx - rx * scale, cy - ry * scale,
                           cx + rx * scale, cy + ry * scale,
                           fill=color, outline="", stipple=stipple, tags="static")


# ----------------------------------------------------------------------
# Game logic
# ----------------------------------------------------------------------

class Game:
    """Game logic, independent of the user interface."""

    def __init__(self):
        self.credits = 0
        self.stock = {m: 0 for m in MATERIALS}
        self.produced_total = {m: 0 for m in MATERIALS}
        self.counts = {b: 0 for b in BUILDINGS}
        self.timers = {b: 0.0 for b in BUILDINGS}
        self.events = []  # (material, amount) — finished production for animations
        # Starting state: one of each extraction building
        for b, data in BUILDINGS.items():
            if data["extraction"]:
                self.counts[b] = 1

    # ----- Production -----

    def produce(self, bname):
        b = BUILDINGS[bname]
        n = self.counts[bname]
        if n <= 0:
            return
        ratio = 1 if b["extraction"] else INPUT_RATIO
        p = n
        for m in b["inputs"]:
            p = min(p, self.stock[m] // ratio)
        if p <= 0:
            return
        for m in b["inputs"]:
            self.stock[m] -= p * ratio
        out = b["output"]
        self.stock[out] += p
        self.produced_total[out] += p
        if len(self.events) < 100:
            self.events.append((out, p))

    def tick(self, dt):
        for bname in BUILDING_ORDER:
            self.timers[bname] += dt
            while self.timers[bname] >= INTERVAL:
                self.timers[bname] -= INTERVAL
                self.produce(bname)

    def simulate_offline(self, seconds):
        seconds = min(seconds, OFFLINE_CAP)
        cycles = int(seconds / INTERVAL)
        for _ in range(cycles):
            for bname in BUILDING_ORDER:
                self.produce(bname)
        self.events.clear()
        return cycles

    # ----- Unlocking / visibility -----

    def building_unlocked(self, bname):
        b = BUILDINGS[bname]
        if b["extraction"]:
            return True
        for m in b["inputs"]:
            if self.produced_total[m] <= 0:
                return False
            if self.counts[PRODUCER[m]] <= 0:
                return False
        return True

    def material_visible(self, mat):
        return self.building_unlocked(PRODUCER[mat])

    # ----- Buying / selling -----

    def cost_of(self, bname):
        b = BUILDINGS[bname]
        credits = round(b["credits"] * (COST_GROWTH ** self.counts[bname]))
        if b["extraction"]:
            if self.counts[bname] >= 1:
                out = b["output"]
                materials = {r: EXTRACTION_MATERIAL_COST for r in RAWS if r != out}
            else:
                materials = {}
        else:
            materials = dict(b["materials"])
        return credits, materials

    def can_afford(self, bname):
        credits, materials = self.cost_of(bname)
        if self.credits < credits:
            return False
        for m, amt in materials.items():
            if self.stock[m] < amt:
                return False
        return True

    def buy(self, bname):
        if not self.building_unlocked(bname) or not self.can_afford(bname):
            return False
        credits, materials = self.cost_of(bname)
        self.credits -= credits
        for m, amt in materials.items():
            self.stock[m] -= amt
        self.counts[bname] += 1
        return True

    def sell(self, mat, amount):
        amount = min(int(amount), self.stock[mat])
        if amount <= 0:
            return 0
        self.stock[mat] -= amount
        gain = amount * MATERIALS[mat]["price"]
        self.credits += gain
        return gain

    # ----- Production / consumption rates (theoretical) -----

    def rate_produced(self, mat):
        return self.counts[PRODUCER[mat]] / INTERVAL

    def rate_consumed(self, mat):
        return sum(self.counts[c] for c in CONSUMERS[mat]) * INPUT_RATIO / INTERVAL

    # ----- Saving / loading -----

    def to_dict(self):
        return {
            "credits": self.credits,
            "stock": self.stock,
            "produced_total": self.produced_total,
            "counts": self.counts,
            "timers": self.timers,
            "saved_at": time.time(),
        }

    def save(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def load(self):
        """Loads the save file. Returns elapsed offline seconds (0 = new game)."""
        if not os.path.exists(SAVE_FILE):
            return 0
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return 0

        def migrate(d):
            # Translate keys of old German save files
            return {LEGACY_NAMES.get(k, k): v for k, v in d.items()}

        stock = migrate(data.get("stock", {}))
        produced = migrate(data.get("produced_total", {}))
        counts = migrate(data.get("counts", {}))
        timers = migrate(data.get("timers", {}))

        self.credits = data.get("credits", 0)
        for m in MATERIALS:
            self.stock[m] = stock.get(m, 0)
            self.produced_total[m] = produced.get(m, 0)
        for b in BUILDINGS:
            self.counts[b] = counts.get(b, self.counts[b])
            self.timers[b] = timers.get(b, 0.0)
        elapsed = max(0, time.time() - data.get("saved_at", time.time()))
        return elapsed


# ----------------------------------------------------------------------
# User interface
# ----------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Space Station Idle")
        self.geometry("1280x800")
        self.configure(bg=BG)

        self.game = Game()
        self.selected_mat = None
        self.running = False
        self.autosave_timer = 0.0
        self.node_rects = []        # (x1, y1, x2, y2, material)
        self.floats = []            # floating texts
        self.flash = {}             # material -> time of production flash
        self.unlock_anim = {}       # material -> start time of reveal animation
        self.seen_visible = None
        self.mouse_widget = None    # (x, y) mouse position in the map canvas
        self.hover_mat = None
        self.credits_shown = 0.0
        self.dt = 0.0
        self.shooting = []          # active shooting stars
        self.next_shoot = 0.0

        # Side panel state
        self.panel_visible = False
        self.panel_offset = PANEL_W   # 0 = open, PANEL_W = hidden
        self.panel_anim = None        # running slide animation
        self.panel_mouse = None
        self.panel_buttons = []     # (x1, y1, x2, y2, enabled, callback)

        # In-game dialog (replaces native message boxes)
        self.dialog = None
        self.dialog_buttons = []    # (x1, y1, x2, y2, callback)
        self.dialog_mouse = None

        # Update check in the background — never blocks the game
        self.update_info = {}
        self.update_prompted = False
        self.update_note_shown = False
        threading.Thread(target=check_for_update,
                         args=(self.update_info,), daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_home()

    # ------------------------------------------------------------------
    # Home screen (animated)
    # ------------------------------------------------------------------

    def show_home(self):
        self.home_active = True
        c = tk.Canvas(self, bg=BG, highlightthickness=0)
        c.pack(fill="both", expand=True)
        self.home_canvas = c

        add_nebula(c, 220, 180, 320, 200, "#2c2158")
        add_nebula(c, 1080, 560, 380, 240, "#1c3a5e")
        add_nebula(c, 620, 760, 300, 160, "#46203f")

        self.home_stars = []
        for _ in range(120):
            x = random.uniform(0, 1400)
            y = random.uniform(0, 900)
            r = random.uniform(0.6, 2.0)
            item = c.create_oval(x - r, y - r, x + r, y + r, outline="")
            self.home_stars.append({
                "item": item, "x": x, "y": y, "r": r,
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.6, 2.0),
                "drift": random.uniform(2, 10),
                "base": random.uniform(0.3, 0.9),
            })

        cx = 640
        self.home_sat = c.create_text(cx, 270, text="🛰️",
                                      font=("Segoe UI Emoji", 16), fill=TEXT_MAIN)
        self.home_title = [
            c.create_text(cx, 270, text="🚀", font=("Segoe UI Emoji", 60), fill=TEXT_MAIN),
            c.create_text(cx, 360, text="Space Station Idle",
                          font=("Segoe UI", 38, "bold"), fill=TEXT_MAIN),
            c.create_text(cx, 410, text="Build your industrial production chain in space",
                          font=("Segoe UI", 13), fill=TEXT_DIM),
        ]
        c.create_text(cx, 760, text=f"v{VERSION}  •  Auto-save  •  Offline production  •  Updates optional",
                      font=("Segoe UI", 10), fill=blend(TEXT_DIM, BG, 0.35), tags="footer")

        # Start button (canvas elements with glow ring)
        bw, bh, by = 220, 58, 500
        self.home_glow = round_rect(c, cx - bw / 2 - 4, by - 4, cx + bw / 2 + 4, by + bh + 4,
                                    16, fill="", outline="#2563eb", width=2)
        self.home_btn = round_rect(c, cx - bw / 2, by, cx + bw / 2, by + bh,
                                   14, fill="#2563eb", outline="", tags="startbtn")
        self.home_btn_text = c.create_text(cx, by + bh / 2, text="Start",
                                           font=("Segoe UI", 16, "bold"),
                                           fill="white", tags="startbtn")
        c.tag_bind("startbtn", "<Button-1>", lambda e: self.start_game())
        c.tag_bind("startbtn", "<Enter>",
                   lambda e: (c.itemconfig(self.home_btn, fill="#3b82f6"),
                              c.config(cursor="hand2")))
        c.tag_bind("startbtn", "<Leave>",
                   lambda e: (c.itemconfig(self.home_btn, fill="#2563eb"),
                              c.config(cursor="")))

        self.home_t0 = time.monotonic()
        self.home_shoot = []
        self.home_next_shoot = self.home_t0 + 2.0
        self.home_loop()

    def home_loop(self):
        if not self.home_active:
            return
        self._poll_update()
        if not self.home_active:
            return  # the update prompt may have triggered a restart
        c = self.home_canvas
        now = time.monotonic()
        t = now - self.home_t0
        w = max(self.winfo_width(), 800)
        h = max(self.winfo_height(), 600)

        for s in self.home_stars:
            s["x"] -= s["drift"] * FRAME_MS / 1000.0
            if s["x"] < -5:
                s["x"] = w + 5
                s["y"] = random.uniform(0, h)
            b = s["base"] * (0.55 + 0.45 * math.sin(t * s["speed"] + s["phase"]))
            c.coords(s["item"], s["x"] - s["r"], s["y"] - s["r"],
                     s["x"] + s["r"], s["y"] + s["r"])
            c.itemconfig(s["item"], fill=blend(BG, "#bcd0f0", b))

        # Title floats gently
        dy = math.sin(t * 1.4) * 6
        base_ys = (270, 360, 410)
        for item, by in zip(self.home_title, base_ys):
            c.coords(item, 640, by + dy)

        # Satellite orbits the rocket
        ang = t * 1.1
        c.coords(self.home_sat, 640 + 150 * math.cos(ang),
                 270 + dy + 45 * math.sin(ang))

        # Button glow pulses
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        c.itemconfig(self.home_glow, outline=blend("#1e3a6e", "#60a5fa", pulse))

        # Shooting stars
        c.delete("shoot")
        if now >= self.home_next_shoot:
            self.home_next_shoot = now + random.uniform(3, 9)
            self.home_shoot.append(self._new_shooting_star(w, h, now))
        self.home_shoot = [s for s in self.home_shoot
                           if self._draw_shooting_star(c, s, now, "shoot")]

        self.after(FRAME_MS, self.home_loop)

    # ------------------------------------------------------------------
    # In-game dialog — styled like the rest of the game, no native popups
    # ------------------------------------------------------------------

    def show_dialog(self, title, message, buttons,
                    accent="#60a5fa", emoji="🛰️"):
        """Shows a centered dialog card. `buttons` is a list of
        (label, callback, primary) — callbacks may be None."""
        self.close_dialog()
        w = 480
        dlg = tk.Canvas(self, bg=PANEL_BG, width=w, height=120,
                        highlightthickness=1, highlightbackground="#2b3a63")
        self.dialog = dlg
        self.dialog_mouse = None

        # Accent strip + badge + title
        dlg.create_rectangle(0, 0, w, 4, fill=accent, outline="")
        bx, by, br = 36, 40, 17
        dlg.create_oval(bx - br, by - br, bx + br, by + br,
                        fill=blend(accent, PANEL_BG, 0.75),
                        outline=blend(accent, PANEL_BG, 0.35))
        dlg.create_text(bx, by, text=emoji, font=("Segoe UI Emoji", 13))
        dlg.create_text(64, by, anchor="w", text=title,
                        font=("Segoe UI", 14, "bold"), fill=TEXT_MAIN)

        # Message (wrapped); dialog height adapts to the text
        msg = dlg.create_text(28, 72, anchor="nw", text=message,
                              font=("Segoe UI", 10), fill=TEXT_DIM,
                              width=w - 56)
        btn_y = dlg.bbox(msg)[3] + 24
        dlg.config(height=btn_y + 36 + 22)

        def render_buttons():
            dlg.delete("btn")
            self.dialog_buttons = []
            x2 = w - 24
            hover_any = False
            for label, cb, primary in reversed(buttons):
                bw = max(110, 9 * len(label) + 30)
                x1 = x2 - bw
                hovered = (self.dialog_mouse is not None and
                           x1 <= self.dialog_mouse[0] <= x2 and
                           btn_y <= self.dialog_mouse[1] <= btn_y + 36)
                hover_any |= hovered
                base = "#2563eb" if primary else "#1d2a4d"
                hov = "#3b82f6" if primary else "#27395f"
                round_rect(dlg, x1, btn_y, x2, btn_y + 36, 9,
                           fill=hov if hovered else base, outline="", tags="btn")
                dlg.create_text((x1 + x2) / 2, btn_y + 18, text=label,
                                font=("Segoe UI", 10, "bold"),
                                fill="white", tags="btn")
                self.dialog_buttons.append((x1, btn_y, x2, btn_y + 36, cb))
                x2 = x1 - 10
            dlg.config(cursor="hand2" if hover_any else "")

        render_buttons()
        dlg.bind("<Motion>", lambda e: (setattr(self, "dialog_mouse", (e.x, e.y)),
                                        render_buttons()))
        dlg.bind("<Leave>", lambda e: (setattr(self, "dialog_mouse", None),
                                       render_buttons()))
        dlg.bind("<Button-1>", self._on_dialog_click)

        dlg.place(relx=0.5, rely=0.36, anchor="center")
        tk.Misc.tkraise(dlg)
        self._dialog_anim_step({"t0": time.monotonic(), "dlg": dlg})

    def _dialog_anim_step(self, anim):
        """Gently floats the dialog into place."""
        dlg = anim["dlg"]
        if dlg is not self.dialog or not dlg.winfo_exists():
            return
        prog = (time.monotonic() - anim["t0"]) / 0.25
        dlg.place_configure(rely=0.36 + 0.06 * ease_out(prog))
        if prog < 1.0:
            self.after(10, lambda: self._dialog_anim_step(anim))

    def _on_dialog_click(self, event):
        for x1, y1, x2, y2, cb in self.dialog_buttons:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.close_dialog()
                if cb is not None:
                    cb()
                return

    def close_dialog(self):
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
        self.dialog_buttons = []

    # ------------------------------------------------------------------
    # Update flow: ask the player, download, restart on the new version
    # ------------------------------------------------------------------

    def _poll_update(self):
        """Called from both the home loop and the game loop."""
        info = self.update_info
        status = info.get("status")

        if status == "update-available" and not self.update_prompted:
            if self.dialog is not None:
                return  # another dialog is open — ask on a later frame
            self.update_prompted = True
            v = info.get("version", "?")

            def accept():
                info["status"] = "downloading"
                self._show_update_note(f"⬇ Downloading update v{v} ...")
                threading.Thread(target=download_update,
                                 args=(info,), daemon=True).start()

            def decline():
                info["status"] = "declined"

            self.show_dialog(
                "Update available",
                f"Version {v} of Space Station Idle is available.\n\n"
                f"Download it now? The game restarts on the new version "
                f"right away.\n\n"
                f"'Not now' keeps the current version (v{VERSION}) — "
                f"you can keep playing normally.",
                [("Not now", decline, False),
                 ("Update & restart", accept, True)],
                accent="#2563eb", emoji="⬆")

        elif status == "downloaded":
            info["status"] = "installing"
            if self.running:
                self.game.save()  # never lose progress on restart
            if not restart_into_update():
                info["status"] = "failed"
                self._show_update_note(
                    "⚠ Update failed — playing the current version")

        elif status == "download-failed" and not self.update_note_shown:
            self.update_note_shown = True
            self._show_update_note(
                "⚠ Update download failed — playing the current version")

    def _show_update_note(self, text):
        """Shows a note in the header (in-game) — silently skipped on the
        home screen, where the restart follows within moments anyway."""
        if hasattr(self, "header"):
            self.header.itemconfig(self.header_update, text=text)

    # ----- Shooting stars (home screen and map) -----

    @staticmethod
    def _new_shooting_star(w, h, now, x_off=0.0, y_off=0.0):
        ang = math.radians(random.uniform(25, 55))
        speed = random.uniform(700, 1100)
        return {
            "x": x_off + random.uniform(0.1, 0.9) * w,
            "y": y_off + random.uniform(0, 0.3) * h,
            "vx": speed * math.cos(ang) * random.choice((1, -1)),
            "vy": speed * math.sin(ang),
            "t0": now,
            "dur": random.uniform(0.5, 0.8),
        }

    @staticmethod
    def _draw_shooting_star(c, s, now, tag):
        age = now - s["t0"]
        if age > s["dur"]:
            return False
        px = s["x"] + s["vx"] * age
        py = s["y"] + s["vy"] * age
        v = math.hypot(s["vx"], s["vy"])
        nx, ny = s["vx"] / v, s["vy"] / v
        fade = 1 - age / s["dur"]
        for ln, col in ((70, blend(BG, "#7d96c8", 0.5 * fade)),
                        (30, blend(BG, "#e8eefc", 0.9 * fade))):
            c.create_line(px - nx * ln, py - ny * ln, px, py,
                          fill=col, width=2, tags=tag)
        return True

    # ------------------------------------------------------------------
    # Game start
    # ------------------------------------------------------------------

    def start_game(self):
        self.home_active = False
        self.home_canvas.destroy()
        self.build_game_ui()

        stock_before = dict(self.game.stock)
        elapsed = self.game.load()
        self.running = True
        self.last_time = time.monotonic()

        if elapsed > INTERVAL:
            self.game.simulate_offline(elapsed)
            gained = {m: self.game.stock[m] - stock_before.get(m, 0)
                      for m in MATERIALS
                      if self.game.stock[m] > stock_before.get(m, 0)}
            if gained:
                top = sorted(gained.items(), key=lambda kv: -kv[1])[:5]
                lines = [f"{MATERIALS[m]['emoji']} {m}:  +{fmt(v)}" for m, v in top]
                hours = min(elapsed, OFFLINE_CAP) / 3600
                self.show_dialog(
                    "Welcome back!",
                    f"Your station kept working for {fmt_rate(hours)} hours "
                    f"while you were away:\n\n" + "\n".join(lines),
                    [("Continue", None, True)],
                    accent=GOLD, emoji="🚀")

        self.credits_shown = float(self.game.credits)
        self.loop()

    # ------------------------------------------------------------------
    # Game UI
    # ------------------------------------------------------------------

    def build_game_ui(self):
        # Header bar as a canvas (for the credits pill)
        hd = tk.Canvas(self, height=50, bg=HEADER_BG, highlightthickness=0)
        hd.pack(fill="x")
        self.header = hd
        hd.create_text(16, 25, anchor="w", text="🚀 Space Station Idle",
                       font=("Segoe UI", 12, "bold"), fill=TEXT_DIM)
        self.header_pill = hd.create_polygon(
            round_rect_points(200, 10, 320, 40, 15),
            smooth=True, fill="#1c2740", outline="#2b3a63")
        self.header_credits = hd.create_text(220, 25, anchor="w",
                                             text="💰 0 Credits",
                                             font=("Segoe UI", 13, "bold"), fill=GOLD)
        self.header_update = hd.create_text(
            470, 25, anchor="w", text="",
            font=("Segoe UI", 10, "bold"), fill=GREEN)
        self.header_hint = hd.create_text(
            1260, 25, anchor="e",
            text="Left-click: open material   |   Right-click + drag: move the map",
            font=("Segoe UI", 10), fill=blend(TEXT_DIM, HEADER_BG, 0.25))
        hd.bind("<Configure>",
                lambda e: hd.coords(self.header_hint, e.width - 16, 25))
        tk.Frame(self, bg="#22315c", height=2).pack(fill="x")

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)

        self.build_panel(main)

        self.canvas = tk.Canvas(main, bg=BG, highlightthickness=0,
                                scrollregion=(-400, -200, 2000, 1900))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", lambda e: setattr(self, "mouse_widget", None))

        self.make_background()

    def make_background(self):
        """Nebulae + starfield — created once, twinkles every frame."""
        c = self.canvas
        add_nebula(c, 150, 350, 360, 230, "#2c2158")
        add_nebula(c, 1500, 520, 420, 260, "#1c3a5e")
        add_nebula(c, 750, 1180, 340, 210, "#46203f")
        add_nebula(c, 250, 1620, 300, 190, "#1c3a5e")
        add_nebula(c, 1650, 1480, 360, 220, "#2c2158")

        self.stars = []
        for _ in range(150):
            x = random.uniform(-400, 2000)
            y = random.uniform(-200, 1900)
            r = random.uniform(0.5, 1.8)
            item = c.create_oval(x - r, y - r, x + r, y + r,
                                 outline="", tags="static")
            self.stars.append({
                "item": item,
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.5, 1.8),
                "base": random.uniform(0.2, 0.7),
            })

    # ------------------------------------------------------------------
    # Side panel — fully canvas-drawn, slides in from the right
    # ------------------------------------------------------------------

    def build_panel(self, parent):
        p = tk.Canvas(parent, bg=PANEL_BG, width=PANEL_W, highlightthickness=0)
        self.panel = p
        # Input field as an embedded widget (persists permanently)
        self.sell_entry = tk.Entry(p, font=("Segoe UI", 11), bg="#0b1220",
                                   fg="white", insertbackground="white",
                                   relief="flat", justify="center")
        self.panel_entry_win = p.create_window(0, 0, window=self.sell_entry,
                                               anchor="nw", width=86, height=28,
                                               state="hidden", tags="win")
        p.bind("<Button-1>", self.on_panel_click)
        p.bind("<Motion>", lambda e: setattr(self, "panel_mouse", (e.x, e.y)))
        p.bind("<Leave>", lambda e: setattr(self, "panel_mouse", None))

    def _panel_hover(self, x1, y1, x2, y2):
        if self.panel_mouse is None:
            return False
        mx, my = self.panel_mouse
        return x1 <= mx <= x2 and y1 <= my <= y2

    def panel_button(self, x1, y1, x2, y2, text, cb, base, hover,
                     enabled=True, font=("Segoe UI", 10, "bold")):
        p = self.panel
        hovered = enabled and self._panel_hover(x1, y1, x2, y2)
        fill = (hover if hovered else base) if enabled else "#232c47"
        round_rect(p, x1, y1, x2, y2, 9, fill=fill, outline="", tags="dyn")
        p.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, font=font,
                      fill="white" if enabled else "#5a6b8f", tags="dyn")
        self.panel_buttons.append((x1, y1, x2, y2, enabled, cb))
        return hovered

    def on_panel_click(self, event):
        for x1, y1, x2, y2, enabled, cb in self.panel_buttons:
            if enabled and x1 <= event.x <= x2 and y1 <= event.y <= y2:
                cb()
                return

    def _start_panel_anim(self, to):
        """Starts the panel slide in/out (its own fast loop)."""
        if self.panel_anim is None and self.panel_offset == to and \
                self.panel_visible == (to == 0):
            return
        if not self.panel_visible:
            self.panel_visible = True
            self.panel.place(relx=1.0, rely=0, relheight=1.0, anchor="ne",
                             x=round(self.panel_offset))
            tk.Misc.tkraise(self.panel)  # Canvas.lift() would mean canvas items
        anim = {"from": self.panel_offset, "to": to, "t0": time.monotonic()}
        self.panel_anim = anim
        self._panel_anim_step(anim)

    def _panel_anim_step(self, anim):
        if self.panel_anim is not anim:
            return  # superseded by a newer animation
        duration = 0.3
        prog = (time.monotonic() - anim["t0"]) / duration
        eased = ease_out(prog)
        self.panel_offset = anim["from"] + (anim["to"] - anim["from"]) * eased
        self.panel.place_configure(x=round(self.panel_offset))
        if prog >= 1.0:
            self.panel_offset = anim["to"]
            self.panel_anim = None
            if anim["to"] >= PANEL_W:  # fully slid out
                self.panel.place_forget()
                self.panel_visible = False
                self.selected_mat = None
            return
        self.after(10, lambda: self._panel_anim_step(anim))

    def draw_panel(self, t):
        p = self.panel
        mat = self.selected_mat
        if not self.panel_visible or mat is None:
            p.itemconfigure(self.panel_entry_win, state="hidden")
            return

        p.delete("dyn")
        self.panel_buttons = []
        ox = 0

        g = self.game
        info = MATERIALS[mat]
        accent = info["color"]
        bname = PRODUCER[mat]
        ph = p.winfo_height()
        hover_any = False

        # Background accents
        p.create_rectangle(ox, 0, ox + PANEL_W, 4, fill=accent, outline="", tags="dyn")
        p.create_line(ox, 0, ox, ph, fill="#22315c", width=2, tags="dyn")

        # Header: badge + name + close
        bx, by, br = ox + 32, 36, 17
        p.create_oval(bx - br, by - br, bx + br, by + br,
                      fill=blend(accent, PANEL_BG, 0.75),
                      outline=blend(accent, PANEL_BG, 0.35), tags="dyn")
        p.create_text(bx, by, text=info["emoji"],
                      font=("Segoe UI Emoji", 13), tags="dyn")
        p.create_text(ox + 58, by, anchor="w", text=mat,
                      font=("Segoe UI", 14, "bold"), fill=TEXT_MAIN, tags="dyn")
        hover_any |= self.panel_button(ox + 282, 22, ox + 308, 48, "✕",
                                       self.close_panel, PANEL_BG, "#243153",
                                       font=("Segoe UI", 12))

        # --- Storage card ---
        p.create_polygon(round_rect_points(ox + 14, 64, ox + 306, 148, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline=blend(accent, PANEL_BG, 0.6), tags="dyn")
        p.create_text(ox + 28, 82, anchor="w", text="STORAGE",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.create_text(ox + 28, 106, anchor="w", text=fmt(g.stock[mat]),
                      font=("Segoe UI", 19, "bold"), fill=TEXT_MAIN, tags="dyn")
        p.create_text(ox + 28, 132, anchor="w",
                      text=f"Value: {fmt(info['price'])} Cr each",
                      font=("Segoe UI", 9), fill=GOLD, tags="dyn")
        prod = g.rate_produced(mat)
        cons = g.rate_consumed(mat)
        p.create_text(ox + 292, 98, anchor="e", text=f"+{fmt_rate(prod)}/s",
                      font=("Segoe UI", 9), fill=GREEN, tags="dyn")
        p.create_text(ox + 292, 114, anchor="e", text=f"-{fmt_rate(cons)}/s",
                      font=("Segoe UI", 9),
                      fill=RED if cons > 0 else blend(TEXT_DIM, PANEL_BG, 0.4),
                      tags="dyn")

        # --- Sell card ---
        p.create_polygon(round_rect_points(ox + 14, 160, ox + 306, 268, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline="#22315c", tags="dyn")
        p.create_text(ox + 28, 178, anchor="w", text="SELL",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.coords(self.panel_entry_win, ox + 28, 192)
        p.itemconfigure(self.panel_entry_win, state="normal")
        hover_any |= self.panel_button(ox + 124, 192, ox + 292, 220, "Sell",
                                       self.sell_amount, "#2563eb", "#3b82f6")
        third = (292 - 28 - 12) / 3
        for i, (label, cb) in enumerate((
                ("10", lambda: self._sell_feedback(g.sell(mat, 10))),
                ("Half", lambda: self._sell_feedback(g.sell(mat, g.stock[mat] // 2))),
                ("All", lambda: self._sell_feedback(g.sell(mat, g.stock[mat]))))):
            bx1 = ox + 28 + i * (third + 6)
            hover_any |= self.panel_button(bx1, 230, bx1 + third, 256, label, cb,
                                           "#1d2a4d", "#27395f",
                                           font=("Segoe UI", 9, "bold"))

        # --- Building card ---
        credits_cost, mats = g.cost_of(bname)
        n_lines = 1 + len(mats)
        cost_y0 = 372
        btn_y = cost_y0 + n_lines * 19 + 10
        card_y2 = btn_y + 36 + 14
        p.create_polygon(round_rect_points(ox + 14, 280, ox + 306, card_y2, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline="#22315c", tags="dyn")
        p.create_text(ox + 28, 298, anchor="w", text="BUILDING",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.create_text(ox + 28, 320, anchor="w", text=bname,
                      font=("Segoe UI", 12, "bold"), fill=accent, tags="dyn")
        p.create_text(ox + 292, 320, anchor="e", text=f"{g.counts[bname]}×",
                      font=("Segoe UI", 12, "bold"), fill=TEXT_MAIN, tags="dyn")
        p.create_text(ox + 28, 340, anchor="w",
                      text=f"Produces 1 {mat} every {fmt_rate(INTERVAL)}s",
                      font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")
        p.create_text(ox + 28, 360, anchor="w", text="COST",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")

        ok = g.credits >= credits_cost
        p.create_text(ox + 28, cost_y0 + 9, anchor="w",
                      text=f"{'✔' if ok else '✘'}  {fmt(credits_cost)} Credits",
                      font=("Segoe UI", 9, "bold"),
                      fill=GOLD if ok else RED, tags="dyn")
        for i, (m, amt) in enumerate(mats.items(), start=1):
            ok = g.stock[m] >= amt
            p.create_text(ox + 28, cost_y0 + 9 + i * 19, anchor="w",
                          text=f"{'✔' if ok else '✘'}  {fmt(amt)} {m}",
                          font=("Segoe UI", 9),
                          fill=TEXT_MAIN if ok else RED, tags="dyn")
            p.create_text(ox + 292, cost_y0 + 9 + i * 19, anchor="e",
                          text=fmt(g.stock[m]),
                          font=("Segoe UI", 8),
                          fill=blend(TEXT_DIM, PANEL_BG, 0.25), tags="dyn")

        affordable = g.can_afford(bname)
        hover_any |= self.panel_button(ox + 28, btn_y, ox + 292, btn_y + 36,
                                       "Buy", self.buy, "#16a34a", "#22c55e",
                                       enabled=affordable,
                                       font=("Segoe UI", 11, "bold"))

        p.config(cursor="hand2" if hover_any else "")

    # ----- Input (map) -----

    def on_mouse_move(self, event):
        self.mouse_widget = (event.x, event.y)

    def on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for x1, y1, x2, y2, mat in self.node_rects:
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.select_mat(mat)
                return
        self.close_panel()  # clicking empty space closes the panel

    def select_mat(self, mat):
        self.selected_mat = mat
        self.sell_entry.delete(0, "end")
        self._start_panel_anim(0)

    def close_panel(self):
        if self.panel_visible:
            self._start_panel_anim(PANEL_W)

    # ----- Actions -----

    def spawn_float(self, x, y, text, color):
        if len(self.floats) < 20:
            self.floats.append({"x": x, "y": y, "text": text,
                                "color": color, "t0": time.monotonic()})

    def sell_amount(self):
        if self.selected_mat is None:
            return
        try:
            amount = int(self.sell_entry.get().strip())
        except ValueError:
            return
        self._sell_feedback(self.game.sell(self.selected_mat, amount))

    def _sell_feedback(self, gain):
        if gain > 0 and self.selected_mat is not None:
            x, y = MATERIALS[self.selected_mat]["pos"]
            self.spawn_float(x + NODE_W / 2, y + 14, f"+{fmt(gain)} Cr", GOLD)

    def buy(self):
        if self.selected_mat is None:
            return
        if self.game.buy(PRODUCER[self.selected_mat]):
            x, y = MATERIALS[self.selected_mat]["pos"]
            self.spawn_float(x + NODE_W / 2, y + 14, "+1 building",
                             MATERIALS[self.selected_mat]["color"])
            self.flash[self.selected_mat] = time.monotonic()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def loop(self):
        if not self.running:
            return
        now = time.monotonic()
        self.dt = now - self.last_time
        self.last_time = now

        self._poll_update()
        self.game.tick(self.dt)

        self.autosave_timer += self.dt
        if self.autosave_timer >= AUTOSAVE_SECONDS:
            self.autosave_timer = 0.0
            self.game.save()

        self.draw()
        self.after(FRAME_MS, self.loop)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self):
        g = self.game
        c = self.canvas
        t = time.monotonic()
        c.delete("dyn")
        self.node_rects = []

        # Credits count up/down smoothly
        self.credits_shown += (g.credits - self.credits_shown) * min(1.0, self.dt * 8)
        if abs(g.credits - self.credits_shown) < 1:
            self.credits_shown = float(g.credits)
        hd = self.header
        hd.itemconfig(self.header_credits,
                      text=f"💰 {fmt(round(self.credits_shown))} Credits")
        bb = hd.bbox(self.header_credits)
        if bb:
            hd.coords(self.header_pill,
                      *round_rect_points(bb[0] - 14, 9, bb[2] + 14, 41, 16))

        # Stars twinkle
        for s in self.stars:
            b = s["base"] * (0.55 + 0.45 * math.sin(t * s["speed"] + s["phase"]))
            c.itemconfig(s["item"], fill=blend(BG, "#bcd0f0", b))

        # Visible map area (for culling)
        vw = c.winfo_width()
        vh = c.winfo_height()
        vx1, vy1 = c.canvasx(0) - 60, c.canvasy(0) - 60
        vx2, vy2 = c.canvasx(vw) + 60, c.canvasy(vh) + 60

        visible = {m for m in MATERIALS if g.material_visible(m)}

        # Newly unlocked nodes -> reveal animation
        if self.seen_visible is None:
            self.seen_visible = set(visible)
        else:
            for mat in visible - self.seen_visible:
                self.unlock_anim[mat] = t
            self.seen_visible = set(visible)

        # Determine hover
        self.hover_mat = None
        if self.mouse_widget is not None:
            mx = c.canvasx(self.mouse_widget[0])
            my = c.canvasy(self.mouse_widget[1])
            for mat in visible:
                x, y = MATERIALS[mat]["pos"]
                if x <= mx <= x + NODE_W and y <= my <= y + NODE_H:
                    self.hover_mat = mat
                    break
        c.config(cursor="hand2" if self.hover_mat else "")

        # Connection lines (glow + arrowhead) + flowing material dots with tail
        for bname, b in BUILDINGS.items():
            out = b["output"]
            if out not in visible:
                continue
            for inp in b["inputs"]:
                if inp not in visible:
                    continue
                p0, p1, p2, p3 = connection_curve(inp, out)
                pts = []
                for i in range(15):
                    px, py = bezier_point(p0, p1, p2, p3, i / 14)
                    pts.extend((px, py))
                col = MATERIALS[inp]["color"]
                bright = blend(col, BG, 0.6)
                c.create_line(*pts, fill=blend(col, BG, 0.86), width=5, tags="dyn")
                c.create_line(*pts, fill=bright, width=1.8, tags="dyn")
                ax, ay = p3
                c.create_polygon(ax, ay - 1, ax - 5, ay - 9, ax + 5, ay - 9,
                                 fill=bright, outline="", tags="dyn")
                # Dot with tail travels in sync with the production cycle
                if g.counts[bname] > 0:
                    phs = (g.timers[bname] / INTERVAL) % 1.0
                    for back, r, dim in ((0.0, 4.0, 0.0), (0.05, 2.8, 0.45),
                                         (0.10, 1.8, 0.7)):
                        tt = phs - back
                        if tt < 0:
                            continue
                        px, py = bezier_point(p0, p1, p2, p3, tt)
                        c.create_oval(px - r, py - r, px + r, py + r,
                                      fill=blend(col, BG, dim), outline="", tags="dyn")

        # Nodes (only draw inside the visible area)
        for mat in visible:
            x, y = MATERIALS[mat]["pos"]
            if x + NODE_W < vx1 or x > vx2 or y + NODE_H < vy1 or y > vy2:
                continue
            self.draw_node(mat, t)

        # Production events -> floating "+n" texts + flash
        for out, p in g.events:
            if out in visible:
                self.flash[out] = t
                x, y = MATERIALS[out]["pos"]
                self.spawn_float(x + NODE_W - 34, y + 30, f"+{fmt(p)}",
                                 MATERIALS[out]["color"])
        g.events.clear()

        alive = []
        for fl in self.floats:
            age = (t - fl["t0"]) / 1.1
            if age >= 1.0:
                continue
            dy = -38 * ease_out(age)
            c.create_text(fl["x"], fl["y"] + dy, text=fl["text"],
                          font=("Segoe UI", 11, "bold"),
                          fill=blend(fl["color"], BG, age * 0.85), tags="dyn")
            alive.append(fl)
        self.floats = alive

        # Shooting stars across the map
        if self.next_shoot == 0.0:
            self.next_shoot = t + random.uniform(5, 14)
        if t >= self.next_shoot:
            self.next_shoot = t + random.uniform(5, 14)
            self.shooting.append(self._new_shooting_star(vw, vh, t, vx1 + 60, vy1 + 60))
        self.shooting = [s for s in self.shooting
                         if self._draw_shooting_star(c, s, t, "dyn")]

        # Close the panel if the material is no longer visible
        if self.selected_mat is not None and self.selected_mat not in visible:
            self.close_panel()
        self.draw_panel(t)

    def draw_node(self, mat, t):
        g = self.game
        c = self.canvas
        info = MATERIALS[mat]
        x, y = info["pos"]
        bname = PRODUCER[mat]
        accent = info["color"]

        # Reveal animation: card grows from the center
        s = 1.0
        if mat in self.unlock_anim:
            age = (t - self.unlock_anim[mat]) / 0.45
            if age >= 1.0:
                del self.unlock_anim[mat]
            else:
                s = 0.25 + 0.75 * ease_out(age)

        cx, cy = x + NODE_W / 2, y + NODE_H / 2
        w, h = NODE_W * s, NODE_H * s
        x1, y1 = cx - w / 2, cy - h / 2
        x2, y2 = cx + w / 2, cy + h / 2

        hovered = mat == self.hover_mat
        selected = mat == self.selected_mat

        if selected:
            pulse = 0.5 + 0.5 * math.sin(t * 4)
            outline = blend(GOLD, "#ffffff", pulse * 0.35)
            fill = CARD_SELECTED
            width = 2.5
        elif hovered:
            outline = blend(accent, "#ffffff", 0.25)
            fill = CARD_HOVER
            width = 2
        else:
            outline = blend(accent, BG, 0.45)
            fill = CARD
            width = 1.5

        # Flash when production finishes
        if mat in self.flash:
            fage = (t - self.flash[mat]) / 0.45
            if fage >= 1.0:
                del self.flash[mat]
            elif not selected:
                outline = blend(outline, accent, (1 - fage) * 0.9)
                width = 1.5 + (1 - fage) * 1.5

        round_rect(c, x1 + 4, y1 + 4, x2 + 4, y2 + 4, 14,
                   fill=SHADOW, outline="", tags="dyn")
        round_rect(c, x1, y1, x2, y2, 14,
                   fill=fill, outline=outline, width=width, tags="dyn")
        # subtle highlight along the top edge
        c.create_line(x1 + 14, y1 + 2, x2 - 14, y1 + 2,
                      fill=blend(fill, "#ffffff", 0.12), tags="dyn")
        self.node_rects.append((x, y, x + NODE_W, y + NODE_H, mat))

        if s < 0.92:
            return  # only show content once the card is almost fully grown

        # Icon badge
        bx, by, br = x + 27, y + 26, 15
        c.create_oval(bx - br, by - br, bx + br, by + br,
                      fill=blend(accent, BG, 0.78),
                      outline=blend(accent, BG, 0.4), tags="dyn")
        c.create_text(bx, by, text=info["emoji"],
                      font=("Segoe UI Emoji", 12), tags="dyn")

        c.create_text(x + 50, y + 26, anchor="w", text=mat,
                      font=("Segoe UI", 11, "bold"), fill=accent, tags="dyn")

        # Stock large, rates stacked on the right
        c.create_text(x + 14, y + 58, anchor="w",
                      text=fmt(g.stock[mat]),
                      font=("Segoe UI", 15, "bold"), fill=TEXT_MAIN, tags="dyn")
        prod = g.rate_produced(mat)
        cons = g.rate_consumed(mat)
        c.create_text(x + NODE_W - 14, y + 50, anchor="e",
                      text=f"+{fmt_rate(prod)}/s",
                      font=("Segoe UI", 9), fill=GREEN, tags="dyn")
        c.create_text(x + NODE_W - 14, y + 65, anchor="e",
                      text=f"-{fmt_rate(cons)}/s",
                      font=("Segoe UI", 9),
                      fill=RED if cons > 0 else blend(TEXT_DIM, BG, 0.4), tags="dyn")

        # Building line + time remaining
        c.create_text(x + 14, y + 81, anchor="w",
                      text=f"{g.counts[bname]}× {bname}",
                      font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")
        if g.counts[bname] > 0:
            rest = max(0.0, INTERVAL - g.timers[bname])
            c.create_text(x + NODE_W - 14, y + 81, anchor="e",
                          text=f"{fmt_rate(rest)}s",
                          font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")

        # Progress bar with a glowing tip
        frac = min(1.0, g.timers[bname] / INTERVAL)
        bar_x, bar_y = x + 14, y + 96
        bar_w, bar_h = NODE_W - 28, 9
        round_rect(c, bar_x, bar_y, bar_x + bar_w, bar_y + bar_h, 4,
                   fill=BG, outline=blend(accent, BG, 0.7), tags="dyn")
        if g.counts[bname] > 0:
            fw = bar_w * frac
            if fw >= 9:
                round_rect(c, bar_x, bar_y, bar_x + fw, bar_y + bar_h, 4,
                           fill=accent, outline="", tags="dyn")
            elif fw > 1:
                c.create_rectangle(bar_x, bar_y + 1, bar_x + fw, bar_y + bar_h - 1,
                                   fill=accent, outline="", tags="dyn")
            if fw > 2:
                hx = bar_x + fw
                hy = bar_y + bar_h / 2
                c.create_oval(hx - 3.5, hy - 3.5, hx + 3.5, hy + 3.5,
                              fill=blend(accent, "#ffffff", 0.45),
                              outline="", tags="dyn")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def on_close(self):
        if self.running:
            self.game.save()
        self.destroy()


if __name__ == "__main__":
    apply_pending_exe_update()
    app = App()
    app.mainloop()
