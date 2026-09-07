# Golem System Asset Generation Guide

Generate visual assets for the Golem System including golem sprites, part sprites, blueprint icons, stance animations, summon effects, command indicators, circuit icons, material icons, and slot indicators.

## Quick Start

```powershell
# Generate all Golem assets
.\GenerateGolemAssets.ps1

# Use C++ backend for better quality
.\GenerateGolemAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Golem Sprites (6 golems)

1. **golem_basic** - Basic golem
2. **golem_stone** - Stone golem
3. **golem_iron** - Iron golem
4. **golem_crystal** - Crystal golem
5. **golem_wood** - Wood golem
6. **golem_arcane** - Arcane golem

### Golem Part Sprites (8 parts)

1. **part_head** - Head part
2. **part_torso** - Torso part
3. **part_arm_left** - Left arm part
4. **part_arm_right** - Right arm part
5. **part_leg_left** - Left leg part
6. **part_leg_right** - Right leg part
7. **part_hand** - Hand part
8. **part_foot** - Foot part

### Golem Blueprint Icons (4 icons)

1. **blueprint_basic** - Basic blueprint
2. **blueprint_advanced** - Advanced blueprint
3. **blueprint_custom** - Custom blueprint
4. **blueprint_template** - Blueprint template

### Golem Stance Animations (6 stances)

1. **stance_idle** - Idle stance animation
2. **stance_guard** - Guard stance animation
3. **stance_patrol** - Patrol stance animation
4. **stance_follow** - Follow stance animation
5. **stance_combat** - Combat stance animation
6. **stance_attack** - Attack stance animation

### Golem Summon Effects (4 effects)

1. **summon_effect** - Summon particle effect
2. **summon_formation** - Formation particle effect
3. **summon_complete** - Summon complete particle effect
4. **summon_fail** - Summon fail particle effect

### Golem Command Indicators (6 indicators)

1. **command_guard** - Guard command indicator
2. **command_patrol** - Patrol command indicator
3. **command_follow** - Follow command indicator
4. **command_attack** - Attack command indicator
5. **command_stop** - Stop command indicator
6. **command_idle** - Idle command indicator

### Golem Circuit Icons (5 icons)

1. **circuit_basic** - Basic circuit
2. **circuit_enhanced** - Enhanced circuit
3. **circuit_magic** - Magic circuit
4. **circuit_combat** - Combat circuit
5. **circuit_utility** - Utility circuit

### Golem Material Icons (6 icons)

1. **material_stone** - Stone material
2. **material_iron** - Iron material
3. **material_crystal** - Crystal material
4. **material_wood** - Wood material
5. **material_arcane** - Arcane material
6. **material_metal** - Metal material

### Golem Slot Indicators (4 indicators)

1. **slot_empty** - Empty slot indicator
2. **slot_occupied** - Occupied slot indicator
3. **slot_attachment** - Attachment slot indicator
4. **slot_resonance** - Resonance slot indicator

## Total: ~47 Assets

## Output Structure

```
assets/
└── golems/
    ├── sprites/
    │   ├── golem_basic.png
    │   ├── golem_stone.png
    │   └── ... (all golem sprites)
    ├── parts/
    │   ├── part_head.png
    │   ├── part_torso.png
    │   └── ... (all part sprites)
    ├── blueprints/
    │   ├── blueprint_basic.png
    │   ├── blueprint_advanced.png
    │   └── ... (all blueprint icons)
    ├── stances/
    │   ├── stance_idle.png
    │   ├── stance_guard.png
    │   └── ... (all stance animations)
    ├── summon/
    │   ├── summon_effect.particle
    │   ├── summon_formation.particle
    │   └── ... (all summon effects)
    ├── commands/
    │   ├── command_guard.png
    │   ├── command_patrol.png
    │   └── ... (all command indicators)
    ├── circuits/
    │   ├── circuit_basic.png
    │   ├── circuit_enhanced.png
    │   └── ... (all circuit icons)
    ├── materials/
    │   ├── material_stone.png
    │   ├── material_iron.png
    │   └── ... (all material icons)
    └── slots/
        ├── slot_empty.png
        ├── slot_occupied.png
        └── ... (all slot indicators)
```

## Integration

### GolemRegistry

```cpp
// Register blueprint
GolemRegistry::instance().registerBlueprint(golemBlueprint);
// Uses: /assets/golems/blueprints/blueprint_*.png

// Create from blueprint
GolemRegistry::instance().createFromBlueprint(blueprintId, seed);
// Uses: /assets/golems/sprites/golem_*.png
// Uses: /assets/golems/parts/part_*.png
// Uses: /assets/golems/summon/summon_effect.particle

// Attach part
GolemRegistry::instance().attachPart(golemId, partRef, slot);
// Uses: /assets/golems/parts/part_*.png
// Uses: /assets/golems/slots/slot_attachment.png

// Set stance
GolemRegistry::instance().setStance(golemId, stanceId);
// Uses: /assets/golems/stances/stance_*.png
```

### GolemManager

```cpp
// Create golem
GolemManager::createGolem(root, ownerId, x, y);
// Uses: /assets/golems/sprites/golem_basic.png
// Uses: /assets/golems/summon/summon_effect.particle

// Create from blueprint
GolemManager::createFromBlueprint(root, blueprint, seed);
// Uses: /assets/golems/blueprints/blueprint_*.png
// Uses: /assets/golems/sprites/golem_*.png
// Uses: /assets/golems/summon/summon_formation.particle

// Command golem
GolemManager::commandGolem(root, golemEntityId, "guard", targetId);
// Uses: /assets/golems/commands/command_guard.png
// Uses: /assets/golems/stances/stance_guard.png

// Attach part
GolemManager::attachPart(golemId, partId, slot);
// Uses: /assets/golems/parts/part_*.png
// Uses: /assets/golems/materials/material_*.png
```

### GolemBlueprint

```cpp
// GolemBlueprint structure
GolemBlueprint bp;
bp.id = "my_golem";
bp.parts = {partRef1, partRef2, ...};
bp.circuits = {circuitRef1, circuitRef2, ...};
bp.materialPresetId = "stone";
// Uses: /assets/golems/blueprints/blueprint_*.png
// Uses: /assets/golems/parts/part_*.png
// Uses: /assets/golems/circuits/circuit_*.png
// Uses: /assets/golems/materials/material_*.png
```

### PartRef

```cpp
// PartRef structure
PartRef part;
part.id = "head";
part.attachTo = "torso";
part.resonanceTags = {"magic", "combat"};
part.mass = 10.0f;
part.inertia = 5.0f;
// Uses: /assets/golems/parts/part_head.png
// Uses: /assets/golems/slots/slot_attachment.png
// Uses: /assets/golems/slots/slot_resonance.png
```

### CircuitRef

```cpp
// CircuitRef structure
CircuitRef circuit;
circuit.id = "basic";
circuit.modifiers = {"spellbus_modifier1", "spellbus_modifier2"};
// Uses: /assets/golems/circuits/circuit_basic.png
```

## Golem Types

### Golem Variants
- **Basic**: Basic golem
- **Stone**: Stone golem
- **Iron**: Iron golem
- **Crystal**: Crystal golem
- **Wood**: Wood golem
- **Arcane**: Arcane/magical golem

## Golem Parts

### Part Types
- **Head**: Golem head part
- **Torso**: Golem torso part
- **Arms**: Left and right arm parts
- **Legs**: Left and right leg parts
- **Hands**: Hand parts
- **Feet**: Foot parts

### Part Properties
- **Mass**: Part mass
- **Inertia**: Part inertia
- **Resonance Tags**: Part resonance tags
- **Attachment Point**: Where part attaches

## Golem Blueprints

### Blueprint Types
- **Basic**: Basic golem blueprint
- **Advanced**: Advanced golem blueprint
- **Custom**: Custom golem blueprint
- **Template**: Blueprint template

### Blueprint Structure
- **Parts**: List of part references
- **Circuits**: List of circuit references
- **Material Preset**: Material preset ID

## Golem Stances

### Stance Types
- **Idle**: Idle stance
- **Guard**: Guard stance
- **Patrol**: Patrol stance
- **Follow**: Follow stance
- **Combat**: Combat stance
- **Attack**: Attack stance

## Golem Commands

### Command Types
- **Guard**: Guard command
- **Patrol**: Patrol command
- **Follow**: Follow command
- **Attack**: Attack command
- **Stop**: Stop command
- **Idle**: Idle command

## Golem Circuits

### Circuit Types
- **Basic**: Basic circuit
- **Enhanced**: Enhanced circuit
- **Magic**: Magic circuit
- **Combat**: Combat circuit
- **Utility**: Utility circuit

### Circuit Modifiers
- Spellbus modifiers
- Internal modifiers
- Custom modifiers

## Golem Materials

### Material Types
- **Stone**: Stone material
- **Iron**: Iron material
- **Crystal**: Crystal material
- **Wood**: Wood material
- **Arcane**: Arcane material
- **Metal**: Metal material

## Golem Slots

### Slot Types
- **Empty**: Empty slot
- **Occupied**: Occupied slot
- **Attachment**: Attachment point
- **Resonance**: Resonance point

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateGolemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Register Blueprint

```cpp
GolemBlueprint bp;
bp.id = "my_golem";
bp.parts = {headPart, torsoPart, ...};
bp.circuits = {basicCircuit, ...};
bp.materialPresetId = "stone";
GolemRegistry::instance().registerBlueprint(bp);
```

### Step 3: Create Golem

```cpp
GolemId golemId = GolemManager::createFromBlueprint(root, bp, seed);
```

### Step 4: Command Golem

```cpp
GolemManager::commandGolem(root, golemEntityId, "guard", targetId);
```

### Step 5: Test in Game

Load the mod and test golem system in-game.

## Advanced Options

### Custom Golem Types

Edit `GenerateGolemAssets.ps1` to add custom golem types.

### Custom Parts

Add custom golem parts as needed.

### Custom Circuits

Add custom golem circuits with unique modifiers.

### Custom Materials

Add custom golem materials with unique properties.

## Tips

1. **Golem sprites**: Use 64x64 for golem sprites
2. **Part sprites**: Use 32x32 for main parts, 16x16 for small parts
3. **Blueprint icons**: Use 32x32 for blueprint icons
4. **Stance animations**: Use 8 frames for stance animations
5. **Summon effects**: Use 64x64 for particle effects
6. **Command indicators**: Make commands clearly visible
7. **Circuit icons**: Keep circuits distinct
8. **Material icons**: Make materials clearly identifiable

## Troubleshooting

### Golems Not Displaying

- Check golem sprite paths
- Verify sprites are in `assets/golems/sprites/`
- Ensure GolemRegistry is initialized

### Parts Not Attaching

- Check part sprite paths
- Verify sprites are in `assets/golems/parts/`
- Ensure slot system is configured

### Blueprints Not Working

- Check blueprint icon paths
- Verify icons are in `assets/golems/blueprints/`
- Ensure blueprint system is initialized

### Stances Not Changing

- Check stance animation paths
- Verify animations are in `assets/golems/stances/`
- Ensure animation system is initialized

### Commands Not Executing

- Check command indicator paths
- Verify indicators are in `assets/golems/commands/`
- Ensure command system is configured

---

*Part of the Starbound Ollama Asset Generator suite*
