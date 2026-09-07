"""List all synergy combinations"""
from weapon_mutation_system import WeaponMutationSystem

system = WeaponMutationSystem('weapon_mutation_example.json')

print("=" * 70)
print("WEAPON MUTATION SYNERGIES")
print("=" * 70)
print()

synergies_found = []

for mut1 in system.mutations.values():
    mut1_synergy = mut1.effects.get('synergyBonus', {})
    if mut1_synergy and 'with' in mut1_synergy:
        for partner_id in mut1_synergy['with']:
            partner = system.get_mutation(partner_id)
            if partner:
                effect = mut1_synergy.get('effect', 'Synergy active')
                synergies_found.append((mut1.name, partner.name, effect))

print(f"Total Synergies: {len(synergies_found)}")
print()
print("-" * 70)

for i, (mut1_name, mut2_name, effect) in enumerate(synergies_found, 1):
    print(f"{i}. {mut1_name} + {mut2_name}")
    print(f"   Effect: {effect}")
    print()

print("=" * 70)
print("Synergy system makes combinations more interesting!")
print("=" * 70)

