# Transcendence Asset Generator

A comprehensive, data-driven asset generation system for Transcendence modding. Generate projectiles, shields, armor, special effects, and shield auras with Nova Drift-inspired aesthetics.

## 🚀 Quick Start

```powershell
# Generate all example assets
.\GenerateAllAssets.ps1 -UseExamples -OutputBaseDir "MyAssets"
```

See `QUICK_START_GUIDE.md` for detailed instructions.

## 📚 System Documentation

### Core Systems

1. **Projectile System** - Data-driven projectiles with physics and FX
   - `PROJECTILE_SYSTEM_README.md`
   - `projectile_registry_schema.json`
   - `projectile_registry_example.json`

2. **Shield/Armor System** - Shields, armor plating, runtime state, UI
   - `SHIELD_ARMOR_SYSTEM_README.md`
   - `shield_armor_registry_schema.json`
   - `shield_armor_example.json`

3. **Nova Drift FX System** - High-energy special effects
   - `NOVA_DRIFT_FX_README.md`
   - `nova_drift_fx_registry_schema.json`
   - `nova_drift_fx_example.json`

4. **Shield Aura System** - Solar wind auras with orbital particles
   - `SHIELD_AURA_README.md`
   - `shield_aura_registry_schema.json`
   - `shield_aura_example.json`

### Integration & Guides

- `SYSTEM_INTEGRATION_GUIDE.md` - Complete integration guide
- `MASTER_SYSTEM_OVERVIEW.md` - System architecture overview
- `QUICK_START_GUIDE.md` - Get started in 5 minutes
- `transcendence_integration_examples.xml` - XML integration examples

## 🛠️ Tools

### Generators

- `ProjectileSystemGenerator.ps1` - Generate projectiles
- `ShieldArmorSystemGenerator.ps1` - Generate shields and armor
- `NovaDriftFXGenerator.ps1` - Generate special effects
- `ShieldAuraGenerator.ps1` - Generate shield auras
- `GenerateAllAssets.ps1` - Generate all asset types

### Utilities

- `validate_registry.py` - Validate registry JSON files
- `create_registry_template.ps1` - Create new registry templates

### Blender Scripts

- `blender_projectile_renderer.py` - Render projectiles
- `blender_shield_renderer.py` - Render shields
- `blender_nova_drift_fx_renderer.py` - Render FX
- `blender_shield_aura_renderer.py` - Render auras

### Exporters

- `transcendence_projectile_exporter.py` - Export projectile XML
- `transcendence_shield_armor_exporter.py` - Export shield/armor XML
- `transcendence_fx_exporter.py` - Export FX XML
- `transcendence_shield_aura_exporter.py` - Export aura XML

### Runtime Systems

- `shield_runtime_model.py` - Shield runtime state
- `projectile_orbit_behavior.py` - Projectile orbit behavior
- `particle_choreography_system.py` - Particle motion patterns

## 📖 Usage Examples

### Generate Single Asset Type

```powershell
# Projectiles
.\ProjectileSystemGenerator.ps1 -RegistryPath "projectile_registry.json" -OutputDir "Output"

# Shields/Armor
.\ShieldArmorSystemGenerator.ps1 -RegistryPath "shield_armor_example.json" -OutputDir "Output"

# FX
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Output"

# Auras
.\ShieldAuraGenerator.ps1 -RegistryPath "shield_aura_example.json" -OutputDir "Output"
```

### Generate All Assets

```powershell
.\GenerateAllAssets.ps1 -UseExamples -OutputBaseDir "Assets"
```

### Create New Registry

```powershell
# Create projectile template
.\create_registry_template.ps1 -Type Projectile -OutputPath "my_projectiles.json" -AssetId "my_plasma_bolt"

# Create shield template
.\create_registry_template.ps1 -Type Shield -OutputPath "my_shields.json" -AssetId "my_energy_shield"

# Create FX template
.\create_registry_template.ps1 -Type FX -OutputPath "my_fx.json" -AssetId "my_explosion"

# Create aura template
.\create_registry_template.ps1 -Type Aura -OutputPath "my_auras.json" -AssetId "my_solar_wind"
```

### Validate Registry

```powershell
python validate_registry.py --registry my_projectiles.json --schema projectile_registry_schema.json
```

## 🎨 Features

### Projectile System
- ✅ 4 projectile types: Missile, Laser, Ballistic, Exotic
- ✅ Physics: speed, acceleration, homing, gravity, drag
- ✅ Damage: base damage, damage types, area effects, status effects
- ✅ FX: trails, impact particles, light emission, sound
- ✅ 120-facings ship support
- ✅ Nova Drift style references

### Shield/Armor System
- ✅ Shield visuals: radius, thickness, colors, pulse, distortion
- ✅ Runtime state: damage handling, recharge logic
- ✅ Armor slots: directional plating with damage reduction
- ✅ UI data binding models
- ✅ Shader recipes (GLSL/HLSL)

### Nova Drift FX System
- ✅ Layered composition: core → bloom → shockwave → debris
- ✅ Procedural distortion fields
- ✅ Particle choreography: radial, spiral, chaotic
- ✅ Timing curves with easing
- ✅ AI prompt templates

### Shield Aura System
- ✅ Solar wind alpha noise fluctuations
- ✅ Orbital particles with gravity well
- ✅ Projectile influence (orbit behavior)
- ✅ Shield HP scaling
- ✅ Distortion fields

## 📁 File Structure

```
Tools/
├── README.md                          # This file
├── QUICK_START_GUIDE.md              # Quick start guide
├── SYSTEM_INTEGRATION_GUIDE.md       # Integration guide
├── MASTER_SYSTEM_OVERVIEW.md         # System overview
│
├── Generators/
│   ├── GenerateAllAssets.ps1         # Master batch generator
│   ├── ProjectileSystemGenerator.ps1
│   ├── ShieldArmorSystemGenerator.ps1
│   ├── NovaDriftFXGenerator.ps1
│   └── ShieldAuraGenerator.ps1
│
├── Schemas/
│   ├── projectile_registry_schema.json
│   ├── shield_armor_registry_schema.json
│   ├── nova_drift_fx_registry_schema.json
│   └── shield_aura_registry_schema.json
│
├── Examples/
│   ├── projectile_registry_example.json
│   ├── shield_armor_example.json
│   ├── nova_drift_fx_example.json
│   └── shield_aura_example.json
│
├── Blender Scripts/
│   ├── blender_projectile_renderer.py
│   ├── blender_shield_renderer.py
│   ├── blender_nova_drift_fx_renderer.py
│   └── blender_shield_aura_renderer.py
│
├── Exporters/
│   ├── transcendence_projectile_exporter.py
│   ├── transcendence_shield_armor_exporter.py
│   ├── transcendence_fx_exporter.py
│   └── transcendence_shield_aura_exporter.py
│
├── Runtime/
│   ├── shield_runtime_model.py
│   ├── projectile_orbit_behavior.py
│   └── particle_choreography_system.py
│
├── Utilities/
│   ├── validate_registry.py
│   └── create_registry_template.ps1
│
└── Documentation/
    ├── PROJECTILE_SYSTEM_README.md
    ├── SHIELD_ARMOR_SYSTEM_README.md
    ├── NOVA_DRIFT_FX_README.md
    ├── SHIELD_AURA_README.md
    ├── SHADER_RECIPES.md
    ├── SHIELD_AURA_SHADER_RECIPES.md
    └── ai_fx_prompt_templates.md
```

## 🔧 Requirements

- **PowerShell 7+** (pwsh)
- **Python 3.x** (for XML export)
- **Blender 5.0+** (for rendering, optional)
- **Pillow (PIL)**: `pip install Pillow`

## 🎯 Workflow

1. **Create Registry**: Use `create_registry_template.ps1` or copy examples
2. **Validate**: Run `validate_registry.py`
3. **Generate**: Use appropriate generator script
4. **Test**: Load assets in Transcendence
5. **Iterate**: Refine registry values and regenerate

## 📝 Best Practices

1. **Start Small**: Generate one asset at a time initially
2. **Use Examples**: Copy example registries as starting points
3. **Validate First**: Always validate before generating
4. **Test Early**: Test assets in-game before batch generation
5. **Version Control**: Keep registry files in version control
6. **Document**: Document your custom entries

## 🐛 Troubleshooting

See `SYSTEM_INTEGRATION_GUIDE.md` for detailed troubleshooting.

Common issues:
- **Blender not found**: Specify `-BlenderPath` or use `-SkipRender`
- **Python not found**: Install Python or use `-SkipExport`
- **Invalid JSON**: Validate with `validate_registry.py`

## 📚 Additional Resources

- Transcendence Modding Documentation
- Nova Drift Wiki (for style references)
- Blender Documentation
- JSON Schema Documentation

## 🤝 Contributing

When adding new asset types or features:
1. Update relevant schema files
2. Add example entries
3. Update documentation
4. Test with validation tool

## 📄 License

This toolset is provided as-is for Transcendence modding.

---

**Happy Asset Generating!** 🚀

For questions or issues, refer to the system-specific README files or integration guide.

