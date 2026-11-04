#!/usr/bin/env python3
"""
CLI map editor for Grim Dawn MAP9 world files (the .map inside Levels.arc / Maps.arc).

A Grim Dawn game session runs exactly one World; travel (riftgates, portals, doors) only
works between regions of that world, and the world carries its own quest list. So making
Nydiamar / NydiamarDungeons / Reign of Terror reachable "while keeping progress" means
merging their regions + quest files into the campaign world, then linking them.

Container layout (reverse-engineered, validated by byte-identical round trips):

    "MAP" 0x09 | u32 offset_of_chunk_26_minus_8
    chunk = u32 id | u32 size | data
      27  quest files      u32 n, n x str
      17  named points     (opaque, kept)
      24  area labels      (opaque, kept)
       1  regions          u32 n, n x { i32 x9 (bounds+position), guid16, str riftgate_record,
                                        str unknown, str skybox_record, str level_name,
                                        u32 abs_offset, u32 size }        -> into chunk 2
      25  minimap index    u32 0, u32 n, n x { u32 abs_offset, u32 size } -> into chunk 26
      16  start point      u32 ?, u32 region_index, f32 x,y,z
      26  minimaps         blob
       2  levels           blob ("LVL" v15 per region, concatenated)
    str = u32 length + bytes (latin-1)

Commands:
    info <map>                          chunks, quest/region counts, start point
    regions <map> [--grep TEXT]          list regions (index, guid, level, riftgate record)
    quests <map>                         list quest files
    roundtrip <map>                      parse + rewrite to a temp file, compare bytes
    merge <base.map> <other.map>... -o <out.map> [--offset X,Y,Z]
                                         append other worlds' regions, quests, minimaps,
                                         level data; start point stays the base world's
    extract <mod> [--arc Levels.arc]     pull .map files out of a mod's .arc
    pack <mod> <map>... [--arc Maps.arc]  put edited .map files back into the mod's .arc
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Sequence, Tuple

MAGIC = b"MAP\x09"
COPY_BUF = 16 * 1024 * 1024


def _str(b: bytes, o: int) -> Tuple[str, int]:
    n = struct.unpack_from("<I", b, o)[0]
    return b[o + 4 : o + 4 + n].decode("latin-1"), o + 4 + n


def _pstr(s: str) -> bytes:
    raw = s.encode("latin-1")
    return struct.pack("<I", len(raw)) + raw


@dataclass
class Region:
    ints: Tuple[int, ...]  # 9 x int32: bounds + world position (grid units)
    guid: bytes
    riftgate: str
    unknown: str
    skybox: str
    level: str
    offset: int
    size: int
    # where the bytes physically live (for merges: another file)
    src: Optional[Path] = None
    # edited level bytes (replace offset/size/src when set)
    data: Optional[bytes] = None

    @property
    def position(self) -> Tuple[int, int, int]:
        return tuple(self.ints[6:9])  # type: ignore[return-value]

    @property
    def length(self) -> int:
        return len(self.data) if self.data is not None else self.size

    def encode(self, offset: int) -> bytes:
        return (
            struct.pack("<9i", *self.ints)
            + self.guid
            + _pstr(self.riftgate)
            + _pstr(self.unknown)
            + _pstr(self.skybox)
            + _pstr(self.level)
            + struct.pack("<II", offset, self.length)
        )


@dataclass
class PointEntry:
    uid: bytes  # entity unique id (riftgate discovery stores this)
    record: str
    region: bytes  # region guid the entity lives in
    pos: Tuple[float, float, float]


@dataclass
class PointGroup:
    """Chunk 17 node: named group of teleport-relevant entities (riftgates, dungeon entrances...)."""

    type: int
    name: str
    category: str
    entries: List[PointEntry]
    guid: bytes
    children: List[Tuple[bytes, "PointGroup"]] = field(default_factory=list)

    def count(self) -> int:
        return 1 + sum(c.count() for _, c in self.children)

    def walk(self):
        yield self
        for _, c in self.children:
            yield from c.walk()


def _read_group(b: bytes, o: int) -> Tuple[PointGroup, int]:
    t = struct.unpack_from("<I", b, o)[0]
    o += 4
    name, o = _str(b, o)
    cat, o = _str(b, o)
    n = struct.unpack_from("<I", b, o)[0]
    o += 4
    ents = []
    for _ in range(n):
        uid = b[o : o + 16]
        o += 16
        rec, o = _str(b, o)
        reg = b[o : o + 16]
        o += 16
        pos = struct.unpack_from("<3f", b, o)
        o += 12
        ents.append(PointEntry(uid, rec, reg, pos))
    gid = b[o : o + 16]
    o += 16
    ns = struct.unpack_from("<I", b, o)[0]
    o += 4
    kids = []
    for _ in range(ns):
        link = b[o : o + 16]
        o += 16
        g, o = _read_group(b, o)
        kids.append((link, g))
    return PointGroup(t, name, cat, ents, gid, kids), o


def _write_group(g: PointGroup) -> bytes:
    parts = [struct.pack("<I", g.type), _pstr(g.name), _pstr(g.category), struct.pack("<I", len(g.entries))]
    for e in g.entries:
        parts += [e.uid, _pstr(e.record), e.region, struct.pack("<3f", *e.pos)]
    parts += [g.guid, struct.pack("<I", len(g.children))]
    for link, c in g.children:
        parts += [link, _write_group(c)]
    return b"".join(parts)


def parse_points(data: bytes) -> Tuple[int, List[PointGroup]]:
    head, total = struct.unpack_from("<II", data, 0)
    o, groups = 8, []
    while o < len(data):
        g, o = _read_group(data, o)
        groups.append(g)
    if sum(g.count() for g in groups) != total:
        raise ValueError("chunk 17 group count mismatch")
    return head, groups


def encode_points(head: int, groups: Sequence[PointGroup]) -> bytes:
    return struct.pack("<II", head, sum(g.count() for g in groups)) + b"".join(_write_group(g) for g in groups)


@dataclass
class Minimap:
    offset: int
    size: int
    src: Optional[Path] = None


@dataclass
class Chunk:
    id: int
    offset: int  # of the chunk header
    size: int


@dataclass
class GameMap:
    path: Path
    header_value: int
    chunks: List[Chunk]
    quests: List[str] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    minimap_head: int = 0
    minimaps: List[Minimap] = field(default_factory=list)
    start: bytes = b""
    raw: Dict[int, bytes] = field(default_factory=dict)  # small opaque chunks
    order: List[int] = field(default_factory=list)

    def chunk(self, cid: int) -> Optional[Chunk]:
        return next((c for c in self.chunks if c.id == cid), None)

    @property
    def start_region(self) -> int:
        return struct.unpack_from("<I", self.start, 4)[0] if len(self.start) >= 8 else -1


def read_map(path: Path) -> GameMap:
    path = Path(path)
    size = os.path.getsize(path)
    with path.open("rb") as f:
        head = f.read(8)
        if head[:4] != MAGIC:
            raise ValueError(f"{path.name}: not a MAP9 file ({head[:4]!r})")
        gm = GameMap(path, struct.unpack("<I", head[4:])[0], [])
        off = 8
        while off < size:
            f.seek(off)
            cid, csize = struct.unpack("<II", f.read(8))
            gm.chunks.append(Chunk(cid, off, csize))
            gm.order.append(cid)
            if cid not in (2, 26):  # the two big blobs are streamed, never loaded
                data = f.read(csize)
                if cid == 27:
                    n = struct.unpack_from("<I", data, 0)[0]
                    o = 4
                    for _ in range(n):
                        q, o = _str(data, o)
                        gm.quests.append(q)
                elif cid == 1:
                    n = struct.unpack_from("<I", data, 0)[0]
                    o = 4
                    for _ in range(n):
                        ints = struct.unpack_from("<9i", data, o)
                        o += 36
                        guid = data[o : o + 16]
                        o += 16
                        rift, o = _str(data, o)
                        unk, o = _str(data, o)
                        sky, o = _str(data, o)
                        lvl, o = _str(data, o)
                        roff, rsize = struct.unpack_from("<II", data, o)
                        o += 8
                        gm.regions.append(Region(ints, guid, rift, unk, sky, lvl, roff, rsize, path))
                    if o != len(data):
                        raise ValueError(f"region table: parsed {o} of {len(data)} bytes")
                elif cid == 25:
                    gm.minimap_head, n = struct.unpack_from("<II", data, 0)
                    for i in range(n):
                        moff, msize = struct.unpack_from("<II", data, 8 + i * 8)
                        gm.minimaps.append(Minimap(moff, msize, path))
                elif cid == 16:
                    gm.start = data
                else:
                    gm.raw[cid] = data
            off += 8 + csize
    if len(gm.minimaps) not in (0, len(gm.regions)):
        raise ValueError("minimap index count != region count")
    return gm


def _copy_range(src: Path, offset: int, size: int, out: BinaryIO, handles: Dict[Path, BinaryIO]) -> None:
    fh = handles.get(src)
    if fh is None:
        fh = handles[src] = src.open("rb")
    fh.seek(offset)
    left = size
    while left:
        buf = fh.read(min(COPY_BUF, left))
        if not buf:
            raise IOError(f"short read in {src}")
        out.write(buf)
        left -= len(buf)


def write_map(gm: GameMap, out_path: Path) -> None:
    """Serialize; region/minimap bytes are streamed from their source files, offsets rebased."""
    out_path = Path(out_path)
    quests = struct.pack("<I", len(gm.quests)) + b"".join(_pstr(q) for q in gm.quests)

    def region_table(level_base: int) -> bytes:
        parts, cur = [struct.pack("<I", len(gm.regions))], level_base
        for r in gm.regions:
            parts.append(r.encode(cur))
            cur += r.length
        return b"".join(parts)

    def minimap_index(base: int) -> bytes:
        parts, cur = [struct.pack("<II", gm.minimap_head, len(gm.minimaps))], base
        for m in gm.minimaps:
            parts.append(struct.pack("<II", cur, m.size))
            cur += m.size
        return b"".join(parts)

    region_len = len(region_table(0))
    index_len = len(minimap_index(0))
    big26 = gm.chunk(26)
    mm_prefix_len = 8 if big26 else 0  # chunk 26 starts with u32 0, u32 n
    mm_total = mm_prefix_len + sum(m.size for m in gm.minimaps) + _minimap_tail_len(gm)
    lvl_total = sum(r.length for r in gm.regions)
    if 8 + lvl_total + sum(len(d) for d in gm.raw.values()) + mm_total >= 2**32:
        raise ValueError(f"world too large for MAP9 32-bit offsets ({lvl_total + mm_total:,} bytes)")

    # pass 1: compute absolute positions of every chunk
    sizes = {27: len(quests), 1: region_len, 25: index_len, 16: len(gm.start), 26: mm_total, 2: lvl_total}
    sizes.update({cid: len(d) for cid, d in gm.raw.items()})
    pos, layout = 8, {}
    for cid in gm.order:
        layout[cid] = pos
        pos += 8 + sizes[cid]
    mm_base = layout.get(26, 0) + 8 + mm_prefix_len
    lvl_base = layout.get(2, 0) + 8
    header_value = layout[26] - 8 if 26 in layout else gm.header_value

    handles: Dict[Path, BinaryIO] = {}
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with tmp.open("wb") as out:
            out.write(MAGIC + struct.pack("<I", header_value))
            for cid in gm.order:
                out.write(struct.pack("<II", cid, sizes[cid]))
                if cid == 27:
                    out.write(quests)
                elif cid == 1:
                    out.write(region_table(lvl_base))
                elif cid == 25:
                    out.write(minimap_index(mm_base))
                elif cid == 16:
                    out.write(gm.start)
                elif cid == 26:
                    out.write(struct.pack("<II", 0, len(gm.minimaps)))
                    for m in gm.minimaps:
                        _copy_range(m.src or gm.path, m.offset, m.size, out, handles)
                    _write_minimap_tail(gm, out, handles)
                elif cid == 2:
                    for r in gm.regions:
                        if r.data is not None:
                            out.write(r.data)
                        else:
                            _copy_range(r.src or gm.path, r.offset, r.size, out, handles)
                else:
                    out.write(gm.raw[cid])
        os.replace(tmp, out_path)
    finally:
        for fh in handles.values():
            fh.close()
        if tmp.exists():
            tmp.unlink()


def _minimap_tail(gm: GameMap) -> Tuple[int, int]:
    """Bytes in chunk 26 after the last indexed minimap (kept verbatim)."""
    c = gm.chunk(26)
    if not c:
        return 0, 0
    end = c.offset + 8 + c.size
    last = max((m.offset + m.size for m in gm.minimaps if (m.src or gm.path) == gm.path), default=c.offset + 16)
    return last, max(0, end - last)


def _minimap_tail_len(gm: GameMap) -> int:
    return _minimap_tail(gm)[1]


def _write_minimap_tail(gm: GameMap, out: BinaryIO, handles: Dict[Path, BinaryIO]) -> None:
    start, n = _minimap_tail(gm)
    if n:
        _copy_range(gm.path, start, n, out, handles)


# ---------------------------------------------------------------- level (LVL v15) objects

LVL_MAGIC = b"LVL\x0f"
LVL_HEADER = 28  # magic + 6 floats (bounds)


@dataclass
class LevelObject:
    record: int  # index into the level's record table
    rot: Tuple[float, ...]  # 3x3 rotation (9 floats)
    pos: Tuple[float, float, float]  # region-local position
    uid: Optional[bytes] = None  # unique id (riftgates, doors, uniques...)

    def encode(self) -> bytes:
        tail = struct.pack("<I", 1) + self.uid if self.uid else struct.pack("<I", 0)
        return struct.pack("<I9f3f", self.record, *self.rot, *self.pos) + tail


@dataclass
class Level:
    header: bytes
    chunks: List[Tuple[int, bytes]]
    records: List[str]
    objects: List[LevelObject]
    obj_tail: bytes  # bytes after the object list inside chunk 5 (normally empty)

    def encode(self) -> bytes:
        c5 = (
            struct.pack("<I", len(self.records))
            + b"".join(_pstr(s) for s in self.records)
            + struct.pack("<I", len(self.objects))
            + b"".join(o.encode() for o in self.objects)
            + self.obj_tail
        )
        out = [self.header]
        for cid, data in self.chunks:
            data = c5 if cid == 5 else data
            out.append(struct.pack("<II", cid, len(data)) + data)
        return b"".join(out)

    def record_index(self, record: str) -> int:
        low = record.replace("\\", "/").lower()
        for i, s in enumerate(self.records):
            if s.replace("\\", "/").lower() == low:
                return i
        self.records.append(record)  # appended: existing indices stay valid
        return len(self.records) - 1

    def find_uid(self, uid: bytes) -> Optional[LevelObject]:
        return next((o for o in self.objects if o.uid == uid), None)


def read_level_bytes(gm: GameMap, region: Region) -> bytes:
    if region.data is not None:
        return region.data
    with (region.src or gm.path).open("rb") as f:
        f.seek(region.offset)
        return f.read(region.size)


def parse_level(b: bytes) -> Level:
    if b[:4] != LVL_MAGIC:
        raise ValueError(f"unsupported level version {b[:4]!r}")
    o, chunks = LVL_HEADER, []
    while o < len(b):
        cid, sz = struct.unpack_from("<II", b, o)
        chunks.append((cid, b[o + 8 : o + 8 + sz]))
        o += 8 + sz
    c5 = next(d for cid, d in chunks if cid == 5)
    n = struct.unpack_from("<I", c5, 0)[0]
    p, records = 4, []
    for _ in range(n):
        s, p = _str(c5, p)
        records.append(s)
    cnt = struct.unpack_from("<I", c5, p)[0]
    p += 4
    objs = []
    for _ in range(cnt):
        vals = struct.unpack_from("<I9f3f", c5, p)
        p += 52
        flag = struct.unpack_from("<I", c5, p)[0]
        p += 4
        uid = None
        if flag == 1:
            uid = c5[p : p + 16]
            p += 16
        objs.append(LevelObject(vals[0], vals[1:10], vals[10:13], uid))
    return Level(b[:LVL_HEADER], chunks, records, objs, c5[p:])


def region_by(gm: GameMap, key) -> Tuple[int, Region]:
    """Region by index, GUID (bytes/hex) or level-name substring."""
    if isinstance(key, int):
        return key, gm.regions[key]
    if isinstance(key, (bytes, bytearray)) or (isinstance(key, str) and len(key) == 32 and all(c in "0123456789abcdef" for c in key.lower())):
        g = bytes(key) if isinstance(key, (bytes, bytearray)) else bytes.fromhex(key)
        for i, r in enumerate(gm.regions):
            if r.guid == g:
                return i, r
        raise KeyError(f"no region with guid {g.hex()}")
    hits = [(i, r) for i, r in enumerate(gm.regions) if str(key).lower() in r.level.lower()]
    if len(hits) != 1:
        raise KeyError(f"region '{key}' matched {len(hits)} regions")
    return hits[0]


def add_object(gm: GameMap, region: Region, record: str, pos, rot=None, uid: Optional[bytes] = None) -> LevelObject:
    lvl = parse_level(read_level_bytes(gm, region))
    obj = LevelObject(lvl.record_index(record), tuple(rot or (1, 0, 0, 0, 1, 0, 0, 0, 1)), tuple(pos), uid)
    lvl.objects.append(obj)
    region.data = lvl.encode()
    return obj


def add_point(gm: GameMap, category: str, group_name: str, entry: PointEntry) -> None:
    """Register an entity in the chunk-17 index (riftgate travel resolves uid -> region/pos here)."""
    head, groups = parse_points(gm.raw[17])
    grp = next((n for g in groups for n in g.walk() if n.name == group_name and n.category == category), None)
    if grp is None:
        grp = PointGroup(3, group_name, category, [], os.urandom(16))
        groups.append(grp)
    grp.entries = [e for e in grp.entries if e.uid != entry.uid] + [entry]
    gm.raw[17] = encode_points(head, groups)


def find_point(gm: GameMap, uid: bytes) -> Optional[PointEntry]:
    _, groups = parse_points(gm.raw[17])
    return next((e for g in groups for n in g.walk() for e in n.entries if e.uid == uid), None)


# ---------------------------------------------------------------- editing

def region_box(r: Region) -> Tuple[int, int, int, int]:
    """Region footprint (x0, z0, x1, z1): position + size. The game's own worlds never overlap these."""
    x, _, z = r.ints[6:9]
    return x, z, x + r.ints[0], z + r.ints[2]


def footprint(regions: Sequence[Region]) -> Tuple[int, int, int, int]:
    boxes = [region_box(r) for r in regions]
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def find_overlaps(regions: Sequence[Region], limit: int = 20) -> List[Tuple[int, int]]:
    """Pairs of region indexes whose footprints overlap (sweep over x)."""
    order = sorted(range(len(regions)), key=lambda i: region_box(regions[i])[0])
    active: List[int] = []
    hits: List[Tuple[int, int]] = []
    for i in order:
        bi = region_box(regions[i])
        active = [j for j in active if region_box(regions[j])[2] > bi[0]]
        for j in active:
            bj = region_box(regions[j])
            if bi[1] < bj[3] and bj[1] < bi[3]:
                hits.append((j, i))
                if len(hits) >= limit:
                    return hits
        active.append(i)
    return hits


def auto_offsets(base: GameMap, others: Sequence[GameMap], gap: int = 512, grid: int = 64) -> List[Tuple[int, int, int]]:
    """Place each extra world in empty space east of everything placed so far (grid-aligned)."""
    def snap(v: int) -> int:
        return -(-v // grid) * grid

    edge = footprint(base.regions)[2] + gap
    out = []
    for other in others:
        x0, z0, x1, _ = footprint(other.regions)
        dx = snap(edge - x0)
        out.append((dx, 0, 0))
        edge = x1 + dx + gap
    return out


def merge_maps(
    base: GameMap,
    others: Sequence[GameMap],
    offset: Tuple[int, int, int] = (0, 0, 0),
    offsets: Optional[Sequence[Tuple[int, int, int]]] = None,
) -> List[str]:
    """Append other worlds' regions/quests/minimaps into base (start point unchanged).

    offsets: per-world shift of every region position (keeps each world's internal layout);
    default `offset` multiplied by the world's index. Regions must not overlap afterwards.
    """
    notes: List[str] = []
    guids = {r.guid for r in base.regions}
    quests_l = {q.lower() for q in base.quests}
    head, groups = parse_points(base.raw[17]) if 17 in base.raw else (0, [])
    for k, other in enumerate(others, start=1):
        if 17 in other.raw:
            # riftgates / dungeon entrances / shrines of merged regions (regions are GUID-keyed)
            _, ogroups = parse_points(other.raw[17])
            have = {e.uid for g in groups for n in g.walk() for e in n.entries}
            fresh = [g for g in ogroups if not any(e.uid in have for n in g.walk() for e in n.entries)]
            groups.extend(fresh)
            notes.append(f"{other.path.name}: +{len(fresh)} teleport/point groups")
        dx, dy, dz = offsets[k - 1] if offsets else tuple(c * k for c in offset)
        added = dup = 0
        for i, r in enumerate(other.regions):
            if r.guid in guids:
                dup += 1
                continue
            ints = list(r.ints)
            ints[6] += dx
            ints[7] += dy
            ints[8] += dz
            base.regions.append(Region(tuple(ints), r.guid, r.riftgate, r.unknown, r.skybox, r.level, r.offset, r.size, r.src or other.path))
            if other.minimaps:
                m = other.minimaps[i]
                base.minimaps.append(Minimap(m.offset, m.size, m.src or other.path))
            guids.add(r.guid)
            added += 1
        newq = [q for q in other.quests if q.lower() not in quests_l]
        base.quests.extend(newq)
        quests_l.update(q.lower() for q in newq)
        notes.append(
            f"{other.path.name}: +{added} regions ({dup} duplicate GUIDs skipped), +{len(newq)} quests, "
            f"shifted by ({dx}, {dy}, {dz})"
        )
    if len(base.minimaps) != len(base.regions):
        raise ValueError("minimap/region count mismatch after merge")
    if 17 in base.raw:
        base.raw[17] = encode_points(head, groups)
    notes.append("area labels (chunk 24) kept from the base world only (minimap text labels)")
    return notes


# ---------------------------------------------------------------- arc I/O

def _game():
    from gd_paths import GamePaths, resolve_game_dir

    return GamePaths(resolve_game_dir(None))


def _unarc(arc: Path, dest: Path) -> None:
    """arzedit unarc: handles >2 GB maps (ArchiveTool crashes) and writes entries at dest's top level."""
    import subprocess

    from gd_paths import resolve_arzedit

    arz = resolve_arzedit()
    if not arz:
        raise RuntimeError("bin/arzedit.exe missing (Build-Arzedit.bat)")
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([str(arz), "unarc", str(arc), "-o", str(dest)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"unarc {arc}: {(proc.stdout + proc.stderr)[-1000:]}")


def extract_maps(mod_root: Path, out_dir: Path, arcs: Sequence[str] = ("Levels.arc", "Maps.arc")) -> List[Path]:
    found: List[Path] = []
    for name in arcs:
        arc = next((p for p in (mod_root / "resources").glob("*.arc") if p.name.lower() == name.lower()), None)
        if not arc:
            continue
        dest = out_dir / arc.stem
        print(f"Extracting {arc} -> {dest}", flush=True)
        _unarc(arc, dest)
        found += sorted(dest.rglob("*.map"))
    return found


def pack_maps(mod_root: Path, maps: Sequence[Path], arc_name: str = "Maps.arc") -> Path:
    """Add/replace .map files at the top level of the mod's resources/<arc_name>."""
    from archive_tool import arc_root, pack_arc

    res = mod_root / "resources"
    arc = next((p for p in res.glob("*.arc") if p.name.lower() == arc_name.lower()), res / arc_name)
    work = Path(tempfile.mkdtemp(prefix="gdmap_pack_", dir=str(Path(__file__).resolve().parent / "work")))
    try:
        if arc.is_file():
            _unarc(arc, work)
        root = arc_root(work, arc)  # also undoes wrongly nested folders from older packers
        for m in maps:
            existing = next((p for p in root.rglob(Path(m).name)), None)
            dest = existing or (root / Path(m).name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(m, dest)
        if arc.is_file():
            bak = arc.with_suffix(".arc.bak_map")
            if not bak.exists():
                shutil.copy2(arc, bak)
        pack_arc(root, arc)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return arc


# ---------------------------------------------------------------- CLI

def _cmd_info(a) -> int:
    gm = read_map(Path(a.map))
    print(f"{gm.path.name}: MAP9, header={gm.header_value}")
    for c in gm.chunks:
        print(f"  chunk {c.id:3}  @{c.offset:>12}  {c.size:>12} bytes")
    print(f"  quests: {len(gm.quests)}   regions: {len(gm.regions)}   minimaps: {len(gm.minimaps)}")
    print(f"  start region: {gm.start_region} ({gm.regions[gm.start_region].level if 0 <= gm.start_region < len(gm.regions) else '?'})")
    rifts = sum(1 for r in gm.regions if r.riftgate)
    print(f"  regions with riftgate-map records: {rifts}")
    if 17 in gm.raw:
        _, groups = parse_points(gm.raw[17])
        cats: Dict[str, int] = {}
        for g in groups:
            for n in g.walk():
                cats[n.category] = cats.get(n.category, 0) + len(n.entries)
        print(f"  point index: {cats}")
    return 0


def _cmd_points(a) -> int:
    gm = read_map(Path(a.map))
    _, groups = parse_points(gm.raw[17])
    idx = {r.guid: (i, r.level) for i, r in enumerate(gm.regions)}
    cat = (a.category or "").lower()
    for g in groups:
        for n in g.walk():
            if cat and cat not in n.category.lower():
                continue
            for e in n.entries:
                ri, lvl = idx.get(e.region, (-1, "?"))
                print(f"{n.category:18} {n.name:40} uid={e.uid.hex()} region={ri} ({lvl}) pos=({e.pos[0]:.1f},{e.pos[1]:.1f},{e.pos[2]:.1f}) {e.record}")
    return 0


def _cmd_regions(a) -> int:
    gm = read_map(Path(a.map))
    g = (a.grep or "").lower()
    for i, r in enumerate(gm.regions):
        line = f"{i:5}  {r.guid.hex()}  pos={r.position}  {r.level}  {r.riftgate}"
        if not g or g in line.lower():
            print(line)
    return 0


def _cmd_quests(a) -> int:
    for q in read_map(Path(a.map)).quests:
        print(q)
    return 0


def _cmd_roundtrip(a) -> int:
    src = Path(a.map)
    gm = read_map(src)
    out = Path(a.out) if a.out else src.with_name(src.stem + ".roundtrip.map")
    write_map(gm, out)
    same = os.path.getsize(out) == os.path.getsize(src)
    if same:
        with src.open("rb") as x, out.open("rb") as y:
            while True:
                bx, by = x.read(COPY_BUF), y.read(COPY_BUF)
                if bx != by:
                    same = False
                    break
                if not bx:
                    break
    print(f"round trip {'IDENTICAL' if same else 'DIFFERS'}: {out}")
    if not a.keep:
        out.unlink()
    return 0 if same else 1


def _cmd_merge(a) -> int:
    base = read_map(Path(a.base))
    others = [read_map(Path(p)) for p in a.others]
    off = tuple(int(x) for x in a.offset.split(",")) if a.offset else (0, 0, 0)
    for n in merge_maps(base, others, off):  # type: ignore[arg-type]
        print(n)
    write_map(base, Path(a.out))
    print(f"wrote {a.out}: {len(base.regions)} regions, {len(base.quests)} quests")
    return 0


def _cmd_extract(a) -> int:
    from gd_paths import find_mod_roots

    game = _game()
    root = (find_mod_roots(game.mods_dir, a.mod) or [Path(a.mod)])[0]
    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "work" / "maps" / root.name
    for p in extract_maps(root, out, a.arc or ("Levels.arc", "Maps.arc")):
        print(p)
    return 0


def _cmd_pack(a) -> int:
    game = _game()
    root = Path(a.mod) if Path(a.mod).is_dir() else game.mods_dir / a.mod
    print(f"packed into {pack_maps(root, [Path(m) for m in a.maps], a.arc)}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Grim Dawn MAP9 world editor (CLI)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info"); s.add_argument("map"); s.set_defaults(fn=_cmd_info)
    s = sub.add_parser("regions"); s.add_argument("map"); s.add_argument("--grep"); s.set_defaults(fn=_cmd_regions)
    s = sub.add_parser("quests"); s.add_argument("map"); s.set_defaults(fn=_cmd_quests)
    s = sub.add_parser("points", help="riftgates / dungeon entrances / shrines index")
    s.add_argument("map"); s.add_argument("--category"); s.set_defaults(fn=_cmd_points)
    s = sub.add_parser("roundtrip"); s.add_argument("map"); s.add_argument("-o", "--out"); s.add_argument("--keep", action="store_true"); s.set_defaults(fn=_cmd_roundtrip)
    s = sub.add_parser("merge"); s.add_argument("base"); s.add_argument("others", nargs="+"); s.add_argument("-o", "--out", required=True)
    s.add_argument("--offset", default=None, help="X,Y,Z added to each merged world's region positions (multiplied per world)")
    s.set_defaults(fn=_cmd_merge)
    s = sub.add_parser("extract"); s.add_argument("mod"); s.add_argument("--arc", nargs="*"); s.add_argument("-o", "--out"); s.set_defaults(fn=_cmd_extract)
    s = sub.add_parser("pack"); s.add_argument("mod"); s.add_argument("maps", nargs="+"); s.add_argument("--arc", default="Maps.arc"); s.set_defaults(fn=_cmd_pack)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
