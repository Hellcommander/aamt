# Grim Dawn Mod Tools — Setup Guide

Python + PowerShell utilities for a **FoA/v1.3 kitchen-sink** install: many masteries/items in Crucible, and a **Custom Game** campaign with Nydiamar (+ Dungeons) plus the same kitchen-sink overlay.

| | |
|---|---|
| **Tools** | `D:\games\Ai assisted toolkit\Tools\GrimDawn` |
| **Game** | `D:\games\Steam\steamapps\common\Grim Dawn` |
| **Override** | `--game` or env `GD_GAME_DIR` / `GRIM_DAWN_DIR` |

Credits: [NOTICE.md](NOTICE.md). Living checklist: [TODOS.md](TODOS.md). Layer notes: [profiles/survival_dlc.md](profiles/survival_dlc.md).

---

## Quick start: the two main tools

### 1. Update a mod for the latest patch + DLC

```bat
Run-GdUpdateMod.bat dom
```

or GUI → **Update mod (latest)** tab, or:

```powershell
python -u patch_mod_for_dlc.py --mod dom --latest --ollama [--rebuild] [--class-mods grimarillion]
```

Writes a **new** Custom Game `mods\<mod>_Latest` (original untouched; `--in-place` backs up the `.arz` and edits the mod itself). Steps:

1. Extracts the mod (re-extracts automatically when the mod's `.arz` changes).
2. Extracts base + every `gdxN` expansion (re-extracts automatically when Steam patches a layer — no stale cache after a game update; a future `gdx4` is picked up without code changes).
3. Compat Pass A + B: imports missing DLC records, merges class hubs (mod classes first, official classes appended — Berserker today, any new class later).
4. Class selection UI expanded (up to 120) and PC skill trees aligned with UI slots.
5. Combo names for **every** mastery pair → `localization\tags_mod_combos.txt`, injected into `resources\Text_EN.arc` (created if the mod has none). See [Combo names](#dual-class-combo-tags).
6. `--rebuild` compiles the `.arz` with `bin\arzedit.exe`.

Re-run it after every game patch or mod update.

### 2. Merge mod databases

```powershell
python -u merge_mod_databases.py --out MyMerge --mods grimarillion Rebirth dom --latest --ollama --rebuild
```

or GUI → **Mod merge** tab / `Run-GdModMerger.ps1 -Out MyMerge -Mods grimarillion,Rebirth -Latest -Ollama`.

- Order comes from `profiles\merge_rules\*.json` (`priority`, higher wins; `enabled:false` mods skipped unless `--include-disabled`). `--keep-order` = command-line order, later wins.
- Mastery-tree overlaps (`records/skills/playerclass*`, `records/ui/skills/class*`) go to the higher `class_priority`.
- `--field-merge` (default `rules`): `none` whole-file replace · `hubs` class hubs union their class lists · `rules` hubs + paths a rule marks `conflict_merge` (with its prefer/keep field lists) · `all` every overlapping `.dbr` keeps unique fields from both mods.
- Rule `skip_overlay_prefixes` and `items_mode: isolate` are honoured.
- `--latest` runs the updater steps 2–5 on the merged result. Each source mod's own combo names survive the renumbering.
- `merge_report.md` (counts per mod pair and merge method) + `merge_conflicts.txt` (every overlapping path) in the output.
- Extracts are cached in `work\_merge_cache` and refreshed when a mod's `.arz` changes.

### 3. Changes that survive game updates (uTXTp patches)

Put tweaks in `patches\*.txt` using the GD-DPS "User Text Patch" format (see `patches\_README.md`); `mods\GD-DPS*\User Text Patch\*.txt` is picked up too. Every update/merge re-extracts fresh game + mod data (game layers and mod `.arz` files are fingerprinted, so a Steam patch or mod update triggers a re-extract) and re-applies the patches, so nothing is lost when the game patches. `utxtp.py` is a native implementation of the format — GD-DPS itself is not installed or run.

### 4. Only out-of-date mods get compat

`--compat auto` (default): a mod is patched only if its player record or class tables lack official classes, or many of its copies of official records miss fields the current game has. Up-to-date mods pass through untouched. Rule override: `"compat": "skip" | "force"` in `profiles\merge_rules\<mod>.json` (Grimarillion = `skip`; its devs update it for each expansion). Merges run this per mod and cache the result until the mod or the game changes.

### 5. Skill class labels (SkillClassTags, regenerated)

`python skill_class_tags.py --base-game` rebuilds `mods\GDMod-SkillClassTags…\text_en` from the current game text (now includes `tagsgdx3_skills.txt` and `[Be]` Berserker; originals kept in `_original_text_en`). Every `--latest` build also labels the skills of **all** classes on its roster (mod masteries get short unique tags, saved in `profiles\skill_class_tags.json`) via `tags_skill_class_labels.txt` in the mod's `Text_EN.arc`.

### 6. Other inputs

- `mods\Sparker` (standalone) outranks the Sparker copies inside Grimarillion and Dawn of Masteries (`merge_rules\sparker.json`: priority 91, field-merge, standalone wins conflicting fields; nothing unique from the bundled copies is dropped).
- Template packs in `mods\<X>\templates\` (e.g. `Templates-82…` that DoM links) are copied into each build's `database\templates`, so arzedit / Asset Manager stop skipping records that use `oneshot_potion.tpl` / `skilltree_expanded.tpl`.

### 7. CLI map editor (`gd_map.py`)

Reads/writes MAP9 world files (the `.map` inside `Levels.arc` / `Maps.arc`); verified byte-identical round trips on the 2.6 GB FoA/Grimarillion world and both Nydiamar worlds.

```powershell
python gd_map.py extract grimarillion --arc Levels.arc        # -> work\maps\grimarillion\world001.map
python gd_map.py info   work\maps\grimarillion\world001.map
python gd_map.py points <map> --category riftgate              # riftgates / dungeon entrances / shrines
python gd_map.py merge  world001.map nydiamar.map -o merged.map --offset 0,0,20000
python gd_map.py pack   CampaignKitchenSink merged.map --arc Levels.arc
```

`merge` appends the other worlds' regions, level data, minimaps, quest files and riftgate/entrance index (GUID-deduplicated; start point stays the campaign's). One game session = one world, so this is how other worlds become reachable with the same progress. Limit: MAP9 stores offsets as 32-bit numbers, so one world file is ≤ 4 GB whether or not the game is 64-bit: campaign + Nydiamar + Crucible arenas fits (~3.5 GB); Nydiamar **and** NydiamarDungeons do not, and they share region IDs (Dungeons is an alternate version of the same world), so Dungeons stays its own Custom Game.

### 8. Portals: Nydiamar + Crucible inside the campaign (`world_link.py`)

```powershell
python -u world_link.py --profile campaign --rebuild      # or --dry-run to only build/verify the world
```

Profile `profiles\world_links\campaign.json` builds the campaign Custom Game the way the expansions do it — one bigger `world001.map` that replaces the old one, new areas joined by in-world doors:

- World: Grimarillion's FoA world001 + Nydiamar + the 10 FoA Crucible arenas (`survivalmode3\resources\Maps.arc`), packed into `CampaignKitchenSink\resources\Levels.arc` (old one kept as `Levels.arc.bak_worldlink`; the separate Nydiamar `Maps.arc` is moved aside so it can't compete at start).
- Portals: 11 two-way portals on clear ground around the Devil's Crossing riftgate — "Portal to Nydiamar" and "Crucible: <arena>" — each paired with a return portal at the destination's start point. Pairing uses the world's "Dungeon Entrances" index, the same mechanism as every cave door, so no quest or riftgate unlock is needed. Portal ids are deterministic, so rebuilds don't break saves.
- Crucible content: records, scripts and assets from `mods\survivalmode` + `survivalmode1..3` (game load order) are imported into the Custom Game every build: Crucible-only records/files refreshed, campaign records never overwritten, the Crucible's `questevents.lua` kept renamed to `questeventssurvival.lua`. This replaces the earlier `survivalmode4` approach — the engine only ever loads `survivalmode1..3` and `mods/survivalmode` (paths are hard-coded in `Engine.dll`), so a `survivalmode4` folder is never read.
- `CampaignKitchenSink\WORLD_LINKS.md` lists where every portal was placed.

- Placement: each merged world is shifted as a whole into empty floor space (Nydiamar east of the campaign, arenas in a row after it). The game's own worlds never have overlapping region footprints, and the first build — arenas all stacked around the origin, Nydiamar over the campaign — hung on a black screen while loading. The build now refuses to write a world with any overlap.
- Resources: the profile's `resources.sources` (low → high merge priority: Nydiamar, ShatteredAffixes, dom, ReignOfTerror, grimarillion, Sparker, Rebirth, Wereform Buffs) build the mod's resource archives every run: archives only one mod has are copied, same-named ones merged per file (later wins), text per tag, `grimdawn.lua`/`main.lua` by combining every mod's `Script.Load` lines. The Cursor-era CampaignKitchenSink had merged only the database ("skip resources"), so it lacked all of Grimarillion's own archives (world art, effects, quests) its Grimarillion world needs.
- Text: a mod text file named like a game file replaces it, so stale copies (Nydiamar's `tags_items.txt` lacked ~4,000 current item names, `tags_ui.txt` 73 UI tags) are merged with the current game's text on every injection (mod wins per tag).

Not verified in-game yet: whether the Crucible's wave logic fully runs outside the main-menu Crucible mode (it is plain Lua + records with no mode checks, but the engine's survival calls could still be mode-gated).

### 9. Archive paths (fixed bug) and `archive_tool.py --repair`

Paths inside an `.arc` never include the archive's own name (`Creatures.arc` holds `ambient/...`; the game resolves `creatures/ambient/x` as Creatures.arc + `ambient/x`). ArchiveTool extracts into a `<stem>/` folder, and earlier versions of this toolkit repacked that folder, so archives came out as `ui/...`, `quests/...`, `text_en/text_en/...` and the game could not find those files (seen in CampaignKitchenSink's ui/Quests/text and NydiamarIntegrated's Maps/Quests). All packers now go through `archive_tool.pack_arc()` from the real top level, and text injection flattens any old nesting itself.

```powershell
python archive_tool.py --repair CampaignKitchenSink NydiamarIntegrated            # fixes archives whose entries ALL carry the prefix
python archive_tool.py --repair CampaignKitchenSink --strip ui.arc text_en.arc    # also mixed nesting (newest copy wins)
```

Use `--strip` only on archives known to be broken: some mods ship a real sub-folder named like the archive (Nydiamar's `Sound.arc` has `sound/...` on purpose). Repaired archives keep a `.bak_prefix` copy. `Levels.arc` (>2 GB map) can't be unpacked by ArchiveTool — rebuild it with `world_link.py` instead.

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
cd "D:\games\Ai assisted toolkit\Tools\GrimDawn"
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
cd /d "D:\games\Ai assisted toolkit\Tools\GrimDawn"

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
cd "D:\games\Ai assisted toolkit\Tools\GrimDawn"

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
python -u patch_class_ui.py   # default: SurvivalPlayground, CampaignKitchenSink, survivalmode4 (or --mod X repeatable)
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
Entries with no class pane (junk like `a`) are dropped from both PC records so mastery N, UI slot N and combo id N stay the same class.

### Dual-class combo tags

Combo tags are index-based (`tagSkillClassName0110` = class 01 + class 10), and each mod numbers its classes differently, so the generator works by **mastery name pair**:

1. Mastery names come from the text (class tree → mastery skill → `skillDisplayName` tag), so mod classes get real names (e.g. *Demon Hunter*), not path guesses.
2. Known names: official game combos, then each source mod read against its **own original** class order, then `work\combo_name_cache.json`.
3. Pairs still unnamed go to Ollama (if enabled), else an `AB` placeholder. Ollama replies are validated (only requested tags, 1–3 word names, no duplicates); accepted names are cached after every batch, so long runs are resumable and rebuilds reuse them.
4. A tag is written for every pair in the final roster, in the game's `tag=value` format; stale index-based combo lines in the mod's other text files are stripped so ours win.

Ollama is auto-started (`ollama serve`) if installed but not running; the model auto-picks a general model (`llama3.1:8b` here), override with `--ollama-model`.

```powershell
python -u fill_combo_tags.py --mod CampaignKitchenSink --ollama
python -u fill_combo_tags.py            # placeholders/cache only, default targets
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
| `Run-GdUpdateMod.bat` | Update one mod for latest patch + DLC (+ Ollama combo names) |
| `Run-NydiamarFoACampaign.bat` | Build `NydiamarIntegrated` |
| `Run-GdSurvivalClasses.bat` | Build `SurvivalPlayground` (DB, profile-driven) |
| `Run-GdSurvivalKitchenSink.bat` | Same + resource ARCs (slow) |
| `Run-GdPackDualArchives.bat` | Pack `survivalmode4` + `CampaignKitchenSink` |
| `Run-GdSurvivalDlcLayer.bat` | Deploy Crucible layer only |
| `Run-GdBuildArz.bat` | Compile `.arz` via toolset arzedit |
| `Run-GdPatchClassUi.bat` | Expand class UI to 120 |
| `Build-Arzedit.bat` | Compile `bin\arzedit.exe` once |
| `Run-GdFoACompat.bat` | FoA compat on one mod |
| `Run-GdModMerger.bat` | Rules-aware merge (`OutName Mod1 Mod2 …`) |
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
| `merge_mod_databases.py` | Merge any mods (rules, field merge, `--latest`) |
| `patch_mod_for_dlc.py` / `patch_dlc_for_mod.py` | Latest-patch updater (`--latest`) / bidirectional compat |
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
