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

MTSA2 (`seal --sign NAME`): sealed against editing. The game still plays it on every machine; nobody can change it.

    "MTSA2\\0"  8 bytes key id  u32 count
    per entry: u16 nameLen, UTF-8 asset path, u64 offset, u32 size (plaintext), 12 bytes nonce
    data:      AES-256-GCM(key, nonce, aad = "MTSA2\\0" + key id + path) ciphertext, then the 16-byte tag
    trailer:   signer public key (ECDSA P-256, X||Y, 64 bytes), signature (r||s, 64 bytes) over everything before it

The audio is encrypted with the reader's key (the one compiled into the plugin, as for MTSA1), so the game decrypts it
in memory anywhere and it never sits on disk in the clear. The archive is signed with a private key that stays in the
local key store (%LOCALAPPDATA%/SealedAudio/keys/NAME.signkey, made on first use, never shipped): a reader refuses an
archive whose signature does not verify, so changing one byte of it makes the game refuse it. A plugin built with the
author's public key (`write-cpp-signer`, SealedSigner.h) also refuses an archive re-signed by anyone else.
`unseal` refuses MTSA2 unless --recover is given (your own copy back after losing the originals).

Per-game keys: every game (or engine build) has its own build key, `--game NAME`, kept in %LOCALAPPDATA%/SealedAudio/game-keys/NAME.key
(made on first use, never in the repository or a mod). There is no shared default key: a key that opened archives for several
games would unlock all of them once it leaked. `rekey` moves an archive to another key without writing a sound to disk.

Local key store: `--local-key NAME` seals with %LOCALAPPDATA%/SealedAudio/keys/NAME.key (made on first use), a key that
stays on this machine. The SealedAudio core (1.3+) looks there for a key whose id matches an archive, so the archive
plays here and nowhere the key was not copied to; nothing in the mod or its zip can open it.

Usage: python audio_seal.py seal <mod folder> <archive> [--include sfx interface/magitech/sounds] [--map sources.json] [--game NAME | --key file | --local-key NAME] [--sign NAME] [--remove]
       python audio_seal.py rekey <archive> --from-key <old key file> --game NAME [--sign NAME]  (in place; MTSA2 needs --sign)
       python audio_seal.py list <archive> [--game NAME | --key file | --local-key NAME]
       python audio_seal.py verify <archive> [--signer NAME]  (MTSA2: is it unedited, and who signed it)
       python audio_seal.py unseal <archive> <out folder> [--game NAME | --key file | --local-key NAME] [--recover]
       python audio_seal.py write-cpp-signer <SealedSigner.h> --sign NAME  (pins the plugin to your signing key)
       python audio_seal.py keys                           (the local key store: names, key ids, and which archive a key opens)
       python audio_seal.py install-lua <mod folder> [--archive /sfx/magitech/sounds.mtsa] [--script /scripts/magitech/audio_unseal.lua] [--game NAME | --key file | --no-key]
       python audio_seal.py write-cpp-key <StarSealedKey.hpp> --game NAME [--namespace SealedKey]
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
MAGIC2 = b"MTSA2\0"
GCM_TAG = 16
MASK = (1 << 64) - 1
HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = (".ogg", ".wav", ".mp3", ".flac")
NL = chr(10)


def key_store() -> str:
    """The per-user key store the SealedAudio core searches by default (sa_config.key_dirs NULL)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "SealedAudio", "keys")


def plain_name(name: str, flag: str) -> str:
    if not name or any(c in name for c in '\\/:*?"<>|') or name in (".", ".."):
        raise SystemExit(f"{flag}: {name!r} is not a plain name (letters, digits, - and _ are safe)")
    return name


def local_key_path(name: str) -> str:
    return os.path.join(key_store(), plain_name(name, "--local-key") + ".key")


def game_key_dir() -> str:
    """Build keys, one per game: the key a game's reader (plugin, engine fork or Lua script) is built with."""
    return os.path.join(os.path.dirname(key_store()), "game-keys")


def game_key_path(name: str) -> str:
    return os.path.join(game_key_dir(), plain_name(name, "--game") + ".key")


def inside(path: str, folder: str) -> bool:
    p, f = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def archive_key_id(path: str) -> bytes:
    with open(path, "rb") as f:
        head = f.read(14)
    if len(head) < 14 or head[:6] not in (MAGIC, MAGIC2):
        raise ValueError("not an MTSA1/MTSA2 archive")
    return head[6:14]


def archive_format(path: str) -> int:
    with open(path, "rb") as f:
        head = f.read(6)
    return 2 if head == MAGIC2 else 1 if head == MAGIC else 0


def aesgcm(key: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise SystemExit("MTSA2 needs the 'cryptography' package: python -m pip install cryptography")
    return AESGCM(key)


def entry_aad(key: bytes, name: str) -> bytes:
    return MAGIC2 + key_id(key) + name.encode("utf-8")


# ---- MTSA2 signing: ECDSA P-256 / SHA-256, raw 64-byte public keys and signatures (what Windows CNG takes) ----------

SIG_TRAILER = 128


def _ec():
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, utils
    except ImportError:
        raise SystemExit("MTSA2 needs the 'cryptography' package: python -m pip install cryptography")
    return hashes, serialization, ec, utils


def signing_key_path(name: str) -> str:
    return local_key_path(name)[:-4] + ".signkey"


def load_signing_key(name: str, create: bool = True):
    hashes, serialization, ec, _ = _ec()
    path = signing_key_path(name)
    if not os.path.exists(path):
        if not create:
            raise SystemExit(f"no signing key named {name!r} ({path})")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        priv = ec.generate_private_key(ec.SECP256R1())
        with open(path, "wb") as f:
            f.write(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        print(f"made a new signing key: {path} (stays on this machine; back it up privately: only it can sign new versions)")
    return serialization.load_pem_private_key(open(path, "rb").read(), password=None)


def public_raw(priv) -> bytes:
    n = priv.public_key().public_numbers()
    return n.x.to_bytes(32, "big") + n.y.to_bytes(32, "big")


def signer_id(pub64: bytes) -> str:
    return hashlib.sha256(pub64).digest()[:8].hex()


def sign_raw(priv, data: bytes) -> bytes:
    hashes, _, ec, utils = _ec()
    r, s = utils.decode_dss_signature(priv.sign(data, ec.ECDSA(hashes.SHA256())))
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def verify_raw(pub64: bytes, data: bytes, sig64: bytes) -> bool:
    hashes, _, ec, utils = _ec()
    try:
        pub = ec.EllipticCurvePublicNumbers(int.from_bytes(pub64[:32], "big"), int.from_bytes(pub64[32:], "big"), ec.SECP256R1()).public_key()
        pub.verify(utils.encode_dss_signature(int.from_bytes(sig64[:32], "big"), int.from_bytes(sig64[32:], "big")), data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def archive_signature(path: str) -> Tuple[str, bool]:
    """MTSA2: (signer id, signature valid)."""
    blob = open(path, "rb").read()
    if blob[:6] != MAGIC2 or len(blob) < 18 + SIG_TRAILER:
        raise ValueError("not an MTSA2 archive")
    pub, sig = blob[-128:-64], blob[-64:]
    return signer_id(pub), verify_raw(pub, blob[:-64], sig)


def load_key(path: "str | None" = None, local: bool = False) -> bytes:
    if not path:
        raise SystemExit("no key named: there is no shared default key any more. Pass a key file, or use game_key_path('NAME') "
                         "(audio_seal.py --game NAME) for this game's own key")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="ascii") as f:
            f.write(os.urandom(32).hex() + NL)
        if local:
            print(f"made a new local key: {path} (back it up privately; without it the archive cannot be opened)")
        else:
            print(f"made a new seal key: {path} (keep it out of the repository; the game's reader is built with this key)")
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


def seal2(items: Iterable[Tuple[str, bytes]], key: bytes, out_path: str, signer) -> Dict[str, int]:
    """MTSA2: AES-256-GCM per entry, signed by `signer` (a P-256 private key). Returns path -> size."""
    aes = aesgcm(key)
    blobs: List[Tuple[bytes, int, bytes, bytes]] = []
    sizes: Dict[str, int] = {}
    for name, data in items:
        nonce = os.urandom(12)
        blobs.append((name.encode("utf-8"), len(data), nonce, aes.encrypt(nonce, data, entry_aad(key, name))))
        sizes[name] = len(data)
    offset = len(MAGIC2) + 8 + 4 + sum(2 + len(n) + 8 + 4 + 12 for n, _, _, _ in blobs)
    index = bytearray()
    for n, size, nonce, enc in blobs:
        index += struct.pack("<H", len(n)) + n + struct.pack("<QI", offset, size) + nonce
        offset += len(enc)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    body = bytearray(MAGIC2 + key_id(key) + struct.pack("<I", len(blobs)) + index)
    for _, _, _, enc in blobs:
        body += enc
    body += public_raw(signer)
    body += sign_raw(signer, bytes(body))
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, out_path)
    return sizes


def seal(items: Iterable[Tuple[str, bytes]], key: bytes, out_path: str, signer=None) -> Dict[str, int]:
    """items: (asset path, bytes). Writes the archive (MTSA2 when `signer` is given); returns path -> size."""
    if signer is not None:
        return seal2(items, key, out_path, signer)
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


def read_index(path: str, key: bytes) -> List[tuple]:
    """(name, offset, size, nonce) per entry; nonce is an int (MTSA1) or 12 bytes (MTSA2), size the plaintext size."""
    with open(path, "rb") as f:
        magic = f.read(len(MAGIC))
        if magic not in (MAGIC, MAGIC2):
            raise ValueError("not an MTSA1/MTSA2 archive")
        if f.read(8) != key_id(key):
            raise ValueError("sealed with a different key")
        (count,) = struct.unpack("<I", f.read(4))
        out = []
        for _ in range(count):
            (n,) = struct.unpack("<H", f.read(2))
            name = f.read(n).decode("utf-8")
            if magic == MAGIC2:
                offset, size = struct.unpack("<QI", f.read(12))
                out.append((name, offset, size, f.read(12)))
            else:
                out.append((name,) + struct.unpack("<QIQ", f.read(20)))
        return out


def unseal_entry(path: str, key: bytes, entry: tuple) -> bytes:
    name, offset, size, nonce = entry
    if isinstance(nonce, bytes):  # MTSA2
        with open(path, "rb") as f:
            f.seek(offset)
            enc = f.read(size + GCM_TAG)
        try:
            return aesgcm(key).decrypt(nonce, enc, entry_aad(key, name))
        except Exception:
            raise SystemExit(f"{name}: authentication failed (the archive was altered or the key is wrong)")
    k0, k1 = key_words(key)
    with open(path, "rb") as f:
        f.seek(offset)
        enc = f.read(size)
    return xor_bytes(enc, keystream(entry_seed(k0, nonce, name), k1, size))


def library_roots() -> List[str]:
    """The licensed sound libraries: sources only, never written to or deleted from (AAMT_AUDIO_LIBRARY, ; separated)."""
    return [p for p in os.environ.get("AAMT_AUDIO_LIBRARY", r"D:\assets\audio").split(os.pathsep) if p]


def collect_map(map_file: str) -> List[Tuple[str, str]]:
    """(asset path, file path) from a JSON object {"/hd/global/sfx/x.flac": "D:/assets/audio/made/impact/a.wav", ...}:
    seal straight from the licensed library, so the licensed files are never copied loose into the mod. Relative
    sources resolve against the map file's folder."""
    base = os.path.dirname(os.path.abspath(map_file))
    out = []
    for name, src in json.load(open(map_file, encoding="utf-8-sig")).items():  # -sig: PowerShell writes a BOM
        full = src if os.path.isabs(src) else os.path.join(base, src)
        if not os.path.isfile(full):
            raise SystemExit(f"--map: {name} -> {full}: no such file")
        out.append(("/" + name.replace("\\", "/").lstrip("/"), full))
    return sorted(out)


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
    lines = ["// Generated by audio_seal.py write-cpp-key from a per-game key. Not in the repository: the sealed sound",
             "// archives (MTSA1) a build can open are the ones sealed with this key (id %s)." % key_id(key).hex(),
             "#pragma once", ""]
    lines += ["namespace %s {" % n for n in namespaces]
    lines += ["  static const unsigned char Key[32] = { %s };" % body, "  static const unsigned char KeyId[8] = { %s };" % kid]
    lines += ["}" for _ in namespaces] + [""]
    return NL.join(lines)


AUDIT_SKIP_DIRS = {".git", "node_modules", ".vs", "__pycache__"}
AUDIT_SCAN_EXT = (".exe", ".dll", ".h", ".hpp", ".lua", ".key", ".js", ".cs", ".py")  # files that can carry a key
AUDIT_MAX_BYTES = 200_000_000


def retired_dir() -> str:
    """Keys taken out of service (leaked): every copy of one is a finding."""
    return os.path.join(os.path.dirname(key_store()), "retired")


def _key_files(folder: str) -> Dict[str, bytes]:
    out = {}
    if os.path.isdir(folder):
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith(".key"):
                try:
                    out[fn[:-4]] = bytes.fromhex(open(os.path.join(folder, fn), encoding="ascii").read().strip())
                except ValueError:
                    pass
    return out


def audit(roots: List[str], binaries: bool = True) -> int:
    """One pass, terse output, for agents billed per token: prints only findings and a one-line summary.
    Findings: archives on a retired or unknown key, retired key material in any build file or header, key files inside
    the scanned trees, and loose sound files that duplicate an entry of a sealed archive (the license forbids loose
    copies). Reads only archive headers/indexes and files that can carry a key, never every file."""
    retired = _key_files(retired_dir())
    known = {key_id(k): f"game:{n}" for n, k in _key_files(game_key_dir()).items()}
    known.update({key_id(k): f"local:{n}" for n, k in _key_files(key_store()).items()})
    keys_by_id = {key_id(k): k for k in list(_key_files(game_key_dir()).values()) + list(_key_files(key_store()).values())}
    retired_ids = {key_id(k): n for n, k in retired.items()}
    pats = []
    for n, k in retired.items():
        k0, k1 = key_words(k)
        pats += [(n, k), (n, k.hex().encode()), (n, ", ".join("0x%02x" % b for b in k).encode()),
                 (n, ("k0 = %d, k1 = %d" % (signed64(k0), signed64(k1))).encode())]
    store_dirs = [os.path.dirname(key_store())]
    findings, counts = [], {"archives": 0, "scanned": 0}
    sealed = {}       # (basename lower, size) -> archive, for loose-copy detection
    loose = []
    for root in roots:
        if not os.path.exists(root):
            findings.append(f"MISSING  {root}")
            continue
        for d, ds, fs in os.walk(root):
            ds[:] = [x for x in ds if x not in AUDIT_SKIP_DIRS]
            for fn in fs:
                p = os.path.join(d, fn)
                low = fn.lower()
                if low.endswith(".mtsa"):
                    counts["archives"] += 1
                    try:
                        kid = archive_key_id(p)
                    except (OSError, ValueError) as e:
                        findings.append(f"BAD-ARCHIVE  {p}  ({e})")
                        continue
                    if kid in retired_ids:
                        findings.append(f"LEAKED-KEY-ARCHIVE  {p}  (key {retired_ids[kid]})")
                    elif kid not in known:
                        findings.append(f"UNKNOWN-KEY-ARCHIVE  {p}  (id {kid.hex()}, no local key opens it)")
                    else:
                        try:
                            for e in read_index(p, keys_by_id[kid]):
                                sealed[(e[0].rsplit("/", 1)[-1].lower(), e[2])] = p
                        except (OSError, ValueError, struct.error):
                            findings.append(f"BAD-INDEX  {p}")
                    continue
                if low.endswith(KINDS):
                    loose.append(p)
                    continue
                if low.endswith((".key", ".signkey")) and not any(inside(p, s) for s in store_dirs):
                    findings.append(f"KEY-FILE-IN-TREE  {p}")
                if not pats or not low.endswith(AUDIT_SCAN_EXT) or (not binaries and low.endswith((".exe", ".dll"))):
                    continue
                try:
                    if os.path.getsize(p) > AUDIT_MAX_BYTES:
                        continue
                    b = open(p, "rb").read()
                except OSError:
                    continue
                counts["scanned"] += 1
                hit = next((n for n, pat in pats if pat in b), None)
                if hit:
                    findings.append(f"LEAKED-KEY-BYTES  {p}  (key {hit})")
    groups: Dict[Tuple[str, str], List[str]] = {}   # (folder, archive) -> file names: one line per folder, few tokens
    for p in loose:
        try:
            arch = sealed.get((os.path.basename(p).lower(), os.path.getsize(p)))
        except OSError:
            continue
        if arch:
            groups.setdefault((os.path.dirname(p), arch), []).append(os.path.basename(p))
    dupes = sum(len(v) for v in groups.values())
    for (folder, arch), names in sorted(groups.items()):
        shown = ", ".join(sorted(names)[:5]) + (", ..." if len(names) > 5 else "")
        findings.append(f"LOOSE-COPY x{len(names)}  {folder}  ({shown}; also sealed in {os.path.basename(arch)})")
    for f in findings:
        print(f)
    print(f"audit: {len(findings)} finding(s); {counts['archives']} archive(s), {counts['scanned']} key-capable file(s) "
          f"scanned, {len(loose)} loose sound(s) ({dupes} duplicate sealed entries), {len(retired)} retired key(s)")
    return 1 if findings else 0


GAME_HELP = "this game's own build key,%%LOCALAPPDATA%%/SealedAudio/game-keys/NAME.key (made on first use by seal, install-lua and write-cpp-key)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="seal sounds into an MTSA1 / MTSA2 archive")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal"); s.add_argument("mod"); s.add_argument("archive"); s.add_argument("--include", nargs="+", default=["sfx"]); s.add_argument("--key"); s.add_argument("--game", metavar="NAME", help=GAME_HELP); s.add_argument("--remove", action="store_true", help="delete the loose files once sealed (release copies)")
    s.add_argument("--local-key", metavar="NAME", help="seal with the local key store's NAME.key (made on first use; never written into the mod)")
    s.add_argument("--embed-key", action="store_true", help="write sounds.key beside the archive, so an engine reader built with another key still opens it (a mod's own key; scrambling, not secrecy)")
    s.add_argument("--map", metavar="JSON", help="seal the files a JSON object names ({asset path: source file}, e.g. sources in the licensed library) instead of the mod's --include folders")
    s.add_argument("--sign", metavar="NAME", help="MTSA2: AES-256-GCM, signed with the local signing key NAME.signkey (made on first use, never shipped); the game refuses an edited archive")
    v = sub.add_parser("verify", help="MTSA2: check the signature (is the archive unedited) and show the signer"); v.add_argument("archive"); v.add_argument("--signer", metavar="NAME", help="also require this local signing key to be the signer")
    w = sub.add_parser("write-cpp-signer", help="write SealedSigner.h: a plugin built with it accepts only archives signed by NAME"); w.add_argument("header"); w.add_argument("--sign", metavar="NAME", required=True)
    l = sub.add_parser("list"); l.add_argument("archive"); l.add_argument("--key"); l.add_argument("--game", metavar="NAME", help=GAME_HELP); l.add_argument("--local-key", metavar="NAME")
    u = sub.add_parser("unseal"); u.add_argument("archive"); u.add_argument("out"); u.add_argument("--key"); u.add_argument("--game", metavar="NAME", help=GAME_HELP); u.add_argument("--local-key", metavar="NAME")
    r = sub.add_parser("rekey", help="re-encrypt an archive under another key, in place, without writing a sound to disk"); r.add_argument("archive"); r.add_argument("--from-key", metavar="FILE", required=True, help="the key file the archive is sealed with now"); r.add_argument("--key"); r.add_argument("--game", metavar="NAME", help="the new per-game key"); r.add_argument("--sign", metavar="NAME", help="MTSA2: the signing key for the new archive")
    u.add_argument("--recover", action="store_true", help="write an MTSA2 archive's sounds to disk in the clear (your own recovery copy)")
    k = sub.add_parser("keys", help="list the local key store"); k.add_argument("--archive", help="also say which key opens this archive")
    i = sub.add_parser("install-lua", help="write the self-contained OpenStarbound postLoad script into a mod and hook it in _metadata")
    i.add_argument("mod"); i.add_argument("--archive", default="/sfx/magitech/sounds.mtsa"); i.add_argument("--script", default="/scripts/magitech/audio_unseal.lua"); i.add_argument("--key"); i.add_argument("--game", metavar="NAME", help=GAME_HELP); i.add_argument("--no-key", action="store_true", help="write the keyless repository copy (idle until a release build installs a key)")
    c = sub.add_parser("write-cpp-key", help="write a C++ key header (StarSealedKey.hpp for the OpenStarbound fork, SealedKey.h for Transcendence)"); c.add_argument("header"); c.add_argument("--key"); c.add_argument("--game", metavar="NAME", help=GAME_HELP); c.add_argument("--namespace", default="Star::SealedKey", help="nested namespaces, e.g. Star::SealedKey or SealedKey")
    sub.add_parser("keystream-test")
    au = sub.add_parser("audit", help="one terse pass over mod/game/source folders: leaked or unknown keys, key files, loose copies of sealed sounds (exit 1 on findings)")
    au.add_argument("roots", nargs="+"); au.add_argument("--no-binaries", action="store_true", help="skip .exe/.dll (faster)")
    a = ap.parse_args(argv)
    if a.cmd == "audit":
        return audit(a.roots, not a.no_binaries)
    if a.cmd == "keystream-test":
        key = bytes(range(32))
        k0, k1 = key_words(key)
        seed = entry_seed(k0, 0x0123456789ABCDEF, "/sfx/test.ogg")
        print(json.dumps({"key_hex": key.hex(), "key_id": key_id(key).hex(), "fnv": "%016x" % fnv1a64(b"/sfx/test.ogg"), "seed": "%016x" % seed,
                          "keystream16": keystream(seed, k1, 16).hex(), "xor_hello": xor_bytes(b"hello sealed world", keystream(seed, k1, 18)).hex()}, indent=1))
        return 0
    if a.cmd == "keys":
        store = key_store()
        want = archive_key_id(a.archive) if a.archive else None
        names = sorted(f for f in os.listdir(store) if f.lower().endswith(".key")) if os.path.isdir(store) else []
        print(f"key store: {store} ({len(names)} key(s))")
        found = False
        for fn in names:
            try:
                kid = key_id(load_key(os.path.join(store, fn)))
            except (SystemExit, ValueError):
                print(f"  {fn[:-4]:24} (not 64 hex characters)")
                continue
            mark = "  <- opens the archive" if want == kid else ""
            found = found or bool(mark)
            print(f"  {fn[:-4]:24} {kid.hex()}{mark}")
        gdir = game_key_dir()
        gnames = sorted(f for f in os.listdir(gdir) if f.lower().endswith(".key")) if os.path.isdir(gdir) else []
        print(f"game keys: {gdir} ({len(gnames)} key(s))")
        for fn in gnames:
            try:
                kid = key_id(load_key(os.path.join(gdir, fn)))
            except (SystemExit, ValueError):
                print(f"  {fn[:-4]:24} (not 64 hex characters)")
                continue
            mark = "  <- opens the archive" if want == kid else ""
            found = found or bool(mark)
            print(f"  {fn[:-4]:24} {kid.hex()}{mark}")
        signers = sorted(f for f in os.listdir(store) if f.lower().endswith(".signkey")) if os.path.isdir(store) else []
        for fn in signers:
            print(f"  {fn[:-8]:24} signing key, signer id {signer_id(public_raw(load_signing_key(fn[:-8], create=False)))}")
        if want is not None and not found:
            print(f"no key here opens {a.archive} (its key id is {want.hex()})")
            return 1
        return 0
    if a.cmd == "verify":
        sid, ok = archive_signature(a.archive)
        print(f"{a.archive}: signature {'valid' if ok else 'INVALID (the archive was edited)'}, signer id {sid}")
        if a.signer:
            want_sid = signer_id(public_raw(load_signing_key(a.signer, create=False)))
            if want_sid != sid:
                print(f"signed by someone else: expected {a.signer} ({want_sid})")
                return 1
        return 0 if ok else 1
    if a.cmd == "write-cpp-signer":
        pub = public_raw(load_signing_key(a.sign, create=False))
        body = ", ".join("0x%02x" % b for b in pub)
        os.makedirs(os.path.dirname(os.path.abspath(a.header)), exist_ok=True)
        open(a.header, "w", encoding="utf-8", newline=NL).write(NL.join([
            "// Generated by audio_seal.py write-cpp-signer. A public key (safe to ship): a reader built with it accepts only",
            "// MTSA2 archives signed by %s (signer id %s)." % (a.sign, signer_id(pub)),
            "#pragma once", "", "namespace SealedSigner {", "  static const unsigned char PublicKey[64] = { %s };" % body, "}", ""]))
        print(f"wrote {a.header} (signer id {signer_id(pub)})")
        return 0
    if getattr(a, "game", None):
        if a.key or getattr(a, "local_key", None):
            raise SystemExit("--game, --key and --local-key each choose the key: give only one")
        a.key = game_key_path(a.game)
        if not os.path.exists(a.key) and a.cmd in ("list", "unseal"):
            raise SystemExit(f"no game key named {a.game!r} ({a.key})")
    if not a.key and not getattr(a, "local_key", None) and not (a.cmd == "install-lua" and a.no_key):
        raise SystemExit("name the key: --game NAME (this game's own key), --key FILE or --local-key NAME. There is no shared "
                         "default key: one key opening every game's archives would unlock them all once it leaked")
    if getattr(a, "local_key", None):
        if getattr(a, "embed_key", False):
            raise SystemExit("--local-key and --embed-key contradict each other: a local key must not travel with the mod")
        if getattr(a, "sign", None):
            raise SystemExit("--sign encrypts with the reader's key so every player's game plays the sounds; with --local-key "
                             "they would play only on this machine. Drop --local-key: the signing key is what stays here")
        a.key = local_key_path(a.local_key)
        if not os.path.exists(a.key) and a.cmd != "seal":
            raise SystemExit(f"no local key named {a.local_key!r} ({a.key})")
        os.makedirs(os.path.dirname(a.key), exist_ok=True)
    if a.cmd == "seal" and (inside(a.key, a.mod) or inside(a.key, os.path.dirname(os.path.abspath(a.archive)))) and (a.local_key or not os.path.exists(a.key)):
        raise SystemExit(f"refusing to make a key inside the mod or beside the archive ({a.key}): it would ship with the mod")
    if a.cmd == "unseal" and archive_format(a.archive) == 2 and not a.recover:
        raise SystemExit("this is an MTSA2 archive: its sounds are decrypted only in memory by the game. "
                         "Writing them to disk in the clear needs --recover")
    key = None if (a.cmd == "install-lua" and a.no_key) else load_key(a.key, bool(getattr(a, "local_key", None)))
    if a.cmd == "rekey":
        if not os.path.isfile(a.from_key):
            raise SystemExit(f"--from-key: {a.from_key} does not exist")
        old = bytes.fromhex(open(a.from_key, encoding="ascii").read().strip())
        fmt = archive_format(a.archive)
        if not fmt:
            raise SystemExit(f"{a.archive} is not an MTSA1/MTSA2 archive")
        if fmt == 2 and not a.sign:
            raise SystemExit("this is an MTSA2 archive: rekeying it signs a new archive, so name the signing key with --sign")
        if old == key:
            raise SystemExit("the new key is the key the archive already has")
        items = [(e[0], unseal_entry(a.archive, old, e)) for e in read_index(a.archive, old)]   # in memory only
        signer = load_signing_key(a.sign) if a.sign else None
        tmp = a.archive + ".rekey.tmp"
        seal(items, key, tmp, signer)
        fresh = {e[0]: e for e in read_index(tmp, key)}
        if len(fresh) != len(items) or any(unseal_entry(tmp, key, fresh[n]) != d for n, d in items):
            os.remove(tmp)
            raise SystemExit("the rekeyed archive does not decrypt back to the original sounds; the archive is unchanged")
        os.replace(tmp, a.archive)
        print(f"rekeyed {len(items)} sounds in {a.archive}: key {key_id(old).hex()} -> {key_id(key).hex()} (verified, no sound was written to disk)")
        return 0
    if a.cmd == "seal":
        pairs = collect_map(a.map) if a.map else collect(a.mod, a.include)
        if not pairs:
            raise SystemExit("no sounds found")
        signer = load_signing_key(a.sign) if a.sign else None
        sizes = seal(((name, open(full, "rb").read()) for name, full in pairs), key, a.archive, signer)
        total = sum(sizes.values())
        kind = f"MTSA2, AES-256-GCM, signed by {a.sign} ({signer_id(public_raw(signer))})" if signer else "MTSA1"
        print(f"sealed {len(sizes)} sounds, {total / 1048576:.1f} MB -> {a.archive} ({kind}, key {key_id(key).hex()})")
        if signer:
            if not archive_signature(a.archive)[1]:
                raise SystemExit("the new archive's signature does not verify; loose files kept")
            entries = {e[0]: e for e in read_index(a.archive, key)}
            for name, full in pairs:  # every entry decrypts back to its source before anything is removed
                if unseal_entry(a.archive, key, entries[name]) != open(full, "rb").read():
                    raise SystemExit(f"verification failed for {name}; loose files kept")
            print(f"verified: signature valid, every entry decrypts back to its source; signing key {signing_key_path(a.sign)} stays here")
        if a.local_key:
            print(f"key: {a.key} (local key store; it stays on this machine and is not part of the mod)")
        if a.embed_key:
            kp = os.path.join(os.path.dirname(os.path.abspath(a.archive)), "sounds.key")
            open(kp, "w", encoding="ascii").write(key.hex() + NL)
            print(f"wrote {kp}: any engine reader opens this archive with it (the key travels with the mod)")
        if a.remove:
            removed = 0
            for _, full in pairs:
                if any(inside(full, root) for root in library_roots()):
                    print(f"kept {full}: it is in the licensed library ({os.pathsep.join(library_roots())}), never deleted")
                    continue
                os.remove(full)
                removed += 1
            print(f"removed {removed} loose file(s)")
        return 0
    if a.cmd == "list":
        for name, offset, size, nonce in read_index(a.archive, key):  # names and sizes only; nothing is decrypted
            print(f"{size:9}  {name}")
        return 0
    if a.cmd == "unseal":
        if archive_format(a.archive) == 2 and not archive_signature(a.archive)[1]:
            print("warning: the signature does not verify (the archive was edited); the game would refuse it")
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
