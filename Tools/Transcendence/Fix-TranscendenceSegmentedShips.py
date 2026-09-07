#!/usr/bin/env python3
"""
Fix-TranscendenceSegmentedShips.py

Autofix a TranscendenceDev-integration-APIxx tree for true segmented ships.

Engine already has Interior <Section> + jointSpine + CShip::SetAsShipSection, but
mods cannot mark runtime-spawned ships as sections via TLisp. Without that,
objAddConnection 'spine only creates a physics rod.

This autofix:
  1. Adds (objAttachShipSection root section [options]) -> connectionID
  2. Adds (objIsShipSection obj) -> True/Nil
  3. Extends objAddConnection with shipSection / length options
  4. Aligns rotation for all spine joints
  5. Destroys runtime ship sections when the root leaves the system

Idempotent: writes .segmented_ships_autofix_v1 under the API root.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER_NAME = ".segmented_ships_autofix_v1"
FIX_VERSION = 1
TAG = "TX_SEGMENTED_SHIPS_AUTOFIX"


def backup_file(path: Path, backup_root: Path, api_root: Path) -> None:
    rel = path.relative_to(api_root)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def write_text(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def once(text: str, old: str, new: str, notes: list[str], label: str) -> str:
    if old not in text:
        if new.strip()[:40] in text or TAG in text and label in notes:
            notes.append(f"{label}: already present")
            return text
        notes.append(f"{label}: WARNING pattern not found")
        return text
    notes.append(label)
    return text.replace(old, new, 1)


def patch_object_joint_cpp(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "FIELD_SHIP_SECTION" in text and TAG in text:
        notes.append("CObjectJoint.cpp: already patched")
        return text, notes

    text = once(
        text,
        '#define FIELD_POS2\t\t\t\t\t\tCONSTLIT("pos2")\n',
        '#define FIELD_POS2\t\t\t\t\t\tCONSTLIT("pos2")\n'
        f'#define FIELD_SHIP_SECTION\t\t\t\tCONSTLIT("shipSection")\t// {TAG}\n',
        notes,
        "CObjectJoint.cpp: FIELD_SHIP_SECTION",
    )

    text = once(
        text,
        "\tif (pOptions == NULL)\n"
        "\t\treturn;\n"
        "\n"
        "\t//\tLength\n"
        "\n"
        "\tICCItem *pLength = pOptions->GetElement(FIELD_LENGTH);\n",
        "\tif (pOptions == NULL)\n"
        "\t\treturn;\n"
        "\n"
        f"\t//\t{TAG}: mark joint as ship compartment\n"
        "\tICCItem *pShipSection = pOptions->GetElement(FIELD_SHIP_SECTION);\n"
        "\tif (pShipSection && !pShipSection->IsNil())\n"
        "\t\tm_fShipCompartment = true;\n"
        "\n"
        "\t//\tLength\n"
        "\n"
        "\tICCItem *pLength = pOptions->GetElement(FIELD_LENGTH);\n",
        notes,
        "CObjectJoint.cpp: ApplyOptions shipSection",
    )

    text = once(
        text,
        "\t//\tIf this is a ship compartment, we rotation the ship to face the attach\n"
        "\t//\tpoint.\n"
        "\t//\n"
        "\t//\tNOTE: We assume that Obj2 always faces Obj1.\n"
        "\n"
        "\tif (m_fShipCompartment)\n",
        f"\t//\t{TAG}: align trailing ship for spine / ship-section joints\n"
        "\t//\tNOTE: We assume that Obj2 always faces Obj1.\n"
        "\n"
        "\tif (m_iType == jointSpine || m_fShipCompartment)\n",
        notes,
        "CObjectJoint.cpp: spine rotation",
    )

    return text, notes


def patch_ccextensions(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if "FN_OBJ_ATTACH_SHIP_SECTION" in text and "case FN_OBJ_ATTACH_SHIP_SECTION:" in text:
        notes.append("CCExtensions.cpp: already patched")
        return text, notes

    text = once(
        text,
        "#define FN_OBJ_DESTINY_ROLL\t\t\t\t154\n",
        "#define FN_OBJ_DESTINY_ROLL\t\t\t\t154\n"
        f"#define FN_OBJ_ATTACH_SHIP_SECTION\t\t155\t// {TAG}\n"
        f"#define FN_OBJ_IS_SHIP_SECTION\t\t\t156\t// {TAG}\n",
        notes,
        "CCExtensions.cpp: FN defines",
    )

    # Help text — replace the options closing of objAddConnection
    text = once(
        text,
        '\t\t\t"   \'pos1: position relative to obj1\\n"\n'
        '\t\t\t"   \'pos2: position relative to obj2\\n",\n'
        "\n"
        '\t\t\t"isi*",\t\tPPFLAG_SIDEEFFECTS,\t},\n',
        '\t\t\t"   \'pos1: position relative to obj1\\n"\n'
        '\t\t\t"   \'pos2: position relative to obj2\\n"\n'
        '\t\t\t"   \'length: joint length in pixels\\n"\n'
        f'\t\t\t"   \'shipSection: True = treat obj2 as ship section of obj1\\n",\t// {TAG}\n'
        "\n"
        '\t\t\t"isi*",\t\tPPFLAG_SIDEEFFECTS,\t},\n',
        notes,
        "CCExtensions.cpp: objAddConnection help",
    )

    # Register primitives before objCalcBestTarget
    attach_reg = (
        f"\t\t//\t{TAG}\n"
        '\t\t{	"objAttachShipSection",\t\t\tfnObjSet,\t\tFN_OBJ_ATTACH_SHIP_SECTION,\n'
        '\t\t\t"(objAttachShipSection root section [options]) -> connectionID\\n\\n"\n'
        "\n"
        '\t\t\t"Attaches section as a true ship compartment of root using a spine\\n"\n'
        '\t\t\t"joint (Nova Drift / Balin Dragon style segmented ships).\\n\\n"\n'
        "\n"
        '\t\t\t"options:\\n\\n"\n'
        "\n"
        '\t\t\t"   \'length: joint length in pixels (default: current distance)\\n"\n'
        '\t\t\t"   \'attachTo: object to joint with (default: root; prior segment for chains)\\n"\n'
        '\t\t\t"   \'pos1 / \'pos2: attach positions\\n",\n'
        "\n"
        '\t\t\t"ii*",\t\tPPFLAG_SIDEEFFECTS,\t},\n'
        "\n"
        f"\t\t//\t{TAG}\n"
        '\t\t{	"objIsShipSection",\t\t\t\tfnObjGet,\t\tFN_OBJ_IS_SHIP_SECTION,\n'
        '\t\t\t"(objIsShipSection obj) -> True/Nil",\n'
        '\t\t\t"i",\t\t0,\t},\n'
        "\n"
    )
    if '"objAttachShipSection"' not in text:
        text = once(
            text,
            '\t\t{	"objCalcBestTarget",',
            attach_reg + '\t\t{	"objCalcBestTarget",',
            notes,
            "CCExtensions.cpp: register primitives",
        )

    # Enhance ADD_CONNECTION
    text = once(
        text,
        "\t\t\tICCItem *pOptions = (pArgs->GetCount() > 3 ? pArgs->GetElement(3) : NULL);\n"
        "\n"
        "\t\t\tDWORD dwID;\n"
        "\t\t\tif (!pSystem->AddJoint(iType, pObj, pObj2, pOptions, &dwID))\n"
        "\t\t\t\treturn pCC->CreateNil();\n"
        "\n"
        "\t\t\treturn pCC->CreateInteger(dwID);\n"
        "\t\t\t}\n"
        "\n"
        "\t\tcase FN_OBJ_ADD_ITEM:\n",
        "\t\t\tICCItem *pOptions = (pArgs->GetCount() > 3 ? pArgs->GetElement(3) : NULL);\n"
        "\n"
        f"\t\t\t//\t{TAG}: optional shipSection before joint so IsAttached() is set\n"
        "\t\t\tif (pOptions)\n"
        "\t\t\t\t{\n"
        "\t\t\t\tICCItem *pShipSection = pOptions->GetElement(CONSTLIT(\"shipSection\"));\n"
        "\t\t\t\tif (pShipSection && !pShipSection->IsNil())\n"
        "\t\t\t\t\t{\n"
        "\t\t\t\t\tCShip *pRoot = pObj->AsShip();\n"
        "\t\t\t\t\tCShip *pSection = pObj2->AsShip();\n"
        "\t\t\t\t\tif (pRoot && pSection)\n"
        "\t\t\t\t\t\tpSection->SetAsShipSection(pRoot);\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\n"
        "\t\t\tDWORD dwID;\n"
        "\t\t\tif (!pSystem->AddJoint(iType, pObj, pObj2, pOptions, &dwID))\n"
        "\t\t\t\treturn pCC->CreateNil();\n"
        "\n"
        "\t\t\treturn pCC->CreateInteger(dwID);\n"
        "\t\t\t}\n"
        "\n"
        f"\t\tcase FN_OBJ_ATTACH_SHIP_SECTION:\t// {TAG}\n"
        "\t\t\t{\n"
        "\t\t\tCSystem *pSystem = pCtx->GetUniverse().GetCurrentSystem();\n"
        "\t\t\tif (pSystem == NULL)\n"
        "\t\t\t\treturn StdErrorNoSystem(*pCC);\n"
        "\n"
        "\t\t\tCShip *pRoot = pObj->AsShip();\n"
        "\t\t\tif (pRoot == NULL)\n"
        "\t\t\t\treturn pCC->CreateError(CONSTLIT(\"Root must be a ship\"), pArgs->GetElement(0));\n"
        "\n"
        "\t\t\tCSpaceObject *pSectionObj = CreateObjFromItem(pArgs->GetElement(1), CCUTIL_FLAG_CHECK_DESTROYED);\n"
        "\t\t\tCShip *pSection = (pSectionObj ? pSectionObj->AsShip() : NULL);\n"
        "\t\t\tif (pSection == NULL)\n"
        "\t\t\t\treturn pCC->CreateError(CONSTLIT(\"Section must be a ship\"), pArgs->GetElement(1));\n"
        "\n"
        "\t\t\tif (pSection == pRoot)\n"
        "\t\t\t\treturn pCC->CreateError(CONSTLIT(\"Cannot attach ship to itself\"));\n"
        "\n"
        "\t\t\tICCItem *pOptions = (pArgs->GetCount() > 2 ? pArgs->GetElement(2) : NULL);\n"
        "\n"
        "\t\t\t//\tUltimate root for GetAttachedRoot / targeting\n"
        "\t\t\tCShip *pAttachRoot = pRoot;\n"
        "\t\t\tif (pRoot->IsShipSection())\n"
        "\t\t\t\t{\n"
        "\t\t\t\tCSpaceObject *pUltimate = pRoot->GetAttachedRoot();\n"
        "\t\t\t\tCShip *pUltimateShip = (pUltimate ? pUltimate->AsShip() : NULL);\n"
        "\t\t\t\tif (pUltimateShip)\n"
        "\t\t\t\t\tpAttachRoot = pUltimateShip;\n"
        "\t\t\t\t}\n"
        "\n"
        "\t\t\t//\tJoint partner (previous segment for chains, else root)\n"
        "\t\t\tCSpaceObject *pJointFrom = pRoot;\n"
        "\t\t\tif (pOptions)\n"
        "\t\t\t\t{\n"
        "\t\t\t\tICCItem *pAttachTo = pOptions->GetElement(CONSTLIT(\"attachTo\"));\n"
        "\t\t\t\tif (pAttachTo && !pAttachTo->IsNil())\n"
        "\t\t\t\t\t{\n"
        "\t\t\t\t\tCSpaceObject *pTo = CreateObjFromItem(pAttachTo, CCUTIL_FLAG_CHECK_DESTROYED);\n"
        "\t\t\t\t\tif (pTo)\n"
        "\t\t\t\t\t\tpJointFrom = pTo;\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\n"
        "\t\t\t//\tMark as section BEFORE joint create so m_fShipCompartment is set\n"
        "\t\t\tpSection->SetAsShipSection(pAttachRoot);\n"
        "\n"
        "\t\t\tDWORD dwID;\n"
        "\t\t\tif (!pSystem->AddJoint(CObjectJoint::jointSpine, pJointFrom, pSection, pOptions, &dwID))\n"
        "\t\t\t\treturn pCC->CreateNil();\n"
        "\n"
        "\t\t\treturn pCC->CreateInteger(dwID);\n"
        "\t\t\t}\n"
        "\n"
        "\t\tcase FN_OBJ_ADD_ITEM:\n",
        notes,
        "CCExtensions.cpp: ADD_CONNECTION + ATTACH impl",
    )

    # IS_SHIP_SECTION in fnObjGet (returns directly, not pResult)
    text = once(
        text,
        "\t\tcase FN_OBJ_DESTINY_ROLL:\n"
        "\t\t\t{\n"
        "\t\t\tif (pArgs->GetCount() < 2)\n"
        "\t\t\t\treturn pCC->CreateError(CONSTLIT(\"objRollDestiny requires at least the chance argument\"));\n",
        f"\t\tcase FN_OBJ_IS_SHIP_SECTION:\t// {TAG}\n"
        "\t\t\t{\n"
        "\t\t\tCShip *pShip = pObj->AsShip();\n"
        "\t\t\treturn pCC->CreateBool(pShip && pShip->IsShipSection());\n"
        "\t\t\t}\n"
        "\n"
        "\t\tcase FN_OBJ_DESTINY_ROLL:\n"
        "\t\t\t{\n"
        "\t\t\tif (pArgs->GetCount() < 2)\n"
        "\t\t\t\treturn pCC->CreateError(CONSTLIT(\"objRollDestiny requires at least the chance argument\"));\n",
        notes,
        "CCExtensions.cpp: IS_SHIP_SECTION impl",
    )

    return text, notes


def patch_cship_on_removed(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if f"{TAG}: destroy runtime ship sections" in text:
        notes.append("CShip.cpp: already patched")
        return text, notes

    text = once(
        text,
        "\tif (HasAttachedSections())\n"
        "\t\t{\n"
        "\t\tfor (i = 0; i < m_Interior.GetCount(); i++)\n"
        "\t\t\t{\n"
        "\t\t\tCSpaceObject *pAttached = m_Interior.GetAttached(i);\n"
        "\t\t\tif (pAttached == NULL)\n"
        "\t\t\t\tcontinue;\n"
        "\n"
        "\t\t\tpAttached->Remove(removedFromSystem, CDamageSource(this, removedFromSystem), true);\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t}\n"
        "\n"
        "void CShip::OnSetEventFlags (void)\n",
        "\tif (HasAttachedSections())\n"
        "\t\t{\n"
        "\t\tfor (i = 0; i < m_Interior.GetCount(); i++)\n"
        "\t\t\t{\n"
        "\t\t\tCSpaceObject *pAttached = m_Interior.GetAttached(i);\n"
        "\t\t\tif (pAttached == NULL)\n"
        "\t\t\t\tcontinue;\n"
        "\n"
        "\t\t\tpAttached->Remove(removedFromSystem, CDamageSource(this, removedFromSystem), true);\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\n"
        f"\t//\t{TAG}: destroy runtime ship sections joined via spine (not in Interior list)\n"
        "\tCObjectJoint *pJoint = GetFirstJoint();\n"
        "\twhile (pJoint)\n"
        "\t\t{\n"
        "\t\tCObjectJoint *pNext = pJoint->GetNextJoint(this);\n"
        "\t\tCSpaceObject *pOther = pJoint->GetOtherObj(this);\n"
        "\t\tCShip *pSection = (pOther ? pOther->AsShip() : NULL);\n"
        "\t\tif (pSection\n"
        "\t\t\t\t&& pSection->IsShipSection()\n"
        "\t\t\t\t&& pSection->GetAttachedRoot() == this)\n"
        "\t\t\t{\n"
        "\t\t\tpSection->Remove(removedFromSystem, CDamageSource(this, removedFromSystem), true);\n"
        "\t\t\t}\n"
        "\t\tpJoint = pNext;\n"
        "\t\t}\n"
        "\t}\n"
        "\n"
        "void CShip::OnSetEventFlags (void)\n",
        notes,
        "CShip.cpp: runtime section cleanup",
    )

    return text, notes


def run(api_root: Path, force: bool, dry_run: bool) -> int:
    api_root = api_root.resolve()
    marker = api_root / MARKER_NAME
    if marker.exists() and not force:
        print(f"Already applied ({marker.name}). Use --force to re-apply.")
        return 0

    mammoth = api_root / "Mammoth"
    if not mammoth.is_dir():
        print(f"ERROR: Mammoth not found under {api_root}", file=sys.stderr)
        return 1

    backup_root = api_root / f".segmented_ships_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    targets = [
        (mammoth / "TSE" / "CObjectJoint.cpp", patch_object_joint_cpp),
        (mammoth / "TSE" / "CCExtensions.cpp", patch_ccextensions),
        (mammoth / "TSE" / "CShip.cpp", patch_cship_on_removed),
    ]

    all_notes: list[str] = []
    for path, patcher in targets:
        if not path.is_file():
            print(f"ERROR: missing {path}", file=sys.stderr)
            return 1
        original = path.read_text(encoding="utf-8", errors="replace")
        new_text, notes = patcher(original)
        all_notes.extend(notes)
        if new_text != original:
            print(f"PATCH {path.relative_to(api_root)}")
            if not dry_run:
                backup_file(path, backup_root, api_root)
                write_text(path, new_text)
        else:
            print(f"SKIP  {path.relative_to(api_root)} (no content change)")

    for n in all_notes:
        print(f"  - {n}")

    warn = [n for n in all_notes if "WARNING" in n]
    if warn and not dry_run:
        print("ERROR: some patterns failed; not writing marker.", file=sys.stderr)
        return 1

    if dry_run:
        print("Dry run — no marker written.")
        return 1 if warn else 0

    marker.write_text(
        f"version={FIX_VERSION}\n"
        f"applied={datetime.now().isoformat()}\n"
        f"tag={TAG}\n"
        + "\n".join(f"note={n}" for n in all_notes)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {marker.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofix Transcendence API tree for segmented ships")
    ap.add_argument("api_root", type=Path, help="Path to TranscendenceDev-integration-APIxx")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return run(args.api_root, args.force, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
