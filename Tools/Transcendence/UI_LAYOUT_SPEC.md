# Shield and Armor UI Layout Specification

## Layout Overview

```
┌─────────────────────────────────────────────────────────┐
│  Shield & Armor Status Panel                            │
├──────────────────┬──────────────────────────────────────┤
│                  │  Armor Plating Map                    │
│  Ship Silhouette │  ┌─────────────────────────────────┐ │
│  with Shield     │  │ Front:  [████████░░] 80% (40/50)│ │
│  Ring Overlay    │  │ Left:   [████░░░░░░] 40% (20/50)│ │
│                  │  │ Right:  [██████████] 100% (50/50)│ │
│  [Shield Ring]   │  │ Rear:   [███████░░░] 70% (35/50)│ │
│                  │  └─────────────────────────────────┘ │
│                  │                                       │
│  Shield: 80/120  │  Quick Actions                       │
│  [████████░░]    │  [Toggle Shield] [Mode] [Repair]     │
│  66% Recharging  │                                       │
└──────────────────┴──────────────────────────────────────┘
```

## UI Elements

### 1. Shield Ring (Circular Meter)

**Location**: Overlay on ship silhouette (left side)

**Visual Design**:
- Circular ring around ship icon
- Color gradient from `baseColor` to `damagedColor` based on strength
- Animated pulse when recharging
- Hit flash ripple effect at hit position

**Data Binding**:
```json
{
  "current": 80,
  "max": 120,
  "percentage": 66.67,
  "color": "#66ccff",
  "damagedColor": "#ff6666",
  "visualIntensity": 0.67,
  "hitFlashIntensity": 0.0,
  "lastHitPosition": {"x": 1.2, "y": 0.5, "z": 0.0}
}
```

**Implementation**:
- SVG path or canvas-based ring
- Gradient stops: `baseColor` at 100%, `damagedColor` at 0%
- Arc length = `percentage * 360 degrees`
- Hit flash: white pulse at angle corresponding to `lastHitPosition`

### 2. Armor Plating Map

**Location**: Right side, vertical list

**Visual Design**:
- List of plating segments
- Each segment shows:
  - Slot name (Front, Left, Right, Rear, Top, Bottom)
  - Health bar (horizontal bar with color coding)
  - Numeric readout (current/max HP and percentage)
  - Visual damage indicators (scorch marks, dents, cracks)

**Data Binding**:
```json
{
  "plating": [
    {
      "slot": "front",
      "hp": 40,
      "maxHp": 50,
      "percentage": 80.0,
      "visualDamage": {
        "scorchMarks": true,
        "dents": false,
        "cracks": false
      }
    }
  ]
}
```

**Color Coding**:
- Green: 75-100% health
- Yellow: 50-75% health
- Orange: 25-50% health
- Red: 0-25% health

### 3. Numeric Readouts

**Location**: Below shield ring

**Display**:
- Current/Max shield: `80/120`
- Shield percentage: `66%`
- Recharge rate: `6.0 HP/s` (if recharging)
- State indicator: `Recharging`, `Active`, `Broken`, `Overloaded`

### 4. State Icons

**Icons**:
- ✅ Active (green checkmark)
- 🔄 Recharging (spinning arrow)
- ❌ Broken (red X)
- ⚠️ Overloaded (yellow warning)
- 🔋 Low Power (battery icon)

### 5. Interactive Controls

**Location**: Bottom of panel

**Buttons**:
- **Toggle Shield**: On/Off toggle
- **Mode Selector**: Dropdown or buttons for `balanced`, `offense`, `defense`
- **Repair**: Quick repair button (if repair system available)
- **Power Allocation**: Sliders for shield/plating power distribution

## UX Details

### Hit Feedback

1. **Hit Flash on Ring**:
   - White flash at hit angle
   - Ripple animation outward
   - Duration: `hitFlashDuration` (default 0.12s)

2. **Armor Damage Overlays**:
   - Scorch marks: Red/brown overlay on damaged slots
   - Dents: Dark shadow overlay
   - Cracks: Thin line overlay

3. **Sound Feedback**:
   - Shield hit sound
   - Shield break sound
   - Low shield warning
   - Recharge start sound

### Tooltips

**Shield Ring Tooltip**:
```
Shield: 80/120 (66%)
Recharge Rate: 6.0 HP/s
State: Recharging
Mode: Balanced
```

**Armor Slot Tooltip**:
```
Front Plating: 40/50 HP (80%)
Damage Reduction:
  - Kinetic: 20%
  - Laser: 10%
  - Plasma: 15%
Status: Minor scorch marks
```

### Responsive Design

- **Desktop**: Full panel with all elements visible
- **Tablet**: Compact layout, collapsible sections
- **Mobile**: Minimal HUD, expandable details on tap

## Implementation Examples

### HTML/CSS/JavaScript

```html
<div class="shield-armor-panel">
  <div class="ship-silhouette">
    <svg class="shield-ring" viewBox="0 0 200 200">
      <circle class="shield-ring-bg" cx="100" cy="100" r="90"/>
      <path class="shield-ring-fill" d="M 100,10 A 90,90 0 1,1 100,10"/>
    </svg>
  </div>
  
  <div class="armor-plating">
    <div class="plating-slot" data-slot="front">
      <span class="slot-name">Front</span>
      <div class="health-bar">
        <div class="health-fill" style="width: 80%"></div>
      </div>
      <span class="health-text">40/50 (80%)</span>
    </div>
  </div>
  
  <div class="controls">
    <button class="toggle-shield">Toggle Shield</button>
    <select class="mode-selector">
      <option value="balanced">Balanced</option>
      <option value="offense">Offense</option>
      <option value="defense">Defense</option>
    </select>
  </div>
</div>
```

### Unity UI (C#)

```csharp
public class ShieldArmorUI : MonoBehaviour {
    public Image shieldRing;
    public Text shieldText;
    public List<ArmorSlotUI> armorSlots;
    
    public void UpdateShield(ShieldInstance shield) {
        float percentage = shield.currentStrength / shield.maxStrength;
        shieldRing.fillAmount = percentage;
        shieldText.text = $"{shield.currentStrength:F0}/{shield.maxStrength:F0}";
        
        // Update color based on percentage
        shieldRing.color = Color.Lerp(damagedColor, baseColor, percentage);
    }
}
```

## Animation Guidelines

### Shield Ring
- Smooth fill animation when shield changes
- Pulse animation when recharging (subtle)
- Hit flash: quick white flash, fade out

### Armor Bars
- Smooth width transitions
- Color transitions based on health percentage
- Damage overlay fade-in on hit

### State Icons
- Fade in/out on state change
- Spin animation for recharging icon
- Pulse animation for low/warning states

## Accessibility

- High contrast mode support
- Colorblind-friendly color schemes
- Screen reader support for numeric values
- Keyboard navigation for controls
- Configurable UI scale

