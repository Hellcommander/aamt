# Quick Start Guide - Transcendence Asset Generator

Get up and running with the asset generator in 5 minutes.

## Prerequisites

1. **PowerShell 7+** (pwsh)
2. **Python 3.x** (for XML export)
3. **Blender 5.0+** (for rendering, optional)
4. **Pillow (PIL)** Python library: `pip install Pillow`

## Step 1: Verify Installation

```powershell
# Check PowerShell version
pwsh --version

# Check Python
python --version

# Check Blender (optional)
# Blender should be at: D:\tools\Blender Foundation\Blender 5.0\blender.exe
# Or specify path manually
```

## Step 2: Generate Example Assets

The easiest way to start is using the example registry files:

```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools"

# Generate all example assets
.\GenerateAllAssets.ps1 -UseExamples -OutputBaseDir "MyFirstAssets"
```

This will generate:
- Projectiles (plasma_bolt, homing_missile, railgun_slug, phase_projectile)
- Shields (energy_shield_mk2, plasma_barrier)
- Armor (reinforced_plating_mk1)
- FX (nova_burst_01, plasma_explosion, energy_impact)
- Auras (solar_wind_shield, plasma_gravity_field)

## Step 3: Check Output

After generation, check your output directory:

```
MyFirstAssets/
├── Projectiles/
│   ├── Spritesheets/
│   ├── XML/
│   └── Resources/
├── ShieldsArmor/
│   ├── Spritesheets/
│   ├── XML/
│   └── Resources/
├── FX/
│   ├── Spritesheets/
│   ├── XML/
│   └── Resources/
└── Auras/
    ├── Spritesheets/
    ├── XML/
    └── Resources/
```

## Step 4: Create Your First Custom Asset

### Create a Custom Projectile

1. Copy the example registry:
```powershell
Copy-Item "projectile_registry_example.json" "my_projectiles.json"
```

2. Edit `my_projectiles.json` and add your projectile:
```json
{
  "version": "1.0.0",
  "projectiles": [
    {
      "id": "my_custom_bolt",
      "type": "Laser",
      "quality": "High",
      "visual": {
        "spriteSize": [32, 32],
        "rotations": 1,
        "frames": 1,
        "palette": {
          "primary": "#00ff00",
          "glow": "#00ff88"
        },
        "material": {
          "type": "Energy",
          "glowIntensity": 3.0
        }
      },
      "physics": {
        "speed": 150,
        "lifetime": 4.0
      },
      "damage": {
        "baseDamage": 20,
        "damageType": "laser"
      },
      "fx": {
        "trail": {
          "enabled": true,
          "length": 20
        }
      },
      "export": {
        "xmlTemplate": "Projectile",
        "unid": "&plMyCustomBolt;",
        "resourcePaths": {
          "image": "Resources/Projectiles/my_custom_bolt.png"
        }
      }
    }
  ]
}
```

3. Generate it:
```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "my_projectiles.json" -OutputDir "MyAssets/Projectiles"
```

## Step 5: Validate Your Registry

Before generating, validate your registry:

```powershell
python validate_registry.py --registry my_projectiles.json --schema projectile_registry_schema.json
```

## Step 6: Generate Individual Asset Types

### Projectiles Only
```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "my_projectiles.json" -OutputDir "Output/Projectiles"
```

### Shields/Armor Only
```powershell
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -OutputDir "Output/ShieldsArmor"
```

### FX Only
```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Output/FX"
```

### Auras Only
```powershell
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Output/Auras"
```

## Step 7: Skip Rendering (XML Only)

If you don't have Blender or want to skip rendering:

```powershell
.\GenerateAllAssets.ps1 -UseExamples -SkipRender -OutputBaseDir "Output"
```

This will generate XML files only (no spritesheets).

## Step 8: Skip Export (Render Only)

If you only want to render spritesheets:

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "my_projectiles.json" -SkipExport -OutputDir "Output"
```

## Common Workflows

### Workflow 1: Quick Test
```powershell
# Generate one projectile quickly
.\ProjectileSystemGenerator.ps1 `
    -RegistryPath "projectile_registry_example.json" `
    -ProjectileId "plasma_bolt" `
    -OutputDir "Test"
```

### Workflow 2: Full Pipeline
```powershell
# Generate everything
.\GenerateAllAssets.ps1 `
    -ProjectileRegistry "my_projectiles.json" `
    -ShieldArmorRegistry "my_shields.json" `
    -FXRegistry "my_fx.json" `
    -AuraRegistry "my_auras.json" `
    -OutputBaseDir "ProductionAssets"
```

### Workflow 3: Iterative Development
```powershell
# 1. Create/Edit registry
# 2. Validate
python validate_registry.py --registry my_assets.json

# 3. Generate
.\ProjectileSystemGenerator.ps1 -RegistryPath "my_assets.json" -OutputDir "Test"

# 4. Test in game
# 5. Iterate
```

## Troubleshooting

### Blender Not Found
```powershell
# Specify Blender path manually
.\ProjectileSystemGenerator.ps1 `
    -RegistryPath "my_projectiles.json" `
    -BlenderPath "D:\tools\Blender Foundation\Blender 5.0\blender.exe" `
    -OutputDir "Output"
```

### Python Not Found
```powershell
# Skip XML export
.\ProjectileSystemGenerator.ps1 `
    -RegistryPath "my_projectiles.json" `
    -SkipExport `
    -OutputDir "Output"
```

### Invalid JSON
```powershell
# Validate first
python validate_registry.py --registry my_assets.json
```

## Next Steps

1. **Read System Documentation**:
   - `PROJECTILE_SYSTEM_README.md`
   - `SHIELD_ARMOR_SYSTEM_README.md`
   - `NOVA_DRIFT_FX_README.md`
   - `SHIELD_AURA_README.md`

2. **Review Examples**:
   - `projectile_registry_example.json`
   - `shield_armor_example.json`
   - `nova_drift_fx_example.json`
   - `shield_aura_example.json`

3. **Check Integration Guide**:
   - `SYSTEM_INTEGRATION_GUIDE.md`

4. **Create Your Assets**:
   - Start with one asset type
   - Test in-game
   - Iterate and refine

## Tips

- **Start Small**: Generate one asset at a time initially
- **Use Examples**: Copy example registries as starting points
- **Validate First**: Always validate before generating
- **Test Early**: Test assets in-game before batch generation
- **Version Control**: Keep registry files in version control
- **Document**: Document your custom entries

## Getting Help

- Check the README files for each system
- Review example registry files
- Validate your JSON against schemas
- Check error messages for specific issues

Happy asset generating! 🚀

