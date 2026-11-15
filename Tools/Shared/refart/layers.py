"""refart layers: split a character picture into layers by naming its parts, and cut item overlays.

split(spec)  Parts are found by phrase (Grounding DINO boxes -> SAM 2.1 masks), assigned to layer files,
             lifted off the working image in spec order, and what each one covered is filled:
               "transparent"            nothing behind it (a sack behind the body, a head above the shoulders)
               "inpaint"                SDXL repaints it in the picture's own style (IP-Adapter on the source)
               "inpaint" + "within"     repaint only inside the hull of those other parts (a horn's base inside
                                        its head's dome); the rest of the part goes transparent
               "dark"                   flat dark colour (eye glow -> empty sockets)
             "only": "bright" keeps just the lit pixels of each match (glows); "fill_negative" (default: the
             phrase) stops inpainting from drawing the removed part back.
             "stump": true draws an outline along the cut, as its own layer shown when the part is not.
             Writes base.png + one PNG per layer (cropped, X/Y on the canvas), portrait.xml (Arendeth_CYFTiles
             layered-portrait format), layers.json, and previews with each optional part removed.

Spec (JSON, paths relative to it):
  {"fighter": "rhomustos", "source": "art.png", "subject": "three-headed green slime mutant",
   "crop": "auto" | [x0,y0,x1,y1], "margin": 16,
   "parts": [
     {"phrase": "white horn", "count": 3, "assign": "x",
      "files": ["horns2.png", "horns.png", "horns3.png"], "follow": ["horns2,head2", "horns", "horns3,head3"],
      "z": "front", "fill": "inpaint", "within": "head", "fill_prompt": "bald green slimy scalp"},
     {"phrase": "glowing eye", "count": 6, "assign": "group:head",
      "files": ["glow2.png", "glow1.png", "glow3.png"], "follow": [...], "z": "front", "fill": "dark"},
     {"phrase": "head", "count": 3, "assign": "x", "files": ["head2.png", null, "head3.png"], ...,
      "z": "back", "fill": "transparent", "stump": true},
     {"phrase": "fleshy sack", "count": 1, "files": ["brood.png"], "follow": ["brood"], "z": "back", "fill": "transparent"}]}
  "assign": "x" sorts the found parts left to right onto "files" (null = found but left in the base);
  "group:<phrase>" merges the parts inside each match of another phrase (ordered by x) into one file each.

overlay(base, instruction, phrase)  An item layer that fits the body: the base is edited (Kontext, or SDXL
             inpaint over the region phrase) to wear/hold the item, the item is found by phrase in the result,
             and those pixels become one RGBA layer on the base's canvas.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from xml.sax.saxutils import quoteattr

import numpy as np
from PIL import Image
from scipy import ndimage

import engine

OUTLINE = np.array([14, 18, 16], np.float32)
SOCKET = np.array([30, 34, 18], np.float32)


def _near(m: np.ndarray, r: int) -> np.ndarray:
    return ndimage.binary_dilation(m, iterations=r) if m.any() and r > 0 else m


def _hull(m: np.ndarray) -> np.ndarray:
    """Filled convex hull of a mask (row/column scan of the hull polygon via PIL)."""
    if not m.any():
        return m
    from scipy.spatial import ConvexHull
    from PIL import ImageDraw
    ys, xs = np.nonzero(m)
    pts = np.stack([xs, ys], 1)
    if len(pts) < 3:
        return m
    try:
        h = ConvexHull(pts)
    except Exception:  # noqa: BLE001
        return m
    im = Image.new("L", (m.shape[1], m.shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(pts[i]) for i in h.vertices], fill=255)
    return np.asarray(im) > 0


def _find(img_path: Path, phrase: str, count: int, alpha: np.ndarray, threshold: float = 0.25) -> List[Dict]:
    """Up to `count` matches, dropping boxes that cover most of the figure (DINO's 'whole picture' hit)."""
    res = engine.segment(img_path, [phrase], threshold, max_per_phrase=max(count * 2, 4))[phrase]
    fig = alpha > 0.5
    fy, fx = np.nonzero(fig)
    fig_area = max(1, (fx.max() - fx.min()) * (fy.max() - fy.min())) if len(fx) else alpha.size
    keep = []
    for d in res:
        x0, y0, x1, y1 = d["box"]
        if (x1 - x0) * (y1 - y0) > 0.45 * fig_area:
            continue
        keep.append(d)
    return keep[:count]


def split(spec_path: Path, out_dir: Path, preview: Optional[Path] = None) -> Dict:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    root = Path(spec_path).parent
    src_path = root / spec["source"]
    src = Image.open(src_path).convert("RGB")
    rgb = np.asarray(src).astype(np.float32)
    alpha = engine.matte(src_path).astype(np.float32)
    alpha[alpha < 0.04] = 0
    work = rgb.copy()
    work_path = out_dir / "_work.png"
    out_dir.mkdir(parents=True, exist_ok=True)

    layers: Dict[str, np.ndarray] = {}
    follow: Dict[str, str] = {}
    order_back: List[str] = []
    order_front: List[str] = []
    found_masks: Dict[str, List[np.ndarray]] = {}
    inpaint_jobs: List[tuple] = []  # (mask, prompt)

    def add_layer(file: str, fol: str, m: np.ndarray, z: str, pixels: np.ndarray, a: np.ndarray) -> None:
        lay = np.zeros(m.shape + (4,), np.float32)
        lay[..., :3] = pixels
        lay[..., 3] = a * m
        if file in layers:
            prev = layers[file]
            take = lay[..., 3] > prev[..., 3]
            prev[take] = lay[take]
        else:
            layers[file] = lay
            (order_back if z == "back" else order_front).append(file)
        follow[file] = fol

    # Every phrase any part refers to ("within", "group:") is found on the untouched picture first,
    # so a part can lean on one that is processed later (horns inside heads, eyes grouped by head).
    Image.fromarray(np.clip(work, 0, 255).astype(np.uint8)).save(work_path)
    counts = {p["phrase"]: int(p.get("count", 1)) for p in spec["parts"]}
    for part in spec["parts"]:
        for ref in [part.get("within"), part.get("assign", "")[6:] if part.get("assign", "").startswith("group:") else None]:
            if ref and ref not in found_masks:
                found_masks[ref] = [d["mask"] & (alpha > 0.05) for d in _find(work_path, ref, counts.get(ref, 8), alpha) if "mask" in d]

    for part in spec["parts"]:
        phrase = part["phrase"]
        files: List[Optional[str]] = part.get("files") or []
        fols: List[Optional[str]] = part.get("follow") or []
        Image.fromarray(np.clip(work, 0, 255).astype(np.uint8)).save(work_path)
        found = _find(work_path, phrase, int(part.get("count", 1)), alpha, part.get("threshold", 0.25))
        masks = [d["mask"] & (alpha > 0.05) for d in found if "mask" in d]
        found_masks.setdefault(phrase, masks)
        assign = part.get("assign", "x")
        groups: List[np.ndarray]
        if assign.startswith("group:"):
            parents = sorted(found_masks.get(assign[6:], []), key=lambda m: np.nonzero(m)[1].mean())
            groups = []
            for pm in parents:
                hull = _hull(pm)
                g = np.zeros_like(alpha, bool)
                for m in masks:
                    if (m & hull).sum() > 0.5 * m.sum():
                        g |= m
                groups.append(g)
        else:
            groups = sorted(masks, key=lambda m: np.nonzero(m)[1].mean() if m.any() else 0)
        z = part.get("z", "front")
        fill = part.get("fill", "transparent")
        for i, m in enumerate(groups):
            file = files[i] if i < len(files) else None
            if file is None or not m.any():
                continue
            if part.get("only") == "bright":
                # glows: only the lit pixels (and a 1 px halo), not SAM's whole socket
                lum = work[..., 0] * 0.299 + work[..., 1] * 0.587 + work[..., 2] * 0.114
                m = _near(m & (lum > float(part.get("bright", 170))), 1) & m
            m = _near(m, int(part.get("grow", 1))) & (alpha > 0.05)
            fol = fols[i] if i < len(fols) and fols[i] else ""
            add_layer(file, fol, m, z, work.copy(), alpha)
            if part.get("stump"):
                edge = _near(m, 3) & ~m & (alpha > 0.5)
                sl = np.zeros(m.shape + (4,), np.float32)
                sl[..., :3] = OUTLINE
                sl[..., 3] = edge
                sfile = file.replace(".png", "_stump.png")
                layers[sfile] = sl
                order_front.insert(0, sfile)
                neg = ",".join("!" + t.split(",")[0] for t in [fol] if t)
                follow[sfile] = neg
            # what the part covered
            if fill == "dark":
                work[m] = SOCKET
            elif fill == "inpaint":
                region = m
                if part.get("within"):
                    within = np.zeros_like(m)
                    for wm in found_masks.get(part["within"], []):
                        within |= wm
                    region = m & _hull(within & ~m)
                    alpha[m & ~region] = 0
                if region.any():
                    inpaint_jobs.append((region, part.get("fill_prompt") or spec.get("subject", ""),
                                         part.get("fill_negative", phrase)))
            else:
                alpha[m] = 0
        if inpaint_jobs:
            _run_inpaint(work, inpaint_jobs, spec, out_dir, src_path)
            inpaint_jobs.clear()

    # base: what is left, minus bits that the cuts left floating (shadow rings, outline crumbs)
    solid = alpha > 0.2
    lab, n = ndimage.label(solid)
    if n > 1:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        crumbs = np.isin(lab, 1 + np.flatnonzero(sizes < max(60, sizes.max() * float(spec.get("crumb", 0.004)))))
        alpha[_near(crumbs, 1) & ~_near(solid & ~crumbs, 1)] = 0
    base = np.zeros(alpha.shape + (4,), np.float32)
    base[..., :3] = work
    base[..., 3] = alpha
    layers["base.png"] = base
    order = order_back + ["base.png"] + order_front

    # crop
    crop = spec.get("crop", "auto")
    if crop == "auto":
        any_a = np.zeros_like(alpha, bool)
        for l in layers.values():
            any_a |= l[..., 3] > 0.02
        ys, xs = np.nonzero(any_a)
        mg = int(spec.get("margin", 16))
        crop = [max(0, xs.min() - mg), max(0, ys.min() - mg), min(alpha.shape[1], xs.max() + mg + 1),
                min(alpha.shape[0], ys.max() + mg + 1)]
    x0, y0, x1, y1 = [int(v) for v in crop]
    fid = spec.get("fighter", "portrait")
    dst = out_dir
    dst.mkdir(parents=True, exist_ok=True)
    xml = ['<?xml version="1.0" encoding="utf-8"?>', f'<portrait Fighter={quoteattr(fid)} Width="{x1 - x0}" Height="{y1 - y0}">']
    meta = []
    for f in order:
        l = layers[f][y0:y1, x0:x1]
        ys, xs = np.nonzero(l[..., 3] > 0.004)
        if len(xs) == 0:
            continue
        bx = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        _img(l[bx[1]:bx[3], bx[0]:bx[2]]).save(dst / f, optimize=True)
        fol = follow.get(f, "")
        xml.append(f'  <layer File={quoteattr(f)} X="{bx[0]}" Y="{bx[1]}"' + (f" Follow={quoteattr(fol)}" if fol else "") + " />")
        meta.append({"file": f, "x": bx[0], "y": bx[1], "follow": fol})
    xml.append("</portrait>")
    (dst / "portrait.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
    (dst / "layers.json").write_text(json.dumps({"crop": [x0, y0, x1, y1], "layers": meta}, indent=1), encoding="utf-8")
    work_path.unlink(missing_ok=True)
    if preview:
        _previews({f: layers[f][y0:y1, x0:x1] for f in order}, order, follow, preview, fid)
    return {"layers": len(meta), "out": str(dst), "crop": [x0, y0, x1, y1]}


def _run_inpaint(work: np.ndarray, jobs: List[tuple], spec: Dict, out_dir: Path, src_path: Path) -> None:
    by_prompt: Dict[tuple, np.ndarray] = {}
    for m, p, neg in jobs:
        by_prompt[(p, neg)] = by_prompt.get((p, neg), np.zeros_like(m)) | m
    for k, ((prompt, negative), m) in enumerate(by_prompt.items()):
        img_p = out_dir / f"_inp_src{k}.png"
        mask_p = out_dir / f"_inp_mask{k}.png"
        res_p = out_dir / f"_inp_res{k}.png"
        Image.fromarray(np.clip(work, 0, 255).astype(np.uint8)).save(img_p)
        Image.fromarray((_near(m, 2) * 255).astype(np.uint8)).save(mask_p)
        full = f"{prompt}, {spec.get('style', 'stylized video game character art, bold dark outline, cel shading')}"
        # The removed part is the negative (a horn must not grow back); the reference keeps the style
        # but weakly, since the reference still shows the part.
        engine.inpaint(img_p, mask_p, full, res_p, refs=[src_path], ref_scale=0.3, grow=4, blur=3,
                       seed=int(spec.get("seed", 0)), negative=negative)
        res = np.asarray(Image.open(res_p).convert("RGB")).astype(np.float32)
        mm = _near(m, 2)
        work[mm] = res[mm]
        for p in (img_p, mask_p, res_p):
            p.unlink(missing_ok=True)


def _img(l: np.ndarray) -> Image.Image:
    a = np.clip(l, 0, 255).copy()
    a[..., 3] = np.clip(l[..., 3], 0, 1) * 255
    a[a[..., 3] < 1] = 0
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def _follows(fol: str, shown: set) -> bool:
    for t in [t.strip() for t in fol.split(",") if t.strip()]:
        neg = t.startswith("!")
        if (t[1:] in shown if neg else t in shown) == neg:
            return False
    return True


def _previews(layers: Dict[str, np.ndarray], order: List[str], follow: Dict[str, str], dst: Path, fid: str) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    terms = sorted({t.lstrip("!") for f in follow.values() for t in f.split(",") if t.strip()})
    shots = [("all", set(terms))] + [(f"no_{t}", set(terms) - {t}) for t in terms]
    h, w = next(iter(layers.values())).shape[:2]
    tiles = []
    for name, shown in shots:
        im = Image.new("RGBA", (w, h), (12, 53, 59, 255))
        for f in order:
            if f == "base.png" or _follows(follow.get(f, ""), shown):
                im.alpha_composite(_img(layers[f]))
        im.save(dst / f"{fid}_{name}.png")
        tiles.append((name, im))
    sc = 0.3
    from PIL import ImageDraw
    sheet = Image.new("RGBA", (int(w * sc) * len(tiles), int(h * sc) + 18), (20, 24, 28, 255))
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(tiles):
        sheet.paste(im.resize((int(w * sc), int(h * sc)), Image.LANCZOS), (i * int(w * sc), 18))
        d.text((i * int(w * sc) + 4, 3), name, fill=(230, 230, 230, 255))
    sheet.save(dst / f"{fid}_sheet.png")


def _changed(a: np.ndarray, b: np.ndarray, thresh: float = 38.0, min_frac: float = 0.002) -> np.ndarray:
    """Pixels an aligned edit really changed: blurred colour distance, closed, holes filled, specks dropped."""
    import cv2
    d = np.sqrt(((cv2.GaussianBlur(a, (0, 0), 2.0) - cv2.GaussianBlur(b, (0, 0), 2.0)) ** 2).sum(-1))
    m = (d > thresh).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k, iterations=2)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros(m.shape, bool)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_frac * m.size:
            keep |= lab == i
    inv = (~keep).astype(np.uint8)  # fill holes: background regions not touching the border
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, n):
        x, y, w, h = stats[i, :4]
        if x > 0 and y > 0 and x + w < m.shape[1] and y + h < m.shape[0] and stats[i, cv2.CC_STAT_AREA] < 0.01 * m.size:
            keep |= lab == i
    return keep


BACKDROP = (12, 53, 59)  # the flat colour overlay() puts behind a transparent base


def _clip_box(rgb_path: Path, region: str, fig: np.ndarray, grow: float = 1.0) -> Optional[np.ndarray]:
    """Where an item for `region` may be: everything from the top of the picture down to the bottom of the
    region's matches (up to 3, e.g. three heads) plus `grow` x their height. Helmets are wider than heads and
    rest on the shoulders, so only the bottom is limited: that is where a repainted torso would leak in.
    None when the region is not found."""
    found = _find(rgb_path, region, 3, fig.astype(np.float32))
    if not found:
        return None
    m = np.zeros(found[0]["mask"].shape, bool)
    for d in found:
        m |= d["mask"].astype(bool)
    ys = np.nonzero(m.any(1))[0]
    if not len(ys):
        return None
    box = np.zeros(m.shape, bool)
    box[:ys.max() + int(grow * (ys.max() - ys.min())) + 1, :] = True
    return box


def _cut_edit(flat: np.ndarray, edited: np.ndarray, allow: Optional[np.ndarray] = None,
              min_frac: float = 0.002) -> np.ndarray:
    """The item in an aligned Kontext edit: changed pixels, minus what the edit painted as plain backdrop
    (Kontext sometimes erases a part of the figure, e.g. a back sack; cutting that patch would paint
    backdrop over the figure), clipped to `allow`, specks dropped, holes filled."""
    import cv2
    m = _changed(flat, edited)
    m &= np.sqrt(((edited - np.array(BACKDROP, np.float32)) ** 2).sum(-1)) > 40
    if allow is not None:
        m &= allow
    m8 = m.astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m8, 8)
    if n <= 1:
        return m
    big = stats[1:, cv2.CC_STAT_AREA].max()
    keep = np.zeros(m.shape, bool)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= max(min_frac * m.size, 0.05 * big):
            keep |= lab == i
    inv = (~keep).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, n):
        x, y, w, h = stats[i, :4]
        if x > 0 and y > 0 and x + w < m.shape[1] and y + h < m.shape[0] and stats[i, cv2.CC_STAT_AREA] < 0.01 * m.size:
            keep |= lab == i
    return keep


def overlay(base: Path, instruction: str, phrase: str, out: Path, mode: str = "edit", region: str = "",
            seed: int = 0, work: Optional[Path] = None, clip: bool = False, ref: Optional[Path] = None,
            protect: Optional[Path] = None, region_grow: float = 0.0, inpaint_ref: Optional[Path] = None,
            ref_scale: float = 0.4, negative: str = "") -> Dict:
    """An RGBA item layer on the base's canvas: base edited to show the item, item pixels cut by phrase.

    edit mode cuts by changed pixels. With clip=True and a region phrase (e.g. "head") the cut stops one
    region-height below that region, so an edit that also repainted the torso cannot
    leak into the layer and hide gear drawn under it. Pixels the edit painted as plain backdrop (an erased
    back sack) are never cut.

    inpaint mode with protect (a mask PNG, white = never repainted, e.g. the face under a helmet): the
    region (grown by region_grow x its height, never below its bottom) minus that mask is repainted with SDXL,
    the protected pixels are pasted back exactly and the item is cut by changed pixels, so a helmet cannot
    redraw or enlarge the face."""
    work = work or out.parent / "_overlay_work"
    work.mkdir(parents=True, exist_ok=True)
    src = Image.open(base)
    has_alpha = src.mode == "RGBA"
    rgb_path = work / "base_rgb.png"
    flat = Image.new("RGB", src.size, BACKDROP)
    flat.paste(src.convert("RGB"), mask=src.split()[-1] if has_alpha else None)
    flat.save(rgb_path)
    edited = work / "edited.png"
    fig = (np.asarray(src.split()[-1]) > 128) if has_alpha else np.ones(src.size[::-1], bool)
    if mode == "edit":
        engine.edit(rgb_path, instruction, edited, seed=seed, ref=ref)
    else:
        # Only a body part may be repainted: a region that is most of the figure would replace the character.
        region = region or phrase
        reg = [d for d in _find(rgb_path, region, 1, fig.astype(np.float32))]
        if not reg or (reg[0]["mask"] & fig).sum() > 0.6 * fig.sum():
            raise RuntimeError(f"no '{region or phrase}' region smaller than the figure; use mode=edit (Kontext)")
        rm = reg[0]["mask"].astype(bool)
        pm = None
        if protect is not None:
            import cv2
            pm = np.asarray(Image.open(protect).convert("L").resize(src.size)) > 128
            ys = np.nonzero(rm.any(1))[0]
            hgt = int(ys.max() - ys.min()) if len(ys) else 0
            if region_grow > 0 and hgt:
                k = max(3, int(region_grow * hgt) * 2 + 1)
                rm = cv2.dilate(rm.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > 0
                rm[ys.max() + int(0.1 * hgt) + 1:, :] = False  # helmets rest on the head, not the chest
            rm &= ~pm
        mask_p = work / "region.png"
        Image.fromarray((rm * 255).astype(np.uint8)).save(mask_p)
        if pm is None:
            engine.inpaint(rgb_path, mask_p, instruction, edited, refs=[rgb_path], ref_scale=0.5, seed=seed)
        else:
            engine.inpaint(rgb_path, mask_p, instruction, edited, refs=[inpaint_ref or rgb_path], ref_scale=ref_scale, seed=seed, negative=negative,
                           strength=1.0, grow=2, blur=2)
            ed = np.asarray(Image.open(edited).convert("RGB")).copy()
            ed[pm] = np.asarray(flat)[pm]  # the protected pixels stay exactly the base
            Image.fromarray(ed).save(edited)
    e = np.asarray(Image.open(edited).convert("RGB")).astype(np.float32)
    if mode == "inpaint" and protect is not None:
        m = _cut_edit(np.asarray(flat).astype(np.float32), e, rm)
        if m.sum() < 64:
            raise RuntimeError(f"the inpaint changed nothing visible around the {region} ({edited})")
    elif mode == "edit":
        # Kontext keeps the framing, so the item is where the picture changed; SAM by phrase only as a fallback.
        allow = None
        if clip and region:
            allow = _clip_box(rgb_path, region, fig)
            if allow is None:
                print(f"refart overlay: no '{region}' region found, cut not clipped", file=sys.stderr)
        m = _cut_edit(np.asarray(flat).astype(np.float32), e, allow)
        if m.sum() < 64:
            raise RuntimeError(f"the edit changed nothing visible{' in the ' + region + ' area' if allow is not None else ''} ({edited})")
    else:
        found = _find(edited, phrase, 3, fig.astype(np.float32))
        if not found:
            raise RuntimeError(f"'{phrase}' not found in the edited picture ({edited})")
        m = np.zeros(found[0]["mask"].shape, bool)
        for d in found:
            m |= d["mask"]
    lay = np.zeros(m.shape + (4,), np.float32)
    lay[..., :3] = e
    lay[..., 3] = m
    if m.sum() > 0.85 * max(1, fig.sum()):
        raise RuntimeError(f"'{phrase}' covers the whole figure in {edited}: the edit repainted the character "
                           "instead of adding a separate item (try clip=True with a region)")
    _img(lay).save(out)
    return {"out": str(out), "edited": str(edited), "pixels": int(m.sum())}
