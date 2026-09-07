# Transcendence Asset Generator - Master System Overview

Complete overview of all asset generation systems and their integration.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Transcendence Asset Generator                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Projectiles │  │ Shields/Armor│  │      FX      │     │
│  │   System     │  │    System    │  │   System     │     │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘     │
│         │                  │                 │             │
│         └──────────────────┼─────────────────┘             │
│                            │                               │
│                   ┌────────▼────────┐                      │
│                   │  Shield Auras   │                      │
│                   │     System      │                      │
│                   └─────────────────┘                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## System Components

### 1. Projectile System
**Purpose**: Generate data-driven projectiles (missiles, lasers, ballistics, exotic)

**Key Files**:
- `projectile_registry_schema.json` - JSON schema
- `projectile_registry_example.json` - Examples
- `blender_projectile_renderer.py` - Blender rendering
- `transcendence_projectile_exporter.py` - XML export
- `weapon_generator_from_projectile.py` - Weapon XML generation
- `ProjectileSystemGenerator.ps1` - Main orchestrator

**Outputs**:
- Projectile spritesheets (PNG)
- Transcendence XML files
- Weapon definitions

**Integration Points**:
- Triggers FX on impact
- Influenced by shield auras
- Applies damage to shields/armor

### 2. Shield/Armor System
**Purpose**: Generate shields, armor plating, runtime state, and UI

**Key Files**:
- `shield_armor_registry_schema.json` - JSON schema
- `shield_armor_example.json` - Examples
- `shield_runtime_model.py` - Runtime state
- `blender_shield_renderer.py` - Blender rendering
- `transcendence_shield_armor_exporter.py` - XML export
- `ShieldArmorSystemGenerator.ps1` - Main orchestrator

**Outputs**:
- Shield spritesheets (PNG)
- Armor overlay textures
- Transcendence XML files
- UI data binding models

**Integration Points**:
- Scales with shield HP
- Triggers FX on break
- Can have associated auras
- Receives damage from projectiles

### 3. Nova Drift FX System
**Purpose**: Generate high-energy special effects with layered composition

**Key Files**:
- `nova_drift_fx_registry_schema.json` - JSON schema
- `nova_drift_fx_example.json` - Examples
- `blender_nova_drift_fx_renderer.py` - Blender rendering
- `particle_choreography_system.py` - Particle motion
- `transcendence_fx_exporter.py` - XML export
- `NovaDriftFXGenerator.ps1` - Main orchestrator

**Outputs**:
- FX spritesheets (PNG)
- Distortion maps
- Particle profiles
- Transcendence XML files

**Integration Points**:
- Triggered by projectile impacts
- Triggered by shield breaks
- Used in weapon muzzle flashes
- Used in explosion effects

### 4. Shield Aura System
**Purpose**: Generate solar wind shield auras with orbital particles and projectile influence

**Key Files**:
- `shield_aura_registry_schema.json` - JSON schema
- `shield_aura_example.json` - Examples
- `SHIELD_AURA_SHADER_RECIPES.md` - Shader code
- `projectile_orbit_behavior.py` - Orbit behavior
- `blender_shield_aura_renderer.py` - Blender rendering
- `transcendence_shield_aura_exporter.py` - XML export
- `ShieldAuraGenerator.ps1` - Main orchestrator

**Outputs**:
- Aura spritesheets (PNG)
- Distortion maps
- Transcendence XML files

**Integration Points**:
- Scales with shield HP
- Influences projectile trajectories
- Visual feedback for shield state

## Data Flow

### Asset Generation Pipeline

```
Registry JSON
    ↓
[Validation]
    ↓
[AI Enhancement] (optional)
    ↓
[Blender Rendering]
    ↓
[Particle Generation]
    ↓
[XML Export]
    ↓
[Asset Packaging]
    ↓
Transcendence Extension
```

### Runtime Integration

```
Game Loop
    ↓
[Update Shields] → [Update Auras] → [Update Projectiles]
    ↓                    ↓                    ↓
[Shield HP]      [Aura Visuals]    [Orbit Behavior]
    ↓                    ↓                    ↓
[UI Updates]      [Distortion]      [Damage Application]
    ↓                    ↓                    ↓
[FX Triggers] ←─────────┴────────────────────┘
```

## Registry File Types

### Projectile Registry
```json
{
  "version": "1.0.0",
  "projectiles": [
    {
      "id": "plasma_bolt",
      "type": "Laser",
      "visual": {...},
      "physics": {...},
      "damage": {...},
      "fx": {...},
      "export": {...}
    }
  ]
}
```

### Shield/Armor Registry
```json
{
  "version": "1.0.0",
  "shields": [...],
  "armor": [...]
}
```

### FX Registry
```json
{
  "version": "1.0.0",
  "effects": [
    {
      "id": "nova_burst_01",
      "type": "fx",
      "style": "novaDrift",
      "visual": {...},
      "particles": {...},
      "timing": {...},
      "export": {...}
    }
  ]
}
```

### Aura Registry
```json
{
  "version": "1.0.0",
  "auras": [
    {
      "id": "solar_wind_shield",
      "type": "shieldAura",
      "visual": {...},
      "particles": {...},
      "behavior": {...},
      "export": {...}
    }
  ]
}
```

## Common Patterns

### Pattern 1: Projectile with Impact FX

```json
{
  "id": "plasma_bolt",
  "fx": {
    "impactParticles": {
      "enabled": true,
      "count": 12
    }
  },
  "export": {
    "resourcePaths": {
      "impactFX": "Resources/FX/plasma_impact"
    }
  }
}
```

### Pattern 2: Shield with Aura

```json
{
  "id": "energy_shield_mk2",
  "visual": {
    "auraProfile": "solar_wind_shield"
  }
}
```

### Pattern 3: Shield Break FX

```json
{
  "id": "energy_shield_mk2",
  "fx": {
    "breakParticleCount": 30,
    "breakFX": "shield_break_explosion"
  }
}
```

## File Organization

### Tools Directory
```
Tools/
├── Registry Schemas/
│   ├── projectile_registry_schema.json
│   ├── shield_armor_registry_schema.json
│   ├── nova_drift_fx_registry_schema.json
│   └── shield_aura_registry_schema.json
├── Examples/
│   ├── projectile_registry_example.json
│   ├── shield_armor_example.json
│   ├── nova_drift_fx_example.json
│   └── shield_aura_example.json
├── Blender Scripts/
│   ├── blender_projectile_renderer.py
│   ├── blender_shield_renderer.py
│   ├── blender_nova_drift_fx_renderer.py
│   └── blender_shield_aura_renderer.py
├── Exporters/
│   ├── transcendence_projectile_exporter.py
│   ├── transcendence_shield_armor_exporter.py
│   ├── transcendence_fx_exporter.py
│   └── transcendence_shield_aura_exporter.py
├── Runtime/
│   ├── shield_runtime_model.py
│   └── projectile_orbit_behavior.py
├── Generators/
│   ├── ProjectileSystemGenerator.ps1
│   ├── ShieldArmorSystemGenerator.ps1
│   ├── NovaDriftFXGenerator.ps1
│   └── ShieldAuraGenerator.ps1
└── Documentation/
    ├── PROJECTILE_SYSTEM_README.md
    ├── SHIELD_ARMOR_SYSTEM_README.md
    ├── NOVA_DRIFT_FX_README.md
    ├── SHIELD_AURA_README.md
    └── SYSTEM_INTEGRATION_GUIDE.md
```

## Quick Reference

### Generate All Assets

```powershell
# Projectiles
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Assets/Projectiles"

# Shields/Armor
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -OutputDir "Assets/ShieldsArmor"

# FX
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Assets/FX"

# Auras
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Assets/Auras"
```

### Validate Registries

```powershell
python validate_registry.py --registry projectile_registry.json --schema projectile_registry_schema.json
python validate_registry.py --registry shield_armor_example.json --schema shield_armor_registry_schema.json
python validate_registry.py --registry nova_drift_fx_example.json --schema nova_drift_fx_registry_schema.json
python validate_registry.py --registry shield_aura_example.json --schema shield_aura_registry_schema.json
```

## Best Practices

1. **Start Small**: Generate one asset type at a time
2. **Validate First**: Always validate registry files before generation
3. **Test Individually**: Test each asset in-game before batch generation
4. **Version Control**: Keep registry files in version control
5. **Documentation**: Document custom entries and modifications
6. **Naming**: Use consistent naming conventions
7. **UNID Management**: Use consistent UNID prefixes
8. **Resource Organization**: Organize resources by type

## Troubleshooting

See `SYSTEM_INTEGRATION_GUIDE.md` for detailed troubleshooting.

## Next Steps

1. Review system documentation for each component
2. Create your registry files
3. Generate test assets
4. Integrate into Transcendence extension
5. Iterate and refine

