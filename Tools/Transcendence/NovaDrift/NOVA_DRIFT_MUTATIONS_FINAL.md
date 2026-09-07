# Nova Drift-Inspired Mutations - Final Implementation

## Added Mutations (4 Total)

### 1. Kinetic Blast (Corrupt)
**Inspired by**: Nova Drift Blaster Mutation concept

**Mechanics**:
- Charges automatically while moving
- Charge rate scales with movement speed
- Fires manually or on head-on collision
- Collision damage scales with crash damage modifiers
- Launches enemies that can collide with others for chain damage

**Balance**:
- Damage: +30% (tuned down from +50%)
- Range: -50% (close-range only)
- Fire Rate: -40% (slow charging)
- Instability: 12

**Synergy**: Lightweight Barrel + Overclock (charge rate scales with speed)

**Playstyle**: High-risk, high-reward close-range build. Rewards aggressive movement.

### 2. Sticky Bomb (Corrupt)
**Inspired by**: Nova Drift Grenade Mutation concept

**Mechanics**:
- Attaches to enemies instead of exploding immediately
- Explodes after short fuse
- Triggering one explodes all nearby Sticky Bombs
- Stacking increases fuse times of attached bombs
- Chain reactions increase damage and radius per reaction
- Higher fire rate but no cluster explosives

**Balance**:
- Fire Rate: +20% (tuned down from +30%)
- Damage: -10% (sidegrade, not buff)
- Range: -20%
- Accuracy: -15%
- Instability: 10

**Synergy**: Entropy Bloom (triggers shards on explosion)

**Playstyle**: Area control and chain reaction specialist. Rewards stacking bombs.

### 3. Harpoon (Major)
**Inspired by**: Nova Drift Dart Mutation concept

**Mechanics**:
- Projectiles lodge in targets
- Creates searing hot tether to shooter
- Deals burn damage over time via tether
- Higher impact damage than base weapon
- Much slower fire rate

**Balance**:
- Damage: +40%
- Fire Rate: -40%
- Range: -20%
- Proc: 100% burn chance

**Synergy**: Burning Rounds (tether burn damage +50%)

**Playstyle**: DoT-focused build. Rewards sustained fire on single targets.

### 4. Greatsword (Corrupt)
**Inspired by**: Nova Drift Swords Mutation concept

**Mechanics**:
- Deploys one massive sword instead of pair
- Indestructible (unlike base Swords)
- Deals more damage the more missing hull you have (up to +100% at 0% hull)
- Provides armor and damage reduction
- Cannot create Spark Projectiles

**Balance**:
- Base Damage: +50% (tuned down from +80%)
- Max Damage: +150% at 0% hull (scales with missing hull)
- Fire Rate: -60%
- Projectile Speed: -50%
- Range: -20%
- Instability: 8

**Synergy**: Condensed Rounds (additional damage scaling)

**Playstyle**: Berserker high-risk build. Rewards low-hull aggressive play.

## Balance Tuning

### Initial Issues
- Sticky Bomb created 8 dominant combinations (+35% to +57% DPS)
- Kinetic Blast was too powerful (+50% damage)
- Greatsword base damage too high (+80%)

### Tuning Applied
1. **Sticky Bomb**:
   - Removed damage multiplier (+25% → removed)
   - Added damage penalty (-10%)
   - Reduced fire rate bonus (+30% → +20%)
   - Increased penalties (range -20%, accuracy -15%)
   - Added conflict with Overclock

2. **Kinetic Blast**:
   - Reduced damage (+50% → +30%)
   - Increased penalties (range -50%, fire rate -40%)

3. **Greatsword**:
   - Reduced base damage (+80% → +50%)
   - Increased penalties (fire rate -60%, speed -50%)
   - Added range penalty (-20%)

## Final Status

### Total Mutations: 18
- Minor: 6
- Major: 6 (was 5, added Harpoon)
- Corrupt: 6 (was 3, added Kinetic Blast, Sticky Bomb, Greatsword)

### Balance Status
- ⚠️ Testing in progress
- Sticky Bomb needs final balance verification
- Other mutations appear balanced

### Interesting Features
- ✅ Behavior-changing mutations
- ✅ Unique mechanics (charging, tethers, stacking, hull-scaling)
- ✅ Synergies with existing system
- ✅ Sidegrade focus maintained

## Design Notes

### Behavior Changes
All new mutations fundamentally change weapon behavior:
- **Kinetic Blast**: Movement-based charging system
- **Sticky Bomb**: Attachment and chain reaction mechanics
- **Harpoon**: Tether-based DoT system
- **Greatsword**: Hull-scaling berserker mechanics

### Sidegrade Philosophy
- Mutations change gameplay, not just power
- Meaningful tradeoffs for all mutations
- No pure power increases
- Interesting playstyles enabled

### Integration
- New mutations work with existing synergy system
- Conflicts prevent overpowered combinations
- Balance tools detect issues automatically

The system now includes these Nova Drift-inspired experimental mutations that create entirely new playstyles while maintaining sidegrade balance!

