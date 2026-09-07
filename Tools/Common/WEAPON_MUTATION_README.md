# Weapon Mutation System

## Overview

A Nova Drift-inspired weapon mutation system for Transcendence that allows weapons to have up to **2 mutations** simultaneously. Mutations are **sidegrades** that add variation and change gameplay, not just power creep.

Inspired by [Nova Drift's mutation system](https://blog.novadrift.io/nova-drifts-demo/), this implementation focuses on:
- **Sidegrade Design**: Mutations change how weapons play, not just increase DPS
- **2-Slot Limit**: Maximum of 2 mutations per weapon
- **Deterministic Merging**: Clear rules for how mutations combine
- **Three Tiers**: Minor, Major, and Corrupt mutations
- **Instability System**: Corrupt mutations add risk/reward

## Quick Start

### Generate Mutations

```powershell
# Export all mutations to XML
python transcendence_weapon_mutation_exporter.py --registry weapon_mutation_example.json --output-dir "Output/Mutations" --combined

# Export specific mutation
python transcendence_weapon_mutation_exporter.py --registry weapon_mutation_example.json --mutation-id "vortex_orb" --output-dir "Output/Mutations"
```

### Use Mutation System

```python
from weapon_mutation_system import WeaponMutationSystem

# Load system
system = WeaponMutationSystem("weapon_mutation_example.json")

# Apply mutations to a weapon
mutations = []
mutations, effects, instability = system.apply_mutation(mutations, "lightweight_barrel")
mutations, effects, instability = system.apply_mutation(mutations, "condensed_rounds")

# Get preview
preview = system.get_mutation_preview(mutations, "overclock")
```

## Mutation Tiers

### Minor (Slot Cost: 1)
- **Power Impact**: Small buff or tweak (~5-15%)
- **Variability**: Low, predictable
- **Risk**: None or tiny
- **Examples**: Lightweight Barrel, Condensed Rounds, Burning Rounds

### Major (Slot Cost: 1-2)
- **Power Impact**: Noticeable change (~15-40%) or new behavior
- **Variability**: Medium, can change playstyle
- **Risk**: Moderate (slot cost, cooldown)
- **Examples**: Shred Mode, Overclock, Pulsewave, Ricochet Rounds

### Corrupt (Slot Cost: 2)
- **Power Impact**: Big, game-changing effect
- **Variability**: High, emergent interactions
- **Risk**: High (instability, side effects)
- **Examples**: Phase Rounds, Entropy Bloom, Vortex Orb

## Core Mechanics

### Two-Slot Limit
Each weapon can hold up to **2 mutations**. Acquiring a third mutation forces a choice:
- **Replace**: Lower tier mutation is replaced
- **Decline**: Keep current mutations

### Sidegrade Design
Every mutation includes **tradeoffs**:
- **Throughput ↔ Burst**: +single-shot damage; -fire rate
- **Range ↔ Spread**: +range; -accuracy
- **Utility ↔ Raw Damage**: Add proc (slow, stun); -base damage

### Diminishing Returns
When stacking multiplicative buffs, apply soft cap:
```
effectiveBonus = 1 + rawBonus / (1 + k * rawBonus)
```
Where `k` (0.5-1.5) controls how quickly returns taper.

### Conflict Resolution
If two mutations conflict:
- **Higher tier wins**: Corrupt > Major > Minor
- **Deterministic**: Same tier = keep first mutation
- **Merge rules**: Some conflicts produce predictable hybrids

### Instability System
Corrupt mutations add **instability** that causes:
- Weapon jam chance
- Self-damage ticks
- Overheating
- Visual side effects

Instability scales with mutation count and tier.

## Mutation Examples

### Minor Mutations

**Lightweight Barrel**
- +10% projectile speed
- -5% damage
- Synergizes with: Condensed Rounds, Overclock

**Condensed Rounds**
- +8% damage
- +10% recoil (affects accuracy)
- Synergizes with: Lightweight Barrel, Shred Mode

### Major Mutations

**Shred Mode**
- Bullets split into 3 on impact
- -25% range
- Conflicts with: Phase Rounds

**Overclock**
- +30% fire rate
- +15% heat buildup
- Synergizes with: Lightweight Barrel, Shred Mode

**Pulsewave**
- Fires single projectile that creates 7-10 pulses
- -50% damage
- Conflicts with: Shred Mode

### Corrupt Mutations

**Phase Rounds**
- Shots phase through shields
- -20% hull damage
- 5% misfire chance
- Instability: 5
- Conflicts with: Shred Mode, Ricochet Rounds

**Entropy Bloom**
- On kill, spawns volatile shard
- 10% chance to damage player
- Instability: 10
- Synergizes with: Shred Mode

**Vortex Orb**
- Creates slow-moving orb that deals burn damage
- Homing submunitions feed the orb
- -30% damage, -50% projectile speed
- Instability: 8
- Conflicts with: Overclock, Shred Mode

## Registry Structure

```json
{
  "version": "1.0.0",
  "mutations": [
    {
      "id": "mutation_id",
      "tier": "minor|major|corrupt",
      "name": "Display Name",
      "description": "Tooltip description",
      "slotCost": 1,
      "instability": 0,
      "effects": {
        "damageMultiplier": 1.15,
        "fireRateMultiplier": 1.30
      },
      "tradeoffs": {
        "damagePenalty": 0.05,
        "heatBuildUp": 0.15
      },
      "compatibility": {
        "synergizesWith": ["other_mutation_id"],
        "conflictsWith": ["conflicting_id"],
        "tags": ["damage", "speed"]
      },
      "weaponTypes": ["all"],
      "rarity": 0.3,
      "export": {
        "unid": "&mutMutationId;"
      }
    }
  ]
}
```

## Merging Rules

### Multipliers
- Combined with diminishing returns
- Example: +10% and +8% damage → ~+17% (not +18%)

### Additive Effects
- Piercing, split count: Added together
- Example: +1 piercing + 2 piercing = 3 total piercing

### Boolean Effects
- Homing: OR logic (either mutation enables it)
- Example: Either mutation enables homing

### Proc Effects
- Proc chance: Combined as independent events
- Formula: `1 - (1-p1) * (1-p2)`
- Proc effect: Higher tier wins

### Behavior Changes
- Higher tier mutation's behavior wins
- Same tier: First mutation's behavior

### Tradeoffs
- Penalties are additive
- Example: -5% damage + -8% damage = -13% damage

## Balancing Guidelines

### Power Caps
- **Two Minor**: Max ~+20-25% effective bonus
- **Two Major**: Max ~+30-40% with clear downsides
- **Corrupt Pair**: High power but significant instability

### Readability
- Clear tooltips for all mutations
- Preview modal shows combined effects
- Visual indicators for active mutations

### Testing Checklist
- [ ] Readability: Players understand mutations
- [ ] Sidegrade: Each mutation has meaningful downside
- [ ] Combo Test: No pair outperforms baseline by >30%
- [ ] Fun Test: Players choose for variety, not power
- [ ] Edge Cases: No infinite loops or breaks

## UI Elements

### Mutation Slots
- Two small badges on weapon UI
- Show active mutations and tier
- Hover shows full tooltip

### Preview Modal
- Shows combined weapon stats
- Lists tradeoffs clearly
- Displays instability if applicable

### Acquisition Flow
- Mutations appear as drops or shop items
- "Apply to which weapon?" prompt
- One-time reroll option (cost)

### Mutation Removal
- Costly reforge option
- Vendor service
- Reduces frustration from bad choices

## Performance

### Recommended Limits
- **Max Mutations per Weapon**: 2 (hard limit)
- **Mutation Pool Size**: 30-50 mutations
- **Active Mutations per Player**: 4-6 (2-3 weapons)

### Optimization
- Cache mutation combinations
- Pre-calculate common merges
- Pool mutation objects

## Integration with Transcendence

### XML Structure
Mutations export as `ItemType` elements with:
- UNID for identification
- Properties for effects and tradeoffs
- Compatibility tags
- Weapon type restrictions

### Runtime Application
- Mutations apply to weapon stats
- Effects modify damage, speed, behavior
- Tradeoffs apply penalties
- Instability triggers side effects

## Related Systems

- **Nova Drift FX**: For mutation visual effects
- **Weapon System**: Base weapon definitions
- **Balance Tools**: For testing and tuning

## References

- [Nova Drift Blog - Demo Release](https://blog.novadrift.io/nova-drifts-demo/)
- Nova Drift's mutation system for inspiration
- Sidegrade design principles

## Status

✅ **Core System**: Complete
✅ **Registry Schema**: Complete
✅ **Mutation Pool**: 14 example mutations
✅ **Merging Logic**: Deterministic rules implemented
✅ **XML Exporter**: Complete
⚠️ **UI Integration**: Pending (requires Transcendence UI work)
⚠️ **Balance Testing**: Pending (requires playtesting)

The mutation system is **production-ready** for integration into Transcendence. All core mechanics are implemented and tested.

