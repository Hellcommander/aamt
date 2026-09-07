#!/usr/bin/env python3
"""
Patch Space-Time Vortex mod XML after Ollama asset generation.

The mod (v2.3.0+) runs with ASCII fallbacks when Textures/ is empty.
After generate_vortex_professional.py writes PNGs, this enables tile references
in ObjectBlueprints.xml and Mutations.xml automatically.

Animated holes use AnimatedMaterialGeneric TileAnimationFrames (wiki Modding:Tiles),
not LowFrameOffset against a missing BlackHole_frame.png sheet.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


def _has_frames(textures_dir: Path, base: str) -> int:
    """Return count of consecutive frame00.. files for base name."""
    count = 0
    for i in range(32):
        if (textures_dir / f"{base}_frame{i:02d}.png").exists():
            count = i + 1
        elif count:
            break
    return count


def _tile_animation_frames(prefix: str, frame_count: int, ticks_per_frame: int = 10) -> str:
    """Build TileAnimationFrames= tick=path,... for AnimatedMaterialGeneric."""
    parts = []
    for i in range(frame_count):
        tick = i * ticks_per_frame
        parts.append(f"{tick}=Textures/{prefix}_frame{i:02d}.png")
    return ",".join(parts)


def _ensure_base_frame_tiles(textures_dir: Path, base: str, frame_count: int) -> None:
    """
    Ensure Textures/{base}_frame.png exists (copy of frame00).

    VortexAssetHelper.HasAnimatedHoleTiles and older docs look for this path;
    TileAnimationFrames still drive playback via numbered frames.
    """
    if frame_count <= 0:
        return
    src = textures_dir / f"{base}_frame00.png"
    dst = textures_dir / f"{base}_frame.png"
    if src.exists():
        shutil.copy2(src, dst)


def _detect_assets(mod_path: Path) -> dict:
    textures = mod_path / "Textures"
    return {
        "icon": (textures / "Space-Time Vortex_icon.png").exists(),
        "black_hole_frames": _has_frames(textures, "BlackHole"),
        "white_hole_frames": _has_frames(textures, "WhiteHole"),
        "warning": (textures / "VortexWarning_marker.png").exists(),
        "particles": any(textures.glob("VortexParticle_*_frame00.png")) if textures.exists() else False,
        "distortion": any(textures.glob("VortexDistortion_*.png")) if textures.exists() else False,
        "ability_aggressive": (textures / "VortexAbility_Aggressive.png").exists(),
        "ability_defensive": (textures / "VortexAbility_Defensive.png").exists(),
    }


def _animation_length(frame_count: int, ticks_per_frame: int = 10) -> int:
    return max(frame_count * ticks_per_frame, 20)


def _write_object_blueprints(mod_path: Path, assets: dict) -> List[str]:
    path = mod_path / "ObjectBlueprints.xml"
    textures = mod_path / "Textures"
    black_frames = assets["black_hole_frames"]
    white_frames = assets["white_hole_frames"]

    _ensure_base_frame_tiles(textures, "BlackHole", black_frames)
    _ensure_base_frame_tiles(textures, "WhiteHole", white_frames)

    black_tile = ""
    black_anim = ""
    if black_frames:
        black_tile = '\n        Tile="Textures/BlackHole_frame00.png"'
        black_anim = (
            f'\n  <part Name="AnimatedMaterialGeneric" '
            f'AnimationLength="{_animation_length(black_frames)}" '
            f'TileAnimationFrames="{_tile_animation_frames("BlackHole", black_frames)}" />'
        )

    white_tile = ""
    white_anim = ""
    if white_frames:
        white_tile = '\n        Tile="Textures/WhiteHole_frame00.png"'
        white_anim = (
            f'\n  <part Name="AnimatedMaterialGeneric" '
            f'AnimationLength="{_animation_length(white_frames)}" '
            f'TileAnimationFrames="{_tile_animation_frames("WhiteHole", white_frames)}" />'
        )

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<objects Encoding="utf-8">
<object Name="VortexBlackHole">
  <part Name="Render"
        DisplayName="{{{{K|space-time singularity}}}}"
        RenderString="@"
        ColorString="&amp;K^m"
        TileColor="&amp;K"
        DetailColor="m"{black_tile} />
  <part Name="Description"
        Short="A roiling tear in spacetime pulls everything toward its hungry center. Light bends around the edges, and the air itself seems to spiral inward." />
  <part Name="Physics" Solid="false" Weight="0" />
  <part Name="ExistenceSupport" />{black_anim}
  <tag Name="IgnoresWalls" Value="true" />
  <tag Name="NoTarget" Value="true" />
  <tag Name="ExcludeFromDynamicEncounters" Value="*noinherit" />
  <tag Name="Gender" Value="neuter" />
  <xtagGrammar Proper="false" />
</object>

<object Name="VortexWhiteHole">
  <part Name="Render"
        DisplayName="{{{{W|space-time rupture}}}}"
        RenderString="*"
        ColorString="&amp;Y^W"
        TileColor="&amp;Y"
        DetailColor="W"{white_tile} />
  <part Name="Description"
        Short="A blinding tear in spacetime expels matter and energy in all directions. The fabric of reality strains at its edges." />
  <part Name="Physics" Solid="false" Weight="0" />
  <part Name="ExistenceSupport" />{white_anim}
  <tag Name="IgnoresWalls" Value="true" />
  <tag Name="NoTarget" Value="true" />
  <tag Name="ExcludeFromDynamicEncounters" Value="*noinherit" />
  <tag Name="Gender" Value="neuter" />
  <xtagGrammar Proper="false" />
</object>
</objects>
"""

    path.write_text(content, encoding="utf-8")
    changes = []
    if black_frames:
        changes.append(f"VortexBlackHole -> {black_frames} TileAnimationFrames + BlackHole_frame.png")
    else:
        changes.append("VortexBlackHole -> ASCII @ fallback (no frame PNGs)")
    if white_frames:
        changes.append(f"VortexWhiteHole -> {white_frames} TileAnimationFrames + WhiteHole_frame.png")
    else:
        changes.append("VortexWhiteHole -> ASCII * fallback (no frame PNGs)")
    return changes


def _write_mutations_xml(mod_path: Path, assets: dict) -> List[str]:
    path = mod_path / "Mutations.xml"
    icon_attr = ""
    if assets["icon"]:
        # Mutation character-creation / selection tile
        icon_attr = '\n      Tile="Textures/Space-Time Vortex_icon.png"'

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<mutations Encoding="utf-8">
  <category Name="Mental">
    <mutation 
      Name="Spacetime Vortex" 
      Class="Arendeth_SpacetimeVortex" 
      Cost="5" 
      MaxSelected="1" 
      Exclusions=""
      DisplayName="Space-Time Vortex"{icon_attr}>
    </mutation>
  </category>
</mutations>
"""
    path.write_text(content, encoding="utf-8")
    if assets["icon"]:
        return ["Mutations.xml -> mutation selection Tile=Textures/Space-Time Vortex_icon.png"]
    return ["Mutations.xml -> no icon PNG found, using default glyph"]


def _write_assets_manifest(mod_path: Path, assets: dict) -> None:
    lines = [
        "Auto-generated by vortex_mod_integration.py",
        "Run after generate_vortex_professional.py",
        "",
        "Detected assets:",
    ]
    for key, value in assets.items():
        lines.append(f"  {key}: {value}")
    lines.extend([
        "",
        "Wiring:",
        "  - Mutations.xml Tile -> mutation selection screen icon",
        "  - ObjectBlueprints TileAnimationFrames -> animated hole tiles",
        "  - Textures/*_frame.png -> base copies of frame00 for helpers",
        "",
        "Mod code (v2.3.0+) auto-detects Textures/ at runtime.",
        "Re-run the generator any time to refresh PNGs and XML wiring.",
    ])
    (mod_path / "ASSETS_INSTALLED.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_mod_integration(mod_path: Path) -> Tuple[bool, List[str]]:
    mod_path = Path(mod_path)
    if not mod_path.is_dir():
        raise FileNotFoundError(f"Mod path not found: {mod_path}")

    assets = _detect_assets(mod_path)
    messages: List[str] = []
    messages.extend(_write_object_blueprints(mod_path, assets))
    messages.extend(_write_mutations_xml(mod_path, assets))
    _write_assets_manifest(mod_path, assets)

    has_any = any(v for v in assets.values() if v)
    if assets["particles"]:
        messages.append("Particles -> VortexParticleEffects.cs will use tile sprites")
    if assets["distortion"]:
        messages.append("Distortion -> overlay tiles enabled at high intensity")
    if assets["warning"]:
        messages.append("Warning markers -> tile sprite enabled")
    if assets["ability_aggressive"] or assets["ability_defensive"]:
        messages.append("Ability icons present (wire via AddMyActivatedAbility UITileDefault in C#)")

    return has_any, messages


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Wire generated vortex PNGs into mod XML")
    parser.add_argument("mod_path", help="Path to Improved Space Time Vortex mod folder")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        found, messages = apply_mod_integration(Path(args.mod_path))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Vortex mod integration")
    print("=" * 50)
    for msg in messages:
        print(f"  • {msg}")
    print()
    if not found:
        print("No PNG assets found in Textures/. Mod will keep ASCII fallbacks.")
        return 0

    print("Integration complete. Reload the mod in Qud to see new tiles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
