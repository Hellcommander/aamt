#!/usr/bin/env python3
"""Move passives off the free 1–10 band and make 11+ passives school-loop payoffs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from s2_paths import output_root  # noqa: E402
from s2_skill_spec import (  # noqa: E402
    _upsert_milestone,
    apply_stat_preset,
    find_row,
    load_spec,
    patch_mod_meta,
    save_spec,
    write_mod,
)
from s2_validate import format_issues, validate_spec  # noqa: E402


def fx(effect: str, value: Any, secondary: Any = None, third: Any = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"effect": effect, "value": value}
    if secondary is not None:
        row["secondary_value"] = secondary
    if third is not None:
        row["third_value"] = third
    return row


# id -> (unlock_level, effects). Mastery rows are omitted (stay at 30).
CHANGES: Dict[str, Tuple[str, Dict[str, Tuple[int, List[Dict[str, Any]]]]]] = {
    "aquamancy": (
        "2.8.0",
        {
            "aquamancy_fluid_body": (
                19,
                [fx("on_attack_stack", "aquamancy_wet"), fx("dodge", 0.08)],
            ),
            "aquamancy_ebb_and_flow": (
                25,
                [fx("stamina_on_stack_consume", "aquamancy_wet"), fx("regeneration", 4)],
            ),
            "aquamancy_pressurized_core": (
                38,
                [fx("increase_effect_value", "bleed", 0.2), fx("bonus_damage", 3, "physical")],
            ),
            "aquamancy_soaked_ground": (
                44,
                [fx("increase_effect_value", "aquamancy_wet", 0.2), fx("extra_duration", 0.25)],
            ),
        },
    ),
    "sanguimancy": (
        "2.8.0",
        {
            "sanguimancy_bloodthirst": (
                25,
                [
                    fx("heal_on_kill", 0.1),
                    fx("death_under_effect_gain_health", "bleed", 8),
                    fx("stamina_percent_on_kill", 0.1),
                ],
            ),
            "sanguimancy_hemorrhagic_cascade": (
                36,
                [
                    fx("increase_effect_value", "bleed", 0.25),
                    fx("death_under_effect_gain_stamina", "bleed", 5),
                ],
            ),
            "sanguimancy_internal_fortitude": (
                40,
                [
                    fx("damage_negation", "bleed", 0.25),
                    fx("health_bonus_percent", 0.1),
                    fx("regeneration_low_health", 0.2),
                ],
            ),
        },
    ),
    "cosmic_magic": (
        "1.8.0",
        {
            "cosmic_magic_plasma_wake": (
                14,
                [
                    fx("on_damage_type_stack", "cosmic_magic_cosmic_charge", "fire"),
                    fx("heal_on_damage_type", "fire", 0.2),
                ],
            ),
            "cosmic_magic_star_forged_body": (
                24,
                [
                    fx("on_attack_stack", "cosmic_magic_cosmic_charge"),
                    fx("health_bonus_percent", 0.12),
                    fx("damage_type_reduction", "fire", 0.2),
                ],
            ),
            "cosmic_magic_kinetic_harvest": (
                34,
                [
                    fx("on_damage_type_stack", "cosmic_magic_cosmic_charge", "physical"),
                    fx("stamina_on_stack_consume", "cosmic_magic_cosmic_charge"),
                ],
            ),
            "cosmic_magic_gravitational_mastery": (
                39,
                [
                    fx("target_resistance", "physical", -0.15),
                    fx("on_attack_stack", "cosmic_magic_gravity"),
                ],
            ),
        },
    ),
    "acid_magic": (
        "1.5.0",
        {
            "acid_magic_corrosive_primer": (
                14,
                [fx("on_damage_type_stack", "acid_magic_corrosion", "acid")],
            ),
            "acid_magic_lab_safety": (
                19,
                [
                    fx("heal_on_damage_type", "acid", 0.25),
                    fx("damage_type_reduction", "acid", 0.2),
                ],
            ),
            "acid_magic_acidara_reagent": (
                43,
                [fx("bonus_damage", 3, "acid"), fx("target_resistance", "acid", -0.2)],
            ),
        },
    ),
    "arendeth_baromancy": (
        "1.4.0",
        {
            "arendeth_baromancy_aerodynamic_flow": (
                14,
                [
                    fx("move_speed", -0.1),
                    fx("movement_stamina", -1.0),
                    fx("on_attack_stack", "arendeth_baromancy_momentum"),
                ],
            ),
            "arendeth_baromancy_stormborn_reflexes": (
                24,
                [fx("dodge", 0.1), fx("bonus_attack", 0.1)],
            ),
            "arendeth_baromancy_pressure_mastery": (
                34,
                [fx("bonus_knockback_damage_percent", 0.35)],
            ),
            "arendeth_baromancy_momentum_overflow": (
                46,
                [
                    fx("max_stamina", 15),
                    fx("stamina_on_stack_consume", "arendeth_baromancy_momentum"),
                ],
            ),
        },
    ),
}


def apply_school(spec_id: str) -> None:
    version, rows = CHANGES[spec_id]
    path = output_root() / spec_id / "skill.json"
    spec = load_spec(path)
    apply_stat_preset(spec, "after10")
    print(f"--- {spec_id} ---")
    for pid, (level, effects) in rows.items():
        row = find_row(spec.get("passives") or [], pid, what="Passive")
        old_lv = None
        for mile in spec.get("milestones") or []:
            if mile.get("id") == pid:
                old_lv = (mile.get("requirements") or {}).get("skill")
                break
        row["effects"] = effects
        _upsert_milestone(
            spec,
            mid=pid,
            name=row.get("name") or pid,
            level=level,
            kind="passive",
            reward_id=pid,
        )
        moved = f" L{old_lv}->{level}" if old_lv != level else f" L{level}"
        print(f"  {row.get('name')}{moved}")
    patch_mod_meta(spec, version=version)
    save_spec(spec, path)
    issues = validate_spec(spec)
    print(format_issues(issues))
    if any(i.level == "error" for i in issues):
        raise SystemExit(f"validate failed for {spec_id}")
    write_mod(spec)
    print(f"wrote {spec_id} v{version}")


def main() -> int:
    for spec_id in CHANGES:
        apply_school(spec_id)
    print("Staged only. Did not install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
