"""Parse and write Grim Dawn .dbr records (key,value, lines)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def read_dbr(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        # Format: key,value,  (value may contain commas rarely; take first comma split)
        if "," not in line:
            continue
        key, rest = line.split(",", 1)
        value = rest[:-1] if rest.endswith(",") else rest
        data[key.strip()] = value
    return data


def write_dbr(path: Path, data: Dict[str, str], preferred_order: Optional[Iterable[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: List[str] = []
    seen = set()
    if preferred_order:
        for k in preferred_order:
            if k in data and k not in seen:
                keys.append(k)
                seen.add(k)
    for k in data:
        if k not in seen:
            keys.append(k)
            seen.add(k)
    lines = [f"{k},{data[k]}," for k in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_list_field(data: Dict[str, str], prefix: str) -> List[str]:
    """Collect numbered fields like skillTree1, skillTree2, ... (case-insensitive prefix)."""
    items: List[Tuple[int, str]] = []
    pl = prefix.lower()
    for key, value in data.items():
        kl = key.lower()
        if kl.startswith(pl):
            suffix = kl[len(pl) :]
            if suffix.isdigit():
                items.append((int(suffix), value))
    items.sort(key=lambda x: x[0])
    return [v for _, v in items]


def _canonical_list_key(prefix: str, index: int) -> str:
    """Map common prefixes to Grim Dawn camelCase field names."""
    canon = {
        "skilltree": "skillTree",
        "skillctrlpane": "skillCtrlPane",
        "classselection": "ClassSelection",
        "skillname": "skillName",
    }.get(prefix.lower())
    base = canon or prefix
    return f"{base}{index}"


def set_list_field(data: Dict[str, str], prefix: str, values: List[str]) -> None:
    """Replace numbered list fields; remove extras beyond len(values)."""
    pl = prefix.lower()
    for key in list(data.keys()):
        kl = key.lower()
        if kl.startswith(pl) and kl[len(pl) :].isdigit():
            del data[key]
    for i, value in enumerate(values, start=1):
        data[_canonical_list_key(prefix, i)] = value


def merge_list_field(mod_data: Dict[str, str], vanilla_data: Dict[str, str], prefix: str) -> List[str]:
    """Union lists preserving mod order, then append missing vanilla entries."""
    mod_list = get_list_field(mod_data, prefix)
    van_list = get_list_field(vanilla_data, prefix)
    out = list(mod_list)
    seen = {x.lower() for x in out}
    for item in van_list:
        if item.lower() not in seen:
            out.append(item)
            seen.add(item.lower())
    return out


def merge_semicolon_field(mod_value: str, vanilla_value: str) -> str:
    """Union semicolon-separated lists; mod entries first, then missing vanilla."""
    def parts(s: str) -> List[str]:
        return [p.strip() for p in (s or "").split(";") if p.strip()]

    out = parts(mod_value)
    seen = {x.lower() for x in out}
    for item in parts(vanilla_value):
        if item.lower() not in seen:
            out.append(item)
            seen.add(item.lower())
    return ";".join(out)


def merge_records(
    mod: Dict[str, str],
    dlc: Dict[str, str],
    *,
    prefer_mod_keys: Optional[Iterable[str]] = None,
    list_prefixes: Optional[Iterable[str]] = None,
    semicolon_keys: Optional[Iterable[str]] = None,
) -> Dict[str, str]:
    """
    Field-level merge: start from DLC, overlay mod keys.
    Numbered list prefixes are union-merged (mod class lines first, then DLC).
    Semicolon keys (class-selection button lists) are union-merged the same way.
    """
    result = dict(dlc)
    prefer = set(prefer_mod_keys or [])
    prefixes = list(list_prefixes or [])
    for prefix in prefixes:
        merged = merge_list_field(mod, dlc, prefix)
        set_list_field(result, prefix, merged)

    for key in semicolon_keys or ():
        if key in mod or key in dlc:
            result[key] = merge_semicolon_field(mod.get(key, ""), dlc.get(key, ""))

    def _is_list_member(key: str) -> bool:
        kl = key.lower()
        for prefix in prefixes:
            pl = prefix.lower()
            if kl.startswith(pl) and kl[len(pl) :].isdigit():
                return True
        return False

    for key, value in mod.items():
        if _is_list_member(key):
            continue
        if key in (semicolon_keys or ()):
            continue
        if key in prefer or key not in dlc or mod.get(key) != dlc.get(key):
            result[key] = value
    return result


def _field_matches_any(key: str, needles: Sequence[str]) -> bool:
    kl = key.lower()
    for n in needles:
        nl = n.lower()
        if not nl:
            continue
        if kl.startswith(nl) or nl in kl:
            return True
    return False


def merge_dbr_preserve_both(
    base: Dict[str, str],
    overlay: Dict[str, str],
    *,
    prefer_overlay_substrings: Optional[Sequence[str]] = None,
    keep_base_substrings: Optional[Sequence[str]] = None,
    list_prefixes: Optional[Iterable[str]] = None,
    semicolon_keys: Optional[Iterable[str]] = None,
) -> Dict[str, str]:
    """
    Targeted conflict merge so neither mod silently drops unique fields.

    - Keys only in base → keep
    - Keys only in overlay → add (nothing lost from overlay-only data)
    - Shared equal values → keep
    - Shared conflicts → keep_base_substrings wins, else prefer_overlay_substrings,
      else overlay (incoming / higher-priority mod)
    - Optional numbered list / semicolon unions when prefixes provided
    """
    prefer_o = list(prefer_overlay_substrings or ())
    keep_b = list(keep_base_substrings or ())
    prefixes = list(list_prefixes or [])
    semi = tuple(semicolon_keys or ())

    result = dict(base)

    for prefix in prefixes:
        merged = merge_list_field(overlay, base, prefix)
        set_list_field(result, prefix, merged)

    for key in semi:
        if key in overlay or key in base:
            result[key] = merge_semicolon_field(overlay.get(key, ""), base.get(key, ""))

    def _is_list_member(key: str) -> bool:
        kl = key.lower()
        for prefix in prefixes:
            pl = prefix.lower()
            if kl.startswith(pl) and kl[len(pl) :].isdigit():
                return True
        return False

    for key, value in overlay.items():
        if _is_list_member(key) or key in semi:
            continue
        if key not in base:
            result[key] = value
            continue
        if base.get(key) == value:
            continue
        if keep_b and _field_matches_any(key, keep_b):
            continue
        if prefer_o and _field_matches_any(key, prefer_o):
            result[key] = value
            continue
        # Default: incoming overlay wins conflicting shared keys
        result[key] = value
    return result
