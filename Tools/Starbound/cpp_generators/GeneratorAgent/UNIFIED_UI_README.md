# Unified Asset Generator UI System

The Unified Asset Generator UI provides a comprehensive interface for managing and generating all asset types in the Magi-Tech mod. This system integrates all the different asset generators into a single, cohesive interface.

## Overview

The unified UI system consists of:

1. **UnifiedAssetGeneratorUI** - Main UI class that orchestrates all asset generation
2. **IAssetGenerator** - Interface for all asset generators
3. **AssetGeneratorFactory** - Factory for creating and managing generators
4. **AssetMetadata** - Standardized asset information structure
5. **UIUtils** - Utility functions for UI rendering and asset management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UnifiedAssetGeneratorUI                     │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │Asset Browser│  │Generator    │  │Preview      │          │
│  │             │  │Panel        │  │Panel        │          │
│  │• Category   │  │• Parameters │  │• Asset Info │          │
│  │• Search     │  │• Generation │  │• Preview    │          │
│  │• Asset List │  │• Export     │  │• Controls   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Export Panel                        │   │
│  │• Export Options • Batch Export • Format Selection     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Asset Generator Factory                     │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │Mech         │  │Projectile   │  │Weapon       │          │
│  │Generators   │  │Generators   │  │Generators   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │Effect       │  │Audio        │  │Visual       │          │
│  │Generators   │  │Generators   │  │Generators   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Asset Categories

The UI organizes assets into logical categories:

### 🚁 **MECHS**
- Basic Mech
- Mini Jet
- Quad Mech
- Centipede Mech
- Worm Mech
- Snake Mech

### ⚡ **PROJECTILES**
- Basic Projectile
- Blackhole Projectile
- Lightning Projectile
- Comet Projectile
- Flame Projectile
- Gyro Projectile
- Ice Shard
- Explosive Projectile
- Homing Missile
- Acid Projectile
- Cluster Bomb
- Shotgun Pellet
- Boomerang Disc

### ⚔️ **WEAPONS**
- Segmented Weapon
- Crossbow
- Beam Net
- Grapple Hook

### 🐛 **CREATURES**
- Segmented Creature
- Monster

### ✨ **EFFECTS**
- Status Effect
- Vortex Spell
- Frost Nova
- Particle Field
- Portal

### 🎵 **AUDIO**
- Audio Asset

### 🎨 **VISUAL**
- Light
- Trail
- Particle
- Geometry
- Atlas
- Texture
- Mesh
- Animation
- Shader

### 🖥️ **UI**
- UI Asset
- Icon Asset
- Cockpit

### 🔧 **UTILITY**
- Damage System
- Ingredient
- Spellstone
- Room
- Magical Item
- Orb
- Trap

### 🌌 **COSMIC**
- Cosmic
- Beam
- Spell
- Snake Spell

### ⚙️ **SYSTEM**
- Dynamic Asset
- Procedural
- Fireball
- Plasma Disc
- Drone Minion

## UI Features

### Main Window Layout

The main window is divided into four panels:

1. **Asset Browser** (Left)
   - Category tabs
   - Search functionality
   - Asset library
   - Quick filters

2. **Generator Panel** (Center)
   - Category selection
   - Generator list
   - Asset type selection
   - Parameter configuration

3. **Preview Panel** (Right)
   - Asset information
   - Preview area
   - Quick actions
   - Asset controls

4. **Export Panel** (Bottom)
   - Export options
   - Batch export
   - Format selection
   - Export controls

### Menu System

#### File Menu
- **New Asset** (Ctrl+N) - Create new asset
- **Open Asset** (Ctrl+O) - Load existing asset
- **Save Asset** (Ctrl+S) - Save current asset
- **Export Asset** (Ctrl+E) - Export asset
- **Exit** - Close application

#### View Menu
- **Asset Browser** - Toggle asset browser panel
- **Generator Panel** - Toggle generator panel
- **Preview Panel** - Toggle preview panel
- **Export Panel** - Toggle export panel
- **Settings** - Open settings panel

#### Tools Menu
- **Batch Generate** - Generate multiple assets
- **Asset Library** - Manage asset library
- **Settings** - Configure application

#### Help Menu
- **Documentation** - Show documentation
- **About** - Show about dialog

## Asset Generation Workflow

### 1. Select Category
Choose the asset category from the category tabs:
```
[Mechs] [Projectiles] [Weapons] [Creatures] [Effects] [Audio] [Visual] [Utility] [Cosmetic] [System]
```

### 2. Choose Generator
Select the appropriate generator for your asset type:
```
Available Generators:
• MechGenerator
• MiniJetGenerator
• QuadMechGenerator
• CentipedeMechGenerator
• StatusEffectGenerator
• BlackholeProjectileGenerator
• AlchemicalLauncherGenerator
• ... (and many more)
```

### 3. Select Asset Type
Choose the specific asset type:
```
Asset Types:
• Basic Mech
• Mini Jet
• Quad Mech
• Centipede Mech
• Worm Mech
• Snake Mech
```

### 4. Configure Parameters
Set the asset parameters:
```
Asset Name: [My Awesome Mech]
Description: [A powerful mech for combat]
Version: [1.0.0]
Author: [Your Name]

Generator Parameters:
• Morph Weight: [0.5] ████████░░
• Module Visibility: [1.0] ██████████
• LOD Level: [2]
• Weapon Firing: [☑]
• Effects Active: [☑]
```

### 5. Generate Asset
Click the "Generate Asset" button to create your asset.

### 6. Preview and Export
Review the generated asset and export it to your desired format.

## Asset Metadata

All assets use a standardized metadata structure:

```cpp
struct AssetMetadata {
    std::string name;                    // Asset name
    std::string description;             // Asset description
    AssetCategory category;              // Asset category
    AssetType type;                      // Asset type
    std::string version;                 // Version string
    std::string author;                  // Author name
    std::vector<std::string> tags;      // Asset tags
    std::unordered_map<std::string, std::any> parameters; // Generator parameters
    bool isGenerated;                    // Generation status
    std::string outputPath;              // Output file path
    std::chrono::system_clock::time_point creationTime; // Creation timestamp
};
```

## Generator Integration

### Creating a Custom Generator

1. **Implement IAssetGenerator Interface**

```cpp
class MyCustomGenerator : public IAssetGenerator {
public:
    bool initialize() override {
        // Initialize your generator
        return true;
    }
    
    void shutdown() override {
        // Cleanup resources
    }
    
    bool isInitialized() const override {
        return m_initialized;
    }
    
    bool generateAsset(const AssetMetadata& metadata) override {
        // Generate your asset
        return true;
    }
    
    bool validateParameters(const std::unordered_map<std::string, std::any>& params) override {
        // Validate parameters
        return true;
    }
    
    std::vector<std::string> getSupportedParameters() const override {
        return {"param1", "param2", "param3"};
    }
    
    std::vector<std::string> getSupportedAssetTypes() const override {
        return {"My Custom Asset"};
    }
    
    std::string getName() const override {
        return "MyCustomGenerator";
    }
    
    std::string getVersion() const override {
        return "1.0.0";
    }
    
    AssetCategory getCategory() const override {
        return AssetCategory::UTILITY;
    }
    
    std::vector<AssetType> getSupportedAssetTypes() const override {
        return {AssetType::CUSTOM_ASSET};
    }
    
    void renderUI() override {
        // Render custom UI
    }
    
    void renderParameters() override {
        // Render parameter controls
    }
    
    void renderPreview() override {
        // Render preview
    }
    
    void renderExport() override {
        // Render export options
    }
    
private:
    bool m_initialized = false;
};
```

2. **Register Your Generator**

```cpp
// In your initialization code
auto& factory = AssetGeneratorFactory::getInstance();
factory.registerGenerator("my_custom", []() -> std::unique_ptr<IAssetGenerator> {
    return std::make_unique<MyCustomGenerator>();
});

// Register with category
factory.registerCategoryGenerator(AssetCategory::UTILITY, "my_custom");
```

3. **Add to UI**

```cpp
// Register with UI
ui.registerGenerator("my_custom", std::make_unique<MyCustomGenerator>());
```

## Configuration System

### Saving Configuration

```cpp
// Save UI state and asset library
ui.saveConfiguration("config.json");
```

### Loading Configuration

```cpp
// Load UI state and asset library
ui.loadConfiguration("config.json");
```

### Configuration Format

```json
{
  "ui_state": {
    "active_category": 0,
    "active_generator": "MechGenerator",
    "active_asset_type": 0,
    "show_asset_browser": true,
    "show_generator_panel": true,
    "show_preview_panel": true,
    "show_export_panel": true,
    "show_settings_panel": false
  },
  "asset_library": [
    {
      "name": "My Mech",
      "description": "A powerful mech",
      "category": 0,
      "type": 0,
      "version": "1.0.0",
      "author": "Your Name",
      "tags": ["combat", "mech"],
      "parameters": {
        "morph_weight": 0.5,
        "module_visibility": 1.0,
        "lod_level": 2,
        "weapon_firing": true,
        "effects_active": true
      },
      "is_generated": true,
      "output_path": "assets/mechs/my_mech.json"
    }
  ]
}
```

## Export System

### Export Options

- **Export Metadata** - Include asset metadata
- **Export Preview** - Include preview images
- **Export Source** - Include source files
- **Export Format** - JSON, YAML, Binary, Custom

### Batch Export

```cpp
// Export multiple assets
std::vector<AssetMetadata> assets = {
    asset1, asset2, asset3
};
ui.exportBatch(assets, "output_directory");
```

## Asset Library Management

### Adding Assets

```cpp
AssetMetadata asset;
asset.name = "My Asset";
asset.description = "Asset description";
asset.category = AssetCategory::MECHS;
asset.type = AssetType::MECH_BASIC;
asset.version = "1.0.0";
asset.author = "Your Name";

ui.addAssetToLibrary(asset);
```

### Searching Assets

The asset browser supports:
- **Text Search** - Search by name or description
- **Category Filter** - Filter by asset category
- **Type Filter** - Filter by asset type
- **Tag Filter** - Filter by asset tags

### Asset Organization

Assets are automatically organized by:
- **Category** - Primary organization
- **Type** - Secondary organization
- **Author** - Tertiary organization
- **Tags** - Flexible organization

## Quick Actions

### Asset Operations
- **Duplicate** - Create copy of asset
- **Export** - Export asset
- **Delete** - Remove asset from library
- **Edit** - Modify asset parameters

### Batch Operations
- **Generate All** - Generate all assets in library
- **Export All** - Export all assets
- **Validate All** - Validate all assets
- **Clean Library** - Remove invalid assets

## Performance Features

### Caching
- **Asset Cache** - Cache generated assets
- **Preview Cache** - Cache preview images
- **Parameter Cache** - Cache parameter values

### Optimization
- **Lazy Loading** - Load generators on demand
- **Background Generation** - Generate assets in background
- **Memory Management** - Automatic cleanup of unused resources

## Error Handling

### Validation
- **Parameter Validation** - Validate generator parameters
- **Asset Validation** - Validate asset metadata
- **Export Validation** - Validate export settings

### Error Reporting
- **Error Messages** - Clear error messages
- **Error Logging** - Detailed error logging
- **Error Recovery** - Automatic error recovery

## Extensibility

### Plugin System
- **Generator Plugins** - Add new generators
- **UI Plugins** - Add custom UI elements
- **Export Plugins** - Add custom export formats

### Customization
- **Theme Support** - Custom UI themes
- **Layout Customization** - Custom panel layouts
- **Hotkey Customization** - Custom keyboard shortcuts

## Usage Examples

### Basic Asset Generation

```cpp
// Create UI
UnifiedAssetGeneratorUI ui;

// Register generators
ui.registerGenerator("mech", std::make_unique<MechGenerator>());
ui.registerGenerator("projectile", std::make_unique<ProjectileGenerator>());

// Show main window
ui.showMainWindow();
```

### Custom Asset Generation

```cpp
// Create custom asset
AssetMetadata asset;
asset.name = "Custom Mech";
asset.description = "A custom mech design";
asset.category = AssetCategory::MECHS;
asset.type = AssetType::MECH_BASIC;
asset.version = "1.0.0";
asset.author = "Your Name";
asset.parameters["morph_weight"] = 0.7f;
asset.parameters["module_visibility"] = 1.0f;

// Generate asset
ui.generateAsset("mech", asset);
```

### Batch Generation

```cpp
// Create multiple assets
std::vector<AssetMetadata> assets;
for (int i = 0; i < 10; i++) {
    AssetMetadata asset;
    asset.name = "Mech " + std::to_string(i);
    asset.category = AssetCategory::MECHS;
    asset.type = AssetType::MECH_BASIC;
    asset.parameters["morph_weight"] = static_cast<float>(i) / 10.0f;
    assets.push_back(asset);
}

// Batch generate
ui.batchGenerateAssets(assets);
```

This unified UI system provides a comprehensive interface for managing all asset types in the Magi-Tech mod, making asset generation efficient, organized, and user-friendly. 