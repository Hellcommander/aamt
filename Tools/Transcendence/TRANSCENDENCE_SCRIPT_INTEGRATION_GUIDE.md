# Transcendence Script Integration Guide for Weapon Mutations

## Overview

This guide explains how to integrate the generated weapon mutation behavior scripts into Transcendence mods. The scripts use Transcendence's TML (Transcendence Markup Language) scripting system.

## Transcendence Scripting Basics

### Script Structure

Transcendence scripts are embedded in XML using `<Events>` blocks:

```xml
<ItemType UNID="&mutPhaseRounds;">
	<Events>
		<OnDamage>
			(block Nil
				; Your script code here
			)
		</OnDamage>
	</Events>
</ItemType>
```

### TML Syntax Rules

1. **Comments**: Use semicolon (`;`) for comments inside script blocks
2. **Parentheses**: All expressions must be properly balanced
3. **Blocks**: Use `(block Nil ...)` for sequencing multiple statements
4. **Variables**: Use `(setq varName value)` to set variables
5. **Conditionals**: Use `(if condition thenValue elseValue)`

### Event Handlers

Common event handlers for weapon mutations:
- `<OnFireWeapon>` - When weapon fires
- `<OnDamage>` - When damage is dealt
- `<OnDestroy>` - When target is destroyed
- `<OnUpdate>` - Per-tick updates (use sparingly)

## Integration Steps

### Step 1: Copy Behavior Code

The generated `weapon_mutation_behaviors.xml` contains `<Events>` blocks for each mutation. Copy the relevant block into your `ItemType` definition.

### Step 2: Add to ItemType

```xml
<ItemType UNID="&mutPhaseRounds;" name="Phase Rounds">
	<Properties>
		<!-- Mutation properties -->
	</Properties>
	
	<!-- Copy the <Events> block from generated file -->
	<Events>
		<OnDamage>
			(block Nil
				(if (and aObjAttacked aCause (objGetData aCause 'mutPhaseRounds))
					(block (phaseDamage)
						(setq phaseDamage (multiply (itmGetLevel aCause) 0.85))
						(objIncProperty aObjAttacked 'armor (subtract 0 phaseDamage))
					)
				)
			)
		</OnDamage>
	</Events>
</ItemType>
```

### Step 3: Apply Mutations to Weapons

Mutations must be marked on weapons/projectiles using `objSetData`:

```xml
<Events>
	<OnFireWeapon>
		(block (projectile)
			(setq projectile (sysCreateWeaponFire aWeaponUNID gSource aFirePos aFireAngle (typGetDataField aWeaponUNID "speed") aTargetObj))
			(if projectile
				(block Nil
					; Check if weapon has Phase Rounds mutation
					(if (objGetData aWeapon 'mutPhaseRounds)
						(objSetData projectile 'mutPhaseRounds true)
					)
				)
			)
		)
	</OnFireWeapon>
</Events>
```

## Generated Behavior Scripts

### Available Behaviors

1. **Phase Through Shields** (`phase_through_shields`)
   - Event: `<OnDamage>`
   - Bypasses shields, deals direct hull damage

2. **Spawn Shard on Kill** (`spawn_shard_on_kill`)
   - Event: `<OnDestroy>`
   - Creates explosion on enemy kill

3. **Vortex Orb** (`orb_creation`)
   - Events: `<OnFireWeapon>`, `<OnUpdate>`
   - Creates slow-moving orb with burn aura

4. **Pulsewave** (`pulsewave`)
   - Event: `<OnFireWeapon>`
   - Creates multiple pulses around projectile

5. **Ricochet** (`ricochet`)
   - Event: `<OnDamage>`
   - Bounces projectiles off surfaces

6. **Kinetic Blast** (`kinetic_blast`)
   - Events: `<OnUpdate>`, `<OnFireWeapon>`, `<OnCollision>`
   - Charges while moving, auto-fires on collision

7. **Sticky Bomb** (`sticky_bomb`)
   - Events: `<OnFireWeapon>`, `<OnUpdate>`
   - Attaches to enemies, chain explosions

8. **Harpoon Tether** (`harpoon_tether`)
   - Events: `<OnFireWeapon>`, `<OnUpdate>`
   - Creates burn tether between projectile and shooter

9. **Greatsword** (`greatsword`)
   - Events: `<OnFireWeapon>`, `<OnUpdate>`
   - Damage scales with missing hull

## Best Practices

### Performance

- **Avoid `<OnUpdate>` when possible**: Use event-driven handlers instead
- **Cache data lookups**: Store mutation flags on objects, not repeated checks
- **Limit per-tick operations**: Only use `<OnUpdate>` for behaviors that need continuous updates

### Error Handling

Always check for `Nil` values:

```xml
<OnDamage>
	(block Nil
		(if (and aObjAttacked aCause (objGetData aCause 'mutPhaseRounds))
			(block (phaseDamage)
				; Safe to proceed
			)
		)
	)
</OnDamage>
```

### Data Storage

Use `objSetData` to mark mutations:

```xml
; On weapon/item
(objSetData weaponObj 'mutPhaseRounds true)

; On projectile
(objSetData projectile 'mutPhaseRounds true)

; Check mutation
(if (objGetData obj 'mutPhaseRounds)
	(block Nil
		; Mutation active
	)
)
```

## Version Compatibility

### API 57+

The generated scripts use API 57+ functions:
- `objGetData` / `objSetData`
- `objIncProperty`
- `sysCreateWeaponFire`
- `sysCreateExplosion`

### Testing

1. Load mod in Transcendence
2. Equip weapon with mutation
3. Test behavior in-game
4. Check debug log for errors

## Troubleshooting

### "content expected" Error

- Check parentheses balance
- Ensure all expressions are wrapped in `(block Nil ...)`
- Verify no XML comments inside script blocks (use semicolon comments)

### Mutation Not Triggering

- Verify `objSetData` is called to mark mutation
- Check event handler is in correct XML element
- Ensure mutation ID matches between XML and script

### Performance Issues

- Reduce `<OnUpdate>` usage
- Cache mutation checks
- Limit per-tick operations

## Example: Complete Integration

```xml
<!DOCTYPE TranscendenceExtension
[
	<!ENTITY unidWeaponMutations	"0xE1271000">
	<!ENTITY mutPhaseRounds			"0xE1272001">
]>

<TranscendenceExtension UNID="&unidWeaponMutations;" name="Weapon Mutations" version="1.0.0">
	
	<!-- Mutation Item Definition -->
	<ItemType UNID="&mutPhaseRounds;" name="Phase Rounds">
		<Properties>
			<MutEffects behaviorChange="phase_through_shields" damageMultiplier="0.85"/>
		</Properties>
		
		<!-- Behavior Script -->
		<Events>
			<OnDamage>
				(block Nil
					(if (and aObjAttacked aCause (objGetData aCause 'mutPhaseRounds))
						(block (phaseDamage)
							(setq phaseDamage (multiply (itmGetLevel aCause) 0.85))
							(objIncProperty aObjAttacked 'armor (subtract 0 phaseDamage))
						)
					)
				)
			</OnDamage>
		</Events>
	</ItemType>
	
	<!-- Weapon with Mutation Applied -->
	<ItemType UNID="&myWeapon;" name="My Weapon">
		<Events>
			<OnFireWeapon>
				(block (projectile)
					(setq projectile (sysCreateWeaponFire aWeaponUNID gSource aFirePos aFireAngle (typGetDataField aWeaponUNID "speed") aTargetObj))
					(if projectile
						(block Nil
							; Apply Phase Rounds mutation if equipped
							(if (objGetData aWeapon 'mutPhaseRounds)
								(objSetData projectile 'mutPhaseRounds true)
							)
						)
					)
				)
			</OnFireWeapon>
		</Events>
	</ItemType>
	
</TranscendenceExtension>
```

## Resources

- Transcendence Forums: https://forums.kronosaur.com/
- API Documentation: Check `FunctionList_API57.txt` or `FunctionList_API59.txt`
- Community Tutorials: Follow 2025 modding guides for current best practices

## Generated Files

- `weapon_mutation_behaviors.xml` - Behavior script implementations
- `weapon_mutations.xml` - Mutation item definitions
- Use both files together for complete integration

