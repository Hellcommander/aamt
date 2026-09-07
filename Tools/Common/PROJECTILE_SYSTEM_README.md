# Transcendence Projectile System

A data-driven projectile generation system that separates visuals, physics/AI, damage/effects, and export configuration for consistent authoring of missiles, lasers, ballistics, and exotic projectiles.

## Overview

The system uses a JSON registry to define projectiles, then generates:
- **Visuals**: Blender-rendered spritesheets with procedural materials
- **Physics**: Transcendence-compatible physics parameters
- **Damage**: Damage types, area effects, and status effects
- **FX**: Trails, particles, lighting, and sound
- **Export**: Transcendence XML/UNID files

## Core Components

### 1. Registry Schema (`projectile_registry_schema.json`)

Defines the structure for projectile definitions. Each projectile includes:
- `id`: Unique identifier
- `type`: Missile, Laser, Ballistic, or Exotic
- `visual`: Sprite size, rotations, frames, palette, materials
- `physics`: Speed, acceleration, homing, gravity, drag, lifetime
- `damage`: Base damage, damage type, area radius, status effects
- `fx`: Trail, impact particles, light emission, sound
- `export`: XML template, UNID, resource paths

### 2. Blender Renderer (`blender_projectile_renderer.py`)

Renders projectiles with:
- Procedural material generation based on registry config
- Rotation spritesheets (1-120 rotations)
- Animation frames
- Normal maps and distortion maps (optional)
- Per-frame PNG export for editing

### 3. XML Exporter (`transcendence_projectile_exporter.py`)

Converts registry entries to Transcendence XML:
- Maps physics fields to engine parameters
- Generates UNID entries
- Creates proper XML structure for ProjectileType, MissileType, or BeamType

### 4. Pipeline Orchestrator (`ProjectileSystemGenerator.ps1`)

Main PowerShell script that:
- Reads registry JSON
- Calls Blender for rendering
- Calls Python exporter for XML generation
- Packages assets for game use

## Usage

### Basic Usage

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Output"
```

### Generate Specific Projectile

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -ProjectileId "plasma_bolt" -OutputDir "Output"
```

### Skip Rendering (XML Only)

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -SkipRender -OutputDir "Output"
```

### With AI Material Generation

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -UseAI -OllamaModel "llama3.2" -OutputDir "Output"
```

### Generate Complete Weapon XML

```powershell
python weapon_generator_from_projectile.py --registry projectile_registry.json --output-dir Weapons --create-items
```

This generates complete `ItemType` elements with embedded `Weapon` definitions ready for use in Transcendence.

## Registry Example

See `projectile_registry_example.json` for complete examples of:
- **Plasma Bolt** (Laser type): Simple energy projectile with glow
- **Homing Missile** (Missile type): Guided projectile with exhaust trail
- **Railgun Slug** (Ballistic type): High-speed projectile with ricochet/penetration
- **Phase Projectile** (Exotic type): Complex projectile with distortion effects

## Projectile Types

### Missile
- **Core Behavior**: Guided, acceleration, turn rate
- **Visual Approach**: Animated sprite + exhaust trail
- **Typical Physics**: `homingStrength > 0`, `acceleration > 0`, `turnRate > 0`

### Laser
- **Core Behavior**: Instant/hit-scan or beam with duration
- **Visual Approach**: Stretched sprite or shader beam
- **Typical Physics**: High speed, no acceleration, `rotations = 1`

### Ballistic
- **Core Behavior**: Projectile arc, gravity, ricochet rules
- **Visual Approach**: Single-frame sprite + rotation frames
- **Typical Physics**: `gravity > 0`, `ricochet.enabled = true`

### Exotic
- **Core Behavior**: Teleport, phase, area distortions
- **Visual Approach**: Animated FX + distortion maps
- **Typical Physics**: Custom behaviors, `distortionMap = true`

## Design Principles

### Deterministic Outputs
Same registry → same sprites/behavior. Registry is the single source of truth.

### Editable Assets
- Blender saves `.blend` files with node groups
- Per-frame PNGs exported for manual editing
- Registry JSON is human-readable and version-controlled

### Data First
Behavior driven by JSON profiles, not hardcoded. Physics interpreter maps registry fields to Transcendence scripting.

### Transcendence Compatibility
Follows engine modding patterns and exports to XML/UNID format.

## File Structure

```
Tools/
├── projectile_registry_schema.json       # JSON schema definition
├── projectile_registry_example.json      # Example registry entries
├── projectile_templates.json             # Pre-built templates for each type
├── blender_projectile_renderer.py       # Blender rendering script
├── transcendence_projectile_exporter.py # Effect/XML exporter
├── weapon_generator_from_projectile.py  # Complete Weapon XML generator
├── ai_material_generator.py             # AI material spec generator
├── ProjectileSystemGenerator.ps1        # Main orchestrator
└── PROJECTILE_SYSTEM_README.md         # This file
```

## Output Structure

```
Output/
├── Spritesheets/          # Rendered PNG spritesheets
│   └── projectile_id.png
├── XML/                   # Transcendence XML files
│   └── projectile_id.xml
└── Resources/             # Game-ready assets
    └── projectile_id.png
```

## Advanced Features

### Normal Maps
Set `visual.normalMap: true` in registry to generate normal maps for depth/shading.

### Distortion Maps
Set `visual.distortionMap: true` for exotic projectiles with visual distortion effects.

### Animation Hints
Registry includes `animationHints` for:
- Pulse animation
- Rotation animation
- Trail length
- Particle count

### Status Effects
Define status effects in `damage.statusEffects`:
- `blind`, `disintegrate`, `emp`, `radiation`, `paralyze`
- `shieldDisrupt`, `armorDisrupt`, `deviceDisrupt`, `weaponDisrupt`, `shatter`

## Performance Considerations

- Many particles/shaders can impact CPU/GPU
- System provides low-quality fallbacks
- LOD (Level of Detail) support for complex projectiles
- Registry allows quality tiers: Standard, High, Ultra

## Testing

Automated in-game smoke tests can spawn each projectile and log:
- Collisions
- Lifetimes
- Damage application
- Status effect application

## Versioning

Registry schema is versioned. Current version: `1.0.0`. Future schema changes will maintain backward compatibility where possible.

## Troubleshooting

### Blender Not Found
- Specify `-BlenderPath` parameter
- Or use `-SkipRender` to skip rendering

### Python Not Found
- Install Python 3.x
- Ensure Python is in PATH
- Or use `-SkipExport` to skip XML generation

### Registry Validation
- Validate JSON against schema before running
- Check required fields: `id`, `type`, `visual`, `physics`, `damage`, `export`

## Future Enhancements

- Preview GUI for live preview + iterative AI tweak loop
- Batch registry processing
- Integration with weapon system
- Advanced shader support
- Particle system integration

