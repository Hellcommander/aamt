#!/usr/bin/env python3
"""
Qud Spring UI pipeline: a window layout spec (JSON) -> a Spring Molting (modern UI) prefab bundle for a mod.

    spec.springui.json  ->  <out>/<Prefab>.resolved.json     theme tokens inlined; what the Unity builder reads
                            <out>/previews/<Prefab>.png       Pillow mock-up of the layout at the reference size
                            <out>/contract.txt                the object names the mod's runtime looks up
                            <out>/manifest.json               what was generated, for the build/install steps

The prefab holds only plain uGUI objects (RectTransform, Image, ScrollRect, layout groups). The mod's C#
(SpringMenuWindow / ConjoinedPickerScreen) finds objects by NAME and attaches the game's own components at
runtime (TextMeshPro + UITextSkin, FrameworkScroller, UIThreeColorProperties, ...), so a spec is mostly rects,
fills, borders and layout groups. Editor/BuildQudUI.cs turns the resolved spec into Assets/QudUI/<Prefab>.prefab
and one asset bundle per platform (Unity 6000.0.77f1, the game's version).

Commands
    generate <spec> [--out DIR] [--no-lint] [--preview] [--theme-dir DIR]
    lint     <spec>                                   schema, names, rects, layout, runtime contract; no Unity
    preview  <spec> [--out DIR] [--scale F]           only the PNG mock-up
    install  <out DIR> [--mod-path DIR] [--force]     copy <out>/Bundles into the mod
    contract [kind]                                   print the runtime name contract(s)
    schema                                            print the spec reference

Run with `python -I` from anywhere; paths in a spec are relative to the spec file.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
TOOLS_ROOT = HERE.parent.parent
THEME_DIR = HERE / "themes"

NODE_TYPES = ("panel", "text", "scroll", "image", "template")
LAYOUT_TYPES = ("vertical", "horizontal", "grid")
FITTER_MODES = ("vertical", "horizontal", "both")
ALIGNMENTS = ("UpperLeft", "UpperCenter", "UpperRight", "MiddleLeft", "MiddleCenter", "MiddleRight",
              "LowerLeft", "LowerCenter", "LowerRight")
TEXT_SIZES = {"header": 26, "normal": 17, "small": 14, "xsmall": 12}

# ------------------------------------------------------------------------------------------- runtime contracts
# Mirrors of the names the mods' C# looks up (SpringMenuWindow.Wire / ConjoinedPickerScreen.Wire). Keep in sync.
CONTRACTS = {
    "springmenu": {
        "runtime": "Mods/Arendeth_SpringUI/SpringMenuWindow.cs",
        "required": [
            "TitleText", "StatusText", "Body",
            "HeaderScroll", "HeaderViewport", "HeaderContent", "HeaderText",
            "ListScroll", "ListViewport", "ListContent",
            "DetailScroll", "DetailViewport", "DetailContent", "DetailText",
            "HotkeyBar", "HotkeyContent", "HintText",
            "Templates", "RowTemplate", "Selection", "HotkeySlot", "HotkeyText", "IconSlot", "Icon",
            "LabelText", "SecondaryText",
        ],
        "scroll": ["HeaderScroll", "ListScroll", "DetailScroll", "HotkeyBar"],
        "layout": {"ListContent": "vertical", "HotkeyContent": "horizontal", "DetailContent": "vertical",
                   "HeaderContent": "vertical", "RowTemplate": "horizontal"},
        "text": ["TitleText", "StatusText", "HeaderText", "DetailText", "HintText", "HotkeyText", "LabelText",
                 "SecondaryText"],
        "template": {"container": "Templates", "template": "RowTemplate"},
        "element": ["HeaderScroll", "ListScroll", "HotkeyBar", "RowTemplate"],
        "accent": True,
    },
    "conjoined_picker": {
        "runtime": "Mods/Arendeth_Conjoined_Extended/UI/ConjoinedPickerScreen.cs",
        "required": [
            "TitleText", "PromptText", "ChosenRow", "SearchBar", "SearchText",
            "GridScroll", "GridViewport", "GridContent",
            "DetailScroll", "DetailViewport", "DetailContent", "DetailText",
            "HotkeyBar", "HotkeyContent", "StatusText",
            "Templates", "TileTemplate", "Icon", "Frame", "Badge", "BadgeText",
        ],
        "scroll": ["GridScroll", "DetailScroll", "HotkeyBar"],
        "layout": {"GridContent": "grid", "HotkeyContent": "horizontal", "DetailContent": "vertical",
                   "ChosenRow": "horizontal"},
        "text": ["TitleText", "PromptText", "SearchText", "DetailText", "StatusText", "BadgeText"],
        "template": {"container": "Templates", "template": "TileTemplate"},
        "element": ["GridScroll", "HotkeyBar"],
        "accent": False,
    },
    "custom": {"runtime": "(your own window class)", "required": [], "scroll": [], "layout": {}, "text": [],
               "template": None, "element": [], "accent": False},
}

SCHEMA_TEXT = """\
Spring UI spec (*.springui.json)
================================

{
  "mod": "Arendeth_SpringUI",          mod id (messages); install target is <Mods>/<modFolder>
  "modFolder": "Arendeth_SpringUI",    folder under Mods when it differs from the id
  "bundle": "arendeth_springui",       lower case [a-z0-9_]; file Bundles/<platform>/<bundle>_<platform>
  "prefab": "SpringMenu",              prefab asset name == root object name; what the runtime LoadAsset()s
  "kind": "springmenu",                runtime contract to lint against: springmenu | conjoined_picker | custom
  "theme": "qud-dark",                 themes/<name>.theme.json, a path, or an inline {"colors": {...}} object
  "reference": [1600, 900],            preview canvas size (the game UI is anchor-based; this is only the mock-up)
  "root": { <node> }                   the window root; it gets Canvas + GraphicRaycaster + CanvasGroup
}

Node
----
{
  "name": "Frame",                     unique; the runtime finds objects by name
  "type": "panel",                     panel | text | scroll | image | template
                                         panel    RectTransform (+ fill Image, border, layout group)
                                         text     empty RectTransform; the runtime adds TextMeshPro + UITextSkin
                                         scroll   ScrollRect; "scroll": {"viewport": <child>, "content": <descendant>}
                                         image    Image meant for a sprite (icon); "preserveAspect": true
                                         template inactive container whose children are cloned at runtime
  "rect": one of
      {"stretch": [left, bottom, right, top]}                 fill the parent minus pixel margins
      {"anchors": [minX, minY, maxX, maxY]}                   fractional anchors, no margins
      {"top": [fromTop, height, sideMargin]}                  full-width band hugging the top
      {"bottom": [fromBottom, height, sideMargin]}            full-width band hugging the bottom
      {"left": [fromLeft, width]}                             full-height band hugging the left edge
      {"right": [fromRight, width]}                           full-height band hugging the right edge
      {"topStretch": true}                                    scroll content: stretches wide, grows down
      {"size": [w, h], "anchor": [ax, ay], "pivot": [px, py], "pos": [x, y]}   fixed-size element
      (omit when a parent layout group positions the node)
  "fill": "panel",                     theme color token or #RRGGBB[AA]; omit for no Image
  "raycast": false,                    the fill Image blocks/receives pointer events (needed on scroll viewports
                                       and on anything hoverable); default false
  "border": {"color": "border", "thickness": 1},   four thin edge Images (ignored by layout groups)
  "layout": {"type": "vertical", "spacing": 2, "padding": [6, 6, 6, 6], "alignment": "UpperLeft",
             "controlWidth": true, "controlHeight": true, "expandWidth": true, "expandHeight": false,
             "cell": [40, 56], "cellSpacing": [6, 6]}          grid uses cell / cellSpacing
  "element": {"minHeight": 30, "preferredHeight": 120, "flexibleHeight": 1, "flexibleWidth": 1,
              "minWidth": 34, "preferredWidth": 34, "ignoreLayout": true}     LayoutElement
  "fitter": "vertical",                ContentSizeFitter preferred-size on that axis (vertical | horizontal | both)
  "mask": true,                        RectMask2D (scroll viewports)
  "scroll": {"horizontal": false, "vertical": true, "sensitivity": 20, "inertia": false,
             "viewport": "ListViewport", "content": "ListContent"}
  "preserveAspect": true,              image only
  "active": false,                     start inactive (the Templates container); templates themselves stay active
  "accent": true,                      runtime tints this Image with the caller's accent color; name must start
                                       with "Accent" (springmenu kind only)
  "text": {"sample": "Mount Anchoring", "size": "header", "color": "text", "align": "center"}
                                       preview only: what to draw there (header | normal | small | xsmall)
  "preview": {"repeat": "RowTemplate", "count": 9,            preview only: clone a template into this content;
              "selected": 2, "activate": ["Selection"]}       clone #selected also draws those inactive children
  "children": [ <node>, ... ]
}

Theme (themes/<name>.theme.json)
--------------------------------
{ "name": "qud-dark", "colors": { "backdrop": "#000000D6", "frame": "#0B0D0EFA", "panel": "#12161A",
  "border": "#5C7370", "status": "#1A1F22", "select": "#FFFF0029", "selectEdge": "#FFFF00E6",
  "accent": "#FFFF00", "badge": "#C02E2E", "text": "#B1C9C3", "textBright": "#FFFFFF", "textMuted": "#6B7A7A",
  "transparent": "#00000000" } }
Any token can be used as a fill / border / text color; unknown tokens fail lint.
"""


# ------------------------------------------------------------------------------------------------------ helpers

class SpecError(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as ex:
        raise SpecError(f"{path}: invalid JSON: {ex}") from ex


def load_theme(spec: dict, spec_dir: Path, theme_dir: Path | None) -> dict:
    t = spec.get("theme", "qud-dark")
    if isinstance(t, dict):
        theme = t
    else:
        cands = []
        p = Path(str(t))
        if p.suffix == ".json":
            cands.append(spec_dir / p)
        for d in (theme_dir, spec_dir / "themes", THEME_DIR):
            if d is not None:
                cands.append(Path(d) / f"{t}.theme.json")
        found = next((c for c in cands if c.exists()), None)
        if found is None:
            raise SpecError(f"theme '{t}' not found (looked in {', '.join(str(c) for c in cands)})")
        theme = load_json(found)
    colors = theme.get("colors")
    if not isinstance(colors, dict) or not colors:
        raise SpecError("theme has no 'colors' object")
    for k, v in colors.items():
        parse_color(v, f"theme color '{k}'")
    return theme


def parse_color(value: str, where: str) -> tuple[int, int, int, int]:
    if not isinstance(value, str) or not value.startswith("#") or len(value) not in (7, 9):
        raise SpecError(f"{where}: color must be #RRGGBB or #RRGGBBAA, got {value!r}")
    try:
        r, g, b = int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
        a = int(value[7:9], 16) if len(value) == 9 else 255
    except ValueError as ex:
        raise SpecError(f"{where}: bad hex color {value!r}") from ex
    return r, g, b, a


def resolve_color(token, theme: dict, where: str) -> str:
    if token is None:
        return None
    if isinstance(token, str) and token.startswith("#"):
        parse_color(token, where)
        return token.upper() if len(token) == 9 else (token.upper() + "FF")
    colors = theme["colors"]
    if token not in colors:
        raise SpecError(f"{where}: unknown theme color token {token!r} (have: {', '.join(sorted(colors))})")
    v = colors[token]
    return v.upper() if len(v) == 9 else (v.upper() + "FF")


def walk(node: dict, parent=None, depth=0):
    yield node, parent, depth
    for c in node.get("children", []) or []:
        yield from walk(c, node, depth + 1)


def find(node: dict, name: str):
    for n, _, _ in walk(node):
        if n.get("name") == name:
            return n
    return None


# --------------------------------------------------------------------------------------------------------- lint

def lint_spec(spec: dict, spec_path: Path, theme: dict) -> list[str]:
    errors: list[str] = []

    def err(msg):
        errors.append(msg)

    for key in ("mod", "bundle", "prefab", "root"):
        if key not in spec:
            err(f"missing top-level '{key}'")
    bundle = spec.get("bundle", "")
    if bundle and (bundle != bundle.lower() or not all(c.isalnum() or c == "_" for c in bundle)):
        err(f"bundle must be lower-case [a-z0-9_]: {bundle!r}")
    kind = spec.get("kind", "custom")
    if kind not in CONTRACTS:
        err(f"kind must be one of {', '.join(CONTRACTS)}: {kind!r}")
        kind = "custom"
    ref = spec.get("reference", [1600, 900])
    if not (isinstance(ref, list) and len(ref) == 2 and all(isinstance(x, (int, float)) and x > 0 for x in ref)):
        err("reference must be [width, height]")
    root = spec.get("root")
    if not isinstance(root, dict):
        return errors or ["root is not an object"]
    if root.get("name") != spec.get("prefab"):
        err(f"root name {root.get('name')!r} must equal prefab {spec.get('prefab')!r} (the runtime LoadAsset()s it)")

    names: dict[str, int] = {}
    for node, parent, depth in walk(root):
        name = node.get("name")
        where = f"node {name!r}" if name else f"unnamed node at depth {depth}"
        if not name or not isinstance(name, str):
            err(f"{where}: every node needs a 'name'")
            continue
        names[name] = names.get(name, 0) + 1
        t = node.get("type", "panel")
        if t not in NODE_TYPES:
            err(f"{where}: type must be one of {', '.join(NODE_TYPES)}")
        for k in node:
            if k not in ("name", "type", "rect", "fill", "raycast", "border", "layout", "element", "fitter", "mask",
                         "scroll", "preserveAspect", "active", "accent", "text", "preview", "children"):
                err(f"{where}: unknown key {k!r}")
        rect = node.get("rect")
        if rect is not None:
            if not isinstance(rect, dict) or len([k for k in rect if k in ("stretch", "anchors", "top", "bottom", "left", "right", "topStretch", "size")]) != 1:
                err(f"{where}: rect needs exactly one of stretch / anchors / top / bottom / left / right / topStretch / size")
            else:
                if "anchors" in rect:
                    a = rect["anchors"]
                    ok = isinstance(a, list) and len(a) == 4 and all(isinstance(x, (int, float)) for x in a)
                    if not ok or not (0 <= a[0] < a[2] <= 1 and 0 <= a[1] < a[3] <= 1):
                        err(f"{where}: anchors must be [minX, minY, maxX, maxY] within 0..1 with min < max")
                for k, n in (("stretch", 4), ("top", 3), ("bottom", 3), ("left", 2), ("right", 2), ("size", 2)):
                    if k in rect and not (isinstance(rect[k], list) and len(rect[k]) == n and all(isinstance(x, (int, float)) for x in rect[k])):
                        err(f"{where}: rect.{k} must be a list of {n} numbers")
        elif parent is not None and not (parent.get("layout")):
            err(f"{where}: needs a rect (its parent has no layout group to position it)")
        if node.get("fill") is not None:
            try:
                resolve_color(node["fill"], theme, f"{where} fill")
            except SpecError as ex:
                err(str(ex))
        b = node.get("border")
        if b is not None:
            if not isinstance(b, dict):
                err(f"{where}: border must be an object")
            else:
                try:
                    resolve_color(b.get("color", "border"), theme, f"{where} border")
                except SpecError as ex:
                    err(str(ex))
                if not isinstance(b.get("thickness", 1), (int, float)) or b.get("thickness", 1) <= 0:
                    err(f"{where}: border.thickness must be > 0")
        lay = node.get("layout")
        if lay is not None:
            if not isinstance(lay, dict) or lay.get("type") not in LAYOUT_TYPES:
                err(f"{where}: layout.type must be one of {', '.join(LAYOUT_TYPES)}")
            else:
                if lay.get("alignment", "UpperLeft") not in ALIGNMENTS:
                    err(f"{where}: layout.alignment must be one of {', '.join(ALIGNMENTS)}")
                pad = lay.get("padding", [0, 0, 0, 0])
                if not (isinstance(pad, list) and len(pad) == 4):
                    err(f"{where}: layout.padding must be [left, right, top, bottom]")
                if lay["type"] == "grid":
                    cell = lay.get("cell")
                    if not (isinstance(cell, list) and len(cell) == 2):
                        err(f"{where}: grid layout needs cell: [w, h]")
        fit = node.get("fitter")
        if fit is not None and fit not in FITTER_MODES:
            err(f"{where}: fitter must be one of {', '.join(FITTER_MODES)}")
        if t == "scroll":
            sc = node.get("scroll") or {}
            vp, ct = sc.get("viewport"), sc.get("content")
            if not ct:
                err(f"{where}: scroll needs scroll.content (a descendant name)")
            else:
                if find(node, ct) is None or ct == name:
                    err(f"{where}: scroll.content {ct!r} is not a descendant")
            if vp and (find(node, vp) is None or vp == name):
                err(f"{where}: scroll.viewport {vp!r} is not a descendant")
            if ct and find(node, ct) is not None and not (find(node, ct).get("rect") or {}).get("topStretch") and not sc.get("horizontalOnly"):
                if sc.get("vertical", True):
                    err(f"{where}: vertical scroll content {ct!r} should use rect {{\"topStretch\": true}}")
        if node.get("accent"):
            if not name.startswith("Accent"):
                err(f"{where}: accent nodes must be named Accent* (the runtime tints Images by that prefix)")
            if not node.get("fill"):
                err(f"{where}: accent node needs a fill Image to tint")
            if not CONTRACTS[kind]["accent"]:
                err(f"{where}: kind {kind!r} runtime does not tint accents")
        tx = node.get("text")
        if tx is not None:
            if t != "text":
                err(f"{where}: 'text' preview block only on type text")
            if tx.get("size", "normal") not in TEXT_SIZES:
                err(f"{where}: text.size must be one of {', '.join(TEXT_SIZES)}")
            if tx.get("color") is not None:
                try:
                    resolve_color(tx["color"], theme, f"{where} text color")
                except SpecError as ex:
                    err(str(ex))
        pv = node.get("preview")
        if pv is not None:
            rep = pv.get("repeat")
            if not rep or find(root, rep) is None:
                err(f"{where}: preview.repeat must name an existing template node")
            act = pv.get("activate", [])
            if not isinstance(act, list) or any(not isinstance(a, str) for a in act):
                err(f"{where}: preview.activate must be a list of node names")
            elif rep and find(root, rep) is not None:
                for a in act:
                    if find(find(root, rep), a) is None:
                        err(f"{where}: preview.activate {a!r} is not inside template {rep!r}")
    for n, c in names.items():
        if c > 1:
            errors.append(f"duplicate node name {n!r} ({c}x): the runtime looks objects up by name")

    # runtime contract
    contract = CONTRACTS[kind]
    for req in contract["required"]:
        if req not in names:
            errors.append(f"[{kind}] missing required object {req!r} (looked up by {contract['runtime']})")
    for s in contract["scroll"]:
        n = find(root, s)
        if n is not None and n.get("type") != "scroll":
            errors.append(f"[{kind}] {s!r} must be type scroll")
    for n_name, lt in contract["layout"].items():
        n = find(root, n_name)
        if n is not None and (n.get("layout") or {}).get("type") != lt:
            errors.append(f"[{kind}] {n_name!r} must have a {lt} layout group")
    for tname in contract["text"]:
        n = find(root, tname)
        if n is not None and n.get("type") != "text":
            errors.append(f"[{kind}] {tname!r} must be type text (empty RectTransform for the runtime's TextMeshPro)")
    for ename in contract["element"]:
        n = find(root, ename)
        if n is not None and n.get("element") is None:
            errors.append(f"[{kind}] {ename!r} needs an 'element' (LayoutElement): FrameworkScroller reads it from the ScrollRect object")
    tpl = contract["template"]
    if tpl:
        cont, t = find(root, tpl["container"]), find(root, tpl["template"])
        if cont is not None and cont.get("active", True):
            errors.append(f"[{kind}] {tpl['container']!r} must be active: false (hidden template container)")
        if t is not None and not t.get("active", True):
            errors.append(f"[{kind}] {tpl['template']!r} must stay active (clones copy its active state)")
        if cont is not None and t is not None and find(cont, tpl["template"]) is None:
            errors.append(f"[{kind}] {tpl['template']!r} must be a child of {tpl['container']!r}")
    return errors


# ------------------------------------------------------------------------------------------------------ resolve

def resolve_spec(spec: dict, theme: dict) -> dict:
    """Inline theme colors so the Unity builder is theme-agnostic."""
    out = json.loads(json.dumps(spec))
    out["theme"] = {"name": theme.get("name", "inline")}

    def fix(node):
        if node.get("fill") is not None:
            node["fill"] = resolve_color(node["fill"], theme, node.get("name", "?"))
        b = node.get("border")
        if isinstance(b, dict):
            b["color"] = resolve_color(b.get("color", "border"), theme, node.get("name", "?"))
            b.setdefault("thickness", 1)
        tx = node.get("text")
        if isinstance(tx, dict) and tx.get("color") is not None:
            tx["color"] = resolve_color(tx["color"], theme, node.get("name", "?"))
        for c in node.get("children", []) or []:
            fix(c)

    fix(out["root"])
    return out


# ------------------------------------------------------------------------------------------------------ preview

def _rect_of(node: dict, parent_rect) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) in preview pixels, y down. parent_rect is the parent's rect."""
    px0, py0, px1, py1 = parent_rect
    pw, ph = px1 - px0, py1 - py0
    r = node.get("rect") or {"stretch": [0, 0, 0, 0]}
    if "stretch" in r:
        l, b, rr, t = r["stretch"]
        return px0 + l, py0 + t, px1 - rr, py1 - b
    if "anchors" in r:
        ax0, ay0, ax1, ay1 = r["anchors"]
        return px0 + pw * ax0, py1 - ph * ay1, px0 + pw * ax1, py1 - ph * ay0
    if "top" in r:
        ft, h, m = r["top"]
        return px0 + m, py0 + ft, px1 - m, py0 + ft + h
    if "bottom" in r:
        fb, h, m = r["bottom"]
        return px0 + m, py1 - fb - h, px1 - m, py1 - fb
    if "left" in r:
        fl, w = r["left"]
        return px0 + fl, py0, px0 + fl + w, py1
    if "right" in r:
        fr, w = r["right"]
        return px1 - fr - w, py0, px1 - fr, py1
    if "topStretch" in r:
        return px0, py0, px1, py1
    if "size" in r:
        w, h = r["size"]
        ax, ay = r.get("anchor", [0.5, 0.5])
        pvx, pvy = r.get("pivot", [0.5, 0.5])
        ox, oy = r.get("pos", [0, 0])
        cx = px0 + pw * ax + ox
        cy = py1 - ph * ay - oy
        x0 = cx - w * pvx
        y0 = cy - h * (1 - pvy)
        return x0, y0, x0 + w, y0 + h
    return parent_rect


def _preferred_height(node: dict, width: float) -> float:
    el = node.get("element") or {}
    if el.get("preferredHeight"):
        return float(el["preferredHeight"])
    if node.get("type") == "text":
        tx = node.get("text") or {}
        size = TEXT_SIZES.get(tx.get("size", "normal"), 17)
        sample = tx.get("sample", node.get("name", ""))
        chars_per_line = max(8, int(width / (size * 0.55))) if width > 0 else 60
        lines = 0
        for para in str(sample).split("\n"):
            lines += max(1, -(-len(para) // chars_per_line))
        return lines * size * 1.3 + 4
    if node.get("layout"):
        return _layout_height(node, width)
    r = node.get("rect") or {}
    if "size" in r:
        return float(r["size"][1])
    if "top" in r or "bottom" in r:
        return float((r.get("top") or r.get("bottom"))[1])
    return float(el.get("minHeight", 28))


def _layout_height(node: dict, width: float) -> float:
    lay = node["layout"]
    pad = lay.get("padding", [0, 0, 0, 0])
    kids = [c for c in node.get("children", []) if c.get("active", True) and not (c.get("element") or {}).get("ignoreLayout")]
    inner_w = width - pad[0] - pad[1]
    if lay["type"] == "vertical":
        total = pad[2] + pad[3] + lay.get("spacing", 0) * max(0, len(kids) - 1)
        for k in kids:
            total += _preferred_height(k, inner_w)
        return total
    if lay["type"] == "horizontal":
        return pad[2] + pad[3] + (max([_preferred_height(k, inner_w) for k in kids]) if kids else 0)
    cell = lay.get("cell", [40, 56])
    return pad[2] + pad[3] + cell[1]


def render_preview(spec: dict, theme: dict, out_png: Path, scale: float = 1.0) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    W, H = spec.get("reference", [1600, 900])
    W, H = int(W * scale), int(H * scale)
    img = Image.new("RGBA", (W, H), (28, 30, 32, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    # a faux game map behind the window so the backdrop alpha reads correctly
    for y in range(0, H, 24):
        for x in range(0, W, 16):
            if (x // 16 + y // 24) % 7 == 0:
                draw.rectangle([x, y, x + 15, y + 23], fill=(40, 60, 44, 255))
            elif (x // 16 * 3 + y // 24) % 11 == 0:
                draw.text((x + 3, y + 4), ".", fill=(90, 110, 90, 255))

    def font(size):
        try:
            return ImageFont.truetype("consola.ttf", int(size * scale))
        except Exception:
            try:
                return ImageFont.load_default(int(size * scale))
            except Exception:
                return ImageFont.load_default()

    def col(token, where):
        return parse_color(resolve_color(token, theme, where), where)

    def fill_rect(x0, y0, x1, y1, color):
        """Alpha-composited rectangle fill (ImageDraw would overwrite pixels)."""
        ix0, iy0, ix1, iy1 = int(x0), int(y0), int(round(x1)), int(round(y1))
        if ix1 <= ix0 or iy1 <= iy0:
            return
        if color[3] >= 255:
            draw.rectangle([ix0, iy0, ix1 - 1, iy1 - 1], fill=color)
            return
        if color[3] <= 0:
            return
        layer = Image.new("RGBA", (ix1 - ix0, iy1 - iy0), color)
        img.alpha_composite(layer, dest=(max(0, ix0), max(0, iy0)))

    def draw_text(node, rect, muted=False):
        tx = node.get("text") or {}
        size = TEXT_SIZES.get(tx.get("size", "normal"), 17)
        color = col(tx.get("color", "textMuted" if muted else "text"), node["name"])
        sample = str(tx.get("sample", node["name"]))
        f = font(size)
        x0, y0, x1, y1 = rect
        maxw = max(10, x1 - x0 - 6)
        lines = []
        for para in sample.split("\n"):
            words, cur = para.split(" "), ""
            for w in words:
                trial = (cur + " " + w).strip()
                if draw.textlength(trial, font=f) <= maxw or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
        align = tx.get("align", "left")
        lh = size * 1.3 * scale
        total = lh * len(lines)
        valign = tx.get("valign", "middle" if (y1 - y0) < lh * 2.2 else "top")
        y = y0 + 3 if valign == "top" else y0 + ((y1 - y0) - total) / 2
        for ln in lines:
            if y + lh > y1 + 2:
                break
            tw = draw.textlength(ln, font=f)
            x = x0 + 4 if align == "left" else (x1 - 4 - tw if align == "right" else x0 + ((x1 - x0) - tw) / 2)
            draw.text((x, y), ln, fill=color, font=f)
            y += lh

    activate_names: set = set()

    def paint(node, rect, template_mode=False):
        if not node.get("active", True) and not template_mode and node.get("name") not in activate_names:
            return
        x0, y0, x1, y1 = rect
        if x1 <= x0 or y1 <= y0:
            return
        fill = node.get("fill")
        if fill is not None:
            fill_rect(x0, y0, x1, y1, col(fill, node["name"]))
        b = node.get("border")
        if b:
            th = max(1, int(round(b.get("thickness", 1) * scale)))
            draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=col(b.get("color", "border"), node["name"]), width=th)
        if node.get("type") == "text":
            draw_text(node, rect)
        if node.get("type") == "image":
            # icon placeholder: a tile-ish glyph box
            draw.rectangle([x0 + 2, y0 + 2, x1 - 3, y1 - 3], outline=(180, 190, 160, 200), width=1)
            draw.text((x0 + (x1 - x0) / 2 - 4, y0 + (y1 - y0) / 2 - 7), "@", fill=(220, 200, 90, 255), font=font(14))

        kids = [c for c in node.get("children", []) if c.get("active", True) or c.get("name") in activate_names]
        lay = node.get("layout")
        pv = node.get("preview")
        if pv and pv.get("repeat"):
            tpl = find(spec["root"], pv["repeat"])
            if tpl is not None:
                count = int(pv.get("count", 6))
                sel = pv.get("selected")
                clones = []
                for i in range(count):
                    if sel is not None and i == int(sel):
                        # the selected clone also paints its inactive highlight children (Selection, Frame, ...)
                        marked = json.loads(json.dumps(tpl))
                        marked["__selected__"] = True
                        clones.append(marked)
                    else:
                        clones.append(tpl)
                kids = kids + clones
        if lay:
            pad = lay.get("padding", [0, 0, 0, 0])
            inner = (x0 + pad[0], y0 + pad[2], x1 - pad[1], y1 - pad[3])
            ignored = [c for c in kids if (c.get("element") or {}).get("ignoreLayout")]
            flow = [c for c in kids if c not in ignored]
            for c in ignored:
                paint(c, _rect_of(c, rect), True)
            def paint_child(c, r):
                if c.get("__selected__"):
                    added = set((pv or {}).get("activate", []))
                    activate_names.update(added)
                    try:
                        paint(c, r, True)
                    finally:
                        activate_names.difference_update(added)
                else:
                    paint(c, r, True)

            if lay["type"] == "vertical":
                iw = inner[2] - inner[0]
                heights = [_preferred_height(c, iw) for c in flow]
                flex = [float((c.get("element") or {}).get("flexibleHeight", 0) or 0) for c in flow]
                spacing = lay.get("spacing", 0)
                used = sum(heights) + spacing * max(0, len(flow) - 1)
                spare = max(0.0, (inner[3] - inner[1]) - used)
                tflex = sum(flex)
                y = inner[1]
                for c, h, fx in zip(flow, heights, flex):
                    h2 = h + (spare * fx / tflex if tflex > 0 else 0)
                    paint_child(c, (inner[0], y, inner[2], y + h2))
                    y += h2 + spacing
            elif lay["type"] == "horizontal":
                ih = inner[3] - inner[1]
                spacing = lay.get("spacing", 0)
                widths = []
                for c in flow:
                    el = c.get("element") or {}
                    w = el.get("preferredWidth") or el.get("minWidth")
                    if w is None:
                        r = c.get("rect") or {}
                        w = r["size"][0] if "size" in r else None
                    if w is None and c.get("type") == "text":
                        tx = c.get("text") or {}
                        w = draw.textlength(str(tx.get("sample", c["name"])), font=font(TEXT_SIZES.get(tx.get("size", "normal"), 17))) / scale + 12
                    widths.append(float(w) if w is not None else 0.0)
                flex = [float((c.get("element") or {}).get("flexibleWidth", 0) or 0) for c in flow]
                used = sum(widths) + spacing * max(0, len(flow) - 1)
                spare = max(0.0, (inner[2] - inner[0]) - used)
                tflex = sum(flex)
                align = lay.get("alignment", "UpperLeft")
                x = inner[0]
                if tflex == 0 and "Center" in align:
                    x = inner[0] + spare / 2
                for c, w, fx in zip(flow, widths, flex):
                    w2 = w + (spare * fx / tflex if tflex > 0 else 0)
                    ch = _preferred_height(c, w2)
                    if (c.get("element") or {}).get("flexibleHeight") or lay.get("expandHeight") or lay.get("controlHeight"):
                        ch = ih
                    cy = inner[1] + (ih - ch) / 2 if "Middle" in align else inner[1]
                    paint_child(c, (x, cy, x + w2, cy + ch))
                    x += w2 + spacing
            else:  # grid
                cw, chh = lay.get("cell", [40, 56])
                sx, sy = lay.get("cellSpacing", [0, 0])
                cols = max(1, int((inner[2] - inner[0] + sx) // (cw + sx)))
                for i, c in enumerate(flow):
                    gx = inner[0] + (i % cols) * (cw + sx)
                    gy = inner[1] + (i // cols) * (chh + sy)
                    if gy + chh > inner[3] + chh:
                        break
                    paint_child(c, (gx, gy, gx + cw, gy + chh))
        else:
            for c in kids:
                paint(c, _rect_of(c, rect), template_mode)

    root = spec["root"]
    paint(root, (0, 0, W, H))

    # caption
    f = font(13)
    cap = f"{spec.get('prefab')}  ·  {spec.get('bundle')}  ·  theme {theme.get('name', 'inline')}  ·  {spec.get('reference', [1600, 900])[0]}x{spec.get('reference', [1600, 900])[1]} mock-up (fonts/sizes approximate; the game lays out with anchors + layout groups)"
    draw.rectangle([0, H - 20 * scale, W, H], fill=(0, 0, 0, 200))
    draw.text((6, H - 17 * scale), cap, fill=(200, 200, 200, 255), font=f)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_png)
    return out_png


# ------------------------------------------------------------------------------------------------------ install

def default_mods_root() -> Path:
    env = os.environ.get("COQ_MODS_ROOT")
    if env:
        return Path(env)
    return Path(os.path.expanduser("~")) / "AppData" / "LocalLow" / "Freehold Games" / "CavesOfQud" / "Mods"


def install(outdir: Path, mod_path: Path | None, force: bool) -> int:
    manifest_path = outdir / "manifest.json"
    if not manifest_path.exists():
        print(f"no manifest.json in {outdir}; run generate first", file=sys.stderr)
        return 2
    manifest = load_json(manifest_path)
    bundle = manifest["bundle"]
    if mod_path is None:
        mod_path = default_mods_root() / (manifest.get("modFolder") or manifest["mod"])
    mod_path = Path(mod_path)
    if not mod_path.exists():
        print(f"mod folder not found: {mod_path}", file=sys.stderr)
        return 2
    src_root = outdir / "Bundles"
    if not src_root.exists():
        print(f"no Bundles under {outdir}; run the Unity build first (-Build)", file=sys.stderr)
        return 2
    copied = 0
    for plat in ("windows", "osx", "linux"):
        src = src_root / plat / f"{bundle}_{plat}"
        if not src.exists():
            continue
        dst = mod_path / "Bundles" / plat / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and not force and dst.stat().st_mtime >= src.stat().st_mtime:
            print(f"  up to date: {dst}")
            continue
        shutil.copy2(src, dst)
        copied += 1
        print(f"  installed: {dst} ({dst.stat().st_size // 1024} KB)")
    if copied == 0:
        print("nothing copied (no bundles found or all up to date)")
    return 0


# ----------------------------------------------------------------------------------------------------- commands

def _prepare(spec_path: Path, theme_dir: str | None):
    spec_path = spec_path.resolve()
    spec = load_json(spec_path)
    theme = load_theme(spec, spec_path.parent, Path(theme_dir) if theme_dir else None)
    return spec_path, spec, theme


def _out_dir(args, spec) -> Path:
    if getattr(args, "out", None):
        return Path(args.out).resolve()
    return TOOLS_ROOT / "Output" / "QudSpringUI" / spec.get("bundle", spec.get("prefab", "ui"))


def cmd_lint(args) -> int:
    try:
        spec_path, spec, theme = _prepare(Path(args.spec), args.theme_dir)
        errors = lint_spec(spec, spec_path, theme)
    except SpecError as ex:
        print(f"LINT ERROR: {ex}")
        return 1
    if errors:
        for e in errors:
            print(f"LINT ERROR: {e}")
        print(f"{len(errors)} problem(s) in {spec_path.name}")
        return 1
    print(f"lint OK: {spec_path.name} ({spec.get('kind', 'custom')} contract, theme {theme.get('name')})")
    return 0


def cmd_generate(args) -> int:
    try:
        spec_path, spec, theme = _prepare(Path(args.spec), args.theme_dir)
    except SpecError as ex:
        print(f"ERROR: {ex}")
        return 1
    if not args.no_lint:
        errors = lint_spec(spec, spec_path, theme)
        if errors:
            for e in errors:
                print(f"LINT ERROR: {e}")
            print(f"{len(errors)} problem(s); fix the spec or pass --no-lint")
            return 1
        print(f"lint OK ({spec.get('kind', 'custom')} contract)")
    out = _out_dir(args, spec)
    out.mkdir(parents=True, exist_ok=True)
    resolved = resolve_spec(spec, theme)
    resolved_path = out / f"{spec['prefab']}.resolved.json"
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)
    print(f"resolved spec: {resolved_path}")
    contract = CONTRACTS.get(spec.get("kind", "custom"), CONTRACTS["custom"])
    with open(out / "contract.txt", "w", encoding="utf-8") as f:
        f.write(f"kind: {spec.get('kind', 'custom')}\nruntime: {contract['runtime']}\nrequired object names:\n")
        for n in contract["required"]:
            f.write(f"  {n}\n")
    if args.preview:
        png = render_preview(spec, theme, out / "previews" / f"{spec['prefab']}.png", args.scale)
        print(f"preview: {png}")
    manifest = {
        "mod": spec["mod"],
        "modFolder": spec.get("modFolder", spec["mod"]),
        "bundle": spec["bundle"],
        "prefab": spec["prefab"],
        "kind": spec.get("kind", "custom"),
        "theme": theme.get("name", "inline"),
        "spec": str(spec_path),
        "resolved": str(resolved_path),
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"manifest: {out / 'manifest.json'}")
    return 0


def cmd_preview(args) -> int:
    try:
        spec_path, spec, theme = _prepare(Path(args.spec), args.theme_dir)
        out = _out_dir(args, spec)
        png = render_preview(spec, theme, out / "previews" / f"{spec['prefab']}.png", args.scale)
    except SpecError as ex:
        print(f"ERROR: {ex}")
        return 1
    print(f"preview: {png}")
    return 0


def cmd_install(args) -> int:
    return install(Path(args.out).resolve(), Path(args.mod_path).resolve() if args.mod_path else None, args.force)


def cmd_contract(args) -> int:
    kinds = [args.kind] if args.kind else list(CONTRACTS)
    for k in kinds:
        c = CONTRACTS.get(k)
        if c is None:
            print(f"unknown kind {k!r}; have {', '.join(CONTRACTS)}")
            return 1
        print(f"[{k}] runtime: {c['runtime']}")
        for n in c["required"]:
            notes = []
            if n in c["scroll"]:
                notes.append("scroll")
            if n in c["layout"]:
                notes.append(c["layout"][n] + " layout")
            if n in c["text"]:
                notes.append("text")
            if n in c["element"]:
                notes.append("element")
            print(f"  {n:<16} {', '.join(notes)}")
        print()
    return 0


def cmd_schema(args) -> int:
    print(SCHEMA_TEXT)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Qud Spring UI pipeline (AAMT)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="spec -> resolved spec, contract, preview, manifest")
    g.add_argument("spec")
    g.add_argument("--out")
    g.add_argument("--no-lint", action="store_true")
    g.add_argument("--preview", action="store_true")
    g.add_argument("--scale", type=float, default=1.0)
    g.add_argument("--theme-dir")
    g.set_defaults(func=cmd_generate)

    l = sub.add_parser("lint", help="validate a spec (schema, names, rects, runtime contract)")
    l.add_argument("spec")
    l.add_argument("--theme-dir")
    l.set_defaults(func=cmd_lint)

    p = sub.add_parser("preview", help="PNG mock-up only")
    p.add_argument("spec")
    p.add_argument("--out")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--theme-dir")
    p.set_defaults(func=cmd_preview)

    i = sub.add_parser("install", help="copy built bundles into the mod")
    i.add_argument("out")
    i.add_argument("--mod-path")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_install)

    c = sub.add_parser("contract", help="print the runtime object-name contract")
    c.add_argument("kind", nargs="?")
    c.set_defaults(func=cmd_contract)

    s = sub.add_parser("schema", help="print the spec reference")
    s.set_defaults(func=cmd_schema)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
