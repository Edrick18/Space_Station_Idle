# 🚀 Raumstation Idle

Ein Idle/Incremental-Spiel mit Raumstation-Thema: Baue eine industrielle
Produktionskette auf — von einfachen Rohstoffen bis zum Basisroboter.

Läuft komplett offline mit Python + tkinter, keine zusätzlichen Pakete nötig.

## Spielen

```
python raumstation_idle.py
```

- **Linksklick** auf ein Material öffnet das Seitenpanel (Verkaufen / Gebäude kaufen)
- **Rechtsklick + Ziehen** verschiebt die Karte
- Der Spielstand wird automatisch in `savegame.json` gespeichert
- **Offline-Produktion:** Gebäude arbeiten weiter, während das Spiel geschlossen ist (max. 24 Stunden werden nachberechnet)

## Auto-Update

Beim Start prüft das Spiel im Hintergrund, ob in diesem Repository eine
neuere Version liegt (`version.json`). Wenn ja, wird `raumstation_idle.py`
automatisch heruntergeladen und ist **beim nächsten Start** aktiv.

**Updates sind nie Pflicht:** Ohne Internet, ohne gefundenes Update oder bei
irgendeinem Fehler startet das Spiel einfach ganz normal mit der vorhandenen
Version. Der Spielstand bleibt bei Updates immer erhalten.

## Ein Update veröffentlichen

1. Änderungen in `raumstation_idle.py` machen
2. Die Konstante `VERSION` in `raumstation_idle.py` erhöhen (z.B. `"1.1.0"`)
3. Die gleiche Nummer in `version.json` eintragen
4. Committen und pushen:

```
git add -A
git commit -m "Update v1.1.0"
git push
```

Alle Spieler bekommen das Update automatisch beim nächsten Spielstart.

## Design

Das vollständige Game-Design-Dokument liegt in
[raumstation_idle_design.md](raumstation_idle_design.md).
