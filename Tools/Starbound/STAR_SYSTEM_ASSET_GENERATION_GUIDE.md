# Star System Asset Generation Guide

Generate assets for the Star System including star type icons, planet icons, and star map textures.

## Quick Start

```powershell
# Generate all star system assets
.\GenerateStarSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateStarSystemAssets.ps1 -UseCppBackend

# Or generate everything including star system assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Star Type Icons (5 icons)

1. **star_yellow_dwarf** - Yellow dwarf star
2. **star_red_giant** - Red giant star
3. **star_white_dwarf** - White dwarf star
4. **star_neutron** - Neutron star
5. **star_black_hole** - Black hole

### Planet Icons (8 icons)

1. **planet_terrestrial** - Terrestrial planet
2. **planet_gas_giant** - Gas giant planet
3. **planet_ice_giant** - Ice giant planet
4. **planet_dwarf** - Dwarf planet
5. **planet_barren** - Barren planet
6. **planet_ocean** - Ocean planet
7. **planet_desert** - Desert planet
8. **planet_forest** - Forest planet

### Star Map Textures (4 textures)

1. **starmap_background** - Star map background
2. **starmap_grid** - Star map grid
3. **starmap_nebula** - Nebula texture
4. **starmap_connection_line** - Connection line texture

## Total: ~17 Assets

## Output Structure

```
assets/
├── stars/
│   ├── star_yellow_dwarf.png
│   ├── star_red_giant.png
│   ├── star_white_dwarf.png
│   ├── star_neutron.png
│   └── star_black_hole.png
├── planets/
│   ├── planet_terrestrial.png
│   ├── planet_gas_giant.png
│   ├── planet_ice_giant.png
│   ├── planet_dwarf.png
│   ├── planet_barren.png
│   ├── planet_ocean.png
│   ├── planet_desert.png
│   └── planet_forest.png
└── starmap/
    ├── starmap_background.png
    ├── starmap_grid.png
    ├── starmap_nebula.png
    └── starmap_connection_line.png
```

## Integration

### Star System Generation

```cpp
// Generate star map
StarMapGenerator generator(width, height, seed);
StarMap map = generator.generate(starCount);
// Uses: /stars/star_*.png icons for each star type
// Uses: /planets/planet_*.png icons for planets
```

### Star Map Display

```cpp
// Render star map
renderStarMap(map);
// Uses: /starmap/starmap_background.png for background
// Uses: /starmap/starmap_grid.png for grid overlay
// Uses: /starmap/starmap_nebula.png for nebula effects
// Uses: /starmap/starmap_connection_line.png for system connections
```

### Star System Visualization

```cpp
// Display star system
renderStarSystem(system);
// Uses: /stars/star_*.png based on system.starType
// Uses: /planets/planet_*.png for each planet
```

## Star Types

### Star Classifications
- **YellowDwarf**: Yellow sun-like star (most common)
- **RedGiant**: Large red star (expanded)
- **WhiteDwarf**: Small white star (collapsed)
- **Neutron**: Dense neutron star (pulsar)
- **BlackHole**: Black hole with accretion disk

## Planet Types

### Planet Classifications
- **Terrestrial**: Rocky planet (Earth-like)
- **Gas Giant**: Large gas planet (Jupiter-like)
- **Ice Giant**: Icy gas planet (Neptune-like)
- **Dwarf**: Small rocky planet (Pluto-like)
- **Barren**: Lifeless rocky planet
- **Ocean**: Water-covered planet
- **Desert**: Sandy desert planet
- **Forest**: Forest-covered planet

## Star Map Features

### Map Elements
- **Background**: Space background texture
- **Grid**: Navigation grid overlay
- **Nebula**: Colorful nebula clouds
- **Connection Lines**: Paths between star systems

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateStarSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Generate Star Map

Generate star map with StarMapGenerator.

### Step 3: Render Star Map

Display star map with generated assets.

### Step 4: Test in Game

Load the mod and test star system navigation in-game.

## Advanced Options

### Custom Star Types

Edit `GenerateStarSystemAssets.ps1` to add custom star types:

```powershell
@{
    Id = "star_custom"
    Name = "Custom Star"
    Desc = "Custom star description, 32x32"
}
```

### Custom Planet Types

Add custom planet icons to the `$planetTypes` array.

### Custom Star Map Elements

Add custom star map textures to the `$starMapTextures` array.

## Tips

1. **Star icons**: Use 32x32 for UI display
2. **Planet icons**: Use 32x32 for UI display
3. **Star map textures**: Use 256x256 for backgrounds, 32x4 for lines
4. **Star colors**: Match star colors to real star types
5. **Planet variety**: Create distinct visuals for each planet type

## Troubleshooting

### Stars Not Displaying

- Check star icon paths in star system definitions
- Verify icons are in `assets/stars/`
- Ensure star system is initialized

### Planets Not Showing

- Check planet icon paths in planet definitions
- Verify icons are in `assets/planets/`
- Ensure planet system is initialized

### Star Map Not Rendering

- Verify star map textures are in correct location
- Check texture paths in star map renderer
- Ensure star map system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
