#!/usr/bin/env python3
"""Post-install validation for monster clothes/armor/weapon packages."""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from build_armor_xml import KIND_META, internal_name
from er_tool_lib import DEFAULT_CONFIG, load_config, mod_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--mod", default="")
    args = ap.parse_args(argv)

    cfg = load_config(Path(args.config))
    mod = mod_path(cfg, args.mod or None)
    xml_path = mod / "Data" / "GameCore" / "LHL_GeneratedMonsterArmor.xml"
    errors: list[str] = []
    ok: list[str] = []

    if not xml_path.exists():
        print("FAIL: missing", xml_path)
        return 1

    root = ET.parse(xml_path).getroot()
    want_alts = bool(cfg.get("altItems", True))
    expected = 0
    for race_key, race in cfg["races"].items():
        for kind in KIND_META:
            if kind not in race:
                continue
            for alt in ((False, True) if want_alts else (False,)):
                expected += 1
                internal = internal_name(cfg, race_key, kind, alt=alt)
                icon = mod / "Gfx" / "Items" / f"{internal}_Icon.png"
                node = root.find(f"./GameItemType[@InternalName='{internal}']")
                if node is None:
                    errors.append(f"{internal}: missing XML node")
                    continue
                if not icon.exists():
                    errors.append(f"{internal}: missing icon {icon.name}")
                elif Image:
                    im = Image.open(icon)
                    if im.size[0] < 32 or im.size[1] < 32:
                        errors.append(f"{internal}: icon too small {im.size}")

                model = node.find(
                    "./GameItemTypeArtDef/GameItemTypeModelPack/GameItemTypeModel/ModelFile"
                )
                models = node.findall(
                    "./GameItemTypeArtDef/GameItemTypeModelPack/SupportedUnitModelType"
                )
                if model is None or not (model.text or "").strip():
                    errors.append(f"{internal}: missing ModelFile")
                if not models:
                    errors.append(f"{internal}: no SupportedUnitModelType")

                if kind in ("clothes", "armor"):
                    attach = node.find(
                        "./GameItemTypeArtDef/GameItemTypeModelPack/GameItemTypeModel/AttachmentType"
                    )
                    if attach is None or (attach.text or "").strip() != "Skinned":
                        errors.append(f"{internal}: clothes/armor must be Skinned")
                else:
                    attach = node.find(
                        "./GameItemTypeArtDef/GameItemTypeModelPack/GameItemTypeModel/Attachment"
                    )
                    if attach is None or not (attach.text or "").strip():
                        errors.append(f"{internal}: weapon missing Attachment")

                item_name = race[kind].get("itemName") or internal
                if alt:
                    item_name = f"{item_name} (Alt)"
                if not any(internal in e for e in errors[-6:]):
                    ok.append(f"{internal} ({item_name})")

    items = root.findall("GameItemType")
    if len(items) != expected:
        errors.append(f"XML item count {len(items)} != expected {expected}")

    print(f"Validated {expected} items against mod install (altItems={want_alts})")
    print(f"OK: {len(ok)}")
    if errors:
        print(f"FAIL: {len(errors)}")
        for e in errors:
            print(" -", e)
        return 1
    print("ALL ITEM CHECKS PASSED")
    for line in ok:
        print(" -", line)

    from er_harden_units import validate_designable_units

    unit_errs = validate_designable_units(mod)
    if unit_errs:
        print(f"FAIL unit presentation: {len(unit_errs)}")
        for e in unit_errs[:60]:
            print(" -", e)
        if len(unit_errs) > 60:
            print(f" - ... +{len(unit_errs) - 60} more")
        return 1
    print("ALL UNIT PRESENTATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
