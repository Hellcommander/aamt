# Magic UI Element Generator - Guide

## Overview

Generates interesting, magic-themed UI elements (buttons, panels, frames, progress bars) for each magic system in CustomRaceClassCreator. Each system gets visually distinct UI components with appropriate colors, patterns, and effects.

## Quick Start

### Generate All UI Elements for All Systems

```powershell
.\MagicUIElementGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -SystemName "all" -UIElementType "all" -UseAI
```

### Generate UI for Specific Magic System

```powershell
.\MagicUIElementGenerator.bat "E:\...\CustomRaceClassCreator" -SystemName "DragonMagic" -UIElementType "all" -UseAI
```

### Generate Specific UI Element Types

```powershell
.\MagicUIElementGenerator.bat "E:\...\CustomRaceClassCreator" -SystemName "BloodMagic" -UIElementType "button,panel" -UseAI
```

## UI Element Types

### Buttons
- **States**: normal, hover, pressed, disabled
- **Size**: 120×40 pixels
- **Features**: Rounded corners, state-based colors, theme patterns, optional glow

### Panels
- **Variants**: default, header, footer, sidebar
- **Size**: 200×150 pixels
- **Features**: Decorative corners, borders, variant-specific elements

### Frames
- **Styles**: border, ornate, minimal, decorative
- **Size**: 100×100 pixels
- **Features**: Various border styles, corner decorations, pattern overlays

### Progress Bars
- **States**: empty, quarter, half, threequarter, full
- **Size**: 200×20 pixels
- **Features**: Fill states, glow effects, theme colors

## Magic System Themes

Each magic system has a unique visual theme:

| System | Colors | Pattern | Style | Glow |
|--------|--------|---------|-------|------|
| **DragonMagic** | Orange/Red/Yellow | Scales | Fiery Dragon | Yes |
| **BloodMagic** | Dark Red/Crimson | Dripping | Bloody | Yes |
| **Necromancy** | Sickly Green | Skull/Bones | Necrotic | Yes |
| **Ice** | Blue/Cyan | Crystalline | Frost | Yes |
| **Fire** | Red/Orange | Flames | Burning | Yes |
| **Nature** | Green | Leaves | Organic | No |
| **DruidicMagic** | Forest Green | Vines | Druidic | No |
| **Arcane** | Purple/Magenta | Runes | Mystical | Yes |
| **Geomancy** | Brown/Earth | Stone | Earthy | No |
| **Technomancy** | Cyan/Blue | Circuits | Tech | Yes |

## Generated Files

UI elements are saved to:
```
Assets/Resources/[SystemName]/UI/
```

### Button Files
- `button_normal.png` - Default state
- `button_hover.png` - Hover state
- `button_pressed.png` - Pressed state
- `button_disabled.png` - Disabled state

### Panel Files
- `panel_default.png` - Standard panel
- `panel_header.png` - Panel with header bar
- `panel_footer.png` - Panel with footer bar
- `panel_sidebar.png` - Panel with sidebar accent

### Frame Files
- `frame_border.png` - Simple border frame
- `frame_ornate.png` - Ornate decorative frame
- `frame_minimal.png` - Minimal thin frame
- `frame_decorative.png` - Decorative with pattern

### Progress Bar Files
- `progressbar_empty.png` - Empty state
- `progressbar_quarter.png` - 25% filled
- `progressbar_half.png` - 50% filled
- `progressbar_threequarter.png` - 75% filled
- `progressbar_full.png` - 100% filled

## Usage Examples

### Example 1: Generate UI for Fire-Based Systems

```powershell
.\MagicUIElementGenerator.bat "E:\...\CustomRaceClassCreator" `
    -SystemName "DragonMagic,Fire,ElementMagic" `
    -UIElementType "all" `
    -UseAI
```

### Example 2: Generate Buttons and Panels Only

```powershell
.\MagicUIElementGenerator.bat "E:\...\CustomRaceClassCreator" `
    -SystemName "all" `
    -UIElementType "button,panel" `
    -UseAI
```

### Example 3: Generate UI for Dark Magic Systems

```powershell
.\MagicUIElementGenerator.bat "E:\...\CustomRaceClassCreator" `
    -SystemName "BloodMagic,Necromancy,SpectreMagic" `
    -UIElementType "all" `
    -UseAI
```

## Visual Features

### Pattern Elements

**Scale Pattern** (DragonMagic):
- Overlapping scale shapes
- Creates dragon-like texture

**Dripping Pattern** (BloodMagic):
- Dripping blood effects
- Dark, visceral appearance

**Rune Pattern** (Arcane):
- Runic symbols along borders
- Mystical, magical appearance

**Crystalline Pattern** (Ice):
- Angular, geometric shapes
- Reflective, icy appearance

**Vine Pattern** (Druidic):
- Organic, flowing lines
- Natural, plant-like appearance

### Glow Effects

Systems with glow enabled get:
- Soft outer glow on UI elements
- Enhanced visibility
- Magical appearance

### Color Gradients

Each element uses:
- Base color from theme
- Highlight color (lighter variant)
- Shadow color (darker variant)
- Accent color for details

## Integration with Unity

1. **Import Assets**: UI elements are automatically detected in `Assets/Resources/`
2. **Create UI Prefabs**: Use generated images in Unity UI Image components
3. **State Management**: Use different button states for hover/pressed effects
4. **Material Assignment**: Apply to UI materials for consistent theming

## Customization

### Adding New Themes

Edit the `$script:MagicThemes` hashtable in the script to add new magic system themes.

### Customizing Patterns

Modify the Python generation scripts in each `Generate-UI*` function to add new patterns.

### Adjusting Sizes

Edit `$script:UIElementConfigs` to change default sizes for each element type.

## Requirements

- **Python 3.x** with PIL/Pillow
- **Ollama** (optional, for AI specifications)
- **PowerShell 5.1+**

## Best Practices

1. **Generate Per System**: Generate UI for one system at a time to review results
2. **Use AI**: Enable `-UseAI` for better, more creative designs
3. **Test in Unity**: Import and test UI elements in Unity before committing
4. **Consistent Theming**: Use the same element types across related systems

## See Also

- `CustomRaceClassCreatorAssetGenerator.ps1` - For textures and other assets
- `ElinSpellAssetGenerator.ps1` - For spell-specific assets
- CustomRaceClassCreator mod documentation

---

**Version**: 1.0  
**Focus**: Magic-themed UI elements for immersive game interfaces

