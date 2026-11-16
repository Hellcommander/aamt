"""Checks the game addresses the D2RLoader plugins hook, and finds them again after an update.

    python PluginAddresses.py check    --mods <game>\\mods [--old <image>] [--new <image>] [--write]
    python PluginAddresses.py selftest --mods <game>\\mods [--old <image>]

The plugins hook routines of the game image that D2RLoader runs, at fixed addresses
(`constexpr std::uint64_t <Name>Rva = 0x...;`), most with the bytes they expect there
(`constexpr std::uint8_t <Name>Expected[] { ... };`). A loader or game update can move them. The
images are memory dumps of that game image, made by the SkillTab4 probe plugin
(<game>\\d2rloader\\data\\skilltab4-probe\\image-<build>.bin, file offset = address).

  check     for every address in every plugin: compares the new image with the expected bytes and
            with the old image. Unchanged addresses pass. For moved ones it takes the function that
            holds the address in the old image (from the image's exception table, .pdata), masks
            the bytes that change when code moves (relative calls, jumps, rip-relative operands),
            finds that function in the new image and reports the new address (and new expected
            bytes when they changed). --write puts the found addresses into the plugin sources.
  selftest  the same search on a copy of the old image with a block of bytes inserted before the
            first hooked routine, so every address moves: each must be found at its moved place.

Addresses in D2RCore.dll (names with "Core") and in data sections are not in the dump or cannot
be found by code; they are listed for checking by hand. Defaults: --old = the image whose bytes
match the plugins' expected bytes best, --new = the newest image.
"""
import argparse
import re
import struct
import sys
from pathlib import Path

try:
    import capstone
except ImportError:  # pragma: no cover
    capstone = None

RVA = re.compile(r'constexpr\s+std::uint64_t\s+(\w+?)Rva\s*=\s*0x([0-9A-Fa-f]+)\s*;')
EXPECTED = re.compile(r'constexpr\s+std::uint8_t\s+(\w+?)Expected\[\]\s*\{([^}]*)\}', re.S)
MAX_SIG = 192  # bytes of a function used to find it again


# ------------------------------------------------------------------ images

class Image:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        pe = struct.unpack_from('<I', self.data, 0x3C)[0]
        if self.data[:2] != b'MZ' or self.data[pe:pe + 4] != b'PE\0\0':
            raise SystemExit('%s: not a PE image dump' % path)
        n_sections = struct.unpack_from('<H', self.data, pe + 6)[0]
        opt_size = struct.unpack_from('<H', self.data, pe + 20)[0]
        opt = pe + 24
        self.sections = []
        for i in range(n_sections):
            s = opt + opt_size + i * 40
            name = self.data[s:s + 8].rstrip(b'\0').decode('latin-1')
            vsize, rva = struct.unpack_from('<II', self.data, s + 8)
            flags = struct.unpack_from('<I', self.data, s + 36)[0]
            self.sections.append((name, rva, vsize, flags))
        exc_rva, exc_size = struct.unpack_from('<II', self.data, opt + 112 + 3 * 8)  # data directory 3
        self.functions = []
        for off in range(exc_rva, exc_rva + exc_size, 12):
            begin, end, _ = struct.unpack_from('<III', self.data, off)
            if begin and end > begin:
                self.functions.append((begin, end))
        self.functions.sort()
        self._starts = [b for b, _ in self.functions]

    def is_code(self, rva):
        return any(rva >= r and rva < r + v and f & 0x20000000 for _, r, v, f in self.sections)

    def section(self, rva):
        for name, r, v, _ in self.sections:
            if r <= rva < r + v:
                return name
        return '?'

    def function_at(self, rva):
        import bisect
        i = bisect.bisect_right(self._starts, rva) - 1
        if i >= 0 and self.functions[i][0] <= rva < self.functions[i][1]:
            return self.functions[i]
        return None

    def code_ranges(self):
        return [(r, r + v) for _, r, v, f in self.sections if f & 0x20000000]


def signature(image, start, length):
    """(pattern bytes, mask) for `length` bytes from `start`: relative operands are wildcards."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    code = image.data[start:start + length + 16]
    pattern, mask = bytearray(), bytearray()
    for ins in md.disasm(code, start):
        if ins.address - start >= length:
            break
        raw = bytearray(ins.bytes)
        keep = bytearray([1] * len(raw))
        ops = ins.operands if hasattr(ins, 'operands') else []
        relative = ins.group(capstone.CS_GRP_BRANCH_RELATIVE) if hasattr(capstone, 'CS_GRP_BRANCH_RELATIVE') else False
        for op in ops:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP and ins.disp_size:
                for k in range(ins.disp_offset, ins.disp_offset + ins.disp_size):
                    keep[k] = 0
            if op.type == capstone.x86.X86_OP_IMM and (relative or ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL)) and ins.imm_size:
                for k in range(ins.imm_offset, ins.imm_offset + ins.imm_size):
                    keep[k] = 0
        pattern += raw
        mask += keep
    return bytes(pattern), bytes(mask)


def search(image, pattern, mask, limit=3):
    """Addresses in code where `pattern` matches (mask 1 = must match), up to `limit` hits."""
    runs, best, cur = [], (0, 0), None
    for i, m in enumerate(mask):
        if m and cur is None:
            cur = i
        if (not m or i == len(mask) - 1) and cur is not None:
            end = i + 1 if m else i
            if end - cur > best[1] - best[0]:
                best = (cur, end)
            cur = None
    anchor = pattern[best[0]:best[1]]
    if len(anchor) < 4:
        return []
    hits = []
    for lo, hi in image.code_ranges():
        pos = image.data.find(anchor, lo + best[0], hi)
        while pos != -1:
            start = pos - best[0]
            seg = image.data[start:start + len(pattern)]
            if len(seg) == len(pattern) and all(not m or a == b for a, b, m in zip(seg, pattern, mask)):
                hits.append(start)
                if len(hits) >= limit:
                    return hits
            pos = image.data.find(anchor, pos + 1, hi)
    return hits


def relocate(old, new, rva):
    """New address of `rva` in `new`, found through its function in `old`: (rva or None, how)."""
    func = old.function_at(rva)
    if func is None:
        return None, 'no function around it in the old image (.pdata)'
    begin, end = func
    offset = rva - begin
    for length in (48, 96, MAX_SIG, max(MAX_SIG, offset + 32)):
        length = min(length, end - begin) if end - begin > 16 else length
        if length <= offset and offset < MAX_SIG * 4:
            length = offset + 16  # include the patch site itself
        pattern, mask = signature(old, begin, length)
        hits = search(new, pattern, mask, limit=8)
        if len(hits) == 1:
            return hits[0] + offset, 'function %#x+%#x found by %d-byte signature' % (begin, offset, len(pattern))
        if not hits:
            return None, 'function %#x (%d bytes) not found: its code changed' % (begin, end - begin)
    # identical copies of the function: keep the one whose neighbours sit at the same distance
    pick = by_neighbours(old, new, func, hits)
    if pick is not None:
        return pick + offset, 'function %#x+%#x: one of %d identical copies, told apart by its neighbours' % (begin, offset, len(hits))
    return None, 'function %#x matches %d places even with %d bytes' % (begin, len(hits), len(pattern))


def by_neighbours(old, new, func, hits):
    """Among identical copies of `func`, the one whose previous or next function in the old image is
    found at the same distance in the new image."""
    i = old.functions.index(func)
    for j in (i - 1, i + 1, i - 2, i + 2):
        if not 0 <= j < len(old.functions):
            continue
        nb, ne = old.functions[j]
        pattern, mask = signature(old, nb, min(64, ne - nb))
        if len(pattern) < 8:
            continue
        good = [h for h in hits if matches_at(new, h + (nb - func[0]), pattern, mask)]
        if len(good) == 1:
            return good[0]
    return None


def matches_at(image, at, pattern, mask):
    seg = image.data[at:at + len(pattern)]
    return len(seg) == len(pattern) and all(not m or a == b for a, b, m in zip(seg, pattern, mask))


# ------------------------------------------------------------------ plugin sources

def sources(mods):
    out = []
    for cpp in sorted(Path(mods).glob('*/*/*.cpp')):
        if cpp.parent.name in ('plugin', 'probe'):
            out.append(cpp)
    return out


def addresses(cpp):
    text = cpp.read_text(encoding='utf-8', errors='replace')
    expected = {}
    for m in EXPECTED.finditer(text):
        body = re.sub(r'//[^\n]*', '', m.group(2))
        expected[m.group(1)] = bytes(int(b, 16) for b in re.findall(r'0x([0-9A-Fa-f]{1,2})\b', body))
    out = []
    for m in RVA.finditer(text):
        name = m.group(1)
        out.append({'name': name, 'rva': int(m.group(2), 16), 'expected': expected.get(name), 'core': 'Core' in name,
                    'span': m.span(2)})
    return out


def loose_addresses(cpp, image, named):
    """Numbers in the code (comments removed) that point into the image's code but are not one of the
    named <Name>Rva constants, e.g. entries of an address table: listed for checking by hand."""
    text = cpp.read_text(encoding='utf-8', errors='replace')
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    text = RVA.sub(' ', text)
    text = EXPECTED.sub(' ', text)
    out = []
    for m in re.finditer(r'\b0x([0-9A-Fa-f]{6,8})\b', text):
        value = int(m.group(1), 16)
        if value not in named and image.is_code(value) and image.function_at(value) and value not in out:
            out.append(value)
    return out


def plugin_name(cpp):
    return cpp.parent.parent.name + ('' if cpp.parent.name == 'plugin' else '/' + cpp.parent.name)


def default_images(game, old, new):
    folder = Path(game) / 'd2rloader' / 'data' / 'skilltab4-probe'
    images = sorted(folder.glob('image-*.bin'), key=lambda p: p.stat().st_mtime)
    if not images and not (old and new):
        raise SystemExit('no image dumps in %s (run the game once with the SkillTab4 probe plugin)' % folder)
    return images, (Path(new) if new else images[-1])


def pick_old(images, all_addresses):
    """The image whose bytes match the plugins' expected bytes best (what the sources were made for)."""
    best, score = None, -1
    for path in images:
        data = path.read_bytes()
        s = sum(1 for _, a in all_addresses if a['expected'] and not a['core']
                and data[a['rva']:a['rva'] + len(a['expected'])] == a['expected'])
        if s > score:
            best, score = path, s
    return best


# ------------------------------------------------------------------ commands

def check(args):
    mods = Path(args.mods)
    found = [(cpp, a) for cpp in sources(mods) for a in addresses(cpp)]
    images, new_path = default_images(mods.parent, args.old, args.new)
    old_path = Path(args.old) if args.old else pick_old(images, found)
    old, new = Image(old_path), (Image(new_path) if Path(new_path) != Path(old_path) else None)
    new = new or old
    print('old image: %s\nnew image: %s\n' % (old_path, new_path))
    edits, problems = {}, 0
    for cpp in sources(mods):
        rows = [a for c, a in found if c == cpp]
        loose = loose_addresses(cpp, old, {a['rva'] for a in rows})
        if not rows and not loose:
            continue
        print(plugin_name(cpp))
        for value in loose:
            same = old.data[value:value + 32] == new.data[value:value + 32]
            if same:
                continue
            moved, how = relocate(old, new, value)
            problems += 1
            print('  %-28s %#010x  %s' % ('(address in a table)', value,
                                         ('MOVED to %#010x: edit by hand (%s)' % (moved, how)) if moved is not None else 'NOT FOUND: ' + how))
        if loose:
            print('  %d other address(es) in tables or code, checked for changes only: %s'
                  % (len(loose), ', '.join('%#x' % v for v in loose[:8]) + (' ...' if len(loose) > 8 else '')))
        for a in rows:
            rva, exp = a['rva'], a['expected']
            label = '  %-28s %#010x' % (a['name'], rva)
            if a['core']:
                print(label + '  D2RCore.dll: not in the game image dump, check by hand')
                continue
            if not old.is_code(rva):
                same = old.data[rva:rva + 16] == new.data[rva:rva + 16]
                print(label + '  data (%s): %s' % (old.section(rva), 'same bytes' if same else 'bytes differ (data changes at run time; check by hand)'))
                continue
            now = new.data[rva:rva + len(exp)] if exp else None
            if exp and now == exp:
                print(label + '  ok')
                continue
            if not exp and old.data[rva:rva + 32] == new.data[rva:rva + 32]:
                print(label + '  ok (no expected bytes; same code as the old image)')
                continue
            moved, how = relocate(old, new, rva)
            if moved is None:
                problems += 1
                print(label + '  NOT FOUND: ' + how)
                continue
            new_exp = new.data[moved:moved + len(exp)] if exp else None
            note = '' if not exp or new_exp == exp else '; expected bytes now ' + ' '.join('%02X' % b for b in new_exp)
            print(label + '  MOVED to %#010x (%s)%s' % (moved, how, note))
            problems += 1
            edits.setdefault(cpp, []).append((a, moved, new_exp))
    if args.write and edits:
        for cpp, changes in edits.items():
            text = cpp.read_text(encoding='utf-8', errors='replace')
            for a, moved, new_exp in sorted(changes, key=lambda c: -c[0]['span'][0]):
                s, e = a['span']
                digits = e - s
                text = text[:s] + ('%0*X' % (digits, moved)) + text[e:]
                if new_exp and new_exp != a['expected']:
                    m = re.search(r'(constexpr\s+std::uint8_t\s+%sExpected\[\]\s*\{)([^}]*)(\})' % re.escape(a['name']), text, re.S)
                    if m:
                        body = ', '.join('0x%02X' % b for b in new_exp)
                        text = text[:m.start(2)] + ' ' + body + ' ' + text[m.end(2):]
            cpp.write_text(text, encoding='utf-8', newline='')
            print('wrote %d address(es) to %s' % (len(changes), cpp))
    print('\n%s' % ('every checked address is where the plugins expect it' if not problems else
                    '%d address(es) moved or not found%s' % (problems, '' if args.write else ' (--write puts found ones into the sources)')))
    return 1 if problems else 0


def selftest(args):
    mods = Path(args.mods)
    found = [(cpp, a) for cpp in sources(mods) for a in addresses(cpp)]
    images, _ = default_images(mods.parent, args.old, None)
    old_path = Path(args.old) if args.old else pick_old(images, found)
    old = Image(old_path)
    code = [a for _, a in found if not a['core'] and old.is_code(a['rva']) and old.function_at(a['rva'])]
    if not code:
        raise SystemExit('no code addresses to test')
    first = min(old.function_at(a['rva'])[0] for a in code)
    shift = 0x1230
    moved = Image.__new__(Image)
    moved.__dict__.update(old.__dict__)
    moved.data = old.data[:first] + b'\xCC' * shift + old.data[first:]
    moved.sections = [(n, r, v + (shift if r <= first < r + v else 0), f) for n, r, v, f in old.sections]
    ok = 0
    for a in code:
        got, how = relocate(old, moved, a['rva'])
        good = got == a['rva'] + shift
        ok += good
        print('  %-28s %#010x -> %s %s' % (a['name'], a['rva'], ('%#010x' % got) if got is not None else 'none', 'ok' if good else 'WRONG (' + how + ')'))
    print('%d of %d addresses found at their moved place (+%#x)' % (ok, len(code), shift))
    return 0 if ok == len(code) else 1


def main():
    if capstone is None:
        raise SystemExit('needs the capstone module (pip install capstone)')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['check', 'selftest'])
    ap.add_argument('--mods', required=True, help="the game's mods folder (plugin sources in <mods>\\<plugin>\\plugin)")
    ap.add_argument('--old', help='image the plugin sources were made for (default: best match)')
    ap.add_argument('--new', help='image to check against (default: the newest dump)')
    ap.add_argument('--write', action='store_true', help='check: put found addresses into the plugin sources')
    args = ap.parse_args()
    sys.exit(check(args) if args.command == 'check' else selftest(args))


if __name__ == '__main__':
    main()
