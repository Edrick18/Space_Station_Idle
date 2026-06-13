# 🚀 Space Station Idle

An idle/incremental game about building an industrial production chain in
space — from simple raw resources all the way up to basic robots.

Runs fully offline with Python + tkinter, no extra packages required.

## Play

```
python space_station_idle.py
```

- **Left-click** a material to open the side panel (sell / buy buildings)
- **Right-click + drag** to move around the map
- Progress is saved automatically to `savegame.json`
- **Offline production:** buildings keep working while the game is closed
  (up to 24 hours are simulated on the next launch)

## Auto-update

On startup the game checks this repository in the background for a newer
version (`version.json`). If one exists, `space_station_idle.py` is
downloaded automatically and becomes active **on the next launch**.

**Updates are never mandatory:** without internet, without an update, or on
any error the game simply starts normally with the version you have. Your
save file is never touched by updates.

## Publishing an update

1. Make your changes in `space_station_idle.py`
2. Bump the `VERSION` constant in `space_station_idle.py` (e.g. `"1.1.0"`)
3. Put the same number into `version.json`
4. Commit and push:

```
git add -A
git commit -m "Update v1.1.0"
git push
```

Every player receives the update automatically the next time they start
the game.

## Design

The full game design document (in German) lives in
[raumstation_idle_design.md](raumstation_idle_design.md).
