# 🚀 Space Station Idle

An idle/incremental game about building an industrial production chain in
space — from simple raw resources all the way up to basic robots.

Runs fully offline with Python + tkinter, no extra packages required.

## Play

**Windows (no Python needed):** download `SpaceStationIdle.exe` from the
[latest release](https://github.com/Edrick18/Space_Station_Idle/releases/latest)
and double-click it. Windows SmartScreen may warn about an unknown publisher
on first launch — click "More info" → "Run anyway".

**From source** (any OS with Python 3):

```
python space_station_idle.py
```

- **Left-click** a material to open the side panel (sell / buy buildings)
- **Right-click + drag** to move around the map
- Progress is saved automatically to `savegame.json`
- **Offline production:** buildings keep working while the game is closed
  (up to 24 hours are simulated on the next launch)

## Auto-update

On startup the game checks GitHub in the background for a newer version:

- **Exe:** compares the latest [release](https://github.com/Edrick18/Space_Station_Idle/releases)
  tag, downloads the new `SpaceStationIdle.exe` and swaps it in on the
  next launch.
- **Source:** compares `version.json`, downloads the new
  `space_station_idle.py`, active on the next launch.

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

5. Build the exe and publish it as a GitHub release with tag `v1.1.0`
   (same number as `VERSION`):

```
python -m PyInstaller --onefile --windowed --name SpaceStationIdle space_station_idle.py
```

Then create a release on GitHub with tag `v1.1.0` and attach
`dist/SpaceStationIdle.exe` as an asset named exactly `SpaceStationIdle.exe`.

Every player receives the update automatically the next time they start
the game.

## Design

The full game design document (in German) lives in
[raumstation_idle_design.md](raumstation_idle_design.md).
