# Biome Generation System Asset Generation Guide

Generate assets for the Biome Generation System including island terrain, features, hazards, vegetation, atmospheric layers, and navigation markers.

## Quick Start

```powershell
# Generate all biome assets
.\GenerateBiomeAssets.ps1

# Use C++ backend for better quality
.\GenerateBiomeAssets.ps1 -UseCppBackend

# Or generate everything including biome assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Island Terrain Tiles (7 tiles)

1. **island_ground_stone** - Stone ground tile
2. **island_ground_grass** - Grass ground tile
3. **island_ground_dirt** - Dirt ground tile
4. **island_ground_rock** - Rock ground tile
5. **island_surface_top** - Top surface tile
6. **island_surface_edge** - Edge surface tile
7. **island_erosion_decal** - Erosion decal texture

### Island Features (4 features)

1. **island_feature_cave** - Cave entrance sprite
2. **island_feature_waterfall** - Waterfall sprite
3. **island_feature_peak** - Mountain peak sprite
4. **island_feature_edge** - Cliff edge sprite

### Island Hazards (3 effects)

1. **island_hazard_unstable** - Unstable ground effect
2. **island_hazard_low_gravity** - Low gravity effect
3. **island_hazard_erosion** - Erosion effect

### Island Vegetation (4 sprites)

1. **island_vegetation_tree** - Island tree sprite
2. **island_vegetation_plant** - Island plant sprite
3. **island_vegetation_grass** - Island grass sprite
4. **island_vegetation_shrub** - Island shrub sprite

### Resource Node Icons (4 icons)

1. **resource_node_ore** - Ore resource node
2. **resource_node_crystal** - Crystal resource node
3. **resource_node_organic** - Organic resource node
4. **resource_node_energy** - Energy resource node

### Spawn Markers (3 icons)

1. **spawn_marker_ship** - Ship spawn marker
2. **spawn_marker_creature** - Creature spawn marker
3. **spawn_marker_building** - Building site marker

### Atmospheric Layer Textures (5 textures)

1. **atmosphere_cloud_troposphere** - Troposphere clouds
2. **atmosphere_cloud_stratosphere** - Stratosphere clouds
3. **atmosphere_sky_low** - Low altitude sky
4. **atmosphere_sky_high** - High altitude sky
5. **atmosphere_fog** - Atmospheric fog

### Wind and Turbulence Effects (6 effects)

1. **wind_effect_light** - Light wind effect
2. **wind_effect_medium** - Medium wind effect
3. **wind_effect_strong** - Strong wind effect
4. **turbulence_effect_light** - Light turbulence effect
5. **turbulence_effect_medium** - Medium turbulence effect
6. **turbulence_effect_strong** - Strong turbulence effect

### Entry/Exit Point Markers (2 icons)

1. **entry_point_marker** - Entry point marker
2. **exit_point_marker** - Exit point marker

### Atmospheric Hazard Effects (4 effects)

1. **atmosphere_hazard_storm** - Storm hazard effect
2. **atmosphere_hazard_wind_shear** - Wind shear hazard effect
3. **atmosphere_hazard_void** - Void hazard effect
4. **atmosphere_hazard_toxic** - Toxic atmosphere hazard effect

## Total: ~42 Assets

## Output Structure

```
assets/
├── biomes/
│   ├── islands/
│   │   ├── tiles/
│   │   │   ├── island_ground_stone.png
│   │   │   ├── island_ground_grass.png
│   │   │   └── ... (all island tiles)
│   │   ├── features/
│   │   │   ├── island_feature_cave.png
│   │   │   ├── island_feature_waterfall.png
│   │   │   └── ... (all island features)
│   │   ├── hazards/
│   │   │   ├── island_hazard_unstable.particle
│   │   │   ├── island_hazard_low_gravity.particle
│   │   │   └── ... (all island hazards)
│   │   └── vegetation/
│   │       ├── island_vegetation_tree.png
│   │       ├── island_vegetation_plant.png
│   │       └── ... (all island vegetation)
│   ├── resources/
│   │   ├── resource_node_ore.png
│   │   ├── resource_node_crystal.png
│   │   └── ... (all resource nodes)
│   ├── markers/
│   │   ├── spawn_marker_ship.png
│   │   ├── spawn_marker_creature.png
│   │   ├── spawn_marker_building.png
│   │   ├── entry_point_marker.png
│   │   └── exit_point_marker.png
│   └── atmosphere/
│       ├── atmosphere_cloud_troposphere.png
│       ├── atmosphere_cloud_stratosphere.png
│       ├── atmosphere_sky_low.png
│       ├── atmosphere_sky_high.png
│       ├── atmosphere_fog.png
│       ├── wind_effect_light.particle
│       ├── wind_effect_medium.particle
│       ├── wind_effect_strong.particle
│       ├── turbulence_effect_light.particle
│       ├── turbulence_effect_medium.particle
│       ├── turbulence_effect_strong.particle
│       ├── atmosphere_hazard_storm.particle
│       ├── atmosphere_hazard_wind_shear.particle
│       ├── atmosphere_hazard_void.particle
│       └── atmosphere_hazard_toxic.particle
```

## Integration

### Island Generation

```lua
-- Generate floating islands
IslandGenerator:generateIslands(worldId)
-- Uses: /biomes/islands/tiles/*.png for terrain
-- Uses: /biomes/islands/features/*.png for features
-- Uses: /biomes/islands/vegetation/*.png for vegetation
-- Uses: /biomes/islands/hazards/*.particle for hazards
```

### Resource Nodes

```lua
-- Get resource nodes
local nodes = IslandGenerator:getResourceNodes(worldId, layerName)
-- Uses: /biomes/resources/resource_node_*.png icons
```

### Spawn Points

```lua
-- Get ship spawns
local spawns = IslandGenerator:getShipSpawns(worldId, layerName)
-- Uses: /biomes/markers/spawn_marker_ship.png marker

-- Get creature spawns
local creatureSpawns = IslandGenerator:getCreatureSpawns(worldId, creatureType)
-- Uses: /biomes/markers/spawn_marker_creature.png marker
```

### Atmospheric Biomes

```lua
-- Generate atmospheric biomes
AtmosphereBiomeGenerator:generateBiomes(worldId)
-- Uses: /biomes/atmosphere/atmosphere_*.png textures
-- Uses: /biomes/atmosphere/wind_effect_*.particle effects
-- Uses: /biomes/atmosphere/turbulence_effect_*.particle effects
```

### Entry/Exit Points

```lua
-- Get entry points
local entryPoints = AtmosphereBiomeGenerator:getEntryPoints(worldId, layerName)
-- Uses: /biomes/markers/entry_point_marker.png marker

-- Get exit points
local exitPoints = AtmosphereBiomeGenerator:getExitPoints(worldId, layerName)
-- Uses: /biomes/markers/exit_point_marker.png marker
```

## Island Features

### Terrain Types
- **Stone**: Grey/brown stone ground
- **Grass**: Green grass ground
- **Dirt**: Brown dirt ground
- **Rock**: Grey rock ground

### Features
- **Cave**: Cave entrance on islands
- **Waterfall**: Flowing waterfall
- **Peak**: Mountain peak
- **Edge**: Cliff edge

### Hazards
- **Unstable**: Shaking/cracking ground
- **Low Gravity**: Floating particles
- **Erosion**: Crumbling debris

## Atmospheric Layers

### Cloud Types
- **Troposphere**: White fluffy clouds
- **Stratosphere**: Thin wispy clouds

### Sky Types
- **Low Altitude**: Blue sky
- **High Altitude**: Dark blue/black sky

### Wind Effects
- **Light**: Gentle breeze
- **Medium**: Moderate breeze
- **Strong**: Strong gusts

### Turbulence Effects
- **Light**: Minor air disturbance
- **Medium**: Moderate air disturbance
- **Strong**: Severe air disturbance

### Atmospheric Hazards
- **Storm**: Lightning and rain
- **Wind Shear**: Dangerous air currents
- **Void**: Dark void
- **Toxic**: Green/yellow toxic gas

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateBiomeAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Generate Islands

Generate floating islands with the IslandGenerator.

### Step 3: Generate Atmospheric Biomes

Generate atmospheric biomes with the AtmosphereBiomeGenerator.

### Step 4: Test in Game

Load the mod and test biome generation in-game.

## Advanced Options

### Custom Island Features

Edit `GenerateBiomeAssets.ps1` to add custom island features:

```powershell
@{
    Id = "island_feature_custom"
    Name = "Custom Feature"
    Desc = "Custom feature description"
}
```

### Custom Atmospheric Layers

Add custom atmospheric layer textures to the `$atmosphericLayers` array.

### Custom Hazards

Add custom hazard effects to the `$islandHazards` or `$atmosphericHazards` arrays.

## Tips

1. **Terrain tiles**: Use 16x16 for seamless tiling
2. **Feature sprites**: Use 32x32 for island features
3. **Vegetation**: Use appropriate sizes (8x8 for grass, 32x32 for trees)
4. **Atmospheric textures**: Use 64x64 for cloud/sky textures
5. **Particle effects**: Create distinct effects for each hazard type

## Troubleshooting

### Islands Not Generating

- Check terrain tile paths in island definitions
- Verify tiles are in `assets/biomes/islands/tiles/`
- Ensure island generation system is initialized

### Features Not Appearing

- Check feature sprite paths
- Verify features are in `assets/biomes/islands/features/`
- Ensure features are properly referenced in island cells

### Atmospheric Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in atmospheric layer definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
