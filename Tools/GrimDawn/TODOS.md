# Grim Dawn Mod Tools — TODOs

Living checklist for `Transcendence/Tools/GrimDawn`.  
Game: `D:\games\Steam\steamapps\common\Grim Dawn`  
Updated: 2026-07-28

---

## Done

- [x] Core tool suite (merger, FoA compat, quest remap, Nydiamar stitch prep, Survival playground)
- [x] Pipeline outputs: `mods\NydiamarIntegrated`, `mods\SurvivalPlayground` (DLC classes baseline)
- [x] Root-level `.arz` mod support (Riftwalk-style)
- [x] Survival achievement DBR protection + `--portal-mods` (content-only, no maps/quests)

---

## SurvivalPlayground kitchen-sink (in progress)

**Base:** `survivalmode`  
**Full content overlays (later wins):**
1. Dawn of Masteries-82-1-6-0e-1752630201  
2. grimarillion  
3. Rebirth  
4. Riftwalk V2.0 236 2.0 2026-07-26T13-54Z Pc0Feo2z8  
5. ShatteredAffixes  
6. Wereform Buffs  

**Portal-mod (items/skills only — no campaign replace):**
- ReignOfTerror → separate Editor portal stitch later (see `profiles/reign_of_terror_portal.md`)

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\GrimDawn"
.\Run-GdSurvivalClasses.ps1 -Out SurvivalPlayground -DryRunNames -SkipResources `
  -ClassMods "dom","grimarillion","Rebirth" `
  -ContentMods "dom","grimarillion","Rebirth","Riftwalk","ShatteredAffixes","Wereform Buffs" `
  -PortalMods "ReignOfTerror"
```

- [ ] Finish kitchen-sink DB build + verify class lines / protected achievements
- [ ] Optional: re-run **without** `-SkipResources` to merge Items/UI ARCs (slow)
- [ ] Asset Manager rebuild → in-game power-level test

---

## ReignOfTerror portal (not campaign replace)

- [ ] Quest-namespace RoT if needed (`quest_remap.py --prefix reignofterror`)
- [ ] Editor portal from campaign/Survival hub → RoT start (same pattern as Nydiamar)
- [ ] Keep base FoA campaign world files intact

---

## NydiamarIntegrated (human)

- [ ] Asset Manager build
- [ ] Editor stitch per `EDITOR_STITCH_CHECKLIST.md`
- [ ] Playtest unified Custom Game

---

## Backlog

- [ ] Pack remapped quest ARCs (`pack_mod_arcs.py`)
- [ ] Re-stitch after Crate map patches
