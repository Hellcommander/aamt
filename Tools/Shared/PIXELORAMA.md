# Pixelorama AI host

Pixel-art editor for AAMT. Agents drive it headless (export / inspect) and can
open the **real Pixelorama GUI** and screenshot it, same pattern as Material
Maker (CLI) and xEdit (`CreateNoWindow = false` so the tool UI is visible).

| | |
|---|---|
| Install | `D:\tools\Orama Interactive\Pixelorama\Pixelorama.exe` |
| Client | `Tools\Shared\pixelorama_client.py` |
| Launchers | `Tools\Pixelorama.ps1`, `Pixelorama.bat`, `Pixelorama-GUI.bat` |
| INI | `PixeloramaExe` in `TranscendenceTools.ini` |
| Env | `AAMT_PIXELORAMA` / `PIXELORAMA` |
| Upstream | https://github.com/Orama-Interactive/Pixelorama |
| CLI docs | https://www.pixelorama.org/user_manual/cli/ |

Godot argument split:

```
Pixelorama.exe [SYSTEM] -- [USER] [FILES]
SYSTEM: --headless --quit
USER:   --export --spritesheet --output --scale --frames --json ...
```

This client always inserts `--` for you.

## Agent commands

```powershell
python Shared\pixelorama_client.py status
python Shared\pixelorama_client.py version
python Shared\pixelorama_client.py inspect sprite.pxo
python Shared\pixelorama_client.py export sprite.pxo --out out.png
python Shared\pixelorama_client.py spritesheet sprite.pxo --out sheet.png --scale 2
python Shared\pixelorama_client.py json sprite.pxo --out project.json
python Shared\pixelorama_client.py open sprite.pxo    # visible editor
python Shared\pixelorama_client.py see --out shot.png # screenshot that window
python Shared\pixelorama_client.py focus
python Shared\pixelorama_client.py quit
python Shared\pixelorama_client.py gui               # operator panel
```

From Python:

```python
from pixelorama_client import export_project, inspect, open_gui, screenshot_gui, status

status()
open_gui(Path("sprite.pxo"))
screenshot_gui(Path("Logs/pixelorama/see.png"))
export_project(Path("sprite.pxo"), Path("out.png"), spritesheet=True)
```

All JSON. Headless export takes the shared GPU lock (`gpu_hub`) because Godot
renders on the GPU and will fight SD / TRELLIS / Material Maker.

Magi-Tech Starbound producer (AAMT `Tools\Starbound`):

```powershell
.\Produce-UnityStillAnimations.ps1 -Backend pixelorama -AssetIds grenade_fire
python produce_pixelorama_sheets.py --ids grenade_fire
```

Projects: `<mod>/assets/magitech/pixelorama/<id>.pxo`. Steam Tools/Starbound is a
stub that forwards here.

## See the GUI

`open` launches Pixelorama with a normal window (not `--headless`). `see`
PrintWindow-captures that HWND (Godot needs `PW_RENDERFULLCONTENT`) and writes
a PNG under `Tools\Logs\pixelorama\` unless `--out` is set. Read that PNG with
vision. `gui` is a small drag-drop operator panel; it does not replace the
editor — use **See GUI** to look at Pixelorama itself.

## Agent sprite edit (no .pxo yet)

Godot CLI only exports authored `.pxo`. For AI iteration from a still:

```powershell
python Shared\pixelorama_client.py scaffold tile.png --out work\tile --frames 4 --style bob
python Shared\pixelorama_client.py pack work\tile\frames --out work\tile\sheet.png
python Shared\pixelorama_client.py split work\tile\sheet.png --out work\tile\frames --fw 16 --fh 24
python Shared\pixelorama_client.py open work\tile\sheet.png   # refine in GUI, then re-split
```

`scaffold` writes `frames/`, `sheet.png`, `still.png`, and `meta.json` (includes a CoQ
`TileAnimationFrames` hint). Refine the sheet in Pixelorama, `split` back to frames,
install numbered PNGs, merge `AnimatedMaterialGeneric`.

## Notes

- Output format is the `--out` extension (`png` / `gif` / `webp` / `json`).
- `--frames 1-8` is a range. `--direction` is `0|1|2`.
- `--split-layers` writes each layer separately.
- If `see` returns `window not found`, `open` first and wait; Godot creates
  the HWND a moment after process start.
