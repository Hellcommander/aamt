# Cockpit Requirements for All Mech Forms

## Overview
All mech forms are **piloted vehicles**, not player transformations. The player sits inside a visible cockpit that must be rendered with alpha channel transparency.

## Requirements

### 1. Cockpit Visibility
- **Player must be visible** inside the cockpit through alpha channel transparency
- Cockpit glass uses alpha channel (typically 0.3-0.5 transparency)
- Cockpit interior area is fully transparent (alpha = 1.0) for player visibility

### 2. Cockpit Components (Per Form)
- **Cockpit Frame**: Opaque frame around the glass (form-specific style)
- **Cockpit Glass**: Transparent with tint, alpha channel enabled
- **Cockpit Interior**: Fully transparent area where player is visible

### 3. Animation Requirements
- **All animation frames** (136 per form) must include the cockpit
- Cockpit position and size remain consistent across all frames
- Alpha channel must be preserved in all animation sprites

### 4. Asset Generation
- Use RGBA format (not RGB) to preserve alpha channel
- Cockpit glass layer uses alpha transparency
- Player visibility area uses full transparency
- Frame is opaque (alpha = 1.0)

## Cockpit Specifications

Each form has cockpit specs in its JSON:
```json
"cockpit": {
  "enabled": true,
  "position": [0, 0.5],        // Relative to mech center
  "size": [30, 30],            // Width x Height in pixels
  "shape": "circular",         // Form-specific shape
  "alphaChannel": true,         // REQUIRED
  "transparencyLevel": 0.3,    // Glass transparency
  "playerVisible": true,        // REQUIRED
  "playerScale": 0.8,          // Player size inside cockpit
  "playerOffset": [0, -0.2]    // Player position offset
}
```

## Generation Scripts

- `GenerateMechCockpitAssets.bat` - Generates cockpit frames, glass, and interiors
- `GenerateMechFormAnimations.bat` - Includes cockpit in all animation frames
- `GenerateMechVariantSet.bat` - Includes cockpit in variant sets

## Visual Example

```
┌─────────────────┐
│  Mech Body      │
│  ┌───────────┐  │
│  │  Frame    │  │  ← Opaque frame
│  │ ┌───────┐ │  │
│  │ │ Glass │ │  │  ← Alpha transparent (player visible)
│  │ │[PLAYER]│ │  │  ← Player visible here
│  │ └───────┘ │  │
│  └───────────┘  │
│  Mech Body      │
└─────────────────┘
```

## Notes

- Mechs are **vehicles**, not player shapeshifting
- Player sits inside cockpit, visible through glass
- All forms must maintain cockpit visibility across all animations
- Variant sets share cockpit style but maintain player visibility
