#!/usr/bin/env python3
"""Differentiate amplifiers, add Wet/bleed payoffs, and scale late nodes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from s2_paths import output_root  # noqa: E402

CLI = HERE / "s2_skill_cli.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cli(args: list[str]) -> None:
    proc = subprocess.run([sys.executable, str(CLI), *args], cwd=str(HERE), capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)


def amp(spec, aid: str) -> dict:
    for row in spec["amplifiers"]:
        if row["id"] == aid:
            return row
    raise KeyError(aid)


def ability(spec, aid: str) -> dict:
    for row in spec["abilities"]:
        if row["id"] == aid:
            return row
    raise KeyError(aid)


def passive(spec, aid: str) -> dict:
    for row in spec["passives"]:
        if row["id"] == aid:
            return row
    raise KeyError(aid)


def paint(items: list) -> None:
    for i, row in enumerate(items):
        row["image"] = i % 8


def apply_amp(spec: dict, sid: str, bonuses, extra: dict, desc: str) -> None:
    row = amp(spec, sid)
    if bonuses is not None:
        row["bonuses"] = bonuses
    row["description"] = desc
    for k, v in extra.items():
        row[k] = v


def improve_aquamancy(spec: dict) -> None:
    spec["mod"]["version"] = "2.1.0"
    spec["mod"]["description"] = (
        "Hydromancy rebuilt through Skill Creator: pressurized cuts, Wet detonations, "
        "skill-scaling pressure supports, and slottable flow amplifiers."
    )
    for sid, bonuses, extra, desc in [
        ("aquamancy_pinprick_bleed_support", [{"effect": "bleed", "value": 8}], {}, "A thin hydraulic nick. +8 bleed."),
        ("aquamancy_novice_razorflow_support", [{"effect": "bleed", "value": 10}], {}, "Sharpen the jet. +10 bleed."),
        ("aquamancy_minor_laceration_support", [{"effect": "bleed", "value": 16}], {}, "A deeper cut. +16 bleed."),
        ("aquamancy_razorflow_support", [{"effect": "bleed", "value": 18}], {}, "Razor water. +18 bleed."),
        (
            "aquamancy_hydraulic_laceration",
            [{"effect": "bleed", "value": 22}, {"effect": "pierce", "value": 1}],
            {},
            "Pressurized slice that ignores armor and bleeds.",
        ),
        (
            "aquamancy_hemorrhaging_flow_support",
            [{"effect": "bleed", "value": 20}, {"effect": "pierce", "value": 1}],
            {},
            "Open arteries. Bleed and pierce.",
        ),
        ("aquamancy_weak_pressure_support", [{"effect": "damage", "value": [1, 1]}], {}, "A little extra force. +1 damage."),
        ("aquamancy_water_power", [{"effect": "skill_level_damage", "value": 0.5}], {}, "Damage grows with Hydromancy level."),
        ("aquamancy_pressure_surge_support", [{"effect": "skill_level_damage", "value": 0.35}], {}, "Pressure scales with skill level."),
        (
            "aquamancy_pressure_overload_support",
            [{"effect": "skill_level_damage", "value": 0.5}, {"effect": "knockback", "value": 1}],
            {},
            "Late-game force: skill scaling and knockback.",
        ),
        ("aquamancy_dewfall_support", [{"effect": "stacker_count", "value": 1}], {}, "Apply 1 extra Wet."),
        ("aquamancy_spray_saturation_support", [{"effect": "stacker_count", "value": 1}], {}, "Apply 1 extra Wet."),
        ("aquamancy_soaked_ground_support", [{"effect": "stacker_count", "value": 2}], {}, "Drench the target. +2 Wet."),
        ("aquamancy_saturation_burst_support", [{"effect": "damage_per_stacks", "value": 2}], {}, "Detonate Wet: +2 damage per stack."),
        ("aquamancy_mist_saturation_support", [{"effect": "aoe_range", "value": 1}], {}, "Mist spreads the effect one tile farther."),
        ("aquamancy_pressure_break_support", [{"effect": "knockback", "value": 1}], {}, "A sharp shove."),
        ("aquamancy_crushing_current", [{"effect": "knockback", "value": 2}], {}, "A heavy hydraulic shove."),
        (
            "aquamancy_hydraulic_impact_support",
            [{"effect": "knockback", "value": 1}, {"effect": "damage", "value": [2, 2]}],
            {},
            "Impact damage and knockback.",
        ),
        ("aquamancy_flow_swap_support", [{"effect": "chain", "value": 2}], {}, "The current leaps to two nearby foes."),
        ("aquamancy_soothing_flow_support", [{"effect": "damage_as_life", "value": 0.04}], {}, "Return 4% of damage as health."),
        ("aquamancy_mistguard_support", [{"effect": "damage_reduce", "value": 5}], {}, "A film of mist. +5 damage reduction."),
        ("aquamancy_mist_screen_support", [{"effect": "damage_reduce", "value": 6}], {}, "A late mist wall. +6 damage reduction."),
        ("aquamancy_dampening_barrier_support", [{"effect": "damage_reduce_percent", "value": 8.0}], {}, "Soak incoming hits. 8% less damage."),
        ("aquamancy_tidal_expansion_support", [{"effect": "aoe_range", "value": 1}], {}, "Widen the flood by 1 tile."),
        ("aquamancy_deluge_compression_support", [{"effect": "aoe_range", "value": 1}], {}, "Compress and widen the deluge."),
        ("aquamancy_gentle_pull_support", [{"effect": "pull_target", "value": 1}], {}, "Draw the target one tile closer."),
        ("aquamancy_undertow_support", [{"effect": "pull_target", "value": 2}], {}, "A stronger undertow. Pull 2 tiles."),
        ("aquamancy_slowing_surge_support", [{"effect": "immobilize", "value": 1}], {}, "Lock footing in the surge."),
        ("aquamancy_current_step_support", [{"effect": "movement_speed", "value": 0.05}], {}, "The current drags at their feet."),
        ("aquamancy_ripple_cast_support", None, {}, "Cast a tenth of a turn faster."),
        ("aquamancy_trickle_extension_support", None, {}, "+1 range."),
        ("aquamancy_novice_flow_efficiency_support", None, {}, "Spend 1 less stamina."),
        ("aquamancy_tidal_extension_support", None, {}, "+2 range."),
        ("aquamancy_flow_efficiency_support", None, {}, "Spend 2 less stamina."),
        ("aquamancy_flow_compression_support", None, {}, "Cooldown reduced by 1."),
        ("aquamancy_hydrostatic_sustain_support", None, {}, "Buffs and summons last 1 turn longer."),
        ("aquamancy_hydraulic_veins_support", None, {}, "Open the pipes. Spend 2 less stamina."),
        ("aquamancy_flow_echo_support", None, {}, "Cooldown reduced by 2."),
    ]:
        apply_amp(spec, sid, bonuses, extra, desc)

    fog = ability(spec, "aquamancy_fog_bank")
    fog["effects"]["summon_count"] = 16
    fog["effects"]["stacker_count"] = 1
    fog.setdefault("effects_keys", {})["stacker"] = "aquamancy_wet"
    fog["description"] = "Conjure a bank of fog that soaks the field with Wet. Lasts ::duration turns."

    whirl = ability(spec, "aquamancy_whirlpool_blast")
    whirl["description"] = (
        "Detonate a whirlpool. Deals ::damage ::damage_type plus bonus damage per Wet stack."
    )

    shield = ability(spec, "aquamancy_water_shield")
    shield["effects"]["damage_reduce"] = 6
    shield["description"] = (
        "Wrap yourself in flowing water: percent DR and +6 damage reduction for ::duration turns."
    )

    tidal = ability(spec, "aquamancy_tidal_wave")
    tidal["animation"] = "aquamancy_deluge_fx"
    tidal["description"] = (
        "A wide surge of water dealing ::damage ::damage_type damage, knocking foes back, and soaking them with Wet."
    )

    rain = ability(spec, "aquamancy_rainstorm")
    rain["animation"] = "aquamancy_fog_bank_fx"

    for p_id, effects in [
        (
            "aquamancy_fluid_body",
            [
                {"effect": "damage_type_reduction", "value": "physical", "secondary_value": 0.1},
                {"effect": "dodge", "value": 0.1},
            ],
        ),
        (
            "aquamancy_pressurized_core",
            [
                {"effect": "bonus_damage", "value": 2, "secondary_value": "physical"},
                {"effect": "hit_bonus", "value": 1},
            ],
        ),
        (
            "aquamancy_hydrostatic_pressure",
            [{"effect": "bonus_damage", "value": 3, "secondary_value": "physical"}],
        ),
    ]:
        passive(spec, p_id)["effects"] = effects

    wet = spec["stackers"][0]
    wet["duration"] = 5
    wet["max_stacks"] = 20
    wet["description"] = "Wet slows movement. Spend stacks with whirlpools, steam, and saturation supports."

    paint(spec["abilities"])
    paint(spec["amplifiers"])
    paint(spec["passives"])


def improve_sanguimancy(spec: dict) -> None:
    spec["mod"]["version"] = "2.1.0"
    spec["mod"]["description"] = (
        "Hemohydraulics rebuilt through Skill Creator: hemorrhage, execute scaling, "
        "chaining ruptures, and blood-ward thorns."
    )
    for sid, bonuses, extra, desc in [
        ("sanguimancy_support_vein_tap", [{"effect": "bleed", "value": 12}], {}, "Tap a vein. +12 bleed."),
        ("sanguimancy_support_rupture_focus", [{"effect": "bleed", "value": 15}], {}, "+15 bleed."),
        ("sanguimancy_support_hemorrhage", [{"effect": "bleed", "value": 16}], {}, "+16 bleed."),
        ("sanguimancy_support_thrombotic_surge", [{"effect": "bleed", "value": 16}], {}, "Clots then bursts. +16 bleed."),
        ("sanguimancy_support_arterial_wilt", [{"effect": "bleed", "value": 20}], {}, "Wilt an artery. +20 bleed."),
        (
            "sanguimancy_support_cascade_hemorrhage",
            [{"effect": "bleed", "value": 12}, {"effect": "chain", "value": 2}],
            {},
            "Bleed that jumps to two nearby bodies.",
        ),
        (
            "sanguimancy_support_cascade_amplification",
            [{"effect": "bleed", "value": 10}, {"effect": "chain", "value": 2}],
            {},
            "Spread the rupture to two nearby foes.",
        ),
        ("sanguimancy_support_rupture_amplification", [{"effect": "bleed", "value": 22}], {}, "+22 bleed."),
        (
            "sanguimancy_support_rupture_mastery",
            [{"effect": "bleed", "value": 22}, {"effect": "pierce", "value": 1}],
            {},
            "Mastered rupture: bleed and pierce.",
        ),
        ("sanguimancy_support_internal_pressure", [{"effect": "damage", "value": [2, 2]}], {}, "+2 damage."),
        (
            "sanguimancy_support_systolic_overload",
            [{"effect": "skill_level_damage", "value": 0.25}],
            {},
            "Scales with Hemohydraulics.",
        ),
        ("sanguimancy_support_hammer_focus", [{"effect": "skill_level_damage", "value": 0.3}], {}, "Blood-hammer scaling."),
        (
            "sanguimancy_support_visceral_collapse",
            [{"effect": "skill_level_damage", "value": 0.25}, {"effect": "knockback", "value": 1}],
            {},
            "Collapse and shove.",
        ),
        ("sanguimancy_support_organ_weakening", [{"effect": "vulnerable", "value": 1}], {}, "Soften the organ. Apply vulnerable."),
        ("sanguimancy_support_arterial_siphon", [{"effect": "damage_as_life", "value": 0.04}], {}, "Steal 4% of damage as health."),
        (
            "sanguimancy_support_execute_focus",
            [{"effect": "damage_on_missing_health", "value": 0.1}],
            {},
            "Bonus damage vs wounded targets.",
        ),
        (
            "sanguimancy_support_pre_implosion",
            [{"effect": "damage_on_missing_health", "value": 0.1}, {"effect": "pierce", "value": 1}],
            {},
            "Set up the implosion: execute damage and pierce.",
        ),
        (
            "sanguimancy_support_implosion_focus",
            [{"effect": "skill_level_damage", "value": 0.35}, {"effect": "pierce", "value": 1}],
            {},
            "Implosion scaling and pierce.",
        ),
        (
            "sanguimancy_support_grand_mal",
            [{"effect": "stun", "value": 1}, {"effect": "damage", "value": [3, 3]}],
            {},
            "Shock the system. Stun and damage.",
        ),
        (
            "sanguimancy_support_terminal_pressure",
            [{"effect": "skill_level_damage", "value": 0.5}],
            {},
            "Peak pressure. Skill-level damage.",
        ),
        ("sanguimancy_support_blood_rebound", [{"effect": "knockback", "value": 1}], {}, "Rebound the blow."),
        ("sanguimancy_support_pressure_wave", [{"effect": "knockback", "value": 2}], {}, "A wide pressure wave."),
        ("sanguimancy_support_circulatory_choke", [{"effect": "immobilize", "value": 1}], {}, "Pin the circulation."),
        ("sanguimancy_support_blood_lock", [{"effect": "stun", "value": 1}], {}, "Lock the heart a beat. Stun."),
        ("sanguimancy_support_vascular_lock", [{"effect": "immobilize", "value": 1}], {}, "Clamp the vessel."),
        ("sanguimancy_support_ward_stability", [{"effect": "damage_reduce", "value": 4}], {}, "+4 damage reduction on the ward."),
        ("sanguimancy_support_fortitude_weave", [{"effect": "damage_reduce", "value": 6}], {}, "+6 damage reduction."),
        ("sanguimancy_support_pressure_conduit", None, {}, "+1 range."),
        ("sanguimancy_support_pain_response", None, {}, "Cast a tenth of a turn faster."),
        ("sanguimancy_support_systolic_reservoir", None, {}, "Spend 2 less stamina."),
        ("sanguimancy_support_systolic_echo", None, {}, "Cooldown reduced by 1."),
    ]:
        apply_amp(spec, sid, bonuses, extra, desc)

    chan = ability(spec, "sanguimancy_sanguine_channel")
    chan["effects"].pop("heal", None)
    chan["effects"]["damage_as_life"] = 0.4
    chan["description"] = "Siphon pressure. Deals ::damage ::damage_type and steals 40% as health."

    heart = ability(spec, "sanguimancy_heart_implosion")
    heart["effects"]["stun"] = 1.0
    heart["description"] = (
        "Implode the heart for ::damage ::damage_type execute trauma and a stun. Costs health."
    )

    contag = ability(spec, "sanguimancy_contagious_rupture")
    contag["effects"]["chain"] = 2
    contag["effects"]["aoe_range"] = 1
    contag["description"] = (
        "A rupture that spreads and chains to 2 nearby bodies. ::damage ::damage_type and hemorrhage."
    )

    ward = ability(spec, "sanguimancy_bloodward")
    ward["effects"]["thorns"] = 8
    ward["description"] = "Harden vessels: damage reduction and 8 thorns for ::duration turns."

    passive(spec, "sanguimancy_internal_fortitude")["effects"] = [
        {"effect": "damage_negation", "value": "bleed", "secondary_value": 0.1},
        {"effect": "damage_reduce", "value": 3},
    ]
    passive(spec, "sanguimancy_hemorrhagic_cascade")["effects"] = [
        {"effect": "increase_effect_value", "value": "bleed", "secondary_value": 0.15},
        {"effect": "bonus_damage", "value": 1, "secondary_value": "physical"},
    ]

    paint(spec["abilities"])
    paint(spec["amplifiers"])
    paint(spec["passives"])


FX = [
    ("aquamancy", "3", "Water Jet FX", "70,160,220", "aquamancy_water_jet"),
    ("aquamancy", "3", "Water Splash FX", "80,170,230", "aquamancy_water_splash"),
    ("aquamancy", "3", "Whirlpool FX", "50,140,210", "aquamancy_whirlpool_blast"),
    ("aquamancy", "3", "Water Shield FX", "110,190,230", "aquamancy_water_shield"),
    ("sanguimancy", "185", "Sanguine Channel FX", "160,20,30", "sanguimancy_sanguine_channel"),
    ("sanguimancy", "3", "Bloodward FX", "140,16,28", "sanguimancy_bloodward"),
    ("sanguimancy", "185", "Contagious Rupture FX", "170,22,32", "sanguimancy_contagious_rupture"),
    ("sanguimancy", "3", "Systolic Surge FX", "150,18,26", "sanguimancy_systolic_surge"),
    ("sanguimancy", "3", "Blood Hammer FX", "130,12,22", "sanguimancy_blood_hammer"),
]


def main() -> int:
    aqua_path = output_root() / "aquamancy" / "skill.json"
    sang_path = output_root() / "sanguimancy" / "skill.json"
    aqua = load(aqua_path)
    sang = load(sang_path)
    improve_aquamancy(aqua)
    improve_sanguimancy(sang)
    dump(aqua_path, aqua)
    dump(sang_path, sang)

    for spec_id, clone, name, color, bind in FX:
        cli(
            [
                "add-animation",
                "--id",
                spec_id,
                "--clone",
                clone,
                "--name",
                name,
                "--color",
                color,
                "--bind-ability",
                bind,
            ]
        )

    for spec_id in ("aquamancy", "sanguimancy"):
        cli(["validate", "--id", spec_id])
        cli(["write", "--id", spec_id])
        cli(["install", "--id", spec_id, "--yes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
