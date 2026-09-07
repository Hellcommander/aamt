# Projectile System Quick Start

## 1. Create a Registry Entry

Create or edit `projectile_registry.json`:

```json
{
  "version": "1.0.0",
  "projectiles": [
    {
      "id": "my_plasma_bolt",
      "type": "Laser",
      "quality": "High",
      "visual": {
        "spriteSize": [32, 32],
        "rotations": 1,
        "frames": 1,
        "palette": {
          "primary": "#FF6B00",
          "glow": "#FF4500"
        },
        "material": {
          "type": "Plasma",
          "glowIntensity": 3.0
        }
      },
      "physics": {
        "speed": 120,
        "lifetime": 5.0
      },
      "damage": {
        "baseDamage": 15,
        "damageType": "plasma"
      },
      "fx": {
        "trail": {
          "enabled": true,
          "length": 15
        }
      },
      "export": {
        "xmlTemplate": "Projectile",
        "unid": "&plMyPlasmaBolt;",
        "resourcePaths": {
          "image": "Resources/Projectiles/my_plasma_bolt.png"
        }
      }
    }
  ]
}
```

## 2. Generate Assets

### Option A: Full Pipeline (Blender + XML)

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Output"
```

This will:
- Render spritesheet in Blender
- Export XML files
- Package assets

### Option B: XML Only (No Rendering)

```powershell
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -SkipRender -OutputDir "Output"
```

### Option C: Generate Complete Weapon XML

```powershell
python weapon_generator_from_projectile.py --registry projectile_registry.json --output-dir Weapons --create-items
```

## 3. Use Templates

Start from a template:

```powershell
# Copy template
$template = Get-Content projectile_templates.json | ConvertFrom-Json
$missile = $template.templates.Missile

# Customize
$missile.id = "my_missile"
$missile.damage.baseDamage = 75

# Add to registry
$registry = @{ version = "1.0.0"; projectiles = @($missile) }
$registry | ConvertTo-Json -Depth 10 | Out-File my_registry.json
```

## 4. AI Material Generation

Enhance registry with AI-generated materials:

```powershell
python ai_material_generator.py --registry projectile_registry.json --output enhanced_registry.json --model llama3.2
```

## 5. Integration with Transcendence

### Using Effect XML

The exporter creates `Effect` elements that can be embedded in `Weapon` definitions:

```xml
<Weapon type="projectile" damage="plasma:15" speed="120" lifetime="900">
  <Effect>
    <Ray style="smooth" shape="oval" width="32" length="32"
         primaryColor="#FF6B00" intensity="24"/>
  </Effect>
</Weapon>
```

### Using Complete Weapon XML

The weapon generator creates ready-to-use `ItemType` elements:

```xml
<ItemType UNID="&plMyPlasmaBolt;" name="My Plasma Bolt">
  <Weapon type="projectile" damage="plasma:15" speed="120" lifetime="900">
    <Effect>...</Effect>
  </Weapon>
</ItemType>
```

## Common Patterns

### Homing Missile

```json
{
  "type": "Missile",
  "physics": {
    "speed": 80,
    "acceleration": 20,
    "homingStrength": 0.8,
    "turnRate": 90
  },
  "fx": {
    "trail": {
      "enabled": true,
      "length": 40
    }
  }
}
```

### Fast Ballistic

```json
{
  "type": "Ballistic",
  "physics": {
    "speed": 200,
    "ricochet": {
      "enabled": true,
      "maxBounces": 2
    },
    "penetration": {
      "enabled": true,
      "maxTargets": 3
    }
  }
}
```

### Area Effect Exotic

```json
{
  "type": "Exotic",
  "damage": {
    "baseDamage": 40,
    "areaRadius": 15,
    "areaDamage": 25,
    "statusEffects": [{
      "type": "deviceDisrupt",
      "duration": 3.0,
      "chance": 0.8
    }]
  },
  "visual": {
    "distortionMap": true
  }
}
```

## Troubleshooting

**Blender not found**: Specify `-BlenderPath` or use `-SkipRender`

**Python not found**: Install Python 3.x or use `-SkipExport`

**Invalid JSON**: Validate against `projectile_registry_schema.json`

**Missing fields**: Check that required fields (`id`, `type`, `visual`, `physics`, `damage`, `export`) are present

