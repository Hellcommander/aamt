"""
Weapon Mutation System
Implements Nova Drift-inspired mutation system with 2-slot limit and deterministic merge rules.
"""

import json
import math
from typing import Dict, List, Optional, Tuple

class WeaponMutation:
    """Represents a single weapon mutation"""
    
    def __init__(self, mutation_data: Dict):
        self.id = mutation_data['id']
        self.tier = mutation_data['tier']
        self.name = mutation_data['name']
        self.description = mutation_data.get('description', '')
        self.slot_cost = mutation_data.get('slotCost', 1)
        self.instability = mutation_data.get('instability', 0)
        self.effects = mutation_data.get('effects', {})
        self.tradeoffs = mutation_data.get('tradeoffs', {})
        self.compatibility = mutation_data.get('compatibility', {})
        self.weapon_types = mutation_data.get('weaponTypes', ['all'])
        self.rarity = mutation_data.get('rarity', 0.5)
    
    def is_compatible_with(self, other: 'WeaponMutation') -> Tuple[bool, str]:
        """Check if this mutation is compatible with another"""
        # Check conflicts
        conflicts = self.compatibility.get('conflictsWith', [])
        if other.id in conflicts:
            return False, f"{self.name} conflicts with {other.name}"
        
        other_conflicts = other.compatibility.get('conflictsWith', [])
        if self.id in other_conflicts:
            return False, f"{other.name} conflicts with {self.name}"
        
        return True, ""
    
    def get_combined_instability(self, other: 'WeaponMutation') -> int:
        """Calculate combined instability from two mutations"""
        base_instability = self.instability + other.instability
        
        # Synergy bonus: if mutations synergize, reduce instability slightly
        if other.id in self.compatibility.get('synergizesWith', []):
            base_instability = max(0, base_instability - 2)
        
        return base_instability

class MutationMerger:
    """Handles deterministic merging of two mutations"""
    
    def __init__(self, diminishing_returns_k: float = 0.75):
        """
        Args:
            diminishing_returns_k: Controls diminishing returns curve (0.5-1.5)
        """
        self.diminishing_returns_k = diminishing_returns_k
    
    def apply_diminishing_returns(self, raw_bonus: float) -> float:
        """
        Apply diminishing returns formula:
        effectiveBonus = 1 + rawBonus / (1 + k * rawBonus)
        """
        if raw_bonus <= 0:
            return 1.0 + raw_bonus
        
        effective = 1.0 + raw_bonus / (1.0 + self.diminishing_returns_k * raw_bonus)
        return effective
    
    def merge_effects(self, mut1: WeaponMutation, mut2: WeaponMutation) -> Dict:
        """
        Deterministically merge two mutations' effects.
        Returns combined effect dictionary.
        Includes synergy bonuses for interesting combinations.
        """
        combined = {}
        
        # Check for synergy bonuses
        synergy_applied = False
        synergy = {}
        mut1_synergy = mut1.effects.get('synergyBonus', {})
        mut2_synergy = mut2.effects.get('synergyBonus', {})
        
        # Check if mutations synergize with each other
        if mut1_synergy and mut2.id in mut1_synergy.get('with', []):
            synergy_applied = True
            synergy = mut1_synergy
        elif mut2_synergy and mut1.id in mut2_synergy.get('with', []):
            synergy_applied = True
            synergy = mut2_synergy
        
        # Handle multipliers with diminishing returns
        multiplier_keys = [
            'damageMultiplier', 'fireRateMultiplier', 'projectileSpeedMultiplier',
            'rangeMultiplier', 'accuracyMultiplier'
        ]
        
        for key in multiplier_keys:
            val1 = mut1.effects.get(key, 1.0)
            val2 = mut2.effects.get(key, 1.0)
            
            # Apply synergy bonus if applicable
            if synergy_applied and key in synergy:
                synergy_val = synergy[key]
                if key == 'damageMultiplier' or key == 'fireRateMultiplier' or key == 'projectileSpeedMultiplier':
                    # Synergy bonus is a multiplier, apply it
                    val1 = val1 * synergy_val if val1 != 1.0 else synergy_val
                elif key == 'rangeMultiplier' or key == 'accuracyMultiplier':
                    val1 = val1 * synergy_val if val1 != 1.0 else synergy_val
            
            if val1 != 1.0 or val2 != 1.0:
                # Calculate raw bonus
                raw_bonus = (val1 - 1.0) + (val2 - 1.0)
                combined[key] = self.apply_diminishing_returns(raw_bonus)
        
        # Handle additive effects
        additive_keys = ['piercing', 'splitOnImpact']
        for key in additive_keys:
            val1 = mut1.effects.get(key, 0)
            val2 = mut2.effects.get(key, 0)
            
            # Apply synergy bonus if applicable
            if synergy_applied and key in synergy:
                synergy_val = synergy.get(key, 0)
                val1 = val1 + synergy_val
            
            combined[key] = val1 + val2
        
        # Handle boolean effects (OR logic)
        boolean_keys = ['homing']
        for key in boolean_keys:
            val1 = mut1.effects.get(key, False)
            val2 = mut2.effects.get(key, False)
            
            # Apply synergy bonus if applicable
            if synergy_applied and key in synergy:
                combined[key] = True
            else:
                combined[key] = val1 or val2
        
        # Handle proc effects (use higher proc chance)
        if 'procChance' in mut1.effects or 'procChance' in mut2.effects:
            proc1 = mut1.effects.get('procChance', 0.0)
            proc2 = mut2.effects.get('procChance', 0.0)
            
            # Apply synergy bonus if applicable
            if synergy_applied and 'procChance' in synergy:
                synergy_proc = synergy.get('procChance', 0.0)
                # Use synergy proc chance if higher, or combine
                if synergy_proc > 0:
                    proc1 = max(proc1, synergy_proc)
            
            # Combine procs: 1 - (1-p1) * (1-p2) for independent events
            combined['procChance'] = 1.0 - (1.0 - proc1) * (1.0 - proc2)
            
            # Use proc effect from higher tier, or mut1 if same tier, or synergy
            tier_order = {'minor': 1, 'major': 2, 'corrupt': 3}
            if synergy_applied and 'procEffect' in synergy:
                combined['procEffect'] = synergy['procEffect']
            elif tier_order.get(mut2.tier, 0) > tier_order.get(mut1.tier, 0):
                combined['procEffect'] = mut2.effects.get('procEffect')
            else:
                combined['procEffect'] = mut1.effects.get('procEffect')
        
        # Store synergy info for UI/tooltips
        if synergy_applied:
            combined['_synergyActive'] = True
            combined['_synergyEffect'] = synergy.get('effect', 'Synergy bonus active')
        
        # Handle behavior changes (higher tier wins, or merge if compatible)
        if 'behaviorChange' in mut1.effects or 'behaviorChange' in mut2.effects:
            tier_order = {'minor': 1, 'major': 2, 'corrupt': 3}
            tier1 = tier_order.get(mut1.tier, 0)
            tier2 = tier_order.get(mut2.tier, 0)
            
            if tier2 > tier1:
                combined['behaviorChange'] = mut2.effects.get('behaviorChange')
            elif tier1 > tier2:
                combined['behaviorChange'] = mut1.effects.get('behaviorChange')
            else:
                # Same tier: use first, or merge if compatible
                combined['behaviorChange'] = mut1.effects.get('behaviorChange')
        
        # Merge tradeoffs (additive penalties)
        combined_tradeoffs = {}
        tradeoff_keys = [
            'damagePenalty', 'fireRatePenalty', 'rangePenalty', 'accuracyPenalty',
            'recoilIncrease', 'heatBuildUp', 'cooldownPenalty', 'misfireChance',
            'selfDamageChance', 'ammoConsumption'
        ]
        
        for key in tradeoff_keys:
            val1 = mut1.tradeoffs.get(key, 0.0)
            val2 = mut2.tradeoffs.get(key, 0.0)
            if val1 != 0.0 or val2 != 0.0:
                combined_tradeoffs[key] = val1 + val2
        
        combined['tradeoffs'] = combined_tradeoffs
        
        return combined
    
    def resolve_conflict(self, mut1: WeaponMutation, mut2: WeaponMutation) -> Optional[WeaponMutation]:
        """
        Resolve conflicts between mutations.
        Returns the mutation to keep (higher tier wins), or None if both should be removed.
        """
        tier_order = {'minor': 1, 'major': 2, 'corrupt': 3}
        tier1 = tier_order.get(mut1.tier, 0)
        tier2 = tier_order.get(mut2.tier, 0)
        
        if tier2 > tier1:
            return mut2
        elif tier1 > tier2:
            return mut1
        else:
            # Same tier: keep first one
            return mut1

class WeaponMutationSystem:
    """Main system for managing weapon mutations"""
    
    def __init__(self, registry_path: str):
        """Load mutation registry"""
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        self.mutations = {
            mut['id']: WeaponMutation(mut)
            for mut in registry.get('mutations', [])
        }
        self.merger = MutationMerger()
    
    def get_mutation(self, mutation_id: str) -> Optional[WeaponMutation]:
        """Get mutation by ID"""
        return self.mutations.get(mutation_id)
    
    def can_apply_mutation(self, current_mutations: List[str], new_mutation_id: str, allow_replace: bool = True) -> Tuple[bool, str]:
        """
        Check if a mutation can be applied to a weapon.
        Returns (can_apply, reason)
        
        Args:
            allow_replace: If True, allows replacing a mutation when at max (2)
        """
        if len(current_mutations) >= 2 and not allow_replace:
            return False, "Weapon already has 2 mutations (max limit). Use replace mode to swap mutations."
        
        new_mut = self.get_mutation(new_mutation_id)
        if not new_mut:
            return False, f"Mutation {new_mutation_id} not found"
        
        # Check compatibility with existing mutations (if replacing, check compatibility with kept mutation)
        if len(current_mutations) >= 2:
            # When replacing, check compatibility with the mutation that would be kept
            existing_muts = [self.get_mutation(mid) for mid in current_mutations if self.get_mutation(mid)]
            existing_muts = [m for m in existing_muts if m]
            
            if existing_muts:
                # Check against higher tier mutation (the one that would be kept)
                tier_order = {'minor': 1, 'major': 2, 'corrupt': 3}
                existing_muts.sort(key=lambda m: tier_order.get(m.tier, 0))
                kept_mut = existing_muts[1]  # Higher tier
                
                compatible, reason = new_mut.is_compatible_with(kept_mut)
                if not compatible:
                    return False, reason
        else:
            # Check compatibility with all existing mutations
            for existing_id in current_mutations:
                existing_mut = self.get_mutation(existing_id)
                if existing_mut:
                    compatible, reason = new_mut.is_compatible_with(existing_mut)
                    if not compatible:
                        return False, reason
        
        return True, ""
    
    def apply_mutation(self, current_mutations: List[str], new_mutation_id: str) -> Tuple[List[str], Dict, int]:
        """
        Apply a mutation to a weapon.
        Returns (final_mutation_list, combined_effects, total_instability)
        """
        new_mut = self.get_mutation(new_mutation_id)
        if not new_mut:
            return current_mutations, {}, 0
        
        # If weapon has 2 mutations, replace one (keep higher tier)
        if len(current_mutations) >= 2:
            existing_muts = [self.get_mutation(mid) for mid in current_mutations if self.get_mutation(mid)]
            existing_muts = [m for m in existing_muts if m]
            
            if existing_muts:
                # Replace lower tier mutation
                tier_order = {'minor': 1, 'major': 2, 'corrupt': 3}
                existing_muts.sort(key=lambda m: tier_order.get(m.tier, 0))
                current_mutations = [existing_muts[1].id]  # Keep higher tier
        
        # Add new mutation
        final_list = current_mutations + [new_mutation_id]
        
        # Calculate combined effects
        if len(final_list) == 2:
            mut1 = self.get_mutation(final_list[0])
            mut2 = self.get_mutation(final_list[1])
            if mut1 and mut2:
                combined_effects = self.merger.merge_effects(mut1, mut2)
                total_instability = mut1.get_combined_instability(mut2)
                return final_list, combined_effects, total_instability
        elif len(final_list) == 1:
            mut = self.get_mutation(final_list[0])
            if mut:
                return final_list, mut.effects.copy(), mut.instability
        
        return final_list, {}, 0
    
    def get_mutation_preview(self, current_mutations: List[str], new_mutation_id: str) -> Dict:
        """
        Get preview of what weapon stats would be with mutation applied.
        Returns preview dictionary with stat changes.
        """
        final_list, combined_effects, instability = self.apply_mutation(current_mutations, new_mutation_id)
        
        preview = {
            "mutations": final_list,
            "effects": combined_effects,
            "instability": instability,
            "slot_usage": sum(self.get_mutation(mid).slot_cost if self.get_mutation(mid) else 0 for mid in final_list)
        }
        
        return preview

def main():
    """Test the mutation system"""
    system = WeaponMutationSystem("weapon_mutation_example.json")
    
    # Test: Apply mutations
    mutations = []
    
    # Apply first mutation
    can_apply, reason = system.can_apply_mutation(mutations, "lightweight_barrel")
    print(f"Can apply lightweight_barrel: {can_apply}, {reason}")
    mutations, effects, instability = system.apply_mutation(mutations, "lightweight_barrel")
    print(f"Applied. Mutations: {mutations}, Instability: {instability}")
    
    # Apply second mutation
    can_apply, reason = system.can_apply_mutation(mutations, "condensed_rounds")
    print(f"Can apply condensed_rounds: {can_apply}, {reason}")
    mutations, effects, instability = system.apply_mutation(mutations, "condensed_rounds")
    print(f"Applied. Mutations: {mutations}, Instability: {instability}")
    print(f"Combined effects: {json.dumps(effects, indent=2)}")
    
    # Try to apply third (should replace one)
    can_apply, reason = system.can_apply_mutation(mutations, "overclock")
    print(f"Can apply overclock: {can_apply}, {reason}")
    mutations, effects, instability = system.apply_mutation(mutations, "overclock")
    print(f"Applied. Mutations: {mutations}, Instability: {instability}")
    
    # Test conflict
    can_apply, reason = system.can_apply_mutation(mutations, "phase_rounds")
    print(f"Can apply phase_rounds: {can_apply}, {reason}")

if __name__ == "__main__":
    main()

