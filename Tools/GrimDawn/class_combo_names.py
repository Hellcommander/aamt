#!/usr/bin/env python3
"""Generate tagSkillClassName combo names for all mastery pairs (gaps only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore

COMMON_DIR = Path(__file__).resolve().parent.parent / "Common"
if COMMON_DIR.is_dir() and str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

TAG_RE = re.compile(r"^(tagSkillClassName\w+)\s+(.+)$", re.IGNORECASE)
TAG_EQ_RE = re.compile(r"^(tagSkillClassName\w+)\s*=\s*(.+)$", re.IGNORECASE)

DEFAULT_MASTERIES = {
    "01": "Soldier",
    "02": "Demolitionist",
    "03": "Occultist",
    "04": "Nightblade",
    "05": "Arcanist",
    "06": "Shaman",
    "07": "Inquisitor",
    "08": "Necromancer",
    "09": "Oathkeeper",
    "10": "Berserker",
}

OLLAMA_BATCH = 40


def parse_tag_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("#"):
            continue
        m = TAG_RE.match(s) or TAG_EQ_RE.match(s)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def collect_tags(roots: List[Path]) -> Dict[str, str]:
    tags: Dict[str, str] = {}
    for root in roots:
        if not root or not Path(root).exists():
            continue
        root = Path(root)
        if root.is_file():
            tags.update(parse_tag_file(root))
            continue
        for path in root.rglob("*.txt"):
            tags.update(parse_tag_file(path))
    return tags


def _pretty_from_path(tree_rel: str) -> str:
    t = tree_rel.replace("\\", "/").lower()
    m = re.search(r"playerclass(\d{2})", t)
    if m and m.group(1) in DEFAULT_MASTERIES:
        return DEFAULT_MASTERIES[m.group(1)]
    m = re.search(
        r"(?:playerclass|zenithclass|ddclass)?([a-z][a-z0-9]+)(?:/_classtree|_skilltree|/)",
        t,
    )
    if m:
        name = m.group(1)
        if name.isdigit():
            return DEFAULT_MASTERIES.get(name, f"Class{name}")
        return name.replace("_", " ").title().replace(" ", "")
    stem = Path(tree_rel).stem
    stem = re.sub(r"^_?classtree_?", "", stem, flags=re.I)
    stem = re.sub(r"^class", "", stem, flags=re.I)
    return stem.replace("_", " ").title().replace(" ", "") or "Unknown"


def discover_mastery_ids(mod_db: Path) -> Dict[str, str]:
    """Prefer PC skillTree order as 01..N (matches class UI slots)."""
    from dbr_io import get_list_field, read_dbr

    found = dict(DEFAULT_MASTERIES)
    pc = mod_db / "records/creatures/pc/malepc01.dbr"
    if pc.is_file():
        trees = get_list_field(read_dbr(pc), "skillTree")
        for i, tree in enumerate(trees):
            mid = f"{i + 1:02d}" if i + 1 < 100 else str(i + 1)
            tl = tree.replace("\\", "/").lower()
            if mid in DEFAULT_MASTERIES and f"playerclass{mid}" in tl:
                found[mid] = DEFAULT_MASTERIES[mid]
            else:
                found[mid] = _pretty_from_path(tree)
        return found

    for p in mod_db.rglob("*"):
        name = p.name.lower()
        m = re.search(r"playerclass(\d{2})|class(\d{2})", name)
        if m:
            mid = m.group(1) or m.group(2)
            found.setdefault(mid, f"Class{mid}")
    return found


def _tag_for_pair(a: str, b: str) -> Tuple[str, str]:
    x, y = sorted([a, b], key=lambda s: (len(s), s))
    return f"tagSkillClassName{x}{y}", f"tagSkillClassName{y}{x}"


def missing_berserker_combos(
    tags: Dict[str, str], masteries: Dict[str, str], berserker_id: str = "10"
) -> List[Tuple[str, str, str]]:
    return missing_combos_for_ids(tags, masteries, anchor_id=berserker_id)


def missing_all_combos(
    tags: Dict[str, str], masteries: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    return missing_combos_for_ids(tags, masteries, anchor_id=None)


def missing_combos_for_ids(
    tags: Dict[str, str],
    masteries: Dict[str, str],
    *,
    anchor_id: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    missing: List[Tuple[str, str, str]] = []
    existing = {k.lower() for k in tags}
    ids = sorted(masteries.keys(), key=lambda s: (len(s), s))
    if anchor_id:
        if anchor_id not in masteries:
            return []
        pairs = [(anchor_id, p) for p in ids if p != anchor_id]
    else:
        pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]

    for a, b in pairs:
        tag, alt = _tag_for_pair(a, b)
        if tag.lower() not in existing and alt.lower() not in existing:
            missing.append((tag, masteries.get(a, a), masteries.get(b, b)))
    return missing


def resolve_ollama_model(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    try:
        from ollama_model_router import get_router

        return get_router().get_model_for_task("visual")
    except Exception:
        return "llama3.1:8b"


def ollama_options(model: str) -> Dict:
    try:
        from ollama_model_router import get_router

        return get_router().get_ollama_api_options(
            model_name=model,
            temperature=0.85,
            top_p=0.9,
            num_predict=1024,
        )
    except Exception:
        return {"temperature": 0.85, "top_p": 0.9}


def ollama_generate(
    model: str,
    pairs: List[Tuple[str, str, str]],
    host: str = "http://127.0.0.1:11434",
) -> Dict[str, str]:
    if requests is None:
        raise RuntimeError("requests package required for Ollama calls")
    out: Dict[str, str] = {}
    for i in range(0, len(pairs), OLLAMA_BATCH):
        batch = pairs[i : i + OLLAMA_BATCH]
        prompt = (
            "You name Grim Dawn dual-class combinations. Style: short fantasy titles "
            "(one or two words), like Blademaster, Elementalist, Spellbreaker.\n"
            "Return ONLY JSON object mapping tag -> name.\n"
            "Pairs:\n"
            + "\n".join(f"- {tag}: {a} + {b}" for tag, a, b in batch)
        )
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": ollama_options(model),
        }
        r = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json=payload,
            timeout=180,
        )
        r.raise_for_status()
        raw = r.json().get("response", "{}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else {}
        out.update({str(k): str(v) for k, v in data.items()})
    return out


def placeholder_names(pairs: List[Tuple[str, str, str]]) -> Dict[str, str]:
    return {tag: f"{a}{b}" for tag, a, b in pairs}


def write_tags(path: Path, new_tags: Dict[str, str], existing: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    have = {
        l.split()[0].lower()
        for l in lines
        if l.strip() and not l.strip().startswith("//")
    }
    for tag, name in sorted(new_tags.items()):
        if tag.lower() in have:
            continue
        lines.append(f"{tag} {name}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def harvest_tag_roots(
    mod_db: Path,
    out_mod: Path,
    game_mods: Optional[Path] = None,
) -> List[Path]:
    roots: List[Path] = [
        mod_db,
        out_mod / "localization",
        out_mod / "resources",
        out_mod / "source",
    ]
    if game_mods and game_mods.is_dir():
        for name in ("grimarillion", "dom", "Rebirth", "Nydiamar", "ReignOfTerror"):
            base = game_mods / name
            for sub in (
                base / "resources" / "text_en",
                base / "resources" / "Text_EN",
                base / "localization",
                base / "source" / "text_en",
            ):
                if sub.is_dir():
                    roots.append(sub)
    return roots


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate dual-class combo name tags")
    p.add_argument("--mod-db", required=True)
    p.add_argument("--tag-roots", nargs="*", default=[])
    p.add_argument("--out-tags", required=True)
    p.add_argument("--game-mods", default=None)
    p.add_argument("--berserker-only", action="store_true")
    p.add_argument("--ollama-model", default=None)
    p.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    p.add_argument("--dry-run-names", action="store_true")
    p.add_argument(
        "--ollama-limit",
        type=int,
        default=0,
        help="Ollama-polish at most N pairs (0=placeholders only, -1=all)",
    )
    args = p.parse_args(argv)

    mod_db = Path(args.mod_db)
    out_tags = Path(args.out_tags)
    roots = harvest_tag_roots(
        mod_db,
        out_tags.parent.parent if out_tags.parent.name == "localization" else out_tags.parent,
        Path(args.game_mods) if args.game_mods else None,
    )
    roots.extend(map(Path, args.tag_roots))
    tags = collect_tags(roots)
    masteries = discover_mastery_ids(mod_db)

    if args.berserker_only:
        missing = missing_berserker_combos(tags, masteries)
        mode = "Berserker-only"
    else:
        missing = missing_all_combos(tags, masteries)
        mode = "all-pairs"

    print(
        f"Masteries: {len(masteries)}  Existing combo tags: {len(tags)}  "
        f"Missing ({mode}): {len(missing)}"
    )
    if not missing:
        print("Nothing to generate.")
        return 0

    generated = placeholder_names(missing)
    if not args.dry_run_names and args.ollama_limit != 0:
        model = resolve_ollama_model(args.ollama_model)
        limit = len(missing) if args.ollama_limit < 0 else args.ollama_limit
        polish = missing[:limit]
        print(f"Ollama model: {model} (polishing {len(polish)} / {len(missing)})")
        try:
            generated.update(ollama_generate(model, polish, args.ollama_host))
        except Exception as exc:
            print(f"Ollama failed ({exc}); keeping placeholders", file=sys.stderr)

    write_tags(out_tags, generated, tags)
    print(f"Wrote {len(generated)} tags -> {out_tags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
