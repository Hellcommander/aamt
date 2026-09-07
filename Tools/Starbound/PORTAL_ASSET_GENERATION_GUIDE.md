# Unified Portal System Asset Generation Guide

Generate assets for the Unified Portal System including sprites, animations, particle effects, and textures.

## Quick Start

```powershell
# Generate all portal assets
.\GeneratePortalAssets.ps1

# Use C++ backend for better quality
.\GeneratePortalAssets.ps1 -UseCppBackend

# Or generate everything including portal assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Portal Sprites (12 sprites)

1. **portal_standard** - Standard portal
2. **portal_dimensional** - Dimensional portal
3. **portal_temporal** - Temporal portal
4. **portal_quantum** - Quantum portal
5. **portal_blink** - Blink portal
6. **portal_alt_universe** - Alt universe portal
7. **portal_chaos** - Chaos portal
8. **portal_mirror** - Mirror portal
9. **portal_void** - Void portal
10. **portal_planetary** - Planetary portal
11. **portal_orbital** - Orbital portal
12. **portal_stellar** - Stellar portal

### Portal Animations (5 animations)

1. **portal_opening** - Opening animation (8 frames, 0.8s)
2. **portal_closing** - Closing animation (8 frames, 0.8s)
3. **portal_active** - Active animation (12 frames, 1.5s)
4. **portal_unstable** - Unstable animation (10 frames, 0.6s)
5. **portal_charging** - Charging animation (6 frames, 1.0s)

### Portal Particle Effects (6 effects)

1. **portal_particle_standard** - Standard portal particles
2. **portal_particle_dimensional** - Dimensional portal particles
3. **portal_particle_temporal** - Temporal portal particles
4. **portal_particle_quantum** - Quantum portal particles
5. **portal_particle_void** - Void portal particles
6. **portal_particle_chaos** - Chaos portal particles

### Portal Glow Textures (5 textures)

1. **portal_glow_standard** - Standard portal glow
2. **portal_glow_dimensional** - Dimensional portal glow
3. **portal_glow_temporal** - Temporal portal glow
4. **portal_glow_quantum** - Quantum portal glow
5. **portal_glow_void** - Void portal glow

### Portal Frame Textures (4 textures)

1. **portal_frame_standard** - Standard portal frame
2. **portal_frame_ancient** - Ancient portal frame
3. **portal_frame_tech** - Tech portal frame
4. **portal_frame_magic** - Magic portal frame

## Total: ~32 Assets

## Output Structure

```
assets/
└── portals/
    ├── portal_standard.png
    ├── portal_dimensional.png
    ├── ... (all portal sprites)
    ├── portal_opening/
    │   ├── portal_opening.png
    │   ├── portal_opening.animation
    │   └── portal_opening.frames
    ├── ... (all portal animations)
    ├── portal_particle_standard.particle
    ├── ... (all portal particles)
    ├── portal_glow_standard.png
    ├── ... (all portal glows)
    ├── portal_frame_standard.png
    └── ... (all portal frames)
```

## Integration

### Portal Creation

After generating assets, create portals with asset references:

```lua
-- Create standard portal
local portalId = UnifiedPortalModule:createSimplePortal({100, 200, 0}, 30)

-- Set portal effects
UnifiedPortalModule:setPortalEffects(portalId, {
    particleEffect = "/portals/portal_particle_standard.particle",
    glowTexture = "/portals/portal_glow_standard.png",
    frameTexture = "/portals/portal_frame_standard.png"
})
```

### Portal Animations

```lua
-- Set portal animation based on state
local state = UnifiedPortalModule:getPortalState(portalId)
if state == "OPENING" then
    UnifiedPortalModule:setPortalAnimation(portalId, "/portals/portal_opening/portal_opening.animation")
elseif state == "CLOSING" then
    UnifiedPortalModule:setPortalAnimation(portalId, "/portals/portal_closing/portal_closing.animation")
elseif state == "OPEN" then
    UnifiedPortalModule:setPortalAnimation(portalId, "/portals/portal_active/portal_active.animation")
end
```

### Portal Types

Each portal type has matching assets:

- **Standard**: Blue/purple energy
- **Dimensional**: Purple/magenta energy
- **Temporal**: Green energy, clockwork
- **Quantum**: Blue energy, quantum effects
- **Blink**: Yellow/cyan energy
- **Alt Universe**: Dark energy
- **Chaos**: Chaotic energy
- **Mirror**: Reflective surface
- **Void**: Dark void energy
- **Planetary**: Blue energy
- **Orbital**: Cyan energy
- **Stellar**: Golden energy

## Portal States

Portals have different states that use different animations:

- **CLOSED**: No animation
- **OPENING**: `portal_opening` animation
- **OPEN**: `portal_active` animation
- **CLOSING**: `portal_closing` animation
- **UNSTABLE**: `portal_unstable` animation
- **CHARGING**: `portal_charging` animation

## Workflow

### Step 1: Generate Assets

```powershell
.\GeneratePortalAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Portals

Create portals with appropriate asset references.

### Step 3: Configure Effects

Set up particle effects, glows, and frames for each portal.

### Step 4: Test in Game

Load the mod and test portals in-game.

## Advanced Options

### Custom Portal Types

Edit `GeneratePortalAssets.ps1` to add custom portal types:

```powershell
@{
    Id = "custom_portal"
    Name = "Custom Portal"
    Description = "Custom portal description"
}
```

### Custom Animations

Add custom portal animations to the `$portalAnimations` array.

### Custom Effects

Add custom particle effects to the `$portalParticles` array.

## Tips

1. **Portal size**: Use 64x64 for portal sprites
2. **Animation frames**: 6-12 frames work well for portal animations
3. **Animation timing**: Match animation cycle to portal state duration
4. **Particle effects**: Create distinct effects for each portal type
5. **Glow textures**: Use emissive maps for glow effects

## Troubleshooting

### Portals Not Appearing

- Check portal definitions reference correct asset paths
- Verify sprites are in `assets/portals/`
- Check portal system is initialized

### Animations Not Playing

- Check `.animation` file references correct PNG
- Verify `.frames` file has correct dimensions
- Ensure animation cycle timing is appropriate

### Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in portal definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
