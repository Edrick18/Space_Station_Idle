# Raumstation Idle — Game Design Dokument

## Übersicht

Ein Idle/Incremental-Spiel mit dem Thema Raumstation. Der Spieler baut eine industrielle Produktionskette auf — beginnend mit einfachen Rohstoffen, die zu immer komplexeren Bauteilen verarbeitet werden. Das Spiel läuft vollständig offline, kein Internet erforderlich.

**Plattform:** Python + tkinter  
**Speichern:** Automatisch, Fortschritt bleibt beim Schließen erhalten  
**Offline-Produktion:** Ja — Zeit wird beim Laden berechnet, Gebäude produzieren auch wenn das Spiel geschlossen ist

---

## Kernmechaniken

### Währung
- **Credits** = einzige Hauptwährung
- Credits werden durch **manuellen Verkauf** von Materialien verdient
- Gebäude kosten Credits **und** Materialien

### Keine Stromverwaltung
Strom existiert nicht als separate Mechanik. Der Fokus liegt ausschließlich auf den Materialketten und der Produktionsbalancierung.

### Skalierung statt Upgrades
- Gebäude können **nicht** geupgradet werden (vermeidet Loopholes / Ressourcen aus dem Nichts)
- Mehr Output = mehr Gebäude kaufen = mehr Materialien benötigen
- Der Spielspaß liegt im **Skalieren und Balancieren** der Produktion

---

## Freischaltungssystem

Neue Gebäude werden erst sichtbar und kaufbar wenn:
1. Das Vorgänger-Gebäude bereits gebaut wurde
2. Der benötigte Rohstoff bereits produziert wird

Gesperrte Gebäude sind **nicht sichtbar** bevor die Bedingungen erfüllt sind. So bekommt der Spieler immer ein klares nächstes Ziel ohne überwältigt zu werden.

---

## Produktionsketten

### Regel
- **Extraktion & erste Verarbeitung:** 1 Input reicht
- **Alle weiteren Stufen:** immer mehrere Inputs erforderlich

### ⛏️ Extraktion (1 Gebäude → 1 Rohstoff)

| Gebäude | Produziert |
|---|---|
| Eisenmine | Eisenerz |
| Kohlemine | Kohle |
| Kupfermine | Kupfererz |
| Siliziumbruch | Siliziumsand |
| Ölpumpe | Rohöl |

### 🔥 Erste Verarbeitung (1 Input → 1 Output)

| Gebäude | Input | Output |
|---|---|---|
| Schmelzofen | Eisenerz | Eisenbarren |
| Kupferschmelze | Kupfererz | Kupferbarren |
| Siliziumofen | Siliziumsand | Rohsilizium |
| Raffinerie | Rohöl | Kunststoff |

### 🔧 Metallkette (mehrere Inputs)

| Gebäude | Input | Output |
|---|---|---|
| Hochofen | Eisenbarren + Kohle | Stahlbarren |
| Walzwerk | Eisenbarren + Stahlbarren | Eisenplatte |
| Stahlwerk | Stahlbarren + Kohle | Stahlblech |
| Presswerk | Stahlblech + Eisenplatte | Stahlträger |

### 🔌 Kabelkette (mehrere Inputs)

| Gebäude | Input | Output |
|---|---|---|
| Drahtziehwerk | Kupferbarren + Kohle | Kupferdraht |
| Kabelwerk | Kupferdraht + Kupferbarren | Kupferkabel |
| Isolierwerk | Kupferkabel + Kunststoff | Isoliertes Kabel |
| Spulenwerk | Isoliertes Kabel + Eisenbarren | Spule |

### 💻 Elektronikkette (mehrere Inputs)

| Gebäude | Input | Output |
|---|---|---|
| Waferwerk | Rohsilizium + Kupferbarren | Siliziumwafer |
| Chipfabrik | Siliziumwafer + Kupferdraht | Mikrochip |
| Platinenwerk | Mikrochip + Isoliertes Kabel | Platine |

### ⚙️ Mechanik — Verbindungspunkte (mehrere Inputs)

| Gebäude | Input | Output |
|---|---|---|
| Maschinenwerk | Stahlträger + Spule | Maschinenrahmen |
| Motorenfabrik | Maschinenrahmen + Stahlblech | Motor |

### 🤖 Robotik (mehrere Inputs)

| Gebäude | Input | Output |
|---|---|---|
| Roboterwerk | Motor + Platine + Stahlträger | Basisroboter |

---

## Kohle — Besondere Rolle

Kohle ist kein "Endprodukt" sondern ein vielseitiger Brennstoff & Zutat:
- Kraftwerk → Strom *(derzeit nicht im Spiel, für spätere Erweiterung)*
- Hochofen: Eisenbarren + **Kohle** → Stahlbarren
- Drahtziehwerk: Kupferbarren + **Kohle** → Kupferdraht
- Stahlwerk: Stahlbarren + **Kohle** → Stahlblech

Kohle kann auch manuell verkauft werden.

---

## Benutzeroberfläche

### Startbildschirm

Beim Öffnen des Spiels erscheint zuerst ein **Homescreen** mit:
- Spielname / Logo
- **[Starten]** Button → wechselt zur Hauptansicht
- (Optional später: Speicherstand laden, Einstellungen)

---

### Hauptansicht: Produktionsbaum

Ein einziger scrollbarer Bildschirm mit allen Materialketten als **Flussdiagramm (Baum)**. Jeder Knoten repräsentiert ein Material.

**Jeder Knoten zeigt:**
```
┌─────────────────────────────────┐
│  🔩 Eisenerz                    │
│  Lager: 450                     │
│  +12/s produziert | -8/s verbraucht │
│  Gebäude: 3x Eisenmine          │
│  [████████░░] nächste in 2s     │
└─────────────────────────────────┘
```

- **Lager:** aktueller Bestand
- **+/- pro Sekunde:** Produktion vs. Verbrauch
- **Gebäudeanzahl:** wie viele Gebäude dieses Material produzieren
- **Fortschrittsbalken:** wann wird die nächste Einheit fertiggestellt

### Klick auf Knoten → Popup

Ein Popup-Fenster öffnet sich mit:
- Aktueller Lagerbestand
- **Verkaufen:** Menge eingeben → für Credits verkaufen
- **Gebäude kaufen:** Liste aller Gebäude die dieses Material produzieren
  - Kosten angezeigt (Credits + Materialien)
  - Kaufen-Button (ausgegraut wenn Voraussetzungen nicht erfüllt)

### Navigation
Die Hauptansicht ist eine große freie Canvas-Fläche. Der Spieler navigiert indem er **Rechtsklick + Ziehen** nutzt um die Ansicht zu verschieben — wie eine Karte. Keine Scrollbalken. Das Popup beim Klicken auf einen Knoten ist ein normales Fenster.

---

## Spielstart

Der Spieler beginnt mit:
- 0 Credits
- Je **1x** jedes Extraktionsgebäude bereits gebaut und aktiv (Eisenmine, Kohlemine, Kupfermine, Siliziumbruch, Ölpumpe)
- Alle Extraktionsgebäude sind von Anfang an sichtbar und kaufbar
- Verarbeitungsgebäude erscheinen erst wenn die Freischaltbedingungen erfüllt sind

Der Spieler sieht sofort Rohstoffe produziert werden, kann sie verkaufen, bekommt erste Credits und lernt die Kauf/Verkauf-Mechanik direkt am Anfang.

---

## Kaufregeln für Extraktionsgebäude

Extraktionsgebäude (Eisenmine, Kohlemine, Kupfermine, Siliziumbruch, Ölpumpe) haben eine besondere Kaufregel:

**1. Kauf (Freischaltung):** kostet nur Credits
**2. Kauf und alle weiteren:** kostet Credits + alle Grundrohstoffe außer dem eigenen

Beispiele:
- Eisenmine (2.+): Credits + Kohle + Kupfererz + Siliziumsand + Rohöl
- Kohlemine (2.+): Credits + Eisenerz + Kupfererz + Siliziumsand + Rohöl
- Kupfermine (2.+): Credits + Eisenerz + Kohle + Siliziumsand + Rohöl

Das zwingt den Spieler früh zu diversifizieren — man kann nicht einfach nur eine Ressource spammen.

---

## Zukünftige Erweiterungen (noch nicht geplant)

- Weitere Ketten: Titan, Platin, Quantentechnik
- Roboter automatisieren bestimmte Prozesse
- Raumschiffteile als späte Kette
- Weitere Rohstoffe (z.B. Gold, seltene Erden)

Das System ist so aufgebaut, dass neue Ketten jederzeit hinzugefügt werden können ohne die bestehende Struktur zu ändern.
