# Slot Magic Asset Generator - Guide

## Overview

Generates high-quality slot machine assets for the SlotMagic system in CustomRaceClassCreator. Creates visually appealing slot reels, magic-themed symbols, and complete slot machine UI.

## Quick Start

```powershell
.\SlotMagicAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -UseAI
```

Or drag the mod folder onto the batch file.

## Generated Assets

### Slot Reel Frame
- **File**: `slot_reel_frame.png`
- **Size**: 80×240 pixels
- **Description**: 3D-style reel container with gold frame, decorative corners, and divider lines
- **Features**: 
  - Gold/metallic frame
  - Dark background for symbol visibility
  - Divider lines marking 3 symbol positions
  - Glow effects

### Slot Reel Background
- **File**: `slot_reel_background.png`
- **Size**: 64×224 pixels (inner area)
- **Description**: Background texture for spinning reels
- **Features**: Subtle pattern for visual interest during spin

### Slot Symbols (10 Magic-Themed Symbols)

| Symbol | Colors | Pattern | Description |
|--------|--------|---------|-------------|
| **fire** | Red/Orange | Flame | Burning flame symbol |
| **ice** | Blue/Cyan | Crystal | Crystalline ice symbol |
| **lightning** | Gold/Yellow | Bolt | Lightning bolt |
| **star** | Purple | Star | Magical star |
| **gem** | Cyan | Diamond | Precious gem |
| **skull** | Green | Skull | Necromantic skull |
| **dragon** | Orange/Red | Dragon | Dragon head |
| **rune** | Purple | Rune | Arcane rune symbol |
| **coin** | Gold | Coin | Gold coin |
| **crown** | Gold/Orange | Crown | Royal crown |

Each symbol:
- **Size**: 64×64 pixels
- **Style**: High-contrast, readable at small sizes
- **Effects**: Glow effects for magical appearance
- **Background**: Circular/hexagonal background

### Slot Machine Panel
- **File**: `slot_machine_panel.png`
- **Size**: 300×400 pixels
- **Description**: Complete slot machine UI panel
- **Features**:
  - Gold/purple casino theme
  - 3 reel slots side by side
  - Decorative top section
  - Control panel with spin button
  - Corner decorations
  - Runic side patterns

### Win Indicator
- **File**: `slot_win_indicator.png`
- **Size**: 200×200 pixels
- **Description**: Glowing star burst for win effects
- **Features**:
  - Gold glow rings
  - Star burst pattern
  - High visibility
  - Glow effects

### Loss Indicator
- **File**: `slot_loss_indicator.png`
- **Size**: 200×200 pixels
- **Description**: Subtle indicator for losses
- **Features**:
  - Gray, non-intrusive
  - Simple design
  - Clear but not negative

## Output Location

All assets are saved to:
```
Assets/Resources/SlotMachine/UI/
```

## Visual Design

### Color Scheme
- **Frame**: Gold (#d4af37) with highlights
- **Background**: Dark purple/black for contrast
- **Accents**: Purple/magenta for magical theme
- **Symbols**: System-appropriate colors per symbol type

### Style Features
- **3D Effects**: Beveled frames, shadows, highlights
- **Glow Effects**: Magical glow on symbols and frames
- **Decorative Elements**: Corner decorations, runic patterns
- **Readability**: High contrast for clear visibility

## Usage in Unity

1. **Import Assets**: Place generated files in `Assets/Resources/SlotMachine/UI/`
2. **Create Reel Prefabs**: Use `slot_reel_frame.png` as container, place symbols inside
3. **Animate Reels**: Use `slot_reel_background.png` for spinning effect
4. **UI Integration**: Use `slot_machine_panel.png` as main UI background
5. **Effects**: Use win/loss indicators for feedback

## Symbol Usage

Each symbol can represent different outcomes:
- **Common**: fire, ice, lightning (lower value)
- **Uncommon**: star, gem (medium value)
- **Rare**: skull, dragon, rune (higher value)
- **Epic**: coin, crown (highest value)

## Customization

### Adding New Symbols

Edit the `$script:SlotSymbols` array in the script to add new symbol types.

### Changing Colors

Modify color arrays in symbol definitions to match your theme.

### Adjusting Sizes

Edit size constants in generation functions to change dimensions.

## Requirements

- **Python 3.x** with PIL/Pillow
- **Ollama** (optional, for AI specifications)
- **PowerShell 5.1+**

## See Also

- `MagicUIElementGenerator.ps1` - For general magic-themed UI
- `CustomRaceClassCreatorAssetGenerator.ps1` - For textures and other assets
- SlotMagic system documentation

---

**Version**: 1.0  
**Focus**: High-quality slot machine assets for SlotMagic system

