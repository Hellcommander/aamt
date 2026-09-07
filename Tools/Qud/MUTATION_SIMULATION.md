# Mutation Architecture Simulation

The Qud Mod Fixer now **simulates how mutations actually work** using the source code index, providing architecturally-correct fixes.

## How It Works

### 1. **Architecture Analysis**
Analyzes the mutation file structure:
- Detects base class (`BaseMutation`, etc.)
- Identifies activated abilities
- Checks lifecycle methods (`Mutate`, `Unmutate`)
- Finds cooldown patterns

### 2. **Source Code Retrieval (RAG)**
Queries the source code index for similar mutations:
```
Query: "BaseMutation AddMyActivatedAbility ApplyCooldown Mutate Unmutate"
```
Retrieves actual game mutations as examples:
- How cooldowns are properly applied
- Correct lifecycle patterns
- Proper cleanup in Unmutate()

### 3. **Lifecycle Simulation**
Simulates what happens at runtime:
- **Mutate Phase**: What abilities are added? Do they have cooldowns?
- **Runtime Phase**: Can abilities be spammed? Any null references?
- **Unmutate Phase**: Are abilities properly removed? Memory leaks?

### 4. **Issue Prediction**
Predicts runtime issues before they happen:
- **Game-Breaking**: Infinite ability spam, crashes
- **Bugs**: Abilities persisting, UI clutter
- **Balance**: Missing energy costs

## Example Output

```
## MUTATION ARCHITECTURE ANALYSIS

Base Class: BaseMutation
Lifecycle Methods: Mutate, Unmutate

Detected Abilities:
  - Space-Time Vortex (Aggressive) (AggressiveAbilityID) - ✗ MISSING COOLDOWN
  - Space-Time Vortex (Defensive) (DefensiveAbilityID) - ✗ MISSING COOLDOWN

## MUTATION LIFECYCLE SIMULATION

Runtime Behavior Prediction:
  Abilities Added: Space-Time Vortex (Aggressive), Space-Time Vortex (Defensive)
  Abilities Removed: None

Predicted Runtime Issues:
  [GAME-BREAKING] Ability 'Space-Time Vortex (Aggressive)' can be spammed infinitely (no cooldown)
  [GAME-BREAKING] Ability 'Space-Time Vortex (Defensive)' can be spammed infinitely (no cooldown)
  [BUG] Ability 'Space-Time Vortex (Aggressive)' persists after mutation removed
  [BUG] Ability 'Space-Time Vortex (Defensive)' persists after mutation removed

## CORRECT PATTERNS FROM GAME SOURCE CODE

Retrieved 5 similar mutations from source:

### Example 1 (XRL.World.Parts.Mutation.Teleportation.cs) - Similarity: 0.89
```csharp
public override bool Mutate(GameObject GO, int Level)
{
    TeleportAbilityID = AddMyActivatedAbility(
        "Teleportation",
        nameof(CommandTeleport),
        "Mental Mutation"
    );
    return base.Mutate(GO, Level);
}

public bool CommandTeleport(GameObject GO)
{
    // ... teleport logic ...
    
    // Apply cooldown based on level
    ApplyCooldown(GO, TeleportAbilityID, GetCooldownForLevel(Level));
    
    return true;
}

private int GetCooldownForLevel(int level)
{
    return Math.Max(10, 50 - (level * 2));
}

public override bool Unmutate(GameObject GO)
{
    RemoveMyActivatedAbility(ref TeleportAbilityID);
    return base.Unmutate(GO);
}
```

## CORRECT COOLDOWN PATTERNS (from source)
  ApplyCooldown(GO, AbilityID, GetCooldownForLevel(Level))
  LinkCooldowns(GO, PrimaryID, SecondaryID, cooldownTurns)
```

## Benefits

### **Architecturally Correct Fixes**
- Matches game's actual mutation patterns
- Uses same cooldown formulas as base game
- Follows proper lifecycle conventions

### **Fewer Bugs**
- Simulates runtime behavior before fixing
- Catches issues that pattern matching misses
- Predicts side effects

### **Better Learning**
- AI sees how real mutations work
- Learns from 300+ game mutations
- Applies consistent patterns

### **Faster Development**
- No need to study source code manually
- AI extracts best practices automatically
- Generates production-ready code

## Usage

### Natural Language Mode
```bash
python qud_mod_fixer.py "Space Time Vortex" --issue "ability has no cooldown"
```

The fixer will:
1. Analyze your mutation structure
2. Retrieve similar mutations from source
3. Simulate lifecycle to find issues
4. Generate fix matching game architecture

### Standard Mode
```bash
python qud_mod_fixer.py "My Mutation Mod"
```

Automatically analyzes mutations and simulates behavior.

## Technical Details

### Architecture Patterns Detected
- `BaseMutation` inheritance
- `AddMyActivatedAbility()` calls
- `ApplyCooldown()` / `LinkCooldowns()`
- `Mutate()` / `Unmutate()` lifecycle
- `RemoveMyActivatedAbility()` cleanup

### Simulation Phases
1. **Static Analysis**: Parse code structure
2. **RAG Retrieval**: Get source examples
3. **Pattern Extraction**: Learn correct patterns
4. **Lifecycle Simulation**: Predict runtime
5. **Fix Generation**: Apply learned patterns

### Source Code Context
The RAG system retrieves:
- Similar mutations by functionality
- Cooldown management patterns
- Proper cleanup examples
- Error handling patterns
- Level scaling formulas

## Comparison: Before vs After

### Before (Pattern Matching Only)
```csharp
// AI doesn't understand mutation architecture
// Just adds basic cooldown without proper integration
ApplyCooldown(GO, someAbilityID, 100);  // Magic number
```

### After (Architecture-Aware)
```csharp
// AI understands mutation lifecycle from source
// Implements proper level-based cooldown
private int GetCooldownForLevel(int level)
{
    int baseCooldown = 100; // Balanced with similar mutations
    int reduction = (level - 1) * 5; // Source pattern
    return Math.Max(20, baseCooldown - reduction);
}

public bool CommandAbility(GameObject GO)
{
    // ... ability logic ...
    
    // Apply cooldown like real mutations do
    ApplyCooldown(GO, AbilityID, GetCooldownForLevel(Level));
    return true;
}

public override bool Unmutate(GameObject GO)
{
    // Proper cleanup following source patterns
    RemoveMyActivatedAbility(ref AbilityID);
    return base.Unmutate(GO);
}
```

## Future Enhancements

Planned improvements:
- Stat requirement simulation
- Energy cost balancing
- Multi-mutation interaction analysis
- Save/load state validation
- Multiplayer sync checking
- Performance impact prediction

