# WandAgent System Asset Generation Guide

Generate visual assets for the WandAgent System including wand sprites, staff sprites, metagem icons, relic icons, mod core icons, casting effects, slot indicators, and graph connection visuals.

## Quick Start

```powershell
# Generate all WandAgent assets
.\GenerateWandAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateWandAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Wand Sprites (9 wands)

1. **wand_runic** - Runic wand
2. **wand_chronomancer** - Chronomancer wand
3. **wand_elementalist** - Elementalist wand
4. **wand_battlemage** - Battlemage wand
5. **wand_apprentice** - Apprentice wand
6. **wand_journeyman** - Journeyman wand
7. **wand_master** - Master wand
8. **wand_archmage** - Archmage wand
9. **wand_legendary** - Legendary wand

### Staff Sprites (10 staves)

1. **staff_wooden** - Wooden staff
2. **staff_crystal** - Crystal staff
3. **staff_metal** - Metal staff
4. **staff_bone** - Bone staff
5. **staff_living** - Living staff
6. **staff_hybrid** - Hybrid staff
7. **staff_world_tree** - World tree staff
8. **staff_star_metal** - Star metal staff
9. **staff_dragon_bone** - Dragon bone staff
10. **staff_void_crystal** - Void crystal staff

### Metagem Icons (6 metagems)

1. **metagem_reduce_mana** - Reduce mana cost metagem
2. **metagem_enhance_elemental** - Enhance elemental damage metagem
3. **metagem_enhance_damage** - Enhance damage metagem
4. **metagem_crit_chance** - Crit chance metagem
5. **metagem_cast_speed** - Cast speed metagem
6. **metagem_spell_range** - Spell range metagem

### Relic Icons (6 relics)

1. **relic_power** - Power relic
2. **relic_speed** - Speed relic
3. **relic_protection** - Protection relic
4. **relic_wisdom** - Wisdom relic
5. **relic_chaos** - Chaos relic
6. **relic_order** - Order relic

### Mod Core Icons (5 mod cores)

1. **modcore_basic** - Basic mod core
2. **modcore_advanced** - Advanced mod core
3. **modcore_elemental** - Elemental mod core
4. **modcore_combat** - Combat mod core
5. **modcore_utility** - Utility mod core

### Wand Casting Effects (4 effects)

1. **wand_cast_effect** - Wand casting particle effect
2. **wand_charge_effect** - Wand charging particle effect
3. **wand_reload_effect** - Wand reloading particle effect
4. **wand_shuffle_effect** - Wand shuffle particle effect

### Staff Casting Effects (4 effects)

1. **staff_cast_effect** - Staff casting particle effect
2. **staff_charge_effect** - Staff charging particle effect
3. **staff_aoe_effect** - Staff area of effect particle effect
4. **staff_elemental_effect** - Staff elemental particle effect

### Slot Node Indicators (8 indicators)

1. **slot_spellstone** - Spellstone slot indicator
2. **slot_modcore** - Mod core slot indicator
3. **slot_metagem** - Metagem slot indicator
4. **slot_relic** - Relic slot indicator
5. **slot_empty** - Empty slot indicator
6. **slot_ready** - Ready slot indicator
7. **slot_cooldown** - Cooldown slot indicator
8. **slot_active** - Active slot indicator

### Graph Connection Visuals (4 visuals)

1. **graph_connection** - Graph connection line
2. **graph_prerequisite** - Graph prerequisite indicator
3. **graph_branch_active** - Active branch indicator
4. **graph_branch_inactive** - Inactive branch indicator

## Total: ~56 Assets

## Output Structure

```
assets/
├── wands/
│   ├── wand_runic.png
│   ├── wand_chronomancer.png
│   └── ... (all wand sprites)
│   ├── metagems/
│   │   ├── metagem_reduce_mana.png
│   │   └── ... (all metagem icons)
│   ├── relics/
│   │   ├── relic_power.png
│   │   └── ... (all relic icons)
│   ├── modcores/
│   │   ├── modcore_basic.png
│   │   └── ... (all mod core icons)
│   ├── effects/
│   │   ├── wand_cast_effect.particle
│   │   └── ... (all wand effects)
│   ├── slots/
│   │   ├── slot_spellstone.png
│   │   └── ... (all slot indicators)
│   └── graph/
│       ├── graph_connection.png
│       └── ... (all graph visuals)
└── staves/
    ├── staff_wooden.png
    ├── staff_crystal.png
    └── ... (all staff sprites)
    └── effects/
        ├── staff_cast_effect.particle
        └── ... (all staff effects)
```

## Integration

### WandAgent

```cpp
// Create wand
WandAgent::createWand("runic", 1);
// Uses: /assets/wands/wand_runic.png

// Create staff
WandAgent::createStaff("wooden", 1);
// Uses: /assets/staves/staff_wooden.png

// Add metagem
WandAgent::addMetagem(wandId, "reduce_mana", slotId);
// Uses: /assets/wands/metagems/metagem_reduce_mana.png

// Add relic
WandAgent::addRelic(wandId, "power", slotId);
// Uses: /assets/wands/relics/relic_power.png

// Add mod core
WandAgent::addModCore(wandId, "basic", slotId);
// Uses: /assets/wands/modcores/modcore_basic.png

// Cast wand
WandAgent::castWand(wandId);
// Uses: /assets/wands/effects/wand_cast_effect.particle
// Uses: /assets/wands/effects/wand_charge_effect.particle

// Cast staff
WandAgent::castStaff(wandId);
// Uses: /assets/staves/effects/staff_cast_effect.particle
// Uses: /assets/staves/effects/staff_charge_effect.particle

// Get active branch
WandAgent::getActiveBranch(wandId);
// Uses: /assets/wands/graph/graph_branch_active.png
// Uses: /assets/wands/graph/graph_connection.png

// Get ready nodes
WandAgent::getReadyNodes(wandId);
// Uses: /assets/wands/slots/slot_ready.png
```

### RunicWand

```cpp
// Get active branch
RunicWand::getActiveBranch();
// Uses: /assets/wands/graph/graph_branch_active.png

// Get ready nodes
RunicWand::getReadyNodes();
// Uses: /assets/wands/slots/slot_ready.png

// Add item to slot
RunicWand::addItem(nodeId, item);
// Uses: /assets/wands/slots/slot_spellstone.png
// Uses: /assets/wands/slots/slot_modcore.png
// Uses: /assets/wands/slots/slot_metagem.png
// Uses: /assets/wands/slots/slot_relic.png
```

## Wand Types

### Wand Variants
- **Runic**: Basic runic wand
- **Chronomancer**: Time magic wand
- **Elementalist**: Elemental magic wand
- **Battlemage**: Combat wand
- **Apprentice**: Beginner wand
- **Journeyman**: Intermediate wand
- **Master**: Advanced wand
- **Archmage**: Expert wand
- **Legendary**: Legendary wand

## Staff Types

### Staff Variants
- **Wooden**: Basic wooden staff
- **Crystal**: Crystal staff
- **Metal**: Metallic staff
- **Bone**: Bone staff
- **Living**: Organic staff
- **Hybrid**: Hybrid staff
- **World Tree**: World tree staff
- **Star Metal**: Star metal staff
- **Dragon Bone**: Dragon bone staff
- **Void Crystal**: Void crystal staff

## Metagem System

### Metagem Effects
- **Reduce Mana**: Reduces spell mana cost
- **Enhance Elemental**: Increases elemental damage
- **Enhance Damage**: Increases spell damage
- **Crit Chance**: Increases critical hit chance
- **Cast Speed**: Increases casting speed
- **Spell Range**: Increases spell range

### Metagem Limits
- Maximum 2 metagems per wand
- Can be placed in any metagem slot

## Relic System

### Relic Types
- **Power**: Power enhancement relic
- **Speed**: Speed enhancement relic
- **Protection**: Protection relic
- **Wisdom**: Wisdom relic
- **Chaos**: Chaos relic
- **Order**: Order relic

### Relic Effects
- **Pre-cast**: Effects applied before casting
- **Post-cast**: Effects applied after casting
- **Passive**: Passive buffs to wand stats

## Mod Core System

### Mod Core Types
- **Basic**: Basic modification core
- **Advanced**: Advanced modification core
- **Elemental**: Elemental modification core
- **Combat**: Combat modification core
- **Utility**: Utility modification core

### Mod Core Effects
- Applied to spells during casting
- Can modify spell properties
- Can be placed in any mod core slot

## Slot System

### Slot Types
- **Spellstone**: Spellstone slot
- **Mod Core**: Mod core slot
- **Metagem**: Metagem slot
- **Relic**: Relic slot

### Slot States
- **Empty**: Empty slot
- **Ready**: Slot ready to activate
- **Cooldown**: Slot on cooldown
- **Active**: Slot currently active

## Graph System

### Graph Elements
- **Connection**: Connection line between nodes
- **Prerequisite**: Prerequisite marker
- **Active Branch**: Active branch indicator
- **Inactive Branch**: Inactive branch indicator

### Graph Features
- Branching graph structure
- Prerequisites for node activation
- Active branch tracking
- Ready node detection

## Noita Integration

### Noita Features
- **Shuffle**: Shuffle spell deck
- **Spells Per Cast**: Multiple spells per cast
- **Cast Delay**: Delay between casts
- **Recharge Time**: Recharge time between casts
- **Spread**: Spread angle for spells

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateWandAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure WandAgent

Set up WandAgent with asset paths.

### Step 3: Create Wands

```cpp
WandAgent agent;
agent.init();
auto wand = agent.createWand("runic", 1);
```

### Step 4: Add Components

```cpp
agent.addSpellstone(wandId, "fire_spellstone", "slot_1");
agent.addMetagem(wandId, "reduce_mana", "slot_2");
agent.addRelic(wandId, "power", "slot_3");
agent.addModCore(wandId, "basic", "slot_4");
```

### Step 5: Cast Wands

```cpp
auto spells = agent.castWand(wandId);
```

### Step 6: Test in Game

Load the mod and test wand system in-game.

## Advanced Options

### Custom Wand Types

Edit `GenerateWandAgentAssets.ps1` to add custom wand types.

### Custom Staff Types

Add custom staff types as needed.

### Custom Metagems

Add custom metagems with unique effects.

### Custom Relics

Add custom relics with unique properties.

## Tips

1. **Wand sprites**: Use 32x32 for wands
2. **Staff sprites**: Use 32x64 for staves (taller)
3. **Icons**: Use 32x32 for all icons
4. **Effects**: Use 64x64 for particle effects
5. **Slot indicators**: Make slots clearly visible
6. **Graph visuals**: Keep graph connections clear
7. **Consistency**: Keep all wand/staff assets consistent

## Troubleshooting

### Wands Not Displaying

- Check wand sprite paths
- Verify sprites are in `assets/wands/`
- Ensure WandAgent is initialized

### Staffs Not Showing

- Check staff sprite paths
- Verify sprites are in `assets/staves/`
- Ensure staff system is configured

### Metagems Not Working

- Check metagem icon paths
- Verify icons are in `assets/wands/metagems/`
- Ensure metagem system is enabled

### Relics Not Applying

- Check relic icon paths
- Verify icons are in `assets/wands/relics/`
- Ensure relic system is enabled

### Mod Cores Not Functioning

- Check mod core icon paths
- Verify icons are in `assets/wands/modcores/`
- Ensure mod core system is enabled

### Casting Effects Not Showing

- Check effect particle paths
- Verify effects are in `assets/wands/effects/` or `assets/staves/effects/`
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
