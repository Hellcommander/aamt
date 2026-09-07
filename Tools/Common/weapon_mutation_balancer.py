"""
Weapon Mutation Balance Testing Tools
Automated simulation and analysis tools for testing mutation combinations.
"""

import json
import math
from typing import Dict, List, Tuple
from weapon_mutation_system import WeaponMutationSystem, WeaponMutation

class MutationSimulator:
    """Simulates weapon performance with mutations"""
    
    def __init__(self, base_damage: float = 100.0, base_fire_rate: float = 1.0, base_range: float = 100.0):
        """
        Args:
            base_damage: Base weapon damage per shot
            base_fire_rate: Base shots per second
            base_range: Base weapon range
        """
        self.base_damage = base_damage
        self.base_fire_rate = base_fire_rate
        self.base_range = base_range
    
    def calculate_dps(self, effects: Dict, tradeoffs: Dict) -> float:
        """Calculate DPS with mutation effects"""
        damage_mult = effects.get('damageMultiplier', 1.0)
        fire_rate_mult = effects.get('fireRateMultiplier', 1.0)
        
        # Apply tradeoffs
        damage_penalty = tradeoffs.get('damagePenalty', 0.0)
        fire_rate_penalty = tradeoffs.get('fireRatePenalty', 0.0)
        
        final_damage = self.base_damage * damage_mult * (1.0 - damage_penalty)
        final_fire_rate = self.base_fire_rate * fire_rate_mult * (1.0 - fire_rate_penalty)
        
        return final_damage * final_fire_rate
    
    def calculate_effective_range(self, effects: Dict, tradeoffs: Dict) -> float:
        """Calculate effective range with mutations"""
        range_mult = effects.get('rangeMultiplier', 1.0)
        range_penalty = tradeoffs.get('rangePenalty', 0.0)
        
        return self.base_range * range_mult * (1.0 - range_penalty)
    
    def calculate_accuracy(self, effects: Dict, tradeoffs: Dict) -> float:
        """Calculate accuracy (0-1) with mutations"""
        accuracy_mult = effects.get('accuracyMultiplier', 1.0)
        accuracy_penalty = tradeoffs.get('accuracyPenalty', 0.0)
        recoil = tradeoffs.get('recoilIncrease', 0.0)
        
        base_accuracy = 0.8  # Assume 80% base accuracy
        final_accuracy = base_accuracy * accuracy_mult * (1.0 - accuracy_penalty) * (1.0 - recoil)
        
        return max(0.0, min(1.0, final_accuracy))

class MutationBalanceAnalyzer:
    """Analyzes mutation combinations for balance issues"""
    
    def __init__(self, system: WeaponMutationSystem):
        self.system = system
        self.simulator = MutationSimulator()
    
    def analyze_all_combinations(self) -> List[Dict]:
        """Analyze all possible 2-mutation combinations"""
        mutations = list(self.system.mutations.keys())
        results = []
        
        for i, mut1_id in enumerate(mutations):
            for mut2_id in mutations[i+1:]:
                # Check compatibility
                mut1 = self.system.get_mutation(mut1_id)
                mut2 = self.system.get_mutation(mut2_id)
                
                if not mut1 or not mut2:
                    continue
                
                compatible, reason = mut1.is_compatible_with(mut2)
                if not compatible:
                    continue
                
                # Apply mutations
                mutations_list, effects, instability = self.system.apply_mutation([mut1_id], mut2_id)
                
                # Calculate stats
                tradeoffs = effects.get('tradeoffs', {})
                dps = self.simulator.calculate_dps(effects, tradeoffs)
                base_dps = self.simulator.calculate_dps({}, {})
                dps_change = (dps / base_dps - 1.0) * 100
                
                range_val = self.simulator.calculate_effective_range(effects, tradeoffs)
                base_range = self.simulator.base_range
                range_change = (range_val / base_range - 1.0) * 100
                
                accuracy = self.simulator.calculate_accuracy(effects, tradeoffs)
                
                results.append({
                    'mutations': mutations_list,
                    'mut1_name': mut1.name,
                    'mut2_name': mut2.name,
                    'tier1': mut1.tier,
                    'tier2': mut2.tier,
                    'dps': dps,
                    'dps_change_percent': dps_change,
                    'range': range_val,
                    'range_change_percent': range_change,
                    'accuracy': accuracy,
                    'instability': instability,
                    'effects': effects,
                    'tradeoffs': tradeoffs
                })
        
        return results
    
    def find_dominant_combos(self, results: List[Dict], threshold: float = 30.0) -> List[Dict]:
        """Find combinations that outperform baseline by threshold%"""
        dominant = []
        
        for result in results:
            if result['dps_change_percent'] > threshold:
                dominant.append(result)
        
        return sorted(dominant, key=lambda x: x['dps_change_percent'], reverse=True)
    
    def find_underpowered_combos(self, results: List[Dict], threshold: float = -20.0) -> List[Dict]:
        """Find combinations that underperform baseline"""
        underpowered = []
        
        for result in results:
            if result['dps_change_percent'] < threshold:
                underpowered.append(result)
        
        return sorted(underpowered, key=lambda x: x['dps_change_percent'])
    
    def analyze_tier_balance(self, results: List[Dict]) -> Dict:
        """Analyze balance across mutation tiers"""
        tier_stats = {
            'minor_minor': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0},
            'minor_major': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0},
            'minor_corrupt': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0},
            'major_major': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0},
            'major_corrupt': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0},
            'corrupt_corrupt': {'count': 0, 'avg_dps_change': 0.0, 'avg_instability': 0.0}
        }
        
        for result in results:
            tier_combo = f"{result['tier1']}_{result['tier2']}"
            if tier_combo in tier_stats:
                stats = tier_stats[tier_combo]
                stats['count'] += 1
                stats['avg_dps_change'] += result['dps_change_percent']
                stats['avg_instability'] += result['instability']
        
        # Calculate averages
        for combo, stats in tier_stats.items():
            if stats['count'] > 0:
                stats['avg_dps_change'] /= stats['count']
                stats['avg_instability'] /= stats['count']
        
        return tier_stats
    
    def generate_balance_report(self, output_path: str = None) -> str:
        """Generate comprehensive balance report"""
        results = self.analyze_all_combinations()
        dominant = self.find_dominant_combos(results)
        underpowered = self.find_underpowered_combos(results)
        tier_balance = self.analyze_tier_balance(results)
        
        report = []
        report.append("=" * 80)
        report.append("WEAPON MUTATION BALANCE REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Total Combinations Analyzed: {len(results)}")
        report.append("")
        
        # Dominant combos
        report.append("DOMINANT COMBINATIONS (>30% DPS increase)")
        report.append("-" * 80)
        if dominant:
            for combo in dominant[:10]:  # Top 10
                report.append(f"{combo['mut1_name']} + {combo['mut2_name']}")
                report.append(f"  DPS Change: +{combo['dps_change_percent']:.1f}%")
                report.append(f"  Instability: {combo['instability']}")
                report.append(f"  Tiers: {combo['tier1']} + {combo['tier2']}")
                report.append("")
        else:
            report.append("No dominant combinations found (good!)")
            report.append("")
        
        # Underpowered combos
        report.append("UNDERPOWERED COMBINATIONS (<-20% DPS)")
        report.append("-" * 80)
        if underpowered:
            for combo in underpowered[:10]:  # Bottom 10
                report.append(f"{combo['mut1_name']} + {combo['mut2_name']}")
                report.append(f"  DPS Change: {combo['dps_change_percent']:.1f}%")
                report.append(f"  Instability: {combo['instability']}")
                report.append("")
        else:
            report.append("No severely underpowered combinations")
            report.append("")
        
        # Tier balance
        report.append("TIER BALANCE ANALYSIS")
        report.append("-" * 80)
        for combo, stats in tier_balance.items():
            if stats['count'] > 0:
                report.append(f"{combo.upper()}:")
                report.append(f"  Combinations: {stats['count']}")
                report.append(f"  Avg DPS Change: {stats['avg_dps_change']:.1f}%")
                report.append(f"  Avg Instability: {stats['avg_instability']:.1f}")
                report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 80)
        if dominant:
            report.append("⚠️  WARNING: Found dominant combinations that may need balancing:")
            for combo in dominant[:5]:
                report.append(f"  - {combo['mut1_name']} + {combo['mut2_name']} (+{combo['dps_change_percent']:.1f}%)")
            report.append("")
            report.append("  Consider:")
            report.append("  - Increasing tradeoffs for dominant mutations")
            report.append("  - Adding conflicts between overpowered pairs")
            report.append("  - Adjusting diminishing returns curve")
            report.append("")
        
        if len(underpowered) > len(results) * 0.3:
            report.append("⚠️  WARNING: Many underpowered combinations found")
            report.append("  Consider buffing mutations or reducing tradeoffs")
            report.append("")
        
        report.append("✅ Balance targets:")
        report.append("  - No combo should exceed +30% DPS without significant downsides")
        report.append("  - Average DPS change should be near 0% (sidegrade focus)")
        report.append("  - Instability should scale with power")
        report.append("")
        
        report_text = "\n".join(report)
        
        if output_path:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Balance report saved: {output_path}")
        
        return report_text

def main():
    """Run balance analysis"""
    import sys
    
    registry_path = sys.argv[1] if len(sys.argv) > 1 else "weapon_mutation_example.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "balance_report.txt"
    
    print("Loading mutation system...")
    system = WeaponMutationSystem(registry_path)
    
    print("Analyzing mutation combinations...")
    analyzer = MutationBalanceAnalyzer(system)
    
    print("Generating balance report...")
    report = analyzer.generate_balance_report(output_path)
    
    # Print report (handle encoding for Windows console)
    try:
        print("\n" + report)
    except UnicodeEncodeError:
        print("\nBalance report generated successfully!")
        print(f"See full report at: {output_path}")

if __name__ == "__main__":
    main()

