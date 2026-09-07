# AAMT Dwarf Fortress — Creature + Civilization Tool

Create a playable (or NPC) custom creature + civ pack for Dwarf Fortress Premium from a JSON spec, with body validation, **biological cost / balance scoring**, language, graphics sheets, optional AAMT worker threads, optional DFHack helpers, and an Adventure Mode parity kit (documented stopgap).

## Quick start

```powershell
cd D:\games\Steam\steamapps\common\Transcendence\Tools\DwarfFortress

python df_civ_cli.py new --id MYFOLK --name "my folk" --preset humanoid_civ
python df_civ_cli.py validate --spec ..\Output\DwarfFortress\MYFOLK\creature.json --fix
python df_civ_cli.py analyze --spec ..\Output\DwarfFortress\MYFOLK\creature.json --workers 4
python df_civ_cli.py generate --spec ..\Output\DwarfFortress\MYFOLK\creature.json --adventure-kit
python df_civ_cli.py art --spec ..\Output\DwarfFortress\MYFOLK\creature.json --no-sd --workers 4
python df_civ_cli.py install --spec ..\Output\DwarfFortress\MYFOLK\creature.json

python df_civ_cli.py editor --spec ..\Output\DwarfFortress\MYFOLK\creature.json
# or: .\ChooseYourCreature.bat -Action Gui
```

## Cost / balance (heuristic)

`df_body_cost.py` scores axes 0–100 from the body graph (complexity, energy, vulnerability, specialization, offense, defense, mobility, utility) and suggests a gameplay `role`. This is a **game-design model**, not hidden DF biology.

- CLI: `analyze` writes `cost_report.json`
- Validate JSON includes `cost`
`df_body_editor.py` + `editor/index.html` is the **Creature Studio**: create/load projects, body graph, cost bars, procedural 32×32 part-sheet preview, generate/install. Launch with `editor` / `-Action Gui`. The old WinForms button sheet is a thin launcher for this studio.

## Threading

`df_workers.py` runs analyze/validate and Pillow part-sheet cells on an AAMT `ThreadPoolExecutor`. **DF’s simulation loop is not multithreaded.** File writes stay on the caller thread. Env: `AAMT_DF_WORKERS`. CLI: `analyze --workers N`, `art --no-sd --workers N`.

## Adventure parity kit

See [`AdventureParity/CLASSIC_VS_STEAM.md`](AdventureParity/CLASSIC_VS_STEAM.md). Staging via `adventure-kit` / `generate --adventure-kit` adds documented `ADVENTURE_MODE_ENABLED` reactions and lore text — not Classic conversation/magic.

## Presets

| Preset | Notes |
|--------|--------|
| `hematophyte` | **Custom body object** — vine-serpent plant–animal (maw + proboscis + thorns); not a vanilla fragment mash |
| `humanoid_civ` | Dwarf-like playable humanoid |
| `winged_humanoid` | Humanoid + `2WINGS` |
| `quadruped_grasp` | Quadruped with front grasp |
| `insectoid` | Chitin / exoskeleton plans |
| `serpentine` | Soft body + head; not site-controllable by default |

## Layout

| Path | Role |
|------|------|
| `df_civ_cli.py` | argparse entrypoint |
| `df_body_cost.py` / `df_body_function.py` / `df_body_evolution.py` / `df_body_balance.py` | cost model |
| `df_workers.py` | AAMT-side thread pool |
| `df_adventure_kit.py` + `AdventureParity/` | Adventure stopgap kit |
| `df_body_editor.py` + `editor/index.html` | SVG body + Cost tab |
| `templates/` | dwarf/entity skeletons |

## Notes

- `info.txt` uses `NUMERIC_VERSION:5316` (53.16-compatible).
- Art prefers Stable Diffusion via `Shared/sd_http_client` when a server is up; `--no-sd` forces Pillow silhouettes.
- DFHack scripts (`*_hooks`, `*_test`, `*_analyze`, `*_adv_lore`) are written only if `hack/` exists.
- See `DWARF_FORTRESS_TOOLSET_INTEGRATION.md` for toolset wiring.
