"""Test synergy system"""
from weapon_mutation_system import WeaponMutationSystem
import json

system = WeaponMutationSystem('weapon_mutation_example.json')

# Test Shred Mode + Condensed Rounds synergy
print("=" * 60)
print("Testing Synergy System")
print("=" * 60)

mutations = []
mutations, e1, i1 = system.apply_mutation(mutations, 'shred_mode')
print(f"\n1. Applied Shred Mode")
print(f"   Split Count: {e1.get('splitOnImpact', 0)}")

mutations, e2, i2 = system.apply_mutation(mutations, 'condensed_rounds')
print(f"\n2. Applied Condensed Rounds")
print(f"   Synergy Active: {e2.get('_synergyActive', False)}")
print(f"   Synergy Effect: {e2.get('_synergyEffect', 'None')}")
print(f"   Split Count: {e2.get('splitOnImpact', 0)}")
print(f"   Damage Multiplier: {e2.get('damageMultiplier', 1.0):.3f}")

# Test Pulsewave + Homing Seeker synergy
print("\n" + "=" * 60)
mutations2 = []
mutations2, e3, i3 = system.apply_mutation(mutations2, 'pulsewave')
mutations2, e4, i4 = system.apply_mutation(mutations2, 'homing_seeker')
print(f"\n3. Applied Pulsewave + Homing Seeker")
print(f"   Synergy Active: {e4.get('_synergyActive', False)}")
print(f"   Synergy Effect: {e4.get('_synergyEffect', 'None')}")
print(f"   Homing: {e4.get('homing', False)}")
print(f"   Damage Multiplier: {e4.get('damageMultiplier', 1.0):.3f}")

# Test Lightweight Barrel + Overclock synergy
print("\n" + "=" * 60)
mutations3 = []
mutations3, e5, i5 = system.apply_mutation(mutations3, 'lightweight_barrel')
mutations3, e6, i6 = system.apply_mutation(mutations3, 'overclock')
print(f"\n4. Applied Lightweight Barrel + Overclock")
print(f"   Synergy Active: {e6.get('_synergyActive', False)}")
print(f"   Synergy Effect: {e6.get('_synergyEffect', 'None')}")
print(f"   Projectile Speed: {e6.get('projectileSpeedMultiplier', 1.0):.3f}")

print("\n" + "=" * 60)
print("Synergy tests complete!")

