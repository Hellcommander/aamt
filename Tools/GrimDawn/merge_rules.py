#!/usr/bin/env python3
"""
Per-mod merge rewiring rules.

Each mod can have a JSON file under profiles/merge_rules/<id>.json.
When a merge/playground run includes that mod, the tool applies those rules
automatically — case-by-case, based on the mod (no AI step).

Supported fields:
  mode: content | class | portal
  enabled: bool — false skips the mod entirely (still listed in profile/rules)
  priority: int — higher wins file/content conflicts (default 50)
  class_priority: int — higher wins class-tree / hub conflicts (defaults to priority)
  skip_overlay_prefixes: string[] — relative DB paths this mod will NOT write
  conflict_merge: bool — when true, overlapping .dbr files field-merge instead of replace
  conflict_merge_prefixes: string[] — limit field-merge to these path prefixes (default: all)
  prefer_field_substrings: string[] — on field conflicts, prefer this mod's value if key matches
  keep_base_field_substrings: string[] — on field conflicts, keep already-merged (base) value
  quest_remap / quest_prefix
  skip_world_maps
  items_mode: merge | isolate | namespace
    merge     — overlay items into the target mod (default)
    isolate   — keep items in the mod world only (do not flood Survival/base)
    namespace — move under records/items/<prefix>/ then overlay (shared but non-colliding)

Default priority ladder (higher wins; unique non-overlapping files still merge):
  100 Riftwalk (enabled:false — OP)
   96 Wereform Buffs (tiny playerclass10 wereform overlay)
   92 Rebirth (FoA mastery skill + AI/controller + enemy rewires; skips items overlay)
   90 Grimarillion (mega content / custom classes)
   80 ReignOfTerror (portal; items isolate; low class_priority)
   70 Dawn of Masteries (extra masteries; loses shared base-class files to Rebirth/Grim)
   60 ShatteredAffixes (affix/loot systems)
   30 Nydiamar (portal)

AI authors these JSON files once; the tool sorts and applies them every run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

TOOLS_DIR = Path(__file__).resolve().parent
RULES_DIR = TOOLS_DIR / "profiles" / "merge_rules"

# Paths skipped when items_mode=isolate (mod-world loot stays out of Survival/base)
ITEM_ISOLATE_PREFIXES = (
    "records/items/",
)

# Paths moved when items_mode=namespace
ITEM_NAMESPACE_BASE = "records/items"

DEFAULT_PRIORITY = 50


@dataclass
class ModMergeRules:
    """Case-by-case rewiring for one mod."""

    id: str
    match: List[str] = field(default_factory=list)
    mode: str = "content"  # content | class | portal
    enabled: bool = True
    # Higher = more authoritative on conflicts (applied later / overwrites)
    priority: int = DEFAULT_PRIORITY
    # Class skill trees / hubs; defaults to priority when unset in JSON
    class_priority: int = DEFAULT_PRIORITY
    # Relative path prefixes this mod must not overlay (defer to other packs)
    skip_overlay_prefixes: List[str] = field(default_factory=list)
    # Field-level merge on overlapping DBRs (preserve unique keys from both mods)
    conflict_merge: bool = False
    conflict_merge_prefixes: List[str] = field(default_factory=list)
    prefer_field_substrings: List[str] = field(default_factory=list)
    keep_base_field_substrings: List[str] = field(default_factory=list)
    quest_remap: bool = False
    quest_prefix: Optional[str] = None
    skip_world_maps: bool = False
    skip_unnamespaced_quests: bool = False
    # merge = flood into target; isolate = keep in mod world; namespace = prefix paths
    items_mode: str = "merge"
    items_prefix: Optional[str] = None
    protect_achievements: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], fallback_id: str = "") -> "ModMergeRules":
        items_mode = str(data.get("items_mode") or "merge").lower()
        if items_mode not in ("merge", "isolate", "namespace"):
            items_mode = "merge"
        priority = int(data.get("priority", DEFAULT_PRIORITY))
        class_priority = (
            int(data["class_priority"])
            if "class_priority" in data and data["class_priority"] is not None
            else priority
        )
        skip_prefixes = [
            str(x).replace("\\", "/").lower()
            for x in (data.get("skip_overlay_prefixes") or [])
        ]
        merge_prefixes = [
            str(x).replace("\\", "/").lower()
            for x in (data.get("conflict_merge_prefixes") or [])
        ]
        return cls(
            id=str(data.get("id") or fallback_id),
            match=[str(x) for x in data.get("match", [])],
            mode=str(data.get("mode") or "content"),
            enabled=bool(data.get("enabled", True)),
            priority=priority,
            class_priority=class_priority,
            skip_overlay_prefixes=skip_prefixes,
            conflict_merge=bool(data.get("conflict_merge", False)),
            conflict_merge_prefixes=merge_prefixes,
            prefer_field_substrings=[str(x) for x in (data.get("prefer_field_substrings") or [])],
            keep_base_field_substrings=[
                str(x) for x in (data.get("keep_base_field_substrings") or [])
            ],
            quest_remap=bool(data.get("quest_remap", False)),
            quest_prefix=data.get("quest_prefix"),
            skip_world_maps=bool(data.get("skip_world_maps", False)),
            skip_unnamespaced_quests=bool(
                data.get("skip_unnamespaced_quests", data.get("quest_remap", False))
            ),
            items_mode=items_mode,
            items_prefix=data.get("items_prefix"),
            protect_achievements=bool(data.get("protect_achievements", False)),
            notes=str(data.get("notes") or ""),
        )


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def load_all_rules(rules_dir: Optional[Path] = None) -> List[ModMergeRules]:
    root = rules_dir or RULES_DIR
    rules: List[ModMergeRules] = []
    if not root.is_dir():
        return rules
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rules.append(ModMergeRules.from_dict(data, fallback_id=path.stem))
    return rules


def find_rules_for_mod(
    mod_name_or_path: str,
    rules: Optional[List[ModMergeRules]] = None,
) -> Optional[ModMergeRules]:
    """Return the first matching per-mod rule, if any."""
    name = Path(mod_name_or_path).name
    key = _norm(name)
    for rule in rules or load_all_rules():
        needles = rule.match or [rule.id]
        for needle in needles:
            n = _norm(needle)
            if n and (n in key or key in n or needle.lower() in name.lower()):
                return rule
    return None


def default_quest_prefix(mod_name: str) -> str:
    cleaned = _norm(mod_name)
    return cleaned[:24] or "portalmod"


def default_items_prefix(mod_name: str) -> str:
    return default_quest_prefix(mod_name)


def should_skip_item_rel(rel_posix: str, rules: Optional[ModMergeRules]) -> bool:
    """True if this relative DB path should not enter the merge target."""
    if not rules or rules.items_mode != "isolate":
        return False
    r = rel_posix.replace("\\", "/").lower()
    return any(r.startswith(p) for p in ITEM_ISOLATE_PREFIXES)


def should_skip_overlay_rel(rel_posix: str, rules: Optional[ModMergeRules]) -> bool:
    """True if rules.skip_overlay_prefixes says this mod must not write the path."""
    if not rules or not rules.skip_overlay_prefixes:
        return False
    r = rel_posix.replace("\\", "/").lower()
    return any(r.startswith(p) for p in rules.skip_overlay_prefixes)


def should_field_merge_rel(rel_posix: str, rules: Optional[ModMergeRules]) -> bool:
    """True if this path should use targeted field merge on overwrite."""
    if not rules or not rules.conflict_merge:
        return False
    if Path(rel_posix).suffix.lower() != ".dbr":
        return False
    r = rel_posix.replace("\\", "/").lower()
    if not rules.conflict_merge_prefixes:
        return True
    return any(r.startswith(p) for p in rules.conflict_merge_prefixes)


def rules_for_mod(
    mod_name_or_path: str,
    rules: Optional[List[ModMergeRules]] = None,
) -> ModMergeRules:
    """Lookup rules or a neutral default (priority 50)."""
    found = find_rules_for_mod(mod_name_or_path, rules)
    if found:
        return found
    name = Path(mod_name_or_path).name
    return ModMergeRules(id=_norm(name) or "unknown", match=[name])


def filter_enabled_mods(
    mods: Sequence[Path],
    rules: Optional[List[ModMergeRules]] = None,
) -> Tuple[List[Path], List[str]]:
    """Drop mods with enabled=false. Returns (kept, skipped_names)."""
    all_rules = rules if rules is not None else load_all_rules()
    kept: List[Path] = []
    skipped: List[str] = []
    for mod in mods:
        r = rules_for_mod(mod.name, all_rules)
        if r.enabled:
            kept.append(mod)
        else:
            skipped.append(mod.name)
    return kept, skipped


def sort_mods_by_priority(
    mods: Sequence[Path],
    rules: Optional[List[ModMergeRules]] = None,
    *,
    class_aware: bool = False,
) -> List[Path]:
    """
    Ascending priority so later overlays win.
    class_aware=True uses class_priority (for mastery/skill tree merges).
    Stable tie-break: original list order.
    """
    all_rules = rules if rules is not None else load_all_rules()

    def key(item: Tuple[int, Path]) -> Tuple[int, int]:
        idx, mod = item
        r = rules_for_mod(mod.name, all_rules)
        p = r.class_priority if class_aware else r.priority
        return (p, idx)

    indexed = list(enumerate(mods))
    indexed.sort(key=key)
    return [m for _, m in indexed]


def paired_sort_by_priority(
    mods: Sequence[Path],
    dbs: Sequence[Path],
    rules: Optional[List[ModMergeRules]] = None,
    *,
    class_aware: bool = False,
) -> List[Tuple[Path, Path]]:
    """Sort (mod, db) pairs the same way as sort_mods_by_priority."""
    if len(mods) != len(dbs):
        raise ValueError("mods and dbs length mismatch")
    all_rules = rules if rules is not None else load_all_rules()

    def key(item: Tuple[int, Path, Path]) -> Tuple[int, int]:
        idx, mod, _db = item
        r = rules_for_mod(mod.name, all_rules)
        p = r.class_priority if class_aware else r.priority
        return (p, idx)

    triples = list(zip(range(len(mods)), mods, dbs))
    triples.sort(key=key)
    return [(mod, db) for _, mod, db in triples]
