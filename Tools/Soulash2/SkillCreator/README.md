# Soulash 2 Skill Creator

Out-of-game skill / ability / amplifier / milestone tool. Lives under `D:\games\Ai assisted toolkit` so Steam Soulash 2 updates cannot wipe it.

**Another AI implementing a mod:** read [`AGENTS.md`](AGENTS.md) first. Use the CLI, validate, then `write`. Do not `install` unless the human asks.

Layout follows **workshop Geomancy / Electromancy / Warlock**. Effect keys come from official docs + vanilla `core_2` + workshop skill mods + **`Soulash 2.exe` string tables**. EXE-only names are stored with `confidence: unconfirmed`.

## Quick start

```powershell
cd D:\games\Ai assisted toolkit\Tools\Soulash2\SkillCreator

python s2_skill_cli.py mine
python s2_skill_cli.py validate --vanilla
python s2_skill_cli.py list-effects --kind amplifier
python s2_skill_cli.py explain pull_target

python s2_skill_cli.py new --id skilltest --name "Skill Test"
python s2_skill_cli.py add-gear --id skilltest first=70:1,second=111:1
python s2_skill_cli.py add-stacker --id skilltest --name Freeze --effect movement_speed=0.01 --max-stacks 50 --duration 3
python s2_skill_cli.py add-ability --id skilltest --ability-name "Frost Bomb" --unlock-level 8 --damage "[7,10]" --damage-type frost --target aoe_target --range 6 --stamina 6 --stacker skilltest_freeze --stacker-count 2
python s2_skill_cli.py add-amplifier --id skilltest --name "Stamina Cost Reduction" --type utility --cost-stamina -2 --unlock-level 3
python s2_skill_cli.py add-passive --id skilltest --name "Durability" --effect health_bonus_percent=0.1 --unlock-level 24
python s2_skill_cli.py add-creature --id skilltest --name "Stone Warden" --preset summon --health 80 --damage "[4,8]"
python s2_skill_cli.py add-ability --id skilltest --ability-name "Summon Warden" --unlock-level 12 --summon skilltest_stone_warden --target tile --range 4
python s2_skill_cli.py add-item --id skilltest --name "Book of Skill Test" --preset skill_book --unlock-level 44
python s2_skill_cli.py clone-entity --id skilltest --source 2893 --name "Test Golem"
python s2_skill_cli.py list-abilities --search fireball
python s2_skill_cli.py clone-ability --id skilltest --source 15 --name "Fireball" --unlock-level 10
python s2_skill_cli.py list-races --search vampire
python s2_skill_cli.py add-race --id skilltest --name Stonefolk --stat strength=2 --no-settle
python s2_skill_cli.py list-buildings --search collegium
python s2_skill_cli.py add-training-building --id skilltest --template magic --name "Test Hall"
python s2_skill_cli.py list-entities --id skilltest
python s2_skill_cli.py list-entities --search golem
python s2_skill_cli.py tree --id skilltest
python s2_skill_cli.py fill-stats-after-10 --id skilltest
python s2_skill_cli.py generate-icons --id skilltest --dry-run
python s2_skill_cli.py validate --id skilltest
python s2_skill_cli.py add-animation --id skilltest --clone 3 --name "Frost Bomb FX" --bind-ability skilltest_frost_bomb
python s2_skill_cli.py new-animation --id skilltest --preset nova --name "Steam Burst FX" --art steam --bind-ability skilltest_steam_burst
python s2_skill_cli.py generate-anim-art --id skilltest --animation skilltest_steam_burst_fx --theme steam
python s2_skill_cli.py write --id skilltest

python s2_skill_cli.py editor --id skilltest
python s2_skill_cli.py planner
python s2_skill_cli.py particles --id skilltest
.\Run-S2Planner.bat
.\Run-S2Particles.bat
```

`write` validates first and aborts on errors unless `--force`. It emits a mod under `Tools/Output/Soulash2/<id>/` including `ability_stackers.json`, `animations/`, `assets.json`, and a 32×32 `icon.png` (replacing the old `S.png` pointer). If `mod.thumbnail` is set, `write` also emits a 4:3 placeholder PNG. Existing PNGs are never overwritten. If the spec has races, control actions, or production actions, `write` also emits a merge-only `character.json` plus `npc/names/*.txt` stubs. `install` copies into the game `data/mods/` folder and **requires `--yes`** — only when the human asks.

## Icons, tilesheets, animations

- `mod.json` uses `"icon": "icon.png"`. `write` generates a 32×32 placeholder if the file is missing. Optional `thumbnail` is a 4:3 Steam PNG (docs §2).
- `assets.json` plus `assets/*.png` placeholder sheets (`skills`, `abilities`, `amplifiers`, `passive_skills`, `stackers`) so `image: 0` has something to point at. Indexes start at the **bottom left**, matching workshop Geomancy (not the docs `{mod}/assets/gfx/skills` path).
- `generate-icons --id skilltest --overwrite` replaces those placeholders with thematic 32×32 tiles packed into the same sheets (local SD server; `--no-sd` for procedural; `--dry-run` prints prompts). `write` does not run SD.
- `list-animations --search fireball` then `add-animation --clone 3 --bind-ability …`. Or set `--animation 0` / `3` / `65` to reuse vanilla FX. Docs: copy an existing animation rather than building one from scratch.
- `new-animation --preset nova --art steam` clones that motion and **tints vanilla particles32 glyphs**. It does not copy `particles.png`. Vision-capable agents should use `produce-fx --dry-run` (writes `strip.png` / `playback.png` / `compare.png` + JSON), look at the PNGs, then drop `--dry-run` to save. `fx-preview` writes PNGs without a spec. Desktop: `particles` / `Run-S2Particles.bat`.

`skills.json` `stat_points` is the +1 statistic schedule. A milestone and a statistic **may share a level**. New combat specs follow Skill Stat Rebalance: no +1 on 1–10, then every level 11–50, plus a unique level-30 mastery (+10% all five attributes). Vanilla Pyromancy skips some post-10 levels; `fill-stats-after-10` unions 11–50 without moving unlocks. Presets: `set-skill --stat-points default|rebalance|after10|early|vanilla|none`.

## Clone an ability

`list-abilities --search fireball` then `clone-ability --source 15 --unlock-level 10` (or `add-ability --clone Fireball`). That copies the vanilla/workshop JSON, gives it a **string** id (`skilltest_fireball`), and sets `skill` to this spec. `image` is reset to 0 so it fits the placeholder tilesheets. Vanilla animation ids (`"3"`) and `effects_keys` that point at core_2 summons/stackers are left as-is. `--clone-animation` also copies the FX file. `dump-ability 15` still prints the original JSON if you want to inspect it.

`--clone` on `add-ability` accepts the same overrides as a from-scratch ability (`--damage`, `--effect`, `--animation`, `--stamina`, `--cost-item`, …). Ability descriptions may use `::damage` / `::damage_type` (docs §6.2). JSON cost keys: `stamina`, `health`, `item` (entity), `item_type`, `ammo`. Requirements use `one_of` / `always` (docs say require_one_of / require_all).

Official docs lag live JSON in a few places this tool already follows: file name is `ability_amplifiers.json` not `amplifiers.json`; passives use `apply_mode: party_only|solo_only` not `only_party`; extra exp_sources `walk` / `carve` / `production` exist in vanilla. Prefer live `core_2` + overlay over stale docs.

`starting_gear` is `add-gear` / `new --gear` / studio **Skill** tab. `add-production-action --clone 1` writes `character.json` production_actions (docs §9). `grant-existing --kind production_action` unlocks a vanilla action as a milestone. Producer tiles are still out of scope.

## Items and creatures

Abilities that summon, construct, or teach a skill need entity JSON. Create them in the same spec:

- `add-item --preset skill_book|weapon|usable` — Geomancy-style book sets `usable.skill_p` to this skill; `--unlock-level` also grants a `recipe` milestone
- `add-creature --preset summon|enemy|tile` — ally summons use player tag `5`; `--summon-ability` writes `effects_keys.summon`
- `clone-entity --source 2893` (or a name like `Golem`) copies vanilla/workshop JSON and retargets the id
- `list-entities --search wolf` searches `core_2` + workshop skill mods

The studio **Items / Creatures** tab does the same thing.

## Races

`list-races --search vampire` then `clone-race --source 6`, or `add-race --name Stonefolk --stat strength=2 --no-settle`. `dump-race 6` prints the vanilla JSON. `list-control-actions --search tame` then `add-control-action --clone core_2_tame --tag 4`. `--base-entity adult=my_adult` is the civ NPC without maps/buildings.

Vampire `6` and Skeleton `17` are the templates for `birth_cost` / `collapse_on_leader_death` / `disabled_trading`. `--keep-id --overlay` patches a vanilla numeric id (workshop Draken). Portraits are out of scope (a race is playable with glyphs). Studio tabs **Skill**, **Races**, and **Buildings**.

## Buildings

`list-buildings --search collegium` then `add-training-building --template magic` (or `combat` / `farm`) clones a vanilla player hall and sets `enables` to this skill. That is how settlement trainers work in 0.10 (Collegium Magicae, Dojo). `write` emits `buildings/*.json`. Do not invent `.smap` maps.

`fix-buildings --scan` checks Officers!, Battlemages, and Silkworm Farm against the current player-building API. `--apply` writes fixed copies under Output; `--in-place` also patches the workshop folder.

`fix-mods --scan` checks every workshop mod (or `--enabled`, or named Steam ids) for 0.10 rot: `game_required`, missing `icon.png`, old `amplifiers.json` / `only_party` / encoding, and the same building/NPC gaps. `--apply` writes snapshots under `Output/Soulash2/_fixed/<id>/`. `--in-place` patches the workshop folder the game loads (Steam can overwrite it). Hydromancy folders are skipped. This does not `install` into `data/mods/`.

## Adding an amplifier

Creating an amplifier also writes the milestone that unlocks it (`rewards.amplifier`). Abilities get `slots` so the amplifier color can be socketed. `--grant-existing core_2_burn` makes a Pyromaniac-style milestone that grants a vanilla amplifier.

**Same id replaces.** `add-amplifier` / `add-passive` / `add-stacker` / `add-ability` update the existing row instead of duplicating (duplicate ids are a validate error). To change one field without rebuilding the object:

```powershell
python s2_skill_cli.py set-amplifier --id skilltest --amplifier skilltest_serrated --bonus bleed=2 --description "Deeper cut."
python s2_skill_cli.py set-passive --id skilltest --passive skilltest_durability --append-effect dodge=0.1
python s2_skill_cli.py set-effect --id skilltest --ability skilltest_frost_bomb --clear heal
python s2_skill_cli.py set-ability --id skilltest --ability skilltest_frost_bomb --description "Detonate frost."
python s2_skill_cli.py list-amplifiers --id skilltest
python s2_skill_cli.py cycle-images --id skilltest
python s2_skill_cli.py set-skill --id skilltest --version 1.1.0
```

Validate also warns on encoding mistakes learned from live rebuilds: amplifier `stamina_cost` belongs at top-level `cost_stamina`; `knockback` is integer tiles; `heal`+`damage` should usually be `damage_as_life`; passives use `move_speed` not `movement_speed`; `summon_count` above 24 is almost certainly wrong.

## Adding a stacker

Stackers are **not** skill-tree unlocks. `add-stacker` writes an `ability_stackers.json` entry. Bind it with `--bind-ability` or `add-ability --stacker <id> --stacker-count 2`. `--clone core_2_freeze` copies a vanilla/workshop stacker. `--apply-caster` makes it a self buff; default is a debuff on the target. Amplifiers can also apply a stacker: `--bonus stacker=myskill_freeze:1`.

## Catalog

`catalog/effects.json`, `catalog/enums.json`, `catalog/exe_strings.json`, `catalog/EFFECTS.md` are generated by `mine` from docs, `core_2`, workshop skill mods, `Soulash 2.exe` strings, and `catalog/patch_overlay.json`. Re-run after game or workshop updates. Patch overlay ids (`confidence: patch`) are dropdown-valid — they catch fields official docs still omit (`apply_mode`, stacker `stamina_regen` / `bonus_damage`, `heal_on_damage_type` secondary ratio).

`explain bleed` (and the studio **Effect info** rail) show what an effect does and where it is valid: ability `effects`, ability `effects_keys`, amplifier `bonuses`, amplifier top-level fields, passives, or stackers. Click a catalog row or change an Add-tab dropdown to fill the box.

Observed counts (vanilla typical / highest seen): **8** ability effects+keys, **2** / **3** amplifier bonuses, **3** / **6** passive effects, **4** amplifier slots on an ability (higher in test JSON), **2** stacker per-stack bonuses. The F2 editor may wipe extra rows past those counts; JSON authored here can still work. The game does not publish engine caps. Validate warns only when you go past the highest observed. The studio does not block you.

## Skill path planner

`python s2_skill_cli.py planner` (or `Run-S2Planner.bat`) opens a **desktop window**. It overlays **core_2 + your enabled mods** (from `%APPDATA%\WizardsOfTheCode\Soulash2\data\user_settings.json`). Pick a race, mark 3 starting skills, drag potential sliders, and switch Young / Middle / Elder. Middle-aged and elder each add +30 max potential (60 over a lifetime); race `ages` decide when those stages hit. The tree preview shows milestones and +1 statistic at the planned cap. Hover a skill or unlock (or click a tree row) to read what it does. Saved plans live in `Output/Soulash2/plans/`. `planner --web` is the old HTML page inside Studio.
