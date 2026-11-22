"""Shared helpers for the Two Worlds II asset tools: the game's archives, its tagged-tree files, output folders.

The archive and tree readers live with the mod in <TW2>\\_modding\\tools (wdtool.py, chm.py, wmpaths.py), because
the WorldMerge Reforged patcher runs them at build time. This module finds that folder (TW2_MODDING, else the
Steam paths below) and imports them from there, so there is one copy of that code.

GameFS: every file in the game's archives, the copy the game loads.
  - Archives are read in sorted name order (WDFiles, without the archives of DLCs the game doesn't have, as
    wmpaths.game_archives() decides), then Mods\\*.wd. The later copy of a path wins. That is the order the
    _modding build tools assume; it is not confirmed in game.
  - --stock (any tool) or TW2_STOCK=1 leaves Mods\\*.wd out: the unmodded game, e.g. to start textures from stock.
  - Meshes name their textures by bare file name (TexS0 = "WP_SWORD_109.dds"); find_name() looks those up.
Read-only: nothing here writes to the game folder.
"""
import os
import sys

CANDIDATES = [
    os.environ.get('TW2_MODDING', ''),
    r'D:\games\Steam\steamapps\common\Two Worlds II\_modding',
    r'E:\SteamLibrary\steamapps\common\Two Worlds II\_modding',
]
HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.environ.get('TW2_OUTPUT') or os.path.join(HERE, 'Output')
CACHE = os.path.join(OUTPUT, 'cache')
TOOLS_ROOT = os.path.dirname(HERE)                      # ...\Ai assisted toolkit\Tools
SHARED = os.path.join(TOOLS_ROOT, 'Shared')


def modding():
    for c in CANDIDATES:
        if c and os.path.isfile(os.path.join(c, 'tools', 'chm.py')):
            return c
    raise SystemExit('Two Worlds II _modding folder not found: set TW2_MODDING')


MODDING = modding()
GAME = os.path.dirname(MODDING)
sys.path.insert(0, os.path.join(MODDING, 'tools'))
import wdtool  # noqa: E402
import chm  # noqa: E402


def game_archives():
    """Archive paths in load order (later wins)."""
    try:
        cwd = os.getcwd()
        os.chdir(MODDING)                      # wmpaths resolves its build folders relative to _modding
        try:
            import wmpaths
            arcs = [wmpaths.archive_path(n) for n in wmpaths.game_archives()]
        finally:
            os.chdir(cwd)
    except Exception as exc:                    # fall back to every archive in WDFiles
        print('note: wmpaths unavailable (%s); reading every WDFiles archive' % exc, file=sys.stderr)
        wd = os.path.join(GAME, 'WDFiles')
        arcs = [os.path.join(wd, n) for n in sorted(os.listdir(wd)) if n.lower().endswith('.wd')]
    mods = os.path.join(GAME, 'Mods')
    if os.path.isdir(mods):
        arcs += [os.path.join(mods, n) for n in sorted(os.listdir(mods)) if n.lower().endswith('.wd')]
    return arcs


class GameFS:
    """Path -> winning archive entry, over the game's archives (tables only; data is read on demand)."""

    def __init__(self, archives=None, mods=None):
        if mods is None:                      # --stock on any tool (or TW2_STOCK=1): the game without Mods\*.wd
            mods = not os.environ.get('TW2_STOCK')
        self.archives = archives or game_archives()
        if not mods:
            self.archives = [a for a in self.archives if os.sep + 'Mods' + os.sep not in a]
        self.files = {}          # PATH (upper, '\\') -> (archive, entry)
        self.copies = {}         # PATH -> number of archives holding it
        for arc in self.archives:
            with open(arc, 'rb') as f:
                try:
                    tab = wdtool.read_table(f)
                except Exception as exc:
                    print('skip %s: %s' % (os.path.basename(arc), exc), file=sys.stderr)
                    continue
            for e in tab:
                k = e[0].replace('/', '\\').upper()
                self.files[k] = (arc, e)
                self.copies[k] = self.copies.get(k, 0) + 1
        self.by_name = {}
        for k in self.files:
            self.by_name.setdefault(k.rsplit('\\', 1)[-1], []).append(k)
        self._handles = {}

    def _h(self, arc):
        h = self._handles.get(arc)
        if h is None:
            h = self._handles[arc] = open(arc, 'rb')
        return h

    def path(self, p):
        """The stored spelling of a path (any case, / or \\), or None."""
        k = p.replace('/', '\\').upper()
        return self.files[k][1][0] if k in self.files else None

    def read(self, p):
        k = p.replace('/', '\\').upper()
        arc, e = self.files[k]
        return wdtool.read_entry(self._h(arc), e)

    def where(self, p):
        return os.path.basename(self.files[p.replace('/', '\\').upper()][0])

    def find_name(self, name):
        """Full paths of a bare file name (mesh texture references), shortest first."""
        n = name.replace('/', '\\').rsplit('\\', 1)[-1].upper()
        return sorted(self.by_name.get(n, []), key=lambda k: (k.count('\\'), k))

    def resolve(self, ref):
        """A path or bare name -> one stored path (prefers an exact path, then the shortest folder)."""
        if self.path(ref):
            return self.path(ref)
        hits = self.find_name(ref)
        if not hits and not ref.lower().endswith('.dds'):
            hits = self.find_name(ref + '.dds')
        return self.files[hits[0]][1][0] if hits else None

    def glob(self, *exts, contains=''):
        exts = tuple(e.upper() for e in exts)
        c = contains.replace('/', '\\').upper()
        return sorted(self.files[k][1][0] for k in self.files if k.endswith(exts) and c in k)


def take_stock_flag(argv):
    """Remove --stock from argv and set TW2_STOCK, so GameFS leaves Mods\\*.wd out."""
    if '--stock' in argv:
        argv.remove('--stock')
        os.environ['TW2_STOCK'] = '1'
    return argv


def tree(data):
    """Parse a tagged-tree file (.vdf .chv .chm .mtr .DX9 ...) from bytes -> list of chm.Node."""
    if data[:4] != chm.MAGIC:
        raise ValueError('not a tagged-tree file (magic %s)' % data[:4].hex())
    return chm.parse(data, 4, len(data))


def safe_name(p):
    return p.replace('\\', '/').rsplit('/', 1)[-1]


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p
