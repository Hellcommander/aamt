# Animation Sprite Generation Guide

Generate animation spritesheets for all mod animations using Ollama AI.

## Quick Start

```powershell
# Generate all animation spritesheets
.\GenerateAnimationSprites.ps1

# Use C++ backend for better quality
.\GenerateAnimationSprites.ps1 -UseCppBackend

# Update animation files to reference new spritesheets
.\UpdateAnimationSprites.ps1
```

## What Gets Generated

### Animation Spritesheets (5+ items)

1. **magitech_device** - Magitech device activation (6 frames, 64x64)
2. **spell_cast** - Spell casting animation (8 frames, 48x48)
3. **magic_aura** - Magic aura status effect (4 frames, 32x32)
4. **alchemical_reaction** - Alchemical reaction (10 frames, 48x48)
5. **portal_opening** - Portal opening animation (12 frames, 64x64)

## Output Structure

```
assets/
└── animations/
    ├── magitech_device/
    │   ├── magitech_device.png      # Spritesheet (6 frames × 64×64 = 384×64)
    │   ├── magitech_device.animation # Animation definition
    │   └── magitech_device.frames    # Frame grid metadata
    ├── spell_cast/
    │   ├── spell_cast.png
    │   ├── spell_cast.animation
    │   └── spell_cast.frames
    └── ... (all other animations)
```

## Animation Types

### DeviceActivation
- **Style**: Pulsing energy, device powering up
- **Use**: Magitech devices, crafting stations
- **Example**: magitech_device

### SpellCast
- **Style**: Growing magical energy, swirling particles
- **Use**: Spell casting, magical effects
- **Example**: spell_cast, alchemical_reaction, portal_opening

### StatusEffect
- **Style**: Shimmering energy field, pulsing glow
- **Use**: Status effects, buffs, debuffs
- **Example**: magic_aura

## Integration

### Using Generated Animations

**In .animation files:**
```json
{
  "animatedParts": {
    "parts": {
      "device": {
        "properties": {
          "image": "/animations/magitech_device/magitech_device.png"
        }
      }
    }
  }
}
```

**In particles:**
```json
{
  "kind": "magicparticle",
  "definition": {
    "type": "animated",
    "animation": "/animations/spell_cast/spell_cast.animation"
  }
}
```

**In Lua:**
```lua
local animation = "/animations/magic_aura/magic_aura.animation"
animator.setAnimationState("aura", "active")
```

## Workflow

### Step 1: Generate Animation Spritesheets

```powershell
.\GenerateAnimationSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

This creates:
- PNG spritesheets with all frames
- `.animation` files with timing and frame data
- `.frames` files with grid metadata

### Step 2: Update Animation Files

```powershell
.\UpdateAnimationSprites.ps1
```

This updates:
- `animations/magitech/magitech_device.animation`
- `animations/magitech/mt_magitech_device.animation`
- Other animation files to reference new spritesheets

### Step 3: Test in Game

Load the mod and verify animations play correctly.

## Customization

### Add More Animations

Edit `GenerateAnimationSprites.ps1` and add to `$animations` array:

```powershell
@{
    Id = "my_animation"
    Name = "My Animation"
    Description = "Detailed description of animation appearance"
    FrameCount = 8
    AnimationCycle = 0.6
    AnimationType = "SpellCast"
    FrameSize = @(48, 48)
}
```

### Adjust Frame Counts

Different animation types need different frame counts:
- **Quick effects**: 4-6 frames
- **Standard animations**: 8-10 frames
- **Complex sequences**: 12-16 frames

### Animation Timing

- **Fast animations**: 0.2-0.4 seconds (sparks, hits)
- **Standard**: 0.5-0.8 seconds (spell casts, activations)
- **Slow**: 1.0-2.0 seconds (portals, transformations)

## Spritesheet Layout

Animations use horizontal strip layout:

```
┌────┬────┬────┬────┬────┬────┐
│ F1 │ F2 │ F3 │ F4 │ F5 │ F6 │  ← 6 frames at 64×64 = 384×64 spritesheet
└────┴────┴────┴────┴────┴────┘
```

Each frame must be exactly the same size.

## Tips

1. **Match frame count to animation complexity**: Simple effects need fewer frames
2. **Time cycles appropriately**: Match AnimationCycle to visual effect duration
3. **Use appropriate sizes**: 32×32 for small effects, 64×64 for devices
4. **Test in-game**: Verify animations loop smoothly
5. **Use C++ backend**: Better quality for final assets

## Troubleshooting

### Animations Not Playing

- Check `.animation` file references correct PNG path
- Verify `.frames` file has correct dimensions
- Ensure frame count matches spritesheet

### Poor Quality

- Use `-UseCppBackend` for better spritesheets
- Increase frame count for smoother animation
- Provide more detailed prompts

### Timing Issues

- Adjust `AnimationCycle` to match desired speed
- Test different cycle values
- Match cycle to particle TimeToLive for seamless loops

---

*Part of the Starbound Ollama Asset Generator suite*
