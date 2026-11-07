#!/usr/bin/env python3
"""tx_scan_obsolete_designs.py <current TransCore> <Extensions folder> - list mod references to TransCore design types
retired (obsoleteVersion) at or below the mod API. Report only; see tx_fix_obsolete_images.py for ship images."""
import re, sys, os, glob
core, ext = sys.argv[1], sys.argv[2]
C = re.compile(r'<!--.*?-->', re.S)
def rd(p): return C.sub('', open(p,'rb').read().decode('utf-8','replace'))
ent = {}
cf = glob.glob(os.path.join(core,'**','*.xml'), recursive=True)
for f in cf:
    for n,v in re.findall(r'<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"', rd(f)): ent[n.lower()] = int(v,16)
obs = {}
for f in cf:
    for m in re.finditer(r'<(\w+)\s+(?:UNID|unid)="&(\w+);"([^>]*)>', rd(f)):
        o = re.search(r'obsoleteVersion\s*=\s*"(\d+)"', m.group(3))
        if o and m.group(1) != 'Image' and m.group(2).lower() in ent:
            obs[ent[m.group(2).lower()]] = (m.group(1), m.group(2), int(o.group(1)))
defined_in_mods = set()
files = glob.glob(os.path.join(ext,'**','*.xml'), recursive=True)
for f in files:
    t = rd(f)
    loc = {n.lower(): int(v,16) for n,v in re.findall(r'<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"', t)}
    for m in re.finditer(r'<\w+\s+(?:UNID|unid)="&(\w+);"', t):
        u = loc.get(m.group(1).lower(), ent.get(m.group(1).lower()))
        if u: defined_in_mods.add(u)
for d in sorted(os.listdir(ext)):
    p = os.path.join(ext, d)
    if not os.path.isdir(p): continue
    fs = glob.glob(os.path.join(p,'**','*.xml'), recursive=True)
    apis = [int(a) for f in fs for a in re.findall(r'<Transcendence(?:Extension|Library|Adventure)\b[^>]*?apiVersion="(\d+)"', rd(f), re.S)]
    api = max(apis) if apis else None
    hits = {}
    for f in fs:
        t = rd(f)
        loc = {n.lower(): int(v,16) for n,v in re.findall(r'<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"', t)}
        body = re.sub(r'<!DOCTYPE.*?\]>', '', t, flags=re.S)
        for m in re.finditer(r'&(\w+);', body):
            u = loc.get(m.group(1).lower(), ent.get(m.group(1).lower()))
            if u in obs and u not in defined_in_mods and (api is None or api >= obs[u][2]):
                hits.setdefault(obs[u], set()).add(os.path.basename(f))
    for (tag, name, ov), fl in hits.items():
        print(f'{d} | {tag} {name} (retired API {ov}, mod API {api}) | {", ".join(sorted(fl))}')
