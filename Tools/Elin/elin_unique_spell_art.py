#!/usr/bin/env python3
"""Unique complex spell art for CustomRaceClassCreator + Starfield overnight.

Every SPELL gets its own visual identity — never reuse system hero concepts.

Per spell produces:
  - complex concept (1024)  — cinematic spell visualization / FX reference
  - icon (512→48 Act*.png)  — Elin Workshop ability icon
  - staged copies under Starfield ArcaneConduit/assets/ElinExport/spell_art/

  python elin_unique_spell_art.py catalog          # write spell_art_catalog.json
  python elin_unique_spell_art.py generate         # SD or procedural unique icons+concepts
  python elin_unique_spell_art.py generate --icons-only --backend procedural
  python elin_unique_spell_art.py export-starfield  # stage catalog + jobs for overnight
  python elin_unique_spell_art.py overnight         # full SD pass (starts when you run it)
  python elin_unique_spell_art.py all               # catalog → generate → export
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

_ELIN = Path(__file__).resolve().parent
sys.path.insert(0, str(_ELIN))
sys.path.insert(0, str(_ELIN.parent / "Shared"))

_CATALOG_CFG = _ELIN / "elin_asset_catalog.json"
_SPELL_ART_CAT = _ELIN / "spell_art_catalog.json"
_OUT = _ELIN / "Output" / "Concepts" / "Spells"
_SF_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Starfield")
_SF_EXPORT = _SF_ROOT / "ArcaneConduit" / "assets" / "ElinExport" / "spell_art"
_SF_SPELL_CAT = _SF_ROOT / "ArcaneConduit" / "spells" / "catalog.json"

ICON_STYLE = (
    "fantasy RPG game spell icon, Elona/Elin inspired, single unique magical effect "
    "centered, clear silhouette, soft rim light, solid dark background, no text, "
    "no watermark, readable at small size, not a generic orb, not a stock fireball"
)
CONCEPT_STYLE = (
    "cinematic fantasy spell visualization, unique magical phenomenon as the subject, "
    "dramatic lighting, physically based materials, dark void background, "
    "Unreal Engine cinematic, no text, no watermark, not a UI icon, not a character portrait, "
    "show the spell's distinctive effect clearly — this spell only, not a generic blast"
)
NEGATIVE = (
    "text, logo, watermark, letters, UI, frame, border, generic glowing orb only, "
    "stock fireball, duplicate template, blurry, lowres, photograph, multiple panels"
)


def _cfg() -> Dict[str, Any]:
    if _CATALOG_CFG.is_file():
        return json.loads(_CATALOG_CFG.read_text(encoding="utf-8"))
    return {}


def mod_path() -> Path:
    return Path(_cfg().get("modPath") or r"E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator")


def heroes_by_system() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for h in _cfg().get("heroes") or []:
        out[(h.get("elinSystem") or "").lower()] = h
        out[h["id"].lower()] = h
    return out


def pascal(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name or "")
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Spell"


def _pretty(name: str) -> str:
    s = (name or "").replace("_", " ").replace("-", " ")
    s = re.sub(r"\btemplate\b", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return "Spell"
    # snake_case / all-lower → Title Case; keep mixed author names
    if "_" in (name or "") or s == s.lower() or s == s.upper():
        return s.title()
    return s


def _clean_desc(desc: str) -> str:
    """Keep the authored fantasy description; strip pipeline boilerplate."""
    text = (desc or "").strip()
    if not text:
        return ""
    # Drop Starfield port notes that dilute Elin feel
    for marker in (
        "Ported from Elin",
        "Starfield Conduit",
        "Starfield:",
        "CustomRaceClassCreator spell design",
    ):
        if marker in text:
            text = text.split(marker)[0].strip()
    text = re.sub(r"\s+", " ", text).strip(" .;")
    return text


def _visual_from_description(pretty: str, desc: str, system: str, tags: List[str]) -> str:
    """Describe the spell visually from its real text — no keyword shortcut table.

    The authored description is the subject. We only add framing so SD/icon
    painters show the effect mid-cast, not a generic school emblem.
    """
    body = _clean_desc(desc)
    tag_note = ""
    useful = [t for t in (tags or []) if t and t.lower() not in {"spell", "magic", "ability", system.lower()}]
    if useful:
        tag_note = f" Tone cues from design tags: {', '.join(useful[:6])}."

    if body:
        # Prefer full sentences — they carry the unique fantasy feel
        return (
            f"Depict the exact magical event of the spell '{pretty}': {body}. "
            f"Show that action or phenomenon in a single clear iconic moment "
            f"(the effect happening, not a character portrait, not a blank orb)."
            f"{tag_note}"
        )
    # Sparse fallback only when XML/LangMod truly lack prose
    sys_bit = f" within the {system} tradition" if system else ""
    return (
        f"Depict the spell '{pretty}'{sys_bit} as a specific magical event "
        f"implied by its name — invent a vivid fantasy visualization that fits "
        f"the title's meaning, still unique to this spell alone."
        f"{tag_note}"
    )


def _build_prompts(sp: Dict[str, Any]) -> None:
    """Attach description-driven icon/concept prompts onto a spell record."""
    pretty = sp["pretty"]
    visual = _visual_from_description(
        pretty,
        sp.get("detail") or sp.get("desc") or "",
        sp.get("system") or "",
        list(sp.get("tags") or []),
    )
    colors = ", ".join(sp.get("colors") or [])
    palette = f" Subtle accent colors {colors}." if colors else ""
    school = sp.get("school") or ""
    school_bit = f" ArcaneConduit school mood: {school}." if school else ""

    sp["motif"] = visual
    sp["icon_prompt"] = (
        f"{ICON_STYLE}. Spell title: {pretty}. {visual}{palette} "
        f"Compress the described effect into a readable spell icon; "
        f"preserve the specific fantasy of the description, not a stock element blob."
    )
    sp["concept_prompt"] = (
        f"{CONCEPT_STYLE}. Spell title: {pretty}. {visual}{palette}{school_bit} "
        f"This is complex key art for one spell — every detail should support "
        f"the description's meaning so a player recognizes '{pretty}' instantly."
    )
    sp["negative"] = NEGATIVE
    sp["seed"] = int(hashlib.md5(sp["elin_id"].encode()).hexdigest()[:8], 16) % 1_000_000


def collect_elin_spells() -> List[Dict[str, Any]]:
    mod = mod_path()
    heroes = heroes_by_system()
    by_id: Dict[str, Dict[str, Any]] = {}

    # XML templates (authoritative MagicPlus set)
    data = mod / "MagicPlus" / "Data"
    if data.is_dir():
        for path in sorted(data.rglob("*.xml")):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            for t in root.iter("Template"):
                tid = (t.get("id") or "").strip()
                if not tid:
                    continue

                def _child_text(node: ET.Element, *names: str) -> str:
                    want = {n.lower() for n in names}
                    for child in list(node):
                        if child.tag.lower() in want and (child.text or "").strip():
                            return (child.text or "").strip()
                    for n in names:
                        hit = node.find(n)
                        if hit is not None and (hit.text or "").strip():
                            return (hit.text or "").strip()
                    return ""

                def _child_attr(node: ET.Element, *names: str, attr: str = "id") -> str:
                    want = {n.lower() for n in names}
                    for child in list(node):
                        if child.tag.lower() in want:
                            return (child.get(attr) or child.text or "").strip()
                    return ""

                raw_name = _child_text(t, "name", "Name", "title", "Title")
                desc = _child_text(t, "description", "Description", "desc", "Desc")
                if not raw_name or raw_name.lower().endswith("template") or raw_name == tid:
                    raw_name = tid.replace("tmpl_", "").replace("template_", "")
                name = raw_name
                effect_bits: List[str] = []
                for eff in list(t.iter()):
                    if eff.tag.lower() != "effect":
                        continue
                    ed = _child_text(eff, "description", "Description") or (eff.get("description") or "").strip()
                    et = (eff.get("type") or "").strip()
                    if ed:
                        effect_bits.append(ed)
                    elif et and et.lower() not in {"damage", "heal", "buff", "debuff"}:
                        effect_bits.append(et.replace("_", " "))
                if effect_bits and len(desc) < 80:
                    desc = ((desc + " ") if desc else "") + " ".join(effect_bits[:3])
                system = _child_text(t, "MagicSystemId", "magicSystemId") or _child_attr(
                    t, "magicSystem", "MagicSystem", attr="id"
                )
                tags: List[str] = []
                for child in list(t):
                    if child.tag.lower() == "tags":
                        for tag in list(child):
                            if tag.tag.lower() == "tag" and (tag.text or "").strip():
                                tags.append((tag.text or "").strip())
                        if not tags and (child.text or "").strip():
                            tags = [x.strip() for x in re.split(r"[;,]", child.text) if x.strip()]
                h = heroes.get(system.lower()) or {}
                colors = h.get("colors") or ["#a855f7", "#38bdf8", "#fbbf24"]
                # Keep Act id aligned with Element alias when possible (actFoo → ActFoo)
                base_for_act = tid.replace("tmpl_", "").replace("_", " ")
                act = "Act" + pascal(base_for_act)
                by_id[tid] = {
                    "elin_id": tid,
                    "name": name,
                    "pretty": _pretty(name),
                    "desc": desc,
                    "system": system,
                    "hero": h.get("id") or "",
                    "colors": colors,
                    "tags": tags,
                    "act": act,
                    "alias": "act" + pascal(base_for_act),
                    "source": "elin_xml",
                    "file": str(path.relative_to(data)).replace("\\", "/"),
                }

    # Element.tsv SPELL rows (ensure Act names match LangMod)
    tsv = mod / "LangMod" / "EN" / "Element.tsv"
    if tsv.is_file():
        for r in csv.DictReader(tsv.read_text(encoding="utf-8-sig").splitlines(), delimiter="\t"):
            if (r.get("group") or "") != "SPELL":
                continue
            name = (r.get("name") or "").strip()
            alias = (r.get("alias") or "").strip()
            if not name and not alias:
                continue
            # match xml by name or alias
            hit = None
            for sp in by_id.values():
                if sp["name"] == name or sp["alias"] == alias:
                    hit = sp
                    break
            if hit:
                if alias.startswith("act"):
                    hit["act"] = "Act" + alias[3:4].upper() + alias[4:] if len(alias) > 3 else hit["act"]
                    # Prefer Element alias → ActName: actBardicHealingMelody → ActBardicHealingMelody
                    hit["act"] = "A" + alias[1:] if alias.startswith("act") else hit["act"]
                    hit["alias"] = alias
                hit["element_id"] = r.get("id")
                ed = (r.get("detail") or "").strip()
                # Prefer the longer authored prose (Element detail vs XML description)
                if len(ed) > len((hit.get("desc") or "").strip()):
                    hit["detail"] = ed
                    hit["desc"] = ed
                elif ed and not hit.get("detail"):
                    hit["detail"] = ed
            else:
                act = "A" + alias[1:] if alias.startswith("act") else "Act" + pascal(name)
                by_id[alias or name] = {
                    "elin_id": alias or name,
                    "name": name or alias,
                    "pretty": _pretty(name or alias),
                    "desc": r.get("detail") or "",
                    "system": "",
                    "hero": "",
                    "colors": ["#a855f7", "#38bdf8", "#fbbf24"],
                    "tags": [],
                    "act": act,
                    "alias": alias,
                    "source": "elin_element",
                    "element_id": r.get("id"),
                }

    # Starfield Elin spells (may include extras beyond XML)
    if _SF_SPELL_CAT.is_file():
        cat = json.loads(_SF_SPELL_CAT.read_text(encoding="utf-8"))
        for s in cat.get("spells") or []:
            if s.get("source") != "elin":
                continue
            eid = s.get("elin_id") or s.get("id")
            if eid in by_id:
                by_id[eid]["sf_id"] = s.get("id")
                by_id[eid]["sf_stem"] = s.get("stem")
                by_id[eid]["school"] = s.get("school")
                continue
            sys_id = (s.get("elin_system") or "").lower()
            h = heroes.get(sys_id) or {}
            name = s.get("name") or eid
            by_id[eid] = {
                "elin_id": eid,
                "name": name,
                "pretty": _pretty(str(name)),
                "desc": s.get("desc") or "",
                "system": sys_id,
                "hero": h.get("id") or "",
                "colors": h.get("colors") or ["#a855f7", "#38bdf8", "#fbbf24"],
                "tags": [],
                "act": "Act" + pascal(str(name)),
                "alias": "act" + pascal(str(name)),
                "source": "starfield_elin",
                "sf_id": s.get("id"),
                "sf_stem": s.get("stem"),
                "school": s.get("school"),
            }

    spells = list(by_id.values())
    for sp in spells:
        # Prefer Element alias for Act filename when present (actFoo → ActFoo)
        alias = sp.get("alias") or ""
        if alias.startswith("act") and len(alias) > 3:
            sp["act"] = "A" + alias[1:]
        sp["pretty"] = _pretty(sp.get("name") or sp["elin_id"])
        _build_prompts(sp)
        sp["paths"] = {
            "concept": str(_OUT / "Concept" / f"{sp['act']}_concept.png"),
            "icon_hi": str(_OUT / "Icon" / f"{sp['act']}_icon.png"),
            "act": str(mod_path() / "Texture" / f"{sp['act']}.png"),
            "sf_concept": str(_SF_EXPORT / "concepts" / f"{sp['act']}_concept.png"),
            "sf_icon": str(_SF_EXPORT / "icons" / f"{sp['act']}_icon.png"),
        }
    spells.sort(key=lambda s: (s.get("system") or "", s.get("name") or ""))
    return spells


def write_catalog(spells: List[Dict[str, Any]]) -> Path:
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(spells),
        "note": "Unique complex art per spell — never reuse system hero concepts.",
        "spells": spells,
    }
    _SPELL_ART_CAT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"catalog {_SPELL_ART_CAT} ({len(spells)} spells)")
    return _SPELL_ART_CAT


def _procedural_icon(sp: Dict[str, Any], size: int = 48) -> Image.Image:
    from elin_procedural import render_rich_icon
    from elin_quality import finalize_rgba

    # Encode uniqueness into shape/effects from seed + name
    shapes = ["emblem", "orb", "blade", "burst", "crest", "spiral", "shard", "totem"]
    accents = ["sparkles", "runes", "flames", "petals", "shards", "rings", "tendrils", "sigils"]
    seed = int(sp["seed"])
    spec = {
        "motif": sp["motif"][:120],
        "description": sp["pretty"],
        "palette": sp.get("colors") or ["#a855f7", "#38bdf8", "#fbbf24"],
        "shape": shapes[seed % len(shapes)],
        "accent": accents[(seed // 7) % len(accents)],
        "theme": sp.get("system") or "spell",
        "seed": seed,
    }
    return finalize_rgba(render_rich_icon(size, spec, seed=seed))


def _sd_render(prompt: str, negative: str, size: int, seed: int) -> Optional[Image.Image]:
    try:
        import elin_sd
        from sd_http_client import generate_image, detect_server
    except Exception as exc:
        print(f"[sd] import fail: {exc}")
        return None
    if not elin_sd.sd_enabled() and not detect_server():
        return None
    try:
        # Use elin_sd path when possible
        spec = {
            "description": prompt,
            "theme": prompt[:80],
            "palette": [],
            "style": "stylized fantasy",
            "seed": seed,
        }
        img = elin_sd.render_from_spec("spell_asset", spec, target_size=size)
        if img is not None:
            return img
    except Exception as exc:
        print(f"[sd] elin_sd fail: {exc}")
    try:
        from sd_http_client import generate_image

        path = generate_image(
            prompt=prompt,
            negative_prompt=negative,
            width=max(512, size),
            height=max(512, size),
            seed=seed,
        )
        if path and Path(path).is_file():
            return Image.open(path).convert("RGBA")
    except Exception as exc:
        print(f"[sd] generate_image fail: {exc}")
    return None


def _save_act(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = img.convert("RGBA").resize((48, 48), Image.Resampling.LANCZOS)
    out.save(dest, optimize=True)


def generate(
    spells: List[Dict[str, Any]],
    *,
    backend: str = "auto",
    icons_only: bool = False,
    limit: int = 0,
    force: bool = False,
) -> Dict[str, int]:
    stats = {"icon_sd": 0, "icon_proc": 0, "concept_sd": 0, "concept_proc": 0, "skipped": 0, "fail": 0}
    work = spells[:limit] if limit else spells
    for i, sp in enumerate(work, 1):
        act_path = Path(sp["paths"]["act"])
        icon_hi = Path(sp["paths"]["icon_hi"])
        concept = Path(sp["paths"]["concept"])
        print(f"[{i}/{len(work)}] {sp['act']} ({sp['pretty']})", flush=True)

        need_icon = force or not act_path.is_file() or _is_dup_generic(act_path)
        if need_icon:
            img = None
            if backend in ("auto", "sd"):
                img = _sd_render(sp["icon_prompt"], sp["negative"], 512, sp["seed"])
                if img is not None:
                    stats["icon_sd"] += 1
            if img is None and backend in ("auto", "procedural"):
                img = _procedural_icon(sp, 48)
                stats["icon_proc"] += 1
            if img is None:
                stats["fail"] += 1
                continue
            icon_hi.parent.mkdir(parents=True, exist_ok=True)
            hi = img.resize((128, 128), Image.Resampling.LANCZOS) if img.size[0] != 128 else img
            if img.size[0] >= 256:
                hi = img.resize((128, 128), Image.Resampling.LANCZOS)
                img.save(icon_hi.with_name(icon_hi.stem.replace("_icon", "_icon512") + ".png"))
            else:
                # procedural 48 → also write 128 upscale for SF staging
                hi = img.resize((128, 128), Image.Resampling.NEAREST)
            hi.save(icon_hi, optimize=True)
            _save_act(img if img.size[0] >= 48 else hi, act_path)
        else:
            stats["skipped"] += 1

        if icons_only:
            continue

        need_concept = force or not concept.is_file()
        if need_concept:
            cimg = None
            if backend in ("auto", "sd"):
                cimg = _sd_render(sp["concept_prompt"], sp["negative"], 1024, sp["seed"] + 17)
                if cimg is not None:
                    stats["concept_sd"] += 1
            if cimg is None and backend in ("auto", "procedural"):
                # Procedural stand-in: larger unique emblem (not cinematic, but unique)
                cimg = _procedural_icon(sp, 256).resize((512, 512), Image.Resampling.NEAREST)
                stats["concept_proc"] += 1
            if cimg is not None:
                concept.parent.mkdir(parents=True, exist_ok=True)
                cimg.convert("RGBA").save(concept, optimize=True)
    return stats


_GENERIC_HASHES: Optional[set] = None


def _is_dup_generic(path: Path) -> bool:
    """True if this Act icon matches one of the old recycled system-concept hashes."""
    global _GENERIC_HASHES
    if not path.is_file():
        return True
    if _GENERIC_HASHES is None:
        tex = mod_path() / "Texture"
        from collections import Counter
        import hashlib as _h

        counts: Dict[str, int] = {}
        for p in tex.glob("Act*.png"):
            dig = _h.md5(p.read_bytes()).hexdigest()
            counts[dig] = counts.get(dig, 0) + 1
        # any hash shared by 3+ Act icons is treated as generic leftover
        _GENERIC_HASHES = {h for h, c in counts.items() if c >= 3}
    import hashlib as _h

    return _h.md5(path.read_bytes()).hexdigest() in (_GENERIC_HASHES or set())


def export_starfield(spells: List[Dict[str, Any]]) -> Path:
    _SF_EXPORT.mkdir(parents=True, exist_ok=True)
    (_SF_EXPORT / "concepts").mkdir(exist_ok=True)
    (_SF_EXPORT / "icons").mkdir(exist_ok=True)
    (_SF_EXPORT / "prompts").mkdir(exist_ok=True)

    # Full catalog for the overnight agent
    shutil.copy2(_SPELL_ART_CAT, _SF_EXPORT / "spell_art_catalog.json")

    pending_icon = []
    pending_concept = []
    copied = 0
    for sp in spells:
        # prompts sidecar
        (_SF_EXPORT / "prompts" / f"{sp['act']}.json").write_text(
            json.dumps(
                {
                    "act": sp["act"],
                    "elin_id": sp["elin_id"],
                    "pretty": sp["pretty"],
                    "motif": sp["motif"],
                    "icon_prompt": sp["icon_prompt"],
                    "concept_prompt": sp["concept_prompt"],
                    "negative": sp["negative"],
                    "seed": sp["seed"],
                    "sf_id": sp.get("sf_id"),
                    "sf_stem": sp.get("sf_stem"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        ip = Path(sp["paths"]["icon_hi"])
        cp = Path(sp["paths"]["concept"])
        ap = Path(sp["paths"]["act"])
        if ip.is_file():
            shutil.copy2(ip, _SF_EXPORT / "icons" / ip.name)
            copied += 1
        elif ap.is_file():
            shutil.copy2(ap, _SF_EXPORT / "icons" / f"{sp['act']}_icon.png")
            copied += 1
        else:
            pending_icon.append(sp["act"])
        if cp.is_file():
            shutil.copy2(cp, _SF_EXPORT / "concepts" / cp.name)
            copied += 1
        else:
            pending_concept.append(sp["act"])

    (_SF_EXPORT / "pending_icons.txt").write_text("\n".join(pending_icon) + ("\n" if pending_icon else ""), encoding="utf-8")
    (_SF_EXPORT / "pending_concepts.txt").write_text(
        "\n".join(pending_concept) + ("\n" if pending_concept else ""), encoding="utf-8"
    )

    runner = _SF_EXPORT / "run_overnight_spell_art.py"
    runner.write_text(
        f'''#!/usr/bin/env python3
"""Overnight unique complex spell art (SD). One GPU — do not run TRELLIS at the same time.

  python run_overnight_spell_art.py
  python run_overnight_spell_art.py --limit 20
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
TOOLS = Path(r"{_ELIN}")
PY = sys.executable
def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--icons-only", action="store_true")
    args = ap.parse_args()
    cmd = [PY, str(TOOLS / "elin_unique_spell_art.py"), "overnight"]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    if args.force:
        cmd.append("--force")
    if args.icons_only:
        cmd.append("--icons-only")
    return subprocess.call(cmd)
if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )

    ps1 = _SF_EXPORT / "START_SPELL_ART_OVERNIGHT.ps1"
    ps1.write_text(
        f"""# Unique complex spell art overnight (Stable Diffusion)
# Do NOT run TRELLIS on the same GPU at the same time.
$ErrorActionPreference = 'Stop'
Set-Location '{_SF_EXPORT}'
# Prefer forcing SD on for complex art
$env:ELIN_SD = 'on'
python .\\run_overnight_spell_art.py @args
""",
        encoding="utf-8",
    )

    readme = _SF_EXPORT / "README.md"
    readme.write_text(
        f"""# Unique per-spell art (Class Creator + Starfield)

**Problem fixed:** Elin `Act*.png` were ~14 recycled system concepts. Spells need
**unique complex visuals** each.

| Spell count | {len(spells)} |
| Pending icons | {len(pending_icon)} |
| Pending concepts | {len(pending_concept)} |
| Catalog | `spell_art_catalog.json` |
| Prompts | `prompts/{{ActName}}.json` |

## Art types
1. **Concept** (`concepts/*_concept.png`) — cinematic unique spell visualization (complex art)
2. **Icon** (`icons/*_icon.png` → Elin `Texture/Act*.png` 48×48)

## Start overnight
```powershell
cd "{_SF_EXPORT}"
.\\START_SPELL_ART_OVERNIGHT.ps1
# smoke:
python .\\run_overnight_spell_art.py --limit 5
```

Afterward icons deploy into:
`{mod_path() / 'Texture'}`
""",
        encoding="utf-8",
    )

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "spells": len(spells),
        "pending_icons": len(pending_icon),
        "pending_concepts": len(pending_concept),
        "copied": copied,
        "elin_texture": str(mod_path() / "Texture"),
        "start": str(ps1),
    }
    (_SF_EXPORT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exported {_SF_EXPORT}")
    print(f"  pending icons={len(pending_icon)} concepts={len(pending_concept)} copied={copied}")
    return _SF_EXPORT


def overnight(spells: List[Dict[str, Any]], **kwargs) -> Dict[str, int]:
    """Legacy entry — this pack uses Cursor GenerateImage, not SD.

    Prefer: agents call GenerateImage → elin_deploy_cursor_spell_art.py
    This function only re-exports staging; it will not start Stable Diffusion.
    """
    print("NOTE: spell art overnight is Cursor GenerateImage only (no SD).")
    print("Generate {Act}_concept.png via Cursor, then run elin_deploy_cursor_spell_art.py")
    export_starfield(spells)
    return {"exported": len(spells)}


def fix_deploy_script() -> None:
    """Patch elin_deploy_real_assets.py so Act icons never come from system concepts."""
    path = _ELIN / "elin_deploy_real_assets.py"
    text = path.read_text(encoding="utf-8")
    old = """    # Spell Act icons — reuse system concept art (Workshop Act*.png = 48x48)
    for sp in spells:
        hid = system_for_spell(sp, heroes)
        src = icon_source(hid) or concept_path(hid)
        if not src:
            continue
        act_name = "Act" + pascal(sp["name"])
        dest = tex / f"{act_name}.png"
        write_png(src, dest, 48)
        counts["act48"] += 1
    print(f"[tex] wrote {counts['act48']} Act*.png icons")
"""
    new = """    # Spell Act icons — UNIQUE per spell (never reuse system hero concepts).
    # Prefer Output/Concepts/Spells/Icon/Act*_icon.png from elin_unique_spell_art.py
    spell_icon_dir = _OUTPUT / "Concepts" / "Spells" / "Icon"
    for sp in spells:
        act_name = "Act" + pascal(sp["name"])
        dest = tex / f"{act_name}.png"
        src = spell_icon_dir / f"{act_name}_icon.png"
        if not src.is_file():
            # leave existing unique Act icon alone; do not fall back to system art
            if dest.is_file():
                counts["act48"] += 1
            else:
                print(f"[tex] MISSING unique icon for {act_name} — run elin_unique_spell_art.py")
            continue
        write_png(src, dest, 48)
        counts["act48"] += 1
    print(f"[tex] wrote/kept {counts['act48']} unique Act*.png icons")
"""
    if old in text:
        path.write_text(text.replace(old, new), encoding="utf-8")
        print(f"patched {path} (no more system-art Act reuse)")
    elif "UNIQUE per spell" in text:
        print("deploy script already patched")
    else:
        print("WARN: deploy script pattern not found — edit manually")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "cmd",
        choices=("catalog", "generate", "export-starfield", "overnight", "all", "fix-deploy"),
    )
    ap.add_argument("--backend", default="auto", choices=("auto", "sd", "procedural"))
    ap.add_argument("--icons-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="regenerate even if files exist")
    args = ap.parse_args()

    if args.cmd == "fix-deploy":
        fix_deploy_script()
        return 0

    spells = collect_elin_spells()
    print(f"spells collected: {len(spells)}")

    if args.cmd in ("catalog", "all"):
        write_catalog(spells)
        fix_deploy_script()

    if args.cmd in ("generate", "all"):
        if not _SPELL_ART_CAT.is_file():
            write_catalog(spells)
        stats = generate(
            spells,
            backend=args.backend,
            icons_only=args.icons_only,
            limit=args.limit,
            force=args.force,
        )
        print("generate", stats)

    if args.cmd == "overnight":
        if not _SPELL_ART_CAT.is_file():
            write_catalog(spells)
        stats = overnight(
            spells,
            icons_only=args.icons_only,
            limit=args.limit,
            force=args.force,
        )
        print("overnight", stats)

    if args.cmd in ("export-starfield", "all"):
        if not _SPELL_ART_CAT.is_file():
            write_catalog(spells)
        # reload from file so paths match
        spells = json.loads(_SPELL_ART_CAT.read_text(encoding="utf-8"))["spells"]
        export_starfield(spells)

    # uniqueness report for Act icons
    if args.cmd in ("generate", "all", "overnight"):
        tex = mod_path() / "Texture"
        import hashlib
        from collections import Counter

        hashes = Counter()
        for p in tex.glob("Act*.png"):
            hashes[hashlib.md5(p.read_bytes()).hexdigest()] += 1
        print(f"Act uniqueness: {len(hashes)} unique hashes / {sum(hashes.values())} files")
        print(f"  dup groups (>=2): {sum(1 for c in hashes.values() if c >= 2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
