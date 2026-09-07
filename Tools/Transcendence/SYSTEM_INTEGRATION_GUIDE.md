# Transcendence Asset Generator - System Integration Guide

Complete guide for integrating all asset generation systems: Projectiles, Shields/Armor, FX, and Shield Auras.

## System Overview

The Transcendence Asset Generator consists of four main systems:

1. **Projectile System**: Data-driven projectiles with visual, physics, damage, and FX
2. **Shield/Armor System**: Shield visuals, armor plating, runtime state, and UI
3. **Nova Drift FX System**: High-energy special effects with layered composition
4. **Shield Aura System**: Solar wind auras with orbital particles and projectile influence

## Quick Start

### 1. Generate Projectiles

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Output/Projectiles"
```

### 2. Generate Shields and Armor

```powershell
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -ParticleProfilePath "particle_profiles_example.json" -OutputDir "Output/ShieldsArmor"
```

### 3. Generate FX Effects

```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Output/FX"
```

### 4. Generate Shield Auras

```powershell
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Output/Auras"
```

## Integration Workflow

### Complete Asset Generation Pipeline

```powershell
# 1. Generate all projectiles
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Assets/Projectiles"

# 2. Generate shields and armor
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -OutputDir "Assets/ShieldsArmor"

# 3. Generate FX for projectiles and shields
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Assets/FX"

# 4. Generate shield auras
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Assets/Auras"

# 5. Package everything for Transcendence
# (Copy all XML and resources to your extension directory)
```

## Cross-System Integration

### Projectiles → FX

Projectiles can trigger FX on impact:

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

### Shields → Auras

Shields can have associated auras:

```json
{
  "id": "energy_shield_mk2",
  "visual": {
    "auraProfile": "solar_wind_shield"
  }
}
```

### Projectiles → Shield Aura

Projectiles get influenced by shield auras:

```python
from projectile_orbit_behavior import update_projectile_in_aura

# In game loop
for projectile in projectiles:
    if shield_aura.active:
        projectile = update_projectile_in_aura(
            projectile,
            player_position,
            aura_behavior,
            delta_time
        )
```

### FX → Shields

FX can be triggered on shield breaks:

```json
{
  "id": "energy_shield_mk2",
  "fx": {
    "breakParticleCount": 30,
    "breakFX": "shield_break_explosion"
  }
}
```

## Registry File Organization

### Recommended Structure

```
Registry/
├── projectiles/
│   ├── projectile_registry.json
│   └── projectile_registry_example.json
├── shields_armor/
│   ├── shield_armor_example.json
│   └── particle_profiles_example.json
├── fx/
│   ├── nova_drift_fx_example.json
│   └── particle_profiles_example.json
└── auras/
    └── shield_aura_example.json
```

## Output Directory Structure

```
Output/
├── Projectiles/
│   ├── Spritesheets/
│   ├── XML/
│   └── Resources/
├── ShieldsArmor/
│   ├── Spritesheets/
│   ├── XML/
│   ├── Resources/
│   └── Particles/
├── FX/
│   ├── Spritesheets/
│   ├── XML/
│   ├── Resources/
│   └── Particles/
└── Auras/
    ├── Spritesheets/
    ├── XML/
    └── Resources/
```

## Transcendence Extension Integration

### XML File Organization

```
YourExtension/
├── YourExtension.xml          # Main extension file
├── Projectiles/
│   ├── projectile_plasma_bolt.xml
│   └── projectile_homing_missile.xml
├── Shields/
│   ├── shield_energy_mk2.xml
│   └── armor_reinforced_mk1.xml
├── FX/
│   ├── fx_nova_burst.xml
│   └── fx_plasma_explosion.xml
└── Auras/
    └── aura_solar_wind_shield.xml
```

### Resource Paths

```
YourExtension/
└── Resources/
    ├── Projectiles/
    │   ├── plasma_bolt.png
    │   └── homing_missile.png
    ├── Shields/
    │   ├── energy_shield_mk2.png
    │   └── reinforced_plating_overlay.png
    ├── FX/
    │   ├── nova_burst_01.png
    │   └── plasma_explosion.png
    └── Auras/
        └── solar_wind_shield.png
```

## Runtime Integration Examples

### Python (for testing/validation)

```python
from shield_runtime_model import CreateShieldInstance, DamageEvent
from projectile_orbit_behavior import update_projectile_in_aura, AuraBehavior
from shield_aura_example import load_aura_registry

# Load shield
shield_profile = {...}  # From registry
shield = CreateShieldInstance(shield_profile)

# Load aura
aura_registry = load_aura_registry("shield_aura_example.json")
aura_data = aura_registry['auras'][0]
aura_behavior = AuraBehavior(**aura_data['behavior'])

# Game loop
def update_game(dt):
    # Update shield
    shield.Update(dt)
    
    # Update projectiles
    for projectile in projectiles:
        # Apply damage if collision
        if check_collision(projectile, player):
            damage = DamageEvent(amount=projectile.damage, damageType=projectile.damageType)
            remaining = shield.ApplyDamage(damage)
            if remaining > 0:
                # Apply to hull
                apply_hull_damage(remaining)
        
        # Update projectile orbit if in aura
        if shield.currentStrength > 0:
            projectile = update_projectile_in_aura(
                projectile,
                player.position,
                aura_behavior,
                dt
            )
        
        # Update projectile position
        projectile.position = (
            projectile.position[0] + projectile.velocity[0] * dt,
            projectile.position[1] + projectile.velocity[1] * dt,
            projectile.position[2] + projectile.velocity[2] * dt
        )
```

### C# (Unity/Similar)

```csharp
public class TranscendenceAssetManager : MonoBehaviour {
    public ShieldInstance shield;
    public AuraBehavior auraBehavior;
    public List<Projectile> projectiles;
    
    void Update() {
        float dt = Time.deltaTime;
        
        // Update shield
        shield.Update(dt);
        
        // Update shield aura
        if (shield.currentStrength > 0) {
            UpdateAuraVisuals(shield.currentStrength / shield.maxStrength);
        }
        
        // Update projectiles
        foreach (var proj in projectiles) {
            // Check collision
            if (Vector3.Distance(proj.position, transform.position) < 0.5f) {
                var damage = new DamageEvent {
                    amount = proj.damage,
                    damageType = proj.damageType
                };
                float remaining = shield.ApplyDamage(damage);
                if (remaining > 0) {
                    // Apply to hull
                }
            }
            
            // Update orbit if in aura
            if (shield.currentStrength > 0 && auraBehavior.projectileInfluence) {
                proj = UpdateProjectileInAura(proj, transform.position, auraBehavior, dt);
            }
            
            // Update position
            proj.position += proj.velocity * dt;
        }
    }
}
```

## Testing and Validation

### Validate Registry Files

```powershell
# Validate JSON schemas
python validate_registry.py --registry projectile_registry.json --schema projectile_registry_schema.json
python validate_registry.py --registry shield_armor_example.json --schema shield_armor_registry_schema.json
python validate_registry.py --registry nova_drift_fx_example.json --schema nova_drift_fx_registry_schema.json
python validate_registry.py --registry shield_aura_example.json --schema shield_aura_registry_schema.json
```

### Test Asset Generation

```powershell
# Test single projectile
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -ProjectileId "plasma_bolt" -OutputDir "Test"

# Test single shield
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -ShieldId "energy_shield_mk2" -OutputDir "Test"

# Test single FX
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -FXId "nova_burst_01" -OutputDir "Test"

# Test single aura
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -AuraId "solar_wind_shield" -OutputDir "Test"
```

## Performance Optimization

### Batch Processing

```powershell
# Generate all assets in parallel (if system supports it)
$jobs = @()
$jobs += Start-Job -ScriptBlock { .\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Output/Projectiles" }
$jobs += Start-Job -ScriptBlock { .\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -OutputDir "Output/ShieldsArmor" }
$jobs += Start-Job -ScriptBlock { .\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Output/FX" }
$jobs += Start-Job -ScriptBlock { .\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Output/Auras" }

# Wait for all jobs
$jobs | Wait-Job | Receive-Job
```

### Incremental Generation

```powershell
# Only generate changed assets
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -ProjectileId "new_plasma_bolt" -OutputDir "Output"
```

## Troubleshooting

### Common Issues

1. **Blender not found**
   - Specify `-BlenderPath` parameter
   - Or use `-SkipRender` to skip rendering

2. **Python not found**
   - Install Python 3.x
   - Ensure Python is in PATH
   - Or use `-SkipExport` to skip XML generation

3. **Registry validation errors**
   - Check JSON syntax
   - Validate against schema
   - Ensure all required fields are present

4. **Missing dependencies**
   - Install Pillow (PIL) for image processing: `pip install Pillow`
   - Ensure Blender Python has required modules

## Best Practices

1. **Version Control**: Keep registry JSON files in version control
2. **Naming Conventions**: Use consistent naming (e.g., `plasma_bolt`, `energy_shield_mk2`)
3. **Resource Organization**: Organize resources by type in separate directories
4. **UNID Management**: Use consistent UNID prefixes (`&pl`, `&sh`, `&fx`, `&au`)
5. **Testing**: Test each asset type individually before batch generation
6. **Documentation**: Document custom registry entries and modifications

## Next Steps

1. Create your registry files for your specific assets
2. Generate assets using the appropriate generators
3. Integrate XML files into your Transcendence extension
4. Test in-game and iterate on registry values
5. Optimize performance based on testing

## Additional Resources

- `PROJECTILE_SYSTEM_README.md`: Projectile system documentation
- `SHIELD_ARMOR_SYSTEM_README.md`: Shield/armor system documentation
- `NOVA_DRIFT_FX_README.md`: FX system documentation
- `SHIELD_AURA_README.md`: Shield aura system documentation
- `SHADER_RECIPES.md`: Shader code for shields
- `SHIELD_AURA_SHADER_RECIPES.md`: Shader code for auras

