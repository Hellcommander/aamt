# CDDA Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the CDDA (Cataclysm: Dark Days Ahead) toolset integrates with AAMT's unified tool detection and integration system.

## Overview

The CDDA toolset generates creature assets for Cataclysm: Dark Days Ahead mods. The toolset has been integrated with AAMT's unified tool detection system for consistent tool management.

## Integrated Scripts

### ✅ CDDABeeSwarmGenerator.ps1
- **Purpose**: Generates bee swarm creature assets for CDDA mods
- **Required Tools**: None (uses built-in .NET System.Drawing)
- **Optional Tools**: Python, ImageMagick
- **Integration**: 
  - Uses `Initialize-ToolsetTools` to check for optional tools
  - Displays tool status with `Show-ToolsetStatus`
  - Works without external dependencies (uses System.Drawing for image generation)
- **Status**: Fully integrated

### ✅ CDDABeeSwarmGenerator.bat
- **Purpose**: Wrapper script for `CDDABeeSwarmGenerator.ps1`
- **Integration**: Added AAMT header comment
- **Status**: Updated

## Tool Requirements

### CDDABeeSwarmGenerator.ps1
- **Required**: None (uses built-in .NET System.Drawing for sprite generation)
- **Optional**: 
  - Python (for any Python-based utilities)
  - ImageMagick (for image post-processing)

## Usage Examples

### Generate Bee Swarm Creature
```powershell
.\CDDABeeSwarmGenerator.ps1 `
    -SwarmName "bee_swarm" `
    -TileSize 16 `
    -SwarmSize Medium `
    -OutputDir "CDDAMods\BeeSwarm"
```

### Generate with Control Room
```powershell
.\CDDABeeSwarmGenerator.ps1 `
    -SwarmName "bee_swarm" `
    -TileSize 32 `
    -SwarmSize Large `
    -LaunchControlRoom
```

### Generate Custom Swarm
```powershell
.\CDDABeeSwarmGenerator.ps1 `
    -SwarmName "wasp_swarm" `
    -TileSize 16 `
    -SwarmSize Small `
    -OutputDir "CDDAMods\WaspSwarm" `
    -WatchDirectory "CDDAMods\WaspSwarm\watch"
```

## Integration Benefits

1. **Unified Detection**: Uses the same detection logic as other toolsets
2. **Clear Error Messages**: Installation hints when tools are missing
3. **Consistent Behavior**: Handles missing tools the same way as other toolsets
4. **Self-Contained**: Works without external dependencies using built-in .NET graphics
5. **Optional Tools**: Python and ImageMagick enhance but don't block execution

## Error Handling

### Missing Optional Tools
- Script continues with built-in .NET graphics
- Clear status messages indicate missing tools
- Installation hints are provided for optional tools

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## Generated Assets

The generator creates:
- **Sprites**: Individual sprite files for each direction and animation frame
- **Spritesheet**: Combined tileset spritesheet (8 directions × 3 frames)
- **Creature Definition**: JSON file with creature stats and properties
- **Mod Info**: modinfo.json for CDDA mod system
- **Tileset Definition**: Text file with tileset configuration
- **README**: Installation and usage instructions
- **Metadata**: Generation metadata JSON file

## Swarm Sizes

- **Small**: 5 bees, 60% tile radius
- **Medium**: 10 bees, 80% tile radius (default)
- **Large**: 20 bees, 100% tile radius

## Directions Supported

8-directional sprites:
- N (North)
- NE (Northeast)
- E (East)
- SE (Southeast)
- S (South)
- SW (Southwest)
- W (West)
- NW (Northwest)

## Animation Frames

- **Idle**: Stationary swarm
- **Flying**: Moving swarm
- **Attacking**: Aggressive swarm

## Tile Sizes

- **16x16**: Standard CDDA tile size
- **32x32**: High-resolution tile size

## Output Structure

```
CDDAMods/
└── BeeSwarm/
    ├── generation_metadata.json
    ├── mods/
    │   └── bee_swarm/
    │       ├── creatures/
    │       │   └── bee_swarm.json
    │       ├── gfx/
    │       │   └── tileset/
    │       │       ├── bee_swarm_tileset.png
    │       │       └── bee_swarm_tileset.txt
    │       ├── modinfo.json
    │       └── README.md
    └── watch/
        └── (individual sprite files)
```

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
