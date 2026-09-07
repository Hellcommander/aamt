# Per-mod merge rules

AI (or a human) **writes** a JSON rule once under `profiles/merge_rules/`.  
The tool **applies** it every run — no rewiring by hand/AI each merge.

## Add a mod

1. Create `profiles/merge_rules/<id>.json`
2. Set `match` to folder-name substrings
3. Set `priority` / `class_priority` / `enabled` / path skips from conflict analysis
4. Re-run the playground/merger

### Fields

| Field | Values | Meaning |
|--------|--------|---------|
| `enabled` | bool | `false` skips the mod (kept in profile for later) |
| `priority` | int | Higher wins file/content conflicts (applied later) |
| `class_priority` | int | Higher wins class-tree conflicts (defaults to `priority`) |
| `skip_overlay_prefixes` | string[] | Paths this mod will not write (e.g. PC hubs / gameengine) |
| `conflict_merge` | bool | Overlapping `.dbr` files field-merge (keep unique keys from both) |
| `conflict_merge_prefixes` | string[] | Limit field-merge to these path prefixes |
| `prefer_field_substrings` | string[] | On conflicts, prefer this mod if the field name matches |
| `keep_base_field_substrings` | string[] | On conflicts, keep already-merged (other mod) value |
| `mode` | `content` / `class` / `portal` | Kitchen-sink classification |
| `quest_remap` | bool | Namespace quests so they do not replace vanilla |
| `quest_prefix` | string | e.g. `reignofterror` → `records/quests/reignofterror/` |
| `skip_world_maps` | bool | Portal mods: do not overlay campaign world/maps |
| `items_mode` | `merge` / `isolate` / `namespace` | Items into target vs stay in mod world vs prefixed paths |
| `items_prefix` | string | Used when `items_mode=namespace` |

Lower-priority mods still contribute **unique** files; only overlapping paths lose.

### Priority ladder (from conflict analysis)

| Pri | Class | Mod | Role |
|-----|-------|-----|------|
| 100 | 100 | Riftwalk | Highest; **`enabled: false`** (OP) |
| 96 | 96 | Wereform Buffs | 38 wereform skill buffs over Rebirth |
| 92 | 94 | Rebirth | FoA mastery + AI/controllers/enemies; **skips items** |
| 90 | 90 | Grimarillion | Mega content + custom classes |
| 80 | 55 | ReignOfTerror | Portal; items isolate; low class stomp |
| 70 | 88 | Dawn of Masteries | Extra masteries; loses shared base to Grim/Rebirth |
| 60 | 40 | ShatteredAffixes | Affix/loot; no mastery touch |
| 30 | 30 | Nydiamar | Portal / campaign pipeline |

**Merge order (low→high):** Shattered → DoM → RoT → Grimarillion → Rebirth → Wereform  
(Riftwalk skipped while disabled.)

### Conflict notes (Survival kitchen-sink unpack)

- ~11k paths in 2+ mods
- DoM∩Grim ~6825 (mostly shared toolchain/other + items)
- **Grim∩Rebirth ≈952** — see [GRIM_REBIRTH_CONFLICTS.md](GRIM_REBIRTH_CONFLICTS.md) (mastery/enemies → Rebirth; items/devotion/UI/gameengine/PC hubs → Grim or hub-union)
- Wereform∩Rebirth: 38/38 mastery wereform skills
- RoT∩Rebirth: 269 mastery + 302 items → class_priority low + items isolate

## Run

```powershell
.\Run-GdSurvivalClasses.ps1 -DryRunNames -SkipResources
```

Uses `profiles/survivalmode.json` for the mod list; each mod’s rule file drives rewiring and order.
