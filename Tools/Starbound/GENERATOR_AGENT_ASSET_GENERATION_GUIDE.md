# GeneratorAgent System Asset Generation Guide

Generate UI assets for the GeneratorAgent System including panels, browser elements, category icons, preview controls, export elements, settings, status indicators, and action buttons.

## Quick Start

```powershell
# Generate all GeneratorAgent UI assets
.\GenerateGeneratorAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateGeneratorAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Generator UI Panel Elements (5 elements)

1. **generator_panel_background** - Panel background texture
2. **generator_panel_border** - Panel border texture
3. **generator_tab_active** - Active tab icon
4. **generator_tab_inactive** - Inactive tab icon
5. **generator_separator** - Separator line texture

### Asset Browser Elements (6 elements)

1. **browser_folder_icon** - Folder icon
2. **browser_file_icon** - File icon
3. **browser_asset_icon** - Asset icon
4. **browser_refresh** - Refresh button
5. **browser_search** - Search icon
6. **browser_filter** - Filter icon

### Generator Category Icons (10 icons)

1. **generator_category_mechs** - Mechs category
2. **generator_category_spells** - Spells category
3. **generator_category_projectiles** - Projectiles category
4. **generator_category_particles** - Particles category
5. **generator_category_textures** - Textures category
6. **generator_category_meshes** - Meshes category
7. **generator_category_animations** - Animations category
8. **generator_category_ui** - UI category
9. **generator_category_status** - Status effects category
10. **generator_category_icons** - Icons category

### Preview Panel Elements (7 elements)

1. **preview_play** - Play button
2. **preview_pause** - Pause button
3. **preview_stop** - Stop button
4. **preview_reset** - Reset button
5. **preview_zoom_in** - Zoom in button
6. **preview_zoom_out** - Zoom out button
7. **preview_rotate** - Rotate button

### Export Panel Elements (6 elements)

1. **export_button** - Export button
2. **export_format_png** - PNG format icon
3. **export_format_json** - JSON format icon
4. **export_format_particle** - Particle format icon
5. **export_success** - Export success indicator
6. **export_failed** - Export failed indicator

### Settings Panel Elements (4 elements)

1. **settings_icon** - Settings icon
2. **settings_save** - Save settings button
3. **settings_reset** - Reset settings button
4. **settings_advanced** - Advanced settings indicator

### Generator Status Indicators (5 indicators)

1. **generator_idle** - Generator idle status
2. **generator_generating** - Generator generating status
3. **generator_complete** - Generator complete status
4. **generator_error** - Generator error status
5. **generator_progress** - Generator progress bar

### Generator Action Buttons (6 buttons)

1. **action_generate** - Generate button
2. **action_cancel** - Cancel button
3. **action_save** - Save button
4. **action_load** - Load button
5. **action_new** - New button
6. **action_delete** - Delete button

## Total: ~49 Assets

## Output Structure

```
assets/
├── generator/
│   └── ui/
│       ├── panels/
│       │   ├── generator_panel_background.png
│       │   ├── generator_panel_border.png
│       │   ├── generator_tab_active.png
│       │   ├── generator_tab_inactive.png
│       │   └── generator_separator.png
│       ├── browser/
│       │   ├── browser_folder_icon.png
│       │   ├── browser_file_icon.png
│       │   ├── browser_asset_icon.png
│       │   ├── browser_refresh.png
│       │   ├── browser_search.png
│       │   └── browser_filter.png
│       ├── categories/
│       │   ├── generator_category_mechs.png
│       │   ├── generator_category_spells.png
│       │   └── ... (all category icons)
│       ├── preview/
│       │   ├── preview_play.png
│       │   ├── preview_pause.png
│       │   └── ... (all preview controls)
│       ├── export/
│       │   ├── export_button.png
│       │   ├── export_format_png.png
│       │   └── ... (all export elements)
│       ├── settings/
│       │   ├── settings_icon.png
│       │   ├── settings_save.png
│       │   └── ... (all settings elements)
│       ├── status/
│       │   ├── generator_idle.png
│       │   ├── generator_generating.png
│       │   └── ... (all status indicators)
│       └── actions/
│           ├── action_generate.png
│           ├── action_cancel.png
│           └── ... (all action buttons)
```

## Integration

### UnifiedAssetGeneratorUI

```cpp
// Show main window
UnifiedAssetGeneratorUI::showMainWindow();
// Uses: /generator/ui/panels/generator_panel_background.png
// Uses: /generator/ui/panels/generator_panel_border.png
// Uses: /generator/ui/panels/generator_tab_*.png for tabs

// Render asset browser
UnifiedAssetGeneratorUI::renderAssetBrowser();
// Uses: /generator/ui/browser/browser_*.png for browser elements

// Render category tabs
UnifiedAssetGeneratorUI::renderCategoryTabs();
// Uses: /generator/ui/categories/generator_category_*.png

// Render preview panel
UnifiedAssetGeneratorUI::renderPreviewPanel();
// Uses: /generator/ui/preview/preview_*.png for preview controls

// Render export panel
UnifiedAssetGeneratorUI::renderExportPanel();
// Uses: /generator/ui/export/export_*.png for export elements

// Render settings panel
UnifiedAssetGeneratorUI::renderSettingsPanel();
// Uses: /generator/ui/settings/settings_*.png

// Render status bar
UnifiedAssetGeneratorUI::renderStatusBar();
// Uses: /generator/ui/status/generator_*.png for status indicators
```

### Generator Factories

```cpp
// Generate asset
WormMechFactory::generateAsync(params, ui);
// Uses: /generator/ui/status/generator_generating.png during generation
// Uses: /generator/ui/status/generator_complete.png on completion
// Uses: /generator/ui/status/generator_error.png on error
// Uses: /generator/ui/actions/action_generate.png for generate button
```

## Generator Categories

### Category Types
- **Mechs**: Mech generation
- **Spells**: Spell generation
- **Projectiles**: Projectile generation
- **Particles**: Particle generation
- **Textures**: Texture generation
- **Meshes**: Mesh generation
- **Animations**: Animation generation
- **UI**: UI element generation
- **Status Effects**: Status effect generation
- **Icons**: Icon generation

## Generator States

### Status States
- **Idle**: Generator is idle
- **Generating**: Generator is actively generating
- **Complete**: Generation completed successfully
- **Error**: Generation encountered an error
- **Progress**: Generation progress indicator

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateGeneratorAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Generator UI

Set up UnifiedAssetGeneratorUI with asset paths.

### Step 3: Test in Game

Load the mod and test generator UI in-game.

## Advanced Options

### Custom Generator Categories

Edit `GenerateGeneratorAgentAssets.ps1` to add custom generator categories.

### Custom UI Elements

Add custom UI elements as needed for specific generator types.

### Custom Status Indicators

Add custom status indicators for additional generator states.

## Tips

1. **Panel elements**: Use 128x128 for backgrounds, 64x32 for tabs
2. **Browser icons**: Use 32x32 for file/folder icons
3. **Category icons**: Use 32x32 for category display
4. **Preview controls**: Use 32x32 for control buttons
5. **Action buttons**: Use 64x32 for action buttons
6. **Status indicators**: Make status clearly visible
7. **UI consistency**: Keep all UI elements consistent in style

## Troubleshooting

### Generator UI Not Displaying

- Check UI element paths
- Verify elements are in `assets/generator/ui/`
- Ensure UnifiedAssetGeneratorUI is initialized

### Categories Not Showing

- Check category icon paths
- Verify icons are in `assets/generator/ui/categories/`
- Ensure category system is configured

### Preview Not Working

- Check preview control paths
- Verify controls are in `assets/generator/ui/preview/`
- Ensure preview system is initialized

### Export Not Functioning

- Check export element paths
- Verify elements are in `assets/generator/ui/export/`
- Ensure export system is configured

---

*Part of the Starbound Ollama Asset Generator suite*
