# World Editor stitch checklist (static reference)

Same-character FoA + Nydiamar requires a **unified Custom Game**, not stock Campaign saves.

## Preferred pattern

1. Keep Nydiamar as its own world file(s).
2. Edit the campaign world (or a [campaign map template](https://forums.crateentertainment.com/t/mod-resource-campaign-map-template/97766)) only enough to add a **portal / riftgate / NPC teleporter** into Nydiamar’s start region.
3. Do not rebuild all campaign pathing or replace FoA map files wholesale.

## Portal hubs (CLI `--portal-hub`)

| Key | Hub |
|-----|-----|
| `devils_crossing` | Devil's Crossing (default) |
| `homestead` | Homestead |
| `fort_ikon` | Fort Ikon |
| `malmouth` | Malmouth outskirts |
| `asterkarn` | Asterkarn / FoA hub |

## Tool prep

```powershell
.\Run-NydiamarFoACampaign.ps1 -PortalHub devils_crossing -DryRunNames
```

This unpacks `Maps.arc` / `Quests.arc` / `Conversations.arc` / `Scripts.arc` / `Text_en.arc` into the output mod’s `source\`, namespaces quests, runs FoA compat, and writes portal stub DBRs + a generated `EDITOR_STITCH_CHECKLIST.md` inside the mod.

## Manual finish

1. Asset Manager → working directory = output mod → Build database.
2. `Editor.exe` → place portal at chosen hub → link to Nydiamar start region.
3. Quest Editor → finish stub quest under `records/quests/nydiamar/portal/`.
4. Build maps/quests → playtest via Custom Game.

## Honesty bounds

- Full automated overworld merge is out of v1 scope.
- Region limits and FoA map updates may require re-stitch after patches.
- Quest path remap is automated; hardcoded script IDs may need hand follow-up.

## FoA regions + Grimarillion World001

CampaignKitchenSink starts on **Grimarillion's edited `world001`** (via `Levels.arc`), not stock FoA and not Nydiamar.

FoA Asterkarn content is part of **gdx3 `world001.map`**. That file and Grimarillion's `world001.map` are different binaries — tools cannot auto-merge them without wiping one side.

To have **both** Grimarillion map edits **and** full FoA map access:

1. Use a FoA-updated Grimarillion `levels.arc` when available, then:
   `python campaign_start_world.py --mod CampaignKitchenSink`
2. Or in World Editor: keep Grimarillion World001 as base; add/link FoA regions from the [campaign map template](https://forums.crateentertainment.com/t/mod-resource-campaign-map-template/97766) / gdx3 FoA world (Fort Ikon → Asterkarn). Do not wholesale-replace with stock FoA Levels.

Nydiamar stays a separate `Maps.arc` world, reached only by portal (and a return portal).
