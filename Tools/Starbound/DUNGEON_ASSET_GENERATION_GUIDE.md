# Dungeon System Asset Generation Guide

Generate tile assets for the dungeon generation system including floor, wall, ceiling, and decorative tiles.

## Quick Start

```powershell
# Generate all dungeon tiles
.\GenerateDungeonAssets.ps1

# Use C++ backend for better quality
.\GenerateDungeonAssets.ps1 -UseCppBackend

# Or generate everything including dungeon assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Floor Tiles (6 tiles)

1. **floor_stone** - Stone floor tile
2. **floor_brick** - Brick floor tile
3. **floor_wood** - Wooden floor tile
4. **floor_metal** - Metal floor tile
5. **floor_dirt** - Dirt floor tile
6. **floor_arcane** - Arcane floor tile

### Wall Tiles (6 tiles)

1. **wall_stone** - Stone wall tile
2. **wall_brick** - Brick wall tile
3. **wall_wood** - Wooden wall tile
4. **wall_metal** - Metal wall tile
5. **wall_arcane** - Arcane wall tile
6. **wall_corner** - Wall corner tile

### Ceiling Tiles (3 tiles)

1. **ceiling_stone** - Stone ceiling tile
2. **ceiling_wood** - Wooden ceiling tile
3. **ceiling_metal** - Metal ceiling tile

### Decorative Tiles (4 tiles)

1. **decor_rune** - Rune decoration
2. **decor_crack** - Crack decoration
3. **decor_moss** - Moss decoration
4. **decor_blood** - Blood decoration

## Total: ~19 Tiles

## Output Structure

```
assets/
└── textures/
    └── dungeon/
        └── tiles/
            ├── floor_stone.png
            ├── floor_brick.png
            ├── wall_stone.png
            ├── wall_brick.png
            ├── ceiling_stone.png
            └── ... (all other tiles)
```

## Tile Atlas Assembly

After generating individual tiles, assemble them into texture atlases:

### Atlas Layout

```
┌────┬────┬────┬────┐
│ T1 │ T2 │ T3 │ T4 │  ← Row 1
├────┼────┼────┼────┤
│ T5 │ T6 │ T7 │ T8 │  ← Row 2
└────┴────┴────┴────┘
```

### Atlas Configuration

```json
{
  "atlasPath": "/textures/dungeon/dungeon_atlas.png",
  "tileWidth": 16,
  "tileHeight": 16,
  "atlasWidth": 256,
  "atlasHeight": 256,
  "tilesPerRow": 16,
  "tileDefinitions": {
    "0": "floor_stone",
    "1": "floor_brick",
    "2": "wall_stone",
    "3": "wall_brick"
  }
}
```

## Integration

### Tilemap Data

Create tilemap data for dungeon generation:

```lua
local tilemap = Dungeon.TilemapData()
tilemap.width = 64
tilemap.height = 64
tilemap.atlasPath = "/textures/dungeon/dungeon_atlas.png"

-- Set tiles
tilemap:setTile(0, 0, 0)  -- floor_stone
tilemap:setTile(1, 0, 0)  -- floor_stone
tilemap:setTile(0, 1, 2)  -- wall_stone
```

### Atlas Layout

Load atlas layout:

```lua
local atlas = Dungeon.AtlasLayout()
atlas:loadFromFile("/textures/dungeon/dungeon_atlas.png")
atlas.tileWidth = 16
atlas.tileHeight = 16
```

### Chunk Building

Build dungeon chunks:

```lua
local chunkDef = Dungeon.ChunkDef()
chunkDef.chunkX = 0
chunkDef.chunkY = 0
chunkDef.tileW = 32
chunkDef.tileH = 32
chunkDef.tileSize = 0.5
chunkDef.layerName = "midground"
chunkDef.generateCollision = true

local chunk = Dungeon.buildChunk(chunkDef, tilemap, atlas)
```

## Tile Types

### Floor Tiles
- **Stone**: Gray stone texture, seamless
- **Brick**: Red brick pattern, seamless
- **Wood**: Wooden planks, seamless
- **Metal**: Metallic grates, seamless
- **Dirt**: Brown dirt texture, seamless
- **Arcane**: Magical runes, purple glow

### Wall Tiles
- **Stone**: Gray stone blocks, seamless
- **Brick**: Red brick blocks, seamless
- **Wood**: Wooden planks, seamless
- **Metal**: Metallic panels, seamless
- **Arcane**: Magical runes, purple glow
- **Corner**: Corner piece for wall connections

### Ceiling Tiles
- **Stone**: Gray stone texture, seamless
- **Wood**: Wooden beams, seamless
- **Metal**: Metallic panels, seamless

### Decorative Tiles
- **Rune**: Magical rune symbol
- **Crack**: Stone crack pattern
- **Moss**: Green moss growth
- **Blood**: Red bloodstain

## Workflow

### Step 1: Generate Tiles

```powershell
.\GenerateDungeonAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Assemble Atlas

Use an atlas builder tool or manually assemble tiles into a texture atlas.

### Step 3: Create Atlas Configuration

Create JSON configuration file for atlas layout.

### Step 4: Create Tilemap Data

Generate or load tilemap data for dungeon layouts.

### Step 5: Build Dungeons

Use dungeon mesh builder to generate dungeon meshes.

## Advanced Options

### Custom Tile Types

Edit `GenerateDungeonAssets.ps1` to add custom tile types:

```powershell
@{
    Id = "custom_tile"
    Name = "Custom Tile"
    Description = "Custom tile description"
}
```

### Tile Variations

Generate multiple variations of each tile type for variety.

### Seamless Tiles

Ensure tiles are seamless for proper tiling in atlases.

## Tips

1. **Tile size**: Use 16x16 or 32x32 pixels for tiles
2. **Seamless**: Ensure tiles tile seamlessly
3. **Atlas size**: Use power-of-2 sizes (256x256, 512x512)
4. **Tile count**: Plan atlas layout to fit all tiles
5. **Variations**: Generate multiple variations for variety

## Troubleshooting

### Tiles Not Tiling

- Ensure tiles are seamless
- Check tile dimensions match atlas configuration
- Verify UV coordinates are correct

### Atlas Not Loading

- Check atlas path is correct
- Verify atlas image exists
- Ensure atlas dimensions match configuration

### Chunks Not Building

- Verify tilemap data is valid
- Check atlas layout is loaded
- Ensure chunk definitions are valid

---

*Part of the Starbound Ollama Asset Generator suite*
