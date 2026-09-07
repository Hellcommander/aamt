# Enhanced Activated Ability Issue Detection

The Qud Mod Fixer now includes **advanced detection** for common activated ability issues that cause gameplay problems.

## New Detection Capabilities

### 1. **Missing Cooldowns** (HIGH SEVERITY)
**Problem:** Activated abilities without cooldowns can be spammed infinitely.

**Detection:**
- Scans for `AddMyActivatedAbility()` calls
- Checks if the ability variable is used with any cooldown method
- Looks for: `ApplyCooldown`, `LinkCooldowns`, `SetCooldown`

**Example Issue:**
```csharp
// BAD - No cooldown!
private Guid VortexAbilityID = Guid.Empty;

public override bool Mutate(GameObject GO, int Level)
{
    VortexAbilityID = AddMyActivatedAbility(
        "Space-Time Vortex",
        nameof(CommandSpaceTimeVortex),
        "Mental Mutation"
    );
    return base.Mutate(GO, Level);
}

public bool CommandSpaceTimeVortex(GameObject GO)
{
    // ... ability logic ...
    return true;  // Missing ApplyCooldown() call!
}
```

**AI-Generated Fix:**
```csharp
public bool CommandSpaceTimeVortex(GameObject GO)
{
    // ... ability logic ...
    
    // Apply cooldown after successful use
    ApplyCooldown(GO, VortexAbilityID, GetCooldownForLevel(GO));
    
    return true;
}

private int GetCooldownForLevel(GameObject caster)
{
    int level = Level; // Mutation level
    int baseCooldown = 100; // Base turns
    int reduction = (level - 1) * 5; // Reduce by 5 turns per level
    return Math.Max(20, baseCooldown - reduction); // Minimum 20 turns
}
```

---

### 2. **Command Methods Without Cooldowns** (MEDIUM SEVERITY)
**Problem:** Command methods that trigger abilities may lack proper cooldown management.

**Detection:**
- Finds methods matching pattern: `public bool Command*(GameObject GO)`
- Checks for cooldown and energy cost management

**AI Recommendations:**
- Add `ApplyCooldown()` if tied to activated ability
- Add `GO.UseEnergy(1000)` if appropriate
- Add ready-state check: `IsMyActivatedAbilityReady()`

---

### 3. **Abilities Not Removed on Unmutate** (MEDIUM SEVERITY)
**Problem:** Abilities persist even after mutation is removed, causing UI clutter and potential bugs.

**Detection:**
- Identifies ability ID variables (e.g., `private Guid SomeAbilityID`)
- Checks if they're removed in `Unmutate()` method
- Looks for `RemoveMyActivatedAbility(ref abilityID)`

**Example Issue:**
```csharp
private Guid AggressiveAbilityID = Guid.Empty;
private Guid DefensiveAbilityID = Guid.Empty;

public override bool Unmutate(GameObject GO)
{
    // Missing RemoveMyActivatedAbility calls!
    return base.Unmutate(GO);
}
```

**AI-Generated Fix:**
```csharp
public override bool Unmutate(GameObject GO)
{
    RemoveMyActivatedAbility(ref AggressiveAbilityID);
    RemoveMyActivatedAbility(ref DefensiveAbilityID);
    return base.Unmutate(GO);
}
```

---

## Usage

### Automatic Detection
The fixer automatically detects these issues when analyzing any mod:

```bash
python qud_mod_fixer.py "Improved and Rebalanced Space Time Vortex" --model codellama:34b
```

### Expected Output
```
[ANALYZING MOD: Improved and Rebalanced Space Time Vortex]
  Found 2 API issues
  
[FIXING API ISSUES]
  Processing 1 files...
  
  [HIGH] Line 58: Activated ability "Space-Time Vortex (Aggressive)" has NO COOLDOWN
         This allows the player to spam the ability infinitely without any cost or delay.
  
  [HIGH] Line 65: Activated ability "Space-Time Vortex (Defensive)" has NO COOLDOWN
         This allows the player to spam the ability infinitely without any cost or delay.
  
  [RAG] Retrieving relevant code context...
  [RAG] [OK] Retrieved 5 relevant code chunks
  [AI] Generating fix with codellama:34b...
  [FIX] [OK] Applied fix to SpaceTimeVortex.cs
```

---

## AI Model Recommendations

For best results with activated ability fixes:

1. **CodeLlama 34B** (Recommended for complex abilities)
   - Best understanding of game mechanics
   - Properly implements cooldown scaling
   - Handles multi-ability coordination

2. **CodeLlama 13B** (Good balance)
   - Fast and accurate
   - Good for most ability fixes

3. **StarCoder 7B** (Fastest)
   - Quick fixes for simple cooldown additions
   - May need manual review for complex cases

---

## Integration with Error Logs

The fixer can read game error logs to provide additional context:

```bash
python qud_mod_fixer.py "My Mod" \
    --error-logs "C:\Users\...\CavesOfQud\Player.log" \
    --model codellama:13b
```

Error logs help the AI understand:
- Which abilities are causing crashes
- Timing issues (cooldowns too short/long)
- Missing null checks
- Energy cost balance

---

## Prompt Engineering

The fixer uses specialized prompts for ability issues:

**For Missing Cooldowns:**
- Provides exact fix pattern with variable names
- Suggests level-based cooldown scaling
- Shows proper placement in command method

**For Unmutate Issues:**
- Shows complete Unmutate() method template
- Handles multiple abilities correctly
- Maintains proper cleanup order

**For Command Methods:**
- Suggests both cooldown and energy costs
- Provides ready-state checking pattern
- Maintains existing functionality

---

## Limitations

Current detection does NOT cover:
- Runtime cooldown bugs (requires game testing)
- Balance issues (cooldown too short/long)
- Missing energy costs (unless obvious)
- Ability state persistence across saves

These require manual testing and tuning.

---

## Future Enhancements

Planned improvements:
- Detect abilities without energy costs
- Check for proper ability state validation
- Detect multiplayer sync issues
- Balance recommendation based on similar abilities
- Auto-generate cooldown formulas based on power level

