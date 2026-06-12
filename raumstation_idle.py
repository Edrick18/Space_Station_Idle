# -*- coding: utf-8 -*-
"""Raumstation Idle — Idle/Incremental-Spiel mit Produktionsketten.

Läuft vollständig offline mit Python + tkinter.
Speichert automatisch in savegame.json (gleicher Ordner).
"""

import json
import math
import os
import random
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "savegame.json")

VERSION = "1.0.0"

# --- Auto-Update über GitHub (optional — schlägt leise fehl) ---
# Beim Start wird im Hintergrund geprüft, ob auf GitHub eine neuere Version
# liegt. Wenn ja, wird sie heruntergeladen und ist beim nächsten Start aktiv.
# Ohne Internet, ohne Update oder bei jedem Fehler läuft das Spiel einfach
# normal weiter — Updates sind nie Pflicht.
UPDATE_USER = "DEIN-GITHUB-BENUTZERNAME"
UPDATE_REPO = "raumstation-idle"
UPDATE_BRANCH = "main"

INTERVAL = 5.0              # Sekunden pro Produktionszyklus
OFFLINE_CAP = 24 * 3600     # Offline-Produktion maximal 24 Stunden
AUTOSAVE_SECONDS = 30.0
COST_GROWTH = 1.2           # Creditkosten steigen pro gekauftem Gebäude
FRAME_MS = 40               # ~25 FPS

RAWS = ["Eisenerz", "Kohle", "Kupfererz", "Siliziumsand", "Rohöl"]

# ----- Farben -----
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

# Akzentfarben pro Produktionskette
C_METALL = "#60a5fa"    # Eisen / Stahl
C_KOHLE = "#9ca3af"
C_KUPFER = "#fb923c"    # Kupfer / Kabel
C_SILIZIUM = "#4ade80"  # Silizium / Elektronik
C_OEL = "#facc15"       # Öl / Kunststoff
C_MECHANIK = "#a78bfa"
C_ROBOTIK = "#f472b6"

# Material: Emoji, Verkaufspreis, Position (x, y), Akzentfarbe
MATERIALS = {
    # Tier 0 — Rohstoffe
    "Eisenerz":         {"emoji": "🔩", "price": 1,    "pos": (150, 60),    "color": C_METALL},
    "Kohle":            {"emoji": "⚫", "price": 1,    "pos": (420, 60),    "color": C_KOHLE},
    "Kupfererz":        {"emoji": "🟠", "price": 1,    "pos": (690, 60),    "color": C_KUPFER},
    "Siliziumsand":     {"emoji": "🏜️", "price": 1,    "pos": (960, 60),    "color": C_SILIZIUM},
    "Rohöl":            {"emoji": "🛢️", "price": 1,    "pos": (1230, 60),   "color": C_OEL},
    # Tier 1 — erste Verarbeitung
    "Eisenbarren":      {"emoji": "🧱", "price": 2,    "pos": (150, 250),   "color": C_METALL},
    "Kupferbarren":     {"emoji": "🟧", "price": 2,    "pos": (690, 250),   "color": C_KUPFER},
    "Rohsilizium":      {"emoji": "💎", "price": 2,    "pos": (960, 250),   "color": C_SILIZIUM},
    "Kunststoff":       {"emoji": "🧪", "price": 2,    "pos": (1230, 250),  "color": C_OEL},
    # Tier 2
    "Stahlbarren":      {"emoji": "⚒️", "price": 6,    "pos": (280, 440),   "color": C_METALL},
    "Kupferdraht":      {"emoji": "🧵", "price": 6,    "pos": (690, 440),   "color": C_KUPFER},
    "Siliziumwafer":    {"emoji": "💿", "price": 8,    "pos": (960, 440),   "color": C_SILIZIUM},
    # Tier 3
    "Eisenplatte":      {"emoji": "🟫", "price": 16,   "pos": (150, 630),   "color": C_METALL},
    "Stahlblech":       {"emoji": "🪨", "price": 14,   "pos": (420, 630),   "color": C_METALL},
    "Kupferkabel":      {"emoji": "🪢", "price": 16,   "pos": (690, 630),   "color": C_KUPFER},
    "Mikrochip":        {"emoji": "🔲", "price": 28,   "pos": (960, 630),   "color": C_SILIZIUM},
    # Tier 4
    "Stahlträger":      {"emoji": "🏗️", "price": 60,   "pos": (280, 820),   "color": C_METALL},
    "Isoliertes Kabel": {"emoji": "🔌", "price": 36,   "pos": (690, 820),   "color": C_KUPFER},
    # Tier 5
    "Spule":            {"emoji": "🧲", "price": 76,   "pos": (500, 1010),  "color": C_KUPFER},
    "Platine":          {"emoji": "💻", "price": 128,  "pos": (830, 1010),  "color": C_SILIZIUM},
    # Tier 6
    "Maschinenrahmen":  {"emoji": "🛠️", "price": 272,  "pos": (420, 1200),  "color": C_MECHANIK},
    # Tier 7
    "Motor":            {"emoji": "⚙️", "price": 572,  "pos": (420, 1390),  "color": C_MECHANIK},
    # Tier 8
    "Basisroboter":     {"emoji": "🤖", "price": 1520, "pos": (650, 1580),  "color": C_ROBOTIK},
}

# Gebäude in Produktionsreihenfolge (Rohstoffe zuerst, damit Ketten
# innerhalb eines Zyklus sauber durchlaufen)
BUILDINGS = {
    # Extraktion
    "Eisenmine":     {"output": "Eisenerz",     "inputs": [], "credits": 50,  "materials": {}, "extraction": True},
    "Kohlemine":     {"output": "Kohle",        "inputs": [], "credits": 50,  "materials": {}, "extraction": True},
    "Kupfermine":    {"output": "Kupfererz",    "inputs": [], "credits": 60,  "materials": {}, "extraction": True},
    "Siliziumbruch": {"output": "Siliziumsand", "inputs": [], "credits": 60,  "materials": {}, "extraction": True},
    "Ölpumpe":       {"output": "Rohöl",        "inputs": [], "credits": 80,  "materials": {}, "extraction": True},
    # Erste Verarbeitung
    "Schmelzofen":    {"output": "Eisenbarren",  "inputs": ["Eisenerz"],     "credits": 100, "materials": {"Eisenerz": 50},     "extraction": False},
    "Kupferschmelze": {"output": "Kupferbarren", "inputs": ["Kupfererz"],    "credits": 100, "materials": {"Kupfererz": 50},    "extraction": False},
    "Siliziumofen":   {"output": "Rohsilizium",  "inputs": ["Siliziumsand"], "credits": 100, "materials": {"Siliziumsand": 50}, "extraction": False},
    "Raffinerie":     {"output": "Kunststoff",   "inputs": ["Rohöl"],        "credits": 120, "materials": {"Rohöl": 50},        "extraction": False},
    # Metallkette
    "Hochofen":  {"output": "Stahlbarren", "inputs": ["Eisenbarren", "Kohle"],        "credits": 300,  "materials": {"Eisenbarren": 30, "Kohle": 30},       "extraction": False},
    "Walzwerk":  {"output": "Eisenplatte", "inputs": ["Eisenbarren", "Stahlbarren"],  "credits": 600,  "materials": {"Eisenbarren": 30, "Stahlbarren": 20}, "extraction": False},
    "Stahlwerk": {"output": "Stahlblech",  "inputs": ["Stahlbarren", "Kohle"],        "credits": 500,  "materials": {"Stahlbarren": 25, "Kohle": 40},       "extraction": False},
    "Presswerk": {"output": "Stahlträger", "inputs": ["Stahlblech", "Eisenplatte"],   "credits": 1500, "materials": {"Stahlblech": 20, "Eisenplatte": 20},  "extraction": False},
    # Kabelkette
    "Drahtziehwerk": {"output": "Kupferdraht",      "inputs": ["Kupferbarren", "Kohle"],            "credits": 300,  "materials": {"Kupferbarren": 30, "Kohle": 30},        "extraction": False},
    "Kabelwerk":     {"output": "Kupferkabel",      "inputs": ["Kupferdraht", "Kupferbarren"],      "credits": 600,  "materials": {"Kupferdraht": 25, "Kupferbarren": 25},  "extraction": False},
    "Isolierwerk":   {"output": "Isoliertes Kabel", "inputs": ["Kupferkabel", "Kunststoff"],        "credits": 1200, "materials": {"Kupferkabel": 20, "Kunststoff": 30},    "extraction": False},
    "Spulenwerk":    {"output": "Spule",            "inputs": ["Isoliertes Kabel", "Eisenbarren"],  "credits": 2500, "materials": {"Isoliertes Kabel": 15, "Eisenbarren": 30}, "extraction": False},
    # Elektronikkette
    "Waferwerk":    {"output": "Siliziumwafer", "inputs": ["Rohsilizium", "Kupferbarren"],   "credits": 500,  "materials": {"Rohsilizium": 30, "Kupferbarren": 25},  "extraction": False},
    "Chipfabrik":   {"output": "Mikrochip",     "inputs": ["Siliziumwafer", "Kupferdraht"],  "credits": 1500, "materials": {"Siliziumwafer": 20, "Kupferdraht": 30}, "extraction": False},
    "Platinenwerk": {"output": "Platine",       "inputs": ["Mikrochip", "Isoliertes Kabel"], "credits": 4000, "materials": {"Mikrochip": 15, "Isoliertes Kabel": 15}, "extraction": False},
    # Mechanik
    "Maschinenwerk": {"output": "Maschinenrahmen", "inputs": ["Stahlträger", "Spule"],            "credits": 8000,  "materials": {"Stahlträger": 10, "Spule": 10},          "extraction": False},
    "Motorenfabrik": {"output": "Motor",           "inputs": ["Maschinenrahmen", "Stahlblech"],   "credits": 15000, "materials": {"Maschinenrahmen": 5, "Stahlblech": 20},  "extraction": False},
    # Robotik
    "Roboterwerk": {"output": "Basisroboter", "inputs": ["Motor", "Platine", "Stahlträger"], "credits": 40000, "materials": {"Motor": 5, "Platine": 5, "Stahlträger": 10}, "extraction": False},
}

BUILDING_ORDER = list(BUILDINGS.keys())

# Material -> Gebäude das es produziert
PRODUCER = {b["output"]: name for name, b in BUILDINGS.items()}
# Material -> Gebäude die es verbrauchen
CONSUMERS = {m: [] for m in MATERIALS}
for _name, _b in BUILDINGS.items():
    for _inp in _b["inputs"]:
        CONSUMERS[_inp].append(_name)

# Materialkosten für 2.+ Kauf eines Extraktionsgebäudes
EXTRACTION_MATERIAL_COST = 25

NODE_W = 235
NODE_H = 118


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------

def fmt(n):
    """Ganzzahl mit Punkt als Tausendertrennzeichen (deutsch)."""
    return f"{int(n):,}".replace(",", ".")


def fmt_rate(r):
    return f"{r:.1f}".replace(".", ",")


def blend(c1, c2, t):
    """Mischt zwei Hex-Farben: t=0 -> c1, t=1 -> c2."""
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
    """Abgerundetes Rechteck als geglättetes Polygon."""
    return canvas.create_polygon(round_rect_points(x1, y1, x2, y2, r),
                                 smooth=True, **kw)


def bezier_point(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]
    return x, y


def connection_curve(inp, out):
    """Bezier-Kontrollpunkte für die Linie von Input-Knoten zu Output-Knoten."""
    ix, iy = MATERIALS[inp]["pos"]
    ox, oy = MATERIALS[out]["pos"]
    p0 = (ix + NODE_W / 2, iy + NODE_H)
    p3 = (ox + NODE_W / 2, oy)
    p1 = (p0[0], p0[1] + 55)
    p2 = (p3[0], p3[1] - 55)
    return p0, p1, p2, p3


def version_tuple(s):
    """'1.2.3' -> (1, 2, 3) für Versionsvergleiche."""
    nums = re.findall(r"\d+", str(s))
    return tuple(int(n) for n in nums[:4]) if nums else (0,)


def check_for_update(result):
    """Prüft auf GitHub nach einer neueren Version und lädt sie herunter.

    Läuft in einem Hintergrund-Thread. Jeder Fehler (kein Internet,
    Repo nicht erreichbar, kaputter Download, ...) wird verschluckt —
    das Spiel läuft dann einfach mit der vorhandenen Version weiter.
    `result` wird befüllt mit:
      status: "unkonfiguriert" | "aktuell" | "installiert" | "offline"
      version: neue Versionsnummer (nur bei "installiert")
    """
    if "DEIN-GITHUB" in UPDATE_USER:
        result["status"] = "unkonfiguriert"
        return
    import urllib.request
    base = (f"https://raw.githubusercontent.com/"
            f"{UPDATE_USER}/{UPDATE_REPO}/{UPDATE_BRANCH}/")
    try:
        with urllib.request.urlopen(base + "version.json", timeout=6) as r:
            info = json.loads(r.read().decode("utf-8"))
        remote = str(info.get("version", "0"))
        if version_tuple(remote) <= version_tuple(VERSION):
            result["status"] = "aktuell"
            return

        with urllib.request.urlopen(base + "raumstation_idle.py", timeout=20) as r:
            code = r.read()
        text = code.decode("utf-8")
        # Plausibilitätsprüfung, damit nie eine kaputte Datei installiert wird
        if "class Game" not in text or "VERSION" not in text or len(text) < 5000:
            result["status"] = "offline"
            return

        target = os.path.join(BASE_DIR, "raumstation_idle.py")
        tmp = target + ".new"
        with open(tmp, "wb") as f:
            f.write(code)
        os.replace(tmp, target)
        result["version"] = remote
        result["status"] = "installiert"
    except Exception:
        result["status"] = "offline"


def add_nebula(canvas, cx, cy, rx, ry, color):
    """Weicher Nebelfleck aus gestaffelten, gestippelten Ovalen."""
    for scale, stipple in ((1.0, "gray12"), (0.7, "gray12"), (0.45, "gray25")):
        canvas.create_oval(cx - rx * scale, cy - ry * scale,
                           cx + rx * scale, cy + ry * scale,
                           fill=color, outline="", stipple=stipple, tags="static")


# ----------------------------------------------------------------------
# Spiellogik
# ----------------------------------------------------------------------

class Game:
    """Spiellogik, unabhängig von der Oberfläche."""

    def __init__(self):
        self.credits = 0
        self.stock = {m: 0 for m in MATERIALS}
        self.produced_total = {m: 0 for m in MATERIALS}
        self.counts = {b: 0 for b in BUILDINGS}
        self.timers = {b: 0.0 for b in BUILDINGS}
        self.events = []  # (material, menge) — fertige Produktionen für Animationen
        # Startzustand: je 1x jedes Extraktionsgebäude
        for b, data in BUILDINGS.items():
            if data["extraction"]:
                self.counts[b] = 1

    # ----- Produktion -----

    def produce(self, bname):
        b = BUILDINGS[bname]
        n = self.counts[bname]
        if n <= 0:
            return
        p = n
        for m in b["inputs"]:
            p = min(p, self.stock[m])
        if p <= 0:
            return
        for m in b["inputs"]:
            self.stock[m] -= p
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

    # ----- Freischaltung / Sichtbarkeit -----

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

    # ----- Kaufen / Verkaufen -----

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

    # ----- Produktions-/Verbrauchsraten (theoretisch) -----

    def rate_produced(self, mat):
        return self.counts[PRODUCER[mat]] / INTERVAL

    def rate_consumed(self, mat):
        return sum(self.counts[c] for c in CONSUMERS[mat]) / INTERVAL

    # ----- Speichern / Laden -----

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
        """Lädt den Spielstand. Gibt die Offline-Sekunden zurück (0 = neues Spiel)."""
        if not os.path.exists(SAVE_FILE):
            return 0
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return 0
        self.credits = data.get("credits", 0)
        for m in MATERIALS:
            self.stock[m] = data.get("stock", {}).get(m, 0)
            self.produced_total[m] = data.get("produced_total", {}).get(m, 0)
        for b in BUILDINGS:
            self.counts[b] = data.get("counts", {}).get(b, self.counts[b])
            self.timers[b] = data.get("timers", {}).get(b, 0.0)
        elapsed = max(0, time.time() - data.get("saved_at", time.time()))
        return elapsed


# ----------------------------------------------------------------------
# Oberfläche
# ----------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Raumstation Idle")
        self.geometry("1280x800")
        self.configure(bg=BG)

        self.game = Game()
        self.selected_mat = None
        self.running = False
        self.autosave_timer = 0.0
        self.node_rects = []        # (x1, y1, x2, y2, material)
        self.floats = []            # schwebende Texte
        self.flash = {}             # material -> Zeitpunkt des Produktions-Aufleuchtens
        self.unlock_anim = {}       # material -> Startzeit der Einblend-Animation
        self.seen_visible = None
        self.mouse_widget = None    # (x, y) Mausposition im Karten-Canvas
        self.hover_mat = None
        self.credits_shown = 0.0
        self.dt = 0.0
        self.shooting = []          # aktive Sternschnuppen
        self.next_shoot = 0.0

        # Seitenpanel-Zustand
        self.panel_visible = False
        self.panel_offset = PANEL_W   # 0 = offen, PANEL_W = ausgeblendet
        self.panel_anim = None        # laufende Slide-Animation
        self.panel_mouse = None
        self.panel_buttons = []     # (x1, y1, x2, y2, enabled, callback)

        # Update-Prüfung im Hintergrund — blockiert nie das Spiel
        self.update_info = {}
        self.update_note_shown = False
        threading.Thread(target=check_for_update,
                         args=(self.update_info,), daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_home()

    # ------------------------------------------------------------------
    # Startbildschirm (animiert)
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
            c.create_text(cx, 360, text="Raumstation Idle",
                          font=("Segoe UI", 38, "bold"), fill=TEXT_MAIN),
            c.create_text(cx, 410, text="Baue deine industrielle Produktionskette im All auf",
                          font=("Segoe UI", 13), fill=TEXT_DIM),
        ]
        c.create_text(cx, 760, text=f"v{VERSION}  •  Automatisches Speichern  •  Offline-Produktion  •  Updates optional",
                      font=("Segoe UI", 10), fill=blend(TEXT_DIM, BG, 0.35), tags="footer")

        # Start-Button (Canvas-Elemente mit Glow-Ring)
        bw, bh, by = 220, 58, 500
        self.home_glow = round_rect(c, cx - bw / 2 - 4, by - 4, cx + bw / 2 + 4, by + bh + 4,
                                    16, fill="", outline="#2563eb", width=2)
        self.home_btn = round_rect(c, cx - bw / 2, by, cx + bw / 2, by + bh,
                                   14, fill="#2563eb", outline="", tags="startbtn")
        self.home_btn_text = c.create_text(cx, by + bh / 2, text="Starten",
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

        # Titel schwebt sanft
        dy = math.sin(t * 1.4) * 6
        base_ys = (270, 360, 410)
        for item, by in zip(self.home_title, base_ys):
            c.coords(item, 640, by + dy)

        # Satellit umkreist die Rakete
        ang = t * 1.1
        c.coords(self.home_sat, 640 + 150 * math.cos(ang),
                 270 + dy + 45 * math.sin(ang))

        # Button-Glow pulsiert
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        c.itemconfig(self.home_glow, outline=blend("#1e3a6e", "#60a5fa", pulse))

        # Sternschnuppen
        c.delete("shoot")
        if now >= self.home_next_shoot:
            self.home_next_shoot = now + random.uniform(3, 9)
            self.home_shoot.append(self._new_shooting_star(w, h, now))
        self.home_shoot = [s for s in self.home_shoot
                           if self._draw_shooting_star(c, s, now, "shoot")]

        self.after(FRAME_MS, self.home_loop)

    # ----- Sternschnuppen (für Home und Karte) -----

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
    # Spielstart
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
                lines = [f"  {MATERIALS[m]['emoji']} {m}: +{fmt(v)}" for m, v in top]
                hours = min(elapsed, OFFLINE_CAP) / 3600
                messagebox.showinfo(
                    "Willkommen zurück!",
                    f"Deine Station hat {fmt_rate(hours)} Stunden weitergearbeitet:\n\n"
                    + "\n".join(lines), parent=self)

        self.credits_shown = float(self.game.credits)
        self.loop()

    # ------------------------------------------------------------------
    # Spiel-Oberfläche
    # ------------------------------------------------------------------

    def build_game_ui(self):
        # Kopfleiste als Canvas (für Credits-Pill)
        hd = tk.Canvas(self, height=50, bg=HEADER_BG, highlightthickness=0)
        hd.pack(fill="x")
        self.header = hd
        hd.create_text(16, 25, anchor="w", text="🚀 Raumstation Idle",
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
            text="Linksklick: Material öffnen   |   Rechtsklick + Ziehen: Karte verschieben",
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
        """Nebel + Sternenhintergrund — einmal erzeugt, twinkelt pro Frame."""
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
    # Seitenpanel — komplett Canvas-gezeichnet, gleitet von rechts herein
    # ------------------------------------------------------------------

    def build_panel(self, parent):
        p = tk.Canvas(parent, bg=PANEL_BG, width=PANEL_W, highlightthickness=0)
        self.panel = p
        # Eingabefeld als eingebettetes Widget (bleibt dauerhaft bestehen)
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
        """Startet das Hinein-/Hinausgleiten des Panels (eigene schnelle Schleife)."""
        if self.panel_anim is None and self.panel_offset == to and \
                self.panel_visible == (to == 0):
            return
        if not self.panel_visible:
            self.panel_visible = True
            self.panel.place(relx=1.0, rely=0, relheight=1.0, anchor="ne",
                             x=round(self.panel_offset))
            tk.Misc.tkraise(self.panel)  # Canvas.lift() würde Canvas-Items meinen
        anim = {"from": self.panel_offset, "to": to, "t0": time.monotonic()}
        self.panel_anim = anim
        self._panel_anim_step(anim)

    def _panel_anim_step(self, anim):
        if self.panel_anim is not anim:
            return  # von einer neueren Animation abgelöst
        duration = 0.3
        prog = (time.monotonic() - anim["t0"]) / duration
        eased = ease_out(prog)
        self.panel_offset = anim["from"] + (anim["to"] - anim["from"]) * eased
        self.panel.place_configure(x=round(self.panel_offset))
        if prog >= 1.0:
            self.panel_offset = anim["to"]
            self.panel_anim = None
            if anim["to"] >= PANEL_W:  # vollständig hinausgeglitten
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

        # Hintergrund-Akzente
        p.create_rectangle(ox, 0, ox + PANEL_W, 4, fill=accent, outline="", tags="dyn")
        p.create_line(ox, 0, ox, ph, fill="#22315c", width=2, tags="dyn")

        # Kopf: Badge + Name + Schließen
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

        # --- Lager-Karte ---
        p.create_polygon(round_rect_points(ox + 14, 64, ox + 306, 148, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline=blend(accent, PANEL_BG, 0.6), tags="dyn")
        p.create_text(ox + 28, 82, anchor="w", text="LAGER",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.create_text(ox + 28, 106, anchor="w", text=fmt(g.stock[mat]),
                      font=("Segoe UI", 19, "bold"), fill=TEXT_MAIN, tags="dyn")
        p.create_text(ox + 28, 132, anchor="w",
                      text=f"Wert: {fmt(info['price'])} Cr/Stück",
                      font=("Segoe UI", 9), fill=GOLD, tags="dyn")
        prod = g.rate_produced(mat)
        cons = g.rate_consumed(mat)
        p.create_text(ox + 292, 98, anchor="e", text=f"+{fmt_rate(prod)}/s",
                      font=("Segoe UI", 9), fill=GREEN, tags="dyn")
        p.create_text(ox + 292, 114, anchor="e", text=f"-{fmt_rate(cons)}/s",
                      font=("Segoe UI", 9),
                      fill=RED if cons > 0 else blend(TEXT_DIM, PANEL_BG, 0.4),
                      tags="dyn")

        # --- Verkaufen-Karte ---
        p.create_polygon(round_rect_points(ox + 14, 160, ox + 306, 268, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline="#22315c", tags="dyn")
        p.create_text(ox + 28, 178, anchor="w", text="VERKAUFEN",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.coords(self.panel_entry_win, ox + 28, 192)
        p.itemconfigure(self.panel_entry_win, state="normal")
        hover_any |= self.panel_button(ox + 124, 192, ox + 292, 220, "Verkaufen",
                                       self.sell_amount, "#2563eb", "#3b82f6")
        third = (292 - 28 - 12) / 3
        for i, (label, cb) in enumerate((
                ("10", lambda: self._sell_feedback(g.sell(mat, 10))),
                ("Hälfte", lambda: self._sell_feedback(g.sell(mat, g.stock[mat] // 2))),
                ("Alles", lambda: self._sell_feedback(g.sell(mat, g.stock[mat]))))):
            bx1 = ox + 28 + i * (third + 6)
            hover_any |= self.panel_button(bx1, 230, bx1 + third, 256, label, cb,
                                           "#1d2a4d", "#27395f",
                                           font=("Segoe UI", 9, "bold"))

        # --- Gebäude-Karte ---
        credits_cost, mats = g.cost_of(bname)
        n_lines = 1 + len(mats)
        cost_y0 = 372
        btn_y = cost_y0 + n_lines * 19 + 10
        card_y2 = btn_y + 36 + 14
        p.create_polygon(round_rect_points(ox + 14, 280, ox + 306, card_y2, 12),
                         smooth=True, fill=PANEL_CARD,
                         outline="#22315c", tags="dyn")
        p.create_text(ox + 28, 298, anchor="w", text="GEBÄUDE",
                      font=("Segoe UI", 8, "bold"),
                      fill=blend(TEXT_DIM, PANEL_BG, 0.2), tags="dyn")
        p.create_text(ox + 28, 320, anchor="w", text=bname,
                      font=("Segoe UI", 12, "bold"), fill=accent, tags="dyn")
        p.create_text(ox + 292, 320, anchor="e", text=f"{g.counts[bname]}×",
                      font=("Segoe UI", 12, "bold"), fill=TEXT_MAIN, tags="dyn")
        p.create_text(ox + 28, 340, anchor="w",
                      text=f"Produziert 1 {mat} alle {fmt_rate(INTERVAL)}s",
                      font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")
        p.create_text(ox + 28, 360, anchor="w", text="KOSTEN",
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
                                       "Kaufen", self.buy, "#16a34a", "#22c55e",
                                       enabled=affordable,
                                       font=("Segoe UI", 11, "bold"))

        p.config(cursor="hand2" if hover_any else "")

    # ----- Eingaben (Karte) -----

    def on_mouse_move(self, event):
        self.mouse_widget = (event.x, event.y)

    def on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for x1, y1, x2, y2, mat in self.node_rects:
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.select_mat(mat)
                return
        self.close_panel()  # Klick ins Leere schließt das Panel

    def select_mat(self, mat):
        self.selected_mat = mat
        self.sell_entry.delete(0, "end")
        self._start_panel_anim(0)

    def close_panel(self):
        if self.panel_visible:
            self._start_panel_anim(PANEL_W)

    # ----- Aktionen -----

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
            self.spawn_float(x + NODE_W / 2, y + 14, "+1 Gebäude",
                             MATERIALS[self.selected_mat]["color"])
            self.flash[self.selected_mat] = time.monotonic()

    # ------------------------------------------------------------------
    # Hauptschleife
    # ------------------------------------------------------------------

    def loop(self):
        if not self.running:
            return
        now = time.monotonic()
        self.dt = now - self.last_time
        self.last_time = now

        self.game.tick(self.dt)

        self.autosave_timer += self.dt
        if self.autosave_timer >= AUTOSAVE_SECONDS:
            self.autosave_timer = 0.0
            self.game.save()

        self.draw()
        self.after(FRAME_MS, self.loop)

    # ------------------------------------------------------------------
    # Zeichnen
    # ------------------------------------------------------------------

    def draw(self):
        g = self.game
        c = self.canvas
        t = time.monotonic()
        c.delete("dyn")
        self.node_rects = []

        # Credits zählen weich hoch/runter
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

        # Hinweis sobald ein Update fertig heruntergeladen wurde
        if not self.update_note_shown and \
                self.update_info.get("status") == "installiert":
            self.update_note_shown = True
            hd.itemconfig(self.header_update,
                          text=f"⬆ Update v{self.update_info.get('version')} "
                               f"geladen — aktiv nach Neustart")

        # Sterne twinkeln
        for s in self.stars:
            b = s["base"] * (0.55 + 0.45 * math.sin(t * s["speed"] + s["phase"]))
            c.itemconfig(s["item"], fill=blend(BG, "#bcd0f0", b))

        # Sichtbarer Kartenausschnitt (für Culling)
        vw = c.winfo_width()
        vh = c.winfo_height()
        vx1, vy1 = c.canvasx(0) - 60, c.canvasy(0) - 60
        vx2, vy2 = c.canvasx(vw) + 60, c.canvasy(vh) + 60

        visible = {m for m in MATERIALS if g.material_visible(m)}

        # Neu freigeschaltete Knoten -> Einblend-Animation
        if self.seen_visible is None:
            self.seen_visible = set(visible)
        else:
            for mat in visible - self.seen_visible:
                self.unlock_anim[mat] = t
            self.seen_visible = set(visible)

        # Hover ermitteln
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

        # Verbindungslinien (Glow + Pfeilspitze) + Material-Punkte mit Schweif
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
                # Punkt mit Schweif wandert im Takt des Produktionszyklus
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

        # Knoten (nur im sichtbaren Ausschnitt zeichnen)
        for mat in visible:
            x, y = MATERIALS[mat]["pos"]
            if x + NODE_W < vx1 or x > vx2 or y + NODE_H < vy1 or y > vy2:
                continue
            self.draw_node(mat, t)

        # Produktions-Ereignisse -> schwebende "+n"-Texte + Aufleuchten
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

        # Sternschnuppen über der Karte
        if self.next_shoot == 0.0:
            self.next_shoot = t + random.uniform(5, 14)
        if t >= self.next_shoot:
            self.next_shoot = t + random.uniform(5, 14)
            self.shooting.append(self._new_shooting_star(vw, vh, t, vx1 + 60, vy1 + 60))
        self.shooting = [s for s in self.shooting
                         if self._draw_shooting_star(c, s, t, "dyn")]

        # Panel schließen falls das Material nicht mehr sichtbar ist
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

        # Einblend-Animation: Karte wächst aus der Mitte
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

        # Aufleuchten bei fertiger Produktion
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
        # dezenter Lichtschein an der Oberkante
        c.create_line(x1 + 14, y1 + 2, x2 - 14, y1 + 2,
                      fill=blend(fill, "#ffffff", 0.12), tags="dyn")
        self.node_rects.append((x, y, x + NODE_W, y + NODE_H, mat))

        if s < 0.92:
            return  # Inhalt erst zeigen, wenn die Karte fast voll aufgeklappt ist

        # Icon-Badge
        bx, by, br = x + 27, y + 26, 15
        c.create_oval(bx - br, by - br, bx + br, by + br,
                      fill=blend(accent, BG, 0.78),
                      outline=blend(accent, BG, 0.4), tags="dyn")
        c.create_text(bx, by, text=info["emoji"],
                      font=("Segoe UI Emoji", 12), tags="dyn")

        c.create_text(x + 50, y + 26, anchor="w", text=mat,
                      font=("Segoe UI", 11, "bold"), fill=accent, tags="dyn")

        # Lagerbestand groß, Raten rechts gestapelt
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

        # Gebäudezeile + Restzeit
        c.create_text(x + 14, y + 81, anchor="w",
                      text=f"{g.counts[bname]}× {bname}",
                      font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")
        if g.counts[bname] > 0:
            rest = max(0.0, INTERVAL - g.timers[bname])
            c.create_text(x + NODE_W - 14, y + 81, anchor="e",
                          text=f"{fmt_rate(rest)}s",
                          font=("Segoe UI", 9), fill=TEXT_DIM, tags="dyn")

        # Fortschrittsbalken mit Leuchtpunkt an der Spitze
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
    # Beenden
    # ------------------------------------------------------------------

    def on_close(self):
        if self.running:
            self.game.save()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
