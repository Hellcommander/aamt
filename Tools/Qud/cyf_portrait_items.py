"""Generate detailed item art for CYF character-sheet portraits (local SD3.5, :1338).

Arendeth_CYFTiles draws every equipped item on a layered portrait at the portrait's anchor for
that slot (hand, head, face, body, back, missile, float). An item with art here is drawn from
its art; any other item falls back to its own game tile, scaled up. This script makes the art:
for each item it reads the blueprint (base game + enabled mods: display name, description,
inheritance), prompts SD in the portrait's style on a plain background, keys the background
out, trims it and records the slot and grip point:

  <out>/Textures/Portraits/_items/<Blueprint>.png
  <out>/Textures/Portraits/_items/items.xml   <item Blueprint= File= Slot= GripX= GripY= Scale= />

GripX/GripY (0..1 from the art's top-left) land on the anchor: the handle for held items, the
bottom centre for headwear, the centre otherwise. Scale (0..1) shrinks an item inside its
anchor box (a torch is shorter than a staff). Edit items.xml to tune; reruns keep edits unless
--force regenerates that item.

  python cyf_portrait_items.py <out_dir> --character <Characters/Name.date.xml>
  python cyf_portrait_items.py <out_dir> --items "Torch:hand,Walking Stick:hand,Filthy Toga:body"
  options: --seed N  --force  --steps 28  --userdata DIR  --workshop DIR  --game DIR

Fitted mode (--fitted <portrait folder with portrait.xml>): instead of a standalone picture, each item is
painted onto the character itself with refart (Shared/REFART.md): the portrait's layers are flattened, the
slot's body region (torso, head, ...) is repainted wearing the item, the item is cut out by name, and the cut
becomes <item Blueprint=...> in portrait.xml, drawn over the base and under horns/eye glow. The mod draws it
while that blueprint is equipped.
  python cyf_portrait_items.py <out_dir> --fitted <dir> --items "Filthy Toga:body" --subject "green slime mutant"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import quoteattr

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Shared"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "Shared"))
from sd_http_client import generate_image  # noqa: E402
from cyf_scan_content import DEFAULT_GAME, DEFAULT_USERDATA, DEFAULT_WORKSHOP, enabled_mods  # noqa: E402

SD_URL = "http://127.0.0.1:1338"
SLOTS = {"Hand": "hand", "Head": "head", "Face": "face", "Body": "body", "Back": "back",
         "Feet": "feet", "Missile Weapon": "missile", "Floating Nearby": "float"}

STYLE = ("isolated video game item art, chunky stylized, bold dark outline, cel shading with simple shaded "
         "materials, retro-futurist post-apocalyptic desert world, centered, whole object in frame, "
         "plain flat light grey background, no text")
NEGATIVE = ("person, hand, arm, body, head, face, mannequin, character, multiple objects, text, letters, "
            "watermark, signature, photo, photorealistic, 3d render, busy background, scenery, frame, border, cropped")
# slot -> (prompt pattern, width, height, grip x, grip y)
KINDS = {
    "hand": ("a single {name} standing upright, vertical, the handle at the bottom", 512, 1024, 0.5, 0.75),
    "missile": ("a single {name} standing upright, vertical, the grip at the bottom", 512, 1024, 0.5, 0.7),
    "head": ("{name}, headwear seen from the front, empty, nobody wearing it", 768, 512, 0.5, 0.9),
    "face": ("{name}, worn over the eyes or face, seen from the front, empty, nobody wearing it", 768, 512, 0.5, 0.5),
    "body": ("{name}, an empty garment seen from the front, hanging flat, nobody wearing it", 768, 1024, 0.5, 0.35),
    "back": ("{name}, carried on the back, seen from the front, empty", 768, 1024, 0.5, 0.4),
    "float": ("{name}, a small floating object", 512, 512, 0.5, 0.5),
}
SHORT = ("torch", "dagger", "knife", "pistol", "revolver", "dart", "vial", "lamp", "lantern", "grenade", "baton", "sickle", "hatchet")
LONG = ("staff", "stick", "spear", "pole", "halberd", "rifle", "musket", "lance", "glaive", "pike", "scythe")


# ------------------------------------------------------------------ blueprints

BAD_REF = re.compile(r"&#(x[0-9a-fA-F]+|[0-9]+);")


def _ref_value(s: str) -> int:
    try:
        return int(s[1:], 16) if s[0] in "xX" else int(s)
    except ValueError:
        return 0x110000


class Blueprints:
    """ObjectBlueprints from the base game and enabled mods (later definitions merge over earlier)."""

    def __init__(self, game: Path, userdata: Path, workshop: Path):
        self.objs: Dict[str, Dict] = {}
        base = game / "CoQ_Data" / "StreamingAssets" / "Base" / "ObjectBlueprints"
        for p in sorted(base.glob("*.xml")):
            self._load(p)
        for _mid, _title, folder in enabled_mods(userdata, workshop):
            for p in folder.rglob("*.xml"):
                if p.stat().st_size < 50_000_000:
                    self._load(p)

    def _load(self, path: Path) -> None:
        try:
            raw = path.read_bytes().decode("utf-8-sig", "replace")
            if "<objects" not in raw[:4000].lower():
                return
            # The game's XML reader accepts control-character references (&#1;) that ElementTree rejects.
            raw = BAD_REF.sub(lambda m: "" if _ref_value(m.group(1)) < 32 and _ref_value(m.group(1)) not in (9, 10, 13) else m.group(0), raw)
            root = ET.fromstring(raw[raw.find("<"):])
        except (ET.ParseError, OSError, ValueError):
            return
        for o in root.iter():
            if o.tag.lower() != "object" or not o.get("Name"):
                continue
            name = o.get("Name")
            ent = self.objs.get(name) if (o.get("Load") or "").lower() == "merge" else None
            if ent is None:
                ent = {"inherits": o.get("Inherits"), "parts": {}, "tags": {}}
                self.objs[name] = ent
            elif o.get("Inherits"):
                ent["inherits"] = o.get("Inherits")
            for c in o:
                if c.tag.lower() == "part" and c.get("Name"):
                    ent["parts"].setdefault(c.get("Name"), {}).update(c.attrib)
                elif c.tag.lower() == "tag" and c.get("Name"):
                    ent["tags"][c.get("Name")] = c.get("Value", "")

    def resolve(self, name: str) -> Dict:
        chain, seen = [], set()
        n: Optional[str] = name
        while n and n in self.objs and n not in seen:
            seen.add(n)
            chain.append(self.objs[n])
            n = self.objs[n]["inherits"]
        parts: Dict[str, Dict] = {}
        tags: Dict[str, str] = {}
        for ent in reversed(chain):
            for k, v in ent["parts"].items():
                parts.setdefault(k, {}).update(v)
            tags.update(ent["tags"])
        return {"found": bool(chain), "parts": parts, "tags": tags, "lineage": [name] + [c["inherits"] for c in chain if c["inherits"]]}


def strip_markup(s: str) -> str:
    s = re.sub(r"\{\{[^|}]*\|", "", s or "")
    s = s.replace("}}", "")
    s = re.sub(r"&[a-zA-Z]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def describe(bp: Blueprints, blueprint: str) -> Tuple[str, str]:
    info = bp.resolve(blueprint)
    render = info["parts"].get("Render", {})
    name = strip_markup(render.get("DisplayName") or blueprint)
    desc = strip_markup(info["parts"].get("Description", {}).get("Short", ""))
    if "=" in desc or len(desc) > 220:
        desc = desc.split(".")[0][:200]
    return name, desc


# ------------------------------------------------------------------ items to make

def items_from_character(path: Path) -> List[Tuple[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    root = ET.fromstring("<r>" + text + "</r>")
    body = root.find("GameObjects/GameObject/Body")
    out: List[Tuple[str, str]] = []

    def walk(node: ET.Element) -> None:
        for part in node.findall("Part"):
            t = part.get("Type") or ""
            # The export names variants (Tentacle, Pseudopod...); the game counts them as their base slot.
            slot = SLOTS.get(t) or ("hand" if any(w in t.lower() for w in ("tentacle", "pseudopod", "claw", "hand")) else None)
            for it in part.findall("Item"):
                if slot and it.get("Blueprint"):
                    out.append((it.get("Blueprint"), slot))
            walk(part)

    if body is not None:
        for it in body.findall("Item"):
            if it.get("Blueprint"):
                out.append((it.get("Blueprint"), "body"))
        walk(body)
    seen, uniq = set(), []
    for b, s in out:
        if b not in seen:
            seen.add(b)
            uniq.append((b, s))
    return uniq


def items_from_arg(arg: str) -> List[Tuple[str, str]]:
    out = []
    for piece in arg.split(","):
        piece = piece.strip()
        if not piece:
            continue
        b, _, s = piece.partition(":")
        out.append((b.strip(), (s.strip() or "hand").lower()))
    return out


# ------------------------------------------------------------------ art

def safe_file(blueprint: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", blueprint).strip("_") + ".png"


def key_background(im: Image.Image) -> Image.Image:
    """Flood the plain background in from the borders; keep the object, trim, soft edge."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    d = np.abs(a - bg).sum(2)
    near_bg = d < 42
    lab, _ = ndimage.label(near_bg)
    edge_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    back = np.isin(lab, list(edge_labels))
    obj = ~back
    lab2, n = ndimage.label(obj)
    if n:
        sizes = ndimage.sum(obj, lab2, range(1, n + 1))
        obj = np.isin(lab2, 1 + np.flatnonzero(sizes >= max(150, sizes.max() * 0.03)))
    obj = ndimage.binary_fill_holes(obj)
    alpha = obj.astype(np.float32)
    edge = obj & ~ndimage.binary_erosion(obj)
    alpha[edge] = np.clip((d[edge] - 20) / 40, 0.35, 1.0)
    ys, xs = np.nonzero(obj)
    if len(xs) == 0:
        raise RuntimeError("nothing left after keying the background")
    x0, y0, x1, y1 = max(0, xs.min() - 4), max(0, ys.min() - 4), min(w, xs.max() + 5), min(h, ys.max() + 5)
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)[y0:y1, x0:x1]
    rgba[rgba[..., 3] == 0] = 0
    return Image.fromarray(rgba, "RGBA")


def grip_of(art: Image.Image, slot: str) -> Tuple[float, float]:
    gx, gy = KINDS[slot][3], KINDS[slot][4]
    if slot not in ("hand", "missile"):
        return gx, gy
    a = np.asarray(art)[..., 3] > 128
    row = min(a.shape[0] - 1, int(a.shape[0] * gy))
    xs = np.nonzero(a[row])[0]
    if len(xs):
        gx = float((xs.min() + xs.max()) / 2 / a.shape[1])
    return round(gx, 3), gy


def scale_of(name: str, slot: str) -> float:
    n = name.lower()
    if slot in ("hand", "missile"):
        if any(w in n for w in SHORT):
            return 0.55
        if any(w in n for w in LONG):
            return 1.0
        return 0.8
    return 1.0


def sd_ready(timeout: float = 600) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(SD_URL + "/ping", timeout=5) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
            if j.get("loaded") and not j.get("loading"):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(4)
    return False


# ------------------------------------------------------------------ items.xml

def read_index(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.is_file():
        return {}
    root = ET.parse(path).getroot()
    return {e.get("Blueprint"): dict(e.attrib) for e in root.iter("item") if e.get("Blueprint")}


def write_index(path: Path, items: Dict[str, Dict[str, str]]) -> None:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<portraititems>"]
    for b in sorted(items):
        e = items[b]
        attrs = " ".join(f"{k}={quoteattr(str(e[k]))}" for k in ("Blueprint", "File", "Slot", "GripX", "GripY", "Scale", "Name") if k in e)
        lines.append(f"  <item {attrs} />")
    lines.append("</portraititems>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


REGION = {"body": "torso", "head": "head", "face": "face", "back": "back", "hand": "hand", "missile": "back",
          "float": "head", "feet": "feet"}


def flatten_portrait(pdir: Path) -> tuple:
    """(RGBA canvas of every non-item layer whose Follow has no '!' term, xml root)."""
    root = ET.parse(pdir / "portrait.xml").getroot()
    w, h = int(root.get("Width")), int(root.get("Height"))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for e in root:
        if e.tag != "layer" or "!" in (e.get("Follow") or ""):
            continue
        im = Image.open(pdir / e.get("File")).convert("RGBA")
        canvas.alpha_composite(im, (int(e.get("X", 0)), int(e.get("Y", 0))))
    return canvas, root


# Where head and face gear goes: Kontext otherwise puts helmets on the shoulder tentacle or goggles on the chest.
PLACE = {
    "head": ", worn on top of the humanoid's own head (the big head at the top centre, not the tentacle);"
            " it fits the skull and the face below it stays visible",
    "face": ", worn on the face of the humanoid's own head (the big head at the top centre, not the tentacle or the chest)",
}


def fitted(pdir: Path, todo: List[Tuple[str, str]], bp: "Blueprints", subject: str, seed: int, force: bool,
           mode: str = "edit", hints: Optional[Dict[str, str]] = None, use_ref: bool = True,
           dry_run: bool = False, protect: Optional[Path] = None, region_grow: float = 0.0) -> int:
    from refart_client import run
    items_dir = pdir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    work = pdir.parent / "_fitted_work"
    work.mkdir(parents=True, exist_ok=True)
    canvas, root = flatten_portrait(pdir)
    base_png = work / "flat_base.png"
    canvas.save(base_png)
    made = 0
    for blueprint, slot in todo:
        file = "items/" + safe_file(blueprint)
        exists = any(e.tag == "item" and e.get("Blueprint") == blueprint for e in root)
        if exists and (pdir / file).is_file() and not force:
            print(f"keep {blueprint}")
            continue
        name, desc = describe(bp, blueprint)
        if hints and blueprint in hints:  # the game's flavour text can mislead (e.g. "sheep's wool" -> fur)
            desc = hints[blueprint]
        noun = name.split()[-1]
        # The item's in-game look (Bright Qud icon + paperdoll, or the mod's own tile) beside the character:
        # Kontext copies its colours and shape instead of guessing them from the name.
        ref = None
        if mode == "edit" and use_ref:
            try:
                import cyf_item_ref
                ref = cyf_item_ref.reference(bp, blueprint, slot, work / f"ref_{safe_file(blueprint)}")
                cols = cyf_item_ref.describe_colors(bp, blueprint) if ref else ""
            except Exception as e:  # a reference is a help, never a blocker
                print(f"no reference for {blueprint}: {e}")
                ref, cols = None, ""
        if mode == "edit":  # Kontext takes an instruction and keeps the rest of the picture
            instr = (f"Make the {subject} on the left wear a {name}" + (f" ({desc})" if desc else "")
                     + PLACE.get(slot, "")
                     + (f". The small pixel-art picture on the right shows this {noun} in game (its icon and how it is worn):"
                        f" copy only its colours and general shape ({cols}); paint it as smooth detailed illustration"
                        f" like the character, never as pixel art or a flat icon" if ref else "")
                     + ". Keep the character's pose, heads, own face (no beard or added hair), colours, art style and the background exactly the same.")
        else:
            instr = (f"{subject} wearing a {name}" + (f", {desc}" if desc else "")
                     + ", detailed comic illustration, bold dark outlines, cel shading, no beard")
        if dry_run:  # prompts only: no GPU job, nothing written
            print(f"[dry-run] {blueprint} [{slot}]: {instr}" + (f"  (ref {ref})" if ref else ""))
            continue
        cut = work / f"cut_{safe_file(blueprint)}"
        t = time.time()
        try:
            # Head and face gear: keep the cut around the heads, so a Kontext edit that also repainted
            # the torso or erased the back sack never leaks into the layer.
            res = run("overlay", base=base_png, instruction=instr, phrase=noun, out=cut, mode=mode,
                      region=REGION.get(slot, "torso"), seed=seed, work=work,
                      clip_region=mode == "edit" and slot in ("head", "face"), ref=ref,
                      protect=protect if mode == "inpaint" else None,
                      region_grow=region_grow if (mode == "inpaint" and protect) else None)
        except RuntimeError as e:  # one bad edit must not lose the rest of a long batch
            print(f"failed {blueprint}: {str(e).strip().splitlines()[-1][:300]}")
            continue
        lay = Image.open(cut).convert("RGBA")
        a = np.asarray(lay)[..., 3]
        ys, xs = np.nonzero(a > 2)
        if len(xs) == 0:
            print(f"no {noun} found for {blueprint}")
            continue
        bx = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        lay.crop(bx).save(pdir / file, optimize=True)
        for e in [e for e in root if e.tag == "item" and e.get("Blueprint") == blueprint]:
            root.remove(e)
        el = ET.Element("item", {"Blueprint": blueprint, "File": file, "X": str(bx[0]), "Y": str(bx[1]), "Slot": slot})
        kids = list(root)
        at = next((i + 1 for i, e in enumerate(kids) if e.get("File") == "base.png"), len(kids))
        while at < len(kids) and "!" in (kids[at].get("Follow") or ""):  # stumps stay right on the base
            at += 1
        if slot == "float":  # floating things hover in front of everything
            at = len(kids)
        root.insert(at, el)
        made += 1
        _write_portrait_xml(pdir, root)  # after every item, so a crash keeps what is done
        print(f"fitted {blueprint} [{slot}] {bx[2] - bx[0]}x{bx[3] - bx[1]} in {time.time() - t:.0f}s ({res.get('pixels')} px)")
    return made


def _write_portrait_xml(pdir: Path, root: ET.Element) -> None:
    ET.indent(root, "  ")
    text = '<?xml version="1.0" encoding="utf-8"?>' + chr(10) + ET.tostring(root, encoding="unicode") + chr(10)
    (pdir / "portrait.xml").write_text(text, encoding="utf-8", newline="")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--character", type=Path)
    ap.add_argument("--items", default="")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the prompts, generate nothing")
    ap.add_argument("--protect", type=Path, help="fitted --mode inpaint: mask PNG of pixels never repainted (the face"
                    " under a helmet), canvas-sized")
    ap.add_argument("--region-grow", type=float, default=0.35, help="with --protect: grow the head region by this x its height")
    ap.add_argument("--fitted", type=Path, help="portrait folder (portrait.xml): paint items onto the character")
    ap.add_argument("--mode", choices=["edit", "inpaint"], default="edit",
                    help="fitted mode: edit = FLUX Kontext instruction edit (default), inpaint = SDXL region repaint")
    ap.add_argument("--hint", action="append", default=[], metavar="BLUEPRINT=TEXT",
                    help="fitted mode: describe an item yourself instead of its in-game description (repeatable)")
    ap.add_argument("--subject", default="the character", help="fitted mode: who wears the items")
    ap.add_argument("--skip", default="", help="blueprints to leave out, comma-separated")
    ap.add_argument("--no-ref", action="store_true",
                    help="fitted mode: do not show Kontext the item's in-game icon (cyf_item_ref.py)")
    ap.add_argument("--userdata", type=Path, default=DEFAULT_USERDATA)
    ap.add_argument("--workshop", type=Path, default=DEFAULT_WORKSHOP)
    ap.add_argument("--game", type=Path, default=DEFAULT_GAME)
    a = ap.parse_args()

    todo = items_from_character(a.character) if a.character else []
    todo += items_from_arg(a.items)
    skip = {s.strip() for s in a.skip.split(",") if s.strip()}
    todo = [(b, s) for b, s in todo if b not in skip and s in KINDS]
    if not todo:
        print("nothing to make (feet items are not drawn on portraits)")
        return 0

    if a.fitted:
        bp = Blueprints(a.game, a.userdata, a.workshop)
        keep = []
        named = {b for b, _ in items_from_arg(a.items)}
        for b, s_ in todo:
            info = bp.resolve(b)
            # Natural gear (mutation limbs, stumps) is part of the base art, except what --items names on
            # purpose, e.g. Mycologist infections, which grow on the body after the base was drawn.
            if b not in named and ("NaturalGear" in info["tags"] or "NaturalEquipment" in info["parts"]):
                print(f"skip {b}: natural gear")
                continue
            keep.append((b, s_))
        hints = dict(h.split("=", 1) for h in a.hint)
        n = fitted(a.fitted, keep, bp, a.subject, a.seed, a.force, a.mode, hints, use_ref=not a.no_ref, dry_run=a.dry_run,
                    protect=a.protect, region_grow=a.region_grow)
        print(f"{n} fitted -> {a.fitted}" if not a.dry_run else "dry run: nothing generated")
        return 0
    dst = a.out_dir / "Textures" / "Portraits" / "_items"
    dst.mkdir(parents=True, exist_ok=True)
    index_path = dst / "items.xml"
    index = read_index(index_path)
    print("reading blueprints (base + enabled mods)...", flush=True)
    bp = Blueprints(a.game, a.userdata, a.workshop)

    made = 0
    for blueprint, slot in todo:
        file = safe_file(blueprint)
        if not a.force and blueprint in index and (dst / index[blueprint].get("File", file)).is_file():
            print(f"keep {blueprint} ({index[blueprint].get('File')})")
            continue
        info = bp.resolve(blueprint)
        if "NaturalGear" in info["tags"] or "NaturalEquipment" in info["parts"]:
            print(f"skip {blueprint}: natural (mutation) gear, the portrait's own layers show it")
            continue
        name, desc = describe(bp, blueprint)
        pattern, w, h, _gx, _gy = KINDS[slot]
        prompt = pattern.format(name=name) + (f". {desc}" if desc else "") + ". " + STYLE
        if made == 0 and not a.dry_run and not sd_ready():
            print("SD server not ready on :1338 (start Start-BroodmotherSDServer.bat)")
            return 1
        if a.dry_run:
            print(f"[dry] {blueprint} [{slot}] {w}x{h}: {prompt}")
            continue
        raw_dir = a.out_dir / "_portrait_items_raw"  # SD output before keying, kept out of the mod
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw = raw_dir / file
        t = time.time()
        generate_image(prompt, raw, api_url=SD_URL + "/v1/images/generations", negative_prompt=NEGATIVE,
                       width=w, height=h, steps=a.steps, guidance_scale=6.5, seed=a.seed)
        art = key_background(Image.open(raw))
        art.save(dst / file, optimize=True)
        gx, gy = grip_of(art, slot)
        index[blueprint] = {"Blueprint": blueprint, "File": file, "Slot": slot, "GripX": gx, "GripY": gy,
                            "Scale": scale_of(name, slot), "Name": name}
        write_index(index_path, index)
        made += 1
        print(f"made {blueprint} [{slot}] {art.size[0]}x{art.size[1]} in {time.time() - t:.0f}s: {name}", flush=True)
    write_index(index_path, index)
    print(f"{made} made -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
