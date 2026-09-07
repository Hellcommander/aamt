# Race Generation System Asset Generation Guide

Generate assets for the Race Generation System including race portraits, character icons, and equipment icons.

## Quick Start

```powershell
# Generate all race assets
.\GenerateRaceAssets.ps1

# Use C++ backend for better quality
.\GenerateRaceAssets.ps1 -UseCppBackend

# Or generate everything including race assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Race Portraits/Icons (7 icons)

1. **race_portrait_human** - Human race portrait
2. **race_portrait_apex** - Apex race portrait
3. **race_portrait_avian** - Avian race portrait
4. **race_portrait_floran** - Floran race portrait
5. **race_portrait_glitch** - Glitch race portrait
6. **race_portrait_hylotl** - Hylotl race portrait
7. **race_portrait_novakid** - Novakid race portrait

### Common Equipment Icons (15 icons)

**Weapons:**
1. **equip_primitiveLaserPistol** - Primitive laser pistol
2. **equip_woodenBow** - Wooden bow
3. **equip_woodSword** - Wood sword
4. **equip_stoneSpear** - Stone spear
5. **equip_copperDagger** - Copper dagger

**Armor:**
6. **equip_clothShirt** - Cloth shirt
7. **equip_leatherArmor** - Leather armor
8. **equip_ironHelmet** - Iron helmet
9. **equip_woolCape** - Wool cape
10. **equip_boneArmor** - Bone armor

**Gadgets:**
11. **equip_healingPotion** - Healing potion
12. **equip_repairKit** - Repair kit
13. **equip_torch** - Torch
14. **equip_rope** - Rope
15. **equip_compass** - Compass

### Rare Equipment Icons (15 icons)

**Weapons:**
1. **equip_ironRifle** - Iron rifle
2. **equip_floranBlade** - Floran blade
3. **equip_avianSpear** - Avian spear
4. **equip_glitchSword** - Glitch sword
5. **equip_hylotlTrident** - Hylotl trident

**Armor:**
6. **equip_chainmail** - Chainmail
7. **equip_floranHide** - Floran hide
8. **equip_avianFeatherCloak** - Avian feather cloak
9. **equip_glitchArmor** - Glitch armor
10. **equip_hylotlScale** - Hylotl scale

**Gadgets:**
11. **equip_energyCell** - Energy cell
12. **equip_teleporterBeacon** - Teleporter beacon
13. **equip_shieldGenerator** - Shield generator
14. **equip_jetpack** - Jetpack
15. **equip_scanner** - Scanner

### Legendary Equipment Icons (15 icons)

**Weapons:**
1. **equip_etherialStaff** - Etherial staff
2. **equip_novaCannon** - Nova cannon
3. **equip_voidKatana** - Void katana
4. **equip_dragonBlade** - Dragon blade
5. **equip_phoenixBow** - Phoenix bow

**Armor:**
6. **equip_dragonPlate** - Dragon plate
7. **equip_phoenixCloak** - Phoenix cloak
8. **equip_titanHelm** - Titan helm
9. **equip_voidArmor** - Void armor
10. **equip_starCloak** - Star cloak

**Gadgets:**
11. **equip_gravityBoots** - Gravity boots
12. **equip_phaseBlade** - Phase blade
13. **equip_timeDilator** - Time dilator
14. **equip_warpDrive** - Warp drive
15. **equip_realityShifter** - Reality shifter

## Total: ~52 Assets

## Output Structure

```
assets/
├── races/
│   └── portraits/
│       ├── race_portrait_human.png
│       ├── race_portrait_apex.png
│       ├── race_portrait_avian.png
│       ├── race_portrait_floran.png
│       ├── race_portrait_glitch.png
│       ├── race_portrait_hylotl.png
│       └── race_portrait_novakid.png
└── equipment/
    ├── common/
    │   ├── equip_primitiveLaserPistol.png
    │   ├── equip_woodenBow.png
    │   └── ... (all common equipment)
    ├── rare/
    │   ├── equip_ironRifle.png
    │   ├── equip_floranBlade.png
    │   └── ... (all rare equipment)
    └── legendary/
        ├── equip_etherialStaff.png
        ├── equip_novaCannon.png
        └── ... (all legendary equipment)
```

## Integration

### Race Generation

```cpp
// Load race configurations
RaceGenerator::instance().loadConfigs();

// Spawn NPCs with races
RaceGenerator::instance().spawnNPCs(worldId, spawnPoints, layerName);
// Uses: /races/portraits/race_portrait_*.png for UI
// Uses: /equipment/*/equip_*.png for equipment icons
```

### Race Queries

```cpp
// Get NPCs by race
auto npcs = RaceGenerator::instance().getNPCsByRace(worldId, "Human");
// Uses: /races/portraits/race_portrait_human.png for UI

// Get NPCs by equipment
auto equipped = RaceGenerator::instance().getNPCsByEquipment(worldId, "ironRifle");
// Uses: /equipment/rare/equip_ironRifle.png for UI
```

### Equipment Sets

The system uses three equipment sets:
- **Common** (70% weight) - Basic equipment
- **Rare** (25% weight) - Advanced equipment
- **Legendary** (5% weight) - Powerful equipment

## Races

### Available Races

1. **Human** - Spawns on DungeonLayer, SkyIslands
2. **Apex** - Spawns on DungeonLayer
3. **Avian** - Spawns on SkyIslands, DungeonLayer
4. **Floran** - Spawns on DungeonLayer
5. **Glitch** - Spawns on DungeonLayer
6. **Hylotl** - Spawns on SkyIslands, DungeonLayer
7. **Novakid** - Spawns on SkyIslands

### Race Models

Each race has male and female models:
- `human_m`, `human_f`
- `apex_m`, `apex_f`
- `avian_m`, `avian_f`
- `floran_m`, `floran_f`
- `glitch_m`, `glitch_f`
- `hylotl_m`, `hylotl_f`
- `novakid_m`, `novakid_f`

## Equipment Categories

### Weapons
- Melee: Swords, spears, daggers, blades
- Ranged: Bows, rifles, pistols, cannons
- Magical: Staves, katanas

### Armor
- Clothing: Shirts, cloaks, capes
- Light Armor: Leather, hide, scale
- Heavy Armor: Chainmail, plate, helm

### Gadgets
- Consumables: Potions, repair kits
- Utility: Torches, ropes, compasses
- Advanced: Teleporters, shields, jetpacks
- Legendary: Time dilators, warp drives, reality shifters

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateRaceAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Load Configurations

Load race and equipment configurations from JSON files.

### Step 3: Spawn NPCs

Spawn NPCs with races and equipment in the world.

### Step 4: Test in Game

Load the mod and test NPC spawning in-game.

## Advanced Options

### Custom Races

Edit `config/races.json` to add custom races:

```json
{
  "name": "CustomRace",
  "models": ["custom_m", "custom_f"],
  "spawnLayers": ["DungeonLayer"],
  "equipmentSets": {
    "common": 0.7,
    "rare": 0.3
  }
}
```

Then add a portrait to `GenerateRaceAssets.ps1`:

```powershell
@{ Id = "race_portrait_custom"; Name = "Custom Race Portrait"; Desc = "Custom race portrait, 64x64" }
```

### Custom Equipment

Edit `config/equipment.json` to add custom equipment sets, then add icons to `GenerateRaceAssets.ps1`.

## Tips

1. **Race portraits**: Use 64x64 for UI display
2. **Equipment icons**: Use 32x32 for inventory/UI
3. **Equipment sets**: Match equipment icons to equipment IDs in JSON
4. **Race themes**: Ensure portraits match race characteristics
5. **Equipment tiers**: Make legendary equipment visually distinct

## Troubleshooting

### Races Not Loading

- Check race configuration file path
- Verify `config/races.json` exists
- Ensure race portraits are in `assets/races/portraits/`

### Equipment Not Appearing

- Check equipment configuration file path
- Verify `config/equipment.json` exists
- Ensure equipment icons match equipment IDs
- Check equipment icons are in correct tier directories

### NPCs Not Spawning

- Verify spawn layers match race spawn layers
- Check model IDs exist in the game
- Ensure equipment sets are properly configured

---

*Part of the Starbound Ollama Asset Generator suite*
