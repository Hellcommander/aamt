# Plugin System Asset Generation Guide

Generate assets for Plugin Systems including plugin management UI, interface manager elements, crafting UI, captain's chair icons, and hyperdrive effects.

## Quick Start

```powershell
# Generate all plugin system assets
.\GeneratePluginAssets.ps1

# Use C++ backend for better quality
.\GeneratePluginAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Plugin Management UI (6 elements)

1. **plugin_enabled** - Plugin enabled indicator
2. **plugin_disabled** - Plugin disabled indicator
3. **plugin_loading** - Plugin loading indicator
4. **plugin_error** - Plugin error indicator
5. **plugin_reload** - Plugin reload button
6. **plugin_settings** - Plugin settings button

### Interface Manager UI (4 elements)

1. **interface_feature_enabled** - Feature enabled indicator
2. **interface_feature_disabled** - Feature disabled indicator
3. **interface_hot_reload** - Hot reload indicator
4. **interface_metrics** - Interface metrics icon

### Crafting UI Icons (6 icons)

1. **crafting_station** - Crafting station icon
2. **crafting_recipe** - Crafting recipe icon
3. **crafting_ingredient** - Crafting ingredient slot icon
4. **crafting_result** - Crafting result slot icon
5. **crafting_craft** - Craft button icon
6. **crafting_cancel** - Cancel button icon

### Captain's Chair Icons (5 icons)

1. **captain_chair_icon** - Captain's chair icon
2. **captain_chair_active** - Chair active indicator
3. **captain_chair_inactive** - Chair inactive indicator
4. **captain_chair_pilot** - Pilot seat icon
5. **captain_chair_command** - Command chair icon

### Hyperdrive Effects (6 effects)

1. **hyperdrive_jump_effect** - Hyperdrive jump particle effect
2. **hyperdrive_travel** - Hyperdrive travel particle effect
3. **hyperdrive_arrival** - Hyperdrive arrival particle effect
4. **hyperdrive_warmup** - Hyperdrive warmup particle effect
5. **hyperdrive_cooldown** - Hyperdrive cooldown particle effect
6. **hyperdrive_icon** - Hyperdrive icon

## Total: ~27 Assets

## Output Structure

```
assets/
├── plugins/
│   ├── ui/
│   │   ├── plugin_enabled.png
│   │   ├── plugin_disabled.png
│   │   ├── plugin_loading.png
│   │   ├── plugin_error.png
│   │   ├── plugin_reload.png
│   │   └── plugin_settings.png
│   ├── interface/
│   │   ├── interface_feature_enabled.png
│   │   ├── interface_feature_disabled.png
│   │   ├── interface_hot_reload.png
│   │   └── interface_metrics.png
│   ├── crafting/
│   │   ├── crafting_station.png
│   │   ├── crafting_recipe.png
│   │   ├── crafting_ingredient.png
│   │   ├── crafting_result.png
│   │   ├── crafting_craft.png
│   │   └── crafting_cancel.png
│   ├── captain_chair/
│   │   ├── captain_chair_icon.png
│   │   ├── captain_chair_active.png
│   │   ├── captain_chair_inactive.png
│   │   ├── captain_chair_pilot.png
│   │   └── captain_chair_command.png
│   └── hyperdrive/
│       ├── hyperdrive_jump_effect.particle
│       ├── hyperdrive_travel.particle
│       ├── hyperdrive_arrival.particle
│       ├── hyperdrive_warmup.particle
│       ├── hyperdrive_cooldown.particle
│       └── hyperdrive_icon.png
```

## Integration

### Plugin Manager

```cpp
// Enable plugin
PluginManager::enablePlugin(pluginId);
// Uses: /plugins/ui/plugin_enabled.png

// Disable plugin
PluginManager::disablePlugin(pluginId);
// Uses: /plugins/ui/plugin_disabled.png

// Reload plugin
PluginManager::reloadPlugin(pluginId);
// Uses: /plugins/ui/plugin_reload.png
```

### Interface Manager

```cpp
// Enable feature
InterfaceManagerBusPlugin::enableFeature(featureName);
// Uses: /plugins/interface/interface_feature_enabled.png

// Hot reload
InterfaceManagerBusPlugin::reloadFeature(featureName);
// Uses: /plugins/interface/interface_hot_reload.png
```

### Crafting Bus Plugin

```cpp
// Open crafting interface
CraftingBusPlugin::openCraftingStation(stationId);
// Uses: /plugins/crafting/crafting_station.png
// Uses: /plugins/crafting/crafting_recipe.png
// Uses: /plugins/crafting/crafting_ingredient.png
// Uses: /plugins/crafting/crafting_result.png
// Uses: /plugins/crafting/crafting_craft.png
// Uses: /plugins/crafting/crafting_cancel.png
```

### Captain's Chair Bus Plugin

```cpp
// Register chair
CaptainChairBusPlugin::registerCaptainChair(entityId, type, name);
// Uses: /plugins/captain_chair/captain_chair_icon.png (for captain's chair)
// Uses: /plugins/captain_chair/captain_chair_pilot.png (for pilot seat)
// Uses: /plugins/captain_chair/captain_chair_command.png (for command chair)

// Player sits down
CaptainChairBusPlugin::onPlayerSitDown(playerId, chairId);
// Uses: /plugins/captain_chair/captain_chair_active.png
```

### Hyperdrive Bus Plugin

```cpp
// Start jump
HyperdriveBusPlugin::startJump(pilotId, targetWorldId, targetPosition);
// Uses: /plugins/hyperdrive/hyperdrive_warmup.particle (during warmup)
// Uses: /plugins/hyperdrive/hyperdrive_jump_effect.particle (jump start)
// Uses: /plugins/hyperdrive/hyperdrive_travel.particle (during travel)
// Uses: /plugins/hyperdrive/hyperdrive_arrival.particle (on arrival)
// Uses: /plugins/hyperdrive/hyperdrive_cooldown.particle (during cooldown)
// Uses: /plugins/hyperdrive/hyperdrive_icon.png (for UI)
```

## Plugin Types

### Plugin States
- **Enabled**: Plugin is active
- **Disabled**: Plugin is inactive
- **Loading**: Plugin is being loaded
- **Error**: Plugin has an error

### Interface Features
- **Enabled**: Feature is active
- **Disabled**: Feature is inactive
- **Hot Reload**: Feature supports hot reloading
- **Metrics**: Feature has performance metrics

### Crafting Elements
- **Station**: Crafting station interface
- **Recipe**: Recipe display
- **Ingredient**: Ingredient slot
- **Result**: Result slot
- **Craft**: Craft action button
- **Cancel**: Cancel action button

### Chair Types
- **Captain's Chair**: Main command chair
- **Pilot Seat**: Pilot interface
- **Command Chair**: Command interface

### Hyperdrive States
- **Warmup**: System warming up
- **Jump**: Jump initiation
- **Travel**: In transit
- **Arrival**: Jump completion
- **Cooldown**: System cooling down

## Workflow

### Step 1: Generate Assets

```powershell
.\GeneratePluginAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Plugins

Set up plugin configurations with asset paths.

### Step 3: Test in Game

Load the mod and test plugin systems in-game.

## Advanced Options

### Custom Plugin Icons

Edit `GeneratePluginAssets.ps1` to add custom plugin icons.

### Custom Crafting UI

Add custom crafting UI elements as needed.

### Custom Hyperdrive Effects

Add custom hyperdrive effects for different jump types.

## Tips

1. **Plugin icons**: Use 32x32 for status indicators
2. **Crafting UI**: Use 64x64 for stations, 32x32 for slots
3. **Chair icons**: Use 64x64 for chair interfaces
4. **Hyperdrive effects**: Match particle colors to jump state
5. **UI consistency**: Keep UI elements consistent in style

## Troubleshooting

### Plugins Not Displaying

- Check plugin icon paths
- Verify icons are in `assets/plugins/ui/`
- Ensure plugin manager is initialized

### Interface Not Showing

- Check interface UI paths
- Verify icons are in `assets/plugins/interface/`
- Ensure interface manager is initialized

### Crafting Not Working

- Verify crafting UI icons are in `assets/plugins/crafting/`
- Check crafting bus plugin is initialized
- Ensure crafting station configurations are correct

### Hyperdrive Effects Not Appearing

- Check hyperdrive effect paths
- Verify effects are in `assets/plugins/hyperdrive/`
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
