# Creature System Asset Generation Guide

Generate assets for the Creature System including spell casting animations, creature sprites, and spell effects.

## Quick Start

```powershell
# Generate all creature assets
.\GenerateCreatureAssets.ps1

# Use C++ backend for better quality
.\GenerateCreatureAssets.ps1 -UseCppBackend

# Or generate everything including creature assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Creature Spell Casting Animations (5 animations)

1. **poptop_mouth_open** - Poptop mouth opening animation (8 frames)
2. **poptop_mouth_cast** - Poptop mouth casting spell animation (6 frames)
3. **poptop_mouth_close** - Poptop mouth closing animation (8 frames)
4. **creature_spell_charge** - Generic creature spell charging animation (10 frames)
5. **creature_spell_release** - Generic creature spell release animation (8 frames)

### Creature Spell Effects (4 effects)

1. **creature_spell_effect_poptop** - Poptop spell casting particle effect
2. **creature_spell_effect_generic** - Generic creature spell casting particle effect
3. **creature_spell_charge_effect** - Creature spell charging particle effect
4. **creature_spell_release_effect** - Creature spell release particle effect

### Creature Sprites (3 sprites)

1. **creature_poptop_base** - Poptop base sprite
2. **creature_poptop_mouth_closed** - Poptop with mouth closed
3. **creature_poptop_mouth_open** - Poptop with mouth open

## Total: ~12 Assets

## Output Structure

```
assets/
├── creatures/
│   ├── animations/
│   │   ├── poptop_mouth_open.png
│   │   ├── poptop_mouth_open.animation
│   │   ├── poptop_mouth_open.frames
│   │   ├── poptop_mouth_cast.png
│   │   ├── poptop_mouth_cast.animation
│   │   ├── poptop_mouth_cast.frames
│   │   ├── poptop_mouth_close.png
│   │   ├── poptop_mouth_close.animation
│   │   ├── poptop_mouth_close.frames
│   │   ├── creature_spell_charge.png
│   │   ├── creature_spell_charge.animation
│   │   ├── creature_spell_charge.frames
│   │   ├── creature_spell_release.png
│   │   ├── creature_spell_release.animation
│   │   └── creature_spell_release.frames
│   ├── effects/
│   │   ├── creature_spell_effect_poptop.particle
│   │   ├── creature_spell_effect_generic.particle
│   │   ├── creature_spell_charge_effect.particle
│   │   └── creature_spell_release_effect.particle
│   └── sprites/
│       ├── creature_poptop_base.png
│       ├── creature_poptop_mouth_closed.png
│       └── creature_poptop_mouth_open.png
```

## Integration

### Poptop Mouth Animation

```cpp
// PoptopMouthAnimator triggers mouth opening animation
PoptopMouthAnimator::Animate(entityId, spellArgs);
// Uses: /creatures/animations/poptop_mouth_open.animation
// Shows: /creatures/effects/creature_spell_effect_poptop.particle
```

### Creature Spell Casting

```lua
-- Trigger creature spell casting animation
CreatureSystem:castSpell(creatureId, spellType)
-- Uses: /creatures/animations/creature_spell_charge.animation
-- Shows: /creatures/effects/creature_spell_charge_effect.particle
-- Then: /creatures/animations/creature_spell_release.animation
-- Shows: /creatures/effects/creature_spell_release_effect.particle
```

### Creature Sprites

```lua
-- Load creature sprite
local sprite = loadSprite("/creatures/sprites/creature_poptop_base.png")
-- Switch to mouth open sprite when casting
local mouthOpen = loadSprite("/creatures/sprites/creature_poptop_mouth_open.png")
```

## Animation Sequences

### Poptop Spell Casting Sequence

1. **Mouth Open** (8 frames) - Poptop opens mouth wide
2. **Mouth Cast** (6 frames) - Spell energy builds in mouth
3. **Spell Release** - Particle effect bursts from mouth
4. **Mouth Close** (8 frames) - Poptop closes mouth

### Generic Creature Spell Casting Sequence

1. **Spell Charge** (10 frames) - Energy builds around creature
2. **Charge Effect** - Particle effect shows energy buildup
3. **Spell Release** (8 frames) - Energy releases from creature
4. **Release Effect** - Particle effect shows energy burst

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateCreatureAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Integrate Animations

Link animations to creature spell casting system.

### Step 3: Test in Game

Load the mod and test creature spell casting in-game.

## Advanced Options

### Custom Creature Animations

Edit `GenerateCreatureAssets.ps1` to add custom creature animations:

```powershell
@{
    Id = "creature_custom_animation"
    Name = "Custom Creature Animation"
    Desc = "Custom animation description, X frames, 32x32"
}
```

### Custom Creature Types

Add custom creature sprites to the `$creatureSprites` array.

### Custom Spell Effects

Add custom spell effects to the `$creatureSpellEffects` array.

## Tips

1. **Animation frames**: Use 6-10 frames for smooth animations
2. **Sprite size**: Use 32x32 for creature sprites
3. **Animation timing**: Match animation cycle to spell casting duration
4. **Particle effects**: Create distinct effects for each spell type
5. **Mouth animations**: Ensure smooth transition between open/close states

## Troubleshooting

### Animations Not Playing

- Check animation file paths in creature definitions
- Verify animations are in `assets/creatures/animations/`
- Ensure animation system is initialized

### Effects Not Appearing

- Verify particle files are in correct location
- Check effect paths in spell definitions
- Ensure particle system is initialized

### Sprites Not Loading

- Check sprite paths in creature definitions
- Verify sprites are in `assets/creatures/sprites/`
- Ensure sprite system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
