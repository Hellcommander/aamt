# Grim Dawn × Rebirth conflict split

Unpacked overlap: **952** shared DBRs (Rebirth 6351, Grimarillion 65767, Rebirth-only 5399).

## Strategy: targeted field merge

Overlapping `.dbr` files are **field-merged** (not full replace):

- Keys only in Grim → kept
- Keys only in Rebirth → added
- Shared conflicts → Rebirth preferred for AI/skill/anim fields; Grim preferred for loot/merchant/faction fields

| Category | Count | Handling |
|----------|------:|----------|
| enemies | 530 | Field-merge (AI/skill → Rebirth, loot → Grim) |
| mastery `playerclass*` | 114 | Field-merge (skill fields → Rebirth) |
| items | 144 | Field-merge (loot/merchant → Grim, FoA skill tweaks → Rebirth) |
| devotion / other skills | ~46 | Field-merge under `records/skills/` |
| inventor / character UI | ~43 | **Skip Rebirth** (Grim keeps) |
| `records/game/` | ≥1 | **Skip Rebirth** (Grim `gameengine`) |
| PC hubs | 2 | **Skip Rebirth** — hub union via `unlock_full_classes` |
| AI controllers | mostly unique | Rebirth-only files copy in; 1 shared field-merges |

Rules: `rebirth.json`, `grimarillion.json`, `wereform_buffs.json`.
