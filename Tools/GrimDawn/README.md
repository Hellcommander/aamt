# Grim Dawn Mod Tools — Setup Guide

Python + PowerShell utilities for a **FoA/v1.3 kitchen-sink** install: many masteries/items in Crucible, and a **Custom Game** campaign with Nydiamar (+ Dungeons) plus the same kitchen-sink overlay.

| | |
|---|---|
| **Tools** | `D:\games\Steam\steamapps\common\Transcendence\Tools\GrimDawn` |
| **Game** | `D:\games\Steam\steamapps\common\Grim Dawn` |
| **Override** | `--game` or env `GD_GAME_DIR` / `GRIM_DAWN_DIR` |

Credits: [NOTICE.md](NOTICE.md). Living checklist: [TODOS.md](TODOS.md). Layer notes: [profiles/survival_dlc.md](profiles/survival_dlc.md).

---

## What you end up with

Grim Dawn does **not** load kitchen-sink mods into the stock Main Campaign. You need **two** playable packs:

| Pack | Path | How you launch it | Contents |
|------|------|-------------------|----------|
| **Survival DLC layer** | `<game>\survivalmode4\` | Main menu → **Crucible / Survival** | Kitchen-sink classes/items on official Crucible maps |
| **Campaign Custom Game** | `<game>\mods\CampaignKitchenSink\` | Main menu → **Custom Game** → CampaignKitchenSink | Nydiamar + Dungeons + kitchen-sink overlay (FoA campaign maps kept where possible) |

Staging merge (not played directly after packing):

| Staging | Path | Role |
|---------|------|------|
| Kitchen-sink DB | `mods\SurvivalPlayground` | Merge source for both packs |
| Nydiamar prep | `mods\NydiamarIntegrated` | FoA + Nydiamar + NydiamarDungeons + portal stubs; **base** for CampaignKitchenSink |

```
mods\SurvivalPlayground  ──pack──►  survivalmode4          (Crucible)
         │
mods\NydiamarIntegrated  ──base──►  mods\CampaignKitchenSink  (Custom Game)
         ▲                              ▲
         │                              └── overlay kitchen-sink DB (skip survival world/maps)
         └── FoA + Nydiamar + Dungeons + portal stubs
```

**Important:** `survivalmode4` never changes stock Campaign. Campaign kitchen-sink is **only** via Custom Game.

Engine still limits **2 active masteries**. Class UI is patched to show up to **120** selectable trees.

---

## Requirements

### Software

- **Grim Dawn** with AoM + FG + FoA (and Crucible), including `ArchiveTool.exe` in the install
- **Python 3.10+** on `PATH` (`python -u …` works from this folder)
- **.NET SDK** (once) to build `bin\arzedit.exe` — or use Crate **Asset Manager** instead
- Optional: **Ollama** + `requests` for nicer dual-class combo names (placeholders work without it)
- Optional: World Editor / Quest Editor (from the GD install) for the **portal stitch** (not fully automatable)

### Mod folders (flat names under `mods\`)

Install/rename so these folder names match `profiles\survivalmode.json` and `profiles\nydiamar.json`:

| Folder | Used for |
|--------|----------|
| `survivalmode` | Crucible base for SurvivalPlayground |
| `dom` | Dawn of Masteries |
| `grimarillion` | Grimarillion |
| `Rebirth` | Rebirth |
| `Riftwalk` | Present but **disabled** in merge rules (too strong) |
| `ShatteredAffixes` | Affixes/loot |
| `Wereform Buffs` | Wereform skill buffs |
| `ReignOfTerror` | Portal-mod content (items; no world replace) |
| `Nydiamar` | [Nexus #40](https://www.nexusmods.com/grimdawn/mods/40) by Houck |
| `NydiamarDungeons` | Sibling of Nydiamar (same parent `mods\`) |

If your Nexus zip is nested (e.g. `Nydiamar-40-…\Nydiamar\`), move/copy the inner folders to `mods\Nydiamar` and `mods\NydiamarDungeons`.

---

## One-time setup

### 1. Confirm paths

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\GrimDawn"
dir "D:\games\Steam\steamapps\common\Grim Dawn\ArchiveTool.exe"
dir "D:\games\Steam\steamapps\common\Grim Dawn\mods"
```

### 2. Build arzedit (recommended)

```bat
Build-Arzedit.bat
```

Expect `bin\arzedit.exe`. Without it, build `.arz` databases with **Asset Manager** instead of `Run-GdBuildArz.bat`.

### 3. (Optional) Point at another game install

```powershell
$env:GD_GAME_DIR = "D:\path\to\Grim Dawn"
```

Or edit `game_dir` in `profiles\survivalmode.json` / `profiles\nydiamar.json`.

### 4. Review merge profile

- Mod list: [`profiles/survivalmode.json`](profiles/survivalmode.json)
- Per-mod priority / skips: [`profiles/merge_rules/`](profiles/merge_rules/README.md)

Default priority (low → high): Shattered 60 → DoM 70 → RoT 80 → Grimarillion 90 → Rebirth 92 → Wereform 96. Riftwalk stays `enabled: false`.

---

## Full rebuild (recommended order)

Use the GUI or the equivalent `.bat` / Python steps. First full run is long (extract + merge); later runs are incremental only when you re-merge.

### Option A — GUI

1. Double-click **`Run-GdToolsGui.bat`**
2. Confirm **Game folder** at the top
3. **Nydiamar** tab → **Run Nydiamar campaign pipeline**  
   → builds `mods\NydiamarIntegrated` (FoA compat, quest remap, portal stubs, map unpack)
4. **Survival playground** tab:
   - Check **Skip resource ARCs** for a faster DB-only merge (first kitchen-sink)
   - **Build SurvivalPlayground (staging)**
   - **Pack both archives (Survival DLC + Campaign)**
   - **Build .arz (arzedit CLI)**
   - **Re-apply class UI (up to 120)** if class list looks truncated
5. Playtest (see [How to play](#how-to-play) below)
6. When ready for story portals: World Editor stitch (see [Portal stitch](#portal-stitch-manual))

### Option B — Batch files (same pipeline)

```bat
cd /d "D:\games\Steam\steamapps\common\Transcendence\Tools\GrimDawn"

REM 1) Nydiamar + Dungeons + FoA + portal stubs
Run-NydiamarFoACampaign.bat

REM 2) Kitchen-sink staging (DB only; use KitchenSink bat for full ARC merge)
Run-GdSurvivalClasses.bat

REM 3) Pack survivalmode4 + CampaignKitchenSink
Run-GdPackDualArchives.bat

REM 4) Compile .arz for both packs
Run-GdBuildArz.bat

REM 5) Ensure class selection UI supports many masteries
Run-GdPatchClassUi.bat
```

### Option C — PowerShell / Python (more control)

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\GrimDawn"

# Nydiamar unified prep
.\Run-NydiamarFoACampaign.ps1 -PortalHub devils_crossing -DryRunNames
# Equivalent:
# python nydiamar_campaign.py --full-compat --remap-quests --prepare-editor-stitch `
#   --portal-hub devils_crossing --merge-dungeons --out NydiamarIntegrated

# Survival playground from profile
.\Run-GdSurvivalClasses.ps1 -DryRunNames -SkipResources

# Dual pack + ARZ
python -u pack_dual_archives.py --source SurvivalPlayground
python -u build_mod_arz.py --target both
python -u patch_class_ui.py --targets SurvivalPlayground,CampaignKitchenSink,survivalmode4
```

### After packing — expected artifacts

| Artifact | Path |
|----------|------|
| Crucible DB | `survivalmode4\database\SurvivalMode4.arz` (name may vary slightly) |
| Campaign DB | `mods\CampaignKitchenSink\database\CampaignKitchenSink.arz` |
| Nydiamar prep DB | `mods\NydiamarIntegrated\database\NydiamarIntegrated.arz` |
| Staging (unpacked OK) | `mods\SurvivalPlayground\database\` |

A few records may be **skipped** during arzedit (missing templates such as `oneshot_potion.tpl` or `skilltree_expanded.tpl`). That is usually non-fatal.

---

## How to play

### Crucible / Survival (kitchen-sink waves)

1. Launch Grim Dawn normally (not Custom Game).
2. Main menu → **Crucible** / Survival.
3. New character (or existing Crucible character).
4. You should see the expanded class list from the merge (UI capped at 120).

If classes look vanilla, confirm `survivalmode4` exists and has a built `.arz`, then restart the game. See [Troubleshooting](#troubleshooting).

### Campaign + Nydiamar + kitchen-sink

1. Main menu → **Custom Game**.
2. Select **CampaignKitchenSink**.
3. New character under that mod (Custom Game saves are **not** shared with stock Campaign).
4. Progress FoA/campaign content in that mod’s world.
5. After [Editor stitch](#portal-stitch-manual): use the hub portal → Nydiamar → in-world dungeon portals (already merged).

**Without** the Editor stitch you still get FoA-updated Nydiamar content in the pack and kitchen-sink classes/items; the campaign-hub → Nydiamar **portal** will not exist until you place it.

Standalone Nydiamar-only Custom Game: use **NydiamarIntegrated** after building its `.arz`.

---

## Portal stitch (manual)

Full portal placement **cannot** be automated with Crate’s CLI. The tools prepare stubs and unpack maps; you finish in the World Editor.

Static reference: [editor_stitch_checklist.md](editor_stitch_checklist.md).  
Per-build checklist: `mods\NydiamarIntegrated\EDITOR_STITCH_CHECKLIST.md` (and/or under CampaignKitchenSink after pack).

### Hub keys (`--portal-hub`)

| Key | Hub |
|-----|-----|
| `devils_crossing` | Devil's Crossing (default) |
| `homestead` | Homestead |
| `fort_ikon` | Fort Ikon |
| `malmouth` | Malmouth outskirts |
| `asterkarn` | Asterkarn / FoA |

### Manual finish

1. Asset Manager / arzedit → database for the Custom Game is built.
2. Open **Editor.exe** → working mod = `CampaignKitchenSink` or `NydiamarIntegrated`.
3. Keep Nydiamar as its **own** world; edit campaign layout only enough to add a **portal / riftgate / NPC** to Nydiamar’s start region.
4. Link the riftgate, **Rebuild Selected Pathing** / **Rebuild Selected Map** (avoid “Rebuild All” unless you know you need it).
5. Quest Editor → finish stub under `records/quests/nydiamar/portal/`.
6. Build maps/quests → playtest Custom Game: hub → portal → Nydiamar → dungeon portals.

**Practical tip:** Do the stitch once, keep the edited map files in the mod, and later rebuilds can reuse them. First placement is manual; repeats can be “just repack.”

Reign of Terror uses the same idea (content-only merge; portal later): [profiles/reign_of_terror_portal.md](profiles/reign_of_terror_portal.md).

---

## Class UI and combo names

### Class selection (up to 120)

```bat
Run-GdPatchClassUi.bat
```

Or GUI → **Re-apply class UI (up to 120)**.  
Maps PC `skillTree` lines into the selection UI; does **not** unlock more than two active masteries.

### Dual-class combo tags

Placeholders (or Ollama names) go into `Text_EN.arc` / localization:

```powershell
python -u fill_combo_tags.py --target CampaignKitchenSink
python -u fill_combo_tags.py --target survivalmode4
# or via class_combo_names.py / Survival pipeline -DryRunNames vs live Ollama
```

Re-run combo injection on CampaignKitchenSink **after** a dual pack if Text_EN was overwritten.

---

## Updating after mod or game patches

| Change | What to re-run |
|--------|----------------|
| New mod version / add a mod | Edit `profiles\survivalmode.json` + optional `merge_rules\<id>.json` → Survival build → dual pack → ARZ → class UI |
| FoA / Crate patch | FoA compat on affected mods; Nydiamar pipeline; Survival rebuild; **re-check Editor stitch** if campaign maps changed |
| Only tweak merge rules | Survival rebuild + pack + ARZ (skip Nydiamar if unchanged) |
| Only Crucible layer | `Run-GdSurvivalDlcLayer.bat` or pack with campaign skip |
| Only campaign pack | `python pack_dual_archives.py --skip-survival` (needs NydiamarIntegrated + SurvivalPlayground) |

---

## Launcher reference

| Bat | Purpose |
|-----|---------|
| `Run-GdToolsGui.bat` | Desktop GUI for all common steps |
| `Run-NydiamarFoACampaign.bat` | Build `NydiamarIntegrated` |
| `Run-GdSurvivalClasses.bat` | Build `SurvivalPlayground` (DB, profile-driven) |
| `Run-GdSurvivalKitchenSink.bat` | Same + resource ARCs (slow) |
| `Run-GdPackDualArchives.bat` | Pack `survivalmode4` + `CampaignKitchenSink` |
| `Run-GdSurvivalDlcLayer.bat` | Deploy Crucible layer only |
| `Run-GdBuildArz.bat` | Compile `.arz` via toolset arzedit |
| `Run-GdPatchClassUi.bat` | Expand class UI to 120 |
| `Build-Arzedit.bat` | Compile `bin\arzedit.exe` once |
| `Run-GdFoACompat.bat` | FoA compat on one mod |
| `Run-GdModMerger.bat` | Simple later-wins merge |
| `Run-GdStash.bat` | GD Stash |

### CLI scripts

| Script | Purpose |
|--------|---------|
| `patch_survival_classes.py` | SurvivalPlayground kitchen-sink merge |
| `pack_dual_archives.py` | Dual pack from staging |
| `pack_survival_dlc_layer.py` | `survivalmode4` only |
| `nydiamar_campaign.py` | Full Nydiamar → FoA Custom Game prep |
| `build_mod_arz.py` | arzedit CLI build |
| `patch_class_ui.py` | Class selection UI |
| `fill_combo_tags.py` / `class_combo_names.py` | Combo name tags |
| `merge_mod_databases.py` | Generic mod merge |
| `patch_mod_for_dlc.py` / `patch_dlc_for_mod.py` | Bidirectional FoA compat |
| `quest_remap.py` | Namespace quests under a prefix |
| `editor_stitch.py` | Unpack maps + portal stubs + checklist |

---

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| Crucible looks vanilla | Confirm `survivalmode4` exists with built `.arz`; restart GD; see [profiles/survival_dlc.md](profiles/survival_dlc.md) fallback patch of `survivalmode3` (backs up first; Steam may restore) |
| Custom Game missing classes | Rebuild CampaignKitchenSink after SurvivalPlayground; run class UI patch; rebuild `.arz` |
| No Nydiamar / wrong maps | Run Nydiamar pipeline **before** dual pack; campaign base must be `NydiamarIntegrated` |
| Hub portal missing | Expected until World Editor stitch |
| arzedit skips records | Missing templates (e.g. `oneshot_potion.tpl`); usually OK; fetch templates if a specific class tree is missing |
| ArchiveTool hung | Close orphan `ArchiveTool.exe` processes; tools also try to kill orphans after extract |
| Stock Campaign unchanged | By design — use Custom Game for kitchen-sink campaign |

---

## RenoDX

HDR install notes live under `renodx_dist\` (separate from these mod tools).
