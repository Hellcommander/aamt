# Dwarf Fortress Toolset Integration

How the AAMT DF Creature + Civ tool plugs into the Transcendence/AAMT Tools tree.

## Paths

| Key | Source | Purpose |
|-----|--------|---------|
| `DwarfFortressPath` | `Tools/TranscendenceTools.ini` | DF install root |
| `AAMT_DF_PATH` / `DWARF_FORTRESS_PATH` / `DF_PATH` | Environment | Overrides INI |
| `OutputDir` | INI | Preferred staging still uses `Tools/Output/DwarfFortress/` |

Python modules call `Shared/tool_paths.py` (`get_path`, `get_setting`, `tools_root`, `find_blender`) with the same pattern as Qud tools (`sys.path` insert of `Tools/Shared`).

## Module map (vs Qud)

| DF | Qud analogue |
|----|----------------|
| `ChooseYourCreature.ps1` | `ChooseYourFighter.ps1` |
| `ChooseYourCreature-GUI.ps1` | `ChooseYourFighter-GUI.ps1` |
| `df_civ_cli.py` | `qud_fighter_import.py` + tile CLI |
| `df_sd_client.py` | `qud_sd_client.py` |
| `df_tile_generator.py` | `qud_fighter_tile_generator.py` |
| `Output/DwarfFortress/<ID>/` | `Output/Fighters/<id>/` |

## Install target

`df_mod_pack.install_mod` copies the staging folder to:

```
<DF>/mods/aamt_<id>/
```

Enable the mod in DF’s Mods screen (or `data/installed_mods` workflow depending on version). Staging always remains under `Tools/Output/DwarfFortress/<ID>/` for iteration.

## Shared services

- **SD**: `df_sd_client` → `sd_http_client.detect_server` / `generate_image` (no auto-start).
- **Blender**: `df_blender_bake.find_blender` → optional; currently falls back to tile PNGs.
- **DFHack**: if `<DF>/hack/scripts` exists, `df_hack_writer` emits `<modid>_hooks.lua`, `<modid>_test.lua`, and `<modid>_analyze.lua` (main-thread unit snapshot via `dfhack.gui.getSelectedUnit`; skips if DFHack is absent). Adventure lore wrappers (`*_adv_lore.lua`) are staged by the adventure kit.
- **Studio GUI**: `df_body_editor.py` + `editor/index.html` — create/load, body graph, cost, tile preview, generate/install. Launch: `python df_civ_cli.py editor` or `ChooseYourCreature.ps1 -Action Gui`.
- **Graphics**: `df_pixel_art.py` draws original 32×32 ANIMAL_PEOPLE layers (head/body/hands/feet/tail), 96×96 framed portraits, and an assembled preview. Not vanilla asset copies. SD remains optional.
- **Workers**: `df_workers.py` `ThreadPoolExecutor` for validate+cost and Pillow part-sheet cells. Env `AAMT_DF_WORKERS`. File writes stay on the caller thread. **Does not multithread DF.**
- **Adventure kit**: `df_adventure_kit.py` clones documented vanilla `ADVENTURE_MODE_ENABLED` reactions (knap stone / wooden cup). Stopgap, not Classic conversation/magic. CLI: `adventure-kit` / `generate --adventure-kit`. PS1: `-Action Analyze` / `-Action AdventureKit`, `-AdventureKit` on Generate, `-Workers` on Art/Analyze.

## Config snippet

Add to `TranscendenceTools.ini` (see `TranscendenceTools.ini.example`):

```ini
[Paths]
DwarfFortressPath = E:\SteamLibrary\steamapps\common\Dwarf Fortress
```

## Smoke test

```text
python df_civ_cli.py new --id SMOKETEST --name "smoke folk" --preset humanoid_civ
python df_civ_cli.py validate --spec <Output>/SMOKETEST/creature.json --fix
python df_civ_cli.py analyze --spec <Output>/SMOKETEST/creature.json --workers 4
python df_civ_cli.py generate --spec <Output>/SMOKETEST/creature.json --adventure-kit
python df_civ_cli.py art --spec <Output>/SMOKETEST/creature.json --no-sd --workers 4
python df_civ_cli.py adventure-kit --spec <Output>/SMOKETEST/creature.json
```
