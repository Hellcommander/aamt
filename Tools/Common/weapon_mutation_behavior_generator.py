"""
Weapon Mutation Behavior Code Generator
Generates Transcendence script code for weapon mutation behavior changes.
"""

import json
from typing import Dict, List, Optional

class BehaviorCodeGenerator:
    """Generates Transcendence script code for weapon mutation behaviors"""
    
    def __init__(self):
        self.behavior_templates = self._load_behavior_templates()
    
    def _load_behavior_templates(self) -> Dict[str, str]:
        """Load behavior implementation templates"""
        return {
            "phase_through_shields": self._phase_through_shields_code(),
            "spawn_shard_on_kill": self._spawn_shard_on_kill_code(),
            "orb_creation": self._orb_creation_code(),
            "pulsewave": self._pulsewave_code(),
            "ricochet": self._ricochet_code(),
            "kinetic_blast": self._kinetic_blast_code(),
            "sticky_bomb": self._sticky_bomb_code(),
            "harpoon_tether": self._harpoon_tether_code(),
            "greatsword": self._greatsword_code(),
        }
    
    def generate_behavior_code(self, behavior_type: str, mutation_data: Dict) -> Optional[str]:
        """Generate code for a specific behavior type"""
        if behavior_type not in self.behavior_templates:
            return None
        
        template = self.behavior_templates[behavior_type]
        
        # Replace placeholders with mutation-specific values
        code = template
        
        # Add mutation-specific parameters
        if 'effects' in mutation_data:
            effects = mutation_data['effects']
            
            # Replace common placeholders
            if 'damageMultiplier' in effects:
                code = code.replace('{damageMultiplier}', str(effects['damageMultiplier']))
            if 'fireRateMultiplier' in effects:
                code = code.replace('{fireRateMultiplier}', str(effects['fireRateMultiplier']))
            if 'splitOnImpact' in effects:
                code = code.replace('{splitCount}', str(effects['splitOnImpact']))
            if 'piercing' in effects:
                code = code.replace('{pierceCount}', str(effects['piercing']))
            if 'procChance' in effects:
                code = code.replace('{procChance}', str(effects['procChance']))
            if 'procEffect' in effects:
                code = code.replace('{procEffect}', effects['procEffect'])
        
        # Default values
        code = code.replace('{damageMultiplier}', '1.0')
        code = code.replace('{fireRateMultiplier}', '1.0')
        code = code.replace('{splitCount}', '3')
        code = code.replace('{pierceCount}', '1')
        code = code.replace('{procChance}', '0.25')
        code = code.replace('{procEffect}', 'burn')
        
        return code
    
    def _phase_through_shields_code(self) -> str:
        """Phase through shields behavior"""
        return """
<!-- Phase Through Shields Behavior -->
<!-- Copy this <Events> block into your ItemType definition -->
<Events>
	<OnDamage>
		(block Nil
			(if (and aObjAttacked aCause (objGetData aCause 'mutPhaseRounds))
				(block (phaseDamage)
					; Phase through shields, deal direct hull damage
					(setq phaseDamage (multiply (itmGetLevel aCause) {damageMultiplier}))
					(objIncProperty aObjAttacked 'armor (subtract 0 phaseDamage))
					(dbgLog (cat "Phase Rounds: Dealt " phaseDamage " direct hull damage"))
				)
			)
		)
	</OnDamage>
</Events>
"""
    
    def _spawn_shard_on_kill_code(self) -> str:
        """Spawn shard on kill behavior"""
        return """
<!-- Spawn Shard on Kill Behavior -->
<!-- Copy this <Events> block into your ItemType definition -->
<Events>
	<OnDestroy>
		(block Nil
			(if (and aObjDestroyed aCause (objGetData aCause 'mutEntropyBloom))
				(block (shardPos shardDamage)
					(setq shardPos (objGetPos aObjDestroyed))
					(setq shardDamage (multiply (itmGetLevel aCause) 2))
					
					; Create volatile shard explosion
					(sysCreateExplosion shardPos 20 shardDamage 'blast)
					
					; Small chance for self-damage
					(if (leq (random 1 100) 10)
						(objIncProperty gSource 'armor (subtract 0 (divide shardDamage 2)))
						Nil
					)
					
					(dbgLog (cat "Entropy Bloom: Spawned shard on kill"))
				)
			)
		)
	</OnDestroy>
</Events>
"""
    
    def _orb_creation_code(self) -> str:
        """Vortex orb creation behavior"""
        return """
<!-- Vortex Orb Behavior -->
<!-- Copy this <Events> block into your ItemType definition -->
<Events>
	<OnFireWeapon>
		(block Nil
			(if (objGetData aWeapon 'mutVortexOrb)
				(block (orbObj orbPos)
					; Create slow-moving orb
					(setq orbPos (objGetPos gSource))
					(setq orbObj (sysCreateWeaponFire aWeaponUNID gSource orbPos aFireAngle 50 aTargetObj))
					
					(if orbObj
						(block Nil
							(objSetData orbObj 'mutVortexOrb true)
							(objSetData orbObj 'orbDamage (multiply (itmGetLevel aWeapon) {damageMultiplier}))
							(objSetVelocity orbObj (multiply (objGetVel gSource) 0.3))
							(dbgLog "Vortex Orb: Created orb")
						)
						Nil
					)
				)
				Nil
			)
		)
	</OnFireWeapon>
	
	<OnUpdate>
		(block Nil
			(if (objGetData gSource 'mutVortexOrb)
				(block (orbDamage nearbyEnemies)
					(setq orbDamage (objGetData gSource 'orbDamage))
					(setq nearbyEnemies (sysFindObject gSource "s E D:40"))
					
					; Apply burn damage to nearby enemies
					(enum nearbyEnemies theEnemy
						(objIncProperty theEnemy 'armor (subtract 0 (divide orbDamage 10)))
					)
				)
				Nil
			)
		)
	</OnUpdate>
</Events>
"""
    
    def _pulsewave_code(self) -> str:
        """Pulsewave behavior"""
        return """
<!-- Pulsewave Behavior -->
<Events>
    <OnFireWeapon>
        (if (objGetData aWeapon 'mutPulsewave)
            (block (pulseCount i pulseAngle pulseProjectile)
                (setq pulseCount {splitCount})
                
                ; Create pulses around projectile
                (for i 0 (subtract pulseCount 1)
                    (block Nil
                        (setq pulseAngle (add aFireAngle (multiply i (divide 360 pulseCount))))
                        (setq pulseProjectile (sysCreateWeaponFire aWeaponUNID gSource aFirePos pulseAngle (multiply (typGetDataField aWeaponUNID "speed") 0.8) aTargetObj))
                        
                        (if pulseProjectile
                            (block Nil
                                (objSetData pulseProjectile 'mutPulsewave true)
                                (objSetData pulseProjectile 'pulseDamage (multiply (itmGetLevel aWeapon) {damageMultiplier}))
                            )
                        )
                    )
                )
                
                (dbgLog (cat "Pulsewave: Created " pulseCount " pulses"))
            )
        )
    </OnFireWeapon>
</Events>
"""
    
    def _ricochet_code(self) -> str:
        """Ricochet behavior"""
        return """
<!-- Ricochet Behavior -->
<Events>
    <OnDamage>
        (if (and aObjAttacked aCause (objGetData aCause 'mutRicochet))
            (block (ricochetCount hitPos hitAngle nearbyTargets)
                (setq ricochetCount (objGetData aCause 'ricochetCount))
                (if (not ricochetCount) (setq ricochetCount 0))
                
                ; Check if should ricochet
                (if (leq ricochetCount {pierceCount})
                    (block (newTarget)
                        (setq hitPos (objGetPos aObjAttacked))
                        (setq hitAngle (objGetRotation aCause))
                        (setq nearbyTargets (sysFindObject hitPos (cat "s E D:60 -" (objGetID aObjAttacked))))
                        
                        ; Find nearest target
                        (setq newTarget (sysFindObject hitPos (cat "s E D:60 -" (objGetID aObjAttacked) " N:1")))
                        
                        (if newTarget
                            (block (newProjectile)
                                ; Create ricochet projectile
                                (setq newProjectile (sysCreateWeaponFire (objGetType aCause) gSource hitPos hitAngle (objGetVel aCause) newTarget))
                                (if newProjectile
                                    (objSetData newProjectile 'ricochetCount (add ricochetCount 1))
                            )
                        )
                    )
                )
            )
        )
    </OnDamage>
</Events>
"""
    
    def _kinetic_blast_code(self) -> str:
        """Kinetic blast behavior"""
        return """
<!-- Kinetic Blast Behavior -->
<Events>
    <OnUpdate>
        (if (objGetData gSource 'mutKineticBlast)
            (block (chargeLevel speed)
                ; Charge based on movement speed
                (setq speed (objGetVel gSource))
                (setq chargeLevel (add (objGetData gSource 'kineticCharge) (divide (objGetVel gSource) 100)))
                
                ; Cap charge
                (if (gr chargeLevel 100) (setq chargeLevel 100))
                (objSetData gSource 'kineticCharge chargeLevel)
            )
        )
    </OnUpdate>
    
    <OnFireWeapon>
        (if (objGetData aWeapon 'mutKineticBlast)
            (block (chargeLevel blastDamage)
                (setq chargeLevel (objGetData gSource 'kineticCharge))
                (if (not chargeLevel) (setq chargeLevel 50))
                
                ; Scale damage with charge
                (setq blastDamage (multiply (itmGetLevel aWeapon) {damageMultiplier} (divide chargeLevel 100)))
                
                ; Create pair of focused blasts
                (sysCreateWeaponFire aWeaponUNID gSource aFirePos (subtract aFireAngle 5) (typGetDataField aWeaponUNID "speed") aTargetObj)
                (sysCreateWeaponFire aWeaponUNID gSource aFirePos (add aFireAngle 5) (typGetDataField aWeaponUNID "speed") aTargetObj)
                
                ; Reset charge
                (objSetData gSource 'kineticCharge 0)
                
                (dbgLog (cat "Kinetic Blast: Fired at " chargeLevel "% charge"))
            )
        )
    </OnFireWeapon>
    
    <OnCollision>
        (if (and aObjHit (objGetData gSource 'mutKineticBlast))
            (block (chargeLevel)
                ; Auto-fire on collision
                (setq chargeLevel (objGetData gSource 'kineticCharge))
                (if (gr chargeLevel 30)
                    (block Nil
                        ; Trigger weapon fire
                        (shpFireWeapon gSource (objGetItemByType gSource (objGetType (objGetItemByType gSource "w"))))
                        (objSetData gSource 'kineticCharge 0)
                    )
                )
            )
        )
    </OnCollision>
</Events>
"""
    
    def _sticky_bomb_code(self) -> str:
        """Sticky bomb behavior"""
        return """
<!-- Sticky Bomb Behavior -->
<Events>
    <OnFireWeapon>
        (if (objGetData aWeapon 'mutStickyBomb)
            (block (bombObj)
                (setq bombObj (sysCreateWeaponFire aWeaponUNID gSource aFirePos aFireAngle (typGetDataField aWeaponUNID "speed") aTargetObj))
                
                (if bombObj
                    (block Nil
                        (objSetData bombObj 'mutStickyBomb true)
                        (objSetData bombObj 'stickyFuse 30) ; 30 ticks fuse
                        (objSetData bombObj 'stickyAttached false)
                    )
                )
            )
        )
    </OnFireWeapon>
    
    <OnUpdate>
        (if (objGetData gSource 'mutStickyBomb)
            (block (fuse attachedTarget nearbyBombs)
                (setq fuse (objGetData gSource 'stickyFuse))
                (setq attachedTarget (objGetData gSource 'stickyAttached))
                
                ; Check for attachment
                (if (not attachedTarget)
                    (block (nearbyTargets)
                        (setq nearbyTargets (sysFindObject gSource "s E D:10"))
                        (if nearbyTargets
                            (block (target)
                                (setq target (@ nearbyTargets 0))
                                (objSetData gSource 'stickyAttached target)
                                (objSetData target 'stickyBombs (add (objGetData target 'stickyBombs) 1))
                            )
                        )
                    )
                )
                
                ; Countdown fuse
                (if (gr fuse 0)
                    (objSetData gSource 'stickyFuse (subtract fuse 1))
                    (block (bombPos bombDamage chainBombs)
                        ; Explode
                        (setq bombPos (objGetPos gSource))
                        (setq bombDamage (multiply (itmGetLevel gSource) {damageMultiplier}))
                        (sysCreateExplosion bombPos 30 bombDamage 'blast)
                        
                        ; Chain reaction: explode nearby sticky bombs
                        (setq chainBombs (sysFindObject bombPos "s D:40"))
                        (enum chainBombs theBomb
                            (if (objGetData theBomb 'mutStickyBomb)
                                (objSetData theBomb 'stickyFuse 0)
                            )
                        )
                        
                        ; Remove from target count
                        (if attachedTarget
                            (objSetData attachedTarget 'stickyBombs (subtract (objGetData attachedTarget 'stickyBombs) 1))
                        )
                        
                        (objDestroy gSource)
                    )
                )
            )
        )
    </OnUpdate>
</Events>
"""
    
    def _harpoon_tether_code(self) -> str:
        """Harpoon tether behavior"""
        return """
<!-- Harpoon Tether Behavior -->
<Events>
    <OnFireWeapon>
        (if (objGetData aWeapon 'mutHarpoon)
            (block (harpoonObj)
                (setq harpoonObj (sysCreateWeaponFire aWeaponUNID gSource aFirePos aFireAngle (multiply (typGetDataField aWeaponUNID "speed") 0.6) aTargetObj))
                
                (if harpoonObj
                    (block Nil
                        (objSetData harpoonObj 'mutHarpoon true)
                        (objSetData harpoonObj 'harpoonShooter gSource)
                        (objSetData harpoonObj 'harpoonDamage (multiply (itmGetLevel aWeapon) {damageMultiplier}))
                    )
                )
            )
        )
    </OnFireWeapon>
    
    <OnUpdate>
        (if (objGetData gSource 'mutHarpoon)
            (block (attachedTarget shooter tetherDamage)
                (setq attachedTarget (objGetData gSource 'harpoonAttached))
                (setq shooter (objGetData gSource 'harpoonShooter))
                
                ; Check for attachment
                (if (not attachedTarget)
                    (block (nearbyTargets)
                        (setq nearbyTargets (sysFindObject gSource "s E D:8"))
                        (if nearbyTargets
                            (objSetData gSource 'harpoonAttached (@ nearbyTargets 0))
                        )
                    )
                )
                
                ; Apply burn damage via tether
                (if (and attachedTarget shooter)
                    (block Nil
                        (setq tetherDamage (divide (objGetData gSource 'harpoonDamage) 20))
                        (objIncProperty attachedTarget 'armor (subtract 0 tetherDamage))
                        
                        ; Visual tether effect (would need custom rendering)
                        (dbgLog (cat "Harpoon: Applied " tetherDamage " burn damage via tether"))
                    )
                )
            )
        )
    </OnUpdate>
</Events>
"""
    
    def _greatsword_code(self) -> str:
        """Greatsword behavior"""
        return """
<!-- Greatsword Behavior -->
<Events>
    <OnFireWeapon>
        (if (objGetData aWeapon 'mutGreatsword)
            (block (swordObj hullPercent damageScale)
                ; Calculate damage scale based on missing hull
                (setq hullPercent (divide (objGetProperty gSource 'armor) (objGetProperty gSource 'maxArmor)))
                (setq damageScale (add 1.0 (multiply (subtract 1.0 hullPercent) 1.0))) ; Up to 2x at 0% hull
                
                ; Create single massive sword
                (setq swordObj (sysCreateWeaponFire aWeaponUNID gSource aFirePos aFireAngle (multiply (typGetDataField aWeaponUNID "speed") 0.5) aTargetObj))
                
                (if swordObj
                    (block Nil
                        (objSetData swordObj 'mutGreatsword true)
                        (objSetData swordObj 'greatswordDamage (multiply (itmGetLevel aWeapon) {damageMultiplier} damageScale))
                        (objSetProperty swordObj 'invulnerable true) ; Indestructible
                    )
                )
                
                (dbgLog (cat "Greatsword: Created at " (multiply hullPercent 100) "% hull, " damageScale "x damage"))
            )
        )
    </OnFireWeapon>
    
    <OnUpdate>
        (if (objGetData gSource 'mutGreatsword)
            (block Nil
                ; Provide armor and damage reduction
                (objIncProperty gSource 'armor 1) ; Small regen
                (objSetProperty gSource 'damageAdj (multiply (objGetProperty gSource 'damageAdj) 0.95)) ; 5% damage reduction
            )
        )
    </OnUpdate>
</Events>
"""
    
    def generate_complete_behavior_file(self, mutations: List[Dict], output_path: str):
        """Generate complete behavior implementation file with proper Transcendence XML structure"""
        code_parts = []
        
        # XML header
        code_parts.append('<?xml version="1.0" encoding="utf-8"?>')
        code_parts.append('')
        code_parts.append('<!--')
        code_parts.append('  Weapon Mutation Behavior Implementations')
        code_parts.append('  Generated for Transcendence mod integration')
        code_parts.append('  ')
        code_parts.append('  USAGE:')
        code_parts.append('  1. Copy the <Events> blocks below into your ItemType definitions')
        code_parts.append('  2. Ensure mutations are applied to weapons via objSetData')
        code_parts.append('  3. Event handlers will automatically trigger based on mutation type')
        code_parts.append('-->')
        code_parts.append('')
        
        # Generate individual behavior blocks
        for mutation in mutations:
            behavior = mutation.get('effects', {}).get('behaviorChange')
            if behavior:
                behavior_code = self.generate_behavior_code(behavior, mutation)
                if behavior_code:
                    # Clean up the code (remove nested Events tags, fix comments)
                    behavior_code = self._clean_behavior_code(behavior_code, mutation)
                    code_parts.append(behavior_code)
                    code_parts.append('')
        
        full_code = "\n".join(code_parts)
        
        # Write to file
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_code)
        
        print(f"Behavior code generated: {output_path}")
    
    def _clean_behavior_code(self, code: str, mutation: Dict) -> str:
        """Clean up behavior code to match Transcendence XML format"""
        # Remove nested Events tags (we'll provide them separately)
        code = code.replace('<!--', '<!--')
        code = code.replace('-->', '-->')
        
        # Convert XML comments inside script blocks to TML comments (semicolon)
        lines = code.split('\n')
        cleaned_lines = []
        in_script_block = False
        
        for line in lines:
            # Detect script block boundaries
            if '<On' in line or '<Events>' in line:
                in_script_block = True
            if '</On' in line or '</Events>' in line:
                in_script_block = False
            
            # Convert XML comments to TML comments inside script blocks
            if in_script_block and '<!--' in line and '-->' in line:
                # Extract comment text
                import re
                match = re.search(r'<!--\s*(.*?)\s*-->', line)
                if match:
                    comment_text = match.group(1)
                    indent = len(line) - len(line.lstrip())
                    cleaned_lines.append(' ' * indent + '; ' + comment_text)
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate behavior code for weapon mutations')
    parser.add_argument('--registry', required=True, help='Path to mutation registry JSON')
    parser.add_argument('--output', required=True, help='Output path for behavior code')
    
    args = parser.parse_args()
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    # Generate code
    generator = BehaviorCodeGenerator()
    generator.generate_complete_behavior_file(registry.get('mutations', []), args.output)

if __name__ == "__main__":
    main()

