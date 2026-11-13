"""Reads D2RLoader's log and lists what the game itself complained about.

D2RLoader writes every failed game check ("ASSERTION - a game check failed") to
<game>\\d2rloader\\logs\\d2rloader.log, with the source file of the check and, for
data tables, the file, row, column and cell that caused it. The log covers the
last game session. Read it first when something misbehaves in the game: a value
the game does not accept is usually named here.

usage:
  LoaderLog.py --game <D2R folder> [--all] [--plugins]

  default    one entry per distinct check, with the time it first fired, how often,
             and the table cell when the game named one
  --all      every occurrence, in order
  --plugins  also the plugin load results and each plugin's own log lines
"""
import argparse
import collections
import os
import re
import sys


def blocks(lines):
    """Yields (line number, time, text before, [body lines]) for each assertion box."""
    i = 0
    while i < len(lines):
        if '[ERROR]' in lines[i] and i + 1 < len(lines) and lines[i + 1].startswith('+---'):
            j = i + 2
            body = []
            while j < len(lines) and not lines[j].startswith('+---'):
                body.append(lines[j].strip('| ').rstrip())
                j += 1
            m = re.match(r'\[([^\]]+)\]', lines[i])
            yield i + 1, m.group(1) if m else '', body
            i = j
        i += 1


def field(body, name):
    """A 'Name : value' field of the box; values wrap onto following lines."""
    out = []
    taking = False
    for line in body:
        m = re.match(r'([A-Za-z ]+?)\s*:\s?(.*)$', line)
        if m and m.group(1).strip() in ('Message', 'Action', 'Scope', 'Location', 'Caller', 'ID', 'Details', 'Help', 'TXT', 'Row name', 'Cell value'):
            taking = m.group(1).strip() == name
            if taking:
                out.append(m.group(2))
        elif line.startswith('Stack'):
            taking = False
        elif taking:
            out.append(line)
    return ' '.join(x for x in out if x).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--plugins', action='store_true')
    args = ap.parse_args()
    if not args.game:
        ap.error('pass --game or set D2R_PATH')
    path = os.path.join(args.game, 'd2rloader', 'logs', 'd2rloader.log')
    if not os.path.exists(path):
        print('no log at', path)
        return 2
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    first = next((re.match(r'\[([^\]]+)\]', l).group(1) for l in lines if l.startswith('[')), '?')
    out = ['log: %s (session started %s)' % (path, first)]
    found = list(blocks(lines))
    groups = collections.OrderedDict()
    for number, when, body in found:
        key = (field(body, 'Message'), field(body, 'Location'))
        groups.setdefault(key, []).append((number, when, body))
    out.append('%d failed game check(s), %d distinct' % (len(found), len(groups)))
    for (message, location), items in groups.items():
        shown = items if args.all else items[:1]
        for number, when, body in shown:
            out.append('')
            out.append('%s  x%d  %s' % (when, len(items), message))
            out.append('    where: %s (log line %d)' % (location or '?', number))
            for name in ('Details', 'TXT', 'Row name', 'Cell value', 'Help'):
                value = field(body, name)
                if value:
                    out.append('    %s: %s' % (name.lower(), value))
    if args.plugins:
        out.append('')
        for l in lines:
            if re.search(r'\[(PLUGIN|PATCH|SKIP|DETAIL)\]|Plugin could not|\[Plugin:', l):
                out.append(re.sub(r'^\[[^\]]+\]\s*', '', l).strip(' ├│└'))
    text = '\n'.join(out) + '\n'
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
