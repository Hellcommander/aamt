"""Seal a folder of sounds into one archive that a game-side reader (Lua or C++) unseals in memory, so the files never
sit loose on disk and can't be lifted out by copying. Format MTSA1, little-endian:

    "MTSA1\\0"  8 bytes key id (SHA-256 of the key, first 8)  u32 count
    per entry: u16 nameLen, UTF-8 asset path ("/sfx/x.ogg"), u64 offset, u32 size, u64 nonce
    data:      each entry's bytes XOR a splitmix64 keystream seeded with key0 ^ nonce ^ fnv1a64(path), each word ^ key1

The cipher is an ARX keystream, not AES, because the Lua reader has to run it fast inside the game's own Lua with no
C library: it scrambles against copying and tools, it is not secrecy, and a reader's key is in that reader. The key is
32 bytes of hex in a key file next to this script by default (audio_seal.key), made on first use and never committed.
Readers: audio_seal_reader.lua (OpenStarbound asset script, installed into a mod with `install-lua`) and the engine
fork's SealedAssetSource (C++, key header from `write-cpp-key`); both must carry the same key, and the key id in the
header lets them refuse an archive sealed with another.

Usage: python audio_seal.py seal <mod folder> <archive> [--include sfx interface/magitech/sounds] [--key file] [--remove]
       python audio_seal.py list <archive> [--key file]
       python audio_seal.py unseal <archive> <out folder> [--key file]
       python audio_seal.py install-lua <mod folder> [--archive /sfx/magitech/sounds.mtsa] [--script /scripts/magitech/audio_unseal.lua] [--key file | --no-key]
       python audio_seal.py write-cpp-key <StarSealedKey.hpp>
       python audio_seal.py keystream-test                 (prints vectors the Lua and C++ readers are checked against)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from typing import Dict, Iterable, List, Tuple

MAGIC = b"MTSA1\0"
MASK = (1 << 64) - 1
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY = os.path.join(HERE, "audio_seal.key")
KINDS = (".ogg", ".wav", ".mp3", ".flac")
NL = chr(10)


def load_key(path: str = DEFAULT_KEY) -> bytes:
    if not os.path.exists(path):
        with open(path, "w", encoding="ascii") as f:
            f.write(os.urandom(32).hex() + NL)
        print(f"made a new seal key: {path} (keep it out of the repository; the readers must carry the same key)")
    key = bytes.fromhex(open(path, encoding="ascii").read().strip())
    if len(key) != 32:
        raise SystemExit(f"{path}: expected 32 bytes as hex")
    return key


def key_id(key: bytes) -> bytes:
    return hashlib.sha256(key).digest()[:8]


def key_words(key: bytes) -> Tuple[int, int]:
    """key0 and key1: the first two 64-bit words of the key (the other 16 bytes only feed the key id)."""
    return struct.unpack("<QQ", key[:16])


def signed64(v: int) -> int:
    return v - (1 << 64) if v >= (1 << 63) else v


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h = ((h ^ b) * 0x100000001B3) & MASK
    return h


def splitmix64(state: int) -> Tuple[int, int]:
    state = (state + 0x9E3779B97F4A7C15) & MASK
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return state, z ^ (z >> 31)


def keystream(seed: int, key1: int, nbytes: int) -> bytes:
    words = (nbytes + 7) // 8
    out = bytearray(words * 8)
    state = seed
    for i in range(words):
        state, z = splitmix64(state)
        struct.pack_into("<Q", out, i * 8, z ^ key1)
    return bytes(out[:nbytes])


def xor_bytes(a: bytes, b: bytes) -> bytes:
    return (int.from_bytes(a, "little") ^ int.from_bytes(b, "little")).to_bytes(len(a), "little")


def entry_seed(key0: int, nonce: int, name: str) -> int:
    return key0 ^ nonce ^ fnv1a64(name.encode("utf-8"))


def seal(items: Iterable[Tuple[str, bytes]], key: bytes, out_path: str) -> Dict[str, int]:
    """items: (asset path, bytes). Writes the archive; returns path -> size."""
    k0, k1 = key_words(key)
    blobs: List[Tuple[bytes, int, bytes]] = []
    sizes: Dict[str, int] = {}
    for name, data in items:
        nonce = int.from_bytes(hashlib.sha256(name.encode("utf-8") + key).digest()[:8], "little")   # fixed per name: repeatable builds
        enc = xor_bytes(data, keystream(entry_seed(k0, nonce, name), k1, len(data)))
        blobs.append((name.encode("utf-8"), nonce, enc))
        sizes[name] = len(data)
    offset = len(MAGIC) + 8 + 4 + sum(2 + len(n) + 8 + 4 + 8 for n, _, _ in blobs)
    index = bytearray()
    for n, nonce, enc in blobs:
        index += struct.pack("<H", len(n)) + n + struct.pack("<QIQ", offset, len(enc), nonce)
        offset += len(enc)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(MAGIC + key_id(key) + struct.pack("<I", len(blobs)) + index)
        for _, _, enc in blobs:
            f.write(enc)
    return sizes


def read_index(path: str, key: bytes) -> List[Tuple[str, int, int, int]]:
    with open(path, "rb") as f:
        if f.read(len(MAGIC)) != MAGIC:
            raise ValueError("not an MTSA1 archive")
        if f.read(8) != key_id(key):
            raise ValueError("sealed with a different key")
        (count,) = struct.unpack("<I", f.read(4))
        out = []
        for _ in range(count):
            (n,) = struct.unpack("<H", f.read(2))
            name = f.read(n).decode("utf-8")
            offset, size, nonce = struct.unpack("<QIQ", f.read(20))
            out.append((name, offset, size, nonce))
        return out


def unseal_entry(path: str, key: bytes, entry: Tuple[str, int, int, int]) -> bytes:
    name, offset, size, nonce = entry
    k0, k1 = key_words(key)
    with open(path, "rb") as f:
        f.seek(offset)
        enc = f.read(size)
    return xor_bytes(enc, keystream(entry_seed(k0, nonce, name), k1, size))


def collect(mod: str, include: List[str]) -> List[Tuple[str, str]]:
    """(asset path, file path) for every sound under the included folders."""
    out = []
    for folder in include:
        base = os.path.join(mod, folder)
        for root, _, files in os.walk(base):
            for fn in sorted(files):
                if fn.lower().endswith(KINDS):
                    full = os.path.join(root, fn)
                    out.append(("/" + os.path.relpath(full, mod).replace(os.sep, "/"), full))
    return sorted(out)


def lua_script(key: "bytes | None", archive: str) -> str:
    """The self-contained OpenStarbound postLoad script: the reader module plus this archive's key. key=None writes the
    keyless copy that belongs in a repository: it stays idle until a release build installs the key (install-lua --key)."""
    reader = open(os.path.join(HERE, "audio_seal_reader.lua"), encoding="utf-8").read()
    module = reader.replace("return M" + NL, "")
    log = "function(msg) if sb and sb.logInfo then sb.logInfo(msg) else print(msg) end end"
    if key is None:
        footer = ["", "-- ---- installed by audio_seal.py install-lua --no-key: repository copy, no key ----",
                  "-- A release build writes the key here (install-lua --key <release key>); this copy never opens the archive.",
                  "local KEY = nil",
                  'if KEY then M.install(assets, "%s", KEY, %s) end' % (archive, log), ""]
        return module + NL.join(footer)
    k0, k1 = key_words(key)
    kid = "".join("\\%d" % b for b in key_id(key))   # Lua decimal escapes, one per key-id byte
    footer = ["", "-- ---- installed by audio_seal.py install-lua: this mod's archive and key ----",
              'local KEY = { id = "%s", k0 = %d, k1 = %d }' % (kid, signed64(k0), signed64(k1)),
              'M.install(assets, "%s", KEY, %s)' % (archive, log), ""]
    return module + NL.join(footer)


def cpp_key_header(key: bytes, namespaces: Tuple[str, ...] = ("Star", "SealedKey")) -> str:
    """Key and key id as C++ constants, inside the given nested namespaces (Star::SealedKey for the OpenStarbound fork,
    SealedKey alone for the Transcendence engine)."""
    body = ", ".join("0x%02x" % b for b in key)
    kid = ", ".join("0x%02x" % b for b in key_id(key))
    lines = ["// Generated by audio_seal.py write-cpp-key from audio_seal.key. Not in the repository: the sealed sound",
             "// archives (MTSA1) a build can open are the ones sealed with this key (id %s)." % key_id(key).hex(),
             "#pragma once", ""]
    lines += ["namespace %s {" % n for n in namespaces]
    lines += ["  static const unsigned char Key[32] = { %s };" % body, "  static const unsigned char KeyId[8] = { %s };" % kid]
    lines += ["}" for _ in namespaces] + [""]
    return NL.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="seal sounds into an MTSA1 archive")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal"); s.add_argument("mod"); s.add_argument("archive"); s.add_argument("--include", nargs="+", default=["sfx"]); s.add_argument("--key", default=DEFAULT_KEY); s.add_argument("--remove", action="store_true", help="delete the loose files once sealed (release copies)")
    s.add_argument("--embed-key", action="store_true", help="write sounds.key beside the archive, so an engine reader built with another key still opens it (a mod's own key; scrambling, not secrecy)")
    l = sub.add_parser("list"); l.add_argument("archive"); l.add_argument("--key", default=DEFAULT_KEY)
    u = sub.add_parser("unseal"); u.add_argument("archive"); u.add_argument("out"); u.add_argument("--key", default=DEFAULT_KEY)
    i = sub.add_parser("install-lua", help="write the self-contained OpenStarbound postLoad script into a mod and hook it in _metadata")
    i.add_argument("mod"); i.add_argument("--archive", default="/sfx/magitech/sounds.mtsa"); i.add_argument("--script", default="/scripts/magitech/audio_unseal.lua"); i.add_argument("--key", default=DEFAULT_KEY); i.add_argument("--no-key", action="store_true", help="write the keyless repository copy (idle until a release build installs a key)")
    c = sub.add_parser("write-cpp-key", help="write a C++ key header (StarSealedKey.hpp for the OpenStarbound fork, SealedKey.h for Transcendence)"); c.add_argument("header"); c.add_argument("--key", default=DEFAULT_KEY); c.add_argument("--namespace", default="Star::SealedKey", help="nested namespaces, e.g. Star::SealedKey or SealedKey")
    sub.add_parser("keystream-test")
    a = ap.parse_args(argv)
    if a.cmd == "keystream-test":
        key = bytes(range(32))
        k0, k1 = key_words(key)
        seed = entry_seed(k0, 0x0123456789ABCDEF, "/sfx/test.ogg")
        print(json.dumps({"key_hex": key.hex(), "key_id": key_id(key).hex(), "fnv": "%016x" % fnv1a64(b"/sfx/test.ogg"), "seed": "%016x" % seed,
                          "keystream16": keystream(seed, k1, 16).hex(), "xor_hello": xor_bytes(b"hello sealed world", keystream(seed, k1, 18)).hex()}, indent=1))
        return 0
    key = None if (a.cmd == "install-lua" and a.no_key) else load_key(a.key)
    if a.cmd == "seal":
        pairs = collect(a.mod, a.include)
        if not pairs:
            raise SystemExit("no sounds found")
        sizes = seal(((name, open(full, "rb").read()) for name, full in pairs), key, a.archive)
        total = sum(sizes.values())
        print(f"sealed {len(sizes)} sounds, {total / 1048576:.1f} MB -> {a.archive} (key {key_id(key).hex()})")
        if a.embed_key:
            kp = os.path.join(os.path.dirname(os.path.abspath(a.archive)), "sounds.key")
            open(kp, "w", encoding="ascii").write(key.hex() + NL)
            print(f"wrote {kp}: any engine reader opens this archive with it (the key travels with the mod)")
        if a.remove:
            for _, full in pairs:
                os.remove(full)
            print("removed the loose files")
        return 0
    if a.cmd == "list":
        for name, offset, size, nonce in read_index(a.archive, key):
            print(f"{size:9}  {name}")
        return 0
    if a.cmd == "unseal":
        for e in read_index(a.archive, key):
            dest = os.path.join(a.out, e[0].lstrip("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(unseal_entry(a.archive, key, e))
        print(f"unsealed into {a.out}")
        return 0
    if a.cmd == "install-lua":
        dest = os.path.join(a.mod, a.script.lstrip("/").replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8", newline=NL).write(lua_script(None if a.no_key else key, a.archive))
        meta_path = os.path.join(a.mod, "_metadata")
        meta = json.load(open(meta_path, encoding="utf-8"))
        post = meta.setdefault("scripts", {}).setdefault("postLoad", [])
        if a.script not in post:
            post.append(a.script)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=2)
        print(f"wrote {dest} and hooked it as a postLoad script in _metadata")
        return 0
    if a.cmd == "write-cpp-key":
        os.makedirs(os.path.dirname(os.path.abspath(a.header)), exist_ok=True)
        open(a.header, "w", encoding="utf-8", newline=NL).write(cpp_key_header(key, tuple(n for n in a.namespace.split("::") if n)))
        print(f"wrote {a.header} (key id {key_id(key).hex()})")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
