#!/usr/bin/env python3
"""Transcendence image / facing tester, built from the engine's own rules.

Every check mirrors code in TranscendenceDev (Mammoth/TSE). The citation is in
the check's docstring so a rule can be re-verified when the engine changes.

  python tx_image_tester.py <folder-or-xml> [...]           # report
  python tx_image_tester.py <folder> --json report.json     # machine-readable
  python tx_image_tester.py <folder> --contact out_dir      # frames 0/30/60/90 per sheet
  python tx_image_tester.py <folder> --inventory            # ShipClass facing counts

Exit code: 0 = no errors, 1 = at least one error (warnings never fail).

Engine rules mirrored
---------------------
R1  rotationColumns > 0  ->  framesPerColumn = ceil(rotationCount / rotationColumns)
    (CObjectImageArray.cpp InitFromXML, ~L1330)
R2  Rotation r of a multi-column sheet sits at
        x = imageX + (r // framesPerColumn) * w,   y = imageY + (r % framesPerColumn) * h
    i.e. COLUMN-major (CObjectImageArray.cpp ComputeSourceXY, ~L486)
    Animated + rotated: x adds frame * colsPerFrame (~L464).
R3  Required sheet size (CObjectImageArray.cpp ~L378-415).
R4  Frame i faces 90 - i*360/n degrees (math CCW, 0 = east): frame 0 is nose-up
    and successive frames turn CLOCKWISE on screen
    (CIntegralRotationDesc.cpp InitFacingsData, ~L101).
R5  JPG/BMP use a separate bitmask; PNG carries alpha (CResourceDb.cpp LoadImageFile ~L620).
    Vanilla masks are 8-bit (P or L); 24-bit masks load but triple the size.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageChops
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: pip install pillow")

Image.MAX_IMAGE_PIXELS = None

ENTITY_RE = re.compile(r'<!ENTITY\s+(\w+)\s+"([^"]*)"\s*>')
TAG_RE = re.compile(r"<(/?)([A-Za-z][\w]*)\b([^>]*?)(/?)>", re.S)
ATTR_RE = re.compile(r'([\w:]+)\s*=\s*"([^"]*)"')
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
OWNER_TAGS = {"ShipClass", "ItemType", "OverlayType", "EffectType", "StationType", "MissileDesc", "Weapon"}


# --------------------------------------------------------------------------- model

@dataclass
class Resource:
    unid: str
    bitmap: Optional[Path]
    bitmask: Optional[Path]
    xml: str
    line: int


@dataclass
class Usage:
    image_id: str
    attrs: Dict[str, str]
    owner_tag: str
    owner: str
    xml: str
    line: int


@dataclass
class Finding:
    level: str  # error | warn | info
    code: str
    where: str
    msg: str


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)
    inventory: List[dict] = field(default_factory=list)
    sheets_checked: int = 0

    def add(self, level, code, where, msg):
        self.findings.append(Finding(level, code, where, msg))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "error"]


# --------------------------------------------------------------------------- parsing

def _xml_files(paths: List[Path]) -> List[Path]:
    out = []
    for p in paths:
        if p.is_dir():
            out += [f for f in p.rglob("*.xml") if not f.name.endswith((".bak", ".backup"))]
        elif p.suffix.lower() == ".xml":
            out.append(p)
    return sorted(set(out))


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def parse(files: List[Path]):
    entities: Dict[str, str] = {}
    texts = {}
    for f in files:
        t = f.read_text(encoding="utf-8", errors="replace")
        texts[f] = t
        for name, val in ENTITY_RE.findall(t):
            entities.setdefault(name, val)

    def resolve(v: str) -> str:
        for _ in range(4):
            m = re.fullmatch(r"&(\w+);", v.strip())
            if not m or m.group(1) not in entities:
                break
            v = entities[m.group(1)]
        return v.strip().lower()

    resources: Dict[str, Resource] = {}
    usages: List[Usage] = []
    ships: List[dict] = []

    for f, raw in texts.items():
        # Blank out comments but keep offsets so line numbers stay right.
        t = COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), raw)
        start = t.find("]>")
        body_from = start if start != -1 else 0
        owners: List[Tuple[str, str]] = []
        for m in TAG_RE.finditer(t, body_from):
            closing, tag, attr_txt, selfclose = m.groups()
            if closing:
                if owners and owners[-1][0] == tag:
                    owners.pop()
                continue
            attrs = dict(ATTR_RE.findall(attr_txt))
            if tag in OWNER_TAGS and not selfclose:
                label = attrs.get("UNID", "") or attrs.get("name", "")
                nm = attrs.get("name") or attrs.get("class") or ""
                owners.append((tag, f"{label} {nm}".strip()))
            if tag != "Image":
                continue
            line = _line_of(t, m.start())
            if "UNID" in attrs and ("bitmap" in attrs or "bitmask" in attrs):
                unid = resolve(attrs["UNID"])
                bm = attrs.get("bitmap")
                mk = attrs.get("bitmask")
                resources[unid] = Resource(
                    unid,
                    (f.parent / bm.replace("\\", "/")).resolve() if bm else None,
                    (f.parent / mk.replace("\\", "/")).resolve() if mk else None,
                    str(f), line,
                )
            elif "imageID" in attrs:
                otag, oname = owners[-1] if owners else ("", "")
                u = Usage(resolve(attrs["imageID"]), attrs, otag, oname, str(f), line)
                usages.append(u)
                if otag == "ShipClass":
                    ships.append({
                        "owner": oname,
                        "rotationCount": int(attrs.get("rotationCount", "20") or 20),
                        "xml": f"{f.name}:{line}",
                    })
    return resources, usages, ships


# --------------------------------------------------------------------------- engine maths

def _int(a: Dict[str, str], k: str, d: int = 0) -> int:
    try:
        return int(a.get(k, d))
    except ValueError:
        return d


def geometry(attrs: Dict[str, str]):
    """R1/R3: frame rect, framesPerColumn and the required sheet size."""
    x, y = _int(attrs, "imageX"), _int(attrs, "imageY")
    w, h = _int(attrs, "imageWidth"), _int(attrs, "imageHeight")
    n = max(1, _int(attrs, "rotationCount", 1))
    rc = _int(attrs, "rotationColumns")
    fpc = math.ceil(n / rc) if rc > 0 else n
    frames = max(1, _int(attrs, "imageFrameCount", 1))
    cols_per_frame = math.ceil(n / fpc)
    need_w = x + frames * cols_per_frame * w
    need_h = y + fpc * h
    return x, y, w, h, n, fpc, need_w, need_h


def engine_xy(r: int, x0, y0, w, h, fpc) -> Tuple[int, int]:
    """R2: column-major placement of rotation r."""
    return x0 + (r // fpc) * w, y0 + (r % fpc) * h


def rowmajor_xy(r: int, x0, y0, w, h, cols) -> Tuple[int, int]:
    return x0 + (r % cols) * w, y0 + (r // cols) * h


# --------------------------------------------------------------------------- image checks

_cache: Dict[Path, Image.Image] = {}


def _open(p: Path) -> Image.Image:
    if p not in _cache:
        _cache[p] = Image.open(p)
        _cache[p].load()
    return _cache[p]


def _silhouette(sheet: Image.Image, mask: Optional[Image.Image], box) -> Image.Image:
    src = mask.crop(box).convert("L") if mask is not None else sheet.crop(box).convert("L")
    thr = 40 if mask is not None else 18
    return src.point(lambda v: 255 if v > thr else 0)


def _iou(a: Image.Image, b: Image.Image) -> float:
    inter = ImageChops.multiply(a, b).histogram()[255]
    union = ImageChops.lighter(a, b).histogram()[255]
    return inter / union if union else 1.0


def rotation_scores(sheet, mask, x0, y0, w, h, n, fpc, cols, place):
    """R4: frame k should be frame 0 turned CLOCKWISE by k*360/n degrees.

    Returns (mean IoU clockwise, mean IoU counter-clockwise) over several k.
    PIL rotate(+a) turns counter-clockwise on screen, so clockwise is rotate(-a).
    """
    step = 360.0 / n
    ks = [k for k in (n // 24, n // 12, n // 8, n // 4) if k > 0]
    cw, ccw = [], []
    for base in (0, n // 3):
        bx, by = place(base)
        f0 = _silhouette(sheet, mask, (bx, by, bx + w, by + h))
        for k in ks:
            kx, ky = place((base + k) % n)
            fk = _silhouette(sheet, mask, (kx, ky, kx + w, ky + h))
            a = step * k
            cw.append(_iou(f0.rotate(-a, resample=Image.NEAREST), fk))
            ccw.append(_iou(f0.rotate(a, resample=Image.NEAREST), fk))
    return (sum(cw) / len(cw), sum(ccw) / len(ccw)) if cw else (1.0, 1.0)


def principal_axis_deg(sil: Image.Image) -> Optional[Tuple[float, float]]:
    """Orientation of the silhouette's long axis (0 = vertical) and elongation."""
    w, h = sil.size
    px = sil.load()
    pts = [(x, y) for y in range(0, h, 2) for x in range(0, w, 2) if px[x, y]]
    if len(pts) < 20:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts) / len(pts)
    syy = sum((p[1] - my) ** 2 for p in pts) / len(pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts) / len(pts)
    ang = 0.5 * math.degrees(math.atan2(2 * sxy, sxx - syy))  # 0 = horizontal
    tr, det = sxx + syy, sxx * syy - sxy * sxy
    l1 = tr / 2 + math.sqrt(max(0.0, tr * tr / 4 - det))
    l2 = tr / 2 - math.sqrt(max(0.0, tr * tr / 4 - det))
    elong = math.sqrt(l1 / l2) if l2 > 1e-6 else 99.0
    from_vertical = abs(((ang - 90) + 90) % 180 - 90)
    return from_vertical, elong


def check_usage(u: Usage, res: Resource, rep: Report, contact_dir: Optional[Path], seen: set):
    where = f"{Path(u.xml).name}:{u.line} {u.owner_tag} {u.owner}".strip()
    a = u.attrs
    x0, y0, w, h, n, fpc, need_w, need_h = geometry(a)
    if not res.bitmap or not res.bitmap.exists():
        rep.add("error", "E-FILE", where, f"bitmap missing: {res.bitmap}")
        return
    if res.bitmask and not res.bitmask.exists():
        rep.add("error", "E-FILE", where, f"bitmask missing: {res.bitmask}")
        return
    sheet = _open(res.bitmap)
    mask = _open(res.bitmask) if res.bitmask else None
    sw, sh = sheet.size
    if w == 0 or h == 0:
        w, h = sw, sh  # engine: default size = whole image
    if sw < need_w or sh < need_h:
        rep.add("error", "E-SIZE", where,
                f"{res.bitmap.name} is {sw}x{sh}, engine reads up to {need_w}x{need_h} "
                f"(frame {w}x{h}, {n} rotations, {fpc} per column)")
        return
    key = (str(res.bitmap), x0, y0, w, h, n, fpc)
    first_time = key not in seen
    seen.add(key)

    if mask is not None and first_time:
        if mask.size != sheet.size:
            rep.add("error", "E-MASK", where, f"mask {mask.size} != bitmap {sheet.size}")
            return
        if mask.mode not in ("L", "P", "1"):
            mb = res.bitmask.stat().st_size / 1e6
            rep.add("warn", "W-MASK8", where,
                    f"{res.bitmask.name} is {mask.mode} ({mb:.1f} MB); vanilla masks are 8-bit")
    if not first_time:
        return
    rep.sheets_checked += 1

    if n > 1:
        cols = math.ceil(n / fpc)
        eng = rotation_scores(sheet, mask, x0, y0, w, h, n, fpc, cols,
                              lambda r: engine_xy(r, x0, y0, w, h, fpc))
        best = max(eng)
        if cols > 1:
            row = rotation_scores(sheet, mask, x0, y0, w, h, n, fpc, cols,
                                  lambda r: rowmajor_xy(r, x0, y0, w, h, cols))
            if max(row) > best + 0.05:
                rep.add("error", "E-LAYOUT", where,
                        f"{res.bitmap.name}: frames are laid out ROW-major (fit {max(row):.2f}) "
                        f"but the engine reads COLUMN-major (fit {best:.2f}); facings will jump")
                return
        cw, ccw = eng
        if ccw > cw + 0.05:
            rep.add("error", "E-SPIN", where,
                    f"{res.bitmap.name}: frames turn counter-clockwise (fit {ccw:.2f} vs {cw:.2f}); "
                    "engine expects clockwise (R4)")
        elif best < 0.55:
            rep.add("warn", "W-SPIN", where,
                    f"{res.bitmap.name}: weak rotation consistency (cw {cw:.2f}, ccw {ccw:.2f})")

        # Heading of frame 0 (nose-up expected). Only meaningful for long hulls.
        sil0 = _silhouette(sheet, mask, (x0, y0, x0 + w, y0 + h))
        pa = principal_axis_deg(sil0)
        if pa and pa[1] > 1.6 and pa[0] > 25:
            rep.add("warn", "W-HEADING", where,
                    f"{res.bitmap.name}: frame 0 long axis is {pa[0]:.0f} deg off vertical; "
                    "frame 0 must face up (R4)")

    # Clipping: content touching the frame border on sampled frames.
    clipped = 0
    samples = range(0, n, max(1, n // 12))
    for r in samples:
        fx, fy = engine_xy(r, x0, y0, w, h, fpc) if n > 1 else (x0, y0)
        sil = _silhouette(sheet, mask, (fx, fy, fx + w, fy + h))
        edge = sum(sil.crop(b).histogram()[255] for b in
                   ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h)))
        if edge > max(2, (w + h) // 40):
            clipped += 1
    if clipped:
        rep.add("warn", "W-CLIP", where, f"{res.bitmap.name}: hull touches frame edge in {clipped}/{len(samples)} sampled facings")

    if contact_dir is not None and n > 1:
        contact_dir.mkdir(parents=True, exist_ok=True)
        picks = [0, n // 4, n // 2, 3 * n // 4]
        cs = Image.new("RGB", (w * 4, h), "black")
        for i, r in enumerate(picks):
            fx, fy = engine_xy(r, x0, y0, w, h, fpc)
            cs.paste(sheet.crop((fx, fy, fx + w, fy + h)).convert("RGB"), (i * w, 0))
        cs.save(contact_dir / f"{res.bitmap.stem}_{x0}_{y0}.png")


def run(paths: List[Path], contact_dir: Optional[Path] = None) -> Report:
    rep = Report()
    files = _xml_files(paths)
    resources, usages, ships = parse(files)
    seen: set = set()
    for u in usages:
        res = resources.get(u.image_id)
        if res is None:
            continue  # defined in another extension / vanilla TDB
        try:
            check_usage(u, res, rep, contact_dir, seen)
        except Exception as e:  # keep going; report the crash as an error
            rep.add("error", "E-CRASH", f"{Path(u.xml).name}:{u.line}", repr(e))
    rep.inventory = ships
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--contact", type=Path, help="write frames 0/90/180/270-degree contact strips here")
    ap.add_argument("--inventory", action="store_true", help="list ShipClass rotation counts")
    args = ap.parse_args(argv)

    rep = run(args.paths, args.contact)
    for f in rep.findings:
        print(f"[{f.level.upper():5}] {f.code:10} {f.where}\n         {f.msg}")
    if args.inventory:
        below = [s for s in rep.inventory if s["rotationCount"] < 120]
        print(f"\nShipClass images: {len(rep.inventory)}, below 120 facings: {len(below)}")
        for s in below:
            print(f"  {s['rotationCount']:4}  {s['owner']:<60} {s['xml']}")
    ne = len(rep.errors)
    nw = sum(1 for f in rep.findings if f.level == "warn")
    print(f"\nsheets checked: {rep.sheets_checked}  errors: {ne}  warnings: {nw}")
    if args.json:
        args.json.write_text(json.dumps({
            "findings": [asdict(f) for f in rep.findings],
            "inventory": rep.inventory,
            "sheets_checked": rep.sheets_checked,
        }, indent=2), encoding="utf-8")
    return 1 if ne else 0


if __name__ == "__main__":
    sys.exit(main())
