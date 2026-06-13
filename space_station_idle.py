# -*- coding: utf-8 -*-
"""Space Station Idle v2.0 — per-building storage, manual chains, research."""
from __future__ import annotations
import json, os, uuid, tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox, simpledialog

# ════════════════════════════════════════════════════════════════════════════════
# Game constants
# ════════════════════════════════════════════════════════════════════════════════
VERSION        = "2.0.0"
INPUT_RATIO    = 3
INTERVAL       = 5.0     # production tick (seconds)
FRACHTER_TICK  = 30.0
SALES_TICK     = 30.0
CAP_PROD       = 200
CAP_SPECIAL    = 1000
STARTING_CR    = 500
MAX_SLOTS_BASE = 10
SLOT_UPGRADES  = [(5_000, 5), (20_000, 5), (80_000, 10)]   # (cost_cr, extra_slots)
STATION_COSTS  = [1_000, 4_000, 12_000, 40_000, 120_000]   # cost to buy station N+1

# ── chain colours ─────────────────────────────────────────────────────────────
C_METAL   = "#60a5fa"
C_COAL    = "#94a3b8"
C_COPPER  = "#fb923c"
C_SILICON = "#4ade80"
C_OIL     = "#facc15"
C_MECH    = "#a78bfa"
C_ROBOT   = "#f472b6"

# ── materials ─────────────────────────────────────────────────────────────────
MATERIALS = {
    "Iron Ore":        {"emoji": "🔩", "price": 1, "pos": (150,  60), "color": C_METAL},
    "Coal":            {"emoji": "⚫", "price": 1, "pos": (420,  60), "color": C_COAL},
    "Copper Ore":      {"emoji": "🟠", "price": 1, "pos": (690,  60), "color": C_COPPER},
    "Silicon Sand":    {"emoji": "🏜️", "price": 1, "pos": (960,  60), "color": C_SILICON},
    "Crude Oil":       {"emoji": "🛢️", "price": 1, "pos": (1230, 60), "color": C_OIL},
    "Iron Ingot":      {"emoji": "🧱", "pos": (150,  250), "color": C_METAL},
    "Copper Ingot":    {"emoji": "🟧", "pos": (690,  250), "color": C_COPPER},
    "Raw Silicon":     {"emoji": "💎", "pos": (960,  250), "color": C_SILICON},
    "Plastic":         {"emoji": "🧪", "pos": (1230, 250), "color": C_OIL},
    "Steel Ingot":     {"emoji": "⚒️", "pos": (280,  440), "color": C_METAL},
    "Copper Wire":     {"emoji": "🧵", "pos": (690,  440), "color": C_COPPER},
    "Silicon Wafer":   {"emoji": "💿", "pos": (960,  440), "color": C_SILICON},
    "Iron Plate":      {"emoji": "🟫", "pos": (150,  630), "color": C_METAL},
    "Steel Sheet":     {"emoji": "🪨", "pos": (420,  630), "color": C_METAL},
    "Copper Cable":    {"emoji": "🪢", "pos": (690,  630), "color": C_COPPER},
    "Microchip":       {"emoji": "🔲", "pos": (960,  630), "color": C_SILICON},
    "Steel Beam":      {"emoji": "🏗️", "pos": (280,  820), "color": C_METAL},
    "Insulated Cable": {"emoji": "🔌", "pos": (690,  820), "color": C_COPPER},
    "Coil":            {"emoji": "🧲", "pos": (500, 1010), "color": C_COPPER},
    "Circuit Board":   {"emoji": "💻", "pos": (830, 1010), "color": C_SILICON},
    "Machine Frame":   {"emoji": "🛠️", "pos": (420, 1200), "color": C_MECH},
    "Motor":           {"emoji": "⚙️", "pos": (420, 1390), "color": C_MECH},
    "Basic Robot":     {"emoji": "🤖", "pos": (650, 1580), "color": C_ROBOT},
    # END_MATERIALS
}

BUILDINGS = {
    "Iron Mine":       {"output":"Iron Ore",      "inputs":[],                                   "credits":30,    "materials":{},                                    "extraction":True},
    "Coal Mine":       {"output":"Coal",           "inputs":[],                                   "credits":30,    "materials":{},                                    "extraction":True},
    "Copper Mine":     {"output":"Copper Ore",     "inputs":[],                                   "credits":30,    "materials":{},                                    "extraction":True},
    "Silicon Quarry":  {"output":"Silicon Sand",   "inputs":[],                                   "credits":60,    "materials":{},                                    "extraction":True},
    "Oil Pump":        {"output":"Crude Oil",      "inputs":[],                                   "credits":30,    "materials":{},                                    "extraction":True},
    "Iron Smelter":    {"output":"Iron Ingot",     "inputs":["Iron Ore"],                         "credits":100,   "materials":{"Iron Ore":50},                       "extraction":False},
    "Copper Smelter":  {"output":"Copper Ingot",   "inputs":["Copper Ore"],                       "credits":100,   "materials":{"Copper Ore":50},                     "extraction":False},
    "Silicon Furnace": {"output":"Raw Silicon",    "inputs":["Silicon Sand"],                     "credits":100,   "materials":{"Silicon Sand":50},                   "extraction":False},
    "Refinery":        {"output":"Plastic",        "inputs":["Crude Oil"],                        "credits":120,   "materials":{"Crude Oil":50},                      "extraction":False},
    "Blast Furnace":   {"output":"Steel Ingot",    "inputs":["Iron Ingot","Coal"],                "credits":300,   "materials":{"Iron Ingot":30,"Coal":30},            "extraction":False},
    "Rolling Mill":    {"output":"Iron Plate",     "inputs":["Iron Ingot","Steel Ingot"],         "credits":600,   "materials":{"Iron Ingot":30,"Steel Ingot":20},     "extraction":False},
    "Steel Mill":      {"output":"Steel Sheet",    "inputs":["Steel Ingot","Coal"],               "credits":500,   "materials":{"Steel Ingot":25,"Coal":40},           "extraction":False},
    "Press Works":     {"output":"Steel Beam",     "inputs":["Steel Sheet","Iron Plate"],         "credits":1500,  "materials":{"Steel Sheet":20,"Iron Plate":20},     "extraction":False},
    "Wire Mill":       {"output":"Copper Wire",    "inputs":["Copper Ingot","Coal"],              "credits":300,   "materials":{"Copper Ingot":30,"Coal":30},          "extraction":False},
    "Cable Works":     {"output":"Copper Cable",   "inputs":["Copper Wire","Copper Ingot"],       "credits":600,   "materials":{"Copper Wire":25,"Copper Ingot":25},   "extraction":False},
    "Insulation Plant":{"output":"Insulated Cable","inputs":["Copper Cable","Plastic"],           "credits":1200,  "materials":{"Copper Cable":20,"Plastic":30},       "extraction":False},
    "Coil Factory":    {"output":"Coil",           "inputs":["Insulated Cable","Iron Ingot"],     "credits":2500,  "materials":{"Insulated Cable":15,"Iron Ingot":30}, "extraction":False},
    "Wafer Plant":     {"output":"Silicon Wafer",  "inputs":["Raw Silicon","Copper Ingot"],       "credits":500,   "materials":{"Raw Silicon":30,"Copper Ingot":25},   "extraction":False},
    "Chip Factory":    {"output":"Microchip",      "inputs":["Silicon Wafer","Copper Wire"],      "credits":1500,  "materials":{"Silicon Wafer":20,"Copper Wire":30},  "extraction":False},
    "Circuit Board Factory":{"output":"Circuit Board","inputs":["Microchip","Insulated Cable"],   "credits":4000,  "materials":{"Microchip":15,"Insulated Cable":15},  "extraction":False},
    "Machine Works":   {"output":"Machine Frame",  "inputs":["Steel Beam","Coil"],               "credits":8000,  "materials":{"Steel Beam":10,"Coil":10},            "extraction":False},
    "Motor Factory":   {"output":"Motor",          "inputs":["Machine Frame","Steel Sheet"],      "credits":15000, "materials":{"Machine Frame":5,"Steel Sheet":20},   "extraction":False},
    "Robot Factory":   {"output":"Basic Robot",    "inputs":["Motor","Circuit Board","Steel Beam"],"credits":40000,"materials":{"Motor":5,"Circuit Board":5,"Steel Beam":10},"extraction":False},
    # END_BUILDINGS
}

BUILDING_ORDER = list(BUILDINGS.keys())
PRODUCER  = {b["output"]: n for n, b in BUILDINGS.items()}
CONSUMERS = {m: [] for m in MATERIALS}
for _n, _b in BUILDINGS.items():
    for _i in _b["inputs"]:
        CONSUMERS[_i].append(_n)


def _compute_prices():
    done = {m for m in MATERIALS if "price" in MATERIALS[m]}
    todo = [m for m in MATERIALS if m not in done]
    while todo:
        for mat in list(todo):
            inps = BUILDINGS[PRODUCER[mat]]["inputs"]
            if all(i in done for i in inps):
                MATERIALS[mat]["price"] = 2 * INPUT_RATIO * sum(
                    MATERIALS[i]["price"] for i in inps)
                done.add(mat); todo.remove(mat)

_compute_prices()

# Research helpers
UNLOCKED_START = frozenset(n for n, b in BUILDINGS.items() if b["extraction"])

def research_cost(bname: str) -> int:
    return BUILDINGS[bname]["credits"] * 2

def research_prereqs(bname: str) -> list[str]:
    return [PRODUCER[inp] for inp in BUILDINGS[bname]["inputs"] if inp in PRODUCER]

# ════════════════════════════════════════════════════════════════════════════════
# Colour palette
# ════════════════════════════════════════════════════════════════════════════════
BG       = "#0b0f1a"
BG2      = "#0e1426"
CARD_BG  = "#151d33"
BORDER   = "#22315c"
TEXT     = "#e8eefc"
TEXT_DIM = "#8fa3c8"
ACCENT   = "#3b82f6"
GREEN    = "#22c55e"
YELLOW   = "#fbbf24"
RED      = "#ef4444"

# ════════════════════════════════════════════════════════════════════════════════
# Data classes
# ════════════════════════════════════════════════════════════════════════════════
@dataclass
class BuildingInstance:
    id:              str
    btype:           str
    slot:            int
    storage:         dict = field(default_factory=dict)
    inputs_from:     dict = field(default_factory=dict)   # resource -> src_id  (Phase 2)
    frachter_routes: list = field(default_factory=list)   # Phase 4

    def cap(self) -> int:
        return CAP_PROD

    def output_resource(self) -> str | None:
        b = BUILDINGS.get(self.btype)
        return b["output"] if b else None

    def storage_amount(self) -> int:
        res = self.output_resource()
        return self.storage.get(res, 0) if res else 0

    def storage_value(self) -> int:
        return sum(int(amt * MATERIALS[r]["price"])
                   for r, amt in self.storage.items() if r in MATERIALS)

    def mat_color(self) -> str:
        res = self.output_resource()
        return MATERIALS[res]["color"] if res else "#ffffff"

    def mat_emoji(self) -> str:
        res = self.output_resource()
        return MATERIALS[res]["emoji"] if res else "❓"

    def to_dict(self) -> dict:
        return {"id": self.id, "btype": self.btype, "slot": self.slot,
                "storage": self.storage, "inputs_from": self.inputs_from,
                "frachter_routes": self.frachter_routes}

    @classmethod
    def from_dict(cls, d: dict) -> "BuildingInstance":
        return cls(id=d["id"], btype=d["btype"], slot=d["slot"],
                   storage=d.get("storage", {}),
                   inputs_from=d.get("inputs_from", {}),
                   frachter_routes=d.get("frachter_routes", []))


@dataclass
class Station:
    name:          str
    slots:         int  = MAX_SLOTS_BASE
    instances:     dict = field(default_factory=dict)   # int slot -> BuildingInstance
    upgrade_level: int  = 0

    def free_slots(self) -> list[int]:
        return [i for i in range(self.slots) if i not in self.instances]

    def to_dict(self) -> dict:
        return {"name": self.name, "slots": self.slots,
                "upgrade_level": self.upgrade_level,
                "instances": {str(k): v.to_dict() for k, v in self.instances.items()}}

    @classmethod
    def from_dict(cls, d: dict) -> "Station":
        s = cls(name=d["name"], slots=d.get("slots", MAX_SLOTS_BASE),
                upgrade_level=d.get("upgrade_level", 0))
        for k, v in d.get("instances", {}).items():
            s.instances[int(k)] = BuildingInstance.from_dict(v)
        return s

# ════════════════════════════════════════════════════════════════════════════════
# Game state
# ════════════════════════════════════════════════════════════════════════════════
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_v2.json")

class GameState:
    def __init__(self):
        self.credits  = STARTING_CR
        self.stations: list[Station] = [Station("Alpha")]
        self.unlocked: set[str]      = set(UNLOCKED_START)
        self.events:   list[str]     = []

    # ── production ───────────────────────────────────────────────────────────
    def produce_tick(self):
        new_ev: list[str] = []
        for st in self.stations:
            for inst in list(st.instances.values()):
                b = BUILDINGS.get(inst.btype)
                if not b:
                    continue
                if b["extraction"]:
                    out = b["output"]
                    cur = inst.storage.get(out, 0)
                    if cur < inst.cap():
                        inst.storage[out] = cur + 1
                        new_ev.append(f"+1 {out}")
                # Processing buildings need connections — Phase 2
        self.events = (new_ev + self.events)[:80]

    # ── buying / removing ────────────────────────────────────────────────────
    def buy_and_place(self, btype: str, station_idx: int, slot: int):
        cost = BUILDINGS[btype]["credits"]
        if self.credits < cost:
            return False, "Not enough credits"
        st = self.stations[station_idx]
        if slot in st.instances:
            return False, "Slot occupied"
        if slot >= st.slots:
            return False, "Slot does not exist"
        self.credits -= cost
        inst = BuildingInstance(id=str(uuid.uuid4())[:8], btype=btype, slot=slot)
        st.instances[slot] = inst
        return True, inst

    def remove_building(self, station_idx: int, slot: int):
        st = self.stations[station_idx]
        st.instances.pop(slot, None)

    def sell_instance(self, station_idx: int, slot: int) -> int:
        inst = self.stations[station_idx].instances.get(slot)
        if not inst:
            return 0
        val = inst.storage_value()
        inst.storage.clear()
        self.credits += val
        return val

    # ── research ─────────────────────────────────────────────────────────────
    def can_research(self, bname: str) -> tuple[bool, str]:
        if bname in self.unlocked:
            return False, "already"
        for pre in research_prereqs(bname):
            if pre not in self.unlocked:
                return False, "prereq"
        if self.credits < research_cost(bname):
            return False, "credits"
        return True, "ok"

    def do_research(self, bname: str) -> bool:
        ok, _ = self.can_research(bname)
        if not ok:
            return False
        self.credits -= research_cost(bname)
        self.unlocked.add(bname)
        self.events.insert(0, f"🔬 Researched {bname}")
        return True

    # ── stations ─────────────────────────────────────────────────────────────
    def station_cost(self) -> int:
        idx = len(self.stations) - 1
        return STATION_COSTS[idx] if idx < len(STATION_COSTS) else STATION_COSTS[-1] * 3

    def add_station(self) -> tuple[bool, str]:
        cost = self.station_cost()
        if self.credits < cost:
            return False, f"Needs {cost:,} Cr"
        self.credits -= cost
        names = ["Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta","Iota","Kappa"]
        n = len(self.stations)
        name = names[n - 1] if n - 1 < len(names) else f"Station {n + 1}"
        self.stations.append(Station(name))
        return True, name

    def upgrade_station(self, idx: int) -> tuple[bool, str]:
        st = self.stations[idx]
        if st.upgrade_level >= len(SLOT_UPGRADES):
            return False, "Max upgrades reached"
        cost, extra = SLOT_UPGRADES[st.upgrade_level]
        if self.credits < cost:
            return False, f"Needs {cost:,} Cr"
        self.credits -= cost
        st.slots += extra
        st.upgrade_level += 1
        return True, f"+{extra} slots"

    # ── save / load ──────────────────────────────────────────────────────────
    def save(self):
        d = {"credits": self.credits,
             "unlocked": list(self.unlocked),
             "stations": [s.to_dict() for s in self.stations]}
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)

    @classmethod
    def load(cls) -> "GameState":
        gs = cls()
        if not os.path.exists(SAVE_PATH):
            return gs
        try:
            with open(SAVE_PATH, encoding="utf-8") as f:
                d = json.load(f)
            gs.credits  = d.get("credits", STARTING_CR)
            gs.unlocked = set(d.get("unlocked", list(UNLOCKED_START)))
            gs.stations = [Station.from_dict(s) for s in d.get("stations", [])] \
                          or [Station("Alpha")]
        except Exception:
            pass
        return gs

# ════════════════════════════════════════════════════════════════════════════════
# UI helpers
# ════════════════════════════════════════════════════════════════════════════════
def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=10, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
           x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
           x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return canvas.create_polygon(pts, smooth=True, **kw)

# ════════════════════════════════════════════════════════════════════════════════
# Main application
# ════════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    # slot grid geometry
    SLOT_W   = 165
    SLOT_H   = 132
    SLOT_PAD = 9
    COLS     = 5

    def __init__(self):
        super().__init__()
        self.gs          = GameState.load()
        self.cur_station = 0
        self.cur_tab     = "station"   # "station" | "research"

        # drag state
        self._drag_btype:    str | None       = None
        self._drag_ghost:    tk.Widget | None = None
        self._drag_moved:    bool             = False
        self._drag_start_xy: tuple[int,int]   = (0, 0)

        self.title(f"Space Station Idle  v{VERSION}")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("1280x760")
        self._build_ui()
        # global drag handlers — always active, guarded by _drag_btype check
        self.bind_all("<Motion>",          self._on_drag_motion)
        self.bind_all("<ButtonRelease-1>", self._on_drag_release)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_tick()

    # ── UI skeleton ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg="#0d1528", height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🚀  Space Station Idle", bg="#0d1528",
                 fg=TEXT, font=("Segoe UI", 13, "bold")).pack(side="left", padx=16, pady=6)
        self._credits_lbl = tk.Label(hdr, text="", bg="#0d1528",
                                      fg=YELLOW, font=("Segoe UI", 12, "bold"))
        self._credits_lbl.pack(side="right", padx=16)
        tk.Label(hdr, text=f"v{VERSION}", bg="#0d1528",
                 fg=TEXT_DIM, font=("Segoe UI", 9)).pack(side="right", padx=4)

        # ── Tab bar ──
        self._tabbar = tk.Frame(self, bg=BG2, height=34)
        self._tabbar.pack(fill="x")
        self._tabbar.pack_propagate(False)

        # ── Content ──
        self._content = tk.Frame(self, bg=BG)
        self._content.pack(fill="both", expand=True)

        # ── Event log ──
        log = tk.Frame(self, bg="#090d18", height=52)
        log.pack(fill="x", side="bottom")
        log.pack_propagate(False)
        tk.Label(log, text="Events:", bg="#090d18", fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side="left", padx=10, pady=4, anchor="n")
        self._log_lbl = tk.Label(log, text="", bg="#090d18", fg=TEXT,
                                  font=("Segoe UI", 8), anchor="w", justify="left",
                                  wraplength=1100)
        self._log_lbl.pack(side="left", padx=4, fill="both", expand=True)

        self._refresh_tabs()
        self._show_content()

    # ── tabs ─────────────────────────────────────────────────────────────────
    def _refresh_tabs(self):
        for w in self._tabbar.winfo_children():
            w.destroy()

        def _tab(text, key, cmd):
            active = (key == f"s{self.cur_station}" and self.cur_tab == "station") \
                     or (key == "research" and self.cur_tab == "research")
            f = tk.Frame(self._tabbar,
                         bg=ACCENT if active else BG2,
                         cursor="hand2", padx=14, pady=5)
            f.pack(side="left", padx=1)
            tk.Label(f, text=text,
                     bg=ACCENT if active else BG2,
                     fg="white" if active else TEXT_DIM,
                     font=("Segoe UI", 9, "bold" if active else "normal")).pack()
            f.bind("<Button-1>", lambda e: cmd())
            for c in f.winfo_children():
                c.bind("<Button-1>", lambda e: cmd())

        for i, st in enumerate(self.gs.stations):
            _tab(f"📡 {st.name}", f"s{i}", lambda idx=i: self._switch_station(idx))

        # add station button
        cost = self.gs.station_cost()
        add = tk.Frame(self._tabbar, bg=BG2, cursor="hand2", padx=10, pady=5)
        add.pack(side="left", padx=1)
        tk.Label(add, text=f"＋ Station ({cost:,} Cr)",
                 bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 9)).pack()
        add.bind("<Button-1>", lambda e: self._buy_station())
        for c in add.winfo_children():
            c.bind("<Button-1>", lambda e: self._buy_station())

        # research tab (right)
        _tab("🔬 Research", "research", self._switch_research)

    def _switch_station(self, idx: int):
        self.cur_station = idx
        self.cur_tab     = "station"
        self._refresh_tabs()
        self._show_content()

    def _switch_research(self):
        self.cur_tab = "research"
        self._refresh_tabs()
        self._show_content()

    def _buy_station(self):
        ok, msg = self.gs.add_station()
        if not ok:
            messagebox.showinfo("Cannot build station", msg)
            return
        self._switch_station(len(self.gs.stations) - 1)

    def _show_content(self):
        for w in self._content.winfo_children():
            w.destroy()
        self._update_credits()
        if self.cur_tab == "station":
            self._build_station_view()
        else:
            self._build_research_view()

    # ── station view ─────────────────────────────────────────────────────────
    def _build_station_view(self):
        st = self.gs.stations[self.cur_station]

        # left: slot canvas
        left = tk.Frame(self._content, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # station header row
        top = tk.Frame(left, bg=BG)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text=f"📡  {st.name}  —  {len(st.instances)}/{st.slots} slots",
                 bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left")
        if st.upgrade_level < len(SLOT_UPGRADES):
            cost, extra = SLOT_UPGRADES[st.upgrade_level]
            tk.Button(top, text=f"⬆ Upgrade  +{extra} slots  ({cost:,} Cr)",
                      bg=BG2, fg=YELLOW, relief="flat", bd=0,
                      activebackground=CARD_BG, activeforeground=YELLOW,
                      cursor="hand2", padx=8, pady=3,
                      command=lambda: self._do_upgrade()).pack(side="left", padx=14)

        # canvas
        rows    = -(-st.slots // self.COLS)   # ceiling division
        cw      = self.COLS * (self.SLOT_W + self.SLOT_PAD) + self.SLOT_PAD
        ch      = rows      * (self.SLOT_H + self.SLOT_PAD) + self.SLOT_PAD
        self._canvas = tk.Canvas(left, width=cw, height=ch,
                                  bg=BG, highlightthickness=0)
        self._canvas.pack()
        self._draw_slots()

        # right: shop
        right = tk.Frame(self._content, bg=BG2, width=245)
        right.pack(side="right", fill="y", padx=(0, 8), pady=8)
        right.pack_propagate(False)
        self._build_shop(right)

    # ── slot canvas ───────────────────────────────────────────────────────────
    def _slot_xy(self, slot_idx: int) -> tuple[int, int]:
        col = slot_idx % self.COLS
        row = slot_idx // self.COLS
        x   = self.SLOT_PAD + col * (self.SLOT_W + self.SLOT_PAD)
        y   = self.SLOT_PAD + row * (self.SLOT_H + self.SLOT_PAD)
        return x, y

    def _draw_slots(self):
        c  = self._canvas
        c.delete("all")
        st = self.gs.stations[self.cur_station]
        for idx in range(st.slots):
            x, y = self._slot_xy(idx)
            if idx in st.instances:
                self._draw_card(c, st.instances[idx], x, y)
            else:
                self._draw_empty(c, idx, x, y)

    def _draw_empty(self, c: tk.Canvas, idx: int, x: int, y: int):
        _round_rect(c, x, y, x+self.SLOT_W, y+self.SLOT_H, r=10,
                    fill=BG2, outline=BORDER, width=1)
        mx, my = x + self.SLOT_W//2, y + self.SLOT_H//2
        c.create_text(mx, my-10, text="＋", fill=BORDER,
                       font=("Segoe UI", 18), anchor="center")
        c.create_text(mx, my+12, text=f"Slot {idx+1}", fill=BORDER,
                       font=("Segoe UI", 8), anchor="center")
        tag = f"es_{idx}"
        c.create_rectangle(x, y, x+self.SLOT_W, y+self.SLOT_H,
                            fill="", outline="", tags=tag)
        c.tag_bind(tag, "<Button-1>",
                    lambda e, s=idx: self._on_empty_slot_click(s))

    def _draw_card(self, c: tk.Canvas, inst: BuildingInstance, x: int, y: int):
        col  = inst.mat_color()
        x2   = x + self.SLOT_W
        y2   = y + self.SLOT_H
        _round_rect(c, x, y, x2, y2, r=10,
                    fill=CARD_BG, outline=col, width=2)

        # Name row
        c.create_text(x+10, y+16, anchor="w",
                       text=f"{inst.mat_emoji()}  {inst.btype}",
                       fill=col, font=("Segoe UI", 9, "bold"))

        # Resource + count
        res = inst.output_resource()
        amt = inst.storage_amount()
        cap = inst.cap()
        c.create_text(x+10, y+35, anchor="w",
                       text=f"{res}: {amt:,} / {cap}",
                       fill=TEXT_DIM, font=("Segoe UI", 8))

        # Storage bar
        bx, by = x+10, y+48
        bw, bh = self.SLOT_W - 20, 8
        _round_rect(c, bx, by, bx+bw, by+bh, r=4, fill=BG, outline=BORDER)
        if amt > 0:
            fw = max(8, int(bw * min(amt, cap) / cap))
            _round_rect(c, bx, by, bx+fw, by+bh, r=4, fill=col, outline="")

        # Value
        val = inst.storage_value()
        c.create_text(x+10, y+65, anchor="w",
                       text=f"Value: {val:,} Cr" if val else "—",
                       fill=YELLOW if val else TEXT_DIM, font=("Segoe UI", 8))

        # Processing building: show needed inputs
        b = BUILDINGS[inst.btype]
        if not b["extraction"] and b["inputs"]:
            inp_txt = "  +  ".join(f"{INPUT_RATIO}× {i}" for i in b["inputs"])
            c.create_text(x+10, y+80, anchor="w",
                           text=inp_txt, fill=TEXT_DIM, font=("Segoe UI", 7))

        # Sell button
        sx, sy, sw, sh = x+8, y+self.SLOT_H-34, 72, 22
        tag_s = f"sell_{inst.id}"
        _round_rect(c, sx, sy, sx+sw, sy+sh, r=5,
                    fill="#14532d", outline=GREEN, tags=tag_s)
        c.create_text(sx+sw//2, sy+sh//2, text="Sell", fill=GREEN,
                       font=("Segoe UI", 8, "bold"), tags=tag_s)
        c.tag_bind(tag_s, "<Button-1>",
                    lambda e, si=self.cur_station, sl=inst.slot: self._sell(si, sl))
        c.tag_bind(tag_s, "<Enter>",
                    lambda e, t=tag_s: c.itemconfig(t, fill="#166534"))
        c.tag_bind(tag_s, "<Leave>",
                    lambda e, t=tag_s: c.itemconfig(t, fill="#14532d"))

        # Remove ×
        tag_r = f"rm_{inst.id}"
        c.create_text(x2-10, y+12, anchor="center", text="×",
                       fill=TEXT_DIM, font=("Segoe UI", 11, "bold"), tags=tag_r)
        c.tag_bind(tag_r, "<Button-1>",
                    lambda e, si=self.cur_station, sl=inst.slot: self._remove(si, sl))
        c.tag_bind(tag_r, "<Enter>",
                    lambda e, t=tag_r: c.itemconfig(t, fill=RED))
        c.tag_bind(tag_r, "<Leave>",
                    lambda e, t=tag_r: c.itemconfig(t, fill=TEXT_DIM))

    # ── shop panel ───────────────────────────────────────────────────────────
    def _build_shop(self, parent: tk.Frame):
        tk.Label(parent, text="Shop", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(10,2), padx=10, anchor="w")
        tk.Label(parent, text="Drag to slot or click to select",
                 bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 7)).pack(padx=10, anchor="w")

        sb   = tk.Scrollbar(parent, orient="vertical")
        sb.pack(side="right", fill="y")
        sc   = tk.Canvas(parent, bg=BG2, highlightthickness=0, yscrollcommand=sb.set)
        sc.pack(side="left", fill="both", expand=True)
        sb.config(command=sc.yview)
        inner = tk.Frame(sc, bg=BG2)
        sc.create_window((0, 0), window=inner, anchor="nw")
        sc.bind("<MouseWheel>",
                 lambda e: sc.yview_scroll(-1*(e.delta//120), "units"))

        self._selected_btype: str | None = None
        self._shop_items: dict[str, tk.Frame] = {}

        for bname in BUILDING_ORDER:
            if bname not in self.gs.unlocked:
                continue
            self._add_shop_item(inner, bname)

        inner.update_idletasks()
        sc.config(scrollregion=sc.bbox("all"))

    def _add_shop_item(self, parent: tk.Frame, bname: str):
        b     = BUILDINGS[bname]
        out   = b["output"]
        col   = MATERIALS[out]["color"]
        emoji = MATERIALS[out]["emoji"]
        cost  = b["credits"]
        afford= self.gs.credits >= cost

        item = tk.Frame(parent, bg=CARD_BG, padx=8, pady=5, cursor="hand2",
                         relief="flat", bd=0)
        item.pack(fill="x", pady=2, padx=5)
        self._shop_items[bname] = item

        row1 = tk.Frame(item, bg=CARD_BG)
        row1.pack(fill="x")
        tk.Label(row1, text=f"{emoji} {bname}", bg=CARD_BG, fg=col,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(row1, text=f"{cost:,} Cr", bg=CARD_BG,
                 fg=YELLOW if afford else RED,
                 font=("Segoe UI", 8)).pack(side="right")

        if b["inputs"]:
            tk.Label(item,
                     text="  +  ".join(f"{INPUT_RATIO}× {i}" for i in b["inputs"]),
                     bg=CARD_BG, fg=TEXT_DIM, font=("Segoe UI", 7)).pack(anchor="w")

        for w in [item, row1] + list(item.winfo_children()):
            w.bind("<ButtonPress-1>",
                    lambda e, bn=bname: self._drag_start(e, bn))

    # ── drag & drop ──────────────────────────────────────────────────────────
    def _drag_start(self, event: tk.Event, bname: str):
        if self.gs.credits < BUILDINGS[bname]["credits"]:
            return
        self._drag_btype    = bname
        self._drag_moved    = False
        self._drag_start_xy = (event.x_root, event.y_root)
        # ghost created lazily on first motion (avoids flicker on plain click)

    def _on_drag_motion(self, event: tk.Event):
        if not self._drag_btype:
            return
        dx = event.x_root - self._drag_start_xy[0]
        dy = event.y_root - self._drag_start_xy[1]
        if abs(dx) < 5 and abs(dy) < 5:
            return   # ignore tiny jitter
        if not self._drag_moved:
            self._drag_moved = True
            # create ghost now that we know it's a real drag
            bname = self._drag_btype
            out   = BUILDINGS[bname]["output"]
            self._drag_ghost = tk.Label(
                self,
                text=f"  {MATERIALS[out]['emoji']}  {bname}  ",
                bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                padx=6, pady=3, relief="raised")
        if self._drag_ghost:
            self._drag_ghost.place(
                x=event.x_root - self.winfo_rootx() - 60,
                y=event.y_root - self.winfo_rooty() - 14)

    def _on_drag_release(self, event: tk.Event):
        if not self._drag_btype:
            return
        btype = self._drag_btype
        moved = self._drag_moved
        self._end_drag()

        if not moved:
            # plain click on shop item → select for click-to-place
            self._selected_btype = btype
            return

        if self.cur_tab != "station" or not hasattr(self, "_canvas"):
            return

        cx   = self._canvas.winfo_rootx()
        cy   = self._canvas.winfo_rooty()
        slot = self._pixel_to_slot(event.x_root - cx, event.y_root - cy)
        if slot is not None:
            st = self.gs.stations[self.cur_station]
            if slot not in st.instances:
                self._place(btype, slot)

    def _end_drag(self):
        if self._drag_ghost:
            self._drag_ghost.destroy()
            self._drag_ghost = None
        self._drag_btype = None

    def _pixel_to_slot(self, px: int, py: int) -> int | None:
        st = self.gs.stations[self.cur_station]
        for idx in range(st.slots):
            x, y = self._slot_xy(idx)
            if x <= px <= x + self.SLOT_W and y <= py <= y + self.SLOT_H:
                return idx
        return None

    def _on_empty_slot_click(self, slot: int):
        if self._selected_btype:
            self._place(self._selected_btype, slot)

    # ── actions ───────────────────────────────────────────────────────────────
    def _place(self, btype: str, slot: int):
        ok, result = self.gs.buy_and_place(btype, self.cur_station, slot)
        if not ok:
            messagebox.showinfo("Cannot place", result)
        self._selected_btype = None
        self._update_credits()
        self._draw_slots()

    def _sell(self, station_idx: int, slot: int):
        val = self.gs.sell_instance(station_idx, slot)
        if val > 0:
            self.gs.events.insert(0, f"💰 Sold {val:,} Cr")
        self._update_credits()
        self._draw_slots()
        self._update_log()

    def _remove(self, station_idx: int, slot: int):
        self.gs.remove_building(station_idx, slot)
        self._draw_slots()

    def _do_upgrade(self):
        ok, msg = self.gs.upgrade_station(self.cur_station)
        if not ok:
            messagebox.showinfo("Cannot upgrade", msg)
        self._show_content()

    # ── research view ─────────────────────────────────────────────────────────
    def _build_research_view(self):
        outer = tk.Frame(self._content, bg=BG)
        outer.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(outer, text="🔬  Research", bg=BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(outer, text="Unlock building types in order. Unlocked buildings appear in the Shop.",
                 bg=BG, fg=TEXT_DIM, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        sb  = tk.Scrollbar(outer)
        sb.pack(side="right", fill="y")
        rc  = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=sb.set)
        rc.pack(side="left", fill="both", expand=True)
        sb.config(command=rc.yview)
        inner = tk.Frame(rc, bg=BG)
        rc.create_window((0, 0), window=inner, anchor="nw")
        rc.bind("<MouseWheel>",
                 lambda e: rc.yview_scroll(-1*(e.delta//120), "units"))

        RCOLS = 4
        col = row = 0
        for bname in BUILDING_ORDER:
            b = BUILDINGS[bname]
            if b["extraction"]:
                continue  # always unlocked, skip

            prereqs     = research_prereqs(bname)
            prereqs_met = all(p in self.gs.unlocked for p in prereqs)
            already     = bname in self.gs.unlocked
            cost        = research_cost(bname)
            can_pay     = self.gs.credits >= cost
            out         = b["output"]
            col_c       = MATERIALS[out]["color"]
            emoji       = MATERIALS[out]["emoji"]

            if already:
                bg_c, border, state_fg = "#0d2d1a", GREEN, GREEN
                state_txt = "✓ Unlocked"
            elif prereqs_met:
                bg_c, border = CARD_BG, ACCENT
                state_fg  = YELLOW if can_pay else RED
                state_txt = f"{cost:,} Cr"
            else:
                bg_c, border, state_fg = BG2, BORDER, TEXT_DIM
                state_txt = "🔒 Locked"

            card = tk.Frame(inner, bg=bg_c, padx=10, pady=8,
                             highlightbackground=border, highlightthickness=1)
            card.grid(row=row, column=col, padx=6, pady=5, sticky="nsew")
            inner.columnconfigure(col, weight=1)

            tk.Label(card, text=f"{emoji} {bname}", bg=bg_c, fg=col_c,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(card, text=f"→ {out}", bg=bg_c, fg=TEXT_DIM,
                     font=("Segoe UI", 8)).pack(anchor="w")
            if prereqs:
                tk.Label(card, text=f"Needs: {', '.join(prereqs)}", bg=bg_c, fg=TEXT_DIM,
                         font=("Segoe UI", 7)).pack(anchor="w")
            tk.Label(card, text=state_txt, bg=bg_c, fg=state_fg,
                     font=("Segoe UI", 8, "bold")).pack(anchor="e", pady=(4, 0))

            if prereqs_met and not already:
                card.configure(cursor="hand2")
                def _handler(e, bn=bname):
                    if self.gs.do_research(bn):
                        self._update_credits()
                        self._build_research_view()
                    else:
                        messagebox.showinfo("Cannot research",
                                            f"Not enough credits ({research_cost(bn):,} Cr needed)")
                for w in [card] + list(card.winfo_children()):
                    w.bind("<Button-1>", _handler)

            col += 1
            if col >= RCOLS:
                col = 0; row += 1

        inner.update_idletasks()
        rc.config(scrollregion=rc.bbox("all"))

    # ── tick & display ────────────────────────────────────────────────────────
    def _schedule_tick(self):
        self.after(int(INTERVAL * 1000), self._tick)

    def _tick(self):
        self.gs.produce_tick()
        if self.cur_tab == "station" and hasattr(self, "_canvas"):
            self._draw_slots()
        self._update_credits()
        self._update_log()
        self._schedule_tick()

    def _update_credits(self):
        self._credits_lbl.config(text=f"💰  {self.gs.credits:,} Cr")

    def _update_log(self):
        self._log_lbl.config(text="   ·   ".join(self.gs.events[:10]))

    def _on_close(self):
        self.gs.save()
        self.destroy()


# ════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()
