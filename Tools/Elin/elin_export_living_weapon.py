#!/usr/bin/env python3
"""Export Elin Biomagic / Living Weapon system as a portable option pack.

Sources (CustomRaceClassCreator):
  MagicPlus/ArcaneSaturation/   — biomagic living weapons (sentience, hunger, mutation…)
  MagicPlus/AssetGeneration/    — asset pipeline notes + generators (incl. segmented weapons research)

Also bundles related feats, Texture/Sound/Resources for ArcaneSaturation, and a
REWRITE_NOTES.md so the pack can be reworked later outside the full mod.

  python elin_export_living_weapon.py
  python elin_export_living_weapon.py --dest-only tools   # or starfield
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

_ELIN = Path(__file__).resolve().parent
_CFG = json.loads((_ELIN / "elin_asset_catalog.json").read_text(encoding="utf-8"))
_MOD = Path(_CFG["modPath"])
_TOOLS_EXPORT = _ELIN / "Exports" / "LivingWeaponSystem"
_SF_EXPORT = (
    Path(_CFG["starfield"]["arcaneConduit"]) / "assets" / "ElinExport" / "LivingWeaponSystem"
)

# Core trees the user pointed at
CORE_DIRS = [
    "MagicPlus/ArcaneSaturation",
    "MagicPlus/AssetGeneration",
]

# Sibling integration / feat glue that makes the living-weapon option usable
RELATED_FILES = [
    "FeatEffects/CustomFeatEffects_BiomagicPack.cs",
    "BiomagicPackFeatApply.cs",
    "FEAT_IMPLEMENTATION_TODO.md",  # has biomagic leftover notes
]

# Runtime / authoring assets for ArcaneSaturation hero + SFX
RELATED_GLOBS = [
    ("Texture", "ArcaneSaturation*.png"),
    ("Texture", "ArcaneSaturation*"),
    ("Sound", "ArcaneSaturation*"),
    ("Portrait", "UN_crcc_arcanesaturation.png"),
    ("Assets/Resources/ArcaneSaturation", "**/*"),
    ("LangMod", "**/Element.*"),  # optional; we filter biomagic feat rows separately
]


def _copy_tree(src: Path, dst: Path) -> int:
    if not src.is_dir():
        print(f"[skip] missing dir {src}")
        return 0
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return sum(1 for _ in dst.rglob("*") if _.is_file())


def _copy_file(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def export_one(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    counts: dict = {"files": 0, "dirs": {}}

    src_root = root / "src"
    for rel in CORE_DIRS:
        n = _copy_tree(_MOD / rel, src_root / rel)
        counts["dirs"][rel] = n
        counts["files"] += n
        print(f"  {rel}: {n} files")

    related = root / "related"
    for rel in RELATED_FILES:
        if _copy_file(_MOD / rel, related / rel):
            counts["files"] += 1
            print(f"  + {rel}")

    # FeatReference / CustomFeatPatches snippets (IDs only — full FeatReference is huge)
    feat_snip = related / "feat_ids_biomagic.md"
    feat_snip.write_text(
        """# Biomagic / living-weapon feat IDs (from CustomRaceClassCreator)

Icons **3910–3939** (after witch 3900–3909), wired in `CustomFeatPatches.cs` / `FeatReference.cs`:

| Alias | Role |
|---|---|
| featLivingWeapon | Melee bonus; biomagic weapons grow faster |
| featBiomagicBond | Bond / relationship |
| featWeaponSentience | Sentience growth |
| featMutationMaster | Mutation mastery |
| featEvolutionPath | Evolution path |
| featCorruptionResist | Corruption resist |
| featFleshShaper | Flesh shaping |
| featOrganicArmor | Organic armor |
| featTentacleMaster | Tentacles |
| featEyeGrowth | Eye growth |
| featBiomagicFeed | Feeding |
| featSaturationControl | Saturation control |
| featPersonalityBond | Personality bond |
| featWeaponDialogue | Weapon dialogue |
| featEvolutionBurst | Evolution burst |
| featMutationChoice | Mutation choice |
| featBiomagicHunger | Hunger |
| featSentienceGrowth | Sentience growth |
| featCorruptedPower | Corrupted power |
| featFleshGraft | Flesh graft |
| featOrganicWeapon | Organic weapon |
| featLivingArmor | Living armor |
| featParasite | Parasite |
| featSymbiote | Symbiote |
| featHiveMind | Hive mind |
| featBioelectricity | Bioelectricity |
| featAcidBlood | Acid blood |
| featRegeneration | Regeneration |
| featAdaptiveImmunity | Adaptive immunity |
| featBiomagicMastery | Biomagic mastery |

Live Harmony for these leftovers: `FeatEffects/CustomFeatEffects_BiomagicPack.cs`.
Core weapon runtime: `MagicPlus/ArcaneSaturation/*` (do not double-PatchAll combat files).
""",
        encoding="utf-8",
    )
    counts["files"] += 1

    assets = root / "assets"
    # Texture system icon + fx
    tex = _MOD / "Texture"
    for name in (
        "ArcaneSaturation.png",
        "ArcaneSaturation_48.png",
        "ArcaneSaturation_fx.png",
    ):
        if _copy_file(tex / name, assets / "Texture" / name):
            counts["files"] += 1
    # Act icons that look biomagic / living-weapon themed (best-effort)
    for p in tex.glob("Act*.png"):
        low = p.stem.lower()
        if any(
            k in low
            for k in (
                "biomagic",
                "living",
                "tentacle",
                "flesh",
                "saturation",
                "corrupt",
                "symbiot",
                "parasite",
                "organic",
            )
        ):
            if _copy_file(p, assets / "Texture" / p.name):
                counts["files"] += 1

    snd = _MOD / "Sound"
    for p in snd.glob("ArcaneSaturation*"):
        if _copy_file(p, assets / "Sound" / p.name):
            counts["files"] += 1

    portrait = _MOD / "Portrait" / "UN_crcc_arcanesaturation.png"
    if _copy_file(portrait, assets / "Portrait" / portrait.name):
        counts["files"] += 1

    res = _MOD / "Assets" / "Resources" / "ArcaneSaturation"
    if res.is_dir():
        n = _copy_tree(res, assets / "Resources" / "ArcaneSaturation")
        counts["dirs"]["Assets/Resources/ArcaneSaturation"] = n
        counts["files"] += n

    # Shared TRELLIS mesh reference (path pointer + copy if present)
    shared_glb = Path(
        r"D:\games\Ai assisted toolkit\Tools\Shared\Concepts\meshes\elinArcaneSaturation.glb"
    )
    shared_concept = Path(
        r"D:\games\Ai assisted toolkit\Tools\Shared\Concepts\elinArcaneSaturation.png"
    )
    if shared_glb.is_file() and _copy_file(shared_glb, assets / "meshes" / shared_glb.name):
        counts["files"] += 1
    if shared_concept.is_file() and _copy_file(
        shared_concept, assets / "concepts" / shared_concept.name
    ):
        counts["files"] += 1

    readme = root / "README.md"
    readme.write_text(
        f"""# Living Weapon / Biomagic option pack (export)

Exported from CustomRaceClassCreator on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}.

This is an **optional, reworkable** slice of the mod — the biomagic **living weapon**
system under Arcane Saturation, plus the **AssetGeneration** tooling/notes that
were meant to feed unique art (including segmented / organic weapon research).

## Layout

```
src/MagicPlus/ArcaneSaturation/   # runtime C# — living weapons, sentience, hunger, mutation, UI
src/MagicPlus/AssetGeneration/    # asset pipeline + OpenStarbound segmented-weapon research notes
related/                          # feat glue + biomagic feat ID table
assets/                           # Texture / Sound / Portrait / Resources / meshes
REWRITE_NOTES.md                  # how to rework this later
manifest.json
```

## What it is

- **Living / biomagic weapons** that hunger, bond, mutate, gain sentience, dialogue, evolution paths
- **Arcane saturation** meter + corruption / enchantment rewriting
- **AssetGeneration** hooks for AI/procedural spell & weapon visuals (research refs to OpenStarbound segmented weapons)

## What it is not

- Not a standalone BepInEx plugin by itself (still namespaced under `CustomRaceClassCreator.MagicPlus.*`)
- Not Starfield Transcendence “living hull” ships (different system; this is Elin’s biomagic weapons)
- Spell Act icons for every MagicPlus school live elsewhere (`elin_unique_spell_art.py`)

## Rework later

See `REWRITE_NOTES.md`. Typical options:
1. Keep as CRCC submodule (status quo)
2. Split into `BiomagicWeapons` BepInEx plugin + soft dependency on CRCC
3. Port concepts (hunger/bond/sentience) to another game’s weapon framework
4. Reuse AssetGeneration notes for unique organic weapon meshes / FX

## API entry points

- `BiomagicApi` / `WeaponSaturationApi` / `WeaponCorruptionApi`
- `WeaponMutationEngine`, `BiomagicEvolutionSystem`, `BiomagicDialogueSystem`
- Docs inside `src/MagicPlus/ArcaneSaturation/BIOMAGIC_WEAPON_API.md`
""",
        encoding="utf-8",
    )

    notes = root / "REWRITE_NOTES.md"
    notes.write_text(
        """# Rework notes — Living Weapon option

## Namespace today
`CustomRaceClassCreator.MagicPlus.ArcaneSaturation`

Initializer: `BiomagicWeaponSystemInitializer` (wired from main plugin startup).

## Hard dependencies inside CRCC
- Harmony patches on combat / card / PCC (see `BiomagicWeaponCombatPatches.cs`)
- Optional hooks: `PCCMutation`, dialogue UI layers, quest system
- Feat pack: `CustomFeatEffects_BiomagicPack.cs` (icons 3910–3939)

## Soft / research dependencies (AssetGeneration)
- `OPENSTARBOUND_SEGMENTED_WEAPONS_NOTES.md` — segmented whips/chains/tentacles for organic weapons
- `SPELLMAKING_RUNTIME_MESH.md`, `SEGMENTED_SPELL_ANIMATIONS.md`
- Pipeline: `AssetGenerationPipeline.cs` → Unity importer / quality verifier

## Clean split checklist (if extracted later)
1. New plugin id + namespace `BiomagicWeapons` (or `LivingWeaponSystem`)
2. Copy `ArcaneSaturation/` sources; rename namespace
3. Move feat pack + Element rows for biomagic feats
4. Keep AssetGeneration as optional Editor/tools package
5. Replace CRCC-only helpers with interfaces (log, save, UI shell)
6. Ship Texture/Sound/Portrait from `assets/` in this export

## Starfield angle (optional)
Starfield ArcaneConduit has a separate Transcendence “living weapon” / biometal ship line.
Do **not** merge blindly — different runtime. This export is the **Elin biomagic** design
if you want to borrow hunger/bond/mutation fantasy for SF later.
""",
        encoding="utf-8",
    )

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_mod": str(_MOD),
        "export_root": str(root),
        "core_dirs": CORE_DIRS,
        "counts": counts,
        "option": "living_weapon_biomagic",
        "reworkable": True,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"export complete -> {root} ({counts['files']} files)")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dest-only",
        choices=("tools", "starfield", "both"),
        default="both",
    )
    args = ap.parse_args()
    dests = []
    if args.dest_only in ("tools", "both"):
        dests.append(_TOOLS_EXPORT)
    if args.dest_only in ("starfield", "both"):
        dests.append(_SF_EXPORT)

    print(f"MOD {_MOD}")
    manifests = []
    for d in dests:
        print(f"== {d} ==")
        manifests.append(export_one(d))
    # index pointer in Tools/Elin/Exports
    idx = _ELIN / "Exports" / "README.md"
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(
        f"""# Elin dual-consumer exports

| Pack | Path |
|---|---|
| Living Weapon / Biomagic | `{_TOOLS_EXPORT}` |
| Starfield mirror | `{_SF_EXPORT}` |
| Spell art (Cursor) | `.../ElinExport/spell_art` |

Living weapon pack regenerated: {datetime.now(timezone.utc).isoformat()}
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
