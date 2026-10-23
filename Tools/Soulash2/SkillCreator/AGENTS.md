# Skill Creator — agent handoff

Use this tool to **author Soulash 2 skill mods**. Drive it with the CLI. Prefer Geomancy / Electromancy / Warlock layout over inventing schema. Do not `install` unless the human explicitly asks.

Working directory:

```
D:\games\Ai assisted toolkit\Tools\Soulash2\SkillCreator
```

Staging (safe): `D:\games\Ai assisted toolkit\Tools\Output\Soulash2\<id>\`  
Live game mods: `D:\games\Steam\steamapps\common\Soulash 2\data\mods\` — **write-only via `install --yes`**  
Game path resolution: `Soulash2Path` in `Tools\TranscendenceTools.ini` → `AAMT_SOULASH2_PATH` → auto-detect (`s2_paths.py`). Top-level `Soulash2\*.py` scripts use `s2_game_paths.py`; never hard-code a Steam library.

Icons/sprites prefer Shared SD3.5 (`D:\games\Ai assisted toolkit\Tools\Shared\AGENTS.md`). External PNGs (including Cursor image-gen) pack via `inject-icon`.

## Hard rules

- **Prefix custom skill ids** with the author slug, same pattern as vanilla `core_2_pyromancy`. Default: `arendeth_<school>` (`new --id baromancy` becomes `arendeth_baromancy`). Never ship a bare school name (`wind_magic`, `geomancy`) — the game may add that id later. `rename-id --to <school>` retargets an existing spec. Hydromancy is a normal school id (`arendeth_hydromancy`); an earlier rebuild had milestone layout problems — that was not a folder-name ban.
- Effect keys and enums: official docs + vanilla `core_2` + workshop skill mods. Prefer `confidence: vanilla` / `docs`. **Do not use `unconfirmed` (exe-only) effects** unless the human insists.
- Full skill-tree layout: **Geomancy** workshop `3132395866`, ElectromancyFIXED `3311158717`, Warlock `3708324224` (`NOTES.md` there lists what the engine actually honors).
- New ability ids are **strings** like `arendeth_baromancy_air_slice`, not vanilla numeric ids (`"15"`).
- File `ability_amplifiers.json` (docs wrongly say `amplifiers.json`).
- Stackers live in `ability_stackers.json`. They are **not** milestone rewards. Abilities apply them via `effects_keys.stacker` + `effects.stacker_count`. Amplifiers can apply them with `bonuses: [{effect: stacker, value: "<id>", secondary_value: 1}]`.
- **Never emit `control_action` as a skill milestone reward.** Engine ignores those. Tame-style control actions belong on `character.json` (`add-control-action`).
- Passive `description` is ignored in-game. Tooltip comes from effects only.
- Always `validate` then `write`. Stop on errors. Observed-count warnings (beyond highest seen in vanilla/workshop) are not blockers. Encoding warnings (knockback as a float, `stamina_cost` as an amplifier bonus, `heal`+`damage` instead of `damage_as_life`, `summon_count` above 24, passive `movement_speed` instead of `move_speed`) are the mistakes this tool made on the Hydromancy rebuild — fix them.
- **Do not run `install` unless the human asked.** It requires `--yes`.

## Three effect encodings (do not mix)

| Kind | JSON | Shape |
|---|---|---|
| Ability | `effects` | object, **one of each key**: `"bleed": 1` |
| Ability refs | `effects_keys` | object of string ids: `"summon": "my_golem"` |
| Amplifier | `bonuses` | array: `{effect, value, secondary_value?, third_value?}` plus optional top-level `cooldown` / `range` / `cost_stamina` |
| Passive | `effects` | array, same `{effect, value, …}` shape as amplifier bonuses |

`--effect summon=my_id` is auto-routed to `effects_keys`. `--effect bleed=1` goes to `effects`. `explain <id>` shows **what it does** and **where it is valid**.

## Workflow

```powershell
cd D:\games\Ai assisted toolkit\Tools\Soulash2\SkillCreator

python s2_skill_cli.py explain bleed
python s2_skill_cli.py list-effects --kind ability --dropdown
python s2_skill_cli.py new --id arendeth_myskill --name "My Skill"
python s2_skill_cli.py add-gear --id arendeth_myskill first=70:1,second=111:1
python s2_skill_cli.py add-exp-source --id arendeth_myskill walk=1

python s2_skill_cli.py add-ability --id arendeth_myskill --ability-name "Stone Bolt" --unlock-level 1 --damage "[2,6]" --damage-type physical --target health --range 4 --stamina 4 --effect bleed=1
python s2_skill_cli.py add-amplifier --id arendeth_myskill --name "Stamina Cost Reduction" --type utility --cost-stamina -2 --unlock-level 3
python s2_skill_cli.py add-amplifier --id arendeth_myskill --name "Serrated" --type offensive --bonus bleed=1 --unlock-level 6
python s2_skill_cli.py set-amplifier --id arendeth_myskill --amplifier arendeth_myskill_serrated --bonus bleed=2 --description "Deeper cut."
python s2_skill_cli.py add-passive --id arendeth_myskill --name "Durability" --effect health_bonus_percent=0.1 --unlock-level 24
python s2_skill_cli.py add-passive --id arendeth_myskill --name "Fire Echo" --unlock-level 24
python s2_skill_cli.py add-spell-trigger --id arendeth_myskill --passive arendeth_myskill_fire_echo --source arendeth_myskill_fire_bolt --cast arendeth_myskill_fire_echo_burst --chance 0.25
python s2_skill_cli.py add-combat-mastery --id arendeth_myskill
python s2_skill_cli.py set-passive --id arendeth_myskill --passive arendeth_myskill_durability --append-effect dodge=0.1
python s2_skill_cli.py set-effect --id arendeth_myskill --ability arendeth_myskill_frost_bomb --clear heal
python s2_skill_cli.py set-ability --id arendeth_myskill --ability arendeth_myskill_frost_bomb --description "Detonate frost. ::damage ::damage_type."
python s2_skill_cli.py list-amplifiers --id arendeth_myskill
python s2_skill_cli.py cycle-images --id arendeth_myskill
python s2_skill_cli.py set-skill --id arendeth_myskill --version 1.1.0
python s2_skill_cli.py fill-stats-after-10 --id arendeth_myskill
python s2_skill_cli.py generate-icons --id arendeth_myskill --dry-run
python s2_skill_cli.py generate-icons --id arendeth_myskill --overwrite
python s2_skill_cli.py add-stacker --id arendeth_myskill --name Freeze --effect movement_speed=0.01 --max-stacks 50 --duration 3
python s2_skill_cli.py add-ability --id arendeth_myskill --ability-name "Frost Bomb" --unlock-level 8 --damage "[7,10]" --damage-type frost --target aoe_target --range 6 --stacker arendeth_myskill_freeze --stacker-count 2
python s2_skill_cli.py add-stacker --id arendeth_myskill --clone core_2_freeze --name "Deep Freeze" --bind-ability arendeth_myskill_frost_bomb --stacker-count 2
python s2_skill_cli.py add-creature --id arendeth_myskill --name "Stone Warden" --preset summon --health 80 --damage "[4,8]"
python s2_skill_cli.py add-ability --id arendeth_myskill --ability-name "Gale Claw" --no-milestone --damage "[4,8]" --damage-type physical --target health --range 2

python s2_skill_cli.py add-ability --id arendeth_myskill --ability-name "Summon Warden" --unlock-level 12 --summon arendeth_myskill_stone_warden --target tile --range 4
python s2_skill_cli.py add-item --id arendeth_myskill --name "Book of My Skill" --preset skill_book --unlock-level 44
python s2_skill_cli.py list-animations --search fireball
python s2_skill_cli.py list-anim-presets
python s2_skill_cli.py list-anim-presets --json
python s2_skill_cli.py produce-fx --id arendeth_myskill --name "Frost Wave FX" --art ice --bind-ability arendeth_myskill_frost_bomb --dry-run
python s2_skill_cli.py particles --id arendeth_myskill
python s2_skill_cli.py add-animation --id arendeth_myskill --clone 3 --name "Frost Bomb FX" --color 120,180,255 --bind-ability arendeth_myskill_frost_bomb
python s2_skill_cli.py list-abilities --search fireball
python s2_skill_cli.py list-races --search vampire
python s2_skill_cli.py dump-race 6
python s2_skill_cli.py list-control-actions --search tame
python s2_skill_cli.py list-buildings --search collegium
python s2_skill_cli.py add-training-building --id arendeth_myskill --template magic --name "My Hall"
python s2_skill_cli.py fix-buildings --scan
python s2_skill_cli.py fix-mods --scan
python s2_skill_cli.py fix-mods --apply --in-place

python s2_skill_cli.py tree --id arendeth_myskill
python s2_skill_cli.py validate --id arendeth_myskill
python s2_skill_cli.py write --id arendeth_myskill
python s2_skill_cli.py planner
```

`--unlock-level` writes the milestone (`rewards.ability` / `passive` / `amplifier` / `recipe`) in `milestones/<skill_id>/{level}_{Name}.json`. `--innate` writes `innate: true`, empty `requirements`, and `skill_id: ""` in `milestones/<skill_id>/innate_{Name}.json`, matching Arborborn; grant it with `entity-milestone` or an entity's `skills.milestones`. Same id on milestone and reward. Ability `skill` remains the owning skill id. Combat abilities default to `slots.offensive=1` and `slots.utility=1`. Self-buffs and transforms that should be shareable with allies need **at least one utility slot**. Do **not** add a `copy_to_party` amplifier — Leadership (companion skill) already grants Party Buff (`core_2_copy_to_party`) for that socket.

`add-ability` / `add-amplifier` / `add-passive` / `add-stacker` **replace** a row with the same id (and update its milestone). They do not append a duplicate. To change bonuses or a description without rebuilding the whole object, use `set-amplifier`, `set-passive`, `set-stacker`, `set-ability`, or `set-effect --clear`. `cycle-images` spreads placeholder `image` indexes so every icon is not 0. `set-skill --version` / `--author` / `--mod-description` patch `mod.json`. `set-skill --stat-points default|vanilla|after10|early|none` replaces `skills.json` `stat_points`. **A milestone and +1 statistic may share a level** — do not snap unlocks off stat levels. Vanilla Pyromancy interleaves empty post-10 levels, so a custom tree that puts a milestone on 12/15/18 can show the unlock with no +1. Default for new combat specs follows Skill Stat Rebalance (`3766934606`): **no +1 on 1–10**, then **every level 11–50**, plus a unique level-30 mastery (`add-combat-mastery`) of +10% strength/dexterity/endurance/intelligence/willpower. `new` adds that mastery unless `--no-combat` or `--no-mastery`. `fill-stats-after-10 --id arendeth_myskill` unions 11–50 into the existing list and leaves milestones in place. `early` is the old 2,4,5,7,8,10 then 11–50 schedule.

**Passives are paid.** Every skill starts at 10 for free, so a passive on 1–10 is free power. Custom trees put passives at **11+** and make them school-loop payoffs (`on_attack_stack`, `on_damage_type_stack`, `on_attack_cast`, consume, convert incoming damage), not generic +dodge/+resist. Abilities and amplifiers may sit on 1–10 as the starter kit. Innate/racial grants are the exception. Validate errors if a combat spec grants stats on 1–10, a non-innate passive before 11, or is missing the level-30 mastery.

`write` always emits `icon.png` (32×32, docs size) and placeholder tilesheets + `assets.json` so `mod.json` is not left pointing at missing `S.png`. Existing PNGs are not overwritten. Ability `image` / amplifier `image` / etc. are indexes on those sheets (0 from bottom left). Replace placeholders with `generate-icons --id arendeth_myskill --overwrite` (starts the local SD3.5 server on :1338 via `Tools\Shared`; `--no-sd` is explicit placeholders only; `--dry-run` prints prompts). Atlas cells are **128px** on a padded 16-col grid. Prefer txt2img (omit `--from-existing`) for new silhouettes; `--names` is comma-separated **display names** (exact match). Do not run SD from `write`. Pack Cursor / hand-made PNGs with `inject-icon --id <id> --name "Display Name" --png path.png` (optional `--sheet passives|amplifiers|…`). Official docs mention `{mod}/assets/gfx/skills`; this tool follows workshop Geomancy (`assets.json` + `assets/*.png`), not that gfx/ layout.

`starting_gear` (docs §5.1): `add-gear --id arendeth_myskill first=70:1,second=111:1` or `new --gear 70:1`. `first` only always grants; `first`+`second` is a character-create choice. Entity ids are strings. Every starting gear / race `items` id must be an **item** entity (has the `item` component) with a whole `amount` ≥ 1: `validate` and `audit-mods` error otherwise. A non-item (e.g. `core_2_Rope`, the placed rope) crashes every new character right after world gen. Docs `exp_sources` list is incomplete — `mine` unions every id seen in core_2 + workshop `skills.json` (e.g. `walk`, `carve`, `production`, Economy's `trade`, `track`, `pet`, `pickpocket`). Agriculture uses `production` + `production_action`. The skill start level key is **`start_level`** (core_2 crafting skills and Economy use 1); older builds of this tool wrote `level_start`, which the game ignores — `load`/`write` migrate it and `fix-mods` repairs shipped `skills.json`.

`mod.json` optional (docs §2): `--thumbnail thumbnail.png` (4:3 Steam PNG; `write` generates a placeholder), `steam_publish_id`, `disable_portraits` (global override — omit unless the human wants that).

Ability costs (docs §6.2): `--stamina` / `--health` / `--cost-item` (JSON `cost.item`) / `--cost-item-type` (corpses are `18`) / `--ammo` / `--min-range`. Requirements: `--require-one-of` → `requirements.one_of`, `--require-all` → `requirements.always`. Empty ability descriptions with `damage` get `::damage ::damage_type`.

`add-production-action --clone 5` copies vanilla `character.json` production_actions (docs §9). Milestone reward kind `production_action` / `grant-existing --kind production_action`. Producer component + “cannot be both destructible and repeatedly gathered” is out of scope — do not fake that.

Vanilla animation ids (`0`, `3` Fireball, `65` teleport) work without cloning. Particle JSON has no tilesheet field — do not invent a second atlas name and do not copy `particles.png`.

**Vision-capable agents (produce FX, then look at the PNGs):**

```powershell
python s2_skill_cli.py list-anim-presets --json
python s2_skill_cli.py produce-fx --id arendeth_myskill --name "Frost Wave" --bind-ability arendeth_myskill_frost_bomb --dry-run
```

That writes labeled PNGs under `Output/Soulash2/_fx_preview/<id>/<fx_id>/` — **never inside the shippable mod folder** (`strip.png` = each glyph with `tile_id` / delay, `playback.png` = time slices, `compare.png` = motion presets with the same tint, `manifest.json`). **Open those PNGs and inspect them.** If the color is wrong, rerun with `--art ice|blood|steam|fire|lightning|earth|poison|arcane`. If the motion is wrong, pick a `--preset` from `compare.png` / `list-anim-presets`. Then drop `--dry-run` to save into the spec. `--missing` fills every ability still using a vanilla numeric animation. `fx-preview --preset wave --art ice --compare` writes PNGs without touching a spec. Desktop: `particles` / `Run-S2Particles.bat` (Export PNGs).

`new-animation --preset wave --art ice --clone-impact --bind-ability …` is the non-visual shortcut. `list-particles --search blood` / `dump-animation 196` inspect vanilla JSON.

`clone-ability --source 15` (or `add-ability --clone Fireball`) copies vanilla/workshop ability JSON, retargets `id` to a string like `arendeth_myskill_fireball`, and sets `skill` to this spec. `image` resets to 0 for the placeholder sheets. Vanilla `animation` ids and `effects_keys` summon/stacker refs are left pointing at core_2 so they still work. `--clone-animation` also copies the FX JSON. `dump-ability 15` prints the original JSON without retargeting.

## Skill path planner

`python s2_skill_cli.py planner` (or `Run-S2Planner.bat`) opens a **tkinter desktop window**, not a browser. Studio **Planner** / `planner --web` is the old HTML page. It loads **core_2 + the mods enabled in** `%APPDATA%\WizardsOfTheCode\Soulash2\data\user_settings.json`, plus workshop/local folders you check. It overlays `character.json` (`max_potential`, playable races/ages) and every `skills.json` / `milestones`.

Potential math: each skill starts at 10 (free). Character creation picks 3 skills at 20 (30 from the shared pool). Remaining pool is `max_potential` (200 vanilla, 275 with the +75 overlay). Middle-aged and elder each add **+30** (60 over a lifetime). Race `ages.adult` / `ages.elder` are the year those stages hit; vampires with 10000/10000 do not get the bonus in play. Allocate sliders against Young / Middle / Elder budgets; the tree preview shows milestones and `+1 statistic` at the planned cap. Hover a skill or tree row (or click an unlock) for what it does — abilities fill `::damage` tokens, amplifiers use their description, passives list effects. Plans save under `Output/Soulash2/plans/`. `plan-dump --race 0 --stage elder` prints the budget as JSON.


Repeatable flags: `--effect` (ability and passive), `--bonus` (amplifier). Secondary values: `--effect statistic_percent=dexterity:0.1` or `--bonus bonus_crafting_unit=0.25:20`.

## Layout emitted by `write`

```
<id>/mod.json
     skills.json
     abilities/<Name>.json
     passives.json
     ability_amplifiers.json
     ability_stackers.json
     animations/<Name>.json
     assets.json
     icon.png
     assets/*.png
     entities/*.json
     buildings/*.json    # optional player training halls (enables)
     character.json      # merge-only races / control_actions / tags / production_actions
     npc/names/*.txt
     loot_exclude.json   # optional
     milestones/<skill_id>/{level}_{Name}.json
     .skillcreator/skill.json # private studio spec, not a game asset
```

Ability source filenames are preserved on import. Strip private `_file` metadata from emitted ability JSON; it belongs only in the private studio spec.

Follow Geomancy, not vanilla numeric ability files.

## Observed counts (not engine caps)

| Slot | Typical | Highest seen |
|---|---|---|
| Ability `effects` + `effects_keys` | 8 | 8 (F2 editor wipes past this; JSON may still load) |
| Amplifier `bonuses[]` | 2 | 3 workshop JSON |
| Passive `effects[]` | 3 | 6 workshop JSON |
| Ability amplifier slots (all colors) | 4 | higher exists in test JSON |
| Stacker `effects[]` | 2 | 2 |

True engine limits have **not** been found; the game does not publish caps. Docs say “as many as you want.” Table numbers are **observed** in vanilla, workshop JSON, and the F2 editor. The in-game editor may wipe or fail to show extra rows past those counts; JSON written by this CLI can still work. This tool does not cap you. Validate warns only when a count exceeds the highest observed.

## Confirmed working (Warlock NOTES + workshop)

Abilities: damage, DoT + `duration`, AoE, `lunge`+`target:tile` teleport, silence, self-buffs, `chain`, `clear_cooldowns`, stamina restore, fear/stun/vulnerable/slow.  
Amplifiers: `chain`, `knockback`, top-level `range`, `skill_level_damage`, `damage_as_life`, `increase_target_cooldown`, `damage_on_missing_health`, `cast_time`, `on_attack_cast`.  
Passives: `dodge`, `critical_hit`, `parry`, `damage_reduce`, `heal_on_kill`, `health_bonus_percent`, `damage_type_reduction`, `regeneration`. Multiple milestones at the same skill level work.

## Does not work / do not ship

- `control_action` as a **skill milestone** reward (use `add-control-action` on character.json instead)
- Passive `description` (ignored; tooltip comes from effects)
- `threesixty` / `infravision` / `sight` as passives (Warlock: no expected effect)
- `craft_persona` / city-worker companion tricks
- Unconfirmed exe-only effect ids

`darkvision` as a passive **is** valid (Dread Mask / docs: ignore infravision daylight penalty). Do not confuse it with `infravision`.

`apply_mode` is `party_only` or `solo_only` (not `only_party` — docs still say that). Secondary values matter: `heal_on_damage_type=electricity:0.2`.

File `ability_amplifiers.json` (docs wrongly say `amplifiers.json`). Live JSON + `patch_overlay.json` beat stale docs when they disagree.

`confidence: patch` (from `catalog/patch_overlay.json` plus live JSON) is dropdown-valid. `stamina_regen` / `bonus_damage` work on stackers.

## Races

Same spec / staging as skills. `write` emits a **partial** `character.json` (races, tags, control_actions, production_actions, custom_eq_slots, and preserved extra sections) plus `npc/names/*.txt` stubs. Never copy vanilla's whole character.json.

Playable minimum (docs §7.1): `id`, `name`, `description`, `playable`, `statistics`, `tags`, `names`, `items`, `recipes`. Civilization (`settlement`, `base_entities`, crests, maps) is optional. Starting kit is race `passives` + `abilities` (patch / workshop Draken), not skill milestones. Portraits (§7.2) are out of scope; glyphs are enough to ship playable. Description color tags like `[color=244,247,118,255]…[/color]` are vanilla flavor, optional.

Clone sources: Human `0` (full civ), Vampire `6` (`birth_cost`, aggression), Skeleton `17` (`collapse_on_leader_death`, `disabled_trading`). `--keep-id --overlay` patches a vanilla numeric id. Tag **9 is `alive`**, not humanoid; **2 = animal**, **4 = undead**.

`import-character-json --file <mod>/character.json` merges all supported entries by id without dropping per-entry fields, copies referenced NPC name files, and round-trips unknown top-level sections in studio state. This covers race settlement/age/entity/name data, custom tag options, production action gates such as `require_liquid: {type, amount}`, custom `control_actions`, and `custom_eq_slots`. `add-equipment-slot` authors a slot directly; `--birth-resource-type`, `--birth-max-population`, and repeatable `--tag-option` support the common structured cases. Studio **Races → Advanced character.json** imports a mod folder, or loads current entries for editing; matching ids replace and unrelated entries remain. Search and clone references should include installed `<game>/data/mods` as well as core and Workshop folders.

## Buildings

Player settlement halls that **train a skill** use `enables: ["<skill_id>"]` (vanilla Collegium Magicae / Dojo). `add-training-building --template magic|combat|farm` clones 389 / 387 / 404, retargets id/name/`enables`, and fills 0.10 fields (`occupation_image`, vampire race `"6"`, `produces`). `write` emits `buildings/*.json`. Do **not** invent `.smap` maps — `copy-building-map` copies an existing file only.

0.10 player-building contract: `allow_player`, `race: "-1"`, `occupation_image`, `occupation_per_race` including vampire `"6"`, `produces` (array; `[]` is fine), `workers`. `min_area` / `group` are **not proven required**: NPC town buildings (e.g. Shaman's Hut `98`) omit them, but all 91 vanilla player halls set them (`group` = `building_groups.json` build-menu tab, trainer halls use `"military"`, `min_area` 30 military / 20 crafters). `type: "military"` is a **different** field: 58 NPC barracks use it without `group`, and the 11 vanilla military trainer halls (Dojo 387, Collegium 389, …) set `type` **and** `group`. Scans report missing `group`/`min_area` as `(optional)`. NPC buildings may also omit `race` and `tier`. Occupation NPCs need `experience_gainer` and must not list `consumer` without a `consumer` object. Trainer begin conversations should include `core_2_train_1`.

**Building maps (`.smap`).** Header is `map id|name|building id|w|h|…`: field 1 is the map's own unique id — special locations pick maps by it (`locations.json` → `special[].scenarios[].building_maps[]{count, ids, mode, placement}`; all 4169 core_2 references resolve this way), field 3 links to `buildings/*.json` `id`; vanilla filenames are `<map id>_…_<building id>.smap`. Vanilla trainer halls (Dojo 387, Collegium 389, …) ship **no** map — players lay them out; only Divine Monastery 482 has maps. `check-building-maps [mod]` reports broken links, map-id collisions (many arendeth halls reused vanilla map id `39`), duplicate files, and map-bearing player halls without `group`/`min_area`. `relink-building-maps <mod> [--apply]` gives each map a unique id, the right building id and the vanilla filename (dry run by default, backups under `Output/Soulash2/_building_map_backups/`). `link-building-map --mod <mod> --map <file.smap> --building <id> [--apply]` drops an existing/exported map into a mod already linked. `errors.log` `Unable to find building of id <modded id>` is **boot-order noise, not a broken map**: the game first initialises with only `core_2`, logs one line per building JSON of each enabled mod (in user_settings order; a duplicated id logs twice), then reloads with the full mod list, and that second pass is clean. Verified 2026-10-22 by moving `arendeth_astral_magic/building_maps` aside — the line for `astral_magic_hall` stayed. Judge mod load errors from the lines after the second `Loading mods:` block only.

`building-guide --search wizard` shows the local docs section, vanilla training templates, and matching examples from `<game>/data/mods`. Building search and cloning include installed mods, `core_2`, and Workshop content. The Studio Buildings tab shows the same references and has a safe-field repair for buildings in the current spec.

`fix-buildings --scan` reports Officers! / Battlemages / Silkworm Farm gaps by default. Pass a mod folder, or use `fix-buildings --installed --scan` to inspect user mods under `<game>/data/mods`. `--apply` writes Output copies; `--in-place` also patches selected source folders and backs up changed generic building files under `Output/Soulash2/_building_fix_backups/`. The default is scan-only. Steam can overwrite Workshop content.

`fix-mods` is the general 0.9→0.10 fixer for **workshop** (default) or `--enabled` mods. It patches `game_required`, `S.png`/`S2.png` → `icon.png`, `amplifiers.json` → `ability_amplifiers.json`, `only_party` → `apply_mode`, passive `movement_speed` → `move_speed`, amplifier `stamina_cost`/`range`/`cooldown` bonuses lifted to top-level fields, 0.10 building fields, and orphan `consumer` / missing `experience_gainer`. `--apply` snapshots to `Output/Soulash2/_fixed/<id>/`; `--in-place` patches the folder the game loads. Does **not** invent `.smap` maps, copy `particles32`, or `install`. Control-action *milestones* match vanilla Hunting/Necromancy; the fixer only writes a missing custom `character.json` control_action.

Procedural terrain maps are supported in both the Studio and CLI. They can be searched and cloned from `core_2`, installed mods, and Workshop content, or authored from JSON. `write` emits `procedural_maps/*.json`; importing a mod preserves the existing `procedual_maps` spelling when that is the source folder. Static settlement/civilization `.smap` files remain copy-only.

## Assets (tilesheets, sounds)

**Tilesheets are per mod** (changelog 0.7.7): a mod that lists a sheet under a vanilla name (`glyph32`, `items`, `abilities`, …) draws *its own* content from *its own* sheet; otherwise core_2's applies. Indexes count from the **bottom-left** cell (verified: core_2 Fireball `image: 42`). So a vanilla index inside a mod that ships a small sheet points past its end — e.g. Arborborn's `core_2_Wicker_Doll` override uses glyph `2364` / item `1031` against Arborborn's 48-cell `glyph32` / 16-cell `items`. (Older notes here said such sheets replace vanilla art game-wide; the exe/changelog say per mod.) Missing sheet files make the game skip drawing ("Skipping draw for ability with unknown or missing tilesheet"). Sheet `file` paths are relative to the mod folder; `../core_2/...` only works next to core_2, not from Workshop.

```powershell
python s2_skill_cli.py check-assets                      # enabled mods; or name mods / core_2 / --installed
python s2_skill_cli.py list-sheets --mod arendeth_arborborn --own
python s2_skill_cli.py show-cells --mod arendeth_arborborn --sheet abilities --index 0-15
```

`check-assets` checks every sheet file exists, is a PNG, and divides into its `tiles` grid, and every index field (ability/amplifier/passive/stacker/skill `image`, entity glyph frames / `light_source.lit_image` / `item.image` / `persona.occupationIconIndex`, building `image` / `occupation_image`, production action `image`, race crests, animation `tile_id`) against the sheet it really resolves to. `show-cells` writes a labelled PNG (Output/Soulash2/_asset_preview/) — vision agents should open it to confirm an icon before setting `image`. core_2 itself checks clean (its 14 glyph `6462548` entities and uneven `portraits` grid are whitelisted vanilla quirks).

**Sounds.** The exe's per-mod `assets.json` loader reads `sounds` (walk/equipment/ui/events/screens/combat, `music`) alongside `tilesheets`/`textures`, so mods can add sounds — but no shipped mod does yet: treat as engine-supported, test in game. Combat sounds are `sounds.combat[] {id, name, file}` (file relative to the mod; vanilla ids `"1"`–`"168"`, so use prefixed ids); animations play them with `"sound": {"id": ..., "volume": 100}` (`"0"` / `"-1"` = none). Production actions instead take a game-root path (`data/mods/<mod>/assets/sfx/x.ogg`), which only resolves for mods under `data/mods`. Ship Ogg Vorbis (`.ogg`), like every vanilla sfx.

```powershell
python s2_skill_cli.py list-sounds --search bash
python s2_skill_cli.py add-sound --id arendeth_myskill --file D:\audio\rune_boom.ogg --name "Rune Boom" --bind-animation arendeth_myskill_boom_fx --volume 80
python s2_skill_cli.py list-sounds --id arendeth_myskill
```

`add-sound` checks the file is Ogg/WAV, copies it to `assets/sfx/`, registers it in the spec's `assets.json`, and `write` re-copies it if the output folder lacks it. `validate` / `check-assets` flag missing files, duplicate or numeric ids, animation sound ids no loaded mod defines (or that come from a mod you don't require), and production-action sound paths that don't exist.

## Weather

`<mod>/weather.json` is an array (docs §11). Fields: `id` (string), `name`, `animation`, `animation_tick`, `ability[]`, `ability_trigger_time`, `disabled_under_roof`, `duration`, `trigger_every`, `trigger_chance` (0–1), `biomes[]`, `trigger_message`; optional `change_entities_on_start` `[{from, to: id|[ids]}]` (0.10.0), `force_night` (Blood Moon), `thirst_multiplier` (Heatwave 4.0), `stop_on_map_exit` (exe-only, untested). Empty `biomes` = never rolls on its own; start it from an ability `effects_keys.summon_weather: "<weather id>"` (vanilla Summon Rain → `"1"`). Ids `1`–`17` are vanilla and replace them; use prefixed ids.

```powershell
python s2_skill_cli.py list-weather --search rain
python s2_skill_cli.py dump-weather "Blood Moon"
python s2_skill_cli.py add-weather --id arendeth_myskill --name "Ashfall" --clone 7 --animation 190 --ability 142 --biome desert --chance 0.1 --change core_2_Dried_Short_Grass=1 --ignore-roof --summon-ability arendeth_myskill_call_ashfall
python s2_skill_cli.py list-weather --id arendeth_myskill
python s2_skill_cli.py remove-weather --id arendeth_myskill --weather arendeth_myskill_ashfall
```

`validate` checks required fields/types, chance range, ability/animation/entity references (vanilla numeric ids pass), unknown biomes, vanilla id replacement, and the exe rule that `change_entities_on_start.to` is a string or array of strings. Importing a mod folder carries `weather.json`; `write` emits it.

## Auditing installed mods together

`audit-mods` (default: the mods enabled in `user_settings.json`; `--installed` for every folder; or name mods) indexes core_2 plus the set and reports: ids defined twice across mods or inside one mod, rows replacing core_2 (`--verbose`; often deliberate edits like Arborborn's Dark Druid loot), references to ids no loaded mod defines (milestone rewards incl. wrong reward kind, entity `skills.milestones` / `ability_user`, `effects_keys` transform/summon/stacker/summon_weather, amplifier stacker bonuses, spell triggers, passive `ability_extend_duration` ability ids, building occupations/`enables`, weather abilities/entities), starting gear (`skills.json` `starting_gear` first/second) and race `items` that are not **item** entities (e.g. `core_2_Rope` is the placed rope object; the game throws `ECStorage::get: entity N is not in the store` building the kit and crashes on new character right after world gen), and file shapes the loader rejects (`skills.json` as a bare object → "Failed to load mod … type must be array"; `fix-mods --apply` wraps it). It also flags duplicate keys inside one JSON object (only the last survives), references that only resolve through a mod missing from `mods_required`, and a building `occupation` set to a job title: `occupation` / `occupation_per_race` must be the worker **entity id** (Collegium 389 → `457`); `persona.occupation` ("Wizard") is display text. Read-only.

`check-building-maps` also validates `locations.json`: top-level keys must be `cultures` / `settlements` / `special` / `unknown_special_images` (a `locations` key is ignored by the game), each special needs `id, name, biomes, difficulty, image, algorithm, scenarios`, and every `building_maps` id must be a `.smap` header map id somewhere. `relink-building-maps` refuses to rename a map id that `locations.json` uses.

`game-log` splits `logs/errors.log` into load passes, hides the core_2-only boot pass "Unable to find building" noise, and annotates known messages.

## Spell logic

The engine-supported event rule is passive `trigger_ability_on_cast`: `value` is the triggering ability id, `secondary_value` is the ability to cast, and `third_value` is a chance from 0 to 1. The Studio Add tab can add multiple rules to one passive; the CLI can append one with `add-spell-trigger`. `validate` checks chance ranges, local ability references, independently rolled branch totals, and recursive trigger cycles. Triggered payload abilities do not need their own milestone unless they should also be directly selectable.

Current data confirms `magic_power_per_entity` as an **amplifier bonus** (`value` = counted entity id, `secondary_value` = power per entity), as in core_2 Hell. The catalog lists a documented ability form but has no vanilla ability example; `effects_keys.magic_power_per_entity` and a passive effect of the same name are not confirmed. Validation warns on those placements. A passing JSON/schema check cannot prove an experimental spell loop is balanced or safe in live combat; recursive chains and summon timing still need in-game review.

Example confirmed slot: `python s2_skill_cli.py add-amplifier --id arendeth_myskill --name "Echo Scaling" --type offensive --bonus magic_power_per_entity=arendeth_myskill_echo:1 --range 10 --unlock-level 20`. The Studio amplifier form exposes `secondary_value` for this encoding.

## Not implemented in this tool

Do not fake these. Clone vanilla JSON with `--from-json` if the human needs them:

- Static civ/building `.smap` authoring, world events (`events/settlement|wilderness/*.json`, 0.10.0), special-location authoring (only checked, see above), portraits, Steam Workshop publishing
- Producer entities (docs §9: a producer cannot be both destructible and repeatedly gathered)

## Checks before you stop

1. `explain` every non-obvious effect you used.
2. `validate --id <id>` is OK or only unused-milestone / beyond-observed-count warnings you understand.
3. `write --id <id>` succeeded.
4. Tree has a milestone for every player-facing ability, passive, and amplifier. Triggered payloads, usable-item abilities, entity `ability_user` kits, stacker casts, racial starting kits, and innate grants are valid no-milestone cases.
5. Summon/construct/transform ids exist in `entities/` (or are vanilla numeric ids). Transform forms need their own unique `ability_user` kit (the engine replaces the player's skills for the duration). Do not fill a form with vanilla Lightning Nova / Cyclone clones.
6. You did **not** install unless asked.
