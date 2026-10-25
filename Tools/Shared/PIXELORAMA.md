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

## AAMT Sprite Forge (Pixelorama extension, headless)

Pixelorama extension that builds and edits sprites for the Magi-Tech Starbound mod.
**Agents always run it headless** (`--headless --quit`) through this client. Before it
starts Godot, the client waits for at least 2 GB of free VRAM, without holding the lock,
and then takes the GPU lock. Both waits time out after 300 s by default (`--vram-wait`,
`--lock-timeout`, or the environment variables `AAMT_SPRITEFORGE_VRAM_WAIT` and
`AAMT_SPRITEFORGE_LOCK_TIMEOUT`). A timeout returns
`{"ok": false, "retryable": true, "error": ...}`, so retry later. Each result is also kept
in `Tools\Logs\pixelorama\spriteforge\result_*.json`.
The dock panel in the GUI is an extra for the user. Every feature below also works
headless.

| | |
|---|---|
| Source | `Tools\Pixelorama\extensions\AAMTSpriteForge\` (`extension\*.gd`, `build.py`, `tools\sf_ai_assist.py`) |
| Installed | `%APPDATA%\pixelorama\extensions\AAMTSpriteForge.zip` + `config.ini [extensions] AAMTSpriteForge=true` |
| Target | Pixelorama v1.2.3-stable (ExtensionsAPI 9, pxo v7). Text GDScript `.zip`; no Godot editor/export step |
| Raw CLI | `Pixelorama.exe --headless --quit -- spriteforge cmd=<cmd> key=value ... result=<res.json>` |

```powershell
python Shared\pixelorama_client.py sf-install          # build + install + enable (Pixelorama closed)
python Shared\pixelorama_client.py sf-status           # installed/enabled? (no launch)
python Shared\pixelorama_client.py sf-selftest         # headless load check

# Unity still -> 4-frame idle .pxo + Starbound sheet/.frames/.animation
python Shared\pixelorama_client.py sf-create still.png --cell 32x32 --frames 4 --style bob `
    --tags idle:1-4:6 --palette auto --outline auto `
    --pxo work\x.pxo --sheet work\x.png --animation auto
# frames folder / sheet (a sibling .frames is read: grid + tag names) as source
python Shared\pixelorama_client.py sf-create work\frames --cell 32x32 --tags "idle:1-4:6,fire:5-8:12:transition:idle" --pxo work\y.pxo
python Shared\pixelorama_client.py sf-create old_sheet.png --pxo work\z.pxo   # uses old_sheet.frames
# palette: file (.gpl/.pal/.hex/.json/.png), Pixelorama name ("DawnBringer 32"), auto, or sampled
python Shared\pixelorama_client.py sf-palette ref1.png ref2_folder --colors 24 --out work\mt.gpl
python Shared\pixelorama_client.py sf-apply work\x.pxo --palette work\mt.gpl --outline "#140c1c" --in-place
python Shared\pixelorama_client.py sf-export work\x.pxo --sheet out\x_sheet.png --animation auto --layout rows
python Shared\pixelorama_client.py sf-render work\x.pxo --out out\preview --frame all --scale 4
python Shared\pixelorama_client.py sf-info work\x.pxo
# candidates (SD outputs, Unity-derived frames) -> hidden layers to hand-pick, or extra frames
python Shared\pixelorama_client.py sf-import work\x.pxo --images sd_out\ --as layers --palette work\mt.gpl --in-place
# OPT-IN, uses the GPU: frame -> SD3.5 img2img (:1338) -> new hidden layer "AI img2img f1"
python Shared\pixelorama_client.py sf-ai work\x.pxo --prompt "arcane crystal, pixel art" --frame 1 --strength 0.45 --in-place
python Shared\pixelorama_client.py sf-batch jobs.json
```

Any other key can be passed as `--set key=value`, for example `--set bg=none`,
`--set anchor=center`, `--set keep_source_layer=false` or `--set image_ref=/items/x/x_sheet.png`.

From Python: `from pixelorama_client import spriteforge` and then
`spriteforge("create", source=Path(...), cell="32x32", ...)` or `spriteforge(job_file=Path("jobs.json"))`.

**Output.** Each command returns JSON: `{ok, exit_code, jobs: [{id, ok, error, outputs{pxo, sheet, frames, animation, palette}, export{grid, cell, sheet_size, frame_names, states}, project{size, frames, fps, durations, layers, tags}, palette{count, colors}, warnings}]}`.
Exit codes: `0` ok, `1` a job failed, `2` bad arguments or job file, `3` internal script error. Pixelorama's log is `%APPDATA%\pixelorama\logs\godot.log`.

**Job file** (`sf-batch`): `{"defaults": {...}, "jobs": [{"id": "...", "cmd": "create", "source": "...", ...}]}`.
The keys are the same as the `key=value` args. `tags` can be a string or a list of
`{name, from, to, fps, mode, transition}`. `from` and `to` are 1-based and inclusive.

**Key reference**

| key | meaning (default) |
|---|---|
| `source`, `type` | still PNG, frames folder, sheet PNG or `.pxo`. `type` is detected automatically (`still`/`frames`/`sheet`/`pxo`) |
| `cell` | target cell `WxH`. Defaults to the trimmed source size rounded up to 8 when it is ≤128, otherwise 64x64 |
| `frames`, `style` | for a still: frame count (4) and motion (`bob`, `float`, `sway`, `pulse`, `flutter` or `none`) |
| `grid`, `frame`, `frames_json` | slicing for a sheet source. A sibling `.frames` file is used when these are missing |
| `bg`, `bg_tol`, `bg_lum`, `bg_color` | background removal: `auto` flood-fills the light, low-saturation border of opaque Unity stills; `light`, `color` or `none` |
| `trim`, `margin`, `anchor`, `resample`, `alpha_threshold` | fitting: shared scale for all frames, `bottom` anchor, `box` resample, binary alpha at 128 (`-1` keeps soft alpha) |
| `palette`, `colors`, `palette_out`, `embed_palette` | quantize to a palette (16 colours for `auto`), write the palette as `.gpl`/`.json`, and store it as a project palette (true) |
| `outline`, `outline_layer`, `outline_diagonal` | `auto` uses the darkest palette colour, or give `#hex`. The outline goes on its own layer (true) |
| `tags`, `fps`, `default_tag` | `name:from-to:fps[:mode[:transition]]`. Per-tag fps becomes the frame duration multiplier, and the project fps is the highest tag fps |
| `keep_source_layer` | adds a hidden "Source (unpaletted)" layer for reference (true) |
| `sheet`, `layout`, `columns`, `scale` | Starbound export. `rows` puts one row per tag, empty cells are `null`. Names are `tag.N`, and aliases are `default` plus each `tag` → `tag.1` |
| `animation`, `state_type`, `part`, `image_ref` | `.animation` stub: `auto` puts it next to the sheet. State `frames` and `cycle` come from the tags |
| `pxo`, `in_place` | where the `.pxo` is saved. It is written with Pixelorama's own `OpenSave.save_pxo_file`, so it is the native format |

**Notes**

- Headless runs restore `config.ini` `[data]` (recent projects and last directory) after saving or opening a project.
- Godot runs with the Dummy renderer when `--headless`. The lock and VRAM wait are kept so other GPU jobs are not disturbed.
- `sf-ai` never starts the SD server. Start it with `Tools\Start-StableDiffusionServer.ps1`. The helper waits until the server reports it is idle, so it does not interleave with another helper's batch. You can also run `tools\sf_ai_assist.py` on its own.
- Pixelorama v1.2.3 ignores the file *name* given to the native `--export --output` (fixed upstream in v1.2.4, #1635). The client's `export`, `spritesheet` and `json` work around it (see Notes). `sf-export` never had this problem.

## Notes

- Output format is the `--out` extension (`png` / `gif` / `webp` / `json`).
- **Output naming (patched 2026-10-24).** `export`, `spritesheet` and `json` export into a staging folder (`.pxexport_*`) next to `--out`, then move what Pixelorama wrote to the requested name. This works whether Pixelorama names the file after the project (v1.2.3) or honours `--output` (v1.2.4+).
  - One file (a spritesheet, a gif, or `--frames 1`) lands at exactly `--out` (`"exact": true`).
  - Several files (a png export of N frames, or `--split-layers`) land next to it as `<out stem>_0001.png`, `_0002.png` and so on (`"exact": false`), and `"outputs"` lists them.
  - JSON: `--out x.json` (or the `json` command) runs `--export --json`, because Pixelorama writes no JSON without an image export. The `.json` lands at `--out` and the frame PNGs go next to it.
  - `ok` is true only when the output file(s) exist. If Pixelorama could not open the `.pxo`, it exports its empty `untitled` project. That is reported as an error, and the stray file is moved to `Tools\Logs\pixelorama\export_rejects\`.
  - Before launching Godot, the client also waits (bounded) for at least 2 GB of free VRAM.
- `--frames 1-8` is a range. `--direction` is `0|1|2`.
- `--split-layers` writes each layer separately.
- If `see` returns `window not found`, `open` first and wait; Godot creates
  the HWND a moment after process start.
