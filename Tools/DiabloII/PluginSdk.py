"""Keeps the D2RLoader plugin SDK that the D2R plugins build against up to date.

    python PluginSdk.py status  --mods <game>\\mods
    python PluginSdk.py diff    --mods <game>\\mods [--ref master]
    python PluginSdk.py apply   --mods <game>\\mods [--ref master] [--no-build]
    python PluginSdk.py rebuild --mods <game>\\mods
    python PluginSdk.py restore --mods <game>\\mods [--to 0.3.0]

All plugins in <mods> (<plugin>\\plugin\\build.bat, SkillTab4\\probe\\build.bat) compile against one
shared copy of the SDK, <mods>\\SkillTab4\\sdk (include\\, README.md, LICENSE). This tool compares
that copy with D2RLoader's public PluginSDK (github.com/D2RLoader/PluginSDK, MIT), shows what changed
in the headers and which plugins use the changed parts, and swaps the copy and rebuilds every
plugin when asked.

  status   installed SDK release and ABI (include\\D2RLPlugin\\version.h), the upstream ref's, the
           installed loader (d2rloader.log, D2RLoader.exe date), the newest published loader (the
           official installer's manifest on d2rloader.net), whether the upstream headers fit it,
           the plugins
  diff     headers added / removed / changed, and per changed header the declarations that went
           away or came in; then, per plugin, the names it uses that are gone, and the service size
           requirements (<Service>RequiredSize) whose value changed. The values are computed by
           compiling a small program against each copy (MSVC, as the plugins), since a definition
           can change while its value stays (0.4.0 grew WidgetService from 64 to 208 bytes but kept
           WidgetServiceRequiredSize at 64)
  trial    builds every plugin against the upstream headers in a temp folder (the shared copy, the
           plugins' dist\\ and build\\ stay as they are): what would break, before anything changes
  apply    refuses (unless --force) while a size requirement a plugin checks grew and the newest
           published loader is still the installed one: the SDK repo runs ahead of the loader, its
           master describes the next loader release.
           Otherwise keeps the current copy as sdk-<version> next to it, puts the upstream include\\, README.md
           and LICENSE in its place, then rebuilds every plugin (DLLs go to each plugin's dist\\ as
           usual; nothing is installed into D2RMM) and reports the ones that fail
  rebuild  rebuilds every plugin against the current copy
  restore  puts a kept copy back (the newest, or --to <version>)

Downloads go to %LOCALAPPDATA%\\D2RModAssets\\pluginsdk\\<ref>-<commit> (outside this repo; the SDK
is third-party code, see THIRD_PARTY.md). Network: the GitHub API (to resolve --ref) and codeload
(the zip), no account needed.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = 'D2RLoader/PluginSDK'
SDK_REL = Path('SkillTab4') / 'sdk'
CACHE = Path(os.environ.get('LOCALAPPDATA', '.')) / 'D2RModAssets' / 'pluginsdk'
LOADER_MANIFEST = 'https://d2rloader.net/download/manifest.json'  # what the official installer reads
AGENT = {'User-Agent': 'aamt-pluginsdk-sync'}
KEEP = ('include', 'README.md', 'LICENSE')
C_WORDS = set('''auto bool break case char const constexpr continue default define do double else enum extern
false float for if include inline int long namespace nullptr return short signed sizeof static struct switch
true typedef typename union unsigned using void volatile while uint8_t uint16_t uint32_t uint64_t int8_t
int16_t int32_t int64_t size_t std pragma once ifdef ifndef endif noexcept static_assert offsetof'''.split())


def fail(message):
    print('error: ' + message, file=sys.stderr)
    sys.exit(1)


# ------------------------------------------------------------------ versions

def sdk_version(root):
    """{'sdk': '0.3.0', 'abi': '4', ...} from include/D2RLPlugin/version.h."""
    path = Path(root) / 'include' / 'D2RLPlugin' / 'version.h'
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8', errors='replace')
    out = {}
    for key, name in (('sdk', 'D2RL_SDK_VERSION'), ('abi', 'D2RL_PLUGIN_ABI_VERSION'), ('minAbi', 'D2RL_PLUGIN_MIN_ABI_VERSION')):
        m = re.search(r'#define\s+%s\s+"?([^"\s]+)"?' % name, text)
        if m:
            out[key] = m.group(1)
    return out


def loader_version(mods):
    log = Path(mods).parent / 'd2rloader' / 'logs' / 'd2rloader.log'
    if not log.exists():
        return None
    m = re.search(r'D2RLoader v(\S+)', log.read_text(encoding='utf-8-sig', errors='replace')[:4000])
    return m.group(1) if m else None


def latest_loader():
    """The release d2rloader.net's installer manifest lists ({'version', 'files': {name: size}}), or None."""
    try:
        req = urllib.request.Request(LOADER_MANIFEST, headers=AGENT)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return {'version': data.get('version'), 'files': {f.get('path', ''): f.get('size') for f in data.get('files', [])}}
    except Exception:
        return None


def installed_loader(mods):
    """Version (log) and build date (D2RLoader.exe) of the loader in the game folder."""
    exe = Path(mods).parent / 'D2RLoader.exe'
    built = None
    if exe.exists():
        import datetime
        built = datetime.date.fromtimestamp(exe.stat().st_mtime).isoformat()
    return {'version': loader_version(mods), 'built': built, 'size': exe.stat().st_size if exe.exists() else None}


VCVARS = r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
_SIZES = {}


def qualified_constants(text):
    """[(name, 'D2RL::Ns::name')] for every `inline constexpr uint32_t <...>RequiredSize` in a header,
    following `namespace X {` blocks (and `struct X {` scopes, for static members) by brace depth."""
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    out, stack, depth, i = [], [], 0, 0
    token = re.compile(r'\bnamespace\s+([\w:]+)\s*\{|\{|\}|inline\s+constexpr\s+uint32_t\s+(\w+RequiredSize)\b')
    for m in token.finditer(text):
        if m.group(1):
            depth += 1
            stack.append((m.group(1), depth))
        elif m.group(2):
            out.append((m.group(2), '::'.join([n for n, _ in stack] + [m.group(2)])))
        elif m.group(0) == '{':
            depth += 1
        else:
            if stack and stack[-1][1] == depth:
                stack.pop()
            depth -= 1
    return out


def required_sizes(root):
    """{'<Name>RequiredSize': bytes} for every service size requirement of the SDK in `root`, computed
    by compiling and running a small program against its headers (MSVC). None when that fails."""
    root = Path(root)
    if root in _SIZES:
        return _SIZES[root]
    include = root / 'include'
    found = {}  # name -> qualified name
    headers = sorted((include / 'D2RLPlugin').glob('*.h'))
    for h in headers:
        for name, qualified in qualified_constants(h.read_text(encoding='utf-8', errors='replace')):
            found.setdefault(name, qualified)
    import tempfile
    work = Path(tempfile.mkdtemp(prefix='pluginsdk-sizes-'))
    names_left = sorted(found)
    result = None
    for _ in range(4):  # drop names the compiler cannot reach and try again
        src = ['#include <cstdio>', '#include <cstddef>', '#include <D2RLPlugin/api.h>']
        src += ['#include <D2RLPlugin/%s>' % h.name for h in headers]
        src += ['int main() {']
        src += ['    std::printf("%%s %%u\\n", "%s", static_cast<unsigned>(%s));' % (n, found[n]) for n in names_left]
        src += ['    return 0;', '}']
        (work / 'sizes.cpp').write_text('\n'.join(src) + '\n', encoding='utf-8')
        # full paths throughout: cmd may refuse to run programs from the current folder
        # (NoDefaultCurrentDirectoryInExePath)
        bat = ['@echo off',
               'cd /d "%~dp0"',
               'call "%s" >nul || exit /b 1' % VCVARS,
               'cl /nologo /std:c++20 /EHsc /I "%s" "%%~dp0sizes.cpp" /Fe:"%%~dp0sizes.exe" >"%%~dp0build.log" 2>&1 || exit /b 1' % include,
               '"%~dp0sizes.exe"']
        (work / 'sizes.bat').write_text('\r\n'.join(bat) + '\r\n', encoding='utf-8')
        proc = subprocess.run(['cmd', '/c', str(work / 'sizes.bat')], cwd=work, capture_output=True, text=True, errors='replace')
        if proc.returncode == 0:
            result = {}
            for line in proc.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    result[parts[0]] = int(parts[1])
            break
        log = (work / 'build.log').read_text(encoding='utf-8', errors='replace') if (work / 'build.log').exists() else ''
        bad = {n for n in names_left if re.search(r"'%s'" % n, log)}
        if not bad:
            break
        names_left = [n for n in names_left if n not in bad]
    shutil.rmtree(work, ignore_errors=True)
    _SIZES[root] = result
    return result


def added_requirements(old_root, new_root):
    """Size requirements only the new headers have (new services or request types)."""
    old_sizes, new_sizes = required_sizes(old_root), required_sizes(new_root)
    if old_sizes is None or new_sizes is None:
        return []
    return sorted(set(new_sizes) - set(old_sizes))


def grown_requirements(report, old_root=None, new_root=None):
    """Service size requirements (<Name>RequiredSize) whose value differs between the two SDK copies.
    A plugin that checks one and is rebuilt with the new headers needs the loader to provide those
    bytes, and treats the service as missing on a loader without them. Falls back to comparing the
    definitions as text (value None) when the sizes cannot be computed."""
    old_sizes = required_sizes(old_root) if old_root else None
    new_sizes = required_sizes(new_root) if new_root else None
    out = []
    if old_sizes is not None and new_sizes is not None:
        for name in sorted(set(old_sizes) & set(new_sizes)):
            if old_sizes[name] != new_sizes[name]:
                out.append({'name': name, 'old': old_sizes[name], 'new': new_sizes[name], 'grew': new_sizes[name] > old_sizes[name]})
        return out
    for rel, change in report['changed'].items():
        old = {m.group(1) for d in change['gone'] for m in [re.search(r'\b(\w+RequiredSize)\s*=', d)] if m}
        new = {m.group(1) for d in change['new'] for m in [re.search(r'\b(\w+RequiredSize)\s*=', d)] if m}
        for name in sorted(old & new):
            out.append({'name': name, 'old': None, 'new': None, 'grew': True})  # unknown: assume the worst
    return out


# ------------------------------------------------------------------ plugins

def plugins(mods):
    """Build scripts that compile against the shared SDK: [(name, build.bat, [sources])]."""
    out = []
    for bat in sorted(Path(mods).glob('*/*/build.bat')):
        text = bat.read_text(encoding='utf-8', errors='replace').lower()
        if 'sdk\\include' not in text:
            continue
        name = bat.parent.parent.name + ('' if bat.parent.name == 'plugin' else '/' + bat.parent.name)
        sources = sorted(p for p in bat.parent.iterdir() if p.suffix.lower() in ('.cpp', '.h', '.hpp', '.rc'))
        out.append((name, bat, sources))
    return out


def build(bat):
    """-> (ok, short log)."""
    proc = subprocess.run(['cmd', '/c', str(bat)], capture_output=True, text=True, errors='replace')
    log = (proc.stdout + proc.stderr).splitlines()
    errors = [l.strip() for l in log if re.search(r'\berror\b|fatal error', l, re.I)]
    return proc.returncode == 0, errors[:8] if errors else log[-3:]


def rebuild_all(mods):
    results = []
    for name, bat, _ in plugins(mods):
        ok, log = build(bat)
        results.append({'plugin': name, 'ok': ok, 'log': log})
        print('  %-24s %s' % (name, 'built' if ok else 'FAILED'))
        if not ok:
            for line in log:
                print('      ' + line)
    return results


def trial_bat(bat, include, work):
    """A copy of a plugin's build.bat that compiles against `include` into `work`: the plugin's own
    sources are used as they are, the shared SDK copy and the plugin's dist\\ and build\\ stay untouched."""
    here = str(bat.parent) + '\\'
    lines = []
    for line in bat.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.replace('%~dp0', here)
        if re.match(r'\s*set\s+"OUT=', line, re.I):
            line = 'set "OUT=%s"' % (work / 'out')
        elif re.match(r'\s*set\s+"OBJ=', line, re.I):
            line = 'set "OBJ=%s"' % (work / 'obj')
        line = re.sub(r'/I\s+"[^"]*sdk\\include"', lambda m: '/I "%s"' % include, line, flags=re.I)
        lines.append(line)
    work.mkdir(parents=True, exist_ok=True)
    out = work / 'trial-build.bat'
    out.write_text('\r\n'.join(lines) + '\r\n', encoding='utf-8')
    return out


def trial_all(mods, root):
    """Builds every plugin against the SDK in `root` (not installed); returns per-plugin results."""
    import tempfile
    base = Path(tempfile.gettempdir()) / 'pluginsdk-trial'
    shutil.rmtree(base, ignore_errors=True)
    results = []
    for name, bat, _ in plugins(mods):
        ok, log = build(trial_bat(bat, root / 'include', base / name.replace('/', '_')))
        results.append({'plugin': name, 'ok': ok, 'log': log})
        print('  %-24s %s' % (name, 'builds' if ok else 'FAILS'))
        if not ok:
            for line in log:
                print('      ' + line)
    shutil.rmtree(base, ignore_errors=True)
    return results


# ------------------------------------------------------------------ upstream

def resolve(ref):
    req = urllib.request.Request('https://api.github.com/repos/%s/commits/%s' % (REPO, ref), headers=AGENT)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['sha']


def fetch(ref):
    """Downloads the SDK at `ref` (branch, tag or commit) once; returns its folder."""
    sha = resolve(ref)
    target = CACHE / ('%s-%s' % (re.sub(r'[^\w.-]', '_', ref), sha[:12]))
    if (target / 'include').is_dir():
        return target, sha
    req = urllib.request.Request('https://codeload.github.com/%s/zip/%s' % (REPO, sha), headers=AGENT)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    tmp = target.with_name(target.name + '.part')
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            parts = info.filename.split('/', 1)
            if len(parts) < 2 or not parts[1] or info.is_dir():
                continue
            out = tmp / parts[1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(info))
    shutil.rmtree(target, ignore_errors=True)
    tmp.rename(target)
    return target, sha


# ------------------------------------------------------------------ header diff

def declarations(text):
    """Header text as a list of normalised declarations (comments and layout removed)."""
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    out = []
    for line in text.splitlines():
        if line.strip().startswith('#'):
            out.append(' '.join(line.split()))
    body = re.sub(r'^\s*#[^\n]*', ' ', text, flags=re.M)
    for part in re.split(r'(?<=[;{}])', body):
        part = ' '.join(part.split())
        if part and part not in ('}', '};', '{'):
            out.append(part)
    return out


def names(decls):
    found = set()
    for d in decls:
        for word in re.findall(r'[A-Za-z_]\w{3,}', d):
            if word not in C_WORDS:
                found.add(word)
    return found


def header_diff(old_root, new_root):
    old_inc, new_inc = Path(old_root) / 'include', Path(new_root) / 'include'
    old_files = {p.relative_to(old_inc).as_posix(): p for p in old_inc.rglob('*') if p.is_file()}
    new_files = {p.relative_to(new_inc).as_posix(): p for p in new_inc.rglob('*') if p.is_file()}
    report = {'added': sorted(set(new_files) - set(old_files)), 'removed': sorted(set(old_files) - set(new_files)), 'changed': {}}
    for rel in sorted(set(old_files) & set(new_files)):
        a = old_files[rel].read_text(encoding='utf-8', errors='replace')
        b = new_files[rel].read_text(encoding='utf-8', errors='replace')
        if a == b:
            continue
        da, db = declarations(a), declarations(b)
        sa, sb = set(da), set(db)
        report['changed'][rel] = {'gone': [d for d in da if d not in sb], 'new': [d for d in db if d not in sa]}
    return report


def touched_names(report, old_root, new_root=None):
    """Names a plugin may trip over: names that no longer appear anywhere in the new headers (gone or
    renamed), plus the service size requirements whose definition changed."""
    gone = []
    for rel in report['removed']:
        gone += declarations((Path(old_root) / 'include' / rel).read_text(encoding='utf-8', errors='replace'))
    for change in report['changed'].values():
        gone += change['gone']
    touched = names(gone)
    if new_root is not None:
        still = set()
        for p in (Path(new_root) / 'include').rglob('*'):
            if p.is_file():
                still |= set(re.findall(r'[A-Za-z_]\w+', p.read_text(encoding='utf-8', errors='replace')))
        touched = {n for n in touched if n not in still}
    return touched | {g['name'] for g in grown_requirements(report, old_root, new_root) if g['grew']}


def uses(mods, touched):
    out = {}
    for name, _, sources in plugins(mods):
        text = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in sources)
        words = set(re.findall(r'[A-Za-z_]\w+', text))
        hit = sorted(words & touched)
        if hit:
            out[name] = hit
    return out


# ------------------------------------------------------------------ commands

def loader_verdict(mods, grown, use, added=()):
    """Whether the newest published loader can serve plugins rebuilt with the new headers.

    The SDK repo moves ahead of the loader: its master describes the next loader release. When the
    newest release on d2rloader.net is still the one installed here and a service size requirement
    grew (and a plugin checks it), rebuilding now would make those plugins treat the service as
    missing. `added`: size requirements only the new headers have (features the next loader brings).
    Returns (ok, text)."""
    here = installed_loader(mods)
    latest = latest_loader()
    checked = sorted({g['name'] for g in grown if g['grew'] for hits in use.values() if g['name'] in hits})
    newer = latest and here['version'] and latest['version'] != here['version']
    lines = ['loader installed : %s (D2RLoader.exe built %s)' % (here['version'] or 'unknown', here['built'] or '?'),
             'loader published : %s (d2rloader.net manifest)%s' % (latest['version'] if latest else 'unknown (offline?)',
                                                                    ': NEWER, install it with its installer' if newer else '')]
    if added:
        lines.append('new in upstream  : %s - features of the next loader release; a plugin can use them only'
                     % ', '.join(n.replace('RequiredSize', '') for n in added))
        lines.append('                   once that loader is installed (check the service size at run time)')
    if not checked:
        return True, '\n'.join(lines + ['no plugin checks a service size that grew: rebuilding with the new headers keeps '
                                        'every plugin working on the installed loader'])
    if latest and not newer and latest['files'].get('D2RLoader.exe') in (None, here['size']):
        return False, '\n'.join(lines + [
            'WAIT: %s grew, and plugins check it; the newest published loader is the one installed,' % ', '.join(checked),
            '      so these headers belong to the next loader release. Rebuilt now, those plugins would treat',
            '      the service as missing. Update the loader first (its installer), then run apply.'])
    return True, '\n'.join(lines + ['a newer loader is published (%s): install it, then apply' % latest['version'] if newer else
                                    'loader state unknown: apply only if the loader provides the new fields of %s' % ', '.join(checked)])


def cmd_status(args, mods, sdk):
    print('installed SDK    : %s (%s)' % (sdk_version(sdk) or 'missing', sdk))
    if not args.offline:
        root, sha = fetch(args.ref)
        print('upstream %-8s: %s (commit %s)' % (args.ref, sdk_version(root), sha[:12]))
        report = header_diff(sdk, root)
        grown = grown_requirements(report, sdk, root)
        print(loader_verdict(mods, grown, uses(mods, touched_names(report, sdk, root)), added_requirements(sdk, root))[1])
    else:
        print('loader installed : %s' % (loader_version(mods) or 'unknown'))
    kept = sorted(p.name for p in sdk.parent.glob('sdk-*') if p.is_dir())
    print('kept copies      : %s' % (', '.join(kept) or 'none'))
    print('plugins          : %s' % ', '.join(n for n, _, _ in plugins(mods)))


def print_diff(report, use, old_v, new_v):
    print('SDK %s -> %s' % (old_v.get('sdk', '?'), new_v.get('sdk', '?')))
    for key in ('abi', 'minAbi'):
        if old_v.get(key) != new_v.get(key):
            print('  %s: %s -> %s' % (key, old_v.get(key), new_v.get(key)))
    if report['added']:
        print('headers added  : ' + ', '.join(report['added']))
    if report['removed']:
        print('headers REMOVED: ' + ', '.join(report['removed']))
    for rel, change in report['changed'].items():
        print('changed %s (-%d +%d declarations)' % (rel, len(change['gone']), len(change['new'])))
        for d in change['gone'][:12]:
            print('    - ' + d[:150])
        for d in change['new'][:12]:
            print('    + ' + d[:150])
        more = max(0, len(change['gone']) - 12) + max(0, len(change['new']) - 12)
        if more:
            print('    ... %d more' % more)
    if use:
        print('plugins using names that are gone or whose size requirement changed (check these first):')
        for name, hit in use.items():
            print('  %-24s %s' % (name, ', '.join(hit[:15]) + (' ...' if len(hit) > 15 else '')))
    else:
        print('no plugin uses a name that is gone or whose size requirement changed')


def cmd_diff(args, mods, sdk):
    root, sha = fetch(args.ref)
    report = header_diff(sdk, root)
    use = uses(mods, touched_names(report, sdk, root))
    print_diff(report, use, sdk_version(sdk), sdk_version(root))
    grown = grown_requirements(report, sdk, root)
    if grown:
        print('service size requirements that changed (a plugin checking one needs a loader with the new fields):')
        for g in grown:
            users = [n for n, hits in use.items() if g['name'] in hits]
            size = '%s -> %s bytes' % (g['old'], g['new']) if g['old'] is not None else 'value unknown'
            print('  %-36s %-18s %s' % (g['name'], size, ('checked by ' + ', '.join(users)) if users else 'no plugin checks it'))
    ok, verdict = loader_verdict(mods, grown, use, added_requirements(sdk, root))
    print(verdict)
    if args.json:
        Path(args.json).write_text(json.dumps({'commit': sha, 'diff': report, 'uses': use, 'grown': grown, 'loaderOk': ok}, indent=1), encoding='utf-8')
    return report, use, root, sha, ok


def cmd_apply(args, mods, sdk):
    report, use, root, sha, loader_ok = cmd_diff(args, mods, sdk)
    old_v, new_v = sdk_version(sdk), sdk_version(root)
    if not report['added'] and not report['removed'] and not report['changed']:
        print('the headers are the same; nothing to apply')
        return
    if not loader_ok and not args.force:
        fail('not applied: these headers need the next loader release (see WAIT above). --force applies anyway.')
    keep = sdk.parent / ('sdk-' + old_v.get('sdk', 'previous'))
    n = 1
    while keep.exists():
        n += 1
        keep = sdk.parent / ('sdk-%s-%d' % (old_v.get('sdk', 'previous'), n))
    shutil.copytree(sdk, keep)
    for item in KEEP:
        src, dst = root / item, sdk / item
        if dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.exists():
            shutil.copy2(src, dst)
    (sdk / 'UPSTREAM.txt').write_text('github.com/%s commit %s (ref %s), SDK %s\n' % (REPO, sha, args.ref, new_v.get('sdk')), encoding='utf-8')
    print('SDK %s -> %s; the old copy is kept as %s' % (old_v.get('sdk'), new_v.get('sdk'), keep.name))
    if args.no_build:
        return
    print('rebuilding the plugins:')
    results = rebuild_all(mods)
    bad = [r['plugin'] for r in results if not r['ok']]
    if bad:
        print('%d plugin(s) fail with the new SDK: %s. Fix them, or go back with: restore' % (len(bad), ', '.join(bad)))
        sys.exit(1)
    print('all plugins build. Installed DLLs are unchanged: copy the new ones from each dist\\ when ready.')


def cmd_trial(args, mods, sdk):
    root, sha = fetch(args.ref)
    print('building every plugin against SDK %s (%s, commit %s) in a temp folder; nothing is replaced:'
          % (sdk_version(root).get('sdk'), args.ref, sha[:12]))
    results = trial_all(mods, root)
    bad = [r['plugin'] for r in results if not r['ok']]
    print('%d of %d build with these headers%s' % (len(results) - len(bad), len(results), ('; fix: ' + ', '.join(bad)) if bad else ''))
    if bad:
        sys.exit(1)


def cmd_restore(args, mods, sdk):
    kept = sorted((p for p in sdk.parent.glob('sdk-*') if p.is_dir()), key=lambda p: p.stat().st_mtime)
    if args.to:
        kept = [p for p in kept if p.name == 'sdk-' + args.to]
    if not kept:
        fail('no kept SDK copy%s next to %s' % (' for ' + args.to if args.to else '', sdk))
    back = kept[-1]
    cur = sdk_version(sdk).get('sdk', 'current')
    aside = sdk.parent / ('sdk-' + cur)
    if aside.exists():
        aside = sdk.parent / ('sdk-%s-replaced' % cur)
        shutil.rmtree(aside, ignore_errors=True)
    sdk.rename(aside)
    back.rename(sdk)
    print('SDK %s is back; %s is kept as %s' % (sdk_version(sdk).get('sdk'), cur, aside.name))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['status', 'diff', 'trial', 'apply', 'rebuild', 'restore'])
    ap.add_argument('--mods', help='the game\'s mods folder (default: %%D2R_PATH%%\\mods)')
    ap.add_argument('--sdk', help='the shared SDK copy (default: <mods>\\SkillTab4\\sdk)')
    ap.add_argument('--ref', default='master', help='upstream branch, tag or commit (default: master)')
    ap.add_argument('--to', help='restore: the version to put back (default: the newest kept copy)')
    ap.add_argument('--no-build', action='store_true', help='apply: swap the SDK only')
    ap.add_argument('--force', action='store_true', help='apply even when the headers need a newer loader than the published one')
    ap.add_argument('--offline', action='store_true', help='status: skip the upstream lookup')
    ap.add_argument('--json', help='diff/apply: also write the diff as JSON')
    args = ap.parse_args()
    mods = Path(args.mods or Path(os.environ.get('D2R_PATH', '')) / 'mods')
    if not mods.is_dir():
        fail('no mods folder at %s: pass --mods <game>\\mods (or set D2R_PATH)' % mods)
    sdk = Path(args.sdk) if args.sdk else mods / SDK_REL
    if args.command != 'restore' and not (sdk / 'include').is_dir():
        fail('no SDK copy at %s' % sdk)
    {'status': cmd_status, 'diff': cmd_diff, 'trial': cmd_trial, 'apply': cmd_apply, 'restore': cmd_restore,
     'rebuild': lambda a, m, s: rebuild_all(m)}[args.command](args, mods, sdk)


if __name__ == '__main__':
    main()
