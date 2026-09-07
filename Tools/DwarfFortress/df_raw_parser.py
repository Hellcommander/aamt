#!/usr/bin/env python3
"""Generic Dwarf Fortress RAW tokenizer and object-block extractor."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

Token = Tuple[str, List[str]]

_TOKEN_RE = re.compile(r"\[([^\]]+)\]")


@dataclass
class ObjectBlock:
    """A top-level object definition such as [CREATURE:DWARF] ... until next same-kind object."""

    kind: str
    id: str
    tokens: List[Token] = field(default_factory=list)
    raw_text: str = ""

    @property
    def header(self) -> Token:
        return (self.kind, [self.id])


def tokenize_text(text: str) -> List[Token]:
    """
    Parse [TOKEN:args] from text.

    Lines that contain no tokens are treated as comments and skipped.
    Nested brackets are not supported (DF raws do not nest).
    """
    tokens: List[Token] = []
    for line in text.splitlines():
        if "[" not in line:
            continue
        for m in _TOKEN_RE.finditer(line):
            inner = m.group(1).strip()
            if not inner:
                continue
            parts = inner.split(":")
            name = parts[0].strip()
            args = [p.strip() for p in parts[1:]]
            if name:
                tokens.append((name, args))
    return tokens


def tokenize_file(path: Union[str, Path], encoding: str = "latin-1") -> List[Token]:
    """Tokenize a RAW file. latin-1 preserves CP437/extended chars in language files."""
    p = Path(path)
    return tokenize_text(p.read_text(encoding=encoding, errors="replace"))


def split_object_blocks(
    text: str,
    *,
    object_kinds: Optional[Sequence[str]] = None,
) -> List[ObjectBlock]:
    """
    Split text into object blocks.

    A block starts at [KIND:ID] where KIND is in object_kinds (or any known object
    starter when None). Continues until the next block of the same KIND (or any
    KIND in the filter set).
    """
    kinds = {k.upper() for k in object_kinds} if object_kinds else None
    # Find all [TOKEN:...] with positions
    matches = list(_TOKEN_RE.finditer(text))
    starters: List[Tuple[int, int, str, str]] = []  # start, end, kind, id
    for m in matches:
        parts = m.group(1).split(":")
        kind = parts[0].strip().upper()
        if kinds is not None and kind not in kinds:
            continue
        if len(parts) < 2:
            continue
        # Heuristic: object headers are KIND:ID with ID being a single identifier
        # and KIND matching known object types when unfiltered.
        if kinds is None and kind not in _DEFAULT_OBJECT_KINDS:
            continue
        oid = parts[1].strip()
        if not oid:
            continue
        starters.append((m.start(), m.end(), kind, oid))

    blocks: List[ObjectBlock] = []
    for i, (start, _end, kind, oid) in enumerate(starters):
        stop = starters[i + 1][0] if i + 1 < len(starters) else len(text)
        chunk = text[start:stop]
        tokens = tokenize_text(chunk)
        blocks.append(ObjectBlock(kind=kind, id=oid, tokens=tokens, raw_text=chunk.rstrip() + "\n"))
    return blocks


_DEFAULT_OBJECT_KINDS = {
    "CREATURE",
    "ENTITY",
    "BODY",
    "BODY_DETAIL_PLAN",
    "TISSUE_TEMPLATE",
    "MATERIAL_TEMPLATE",
    "TRANSLATION",
    "WORD",
    "SYMBOL",
    "ITEM",
    "BUILDING",
    "REACTION",
    "INTERACTION",
    "GRAPHICS",
    "TILE_PAGE",
    "CREATURE_GRAPHICS",
    "LAYER_SET_TEMPLATE",
    "PLANT",
    "INORGANIC",
    "DESCRIPTOR_COLOR",
    "DESCRIPTOR_SHAPE",
    "DESCRIPTOR_PATTERN",
    "LANGUAGE",
}


def extract_named_block(
    text: str,
    kind: str,
    object_id: str,
) -> Optional[ObjectBlock]:
    """Extract a single named CREATURE / ENTITY / BODY / etc. block."""
    kind_u = kind.upper()
    id_u = object_id.upper()
    for block in split_object_blocks(text, object_kinds=(kind_u,)):
        if block.id.upper() == id_u:
            return block
    return None


def extract_named_block_from_file(
    path: Union[str, Path],
    kind: str,
    object_id: str,
    encoding: str = "latin-1",
) -> Optional[ObjectBlock]:
    text = Path(path).read_text(encoding=encoding, errors="replace")
    return extract_named_block(text, kind, object_id)


def tokens_to_dict_multi(tokens: Iterable[Token]) -> Dict[str, List[List[str]]]:
    """Map token name → list of arg lists (preserves duplicates)."""
    out: Dict[str, List[List[str]]] = {}
    for name, args in tokens:
        out.setdefault(name.upper(), []).append(args)
    return out


def find_tokens(tokens: Iterable[Token], name: str) -> List[Token]:
    n = name.upper()
    return [(t, a) for t, a in tokens if t.upper() == n]


def format_token(name: str, args: Sequence[str] | None = None) -> str:
    if not args:
        return f"[{name}]"
    return f"[{name}:{':'.join(args)}]"
