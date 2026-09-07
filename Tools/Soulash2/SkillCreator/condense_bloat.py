#!/usr/bin/env python3
"""Cut ability/passive bloat so each school stays unique (Geomancy-sized kits)."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from s2_paths import output_root  # noqa: E402
from s2_skill_spec import (  # noqa: E402
    cycle_images,
    load_spec,
    patch_mod_meta,
    remove_ability,
    remove_passive,
    save_spec,
    write_mod,
)
from s2_validate import format_issues, validate_spec  # noqa: E402

# Wet jets, undertow, brine, one summon, Wet detonate. No freeze/steam/fog clones.
AQUA_ABS = {
    "aquamancy_water_splash",
    "aquamancy_water_bolt",
    "aquamancy_geyser_burst",
    "aquamancy_splash_step",
    "aquamancy_water_jet",
    "aquamancy_riptide",
    "aquamancy_undertow",
    "aquamancy_brine_skin",
    "aquamancy_summon_water_elemental",
    "aquamancy_whirlpool_blast",
    "aquamancy_water_vortex",
    "aquamancy_tidal_wave",
    "aquamancy_mistform",
    "aquamancy_deluge",
}
AQUA_PAS = {
    "aquamancy_mastery",
    "aquamancy_fluid_body",
    "aquamancy_pressurized_core",
    "aquamancy_soaked_ground",
    "aquamancy_tide_pact",
    "aquamancy_ebb_and_flow",
}

# Hemorrhage, Hypertension, execute, siphon. No knockback/hide clones.
SANG_ABS = {
    "sanguimancy_pressure_spike",
    "sanguimancy_capillary_rupture",
    "sanguimancy_sanguine_channel",
    "sanguimancy_hypertensive_field",
    "sanguimancy_circulatory_lock",
    "sanguimancy_blood_step",
    "sanguimancy_pressure_dump",
    "sanguimancy_contagious_rupture",
    "sanguimancy_organ_crush",
    "sanguimancy_bloodward",
    "sanguimancy_heart_implosion",
}
SANG_PAS = {
    "sanguimancy_mastery",
    "sanguimancy_hemorrhagic_cascade",
    "sanguimancy_pulse_pact",
    "sanguimancy_internal_fortitude",
    "sanguimancy_bloodthirst",
}

# Meteors, Charge, Gravity, starfire. Falling Sky needs falling_star + meteor_swarm.
COSMIC_ABS = {
    "cosmic_magic_falling_star",
    "cosmic_magic_gravity_pin",
    "cosmic_magic_stellar_ward",
    "cosmic_magic_astral_step",
    "cosmic_magic_meteorite_slam",
    "cosmic_magic_starfire_lance",
    "cosmic_magic_asteroid_drop",
    "cosmic_magic_event_horizon",
    "cosmic_magic_meteor_swarm",
    "cosmic_magic_planet_cracker",
    "cosmic_magic_collapse_of_reality",
}
COSMIC_PAS = {
    "cosmic_magic_mastery",
    "cosmic_magic_kinetic_harvest",
    "cosmic_magic_plasma_wake",
    "cosmic_magic_falling_sky",
    "cosmic_magic_starcaller_pact",
    "cosmic_magic_star_forged_body",
    "cosmic_magic_gravitational_mastery",
}

# Corrosion, puddles, armor melt, reagent consume, Acidara silence. Aura trigger is hidden.
ACID_ABS = {
    "acid_magic_acid_dart",
    "acid_magic_etch",
    "acid_magic_alembic_ward",
    "acid_magic_vitriol_infusion",
    "acid_magic_acid_pool",
    "acid_magic_vitriol_step",
    "acid_magic_armor_melt",
    "acid_magic_neutralize",
    "acid_magic_volatile_reaction",
    "acid_magic_acid_gag",
    "acid_magic_fuming_aura",
    "acid_magic_fuming_aura_trigger",
    "acid_magic_hemolysis",
    "acid_magic_total_dissolution",
}
ACID_PAS = {
    "acid_magic_mastery",
    "acid_magic_corrosive_primer",
    "acid_magic_lab_safety",
    "acid_magic_catalytic_wake",
    "acid_magic_chemical_recycling",
    "acid_magic_acidara_reagent",
}

# Knockback into walls, Momentum, one storm kit. Drop extra defense/filler.
WIND_ABS = {
    "wind_magic_air_slice",
    "wind_magic_gust_push",
    "wind_magic_wind_veil",
    "wind_magic_zephyr_step",
    "wind_magic_cyclone_grip",
    "wind_magic_mini_tornado",
    "wind_magic_wind_lance",
    "wind_magic_tempest",
    "wind_magic_eye_of_the_storm",
    "wind_magic_skybreaker",
    "wind_magic_summon_air_elemental",
    "wind_magic_become_air_elemental",
    "wind_magic_summon_storm_elemental",
}
WIND_PAS = {
    "wind_magic_mastery",
    "wind_magic_aerodynamic_flow",
    "wind_magic_stormborn_reflexes",
    "wind_magic_pressure_mastery",
    "wind_magic_momentum_overflow",
}

KEEP = {
    "aquamancy": (AQUA_ABS, AQUA_PAS, "2.7.0"),
    "sanguimancy": (SANG_ABS, SANG_PAS, "2.7.0"),
    "cosmic_magic": (COSMIC_ABS, COSMIC_PAS, "1.7.0"),
    "acid_magic": (ACID_ABS, ACID_PAS, "1.4.0"),
    "wind_magic": (WIND_ABS, WIND_PAS, "1.2.0"),
}


def condense(spec_id: str) -> None:
    keep_abs, keep_pas, version = KEEP[spec_id]
    path = output_root() / spec_id / "skill.json"
    spec = load_spec(path)
    have_abs = [str(row.get("id") or "") for row in spec.get("abilities") or []]
    have_pas = [str(row.get("id") or "") for row in spec.get("passives") or []]
    missing = sorted((keep_abs - set(have_abs)) | (keep_pas - set(have_pas)))
    if missing:
        raise SystemExit(f"{spec_id}: keep-list ids not in spec: {missing}")
    dropped = []
    for aid in list(have_abs):
        if aid not in keep_abs:
            row = remove_ability(spec, aid)
            dropped.append(f"ability {aid} ({row.get('name')})")
    for pid in list(have_pas):
        if pid not in keep_pas:
            row = remove_passive(spec, pid)
            dropped.append(f"passive {pid} ({row.get('name')})")
    cycle_images(spec, kinds=["ability", "passive"])
    patch_mod_meta(spec, version=version)
    save_spec(spec, path)
    issues = validate_spec(spec)
    print(f"--- {spec_id}: abilities {len(have_abs)}->{len(keep_abs)}, passives {len(have_pas)}->{len(keep_pas)} ---")
    for line in dropped:
        print(f"  drop {line}")
    print(format_issues(issues))
    if any(i.level == "error" for i in issues):
        raise SystemExit(f"validate failed for {spec_id}")
    write_mod(spec)
    print(f"wrote {spec_id} v{version}")


def main() -> int:
    for spec_id in KEEP:
        condense(spec_id)
    print("Staged only. Did not install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
