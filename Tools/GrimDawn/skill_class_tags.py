#!/usr/bin/env python3
"""
Skill class tags -- regenerated "GDMod-SkillClassTags" labels (e.g. 'Grenado {^H}[De]').

The original mod ships hand-edited copies of the official skill text files, so it only knows
the 9 pre-FoA classes and goes stale with every game patch. This rebuilds the labels from the
*current* text every run:

  * build mode (default): every class on a mod's roster -- official, Berserker, and all mod
    masteries -- gets a label on each of its skills, written to
    localization/tags_skill_class_labels.txt and injected into the mod's Text_EN.arc
  * --base-game: regenerates the SkillClassTags mod folder's own text_en files from the current
    official text (adds gdx3 + Berserker), keeping its _ChangeClassTagFormat.cmd workflow

Color and official tags come from that mod's _ChangeClassTagFormat.ini; tags for other classes
are generated once (short, unique) and remembered in profiles/skill_class_tags.json so they stay
stable across rebuilds -- edit that file to rename any of them.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from class_combo_names import (
    GENERATED_MARKER,
    collect_all_text_tags,
    discover_mastery_ids,
    extract_text_roots,
    harvest_tag_roots,
    mod_text_roots,
)
from dbr_io import get_list_field, read_dbr

TOOLS_DIR = Path(__file__).resolve().parent
PROFILE = TOOLS_DIR / "profiles" / "skill_class_tags.json"
LABEL_FILE = "tags_skill_class_labels.txt"
OFFICIAL_TAGS = {
    "Soldier": "[So]", "Demolitionist": "[De]", "Occultist": "[Oc]", "Nightblade": "[Ni]",
    "Arcanist": "[Ar]", "Shaman": "[Sh]", "Inquisitor": "[In]", "Necromancer": "[Ne]",
    "Oathkeeper": "[Oa]", "Berserker": "[Be]",
}
INI_KEYS = {f"{name}Tag": name for name in OFFICIAL_TAGS}
OFFICIAL_SKILL_FILES = ("tags_skills.txt", "tagsgdx1_skills.txt", "tagsgdx2_skills.txt", "tagsgdx3_skills.txt")
# an existing label at the end of a skill name, from this tool or the original mod
LABEL_RE = re.compile(r"\s*(?:\^Q)?\{\^\w?\}\[[^\]]{1,8}\](?:\^E)?\s*$")
LINK_KEYS = ("buffSkillName", "petSkillName")


def find_skill_class_tags_mod(game_dir: Path) -> Optional[Path]:
    for d in sorted((Path(game_dir) / "mods").glob("GDMod-SkillClassTags*")):
        if (d / "text_en").is_dir():
            return d
    return None


def load_settings(game_dir: Optional[Path]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """(color, official class -> tag, other class -> tag) from the mod's .ini + our profile."""
    color, official = "{^H}", dict(OFFICIAL_TAGS)
    mod = find_skill_class_tags_mod(game_dir) if game_dir else None
    ini = mod / "text_en" / "_ChangeClassTagFormat.ini" if mod else None
    if ini and ini.is_file():
        for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$", line)
            if not m or line.lstrip().startswith(";"):
                continue
            if m.group(1) == "ClassTagColor":
                color = m.group(2)
            elif m.group(1) in INI_KEYS:
                official[INI_KEYS[m.group(1)]] = m.group(2)
    try:
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))
    except Exception:
        prof = {}
    color = prof.get("color", color)
    official.update(prof.get("official", {}))
    return color, official, dict(prof.get("classes", {}))


def save_profile(color: str, others: Dict[str, str]) -> None:
    try:
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))
    except Exception:
        prof = {"_note": "Skill class labels. 'classes' = mod masteries; edit freely, rebuild to apply."}
    prof.setdefault("color", color)
    prof["classes"] = dict(sorted({**prof.get("classes", {}), **others}.items()))
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(json.dumps(prof, indent=1), encoding="utf-8")


def make_tag(name: str, used: Iterable[str]) -> str:
    """Short unique [Xy] tag for a class name (2 letters, then 3 if needed)."""
    taken = {u.lower() for u in used}
    letters = re.sub(r"[^A-Za-z]", "", name) or "Xx"
    words = re.findall(r"[A-Za-z]+", name)
    cands = [letters[:2]]
    if len(words) > 1:
        cands.append(words[0][0] + words[1][0])
    cands += [letters[0] + c for c in letters[2:]] + [letters[:3]]
    cands += [letters[:2] + str(i) for i in range(2, 10)]
    for c in cands:
        tag = f"[{c[0].upper()}{c[1:].lower()}]"
        if tag.lower() not in taken:
            return tag
    return f"[{letters[:4].title()}]"


class RecordLookup:
    """Find a record in the build first, then in official layers (newest first)."""

    def __init__(self, db: Path, vanilla_cache: Path):
        self.roots = [Path(db)]
        layers = Path(vanilla_cache) / "layers"
        if layers.is_dir():
            gdx = sorted(
                (d for d in layers.iterdir() if re.fullmatch(r"gdx\d+", d.name.lower())),
                key=lambda d: int(d.name[3:]),
                reverse=True,
            )
            self.roots += gdx + [layers / "database"]

    def read(self, rel: str) -> Optional[Dict[str, str]]:
        rel = rel.strip().replace("\\", "/")
        for root in self.roots:
            p = root / rel
            if p.is_file():
                try:
                    return read_dbr(p)
                except Exception:
                    return None
        return None


def _links(rec: Dict[str, str]) -> List[str]:
    """Records a skill hands off to: buffs, pet skills, summoned pets and the pets' own skills."""
    out: List[str] = []
    for key in LINK_KEYS + ("spawnObjects",):
        out += [v for v in (rec.get(key) or "").split(";") if v.strip().lower().endswith(".dbr")]
    if (rec.get("Class") or "").lower().startswith("monster") or "pet" in (rec.get("templateName") or "").lower():
        out += [v for v in get_list_field(rec, "skillName") if v.strip().lower().endswith(".dbr")]
    return out


def class_skill_tags(lookup: RecordLookup, tree_rel: str) -> List[str]:
    """skillDisplayName tags of every skill on a class tree incl. its buffs and pet abilities."""
    tree = lookup.read(tree_rel)
    if not tree:
        return []
    tags: List[str] = []
    seen = set()
    for i, rel in enumerate(get_list_field(tree, "skillName")):
        if i == 0 or not rel.strip():
            continue  # skillName1 is the mastery (its name is the class name)
        frontier = [(rel, 0)]
        while frontier:
            cur, depth = frontier.pop()
            key = cur.strip().replace("\\", "/").lower()
            if key in seen or depth > 3:
                continue
            seen.add(key)
            rec = lookup.read(cur)
            if not rec:
                continue
            tag = rec.get("skillDisplayName", "").strip()
            if tag and tag not in tags:
                tags.append(tag)
            frontier += [(link, depth + 1) for link in _links(rec)]
    return tags


def label_map(
    lookup: RecordLookup,
    roster: Sequence[str],
    names: Dict[str, str],
    color: str,
    official: Dict[str, str],
    others: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """{skill tag (lower) -> label suffix}, plus any newly generated class tags."""
    used = set(official.values()) | set(others.values())
    new: Dict[str, str] = {}
    labels: Dict[str, List[str]] = {}
    for i, tree in enumerate(roster):
        name = names.get(f"{i + 1:02d}", "")
        if not name:
            continue
        tag = official.get(name) or others.get(name) or new.get(name)
        if not tag:
            tag = make_tag(name, used)
            used.add(tag)
            new[name] = tag
        for skill in class_skill_tags(lookup, tree):
            labels.setdefault(skill.lower(), [])
            if tag not in labels[skill.lower()]:
                labels[skill.lower()].append(tag)
    return {k: f" {color}{''.join(v)}" for k, v in labels.items()}, new


def _labeled(value: str, suffix: str) -> str:
    return LABEL_RE.sub("", value).rstrip() + suffix


def generate_build_labels(
    mod_db: Path,
    out_file: Path,
    *,
    game_dir: Optional[Path],
    vanilla_cache: Path = TOOLS_DIR / "work" / "_vanilla_cache",
    work: Path = TOOLS_DIR / "work",
) -> int:
    """Write label overrides for every class skill on the build's roster. Returns line count."""
    out_mod = out_file.parent.parent if out_file.parent.name == "localization" else out_file.parent
    roots = list(harvest_tag_roots(mod_db, out_mod))
    if game_dir:
        roots += extract_text_roots(Path(game_dir), [], work)
        roots += mod_text_roots(Path(game_dir), out_mod, work)
    text = collect_all_text_tags(roots)
    keys = {}
    for root in roots:  # keep original key casing for output
        for path in (Path(root).rglob("*.txt") if Path(root).is_dir() else []):
            if path.name == LABEL_FILE:
                continue
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                k = line.split("=", 1)[0].strip()
                if k.lower().startswith("tag"):
                    keys.setdefault(k.lower(), k)

    pc = mod_db / "records/creatures/pc/malepc01.dbr"
    roster = get_list_field(read_dbr(pc), "skillTree") if pc.is_file() else []
    names = discover_mastery_ids(mod_db, text)
    color, official, others = load_settings(game_dir)
    labels, new = label_map(RecordLookup(mod_db, vanilla_cache), roster, names, color, official, others)
    if new:
        save_profile(color, new)
        print(f"New class tags: {new} (saved to {PROFILE.name})", flush=True)

    lines = [GENERATED_MARKER + " -- skill class labels; regenerate instead of editing"]
    for key in sorted(labels):
        value = text.get(key)
        if value:
            lines.append(f"{keys.get(key, key)}={_labeled(value, labels[key])}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Skill class labels: {len(lines) - 1} skills across {len(roster)} classes -> {out_file}", flush=True)
    return len(lines) - 1


def regenerate_base_game_mod(
    game_dir: Path,
    *,
    vanilla_cache: Path = TOOLS_DIR / "work" / "_vanilla_cache",
    work: Path = TOOLS_DIR / "work",
) -> Path:
    """Rebuild GDMod-SkillClassTags text_en from current official text (adds gdx3/Berserker)."""
    mod = find_skill_class_tags_mod(game_dir)
    if not mod:
        raise FileNotFoundError("GDMod-SkillClassTags folder not found under mods/")
    text_dir = mod / "text_en"
    backup = mod / "_original_text_en"
    if not backup.exists():
        shutil.copytree(text_dir, backup)

    roots = extract_text_roots(Path(game_dir), [], work)
    gdx3_pc = Path(vanilla_cache) / "layers"
    newest = sorted((d for d in gdx3_pc.glob("gdx*") if d.name[3:].isdigit()), key=lambda d: int(d.name[3:]))
    pc_root = newest[-1] if newest else gdx3_pc / "database"
    roster = get_list_field(read_dbr(pc_root / "records/creatures/pc/malepc01.dbr"), "skillTree")
    names = {f"{i + 1:02d}": n for i, n in enumerate(OFFICIAL_TAGS)}
    color, official, _ = load_settings(game_dir)
    # .base files keep the mod's default {^H} + default tags so its .cmd can re-skin them
    lookup = RecordLookup(pc_root, vanilla_cache)
    base_labels, _ = label_map(lookup, roster, names, "{^H}", dict(OFFICIAL_TAGS), {})
    live_labels, _ = label_map(lookup, roster, names, color, official, {})

    written = 0
    for name in OFFICIAL_SKILL_FILES:
        src = next((r / "text_en" / name for r in roots if (r / "text_en" / name).is_file()), None)
        if src is None:
            continue
        raw = src.read_text(encoding="utf-8", errors="replace").splitlines()
        for labels, out in ((base_labels, text_dir / f"{name}.base"), (live_labels, text_dir / name)):
            lines = []
            for line in raw:
                k, sep, v = line.partition("=")
                suffix = labels.get(k.strip().lower()) if sep else None
                lines.append(f"{k}={_labeled(v, suffix)}" if suffix else line)
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += 1
    _patch_cmd(text_dir)
    print(f"Regenerated {written} skill text files in {text_dir} (originals in {backup.name})", flush=True)
    return text_dir


def _patch_cmd(text_dir: Path) -> None:
    """Teach the mod's _ChangeClassTagFormat.cmd/.ini about gdx3 and Berserker."""
    cmd = text_dir / "_ChangeClassTagFormat.cmd"
    if cmd.is_file():
        s = cmd.read_text(encoding="utf-8", errors="replace")
        s = s.replace(
            'set "BaseFiles=tags_skills.txt.base tagsgdx1_skills.txt.base tagsgdx2_skills.txt.base"',
            'set "BaseFiles=tags_skills.txt.base tagsgdx1_skills.txt.base tagsgdx2_skills.txt.base tagsgdx3_skills.txt.base"',
        )
        if "BerserkerTag" not in s:
            s = s.replace("echo Oathkeeper: !OathkeeperTag!", "echo Oathkeeper: !OathkeeperTag!\necho Berserker: !BerserkerTag!")
            s = s.replace(
                "\"-replace '\\[Oa\\]', '!OathkeeperTag!' \" ^",
                "\"-replace '\\[Oa\\]', '!OathkeeperTag!' \" ^\n    \"-replace '\\[Be\\]', '!BerserkerTag!' \" ^",
            )
        cmd.write_text(s, encoding="utf-8")
    ini = text_dir / "_ChangeClassTagFormat.ini"
    if ini.is_file():
        s = ini.read_text(encoding="utf-8", errors="replace")
        if "BerserkerTag" not in s:
            s = s.rstrip() + "\nBerserkerTag=[Be]\n"
            s = s.replace("[Ne],[Oa])", "[Ne],[Oa],[Be])")
            ini.write_text(s, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Regenerate skill class labels (SkillClassTags)")
    p.add_argument("--game", default=None)
    p.add_argument("--mod", default=None, help="Build (mods/<name>, unpacked database) to label")
    p.add_argument("--base-game", action="store_true", help="Regenerate the SkillClassTags mod's own files")
    p.add_argument("--no-inject", action="store_true", help="Build mode: don't repack Text_EN.arc")
    args = p.parse_args(argv)

    from gd_paths import GamePaths, resolve_game_dir

    game = GamePaths(resolve_game_dir(args.game))
    if args.base_game:
        regenerate_base_game_mod(game.game_dir)
    if args.mod:
        root = Path(args.mod) if Path(args.mod).is_dir() else game.mods_dir / args.mod
        out = root / "localization" / LABEL_FILE
        n = generate_build_labels(root / "database", out, game_dir=game.game_dir)
        if n and not args.no_inject:
            from fill_combo_tags import inject_tags_into_text_arc

            print(inject_tags_into_text_arc(game, root, [out], create=True))
    if not (args.base_game or args.mod):
        p.error("pass --mod NAME and/or --base-game")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
