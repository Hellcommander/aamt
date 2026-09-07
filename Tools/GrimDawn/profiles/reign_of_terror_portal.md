# ReignOfTerror — portal access (not campaign replace)

Intent: keep base campaign / Survival maps; visit Reign of Terror via a **portal / riftgate**,
same pattern as Nydiamar stitch.

## Survival playground

`patch_survival_classes.py --portal-mods ReignOfTerror` overlays **items/skills/affixes only**
and skips RoT `world` / `maps` / `quests` so Survival waves are not replaced.

## Full portal stitch (later)

1. Keep RoT as its own world files under a Custom Game (or unified campaign mod).
2. Editor: add portal from Devil's Crossing / Fort Ikon / Survival hub → RoT start region.
3. Quest-namespace RoT quests if they collide with vanilla (`quest_remap.py --prefix reignofterror`).
4. Do not wholesale overwrite FoA campaign world files.

See also: `editor_stitch_checklist.md`, Nydiamar `EDITOR_STITCH_CHECKLIST.md`.
