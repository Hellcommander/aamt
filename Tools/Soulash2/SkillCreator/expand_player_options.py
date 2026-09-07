#!/usr/bin/env python3
"""Add build options through the Skill Creator CLI (slots, new nodes, hypertension)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE / "s2_skill_cli.py"


def cli(args: list[str]) -> None:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(HERE),
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)


def aquamancy() -> None:
    cli(
        [
            "set-skill",
            "--id",
            "aquamancy",
            "--version",
            "2.2.0",
            "--mod-description",
            "Hydromancy: pressurized cuts, Wet detonations, Tide Pact melee, brine tanking, and slottable flow supports.",
            "--description",
            "Pressure-and-flow water magic. Socket laceration, saturation, or mist supports. Tide Pact turns every weapon swing into a Water Bolt.\n\nLevels 1–10 grant abilities and supports only; stat points begin at 11.\n\nYou can train this skill by using abilities.",
        ]
    )
    for ability, off, de, util in [
        ("aquamancy_water_splash", 2, None, 2),
        ("aquamancy_water_bolt", 2, None, 2),
        ("aquamancy_water_jet", 2, None, 2),
        ("aquamancy_geyser_burst", 2, None, 2),
        ("aquamancy_pressure_lance", 2, None, 2),
        ("aquamancy_water_barrage", 2, None, 2),
        ("aquamancy_whirlpool_blast", 2, None, 2),
        ("aquamancy_tidal_wave", 2, None, 2),
        ("aquamancy_waterfall_blast", 2, None, 2),
        ("aquamancy_deluge", 2, None, 2),
        ("aquamancy_water_shield", None, 2, 2),
        ("aquamancy_mistform", None, 2, 2),
        ("aquamancy_splash_step", 1, None, 3),
    ]:
        args = ["set-slots", "--id", "aquamancy", "--ability", ability]
        if off is not None:
            args += ["--offensive", str(off)]
        if de is not None:
            args += ["--defensive", str(de)]
        if util is not None:
            args += ["--utility", str(util)]
        cli(args)

    cli(
        [
            "add-ability",
            "--id",
            "aquamancy",
            "--ability-name",
            "Riptide",
            "--unlock-level",
            "10",
            "--target",
            "health",
            "--range",
            "6",
            "--stamina",
            "6",
            "--cooldown",
            "4",
            "--cast-time",
            "0.6",
            "--damage",
            "[4,8]",
            "--damage-type",
            "physical",
            "--stacker",
            "aquamancy_wet",
            "--stacker-count",
            "1",
            "--animation",
            "aquamancy_water_bolt_fx",
            "--effect",
            "chain=2",
            "--effect",
            "magic_power_damage=0.9",
            "--description",
            "A leaping jet that chains to 2 nearby foes. Deals ::damage ::damage_type and soaks them with Wet.",
        ]
    )
    cli(["set-slots", "--id", "aquamancy", "--ability", "aquamancy_riptide", "--offensive", "2", "--utility", "2"])

    cli(
        [
            "add-ability",
            "--id",
            "aquamancy",
            "--ability-name",
            "Brine Skin",
            "--unlock-level",
            "18",
            "--target",
            "self",
            "--range",
            "0",
            "--stamina",
            "7",
            "--cooldown",
            "22",
            "--duration",
            "8",
            "--animation",
            "aquamancy_water_shield_fx",
            "--effect",
            "thorns=8",
            "--effect",
            "damage_reduce=4",
            "--description",
            "Crust yourself in saltwater: thorns and flat damage reduction for ::duration turns.",
        ]
    )
    cli(
        [
            "set-slots",
            "--id",
            "aquamancy",
            "--ability",
            "aquamancy_brine_skin",
            "--offensive",
            "0",
            "--defensive",
            "2",
            "--utility",
            "2",
        ]
    )

    cli(
        [
            "add-ability",
            "--id",
            "aquamancy",
            "--ability-name",
            "Flood Step",
            "--unlock-level",
            "47",
            "--target",
            "tile",
            "--range",
            "6",
            "--stamina",
            "5",
            "--cooldown",
            "4",
            "--cast-time",
            "0.3",
            "--animation",
            "65",
            "--effect",
            "lunge=1",
            "--stacker",
            "aquamancy_wet",
            "--stacker-count",
            "1",
            "--description",
            "Surge through a flood-gate to a visible tile and soak the landing.",
        ]
    )
    cli(["set-slots", "--id", "aquamancy", "--ability", "aquamancy_flood_step", "--offensive", "1", "--utility", "3"])

    cli(
        [
            "add-amplifier",
            "--id",
            "aquamancy",
            "--name",
            "Brine Thorns",
            "--type",
            "defensive",
            "--bonus",
            "thorns=6",
            "--unlock-level",
            "17",
            "--description",
            "Salt crust on a ward. +6 thorns.",
        ]
    )
    cli(
        [
            "add-amplifier",
            "--id",
            "aquamancy",
            "--name",
            "Icy Bind",
            "--type",
            "utility",
            "--bonus",
            "stacker=core_2_freeze:1",
            "--unlock-level",
            "33",
            "--description",
            "The jet flash-freezes. Apply Freeze.",
        ]
    )
    cli(
        [
            "add-amplifier",
            "--id",
            "aquamancy",
            "--name",
            "Cresting Wave",
            "--type",
            "offensive",
            "--bonus",
            "aoe_range=1",
            "--bonus",
            "knockback=1",
            "--unlock-level",
            "47",
            "--description",
            "Widen the flood and shove.",
        ]
    )
    cli(
        [
            "add-passive",
            "--id",
            "aquamancy",
            "--name",
            "Ebb and Flow",
            "--effect",
            "regeneration=3",
            "--effect",
            "dodge=0.1",
            "--unlock-level",
            "25",
        ]
    )
    cli(
        [
            "add-passive",
            "--id",
            "aquamancy",
            "--name",
            "Tide Pact",
            "--effect",
            "on_attack_cast=aquamancy_water_bolt:1.0",
            "--unlock-level",
            "47",
        ]
    )


def sanguimancy() -> None:
    cli(
        [
            "set-skill",
            "--id",
            "sanguimancy",
            "--version",
            "2.2.0",
            "--mod-description",
            "Hemohydraulics: hemorrhage, Hypertension stacks, execute scaling, Pulse Pact melee, and blood-ward thorns.",
            "--description",
            "Hydraulic blood magic. Build Hypertension then dump it, or socket execute and cascade supports. Pulse Pact fires Pressure Spike on every weapon attack.\n\nLevels 1–10 grant abilities and supports only; stat points begin at 11.\n\nYou can train this skill by using abilities.",
        ]
    )
    for ability, off, de, util in [
        ("sanguimancy_pressure_spike", 2, None, 2),
        ("sanguimancy_vein_burst", 2, None, 2),
        ("sanguimancy_sanguine_channel", 2, None, 2),
        ("sanguimancy_contagious_rupture", 2, None, 2),
        ("sanguimancy_organ_crush", 2, None, 2),
        ("sanguimancy_systolic_surge", 2, None, 2),
        ("sanguimancy_blood_hammer", 2, None, 2),
        ("sanguimancy_heart_implosion", 2, None, 2),
        ("sanguimancy_bloodward", None, 2, 2),
        ("sanguimancy_hypertensive_field", 2, None, 2),
    ]:
        args = ["set-slots", "--id", "sanguimancy", "--ability", ability]
        if off is not None:
            args += ["--offensive", str(off)]
        if de is not None:
            args += ["--defensive", str(de)]
        if util is not None:
            args += ["--utility", str(util)]
        cli(args)

    cli(
        [
            "add-stacker",
            "--id",
            "sanguimancy",
            "--name",
            "Hypertension",
            "--effect",
            "movement_speed=0.015",
            "--max-stacks",
            "15",
            "--duration",
            "4",
            "--description",
            "Spiking blood pressure slows movement. Dump stacks with Pressure Dump.",
        ]
    )
    cli(
        [
            "set-ability",
            "--id",
            "sanguimancy",
            "--ability",
            "sanguimancy_pressure_spike",
            "--effect",
            "stacker=sanguimancy_hypertension",
            "--effect",
            "stacker_count=1",
        ]
    )
    cli(
        [
            "set-ability",
            "--id",
            "sanguimancy",
            "--ability",
            "sanguimancy_hypertensive_field",
            "--effect",
            "stacker=sanguimancy_hypertension",
            "--effect",
            "stacker_count=2",
        ]
    )
    cli(
        [
            "set-ability",
            "--id",
            "sanguimancy",
            "--ability",
            "sanguimancy_systolic_surge",
            "--effect",
            "stacker=sanguimancy_hypertension",
            "--effect",
            "stacker_count=1",
        ]
    )

    cli(
        [
            "add-ability",
            "--id",
            "sanguimancy",
            "--ability-name",
            "Blood Step",
            "--unlock-level",
            "16",
            "--target",
            "tile",
            "--range",
            "5",
            "--stamina",
            "6",
            "--cooldown",
            "6",
            "--cast-time",
            "0.3",
            "--animation",
            "65",
            "--damage",
            "[3,6]",
            "--damage-type",
            "physical",
            "--effect",
            "lunge=1",
            "--effect",
            "bleed=6",
            "--effect",
            "magic_power_damage=0.7",
            "--description",
            "Lunge through a burst vessel to a tile. Deals ::damage ::damage_type and a light hemorrhage.",
        ]
    )
    cli(["set-slots", "--id", "sanguimancy", "--ability", "sanguimancy_blood_step", "--offensive", "1", "--utility", "3"])

    cli(
        [
            "add-ability",
            "--id",
            "sanguimancy",
            "--ability-name",
            "Pressure Dump",
            "--unlock-level",
            "22",
            "--target",
            "aoe_tile",
            "--range",
            "5",
            "--stamina",
            "8",
            "--cooldown",
            "10",
            "--cast-time",
            "0.75",
            "--animation",
            "sanguimancy_vein_burst_fx",
            "--damage",
            "[8,14]",
            "--damage-type",
            "physical",
            "--stacker",
            "sanguimancy_hypertension",
            "--stacker-count",
            "1",
            "--effect",
            "aoe_range=2",
            "--effect",
            "damage_per_stacks=2",
            "--effect",
            "magic_power_damage=1.1",
            "--description",
            "Dump built Hypertension. Deals ::damage ::damage_type plus bonus damage per Hypertension stack.",
        ]
    )
    cli(["set-slots", "--id", "sanguimancy", "--ability", "sanguimancy_pressure_dump", "--offensive", "2", "--utility", "2"])

    cli(
        [
            "add-ability",
            "--id",
            "sanguimancy",
            "--ability-name",
            "Crimson Veil",
            "--unlock-level",
            "34",
            "--target",
            "self",
            "--range",
            "0",
            "--stamina",
            "8",
            "--cooldown",
            "18",
            "--duration",
            "3",
            "--animation",
            "sanguimancy_bloodward_fx",
            "--effect",
            "hide=1",
            "--effect",
            "damage_reduce_percent=12.0",
            "--description",
            "Drown your outline in blood-mist. Hidden and reduced damage for ::duration turns.",
        ]
    )
    cli(
        [
            "set-slots",
            "--id",
            "sanguimancy",
            "--ability",
            "sanguimancy_crimson_veil",
            "--offensive",
            "0",
            "--defensive",
            "2",
            "--utility",
            "2",
        ]
    )

    cli(
        [
            "add-amplifier",
            "--id",
            "sanguimancy",
            "--name",
            "Hypertensive Burst",
            "--type",
            "offensive",
            "--bonus",
            "damage_per_stacks=2",
            "--unlock-level",
            "22",
            "--description",
            "Detonate Hypertension on any hooked ability. +2 damage per stack.",
        ]
    )
    cli(
        [
            "add-amplifier",
            "--id",
            "sanguimancy",
            "--name",
            "Vein Leap",
            "--type",
            "utility",
            "--range",
            "2",
            "--unlock-level",
            "16",
            "--description",
            "+2 range. Pairs with Blood Step and spikes.",
        ]
    )
    cli(
        [
            "add-passive",
            "--id",
            "sanguimancy",
            "--name",
            "Pulse Pact",
            "--effect",
            "on_attack_cast=sanguimancy_pressure_spike:1.0",
            "--unlock-level",
            "21",
        ]
    )
    cli(
        [
            "add-passive",
            "--id",
            "sanguimancy",
            "--name",
            "Bloodthirst",
            "--effect",
            "heal_on_kill=0.04",
            "--unlock-level",
            "25",
        ]
    )
    cli(
        [
            "add-passive",
            "--id",
            "sanguimancy",
            "--name",
            "Butcher's Calm",
            "--effect",
            "critical_hit=0.1",
            "--effect",
            "parry=2",
            "--unlock-level",
            "39",
        ]
    )


def main() -> int:
    aquamancy()
    sanguimancy()
    for spec_id in ("aquamancy", "sanguimancy"):
        cli(["validate", "--id", spec_id])
        cli(["write", "--id", spec_id])
        cli(["install", "--id", spec_id, "--yes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
