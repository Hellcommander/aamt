# Classic vs Steam Adventure Mode (honest gap catalog)

This is a **documentation stopgap** for AAMT. It does **not** restore Classic systems.

| System | Steam status | AAMT kit |
|--------|--------------|----------|
| Movement / combat / inventory | Complete enough to play | None needed |
| Fast travel / sites | Complete | None needed |
| Companions | Present | None needed |
| Conversation depth | Partial vs Classic | Lore/rumor text only (not dialogue trees) |
| Crafting / reactions | Partial | `ADVENTURE_MODE_ENABLED` reactions using documented vanilla patterns (`MAKE_SHARP_ROCK`, adventure carpentry) |
| Magic / secrets | Missing / incomplete | Omitted (no invented APIs) |
| Site / camp building | Partial | Use official Steam Adventure camp tools when present; do not fake construction |
| Quests | Basic | Not emulated |
| World politics | Missing | Not emulated |

## Rules

- Do not invent DF raw tokens.
- Do not invent DFHack conversation overlay APIs.
- DF simulation remains single-threaded; AAMT workers are tool-side only.
- Workers/scripts must not claim Classic parity.

## How to use the kit

```powershell
python df_civ_cli.py adventure-kit --spec ..\Output\DwarfFortress\MYFOLK\creature.json
# or
python df_civ_cli.py generate --spec ... --adventure-kit
```

Staged under the mod: `objects/reaction_adv_*.txt`, `AdventureParity/`, optional DFHack `*_adv_lore.lua` if `hack/` exists.

## Sources

Player-facing Steam Adventure Mode status as of Premium development (feature-incomplete vs Classic ASCII UI era). Update this table when official patches land.
