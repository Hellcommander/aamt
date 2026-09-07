#!/usr/bin/env python3
"""Keep a unique amplifier set per custom skill so schools do not share a generic kit.

Shared "Stamina Cost Reduction" / damage-type conversions / execute / leech clones
are dropped. Each school keeps only the supports that sell its loop.
"""

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
    remove_amplifier,
    save_spec,
    write_mod,
)
from s2_validate import format_issues, validate_spec  # noqa: E402

# Wet apply/detonate/consume, hydraulic cut, undertow, brine thorns.
AQUAMANCY = {
    "aquamancy_pinprick_bleed_support",
    "aquamancy_dewfall_support",
    "aquamancy_soaked_ground_support",
    "aquamancy_water_power",
    "aquamancy_hydraulic_laceration",
    "aquamancy_crushing_current",
    "aquamancy_saturation_burst_support",
    "aquamancy_undertow_support",
    "aquamancy_mistguard_support",
    "aquamancy_flow_swap_support",
    "aquamancy_hydrostatic_sustain_support",
    "aquamancy_tidal_expansion_support",
    "aquamancy_brine_thorns",
    "aquamancy_riptide_detonation",
    "aquamancy_maelstrom_socket",
}

# Hemorrhage, execute, siphon, Hypertension consume. No knockback/fear clones.
SANGUIMANCY = {
    "sanguimancy_support_vein_tap",
    "sanguimancy_support_organ_weakening",
    "sanguimancy_support_blood_lock",
    "sanguimancy_support_arterial_siphon",
    "sanguimancy_support_cascade_hemorrhage",
    "sanguimancy_support_execute_focus",
    "sanguimancy_support_rupture_mastery",
    "sanguimancy_support_vascular_lock",
    "sanguimancy_support_fortitude_weave",
    "sanguimancy_hypertensive_burst",
    "sanguimancy_hypertensive_collapse",
    "sanguimancy_support_systolic_reservoir",
}

# Meteor payloads + Charge/Gravity consume. Cosmic owns damage-type conversion.
COSMIC = {
    "cosmic_magic_molten_descent",
    "cosmic_magic_shattering_impact",
    "cosmic_magic_astral_infusion",
    "cosmic_magic_unleash_charge",
    "cosmic_magic_gravity_collapse",
    "cosmic_magic_cryo_comet",
    "cosmic_magic_thunderstrike_meteors",
    "cosmic_magic_voidfall",
    "cosmic_magic_orbital_velocity",
    "cosmic_magic_event_tide",
    "cosmic_magic_gravitational_shear",
    "cosmic_magic_cosmic_inflation",
}

# Corrosion/Catalysis, puddles, reagent consume. No meteor conversions or execute.
ACID = {
    "acid_magic_corrosive_coating",
    "acid_magic_fuming_mixture",
    "acid_magic_unleash_catalysis",
    "acid_magic_catalyst_amp",
    "acid_magic_volatile_catalyst",
    "acid_magic_runaway_reaction",
    "acid_magic_residual_pool",
    "acid_magic_neutralizing_salts",
    "acid_magic_aqua_regia",
    "acid_magic_oleum",
    "acid_magic_flesh_solvent",
    "acid_magic_alkali_crash",
    "acid_magic_acidaras_brand",
    "acid_magic_lung_burn",
}

# Knockback into walls, Momentum, Shear consume. Wind owns collision.
WIND = {
    "wind_magic_shear_edge",
    "wind_magic_wall_collision",
    "wind_magic_unleash_momentum",
    "wind_magic_gale_reach",
    "wind_magic_sustained_cell",
    "wind_magic_pierce_winds",
    "wind_magic_collapse_shear",
    "wind_magic_overpressure",
}

KEEP = {
    "aquamancy": AQUAMANCY,
    "sanguimancy": SANGUIMANCY,
    "cosmic_magic": COSMIC,
    "acid_magic": ACID,
    "wind_magic": WIND,
}

VERSIONS = {
    "aquamancy": ("2.6.0", "Hydromancy: pressurized cuts, Wet detonations, undertow, brine thorns, and Wet-consume supports."),
    "sanguimancy": ("2.6.0", "Sanguimancy: hemorrhage, execute scaling, Hypertension consume, Pulse Pact melee, and a Sanguine Collegium."),
    "cosmic_magic": ("1.6.0", "Cosmic Magic: meteor payloads (fire, holy, frost, lightning, death), Cosmic Charge, Gravity consume, and a Celestial Collegium."),
    "acid_magic": ("1.3.0", "Acid Magic: Corrosion, Catalysis, reagent consume, acid pools, and Acidara silence. No borrowed meteor conversions."),
    "wind_magic": ("1.1.0", "Wind Magic: shear knockback into walls, Momentum, storm cells, and Gale Reach. Collision damage is this school's job."),
}


def condense(spec_id: str) -> None:
    keep = KEEP[spec_id]
    path = output_root() / spec_id / "skill.json"
    spec = load_spec(path)
    have = [str(row.get("id") or "") for row in spec.get("amplifiers") or []]
    missing = sorted(keep - set(have))
    if missing:
        raise SystemExit(f"{spec_id}: keep-list ids not in spec: {missing}")
    dropped = []
    for amp_id in list(have):
        if amp_id not in keep:
            row = remove_amplifier(spec, amp_id)
            dropped.append(f"{amp_id} ({row.get('name')})")
    cycle_images(spec, kinds=["amplifier"])
    version, desc = VERSIONS[spec_id]
    patch_mod_meta(spec, version=version, description=desc)
    save_spec(spec, path)
    issues = validate_spec(spec)
    print(f"--- {spec_id}: kept {len(keep)}, dropped {len(dropped)} ---")
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
