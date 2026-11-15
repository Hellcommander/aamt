"""Raise D2RMM's D2RLoader package size limit (512 MiB by default).

D2RMM checks every D2RLoader package it imports against a hard-coded
ResourceBudget `{maxBytes:536870912,maxDepth:64,maxEntries:1e4}` in
`resources/app.asar`. Large mods (e.g. shattered, ~1.1 GB) fail with
"Resource byte limit exceeded by ...". This script rewrites that number in
place with a same-length value, so no offsets inside the asar move.

Safe to run again after every D2RMM update: an already-patched install is
left alone. A backup of the unpatched file is kept as `app.asar.bak`.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

# The limits object for D2RLoader package imports. Matches the original and a
# patched value (number padded with spaces).
LIMITS = re.compile(rb'maxBytes:([0-9][0-9.e]*)( *),maxDepth:\d+,maxEntries:')
# Electron fuse wire: sentinel, version byte, fuse count, then one char per fuse.
FUSE_SENTINEL = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX'
FUSE_ASAR_INTEGRITY = 4  # EnableEmbeddedAsarIntegrityValidation
BACKUP_SUFFIX = '.bak'
MAX_SEARCH_DEPTH = 4


def compact_number(n):
    """Shortest JS literal for n: plain digits or <m>e<k>."""
    best = str(n)
    m, k = n, 0
    while m and m % 10 == 0:
        m //= 10
        k += 1
        best = min(best, f'{m}e{k}', key=len)
    return best


def find_exe(install_dir):
    for name in os.listdir(install_dir):
        if name.lower().startswith('d2rmm') and name.lower().endswith('.exe'):
            return os.path.join(install_dir, name)
    return None


def find_installs(root):
    """Folders under root that hold a D2RMM*.exe next to resources/app.asar."""
    root = os.path.abspath(root)
    base_depth = root.rstrip(os.sep).count(os.sep)
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        if dirpath.count(os.sep) - base_depth >= MAX_SEARCH_DEPTH:
            dirnames[:] = []
        # never descend into mod content or asar unpack folders
        dirnames[:] = [d for d in dirnames if d.lower() not in ('mods', 'data', 'node_modules', 'app.asar.unpacked')
                       and not d.lower().endswith('.mpq')]
        if os.path.isfile(os.path.join(dirpath, 'resources', 'app.asar')) and find_exe(dirpath):
            found.append(dirpath)
    return found


def is_running(exe):
    name = os.path.basename(exe)
    try:
        out = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {name}', '/NH'],
                             capture_output=True, text=True, check=False).stdout
    except OSError:
        return False
    return name.lower() in out.lower()


def asar_integrity_enabled(exe):
    data = open(exe, 'rb').read()
    i = data.find(FUSE_SENTINEL)
    if i < 0:
        return None
    count = data[i + len(FUSE_SENTINEL) + 1]
    fuses = data[i + len(FUSE_SENTINEL) + 2:i + len(FUSE_SENTINEL) + 2 + count]
    return len(fuses) > FUSE_ASAR_INTEGRITY and fuses[FUSE_ASAR_INTEGRITY:FUSE_ASAR_INTEGRITY + 1] == b'1'


def read_limit(asar_bytes):
    matches = list(LIMITS.finditer(asar_bytes))
    if len(matches) != 1:
        raise RuntimeError(f'expected 1 package limits object, found {len(matches)}; '
                           'this D2RMM version changed the code, the patcher needs updating')
    m = matches[0]
    return m, int(float(m.group(1)))


def process(install, limit, mode):
    exe = find_exe(install)
    asar = os.path.join(install, 'resources', 'app.asar')
    backup = asar + BACKUP_SUFFIX
    print(f'{install}')

    if mode == 'restore':
        if not os.path.isfile(backup):
            raise RuntimeError(f'no backup at {backup}')
        if is_running(exe):
            raise RuntimeError(f'{os.path.basename(exe)} is running; close it first')
        shutil.copy2(backup, asar)
        print(f'  restored from {os.path.basename(backup)}')
        return

    data = open(asar, 'rb').read()
    m, current = read_limit(data)
    print(f'  current limit: {current:,} bytes')
    if current >= limit:
        print('  already at or above the target, nothing to do')
        return
    if mode == 'check':
        print(f'  needs patching to {limit:,}')
        return

    width = len(m.group(1)) + len(m.group(2))
    literal = compact_number(limit)
    if len(literal) > width:
        raise RuntimeError(f'{literal} does not fit in {width} characters')
    if asar_integrity_enabled(exe):
        raise RuntimeError('this D2RMM build validates app.asar integrity; patching it would stop the app starting')
    if is_running(exe):
        raise RuntimeError(f'{os.path.basename(exe)} is running; close it first')

    patched = data[:m.start(1)] + literal.encode().ljust(width) + data[m.end(2):]
    assert len(patched) == len(data)
    shutil.copy2(asar, backup)
    tmp = asar + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(patched)
    os.replace(tmp, asar)
    _, now = read_limit(open(asar, 'rb').read())
    if now != limit:
        shutil.copy2(backup, asar)
        raise RuntimeError('verification failed, original restored')
    print(f'  patched to {now:,} bytes (backup: {os.path.basename(backup)})')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--root', default=os.environ.get('D2R_PATH') or '.',
                    help='folder to search for D2RMM installs (default: D2R_PATH or cwd)')
    ap.add_argument('--install', action='append', default=[],
                    help='a D2RMM install folder (the one holding the .exe); skips the search')
    ap.add_argument('--limit', type=int, default=4_000_000_000, help='new byte limit (default 4e9)')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='report only, change nothing')
    group.add_argument('--restore', action='store_true', help='put app.asar.bak back')
    args = ap.parse_args()

    if not 0 < args.limit <= 2 ** 53 - 1:
        ap.error('--limit must be a positive safe integer')
    installs = args.install or find_installs(args.root)
    if not installs:
        print(f'no D2RMM install found under {os.path.abspath(args.root)}', file=sys.stderr)
        return 1

    mode = 'check' if args.check else 'restore' if args.restore else 'patch'
    failed = 0
    for install in installs:
        try:
            process(install, args.limit, mode)
        except Exception as e:  # report and carry on with other installs
            print(f'  ERROR: {e}', file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
