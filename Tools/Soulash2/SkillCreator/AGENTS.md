# Skill Creator — agent handoff

Use this tool to **author Soulash 2 skill mods**. Drive it with the CLI. Prefer Geomancy / Electromancy / Warlock layout over inventing schema. Do not `install` unless the human explicitly asks.

Working directory:

```
D:\games\Ai assisted toolkit\Tools\Soulash2\SkillCreator
```

Staging (safe): `D:\games\Ai assisted toolkit\Tools\Output\Soulash2\<id>\`  
Live game mods: `E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\` — **write-only via `install --yes`**

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

`--unlock-level` writes the milestone (`rewards.ability` / `passive` / `amplifier` / `recipe`) in `milestones/<skill_id>/{level}_{Name}.json`. Same id on milestone, reward, and the ability/passive/amplifier. Ability `skill` is set to `skill_id`. Combat abilities default to `slots.offensive=1` and `slots.utility=1`. Self-buffs and transforms that should be shareable with allies need **at least one utility slot**. Do **not** add a `copy_to_party` amplifier — Leadership (companion skill) already grants Party Buff (`core_2_copy_to_party`) for that socket.

`add-ability` / `add-amplifier` / `add-passive` / `add-stacker` **replace** a row with the same id (and update its milestone). They do not append a duplicate. To change bonuses or a description without rebuilding the whole object, use `set-amplifier`, `set-passive`, `set-stacker`, `set-ability`, or `set-effect --clear`. `cycle-images` spreads placeholder `image` indexes so every icon is not 0. `set-skill --version` / `--author` / `--mod-description` patch `mod.json`. `set-skill --stat-points default|vanilla|after10|early|none` replaces `skills.json` `stat_points`. **A milestone and +1 statistic may share a level** — do not snap unlocks off stat levels. Vanilla Pyromancy interleaves empty post-10 levels, so a custom tree that puts a milestone on 12/15/18 can show the unlock with no +1. Default for new combat specs follows Skill Stat Rebalance (`3766934606`): **no +1 on 1–10**, then **every level 11–50**, plus a unique level-30 mastery (`add-combat-mastery`) of +10% strength/dexterity/endurance/intelligence/willpower. `new` adds that mastery unless `--no-combat` or `--no-mastery`. `fill-stats-after-10 --id arendeth_myskill` unions 11–50 into the existing list and leaves milestones in place. `early` is the old 2,4,5,7,8,10 then 11–50 schedule.

**Passives are paid.** Every skill starts at 10 for free, so a passive on 1–10 is free power. Custom trees put passives at **11+** and make them school-loop payoffs (`on_attack_stack`, `on_damage_type_stack`, `on_attack_cast`, consume, convert incoming damage), not generic +dodge/+resist. Abilities and amplifiers may sit on 1–10 as the starter kit. Innate/racial grants are the exception. Validate errors if a combat spec grants stats on 1–10, a non-innate passive before 11, or is missing the level-30 mastery.

`write` always emits `icon.png` (32×32, docs size) and placeholder tilesheets + `assets.json` so `mod.json` is not left pointing at missing `S.png`. Existing PNGs are not overwritten. Ability `image` / amplifier `image` / etc. are indexes on those sheets (0 from bottom left). Replace placeholders with `generate-icons --id arendeth_myskill --overwrite` (starts the local SD3.5 server on :1338 via `Tools\Shared`; `--no-sd` is explicit placeholders only; `--dry-run` prints prompts). Atlas cells are **128px** on a padded 16-col grid. Prefer txt2img (omit `--from-existing`) for new silhouettes; `--names` is comma-separated **display names** (exact match). Do not run SD from `write`. Pack Cursor / hand-made PNGs with `inject-icon --id <id> --name "Display Name" --png path.png` (optional `--sheet passives|amplifiers|…`). Official docs mention `{mod}/assets/gfx/skills`; this tool follows workshop Geomancy (`assets.json` + `assets/*.png`), not that gfx/ layout.

`starting_gear` (docs §5.1): `add-gear --id arendeth_myskill first=70:1,second=111:1` or `new --gear 70:1`. `first` only always grants; `first`+`second` is a character-create choice. Entity ids are strings. Docs `exp_sources` list is incomplete — live JSON also has `walk`, `carve`, `production` (Agriculture uses `production` + `production_action`).

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
     skill.json          # studio spec; not copied on install
```

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

Same spec / staging as skills. `write` emits a **partial** `character.json` (races, optional tags, control_actions) plus `npc/names/*.txt` stubs. Never copy vanilla's whole character.json.

Playable minimum (docs §7.1): `id`, `name`, `description`, `playable`, `statistics`, `tags`, `names`, `items`, `recipes`. Civilization (`settlement`, `base_entities`, crests, maps) is optional. Starting kit is race `passives` + `abilities` (patch / workshop Draken), not skill milestones. Portraits (§7.2) are out of scope; glyphs are enough to ship playable. Description color tags like `[color=244,247,118,255]…[/color]` are vanilla flavor, optional.

Clone sources: Human `0` (full civ), Vampire `6` (`birth_cost`, aggression), Skeleton `17` (`collapse_on_leader_death`, `disabled_trading`). `--keep-id --overlay` patches a vanilla numeric id. Tag **9 is `alive`**, not humanoid; **2 = animal**, **4 = undead**.

## Buildings

Player settlement halls that **train a skill** use `enables: ["<skill_id>"]` (vanilla Collegium Magicae / Dojo). `add-training-building --template magic|combat|farm` clones 389 / 387 / 404, retargets id/name/`enables`, and fills 0.10 fields (`occupation_image`, vampire race `"6"`, `produces`). `write` emits `buildings/*.json`. Do **not** invent `.smap` maps — `copy-building-map` copies an existing file only.

0.10 player-building contract: `allow_player`, `race: "-1"`, `occupation_image`, `occupation_per_race` including vampire `"6"`, `produces` (array; `[]` is fine), `workers` / `min_area` / `group`. Occupation NPCs need `experience_gainer` and must not list `consumer` without a `consumer` object. Trainer begin conversations should include `core_2_train_1`.

`fix-buildings --scan` reports Officers! / Battlemages / Silkworm Farm gaps. `--apply` writes Output copies; `--in-place` also patches the workshop folder the game loads. Steam can overwrite workshop.

`fix-mods` is the general 0.9→0.10 fixer for **workshop** (default) or `--enabled` mods. It patches `game_required`, `S.png`/`S2.png` → `icon.png`, `amplifiers.json` → `ability_amplifiers.json`, `only_party` → `apply_mode`, passive `movement_speed` → `move_speed`, amplifier `stamina_cost`/`range`/`cooldown` bonuses lifted to top-level fields, 0.10 building fields, and orphan `consumer` / missing `experience_gainer`. `--apply` snapshots to `Output/Soulash2/_fixed/<id>/`; `--in-place` patches the folder the game loads. Does **not** invent `.smap` maps, copy `particles32`, or `install`. Control-action *milestones* match vanilla Hunting/Necromancy; the fixer only writes a missing custom `character.json` control_action.

## Not implemented in this tool

Do not fake these. Clone vanilla JSON with `--from-json` if the human needs them:

- Civ maps, world events, weather, portraits, Steam Workshop publishing
- Producer entities (docs §9: a producer cannot be both destructible and repeatedly gathered)

## Checks before you stop

1. `explain` every non-obvious effect you used.
2. `validate --id <id>` is OK or only unused-milestone / beyond-observed-count warnings you understand.
3. `write --id <id>` succeeded.
4. Tree has a milestone for every ability, passive, and amplifier (racial starting kits, innate grants, and transform/summon `ability_user` kits are exceptions — those use `add-ability --no-milestone`).
5. Summon/construct/transform ids exist in `entities/` (or are vanilla numeric ids). Transform forms need their own unique `ability_user` kit (the engine replaces the player's skills for the duration). Do not fill a form with vanilla Lightning Nova / Cyclone clones.
6. You did **not** install unless asked.
