# Tile Library Asset Generation Pipeline

A comprehensive system for generating curated, license-compliant tile libraries by scanning permitted assets, validating licenses, producing variants, and packing them into runtime atlases.

## 🎯 **Overview**

The Tile Library Builder provides a complete pipeline for:
- **License-based asset ingestion** from manifest files or directory scanning
- **Automatic license validation** against allowlists (CC0, CC-BY, MIT)
- **Parametric variant generation** with color tinting, noise overlays, and transformations
- **Texture atlas packing** with efficient UV coordinate generation
- **Lua integration** for runtime tile lookup and world generation

## 📁 **File Structure**

```
tile_library_builder/
├── TileLibraryBuilder.hpp          # Main builder class header
├── TileLibraryBuilder.cpp          # Complete pipeline implementation
├── TileLibraryLuaBindings.hpp     # Lua bindings header
├── TileLibraryLuaBindings.cpp     # Lua integration
└── README.md                      # This documentation
```

## 🔧 **Core Components**

### **TileAsset Structure**
```cpp
struct TileAsset {
    fs::path path;                    // File path to image
    std::string license;              // License type (CC0, CC-BY, MIT)
    std::string category;             // Category (floor, wall, ceiling, prop, trap)
    std::vector<std::string> tags;    // Searchable tags
    glm::ivec2 size = {64, 64};      // Tile dimensions
    uint64_t hashKey() const;         // For caching
};
```

### **TileVariant Structure**
```cpp
struct TileVariant {
    std::string baseId;               // Original tile ID
    glm::vec4 tintColor;              // Color tinting
    float noiseIntensity;             // Wear/noise overlay
    float rotation;                   // Rotation in degrees
    bool mirrored;                    // Horizontal flip
    uint64_t hashKey() const;         // For caching
};
```

### **AtlasMetadata Structure**
```cpp
struct AtlasMetadata {
    std::string atlasName;            // Atlas identifier
    std::string texturePath;          // Output texture file
    glm::ivec2 tileSize;             // Individual tile size
    glm::ivec2 atlasSize;            // Atlas dimensions
    std::unordered_map<std::string, AtlasTile> tiles;  // Tile lookup
    uint64_t hashKey() const;         // For caching
};
```

## 🚀 **Usage Examples**

### **C++ Usage**
```cpp
#include "TileLibraryBuilder.hpp"

// Create builder instance
TileLibraryBuilder builder;

// Configure settings
builder.setTileSize({64, 64});
builder.setAtlasSize({512, 256});
builder.setAllowedLicenses({"CC0", "CC-BY", "MIT"});

// Load assets from manifest
builder.loadManifest("assets/tiles/manifest.json");

// Or scan directory automatically
builder.scanDirectory("assets/tiles/");
builder.categorizeAssets();

// Validate licenses
builder.validateLicenses({"CC0", "CC-BY", "MIT"});

// Generate variants
builder.generateVariants(3);  // 3 variants per tile

// Pack into atlases
builder.packAtlases("output/atlases/");

// Write metadata
builder.writeMetadata("output/atlases/");
```

### **Lua Usage**
```lua
-- Load from manifest
TileLibrary.loadFromManifest("assets/tiles/manifest.json")

-- Build complete pipeline
TileLibrary.buildAtlases("output/atlases/", 3)

-- Look up tile UVs
local uv = TileLibrary.getTileUV("oak_plain")
if uv then
    print("UV: ", uv.x, uv.y, uv.z, uv.w)
end

-- Get tiles by category
local floorTiles = TileLibrary.getTilesByCategory("floor")
for i, tileId in pairs(floorTiles) do
    print("Floor tile: " .. tileId)
end

-- Get atlas information
local info = TileLibrary.getAtlasInfo("atlas_floor")
if info then
    print("Atlas: " .. info.name)
    print("Tiles: " .. info.tileCount)
end
```

## 📋 **Manifest Format**

The manifest file (`manifest.json`) defines all tile assets:

```json
[
  {
    "path": "floors/oak_plain.png",
    "license": "CC0",
    "category": "floor",
    "tags": ["wood", "indoor", "natural"],
    "size": [64, 64]
  },
  {
    "path": "walls/cracked_stone.png",
    "license": "CC-BY",
    "category": "wall",
    "tags": ["stone", "ruins", "damaged"],
    "size": [64, 64]
  }
]
```

## 🎨 **Variant Generation**

The system automatically generates parametric variants:

- **Color Tinting**: Random hue/saturation adjustments
- **Noise Overlays**: Perlin/FBM noise for wear effects
- **Rotation**: Random 0-360° rotation
- **Mirroring**: Random horizontal flips

```cpp
// Example variant parameters
TileVariant variant;
variant.tintColor = glm::vec4(0.8f, 0.9f, 1.0f, 1.0f);  // Blue tint
variant.noiseIntensity = 0.2f;                             // 20% noise
variant.rotation = 45.0f;                                  // 45° rotation
variant.mirrored = true;                                   // Horizontal flip
```

## 📦 **Atlas Packing**

### **Grid-Based Packing**
- Tiles are packed in a regular grid within each atlas
- UV coordinates are automatically calculated
- Each category gets its own atlas (floor, wall, ceiling, prop, trap)

### **Atlas Structure**
```
atlas_floor.png
├── oak_plain (0,0)     → UV: (0.0, 0.0, 0.125, 0.25)
├── mossy_stone (1,0)   → UV: (0.125, 0.0, 0.25, 0.25)
├── metal_grating (2,0) → UV: (0.25, 0.0, 0.375, 0.25)
└── ...
```

### **Metadata Output**
```json
{
  "atlas": "atlas_floor.png",
  "tileSize": [64, 64],
  "atlasSize": [512, 256],
  "tiles": {
    "oak_plain": {
      "uv": [0.0, 0.0, 0.125, 0.25],
      "license": "CC0",
      "category": "floor",
      "size": [64, 64]
    }
  }
}
```

## 🔍 **License Validation**

### **Supported Licenses**
- **CC0**: Public domain (unrestricted use)
- **CC-BY**: Creative Commons Attribution
- **MIT**: MIT License

### **Validation Process**
1. Read license from manifest or filename
2. Check against allowed license list
3. Reject assets with non-compliant licenses
4. Log warnings for rejected assets

## 🎮 **Runtime Integration**

### **Tile Lookup**
```lua
-- Get UV coordinates for rendering
local uv = TileLibrary.getTileUV("oak_plain")
if uv then
    -- Use uv.x, uv.y, uv.z, uv.w for texture sampling
    renderTile(x, y, uv)
end
```

### **Category Filtering**
```lua
-- Get all floor tiles for UI selection
local floorTiles = TileLibrary.getTilesByCategory("floor")
for i, tileId in pairs(floorTiles) do
    addToDropdown(tileId)
end
```

### **Atlas Information**
```lua
-- Get atlas details for loading
local info = TileLibrary.getAtlasInfo("atlas_floor")
if info then
    loadTexture(info.texture)
    setTileSize(info.tileSize)
end
```

## 🛠️ **Configuration Options**

### **Tile Size**
```cpp
builder.setTileSize({64, 64});    // 64x64 pixels
builder.setTileSize({128, 128});  // 128x128 pixels
```

### **Atlas Size**
```cpp
builder.setAtlasSize({512, 256});   // 512x256 atlas
builder.setAtlasSize({1024, 1024}); // 1024x1024 atlas
```

### **Allowed Licenses**
```cpp
builder.setAllowedLicenses({"CC0", "CC-BY"});  // Only CC0 and CC-BY
builder.setAllowedLicenses({"CC0"});           // Only CC0
```

## 📊 **Performance Features**

### **Caching**
- Hash-based caching for all assets and variants
- LRU eviction for memory management
- Async generation support

### **Memory Management**
- Efficient UV coordinate storage
- Minimal metadata overhead
- Automatic cleanup on shutdown

### **Thread Safety**
- Concurrent atlas packing
- Thread-safe asset validation
- Async variant generation

## 🔮 **Future Extensions**

### **Planned Features**
- **GPU-accelerated variant generation** using compute shaders
- **Advanced bin packing** (max-rects, shelf algorithms)
- **Normal map generation** for lighting
- **LOD system** for different detail levels
- **Web-based manifest editor** with license pickers

### **Integration Points**
- **World generation** systems
- **Level editor** tools
- **Asset management** pipelines
- **Modding support** for custom tiles

## 📝 **License Compliance**

This system ensures all generated assets comply with their original licenses:

- **CC0**: No restrictions, can be used commercially
- **CC-BY**: Must credit original author
- **MIT**: Must include license text

The pipeline automatically tracks and preserves license information throughout the generation process.

---

**Status**: ✅ **Complete Implementation**
**Next Steps**: Integrate with world generation systems and add GPU-accelerated variant generation. 