# Runic Weapon System Asset Generation Guide

Generate assets for the Runic Weapon System including rune icons, wand sprites, staff sprites, and rune effects.

## Quick Start

```powershell
# Generate all runic weapon assets
.\GenerateRunicWeaponAssets.ps1

# Use C++ backend for better quality
.\GenerateRunicWeaponAssets.ps1 -UseCppBackend

# Or generate everything including runic weapon assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Rune Icons (20 icons)

**Elemental Runes:**
1. **rune_fire** - Fire rune (Ignis)
2. **rune_water** - Water rune (Aqua)
3. **rune_earth** - Earth rune (Terra)
4. **rune_air** - Air rune (Ventus)

**Power Runes:**
5. **rune_force** - Force rune (Vis)
6. **rune_shield** - Shield rune (Aegis)
7. **rune_heal** - Heal rune (Vitae)
8. **rune_drain** - Drain rune (Vampyr)

**Utility Runes:**
9. **rune_teleport** - Teleport rune (Porta)
10. **rune_time** - Time rune (Chronos)
11. **rune_illusion** - Illusion rune (Mirage)
12. **rune_summon** - Summon rune (Evocatio)

**Modifier Runes:**
13. **rune_amplify** - Amplify rune (Magnus)
14. **rune_split** - Split rune (Divisio)
15. **rune_chain** - Chain rune (Catena)
16. **rune_pierce** - Pierce rune (Penetratio)

**Forbidden Runes:**
17. **rune_chaos** - Chaos rune (Entropy)
18. **rune_void** - Void rune (Nihil)
19. **rune_soul** - Soul rune (Anima)
20. **rune_corrupt** - Corrupt rune (Corruptio)

### Wand Sprites (9 sprites)

1. **wand_apprentice** - Apprentice wand (1-2 slots)
2. **wand_journeyman** - Journeyman wand (3-4 slots)
3. **wand_master** - Master wand (5-6 slots)
4. **wand_archmage** - Archmage wand (7-8 slots)
5. **wand_legendary** - Legendary wand (9+ slots)
6. **wand_battle** - Battle wand
7. **wand_utility** - Utility wand
8. **wand_channeling** - Channeling wand
9. **wand_ritual** - Ritual wand

### Staff Sprites (10 sprites)

1. **staff_wooden** - Wooden staff
2. **staff_crystal** - Crystal staff
3. **staff_metal** - Metal staff
4. **staff_bone** - Bone staff
5. **staff_living** - Living staff
6. **staff_hybrid** - Hybrid staff
7. **staff_world_tree** - World Tree staff (legendary)
8. **staff_star_metal** - Star Metal staff (legendary)
9. **staff_dragon_bone** - Dragon Bone staff (legendary)
10. **staff_void_crystal** - Void Crystal staff (legendary)

### Rune Glow Effects (8 effects)

1. **rune_glow_fire** - Fire rune glow
2. **rune_glow_water** - Water rune glow
3. **rune_glow_earth** - Earth rune glow
4. **rune_glow_air** - Air rune glow
5. **rune_glow_force** - Force rune glow
6. **rune_glow_shield** - Shield rune glow
7. **rune_glow_heal** - Heal rune glow
8. **rune_glow_void** - Void rune glow

### Rune Activation Effects (8 effects)

1. **rune_activation_fire** - Fire rune activation
2. **rune_activation_water** - Water rune activation
3. **rune_activation_earth** - Earth rune activation
4. **rune_activation_air** - Air rune activation
5. **rune_activation_force** - Force rune activation
6. **rune_activation_shield** - Shield rune activation
7. **rune_activation_teleport** - Teleport rune activation
8. **rune_activation_combination** - Combination rune activation

## Total: ~55 Assets

## Output Structure

```
assets/
├── runes/
│   ├── rune_fire.png
│   ├── rune_water.png
│   ├── ... (all rune icons)
│   ├── rune_glow_fire.particle
│   ├── rune_glow_water.particle
│   ├── ... (all rune glows)
│   ├── rune_activation_fire.particle
│   ├── rune_activation_water.particle
│   └── ... (all rune activations)
├── weapons/
│   ├── wands/
│   │   ├── wand_apprentice.png
│   │   ├── wand_journeyman.png
│   │   └── ... (all wand sprites)
│   └── staves/
│       ├── staff_wooden.png
│       ├── staff_crystal.png
│       └── ... (all staff sprites)
```

## Integration

### Rune Inscription

```lua
-- Inscribe rune on weapon
RunicWeaponSystem:inscribeRune(weapon, slotIndex, RuneType.FIRE)
-- Uses: /runes/rune_fire.png icon
-- Shows: /runes/rune_glow_fire.particle glow effect
```

### Rune Casting

```lua
-- Cast rune
RunicWeaponSystem:castRune(weapon, runeIndex, origin, direction)
-- Shows: /runes/rune_activation_fire.particle activation effect
```

### Combination Casting

```lua
-- Cast combination of runes
RunicWeaponSystem:executeCombination(weapon, origin, direction)
-- Shows: /runes/rune_activation_combination.particle combination effect
```

### Weapon Generation

```lua
-- Generate wand
local wand = RunicWeaponSystem:generateWand(WandType.MASTER, "elegant")
-- Uses: /weapons/wands/wand_master.png sprite

-- Generate staff
local staff = RunicWeaponSystem:generateStaff(StaffType.CRYSTAL, "ancient")
-- Uses: /weapons/staves/staff_crystal.png sprite
```

## Rune Types

### Elemental Runes
- **Fire (Ignis)**: Red/orange, fire damage
- **Water (Aqua)**: Blue/cyan, water/ice effects
- **Earth (Terra)**: Brown/green, earth/stone magic
- **Air (Ventus)**: White/light blue, wind/lightning

### Power Runes
- **Force (Vis)**: Purple, raw magical force
- **Shield (Aegis)**: Golden, protective barriers
- **Heal (Vitae)**: Green, restoration magic
- **Drain (Vampyr)**: Dark red, life drain

### Utility Runes
- **Teleport (Porta)**: Purple/blue, spatial magic
- **Time (Chronos)**: Gold/blue, temporal effects
- **Illusion (Mirage)**: Purple/pink, deception magic
- **Summon (Evocatio)**: Dark purple, summoning

### Modifier Runes
- **Amplify (Magnus)**: Yellow, increase power
- **Split (Divisio)**: Cyan, multi-cast
- **Chain (Catena)**: Silver, chain effects
- **Pierce (Penetratio)**: Dark blue, armor bypass

### Forbidden Runes
- **Chaos (Entropy)**: Chaotic colors, random effects
- **Void (Nihil)**: Black/purple, void magic
- **Soul (Anima)**: Dark purple, soul manipulation
- **Corrupt (Corruptio)**: Dark red/black, dark magic

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateRunicWeaponAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Generate Weapons

Generate wands and staves with the system.

### Step 3: Inscribe Runes

Inscribe runes onto weapons using the rune icons.

### Step 4: Test in Game

Load the mod and test runic weapons in-game.

## Advanced Options

### Custom Rune Types

Edit `GenerateRunicWeaponAssets.ps1` to add custom rune types:

```powershell
@{
    Id = "rune_custom"
    Name = "Custom Rune"
    Desc = "Custom rune description"
}
```

### Custom Wand Types

Add custom wand types to the `$wandSprites` array.

### Custom Staff Types

Add custom staff types to the `$staffSprites` array.

## Tips

1. **Rune icons**: Use 32x32 for UI display
2. **Wand/Staff size**: Use 64x64 for weapon sprites
3. **Glow effects**: Create distinct glows for each rune type
4. **Activation effects**: Make activations visually distinct
5. **Combination effects**: Use mixed colors for combination effects

## Troubleshooting

### Runes Not Appearing

- Check rune icon paths in weapon definitions
- Verify icons are in `assets/runes/`
- Ensure rune system is initialized

### Weapons Not Generating

- Check wand/staff sprite paths
- Verify weapon generation system is initialized
- Ensure sprites are in correct directories

### Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in rune definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
