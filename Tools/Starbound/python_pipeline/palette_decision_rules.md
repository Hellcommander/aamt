# Palette Decision Rules for AI-Driven Frame Generation

## Overview

This document defines the rules and prompts for AI-driven color palette selection when generating OpenStarbound assets. The AI uses these rules to ensure consistent, high-quality color choices.

## Role-Based Palette Mapping

### Assault Mechs
**Role**: Aggressive, combat-focused
**Default Palette**:
- Primary: Warm reds/oranges (200, 50, 50) - aggression
- Secondary: Bright yellows/golds (255, 200, 100) - energy
- Accent: Dark grays (100, 100, 100) - metal
- Highlight: Bright whites (255, 255, 255) - shine
- Damage: Dark reds (150, 25, 25) - wear

**AI Prompt Template**:
```
Generate a 5-color palette for an assault mech segment. Colors should convey:
- Aggression and power (warm reds/oranges)
- High energy (bright yellows/golds)
- Metallic structure (dark grays)
- Shine and polish (bright whites)
- Battle damage (dark reds)

Return RGB values only: [[r1,g1,b1], [r2,g2,b2], ...]
```

### Support Mechs
**Role**: Defensive, utility-focused
**Default Palette**:
- Primary: Cool blues (50, 150, 200) - stability
- Secondary: Light blues (100, 200, 255) - clarity
- Accent: Soft purples (150, 150, 200) - technology
- Highlight: Light cyans (200, 220, 255) - efficiency
- Damage: Dark blues (50, 100, 150) - wear

**AI Prompt Template**:
```
Generate a 5-color palette for a support mech segment. Colors should convey:
- Stability and reliability (cool blues)
- Clarity and precision (light blues)
- Advanced technology (soft purples)
- Efficiency (light cyans)
- Wear and use (dark blues)

Return RGB values only: [[r1,g1,b1], [r2,g2,b2], ...]
```

### Horror Mechs
**Role**: Dark, menacing, corrupted
**Default Palette**:
- Primary: Dark reds (80, 20, 20) - blood/danger
- Secondary: Deep maroons (120, 40, 40) - decay
- Accent: Near-black (40, 40, 40) - shadow
- Highlight: Bright red (200, 0, 0) - threat
- Damage: Dark grays (60, 60, 80) - corruption

**AI Prompt Template**:
```
Generate a 5-color palette for a horror mech segment. Colors should convey:
- Danger and blood (dark reds)
- Decay and rot (deep maroons)
- Shadow and darkness (near-black)
- Threat and warning (bright red)
- Corruption (dark grays)

Return RGB values only: [[r1,g1,b1], [r2,g2,b2], ...]
```

### Magitech Mechs
**Role**: Mystical, arcane, magical
**Default Palette**:
- Primary: Magical blues (100, 150, 255) - arcane energy
- Secondary: Mystical purples (200, 100, 255) - magic
- Accent: Ethereal cyans (150, 200, 255) - otherworldly
- Highlight: Bright golds (255, 200, 100) - enchantment
- Damage: Dark purples (100, 100, 200) - fading magic

**AI Prompt Template**:
```
Generate a 5-color palette for a magitech mech segment. Colors should convey:
- Arcane energy (magical blues)
- Mystical power (purples)
- Otherworldly presence (ethereal cyans)
- Enchantment (bright golds)
- Fading magic (dark purples)

Return RGB values only: [[r1,g1,b1], [r2,g2,b2], ...]
```

## Color Hint Processing

When user provides color hints, the AI should:

1. **Extract Keywords**: Parse hints for color names, materials, emotions
2. **Map to Palette Roles**: Assign hints to primary, secondary, accent, highlight, damage
3. **Ensure Contrast**: Verify contrast ratios for readability (WCAG AA minimum)
4. **Maintain Consistency**: Use similar hues across related assets

### Example Hint Processing

**Input**: `["crimson", "brass", "dark slate"]`

**Processing**:
- "crimson" → Primary (warm red)
- "brass" → Secondary (metallic gold)
- "dark slate" → Accent (dark gray-blue)

**Output Palette**:
```json
[
  [220, 20, 60],   // Crimson (primary)
  [181, 166, 66],  // Brass (secondary)
  [47, 79, 79],    // Dark slate (accent)
  [255, 255, 255], // White (highlight)
  [139, 0, 0]      // Dark red (damage)
]
```

## Quality Level Considerations

### Pixel Art (16x16, 32x32)
- **Limited Colors**: Use 3-5 colors maximum
- **High Contrast**: Ensure colors are distinct at small sizes
- **Avoid Gradients**: Use flat colors only
- **Dithering**: Optional for smooth transitions

### High-Res (64x64, 128x128)
- **More Colors**: Can use 5-8 colors
- **Subtle Gradients**: Allow for smooth color transitions
- **Detail Colors**: Additional colors for fine details
- **Anti-aliasing**: Smooth edges acceptable

### MS-Designer Level (256x256+)
- **Full Palette**: 8-16 colors allowed
- **Complex Gradients**: Multi-stop gradients
- **Photorealistic**: Can match reference images
- **Layered Rendering**: Multiple passes for depth

## Contrast Requirements

For UI visibility and readability:

- **Primary vs Background**: Minimum 4.5:1 contrast ratio
- **Text on Icons**: Minimum 7:1 contrast ratio
- **Interactive Elements**: High contrast for visibility
- **Damage States**: Clearly distinguishable from normal state

## Consistency Rules

1. **Related Assets**: Use same base palette with variations
2. **Faction Colors**: Maintain faction identity across assets
3. **Material Colors**: Consistent metal/energy/material colors
4. **Animation Frames**: Smooth color transitions across frames

## Fallback Behavior

If AI palette generation fails:

1. Use role-based default palette
2. Log warning for manual review
3. Continue generation with fallback palette
4. Mark output for quality review

## Integration with PowerShell Pipeline

The PowerShell scripts can call the Python orchestrator:

```powershell
# Generate palette and frames
python frame_generator_orchestrator.py `
    --job "example_job.json" `
    --output "assets\animations" `
    --ollama-url "http://localhost:11434"
```

The orchestrator will:
1. Generate palette using AI or Colormind
2. Create frames with proper colors
3. Pack into atlas
4. Generate .frames metadata
5. Validate output
