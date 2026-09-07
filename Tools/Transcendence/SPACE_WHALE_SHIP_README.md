# Space Whale Ship Generator

## Overview

The Space Whale Ship Generator creates playable bio-mech capital ships that function as living carriers and area-control platforms. These massive vessels feature:

- **Bioluminescent Materials**: Subsurface scattering, glowing veins, and animated energy flow
- **Modular Design**: Head, mid, belly, tail, and dorsal crest modules
- **Breathing Animations**: Slow, organic hull expansion and gill vent pulsing
- **Orbit Field Systems**: Solar wind-style aura that influences projectiles and small objects
- **Drone Bay**: Internal bay for spawning and managing drone swarms
- **Bio-Core Power System**: Powers abilities, shields, and drone production

## Quick Start

### Generate a Space Whale Ship

```powershell
# Generate all ships from example registry
.\SpaceWhaleShipGenerator.ps1

# Generate specific ship
.\SpaceWhaleShipGenerator.ps1 -ShipId "leviathan_alpha"

# Custom registry and output
.\SpaceWhaleShipGenerator.ps1 -RegistryPath "my_ships.json" -OutputDir "Output/MyShips"
```

### Registry Structure

```json
{
  "version": "1.0.0",
  "ships": [
    {
      "id": "leviathan_alpha",
      "type": "spaceWhale",
      "visual": {
        "silhouette": {
          "length": 8.0,
          "width": 3.5,
          "height": 2.0,
          "profile": "streamlined"
        },
        "materials": {
          "skinType": "bioluminescent",
          "baseColor": "#1a2a3a",
          "veinColor": "#66ccff",
          "emissiveIntensity": 3.5
        },
        "animations": {
          "breathingEnabled": true,
          "breathingSpeed": 0.8,
          "gillVentCount": 6
        }
      },
      "systems": {
        "bioCore": {
          "maxEnergy": 1000,
          "rechargeRate": 25
        },
        "orbitField": {
          "radius": 2.5,
          "pullStrength": 0.8
        },
        "droneBay": {
          "maxDrones": 12,
          "deadZoneCapacity": 6
        }
      },
      "stats": {
        "hullHP": 2000,
        "baseSpeed": 0.3,
        "turnRate": 0.15
      },
      "export": {
        "unid": "&shLeviathanAlpha;",
        "resourcePaths": {
          "shipImage": "Resources/Ships/leviathan_alpha.png"
        }
      }
    }
  ]
}
```

## System Components

### Visual Design

#### Silhouette
- **Length**: Overall ship length in units
- **Width**: Widest point width
- **Height**: Ship height
- **Profile**: `streamlined`, `bulky`, or `serpentine`

#### Materials
- **Skin Type**: `bioluminescent`, `carapace`, or `hybrid`
- **Base Color**: Primary hull color (hex)
- **Vein Color**: Energy flow color (hex)
- **Emissive Intensity**: Glow strength (0-10)
- **Subsurface Scattering**: Enable/disable SSS
- **Vein Flow Speed**: Animation speed for energy flow

#### Animations
- **Breathing**: Slow hull expansion/contraction
- **Tail Sweep**: Graceful tail motion during acceleration
- **Gill Vents**: Pulsing vents along ship sides
- **Dorsal Crest Glow**: Animated crest emission

### Gameplay Systems

#### Bio-Core
- Powers all abilities and drone production
- Output scales with core integrity
- Drains when abilities are active

#### Orbit Field
- Passive aura that tugs objects into slow orbits
- Increases collision damage inside field
- Strength scales with Bio-Core output
- Visual styles: `solarWind`, `gravityWell`, `plasmaAura`

#### Drone Bay
- Internal bay for spawning drones
- Dead zone for protecting drones
- Drone types: `interceptor`, `repair`, `harasser`, `heavy`

#### Shield System
- Shared shield pool with minions
- Minion link routes shield to drones
- Player becomes vulnerable while link is active

#### Abilities
- **Solar Wind Toggle**: Activates orbit field and minion link
- **Song Pulse**: Charged shockwave that pushes objects outward
- **Feeding Surge**: Consumes Bio-Core to spawn/empower drones

## Blender Rendering

The Blender renderer creates:

1. **Modular Ship Sections**: Head, mid, belly, tail, dorsal crest
2. **Bioluminescent Materials**: Subsurface scattering + emission
3. **Breathing Animation**: 16-frame animation cycle
4. **Gill Vent Animation**: Pulsing vents with particle plumes
5. **Spritesheet Output**: Horizontal layout for Transcendence

### Rendering Options

```powershell
# Render with custom frame count
.\SpaceWhaleShipGenerator.ps1 -Frames 24

# Skip Blender rendering
.\SpaceWhaleShipGenerator.ps1 -SkipBlender

# Skip XML export
.\SpaceWhaleShipGenerator.ps1 -SkipXML
```

## Transcendence Integration

### XML Output

The exporter creates Transcendence XML with:

- Ship class definition with UNID
- Armor and shield configuration
- Drive and reactor stats
- Device slots for Bio-Core, Orbit Field, Drone Bay
- Ability devices (Solar Wind, Song Pulse, Feeding Surge)
- Image references for spritesheets

### Example XML Structure

```xml
<ShipClass UNID="&shLeviathanAlpha;" name="Leviathan Alpha">
  <Armor armorID="&shLeviathanAlphaArmor;" />
  <Shields type="light" HP="500" regen="8" />
  <Image UNID="&shLeviathanAlphaImage;">
    <ImageDesc bitmap="Resources/Ships/leviathan_alpha.png" 
               frameCount="16" ticksPerFrame="2" />
  </Image>
  <Drive maxSpeed="30" thrust="10" maneuver="15" />
  <Device deviceID="&shLeviathanAlphaBioCore;" slots="1" />
  <Device deviceID="&shLeviathanAlphaDroneBay;" slots="1" />
  <!-- ... more devices ... -->
</ShipClass>
```

## Workflow

### 1. Design Phase
- Create concept thumbnails (10-20 silhouettes)
- Refine 2-3 into color comps
- Define gameplay role (carrier, tank, area control)

### 2. Registry Creation
- Define ship ID and type
- Set silhouette dimensions
- Configure materials and colors
- Set up systems (Bio-Core, Orbit Field, Drone Bay)
- Define stats (HP, speed, turn rate)

### 3. Blender Rendering
- Generates modular ship sections
- Applies bioluminescent materials
- Creates breathing animation
- Exports spritesheet

### 4. XML Export
- Creates Transcendence ship class
- Defines devices and systems
- Links image resources
- Sets up stats and abilities

### 5. Integration
- Copy generated assets to Transcendence extension
- Test in-game
- Tune balance and visuals

## Tips and Best Practices

### Silhouette Design
- **Readability**: Ensure ship reads clearly at game scale
- **Proportions**: Long, streamlined profile for whale aesthetic
- **Modules**: Keep modules distinct but cohesive

### Material Design
- **Color Harmony**: Use complementary colors for base and veins
- **Emissive Intensity**: Start at 3.0-4.0, adjust for visibility
- **Vein Flow**: Speed of 1.0-2.0 creates organic feel

### Animation Timing
- **Breathing Speed**: 0.6-1.2 for natural rhythm
- **Breathing Amplitude**: 0.03-0.08 for subtle expansion
- **Gill Pulse**: 1.5-2.5 for energetic feel

### Balance Considerations
- **Bio-Core**: Balance max energy vs drain rate
- **Orbit Field**: Radius should match ship size
- **Drone Bay**: Cap drone count for performance
- **Shield Link**: Make vulnerability meaningful tradeoff

## Performance

### Optimization
- **LOD**: Reduce particle/shader complexity at distance
- **Pooling**: Pool drones and orbiting objects
- **Capping**: Cap max drones and orbiting objects
- **Baking**: Bake animations to spritesheets

### Recommended Limits
- **Max Drones**: 12-16 per ship
- **Orbit Field Objects**: 20-30 max
- **Animation Frames**: 16-24 for breathing
- **Gill Vents**: 6-8 per side

## Troubleshooting

### Blender Rendering Issues
- **Missing Materials**: Check material configuration in registry
- **Animation Not Working**: Verify breathing settings
- **Size Issues**: Adjust silhouette dimensions

### XML Export Issues
- **UNID Format**: Ensure `&UNID;` format (not `&amp;UNID;`)
- **Missing Resources**: Verify resource paths exist
- **Device Errors**: Check system configuration

### Performance Issues
- **Too Many Drones**: Reduce max drone count
- **Orbit Field Lag**: Cap orbiting objects
- **Animation Stutter**: Reduce frame count or optimize shaders

## Examples

See `space_whale_ship_example.json` for complete examples:
- **Leviathan Alpha**: Balanced carrier with 12 drones
- **Serpent Void**: Fast, aggressive variant with 16 drones

## Next Steps

1. **Test Generated Ships**: Load into Transcendence and verify
2. **Tune Balance**: Adjust stats and abilities
3. **Add Variants**: Create different ship profiles
4. **Enhance FX**: Add orbit field distortion and particle effects
5. **Drone System**: Implement drone AI and behaviors

## Related Systems

- **Nova Drift FX**: For orbit field visual effects
- **Shield Aura**: For solar wind-style auras
- **Drone System**: For drone spawning and AI (coming soon)

