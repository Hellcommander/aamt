#!/usr/bin/env python3
"""
osfui_gen - generate OSF UI interfaces (settings schemas + custom views) from a
declarative spec, and derive that spec from an existing SFSE plugin INI.

WHY THIS EXISTS
---------------
OSF UI renders HTML/CSS/JS in Starfield through WebView2 and auto-builds a
settings page from a JSON schema. Both halves are plain structured text, which
is exactly what an LLM emits reliably -- but only if it writes to the real
contract. The contract below was recovered from the shipped OSF UI 1.5.0
(OSFUI.dll validation strings, the Preact settings renderer, shared/osfui.js,
shared/osfui.css and Scripts/Source/OSFUI.psc), not guessed, because a schema
that violates it is silently dropped at load with only a log line.

The generator is the trust boundary: a spec is validated against that contract
BEFORE anything is written, so an authoring mistake surfaces as a precise error
here instead of an empty settings page in game.

PIPELINE
--------
    plugin INI  --from-ini-->  spec.json  --build/install-->  Data/SFSE/Plugins/OSFUI/
                                  ^
                                  |  hand-written or LLM-written
                                  |  (see OSF_UI_CONTRACT.md)

OSF UI hot-reloads drop-in schemas, so `install` alone updates a running game's
settings page. Views are reloaded when reopened.

LAYOUT WRITTEN (all relative to the game's Data folder)
-------------------------------------------------------
    SFSE/Plugins/OSFUI/settings/<author>.<modname>.json     settings schema
    SFSE/Plugins/OSFUI/views/<author>.<modname>/<view>/     custom view
        manifest.json  index.html  main.js  style.css

CONTRACT NOTES THAT BITE
------------------------
* Mod id grammar: "<author>.<modname>", lowercase [a-z0-9-] segments, exactly
  one dot. Dotless ids are reserved for the platform. The schema `id` MUST
  equal the settings filename stem, and the view folder MUST equal the mod id.
* Value-bearing setting types are exactly: bool int float enum flags string key.
  `action` is a button (no stored value). Anything else is served read-only.
* A view id is always qualified "<modId>/<viewName>"; a bare name never resolves.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import webbrowser
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = Path(r"F:\SteamLibrary\steamapps\common\Starfield\Data")

# --- the recovered contract ---------------------------------------------------

# Exactly the list the settings renderer switches on (bundle: Je=[...]).
VALUE_TYPES = ("bool", "int", "float", "enum", "flags", "string", "key")
# Entries that render but store nothing.
ENTRY_TYPES = VALUE_TYPES + ("action",)
NUMERIC_TYPES = ("int", "float")

# `widget` narrows the control chosen for a type; anything else falls back to
# that type's default control.
WIDGETS = {
    "int": ("stepper",),
    "float": ("stepper",),
    "enum": ("segmented",),
    "string": ("color", "textarea"),
}

# OSFUI.dll: "mod ids are '<author>.<modname>' (lowercase [a-z0-9-] segments,
# exactly one dot ...); dotless ids are reserved for the platform".
MOD_ID_RE = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")
MOD_ID_MAX = 64
# Bridge commands a plugin registers are "<author>.<modname>.<name>".
COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
# Settings keys are free-form, but keep them boring so Papyrus string interning
# (which folds case) and JSON round-tripping stay predictable.
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
VIEW_NAME_RE = re.compile(r"^[a-z0-9-]+$")

# Manifest keys the host reads. Unknown keys are preserved but meaningless, so
# the validator rejects them to catch typos like "capturesinput".
MANIFEST_KEYS = {
    "$schema", "id", "title", "description", "entry", "mod", "hub", "kind",
    "width", "height", "transparent", "capturesInput", "pausesGame",
    "debugOnly", "readySignal", "permissions", "accent", "icon",
}

# Row kinds the generated renderer implements.
DATA_ROWS = ("stat", "bar", "list")
SETTING_ROWS = ("toggle", "slider", "select")
STATIC_ROWS = ("text", "button")
ROW_KINDS = DATA_ROWS + SETTING_ROWS + STATIC_ROWS


class SpecError(Exception):
    """Raised with a human-actionable message; the CLI prints and exits 2."""


# --- INI -> spec --------------------------------------------------------------

# Some plugin INIs still name keys bEnabled / fMaxEssence. That is an INI habit,
# not an OSF UI rule. Strip it from the public key; type comes from the value.
_HUNGARIAN = {"b": "bool", "f": "float", "i": "int", "s": "string", "u": "int"}
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
_BOOLISH_NAME = re.compile(
    r"^(b)?(is|has|use|allow|enable|enabled|disable|disabled|require|respect|"
    r"pause|verbose|debug|dump|replace|drain|clinical)",
    re.IGNORECASE,
)


def _split_ini_key(key: str) -> tuple[str, str | None]:
    if len(key) > 1 and key[0] in _HUNGARIAN and key[1].isupper():
        return key[1:], _HUNGARIAN[key[0]]
    return key, None


def _ini_type(name: str, raw: str, hinted: str | None) -> str:
    token = raw.strip().lower()
    if token in ("true", "false", "yes", "no", "on", "off"):
        return "bool"
    if token in ("0", "1") and (hinted == "bool" or _BOOLISH_NAME.match(name)):
        return "bool"
    if hinted == "string" or not _is_number(raw):
        return "string"
    if hinted == "float" or "." in raw:
        return "float"
    return "int"


def _as_bool(raw: str) -> bool:
    return raw.strip().lower() in _TRUE


def _is_number(raw: str) -> bool:
    try:
        float(raw)
        return True
    except ValueError:
        return False


def _numeric_range(kind: str, value: float) -> dict:
    """
    Pick a slider range around a default. The INI carries no bounds, so the
    range has to be inferred; these bounds are deliberately generous because a
    too-tight max is worse than a loose one (it makes a valid config
    unreachable in the UI).
    """
    if kind == "int":
        if value in (0, 1):
            return {"min": 0, "max": 10, "step": 1}
        span = max(10, int(abs(value) * 4))
        return {"min": 0 if value >= 0 else -span, "max": span, "step": 1}
    magnitude = abs(value)
    if magnitude == 0:
        return {"min": 0.0, "max": 1.0, "step": 0.01}
    if magnitude <= 1:
        return {"min": 0.0, "max": 1.0, "step": 0.01}
    if magnitude <= 100:
        return {"min": 0.0, "max": round(magnitude * 4, 2), "step": 0.1}
    return {"min": 0.0, "max": round(magnitude * 4, 2), "step": 1.0}


def _humanize(key: str) -> str:
    """MaxEssencePerShot -> 'Max essence per shot'."""
    body = _split_ini_key(key)[0]
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", body)
    if not words:
        return key
    first, *rest = words
    return " ".join([first[:1].upper() + first[1:]] + [w.lower() if w.isupper() and len(w) > 3 else w for w in rest])


def parse_ini(path: Path) -> list[dict]:
    """
    Read an INI into [{section, keys: [{key, raw, comment}]}].

    Comments immediately above a key are its documentation, so they become the
    setting `hint` -- that is where the real explanatory text already lives, and
    re-authoring it by hand would guarantee drift.
    """
    sections: list[dict] = []
    current: dict | None = None
    pending: list[str] = []

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            pending.clear()
            continue
        if stripped.startswith(";") or stripped.startswith("#"):
            text = stripped.lstrip(";#").strip()
            # Banner rules ("=====") are decoration, not documentation.
            if text and not set(text) <= set("=-*_ "):
                pending.append(text)
            continue
        match = re.match(r"^\[(.+?)\]$", stripped)
        if match:
            current = {"section": match.group(1).strip(), "keys": []}
            sections.append(current)
            pending.clear()
            continue
        if "=" in stripped and current is not None:
            key, _, raw = stripped.partition("=")
            key = key.strip()
            raw = raw.split(";", 1)[0].strip()
            if key:
                current["keys"].append({"key": key, "raw": raw, "comment": " ".join(pending)})
            pending.clear()

    return [s for s in sections if s["keys"]]


def _osf_key(section: str, name: str) -> str:
    # OSF keys cannot contain spaces. Spell names in the INI still show as labels.
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "", name.replace(" ", ""))
    return f"{section}.{slug or 'Setting'}"


def spec_from_ini(
    ini_path: Path,
    mod_id: str,
    title: str,
    *,
    description: str = "",
    accent: str | None = None,
    ini_relpath: str | None = None,
) -> dict:
    """Build a full spec from a plugin INI: one group per INI section."""
    groups = []
    for section in parse_ini(ini_path):
        settings = []
        for entry in section["keys"]:
            key, raw = entry["key"], entry["raw"]
            name, hinted = _split_ini_key(key)
            kind = _ini_type(name, raw, hinted)
            setting: dict = {
                "key": _osf_key(section["section"], name),
                "label": name if " " in name else _humanize(name),
                "type": kind,
            }
            if kind == "bool":
                setting["default"] = _as_bool(raw)
            elif kind == "int":
                setting["default"] = int(float(raw)) if _is_number(raw) else 0
                setting.update(_numeric_range("int", setting["default"]))
            elif kind == "float":
                setting["default"] = float(raw) if _is_number(raw) else 0.0
                setting.update(_numeric_range("float", setting["default"]))
            else:
                setting["default"] = raw
                setting["maxLength"] = max(64, len(raw) + 32)
            hint = entry["comment"]
            if hint:
                # The renderer shows hints inline; keep them to one tidy sentence.
                setting["hint"] = hint if len(hint) <= 300 else hint[:297].rstrip() + "..."
            settings.append(setting)

        groups.append({
            "id": re.sub(r"[^a-z0-9-]+", "-", section["section"].lower()).strip("-") or "general",
            "label": section["section"],
            "settings": settings,
        })

    spec: dict = {
        "modId": mod_id,
        "title": title,
        "description": description or f"Settings for {title}.",
        "version": 1,
        "source": {"ini": ini_relpath or ini_path.name},
        "settings": {"groups": groups},
        "views": [],
    }
    if accent:
        spec["accent"] = accent
    return spec


# --- validation ---------------------------------------------------------------

def validate_spec(spec: dict) -> list[str]:
    """Return a list of problems; empty means the spec is safe to emit."""
    problems: list[str] = []

    mod_id = spec.get("modId", "")
    if not MOD_ID_RE.match(mod_id or ""):
        problems.append(
            f"modId {mod_id!r} must be '<author>.<modname>' with lowercase [a-z0-9-] "
            "segments and exactly one dot (dotless ids are reserved for OSF UI itself)"
        )
    elif len(mod_id) > MOD_ID_MAX:
        problems.append(f"modId {mod_id!r} is longer than {MOD_ID_MAX} chars")

    if not spec.get("title"):
        problems.append("title is required (it names the mod card in the settings list)")

    accent = spec.get("accent")
    if accent is not None and not COLOR_RE.match(str(accent)):
        problems.append(f"accent {accent!r} must be #RRGGBB or #RRGGBBAA")

    groups = spec.get("settings", {}).get("groups", [])
    seen_keys: set[str] = set()
    seen_groups: set[str] = set()
    for gi, group in enumerate(groups):
        where = f"settings.groups[{gi}]"
        gid = group.get("id", "")
        if not gid:
            problems.append(f"{where}: id is required")
        elif gid in seen_groups:
            problems.append(f"{where}: duplicate group id {gid!r}")
        seen_groups.add(gid)
        if not group.get("label"):
            problems.append(f"{where}: label is required")
        for si, setting in enumerate(group.get("settings", [])):
            problems.extend(_validate_setting(setting, f"{where}.settings[{si}]", seen_keys))

    view_names: set[str] = set()
    for vi, view in enumerate(spec.get("views", [])):
        problems.extend(_validate_view(view, f"views[{vi}]", view_names, seen_keys))

    return problems


def _validate_setting(setting: dict, where: str, seen: set[str]) -> list[str]:
    problems: list[str] = []
    kind = setting.get("type")
    key = setting.get("key", "")

    if kind == "action":
        if not setting.get("label"):
            problems.append(f"{where}: an action needs a label")
        if not setting.get("action"):
            problems.append(f"{where}: an action needs an 'action' name")
        return problems

    if kind not in VALUE_TYPES:
        problems.append(
            f"{where}: type {kind!r} is not stored by OSF UI "
            f"(use one of {', '.join(VALUE_TYPES)}, or 'action' for a button)"
        )
        return problems

    if not key:
        problems.append(f"{where}: key is required")
    elif not KEY_RE.match(key):
        problems.append(f"{where}: key {key!r} may only use letters, digits, dot, dash, underscore")
    elif key.lower() in seen:
        # The store folds case, so two keys differing only in case collide.
        problems.append(f"{where}: duplicate key {key!r} (keys are case-insensitive)")
    seen.add(key.lower())

    if not setting.get("label"):
        problems.append(f"{where}: label is required")

    widget = setting.get("widget")
    if widget is not None:
        allowed = WIDGETS.get(kind, ())
        if widget not in allowed:
            problems.append(
                f"{where}: widget {widget!r} is not valid for type {kind!r}"
                + (f" (allowed: {', '.join(allowed)})" if allowed else " (this type takes no widget)")
            )

    default = setting.get("default")
    if default is None:
        problems.append(f"{where}: default is required (it is what every reader falls back to)")

    if kind == "bool" and default is not None and not isinstance(default, bool):
        problems.append(f"{where}: bool default must be true/false, got {default!r}")

    if kind in NUMERIC_TYPES:
        if default is not None and isinstance(default, bool) or not isinstance(default, (int, float)):
            problems.append(f"{where}: {kind} default must be a number, got {default!r}")
        else:
            low, high = setting.get("min"), setting.get("max")
            if low is not None and high is not None and low > high:
                problems.append(f"{where}: min {low} is above max {high}")
            if low is not None and default < low:
                problems.append(f"{where}: default {default} is below min {low}")
            if high is not None and default > high:
                problems.append(f"{where}: default {default} is above max {high}")
        step = setting.get("step")
        if step is not None and (not isinstance(step, (int, float)) or step <= 0):
            # The renderer warns '"key" has invalid step' and falls back.
            problems.append(f"{where}: step must be a positive number, got {step!r}")
        if kind == "int" and isinstance(step, float) and step != int(step):
            problems.append(f"{where}: an int setting cannot have a fractional step ({step})")

    if kind in ("enum", "flags"):
        options = setting.get("options")
        if not isinstance(options, list) or not options:
            problems.append(f"{where}: {kind} requires a non-empty options list")
        else:
            if len(set(options)) != len(options):
                problems.append(f"{where}: options contain duplicates")
            labels = setting.get("optionLabels")
            if labels is not None and len(labels) != len(options):
                problems.append(
                    f"{where}: optionLabels has {len(labels)} entries but options has {len(options)} "
                    "(they are matched by index)"
                )
            if kind == "enum" and default not in options:
                problems.append(f"{where}: default {default!r} is not one of options")
            if kind == "flags":
                if not isinstance(default, list):
                    problems.append(f"{where}: a flags default must be a list of selected options")
                else:
                    unknown = [d for d in default if d not in options]
                    if unknown:
                        problems.append(f"{where}: flags default contains unknown options {unknown}")

    if kind == "string":
        if not isinstance(default, str):
            problems.append(f"{where}: string default must be a string, got {default!r}")
        elif setting.get("widget") == "color" and not COLOR_RE.match(default):
            problems.append(f"{where}: a color widget needs a #RRGGBB(AA) default, got {default!r}")
        max_length = setting.get("maxLength")
        if max_length is not None:
            if not isinstance(max_length, int) or max_length <= 0:
                problems.append(f"{where}: maxLength must be a positive integer")
            elif isinstance(default, str) and len(default) > max_length:
                problems.append(f"{where}: default is longer than maxLength {max_length}")

    if kind == "key" and not isinstance(default, str):
        problems.append(f"{where}: a key setting's default is a key name string such as \"F10\" or \"\"")

    for cond_name in ("visibleWhen", "enabledWhen"):
        cond = setting.get(cond_name)
        if cond is not None:
            problems.extend(_validate_condition(cond, f"{where}.{cond_name}"))

    return problems


# The evaluator accepts all/any/not combinators and one comparison per leaf.
CONDITION_OPS = ("eq", "ne", "in", "gt", "gte", "lt", "lte", "truthy")


def _validate_condition(cond: dict, where: str) -> list[str]:
    if not isinstance(cond, dict):
        return [f"{where}: a condition must be an object"]
    problems: list[str] = []
    for combinator in ("all", "any"):
        if combinator in cond:
            if not isinstance(cond[combinator], list):
                problems.append(f"{where}.{combinator} must be a list of conditions")
            else:
                for i, sub in enumerate(cond[combinator]):
                    problems.extend(_validate_condition(sub, f"{where}.{combinator}[{i}]"))
            return problems
    if "not" in cond:
        return _validate_condition(cond["not"], f"{where}.not")
    if "key" not in cond:
        problems.append(f"{where}: needs a 'key', or an all/any/not combinator")
        return problems
    if not any(op in cond for op in CONDITION_OPS):
        problems.append(f"{where}: needs one comparison ({', '.join(CONDITION_OPS)})")
    return problems


def _validate_view(view: dict, where: str, seen: set[str], setting_keys: set[str]) -> list[str]:
    problems: list[str] = []
    name = view.get("name", "")
    if not VIEW_NAME_RE.match(name or ""):
        problems.append(f"{where}: name {name!r} must be lowercase [a-z0-9-] (it becomes the folder name)")
    elif name in seen:
        problems.append(f"{where}: duplicate view name {name!r}")
    seen.add(name)

    if not view.get("title"):
        problems.append(f"{where}: title is required (it labels the view in the hub)")

    for numeric in ("width", "height"):
        value = view.get(numeric)
        if value is not None and (not isinstance(value, int) or value <= 0):
            problems.append(f"{where}: {numeric} must be a positive integer")

    sections = view.get("sections")
    if not isinstance(sections, list) or not sections:
        problems.append(f"{where}: a view needs at least one section")
        return problems

    for si, section in enumerate(sections):
        swhere = f"{where}.sections[{si}]"
        if not section.get("title"):
            problems.append(f"{swhere}: title is required")
        rows = section.get("rows")
        if not isinstance(rows, list) or not rows:
            problems.append(f"{swhere}: needs at least one row")
            continue
        for ri, row in enumerate(rows):
            problems.extend(_validate_row(row, f"{swhere}.rows[{ri}]", setting_keys))
    return problems


def _validate_row(row: dict, where: str, setting_keys: set[str]) -> list[str]:
    problems: list[str] = []
    kind = row.get("kind")
    if kind not in ROW_KINDS:
        return [f"{where}: kind {kind!r} is not supported (use one of {', '.join(ROW_KINDS)})"]

    if kind in DATA_ROWS:
        if not row.get("data"):
            problems.append(
                f"{where}: a {kind} row needs a 'data' key -- the same key the mod publishes "
                "with OSFUI.SetView* (Papyrus) or a data.state push"
            )
        if not row.get("label"):
            problems.append(f"{where}: a {kind} row needs a label")
        if kind == "bar" and row.get("max") is None and not row.get("maxData"):
            problems.append(f"{where}: a bar row needs 'max' or 'maxData' to scale against")

    if kind in SETTING_ROWS:
        key = row.get("setting")
        if not key:
            problems.append(f"{where}: a {kind} row needs a 'setting' key to bind to")
        elif setting_keys and key.lower() not in setting_keys:
            problems.append(
                f"{where}: setting {key!r} is not declared in this spec's schema "
                "(a view may only read and write its own mod's settings)"
            )

    if kind == "button":
        if not row.get("label"):
            problems.append(f"{where}: a button needs a label")
        if not row.get("action"):
            problems.append(
                f"{where}: a button needs an 'action' name -- it is delivered to Papyrus as "
                "OnOSFUIViewAction(action, args)"
            )
        variant = row.get("variant")
        if variant is not None and variant not in ("accent", "ghost", "danger"):
            problems.append(f"{where}: variant {variant!r} must be accent, ghost or danger")

    if kind == "text" and not row.get("text"):
        problems.append(f"{where}: a text row needs 'text'")

    return problems


# --- emitters -----------------------------------------------------------------

def build_schema(spec: dict) -> dict:
    """Emit the drop-in settings schema exactly as SettingsStore expects it."""
    schema: dict = {
        "id": spec["modId"],
        "title": spec["title"],
        "description": spec.get("description", ""),
        "version": spec.get("version", 1),
    }
    if spec.get("accent"):
        schema["accent"] = spec["accent"]
    if spec.get("icon"):
        schema["icon"] = spec["icon"]

    groups = []
    for group in spec.get("settings", {}).get("groups", []):
        emitted = []
        for setting in group.get("settings", []):
            # Copy through only contract keys so a stray spec field cannot end up
            # in the schema and trip the host's "entries this host can't
            # understand" preservation path.
            allowed = {
                "key", "label", "type", "default", "hint", "min", "max", "step",
                "options", "optionLabels", "maxLength", "widget", "rows",
                "placeholder", "allowUnbound", "format", "visibleWhen",
                "enabledWhen", "action", "icon",
            }
            emitted.append({k: v for k, v in setting.items() if k in allowed})
        groups.append({"id": group["id"], "label": group["label"], "settings": emitted})
    schema["groups"] = groups
    return schema


def build_manifest(spec: dict, view: dict) -> dict:
    manifest = {
        "id": view["name"],
        "title": view["title"],
        "description": view.get("description", ""),
        "entry": "index.html",
        "mod": spec["modId"],
        "hub": bool(view.get("hub", True)),
        "kind": view.get("kind", "menu"),
        "width": int(view.get("width", 1600)),
        "height": int(view.get("height", 900)),
        "transparent": bool(view.get("transparent", True)),
        "capturesInput": bool(view.get("capturesInput", True)),
        "pausesGame": bool(view.get("pausesGame", False)),
        "permissions": {
            # A view that talks to the mod at all needs the bridge; filesystem
            # and network stay off because nothing generated here uses them.
            "nativeBridge": True,
            "filesystem": False,
            "network": False,
        },
    }
    if view.get("debugOnly"):
        manifest["debugOnly"] = True
    if spec.get("accent"):
        manifest["accent"] = spec["accent"]
    return manifest


def build_index_html(spec: dict, view: dict) -> str:
    # Script order is load-bearing: the shared helper defines window.osfui,
    # padnav attaches gamepad/keyboard focus, then main.js mounts.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(view['title'])}</title>
  <link rel="stylesheet" href="../../shared/osfui.css">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="app" class="view"></div>
  <script src="../../shared/osfui.js"></script>
  <script src="../padnav.js"></script>
  <script src="main.js"></script>
</body>
</html>
"""


def build_style_css(spec: dict, view: dict) -> str:
    # Layout only. Color, radius, and type come from the shared kit.
    # tokens so a generated view inherits OSF UI's look and any future retheme.
    return """/* Layout for a generated view. Colours/typography come from shared/osfui.css. */

body {
  margin: 0;
  font-family: var(--osf-font-sans);
  color: var(--osf-text-body);
  background: transparent;
}

.view {
  display: flex;
  flex-direction: column;
  gap: var(--osf-space-5);
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--osf-space-9) var(--osf-space-5);
}

.view-head h1 {
  margin: 0;
  font-family: var(--osf-font-display);
  font-size: var(--osf-text-3xl);
  letter-spacing: var(--osf-tracking-wide);
  color: var(--osf-text-bright);
}

.view-head p {
  margin: var(--osf-space-1) 0 0;
  color: var(--osf-text-muted);
  font-size: var(--osf-text-sm);
}

.section + .section { margin-top: var(--osf-space-5); }

.section > h2 {
  margin: 0 0 var(--osf-space-5);
  font-size: var(--osf-text-2xs);
  letter-spacing: var(--osf-tracking-label);
  text-transform: uppercase;
  color: var(--osf-text-faint);
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--osf-space-5);
  min-height: var(--osf-control-h-sm);
  padding: var(--osf-space-1) 0;
}

.row + .row { border-top: 1px solid var(--osf-line); }

.row-label { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.row-label > span { color: var(--osf-text-body); }
.row-label > small { color: var(--osf-text-faint); font-size: var(--osf-text-xs); }

.row-control { display: flex; align-items: center; gap: var(--osf-space-1); flex: 0 0 auto; }

.row-value {
  font-family: var(--osf-font-mono);
  font-size: var(--osf-text-sm);
  color: var(--osf-text-bright);
}

/* bar */
.bar-track {
  width: 260px;
  height: 6px;
  border-radius: var(--osf-radius-pill);
  background: var(--osf-surface-input);
  border: 1px solid var(--osf-line);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  width: 0;
  background: var(--osf-accent, var(--osf-sf-blue));
  transition: width var(--osf-dur-fast) var(--osf-ease-out);
}

/* list */
.row.is-block { flex-direction: column; align-items: stretch; }
.list {
  margin: var(--osf-space-1) 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow-y: auto;
}
.list li {
  font-family: var(--osf-font-mono);
  font-size: var(--osf-text-xs);
  color: var(--osf-text-muted);
  padding: 2px var(--osf-space-1);
  border-radius: var(--osf-radius-sm);
  background: var(--osf-surface-input);
}
.list-empty { color: var(--osf-text-faint); font-size: var(--osf-text-xs); font-style: italic; }

.row-text { color: var(--osf-text-muted); font-size: var(--osf-text-sm); line-height: 1.5; }

.offline {
  display: none;
  margin-top: var(--osf-space-1);
}
body.is-standalone .offline { display: block; }
"""


def build_main_js(spec: dict, view: dict) -> str:
    """
    Emit a self-contained renderer driven by an embedded view model.

    Generated code stays data-driven on purpose: the spec is the only thing that
    changes between views, so the logic below is identical everywhere and can be
    reviewed once. It uses no framework and no build step, which keeps a
    generated view debuggable in a plain browser.
    """
    model = {
        "modId": spec["modId"],
        "title": view["title"],
        "subtitle": view.get("description", ""),
        "accent": spec.get("accent") or "",
        "sections": view["sections"],
    }
    model_json = json.dumps(model, indent=2, ensure_ascii=False)
    return f'''"use strict";
// Generated by osfui_gen. Edit the spec, not this file.
//
// Contract touched here:
//   osfui.ready                     runtime handshake
//   osfui.data.on(key, fn)          typed, cached Papyrus state (SetView*)
//   osfui.call("settings.get")      this mod's current setting values
//   osfui.call("settings.set")      write one setting (own mod only)
//   osfui.on("settings.changed")    another writer committed a value
//   osfui.action(name, ...args)     fire-and-forget to OnOSFUIViewAction

const MODEL = {model_json};

const app = document.getElementById("app");
const settings = new Map();   // lower-case key -> current value
const binders = [];           // fn() re-render callbacks for setting rows

function el(tag, className, text) {{
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = String(text);
  return node;
}}

function labelBlock(row) {{
  const wrap = el("div", "row-label");
  wrap.appendChild(el("span", null, row.label));
  if (row.hint) wrap.appendChild(el("small", null, row.hint));
  return wrap;
}}

function formatValue(row, value) {{
  const fmt = row.format || {{}};
  if (value == null) return fmt.empty != null ? fmt.empty : "--";
  let out = value;
  if (typeof value === "number") {{
    const scaled = value * (typeof fmt.scale === "number" ? fmt.scale : 1);
    out = typeof fmt.decimals === "number" ? scaled.toFixed(fmt.decimals) : String(scaled);
  }}
  return (fmt.prefix || "") + out + (fmt.suffix || "");
}}

// --- row builders ------------------------------------------------------------

function buildStat(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const value = el("div", "row-control");
  const out = el("span", "row-value", formatValue(row, null));
  value.appendChild(out);
  node.appendChild(value);
  osfui.data.on(row.data, (v) => {{ out.textContent = formatValue(row, v); }});
  return node;
}}

function buildBar(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const control = el("div", "row-control");
  const track = el("div", "bar-track");
  const fill = el("div", "bar-fill");
  track.appendChild(fill);
  const out = el("span", "row-value", formatValue(row, null));
  control.appendChild(track);
  control.appendChild(out);
  node.appendChild(control);

  let max = typeof row.max === "number" ? row.max : 1;
  let current = null;
  const paint = () => {{
    out.textContent = formatValue(row, current);
    const ratio = current == null || !(max > 0) ? 0 : Math.max(0, Math.min(1, current / max));
    fill.style.width = (ratio * 100).toFixed(1) + "%";
  }};
  osfui.data.on(row.data, (v) => {{ current = typeof v === "number" ? v : null; paint(); }});
  if (row.maxData) osfui.data.on(row.maxData, (v) => {{ if (typeof v === "number") {{ max = v; paint(); }} }});
  return node;
}}

function buildList(row) {{
  const node = el("div", "row is-block");
  node.appendChild(labelBlock(row));
  const list = el("ul", "list");
  const empty = el("div", "list-empty", row.emptyText || "Nothing to show.");
  node.appendChild(list);
  node.appendChild(empty);
  osfui.data.on(row.data, (values) => {{
    list.textContent = "";
    const items = Array.isArray(values) ? values : [];
    for (const item of items) {{
      // Papyrus pushes forms as objects; show their name, else the raw string.
      const text = item && typeof item === "object" ? (item.name || item.formId || "") : item;
      list.appendChild(el("li", null, text));
    }}
    empty.style.display = items.length ? "none" : "";
  }});
  return node;
}}

function commit(key, value) {{
  settings.set(key.toLowerCase(), value);
  // settings.set is fire-and-forget from the view's side: the host validates and
  // clamps against the schema, then echoes settings.changed, which re-syncs us.
  osfui.call("settings.set", {{ mod: MODEL.modId, key: key, value: value }})
    .catch((err) => console.error("settings.set " + key + " failed:", err));
}}

function currentValue(row, fallback) {{
  const value = settings.get(String(row.setting).toLowerCase());
  return value === undefined ? fallback : value;
}}

function buildToggle(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const control = el("div", "row-control");
  const button = el("button", "osf-switch");
  button.type = "button";
  button.setAttribute("role", "switch");
  control.appendChild(button);
  node.appendChild(control);

  const paint = () => {{
    const on = currentValue(row, false) === true;
    button.classList.toggle("osf-on", on);
    button.setAttribute("aria-checked", on ? "true" : "false");
  }};
  button.addEventListener("click", () => {{
    commit(row.setting, !(currentValue(row, false) === true));
    paint();
  }});
  binders.push(paint);
  return node;
}}

function buildSlider(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const control = el("div", "row-control");
  const input = el("input", "osf-range");
  input.type = "range";
  if (row.min != null) input.min = row.min;
  if (row.max != null) input.max = row.max;
  if (row.step != null) input.step = row.step;
  const out = el("span", "row-value");
  control.appendChild(input);
  control.appendChild(out);
  node.appendChild(control);

  const paint = () => {{
    const value = Number(currentValue(row, row.min != null ? row.min : 0));
    input.value = String(value);
    out.textContent = formatValue(row, value);
  }};
  input.addEventListener("input", () => {{
    out.textContent = formatValue(row, Number(input.value));
  }});
  // Commit on release, not on every frame of the drag: each set is a queued
  // write the host validates and persists.
  input.addEventListener("change", () => {{
    commit(row.setting, Number(input.value));
    paint();
  }});
  binders.push(paint);
  return node;
}}

function buildSelect(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const control = el("div", "row-control");
  const select = el("select", "osf-select");
  const options = Array.isArray(row.options) ? row.options : [];
  const labels = Array.isArray(row.optionLabels) ? row.optionLabels : [];
  options.forEach((value, i) => {{
    const option = el("option", null, labels[i] != null ? labels[i] : value);
    option.value = value;
    select.appendChild(option);
  }});
  control.appendChild(select);
  node.appendChild(control);

  const paint = () => {{ select.value = String(currentValue(row, options[0])); }};
  select.addEventListener("change", () => {{ commit(row.setting, select.value); }});
  binders.push(paint);
  return node;
}}

function buildButton(row) {{
  const node = el("div", "row");
  node.appendChild(labelBlock(row));
  const control = el("div", "row-control");
  const variant = row.variant === "danger" ? " osf-btn--danger"
    : row.variant === "ghost" ? " osf-btn--ghost"
    : " osf-btn--osf-accent";
  const button = el("button", "osf-btn" + variant, row.buttonLabel || row.label);
  button.type = "button";
  button.addEventListener("click", () => {{
    const args = Array.isArray(row.args) ? row.args : [];
    osfui.action(row.action, ...args);
    // Nothing comes back from an action, so acknowledge locally.
    button.classList.add("osf-seduce");
    setTimeout(() => button.classList.remove("osf-seduce"), 400);
  }});
  control.appendChild(button);
  node.appendChild(control);
  return node;
}}

function buildText(row) {{
  const node = el("div", "row is-block");
  node.appendChild(el("p", "row-text", row.text));
  return node;
}}

const BUILDERS = {{
  stat: buildStat,
  bar: buildBar,
  list: buildList,
  toggle: buildToggle,
  slider: buildSlider,
  select: buildSelect,
  button: buildButton,
  text: buildText,
}};

// --- mount -------------------------------------------------------------------

function render() {{
  app.textContent = "";

  const head = el("div", "view-head");
  head.appendChild(el("h1", null, MODEL.title));
  if (MODEL.subtitle) head.appendChild(el("p", null, MODEL.subtitle));
  app.appendChild(head);

  const offline = el("div", "osf-note osf-note--warn offline",
    "No OSF UI bridge: this is a standalone preview, so live values and writes are inert.");
  app.appendChild(offline);

  for (const section of MODEL.sections) {{
    const card = el("section", "osf-card section");
    card.appendChild(el("h2", null, section.title));
    for (const row of section.rows) {{
      const build = BUILDERS[row.kind];
      if (build) card.appendChild(build(row));
    }}
    app.appendChild(card);
  }}

  if (MODEL.accent) osfui.applyAccent(document.documentElement, MODEL.accent);
}}

function syncSettings(values) {{
  if (!values || typeof values !== "object") return;
  for (const [key, value] of Object.entries(values)) settings.set(key.toLowerCase(), value);
  for (const paint of binders) paint();
}}

if (!osfui.available()) {{
  // Standalone preview: render the shell so layout can be checked in a browser.
  document.body.classList.add("is-standalone");
  render();
}} else {{
  render();
  osfui.ready.then(() => {{
    osfui.call("settings.get", {{ mod: MODEL.modId }})
      .then((payload) => syncSettings(payload && (payload.values || payload.settings)))
      .catch((err) => console.error("settings.get failed:", err));
    // Another writer (the settings menu, Papyrus, native code) committed a value.
    osfui.on("settings.changed", (payload) => {{
      if (!payload || payload.mod !== MODEL.modId) return;
      if (payload.key != null) {{
        settings.set(String(payload.key).toLowerCase(), payload.value);
        for (const paint of binders) paint();
      }} else {{
        syncSettings(payload.values);
      }}
    }});
    osfui.viewReady();
  }});
}}
'''


def _escape(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --- write out ----------------------------------------------------------------

def emit(spec: dict, out_root: Path, *, for_install: bool) -> list[Path]:
    """
    Write the schema and views under out_root.

    out_root is a Data folder when installing, or a staging folder when building,
    and the tree is identical either way so a build can be diffed against what
    is live before it is installed.
    """
    written: list[Path] = []
    mod_id = spec["modId"]
    osfui_root = out_root / "SFSE" / "Plugins" / "OSFUI"

    if spec.get("settings", {}).get("groups"):
        settings_dir = osfui_root / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        # The store rejects a schema whose id does not equal the filename stem.
        target = settings_dir / f"{mod_id}.json"
        target.write_text(json.dumps(build_schema(spec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)

    for view in spec.get("views", []):
        view_dir = osfui_root / "views" / mod_id / view["name"]
        view_dir.mkdir(parents=True, exist_ok=True)
        if view.get("custom"):
            src = TOOL_DIR / "custom-views" / mod_id / view["name"]
            if not src.is_dir():
                raise SpecError(f"custom view {mod_id}/{view['name']} is missing under custom-views/")
            shutil.copytree(src, view_dir, dirs_exist_ok=True)
            manifest_path = view_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(build_manifest(spec, view), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            written.append(manifest_path)
            for path in sorted(view_dir.iterdir()):
                if path.is_file() and path not in written:
                    written.append(path)
        else:
            files = {
                "manifest.json": json.dumps(build_manifest(spec, view), indent=2, ensure_ascii=False) + "\n",
                "index.html": build_index_html(spec, view),
                "main.js": build_main_js(spec, view),
                "style.css": build_style_css(spec, view),
            }
            for name, content in files.items():
                path = view_dir / name
                path.write_text(content, encoding="utf-8")
                written.append(path)

        padnav_src = DEFAULT_DATA / "SFSE" / "Plugins" / "OSFUI" / "views" / "osfui" / "padnav.js"
        padnav_dst = view_dir.parent / "padnav.js"
        if padnav_src.exists() and not padnav_dst.exists():
            shutil.copy2(padnav_src, padnav_dst)
            written.append(padnav_dst)

    return written


def build_preview(spec: dict, view: dict, out_dir: Path) -> Path:
    """
    Stage a view so it opens in a desktop browser with a mock bridge.

    This is what makes iterating on a generated view cheap: layout, wiring and
    fake live data can be checked without launching Starfield, and the same
    files are what ship.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    shared = out_dir / "shared"
    shared.mkdir(exist_ok=True)
    view_dir = out_dir / "views" / spec["modId"] / view["name"]
    view_dir.mkdir(parents=True, exist_ok=True)

    data_root = DEFAULT_DATA / "SFSE" / "Plugins" / "OSFUI" / "views"
    for name in ("osfui.css", "osfui.js"):
        source = data_root / "shared" / name
        if source.exists():
            shutil.copy2(source, shared / name)
    padnav = data_root / "osfui" / "padnav.js"
    stub_parent = out_dir / "views" / spec["modId"]
    if padnav.exists():
        shutil.copy2(padnav, stub_parent / "padnav.js")
    else:
        (stub_parent / "padnav.js").write_text("// padnav stub\n", encoding="utf-8")

    (view_dir / "index.html").write_text(build_index_html(spec, view), encoding="utf-8")
    (view_dir / "style.css").write_text(build_style_css(spec, view), encoding="utf-8")
    (view_dir / "main.js").write_text(build_main_js(spec, view), encoding="utf-8")

    # The mock stands in for the native host: it answers settings.get/set and
    # replays whatever sample data the spec declares, so every row renders.
    samples = {}
    for section in view["sections"]:
        for row in section["rows"]:
            if row.get("data") and "sample" in row:
                samples[row["data"]] = row["sample"]
            if row.get("maxData") and "maxSample" in row:
                samples[row["maxData"]] = row["maxSample"]
    defaults = {}
    for group in spec.get("settings", {}).get("groups", []):
        for setting in group.get("settings", []):
            if setting.get("type") != "action":
                defaults[setting["key"]] = setting.get("default")

    mock = f"""// Mock OSF UI host for browser preview. Never shipped into Data.
(function () {{
  const VALUES = {json.dumps(defaults, indent=2, ensure_ascii=False)};
  const SAMPLES = {json.dumps(samples, indent=2, ensure_ascii=False)};
  const MOD = {json.dumps(spec['modId'])};

  window.osfui = window.osfui || {{}};
  window.osfui.postMessage = function (json) {{
    const message = JSON.parse(json);
    const payload = message.payload || {{}};
    if (payload.command === "settings.get") {{
      reply(message.requestId, "settings.data", {{ mod: MOD, values: VALUES }});
    }} else if (payload.command === "settings.set") {{
      VALUES[payload.key] = payload.value;
      reply(message.requestId, "ui.result", {{ ok: true, command: "settings.set" }});
      deliver("settings.changed", {{ mod: MOD, key: payload.key, value: payload.value }});
    }} else if (payload.command === "ui.action") {{
      console.log("[mock] action", payload.action, payload.args || []);
      reply(message.requestId, "ui.result", {{ ok: true, command: "ui.action" }});
    }} else if (payload.command === "i18n.get") {{
      reply(message.requestId, "i18n.data", {{ locale: "en", strings: {{}} }});
    }} else {{
      reply(message.requestId, "ui.result", {{ ok: true, command: payload.command }});
    }}
  }};

  function send(message) {{ window.osfui.onMessage(JSON.stringify(message)); }}
  function reply(requestId, type, payload) {{ setTimeout(() => send({{ type, requestId, payload }}), 10); }}
  function deliver(type, payload) {{ setTimeout(() => send({{ type, payload }}), 10); }}

  window.addEventListener("DOMContentLoaded", () => {{
    send({{ type: "runtime.ready", payload: {{ version: "1.5.0-preview" }} }});
    for (const [key, value] of Object.entries(SAMPLES)) {{
      deliver("data.state", {{ mod: MOD, key, value }});
    }}
  }});
}})();
"""
    (shared / "mock-host.js").write_text(mock, encoding="utf-8")

    # Inject the mock ahead of the shared helper, which decorates window.osfui
    # and treats a present postMessage as "bridge available".
    html = (view_dir / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        '<script src="../../shared/osfui.js"></script>',
        '<script src="../../shared/mock-host.js"></script>\n  <script src="../../shared/osfui.js"></script>',
    )
    (view_dir / "index.html").write_text(html, encoding="utf-8")
    return view_dir / "index.html"


# --- installed-tree lint ------------------------------------------------------

def lint_installed(data: Path) -> tuple[int, list[str]]:
    """
    Validate every schema and manifest already in Data.

    Hand edits are expected -- this catches the ones OSF UI would silently drop.
    """
    problems: list[str] = []
    root = data / "SFSE" / "Plugins" / "OSFUI"
    checked = 0

    settings_dir = root / "settings"
    if settings_dir.is_dir():
        for path in sorted(settings_dir.glob("*.json")):
            checked += 1
            try:
                schema = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"{path.name}: not valid JSON ({exc})")
                continue
            stem = path.stem
            schema_id = schema.get("id", "")
            if schema_id != stem:
                problems.append(f"{path.name}: id {schema_id!r} must equal the filename stem {stem!r}")
            if stem != "osfui" and not MOD_ID_RE.match(stem):
                problems.append(f"{path.name}: filename must be '<author>.<modname>.json'")
            spec = {
                "modId": schema_id if MOD_ID_RE.match(schema_id or "") else "author.modname",
                "title": schema.get("title", ""),
                "settings": {"groups": schema.get("groups", [])},
                "views": [],
            }
            if schema.get("accent"):
                spec["accent"] = schema["accent"]
            for problem in validate_spec(spec):
                problems.append(f"{path.name}: {problem}")

    views_dir = root / "views"
    if views_dir.is_dir():
        for manifest_path in sorted(views_dir.glob("*/*/manifest.json")):
            checked += 1
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"{manifest_path}: not valid JSON ({exc})")
                continue
            rel = manifest_path.parent
            unknown = set(manifest) - MANIFEST_KEYS
            if unknown:
                problems.append(f"{rel.name}: unknown manifest keys {sorted(unknown)}")
            if manifest.get("id") != rel.name:
                problems.append(f"{rel.name}: manifest id {manifest.get('id')!r} must equal the folder name")
            if manifest.get("mod") != rel.parent.name:
                problems.append(
                    f"{rel.name}: manifest mod {manifest.get('mod')!r} must equal the parent folder "
                    f"{rel.parent.name!r} (the view id is '<mod>/<view>')"
                )
            entry = manifest.get("entry", "index.html")
            if not (rel / entry).exists():
                problems.append(f"{rel.name}: entry {entry!r} does not exist")
            if manifest.get("readySignal") and not manifest.get("permissions", {}).get("nativeBridge"):
                problems.append(f"{rel.name}: readySignal needs permissions.nativeBridge")

    return checked, problems


# --- CLI ----------------------------------------------------------------------

def _load_spec(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path}: not valid JSON ({exc})") from exc


def _report(problems: list[str], label: str) -> int:
    if problems:
        print(f"[fail] {label}: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
        return 2
    print(f"[ok]   {label}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="osfui_gen",
        description="Generate OSF UI settings schemas and custom views from a spec.",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="game Data folder")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ini = sub.add_parser("from-ini", help="derive a spec from an SFSE plugin INI")
    p_ini.add_argument("ini", type=Path)
    p_ini.add_argument("--mod-id", required=True, help="<author>.<modname>")
    p_ini.add_argument("--title", required=True)
    p_ini.add_argument("--description", default="")
    p_ini.add_argument("--accent", default=None)
    p_ini.add_argument("-o", "--output", type=Path, required=True)

    p_val = sub.add_parser("validate", help="check a spec against the OSF UI contract")
    p_val.add_argument("spec", type=Path, nargs="+")

    p_build = sub.add_parser("build", help="emit into a staging folder")
    p_build.add_argument("spec", type=Path, nargs="+")
    p_build.add_argument("--out", type=Path, default=TOOL_DIR / "build")

    p_install = sub.add_parser("install", help="emit straight into the game Data folder")
    p_install.add_argument("spec", type=Path, nargs="+")

    p_prev = sub.add_parser("preview", help="stage a view for a desktop browser")
    p_prev.add_argument("spec", type=Path)
    p_prev.add_argument("--view", default=None, help="view name (default: first)")
    p_prev.add_argument("--out", type=Path, default=TOOL_DIR / "build" / "preview")
    p_prev.add_argument("--open", action="store_true", help="open in the default browser")

    sub.add_parser("lint", help="validate the schemas and views already installed")

    args = parser.parse_args()

    try:
        if args.command == "from-ini":
            spec = spec_from_ini(
                args.ini, args.mod_id, args.title,
                description=args.description, accent=args.accent,
                ini_relpath=f"SFSE/Plugins/{args.ini.name}",
            )
            problems = validate_spec(spec)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            count = sum(len(g["settings"]) for g in spec["settings"]["groups"])
            print(f"[ok]   {args.output} ({len(spec['settings']['groups'])} groups, {count} settings)")
            return _report(problems, f"{args.mod_id} spec")

        if args.command == "validate":
            status = 0
            for path in args.spec:
                spec = _load_spec(path)
                status |= _report(validate_spec(spec), f"{path.name} ({spec.get('modId', '?')})")
            return status

        if args.command in ("build", "install"):
            root = args.data if args.command == "install" else args.out
            status = 0
            for path in args.spec:
                spec = _load_spec(path)
                problems = validate_spec(spec)
                if problems:
                    status |= _report(problems, f"{path.name} (nothing written)")
                    continue
                written = emit(spec, root, for_install=args.command == "install")
                print(f"[ok]   {spec['modId']}: {len(written)} file(s) -> {root}")
                for file in written:
                    print(f"       {file}")
            return status

        if args.command == "preview":
            spec = _load_spec(args.spec)
            problems = validate_spec(spec)
            if problems:
                return _report(problems, f"{args.spec.name} (nothing written)")
            views = spec.get("views", [])
            if not views:
                raise SpecError(f"{args.spec}: spec declares no views to preview")
            view = views[0] if args.view is None else next((v for v in views if v["name"] == args.view), None)
            if view is None:
                raise SpecError(f"no view named {args.view!r} (have: {', '.join(v['name'] for v in views)})")
            index = build_preview(spec, view, args.out)
            print(f"[ok]   preview -> {index}")
            if args.open:
                webbrowser.open(index.as_uri())
            return 0

        if args.command == "lint":
            checked, problems = lint_installed(args.data)
            print(f"[info] checked {checked} file(s) under {args.data}")
            return _report(problems, "installed OSF UI tree")

    except SpecError as exc:
        print(f"[fail] {exc}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
