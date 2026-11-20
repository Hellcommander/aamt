"""Converter for Diablo II: Resurrected data mods (whole-file overrides) into D2RMM mods.

Starts a small local web server and serves ModConverter.html. The page:
  - Convert: takes a mod folder, a .zip / .7z / .rar download or a packed .mpq, finds the mod's
    data (<Name>.mpq\\data with modinfo.json, or data\\) and its d2rloader folder, shows what it
    changes per feature, puts it into D2RMM's mods folder and runs ConvertDataMod.py on it:
    tables and strings are patched row by row, every feature and every D2RLoader plugin gets an
    on/off switch in the mod's D2RMM settings, plugins can also become their own D2RLoader
    packages (D2RMM's Plugins tab).
  - Update: takes the new download of a mod converted before, keeps the old files in
    <mod>\\d2rmm\\previous, puts the new ones in place and converts again with the settings the
    mod was converted with (convert.json). If the conversion fails, the old files come back.
D2RLoader itself (D2RLoader.exe, D2RCore.dll...) inside a download is left out: D2RMM's
loader is the one that runs.

  Update also turns the plugins and patches of the download's other d2rloader folder (the one a
  D2RLoader install has beside mods\\) into D2RMM packages, and for a mod made from compiled
  tables (<mod>\\d2rmm\\update.json, method merge-compiled: Rebirth) merges the new tables first
  (MergeCompiledMod.py).

usage:
  ModConverter.py --game <D2R folder> [--d2rmm <D2RMM folder>] [--port 8766] [--no-browser]
  ModConverter.py --game <D2R folder> --update <mod id> [--update <mod id>...] [--source <download>]
                  [--match-trim | --no-match-trim] [--duplicates content|order] [--deleted disable|leave]
                  [--conflicts mod|earlier] [--files overwrite|keep] [--base-rows stubs|leave]
      (no page: updates the mods from --source, or from the download each was converted from;
       the row-matching options replace the ones the mod was converted with)
  ModConverter.py --game <D2R folder> --convert <download> [--id <mod id>] [--name N] [--author A]
                  [--version V] [--rows keep|rebuild] [--plugins mod|packages] (+ the options above)
      (no page: the page's Convert; the download is remembered, so --update <mod id> redoes it)

Only this computer can reach the server (it listens on 127.0.0.1).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ConvertDataMod  # noqa: E402  (feature table)

ARCHIVES = ('.zip', '.7z', '.rar')
LOADER_BINARIES = {'d2rloader.exe', 'd2rcore.dll', 'd2r_loader.dll', 'd2rloader.mpq'}


# --------------------------------------------------------------------------- places

def find_d2rmm(game):
    """D2RMM's folder: the one beside or inside the game folder that has mods\\ and the app."""
    for cand in [game] + sorted(p for p in game.iterdir() if p.is_dir()):
        if (cand / 'mods').is_dir() and any((cand / n).exists() for n in ('D2RMM Custom.exe', 'D2RMM.exe', 'types.d.ts')):
            return cand
    return None


def make_writable(root):
    """Clears read-only flags under a folder; returns how many were set. Some downloads (Reimagined
    3.1.1's zip) record every folder as read-only, and Windows will not rename or remove a read-only
    folder: the update could then neither move the files into place nor clean up."""
    import stat
    n = 0
    for p in [Path(root), *Path(root).rglob('*')]:
        mode = os.stat(p).st_mode
        if not mode & stat.S_IWRITE:
            os.chmod(p, mode | stat.S_IWRITE)
            n += 1
    return n


def _rm_writable(func, path, exc):
    """rmtree error handler: clear read-only and retry once."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rm_quiet(path):
    """Removes a folder of the converter's own, read-only parts too; never fails the job."""
    try:
        shutil.rmtree(path, onexc=_rm_writable)
    except OSError:
        pass


def find_7z():
    for p in (shutil.which('7z'), shutil.which('7za'), r'C:\Program Files\7-Zip\7z.exe', r'C:\Program Files (x86)\7-Zip\7z.exe'):
        if p and Path(p).exists():
            return p
    return None


def data_root_of(mod_dir):
    """(data folder, container to move) of a mod folder, or None."""
    # the <Name>.mpq folder itself given as the source (e.g. <game>\Reimagined.mpq): keep it whole,
    # so modinfo.json (name, version) goes along with its data
    if mod_dir.is_dir() and mod_dir.name.lower().endswith('.mpq') and (mod_dir / 'modinfo.json').exists() \
            and (mod_dir / 'data').is_dir():
        return mod_dir / 'data', mod_dir
    for p in sorted(mod_dir.iterdir()) if mod_dir.is_dir() else []:
        if p.is_dir() and p.name.lower().endswith('.mpq') and (p / 'modinfo.json').exists() and (p / 'data').is_dir():
            return p / 'data', p
    if (mod_dir / 'data').is_dir() and any((mod_dir / 'data' / x).is_dir() for x in ('global', 'hd', 'local')):
        return mod_dir / 'data', mod_dir / 'data'
    return None


def find_mods(root, depth=6):
    """Mod folders under an extracted download: [(mod folder, data folder, container)]."""
    out = []

    def walk(d, n):
        if n < 0 or d.name.lower() in ('d2rloader',):
            return
        found = data_root_of(d)
        if found:
            out.append((d, found[0], found[1]))
            return
        for c in sorted(x for x in d.iterdir() if x.is_dir()):
            walk(c, n - 1)
    walk(root, depth)
    return out


def find_loader(root, mod_dir):
    """The download's d2rloader folder: in the mod folder or one of the folders above it."""
    d = mod_dir
    while True:
        if (d / 'd2rloader').is_dir():
            return d / 'd2rloader'
        if d == root or d.parent == d:
            return None
        d = d.parent


def extra_loaders(root, mod_dir, used):
    """d2rloader folders of a download other than the mod's own: in the folders above the mod folder
    up to the download's root, and for a mod folder inside <install>\\mods\\ the install's own
    d2rloader (a D2RLoader setup ships plugins there, beside mods\\). Never the game's own."""
    used = Path(used).resolve() if used else None
    out = []

    def add(c):
        if c.is_dir() and c.resolve() != used and c not in out and not (c.parent / 'D2R.exe').exists():
            out.append(c)
    d = mod_dir
    while True:
        add(d / 'd2rloader')
        if d == root or d.parent == d:
            break
        d = d.parent
    if root.parent.name.lower() == 'mods':
        add(root.parent.parent / 'd2rloader')
    return out


def compiled_updater(mod_dir):
    """A converted mod made from compiled tables (d2rmm/update.json, method merge-compiled): an
    update runs MergeCompiledMod.py on the new download before converting."""
    try:
        info = json.loads((mod_dir / 'd2rmm' / 'update.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None
    return info if info.get('method') == 'merge-compiled' else None


def is_mpq(f):
    with open(f, 'rb') as fh:
        return fh.read(4) == b'MPQ\x1a'


def mod_version(container, fallback=None):
    """The version a mod states: modinfo.json "version", else a 'Mod Version: x' line (in modinfo's
    comment block or mod.txt), else fallback."""
    try:
        v = ConvertDataMod.read_modinfo(container / 'modinfo.json').get('version')
        if v:
            return str(v)
    except (OSError, ValueError):
        pass
    for n in ('modinfo.json', 'mod.txt'):
        try:
            text = (container / n).read_text(encoding='utf-8-sig', errors='replace')
        except OSError:
            continue
        m = re.search(r'(?im)\b(?:mod\s*)?version\s*[:=]\s*v?([0-9][\w.\-]*)', text)
        if m:
            return m.group(1)
    return fallback


def tool_python():
    return sys.executable


# --------------------------------------------------------------------------- jobs

def updater_of(mod_dir):
    """A mod's own updater (dev/update.json naming a script), for mods the converter cannot redo
    itself, such as ones made from compiled tables."""
    p = mod_dir / 'dev' / 'update.json'
    try:
        info = json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None
    script = mod_dir / 'dev' / info.get('script', '')
    return {'script': str(script), 'kind': info.get('kind', ''), 'source': info.get('source', '')} if script.is_file() else None


class Job:
    def __init__(self, title):
        self.id = hashlib.sha1(('%s%f' % (title, time.time())).encode()).hexdigest()[:10]
        self.title = title
        self.state = 'running'
        self.lines = []
        self.result = None

    def log(self, text):
        for line in str(text).splitlines() or ['']:
            self.lines.append(line)

    def run(self, fn):
        def go():
            try:
                self.result = fn(self)
                self.state = 'done'
            except Exception as e:  # shown in the page
                self.log('ERROR: %s' % e)
                self.log(traceback.format_exc())
                self.state = 'failed'
        threading.Thread(target=go, daemon=True).start()
        return self


class App:
    def __init__(self, game, d2rmm):
        self.game = game
        self.d2rmm = d2rmm
        self.mods = d2rmm / 'mods'
        self.work = d2rmm / 'converter-work'  # extracted downloads (safe to delete)
        self.sevenzip = find_7z()
        self.jobs = {}

    # ---- what is there
    def state(self):
        mods = []
        for d in sorted(self.mods.iterdir()):
            mj = d / 'mod.json'
            if not mj.is_file():
                continue
            try:
                info = json.loads(mj.read_text(encoding='utf-8-sig'))
            except ValueError:
                info = {}
            report = ConvertDataMod.old_report(d)
            mods.append({'id': d.name, 'name': info.get('name', d.name), 'version': info.get('version', ''),
                         'author': info.get('author', ''), 'converted': bool(report) or (d / 'dev' / 'update.json').exists(),
                         'updater': updater_of(d),
                         'settings': report.get('settings') or {}, 'features': report.get('features') or {},
                         'rows': report.get('rows', 'rebuild' if report else None)})
        downloads = []
        for folder in {self.game, self.d2rmm, Path.home() / 'Downloads'}:
            if not folder.is_dir():
                continue
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in ARCHIVES + ('.mpq',) and p.name.lower() not in LOADER_BINARIES:
                    downloads.append({'path': str(p), 'size': p.stat().st_size, 'time': p.stat().st_mtime})
        downloads.sort(key=lambda x: -x['time'])
        return {'game': str(self.game), 'd2rmm': str(self.d2rmm), 'sevenzip': self.sevenzip, 'mods': mods,
                'downloads': downloads, 'features': [[f[0], f[1]] for f in ConvertDataMod.FEATURES]}

    # ---- getting a download into a folder
    def stage(self, source, job, unpack=True):
        """-> folder holding the download's files (a folder source is used where it is)."""
        src = Path(source)
        if not src.exists():
            raise ValueError('not found: %s' % source)
        if src.is_dir():
            return self.stage_folder(src, job) if unpack else (src, False)
        key = hashlib.sha1(('%s|%d|%d' % (src.resolve(), src.stat().st_size, src.stat().st_mtime)).encode()).hexdigest()[:12]
        out = self.work / ('%s-%s' % (src.stem[:40].replace(' ', '_'), key))
        if (out / '.complete').exists():
            job.log('already extracted: %s' % out)
            if unpack:
                self.unpack_packed(out, job)
            return out, True
        if out.exists():
            shutil.rmtree(out, onexc=_rm_writable)
        out.mkdir(parents=True)
        ext = src.suffix.lower()
        if ext == '.mpq':
            # a packed D2RLoader package: <Name>.mpq beside its d2rloader folder
            job.log('unpacking %s ...' % src.name)
            self.run_tool([tool_python(), str(HERE / 'MpqArchive.py'), 'extract', str(src), str(out / src.stem)], job)
            if (src.parent / 'd2rloader').is_dir():
                shutil.copytree(src.parent / 'd2rloader', out / src.stem / 'd2rloader')
        elif ext in ARCHIVES:
            if not self.sevenzip:
                raise ValueError('7-Zip is needed to open %s files (install it from 7-zip.org)' % ext)
            job.log('extracting %s (%d MB) ...' % (src.name, src.stat().st_size // 2 ** 20))
            self.run_tool([self.sevenzip, 'x', '-y', '-bso0', '-bsp0', '-o' + str(out), str(src)], job)
        else:
            raise ValueError('cannot open %s (folder, .zip, .7z, .rar or .mpq)' % src.name)
        cleared = make_writable(out)
        if cleared:
            job.log('  %d read-only files/folders in the download made writable' % cleared)
        if unpack:
            self.unpack_packed(out, job)
        (out / '.complete').write_text('ok')
        return out, True

    def packed_in(self, root):
        """Packed MPQ files (not plugins' archives) under a folder."""
        out = []
        for f in sorted(root.rglob('*.mpq')):
            if not f.is_file() or f.name.lower() in LOADER_BINARIES or f.parent.name.lower() == 'plugins':
                continue
            with open(f, 'rb') as fh:
                if fh.read(4) == b'MPQ\x1a':
                    out.append(f)
        return out

    def stage_folder(self, src, job):
        """A folder download used where it is, unless it holds the mod only as a packed MPQ file
        (Frankenstein: FMMP-Experimental-R67\\FMMP-Experimental-R67.mpq beside its d2rloader): then
        each packed file is unpacked into the work folder, with the d2rloader folder beside it, so
        the download itself stays as it is."""
        if find_mods(src):
            return src, False
        packed = self.packed_in(src)
        if not packed:
            return src, False
        key = hashlib.sha1('|'.join('%s|%d|%d' % (f.resolve(), f.stat().st_size, f.stat().st_mtime)
                                    for f in packed).encode()).hexdigest()[:12]
        out = self.work / ('%s-%s' % (src.name[:40].replace(' ', '_'), key))
        if (out / '.complete').exists():
            job.log('already unpacked: %s' % out)
            return out, True
        if out.exists():
            shutil.rmtree(out)
        for f in packed:
            dest = out / f.parent.relative_to(src)
            dest.mkdir(parents=True, exist_ok=True)
            job.log('unpacking the packed archive %s ...' % f.relative_to(src))
            self.run_tool([tool_python(), str(HERE / 'MpqArchive.py'), 'extract', str(f), str(dest / (f.stem + '-unpacked'))], job)
            if (f.parent / 'd2rloader').is_dir() and not (dest / 'd2rloader').exists():
                shutil.copytree(f.parent / 'd2rloader', dest / 'd2rloader')
        (out / '.complete').write_text('ok')
        return out, True

    def unpack_packed(self, root, job):
        """A download can hold the mod as a packed MPQ file (mods\\Rebirth\\Rebirth.mpq is a file):
        each one is unpacked beside it into <stem>-unpacked\\<stem>.mpq\\data."""
        for f in sorted(root.rglob('*.mpq')):
            if not f.is_file() or f.name.lower() in LOADER_BINARIES or f.parent.name.lower() == 'plugins':
                continue
            with open(f, 'rb') as fh:
                if fh.read(4) != b'MPQ\x1a':
                    continue
            out = f.parent / (f.stem + '-unpacked')
            if out.exists():
                continue
            job.log('unpacking the packed archive %s ...' % f.relative_to(root))
            self.run_tool([tool_python(), str(HERE / 'MpqArchive.py'), 'extract', str(f), str(out)], job)

    def run_tool(self, cmd, job):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding='utf-8', errors='replace')
        for line in proc.stdout:
            line = line.rstrip()
            if line and 'fetched' not in line:
                job.log(line)
        if proc.wait() != 0:
            raise RuntimeError('%s failed (exit %d)' % (Path(cmd[1] if cmd[0] == tool_python() else cmd[0]).name, proc.returncode))

    def describe(self, root):
        """What a staged download holds: the mod folders in it, per feature, and its loader parts."""
        found = []
        for mod_dir, data, container in find_mods(root):
            info = {}
            if (container / 'modinfo.json').exists():
                try:
                    info = json.loads((container / 'modinfo.json').read_text(encoding='utf-8-sig'))
                except ValueError:
                    pass
            counts = {}
            nfiles = 0
            for p in data.rglob('*'):
                if p.is_file():
                    nfiles += 1
                    f = ConvertDataMod.feature_of(p.relative_to(data).as_posix())
                    counts[f] = counts.get(f, 0) + 1
            loader = find_loader(root, mod_dir)
            plugins, patches = [], []
            if loader:
                plugins = sorted(p.name for p in (loader / 'plugins').glob('*.dll')) if (loader / 'plugins').is_dir() else []
                patches = sorted(p.name for p in (loader / 'patches').glob('*.json')) if (loader / 'patches').is_dir() else []
            binaries = sorted(p.name for p in root.rglob('*') if p.is_file() and p.name.lower() in LOADER_BINARIES)
            excel = data / 'global' / 'excel'
            compiled = sorted(p.stem for p in excel.glob('*.bin')
                              if not (excel / (p.stem + '.txt')).exists()) if excel.is_dir() else []
            mod_id = mod_dir.name if mod_dir != root else container.stem
            if mod_id.endswith('-unpacked'):
                mod_id = mod_id[:-len('-unpacked')]
            found.append({'folder': str(mod_dir), 'id': mod_id,
                          'name': info.get('name') or mod_dir.name, 'version': info.get('version', ''),
                          'data': str(data), 'container': str(container), 'files': nfiles, 'features': counts,
                          'loader': str(loader) if loader else None, 'plugins': plugins, 'patches': patches,
                          'ignored': binaries, 'compiledOnly': compiled})
        return found

    # ---- updates: old files kept in <mod>\d2rmm\previous until the new conversion passed its check
    def backup(self, target, job):
        prev = target / 'd2rmm' / 'previous'
        if prev.exists():
            shutil.rmtree(prev, onexc=_rm_writable)
        prev.mkdir(parents=True)
        old = data_root_of(target)
        moved = []
        for part in ([old[1]] if old else []) + ([target / 'd2rloader'] if (target / 'd2rloader').is_dir() else []):
            shutil.move(str(part), str(prev / part.name))
            moved.append(part.name)
        job.log('old files kept in %s: %s' % (prev, ', '.join(moved)))

    def restore(self, target, job):
        job.log('the conversion failed: putting the old files back')
        for part in list((target / 'd2rmm' / 'previous').iterdir()):
            now = target / part.name
            if now.exists():
                shutil.rmtree(now, onexc=_rm_writable) if now.is_dir() else now.unlink()
            shutil.move(str(part), str(now))
        job.log('old files restored; run the old conversion again with ConvertDataMod.py if mod.js changed')

    def convert_cmd(self, target, want, source):
        cmd = [tool_python(), str(HERE / 'ConvertDataMod.py'), '--game', str(self.game), '--mod', str(target),
               '--rows', want['rows'], '--plugins', want['plugins'], '--source', str(source), '--check',
               '--d2rmm', str(self.d2rmm)]
        for k in ('name', 'author', 'version'):
            if want.get(k):
                cmd += ['--' + k, str(want[k])]
        # row matching (defaults of ConvertDataMod.py when a mod was converted before they existed)
        cmd += ['--match-trim' if want.get('matchTrim', True) not in (False, 'false', 0) else '--no-match-trim',
                '--duplicates', want.get('duplicates') or 'content', '--deleted', want.get('deleted') or 'disable']
        # load order: defaults of the converted mod's Load order settings
        cmd += ['--conflicts', want.get('conflicts') or 'mod', '--files', want.get('files') or 'overwrite',
                '--base-rows', want.get('baseRows') or 'stubs']
        return cmd

    @staticmethod
    def row_options(p, settings):
        """Row-matching and load-order options: the page's choice, else what the mod was converted with."""
        out = {}
        for k in ('matchTrim', 'duplicates', 'deleted', 'conflicts', 'files', 'baseRows'):
            v = p.get(k)
            out[k] = v if v not in (None, '') else settings.get(k)
        return out

    def package_extras(self, mod_id, target, extras, job):
        """The download's other d2rloader folders as D2RMM packages; noted in convert.json."""
        done = []
        for ld in extras:
            job.log('plugins and patches of %s -> D2RMM packages ...' % ld)
            r = ConvertDataMod.package_loader_folder(ld, self.d2rmm / 'd2rloader', mod_id, self.game)
            for k, what in (('packaged', 'new package (D2RMM imports it on start or Plugins > Refresh)'),
                            ('unchanged', 'package unchanged'), ('alreadyInstalled', 'installed already by'),
                            ('conflicts', 'NOT packaged, another package puts a different file there'),
                            ('builtFromSource', 'left out, a source build is on this machine')):
                items = r[k].items() if isinstance(r[k], dict) else ((x, None) for x in r[k])
                for name, extra in items:
                    job.log('  %s: %s%s' % (name, what, (' ' + ', '.join(extra) if isinstance(extra, list) else ' ' + extra) if extra else ''))
            done.append(dict(r, folder=str(ld)))
        report_path = target / 'd2rmm' / 'convert.json'
        report = ConvertDataMod.old_report(target)
        if report:
            report['extraLoaderFolders'] = done
            report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')

    def update_compiled(self, p, info, job):
        """Update of a mod made from compiled tables: extract the new download, merge its tables onto
        the game's (MergeCompiledMod.py), put the result in place, convert with the old settings."""
        mod_id = p['id']
        target = self.mods / mod_id
        settings = dict(ConvertDataMod.old_report(target).get('settings') or {})
        source = p.get('source') or settings.get('source')
        if not source:
            raise ValueError('%s: no download given and none in convert.json' % mod_id)
        name = info.get('mpqName') or mod_id
        root, temporary = self.stage(source, job, unpack=False)
        work = self.work / ('%s-merge' % mod_id)
        try:
            if work.exists():
                shutil.rmtree(work)
            work.mkdir(parents=True)
            cands = [root] if root.is_file() else sorted(root.rglob('*.mpq'))
            packed = [f for f in cands if f.is_file() and f.stem.lower() == name.lower()
                      and f.parent.name.lower() != 'plugins' and is_mpq(f)]
            if packed:
                src = work / 'src'
                mod_dir = packed[0].parent
                job.log('extracting %s ...' % packed[0])
                self.run_tool([tool_python(), str(HERE / 'MpqArchive.py'), 'extract', str(packed[0]), str(src)], job)
                inner = [d for d in [src] + sorted(x for x in src.iterdir() if x.is_dir()) if (d / 'data' / 'global' / 'excel').is_dir()]
                if not inner:
                    raise ValueError('%s holds no data\\global\\excel' % packed[0])
                src = inner[0]  # the archive keeps its own top folder (Rebirth.mpq\data\...)
            else:  # unpacked: a <name>.mpq (or <name>) folder with data\global\excel
                folders = [d for d in [root] + sorted(x for x in root.rglob('*') if x.is_dir())
                           if re.sub(r'(?i)\.mpq$', '', d.name).lower() == name.lower()
                           and (d / 'data' / 'global' / 'excel').is_dir()]
                if not folders:
                    raise ValueError('no %s.mpq (packed file or folder with data) in %s' % (name, source))
                src = mod_dir = folders[0]
            nfiles = sum(1 for x in src.rglob('*') if x.is_file())
            version = p.get('version') or mod_version(src, settings.get('version'))
            job.log('%s: %d files, version %s' % (src, nfiles, version))
            staging = work / 'out'
            self.run_tool([tool_python(), str(HERE / 'MergeCompiledMod.py'), str(src), str(staging), '--name', name,
                           '--game', str(self.game)], job)
            self.backup(target, job)
            shutil.move(str(staging / (name + '.mpq')), str(target / (name + '.mpq')))
            want = {'name': p.get('name') or settings.get('name'), 'author': p.get('author') or settings.get('author'),
                    'version': version, 'rows': settings.get('rows') or 'rebuild',
                    'plugins': settings.get('plugins') or 'mod', **self.row_options(p, settings)}
            before = ConvertDataMod.old_report(target).get('features') or {}
            try:
                self.run_tool(self.convert_cmd(target, want, source), job)
            except Exception:
                self.restore(target, job)
                raise
            shutil.copy2(staging / 'merge-report.json', target / 'd2rmm' / 'merge-report.json')
            extras = extra_loaders(root, mod_dir, None)
            if extras:
                self.package_extras(mod_id, target, extras, job)
            after = ConvertDataMod.old_report(target).get('features') or {}
            for fid in sorted(set(before) | set(after)):
                if before.get(fid) != after.get(fid):
                    job.log('  %s: %s -> %s files' % (fid, before.get(fid, 0), after.get(fid, 0)))
        finally:
            shutil.rmtree(work, ignore_errors=True)
            if temporary:
                shutil.rmtree(root, ignore_errors=True)
        job.log('done: %s %s is ready. In D2RMM: Refresh list, keep it at the TOP of the load order, then Install '
                'Mods with the game closed.' % (mod_id, version))
        return {'id': mod_id}

    # ---- actions
    def inspect(self, source):
        job = Job('inspect')

        def go(job):
            root, _ = self.stage(source, job)
            found = self.describe(root)
            if not found:
                raise ValueError('no mod data found (a <Name>.mpq folder with modinfo.json and data, or a data folder)')
            job.log('found %d mod folder(s)' % len(found))
            return {'root': str(root), 'mods': found}
        self.jobs[job.id] = job.run(go)
        return job

    def convert(self, p, update=False):
        job = Job('update' if update else 'convert')
        compiled = compiled_updater(self.mods / p.get('id', '')) if update else None
        if compiled:
            self.jobs[job.id] = job.run(lambda job: self.update_compiled(p, compiled, job))
            return job
        own = updater_of(self.mods / p.get('id', '')) if update else None
        if own:
            def go_own(job):
                job.log('%s has its own updater (%s): %s' % (p['id'], own['kind'], Path(own['script']).name))
                self.run_tool([tool_python(), own['script'], p['source'], '--game', str(self.game)], job)
                return {'id': p['id']}
            self.jobs[job.id] = job.run(go_own)
            return job

        def go(job):
            root, temporary = self.stage(p['source'], job)
            found = self.describe(root)
            pick = [m for m in found if m['folder'] == p.get('folder')] or found[:1]
            if not pick:
                raise ValueError('no mod data in %s' % p['source'])
            m = pick[0]
            mod_id = p['id']
            target = self.mods / mod_id
            settings = {}
            if update:
                if not target.is_dir():
                    raise ValueError('%s is not in the mods folder' % mod_id)
                settings = dict(ConvertDataMod.old_report(target).get('settings') or {})
                if not settings:
                    info = json.loads((target / 'mod.json').read_text(encoding='utf-8-sig'))
                    settings = {'name': info.get('name'), 'author': info.get('author'), 'version': info.get('version'),
                                'rows': ConvertDataMod.old_report(target).get('rows', 'keep'), 'plugins': 'mod'}
                self.backup(target, job)  # kept until the new conversion has passed its check
            else:
                if target.exists():
                    raise ValueError('%s is already in the mods folder: use Update, or pick another id' % mod_id)
                target.mkdir(parents=True)
            def copy(a, b):
                if Path(b).exists():  # a half-done move
                    shutil.rmtree(b, onexc=_rm_writable) if Path(b).is_dir() else Path(b).unlink()
                shutil.copytree(a, b) if Path(a).is_dir() else shutil.copy2(a, b)

            def put(a, b):
                # An extracted copy is moved; Windows can refuse the rename (a scanner holding the
                # fresh files), and shutil.move's own fallback then fails deleting the source. Copy
                # instead: the extracted folder is removed afterwards with errors ignored.
                if not temporary:
                    return copy(a, b)
                try:
                    os.rename(a, b)
                except OSError as e:
                    job.log('  moving %s was refused (%s): copying instead' % (Path(a).name, e.strerror or e))
                    copy(a, b)
            container = Path(m['container'])
            extras = extra_loaders(root, Path(m['folder']), m['loader'])
            want = {
                'name': p.get('name') or settings.get('name'),
                'author': p.get('author') or settings.get('author'),
                'version': p.get('version') or (m['version'] if update and m['version'] else settings.get('version')),
                'rows': p.get('rows') or settings.get('rows') or 'keep',
                'plugins': p.get('plugins') or settings.get('plugins') or 'mod',
                **self.row_options(p, settings),
            }
            before = (ConvertDataMod.old_report(target).get('features') or {}) if update else {}
            try:
                # inside the try: a failure while placing the new files also puts the old ones back
                job.log('putting %s into %s ...' % (container.name, target))
                put(str(container), str(target / container.name))
                if m['loader']:
                    put(str(m['loader']), str(target / 'd2rloader'))
                self.run_tool(self.convert_cmd(target, want, p['source']), job)
                if extras:
                    self.package_extras(mod_id, target, extras, job)
            except Exception:
                if update:
                    self.restore(target, job)
                raise
            finally:
                if temporary:  # the extracted copy is used up
                    rm_quiet(root)
            after = ConvertDataMod.old_report(target).get('features') or {}
            if update:
                for fid in sorted(set(before) | set(after)):
                    if before.get(fid) != after.get(fid):
                        job.log('  %s: %s -> %s files' % (fid, before.get(fid, 0), after.get(fid, 0)))
                # the new conversion passed its check: the old files are no longer needed
                rm_quiet(target / 'd2rmm' / 'previous')
                job.log('old files removed from %s' % (target / 'd2rmm' / 'previous'))
            job.log('done: %s is ready. In D2RMM: Refresh list (and Plugins > Refresh when plugins were packaged), '
                    'then Install Mods with the game closed.' % mod_id)
            return {'id': mod_id}
        self.jobs[job.id] = job.run(go)
        return job


def make_handler(app):
    page = (HERE / 'ModConverter.html').read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path in ('/', '/index.html'):
                return self.send(200, page, 'text/html; charset=utf-8')
            if u.path == '/api/state':
                return self.send(200, app.state())
            if u.path == '/api/job':
                job = app.jobs.get((q.get('id') or [''])[0])
                if not job:
                    return self.send(404, {'error': 'no such job'})
                since = int((q.get('since') or ['0'])[0])
                return self.send(200, {'state': job.state, 'lines': job.lines[since:], 'next': len(job.lines),
                                       'result': job.result})
            self.send(404, {'error': 'not found'})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0)) or 0) or b'{}')
                if u.path == '/api/inspect':
                    return self.send(200, {'job': app.inspect(body['source']).id})
                if u.path == '/api/convert':
                    return self.send(200, {'job': app.convert(body, update=False).id})
                if u.path == '/api/update':
                    return self.send(200, {'job': app.convert(body, update=True).id})
            except Exception as e:
                return self.send(400, {'error': str(e)})
            self.send(404, {'error': 'not found'})
    return Handler


def follow(job):
    """Prints a job's log until it ends; True when it succeeded."""
    n = 0
    while True:
        state = job.state  # read before printing, so lines logged before the end are all printed
        while n < len(job.lines):
            print(job.lines[n], flush=True)
            n += 1
        if state != 'running':
            return state == 'done'
        time.sleep(0.3)


def convert_cli(app, source, p):
    """--convert: the page's Convert without the page. The download is recorded in convert.json, so
    --update <id> later redoes the conversion from it (or from a new --source)."""
    src = Path(source)
    if src.exists():
        source = str(src.resolve())
    if not p.get('id'):
        job = Job('inspect')
        root, _ = app.stage(source, job, unpack=False)
        found = app.describe(root) if root.is_dir() else []
        p['id'] = found[0]['id'] if found else src.stem
    print('== converting %s into %s' % (source, app.mods / p['id']), flush=True)
    ok = follow(app.convert(dict(p, source=source), update=False))
    print('== %s: %s' % (p['id'], 'done' if ok else 'failed'), flush=True)
    return 0 if ok else 1


def update_cli(app, ids, source, options=None):
    """--update: the page's Update, run here one mod after the other; exit 1 if any failed.
    options: row-matching choices that replace the ones the mod was converted with."""
    code = 0
    for mod_id in ids:
        target = app.mods / mod_id
        if not (target / 'mod.json').is_file():
            print('%s: not a mod in %s' % (mod_id, app.mods))
            code = 1
            continue
        src = source or (ConvertDataMod.old_report(target).get('settings') or {}).get('source')
        if not src:
            print('%s: no download in its convert.json; pass --source' % mod_id)
            code = 1
            continue
        print('== updating %s from %s' % (mod_id, src), flush=True)
        ok = follow(app.convert(dict(options or {}, id=mod_id, source=src), update=True))
        print('== %s: %s' % (mod_id, 'done' if ok else 'failed'), flush=True)
        if not ok:
            code = 1
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--d2rmm', help="D2RMM's folder (default: found beside or inside the game folder)")
    ap.add_argument('--port', type=int, default=8766)
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--update', action='append', metavar='MOD_ID',
                    help='update this converted mod without the page (repeatable)')
    ap.add_argument('--source', help='with --update: the new download (default: the one in its convert.json)')
    ap.add_argument('--convert', metavar='SOURCE',
                    help='convert a mod without the page: a folder (also a <Name>.mpq folder), .zip/.7z/.rar or packed '
                         '.mpq; it goes into <D2RMM>\\mods\\<id> and is remembered for --update')
    ap.add_argument('--id', help='with --convert: the mod folder name in D2RMM (default: the mod\'s own name)')
    ap.add_argument('--name', help='with --convert: the name shown in D2RMM')
    ap.add_argument('--author', help='with --convert: the author shown in D2RMM')
    ap.add_argument('--version', help='with --convert: the version (default: the mod\'s modinfo.json)')
    ap.add_argument('--rows', choices=('keep', 'rebuild'), help='with --convert: row merge mode (default keep)')
    ap.add_argument('--plugins', choices=('mod', 'packages'), help='with --convert: D2RLoader plugins in mod.js or as packages')
    ap.add_argument('--match-trim', action=argparse.BooleanOptionalAction, default=None,
                    help='with --update: match row names with the spaces around them ignored (default: as converted, else on)')
    ap.add_argument('--duplicates', choices=('content', 'order'),
                    help='with --update: rows sharing a name matched by content or by order (default: as converted, else content)')
    ap.add_argument('--deleted', choices=('disable', 'leave'),
                    help='with --update, rows keep: switch off the rows the mod deleted, or leave them (default: as converted, else disable)')
    ap.add_argument('--conflicts', choices=('mod', 'earlier'),
                    help='with --update: default of the mod\'s Load order > Conflicts setting (default: as converted, else mod)')
    ap.add_argument('--files', choices=('overwrite', 'keep'),
                    help='with --update: default of the mod\'s Load order > Files setting (default: as converted, else overwrite)')
    ap.add_argument('--base-rows', choices=('stubs', 'leave'),
                    help='with --update: default of the mod\'s Load order > Classic-rules tables setting: stub rows in '
                         'global\\excel\\base for missile rows only the main table has (default: as converted, else stubs)')
    args = ap.parse_args()
    if not args.game or not Path(args.game).is_dir():
        raise SystemExit('Pass --game (or set D2R_PATH) to the folder that contains D2R.exe.')
    game = Path(args.game)
    d2rmm = Path(args.d2rmm) if args.d2rmm else (Path(os.environ['D2RMM_PATH']) if os.environ.get('D2RMM_PATH')
                                                 else find_d2rmm(game))
    if not d2rmm or not (d2rmm / 'mods').is_dir():
        raise SystemExit("D2RMM's folder not found: pass --d2rmm <folder with mods\\> (or set D2RMM_PATH)")
    ConvertDataMod.use_d2rmm_casclib(d2rmm)  # also for the tools it runs (they inherit the environment)
    app = App(game, d2rmm)
    if args.update:
        options = {k: v for k, v in (('matchTrim', args.match_trim), ('duplicates', args.duplicates),
                                     ('deleted', args.deleted), ('conflicts', args.conflicts),
                                     ('files', args.files), ('baseRows', args.base_rows)) if v is not None}
        sys.exit(update_cli(app, args.update, args.source, options))
    if args.convert:
        p = {k: v for k, v in (('id', args.id), ('name', args.name), ('author', args.author), ('version', args.version),
                               ('rows', args.rows), ('plugins', args.plugins), ('matchTrim', args.match_trim),
                               ('duplicates', args.duplicates), ('deleted', args.deleted),
                               ('conflicts', args.conflicts), ('files', args.files),
                               ('baseRows', args.base_rows)) if v is not None}
        sys.exit(convert_cli(app, args.convert, p))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    url = 'http://127.0.0.1:%d/' % args.port
    print('Mod converter on %s (game %s, D2RMM %s). Ctrl+C stops it.' % (url, game, d2rmm))
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
