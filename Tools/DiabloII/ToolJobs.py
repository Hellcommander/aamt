"""A job queue for the community tools in Tools/DiabloII/third_party (downloads, not part of the
toolkit): an assistant or a script queues jobs, a person runs them, and the results come back
as files that can be read and compared.

Why a queue: those tools are executables from outside. The toolkit's own scripts (and the AI
assistant working on it) do not start them. A job only describes a run of one known tool with
arguments built from a fixed pattern; nothing runs until someone starts `run` (or double-clicks
Drop\\Run tool jobs.bat), which lists the exact command lines first and asks.

    python ToolJobs.py tools                               the tools a job can use
    python ToolJobs.py add noesis-export <model> [--to obj,smd,dae]     queue: Noesis converts a .model / .skeleton
    python ToolJobs.py add animdata-extract <animdata.d2>               queue: animdata.d2 -> animdata.txt
    python ToolJobs.py add animdata-pack <animdata.txt>                 queue: animdata.txt -> animdata.d2
    python ToolJobs.py list                                pending and finished jobs
    python ToolJobs.py run [--yes]                         (a person) run the pending jobs
    python ToolJobs.py show <job>                          a finished job's result: exit codes, output, files
    python ToolJobs.py compare <job>                       noesis-export: what Noesis read against what Granny.py reads

Jobs and results live in Tools/Output/ToolJobs (git-ignored): pending/<id>.json, done/<id>.json,
and <id>/ with the copies the tool worked on and what it wrote. A tool always works on a copy in
the job's folder, never on the file that was queued.

Tools known here (paths under third_party; each is looked up when a job is added and again when
it runs): Noesis 4.x with the GR2 reader script v1.3.5 (`?cmode <in> <out>`), Paul Siramy's
animdata_edit (2002). Tools with only a window (MoPaH, SpriteEditor, the DS1 editor) cannot be
queued: they have no command line.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THIRD = os.path.join(HERE, 'third_party')
QUEUE = os.path.normpath(os.path.join(HERE, '..', 'Output', 'ToolJobs'))

TOOLS = {
    'noesis-export': {
        'exe': os.path.join('D2RM_Noesis+Plugins', 'Noesis64.exe'),
        'about': 'Noesis reads a .model / .skeleton with its GR2 script and writes it out again as OBJ / SMD / DAE / FBX / glTF',
        'input': ('.model', '.skeleton', '.gr2'), 'formats': ('obj', 'smd', 'dae', 'fbx', 'gltf'),
    },
    'animdata-extract': {
        'exe': os.path.join('D2RM_AnimData_Editor', 'AnimData Editor', 'animdata_edit.exe'),
        'about': 'animdata.d2 -> animdata.txt', 'input': ('.d2',),
    },
    'animdata-pack': {
        'exe': os.path.join('D2RM_AnimData_Editor', 'AnimData Editor', 'animdata_edit.exe'),
        'about': 'animdata.txt -> animdata.d2', 'input': ('.txt',),
    },
}


def _exe(tool):
    path = os.path.join(THIRD, TOOLS[tool]['exe'])
    if not os.path.isfile(path):
        raise SystemExit(f'{tool}: {path} is not there')
    return path


def _commands(job, folder):
    """The command lines of a job, built here from its tool and files; a job file holds no command."""
    tool, exe = job['tool'], _exe(job['tool'])
    source = os.path.join(folder, job['copy'])
    if tool == 'noesis-export':
        stem = os.path.splitext(job['copy'])[0]
        # Noesis picks a reader by file extension; its GR2 script takes .model and .skeleton.
        return [([exe, '?cmode', source, os.path.join(folder, f'{stem}.{fmt}')], folder) for fmt in job['formats']]
    if tool in ('animdata-extract', 'animdata-pack'):
        return [([exe, job['copy']], folder)]         # the tool writes beside its input, in the job folder
    raise SystemExit(f'unknown tool {tool}')


def add(args):
    tool = args.tool
    if tool not in TOOLS:
        raise SystemExit(f'unknown tool {tool}; known: {", ".join(TOOLS)}')
    _exe(tool)
    source = os.path.abspath(args.file)
    if not os.path.isfile(source):
        raise SystemExit(f'{source} is not a file')
    if not source.lower().endswith(TOOLS[tool]['input']):
        raise SystemExit(f'{tool} takes {" / ".join(TOOLS[tool]["input"])} files')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    number = len(os.listdir(os.path.join(QUEUE, 'pending'))) if os.path.isdir(os.path.join(QUEUE, 'pending')) else 0
    job_id = f'{stamp}-{number:02d}-{tool}'
    folder = os.path.join(QUEUE, job_id)
    os.makedirs(folder)
    os.makedirs(os.path.join(QUEUE, 'pending'), exist_ok=True)
    name = os.path.basename(source)
    if tool.startswith('animdata'):
        name = 'animdata' + os.path.splitext(name)[1].lower()          # the tool knows these two names
    shutil.copyfile(source, os.path.join(folder, name))
    job = {'id': job_id, 'tool': tool, 'source': source, 'copy': name, 'queued': stamp, 'note': args.note or ''}
    if tool == 'noesis-export':
        formats = [f.strip().lower() for f in (args.to or 'obj,smd').split(',') if f.strip()]
        bad = [f for f in formats if f not in TOOLS[tool]['formats']]
        if bad:
            raise SystemExit(f'noesis-export writes {", ".join(TOOLS[tool]["formats"])}, not {", ".join(bad)}')
        job['formats'] = formats
    with open(os.path.join(QUEUE, 'pending', job_id + '.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(job, f, indent=1)
    print(f'queued {job_id}')
    print('  it runs when someone starts: python ToolJobs.py run   (or Drop\\Run tool jobs.bat)')
    return job_id


def _jobs(state):
    folder = os.path.join(QUEUE, state)
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        if name.endswith('.json'):
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                out.append(json.load(f))
    return out


def listing(args):
    for state in ('pending', 'done'):
        for job in _jobs(state):
            result = ''
            if state == 'done':
                result = ' | exit ' + ','.join(str(r['exit']) for r in job.get('runs', [])) + f" | {len(job.get('files', []))} files"
            print(f"{state:8} {job['id']} | {os.path.basename(job['source'])}{result}{' | ' + job['note'] if job.get('note') else ''}")
    if not _jobs('pending') and not _jobs('done'):
        print('no jobs')


def run(args):
    pending = _jobs('pending')
    if not pending:
        print('no pending jobs')
        return 0
    plan = []
    for job in pending:
        folder = os.path.join(QUEUE, job['id'])
        for command, cwd in _commands(job, folder):
            plan.append((job, command, cwd))
    print('These programs from Tools\\DiabloII\\third_party will be started (downloaded tools, not part of the toolkit):\n')
    for job, command, cwd in plan:
        print('  ' + ' '.join(f'"{c}"' if ' ' in c else c for c in command))
    if not args.yes:
        if input(f'\nRun these {len(plan)} commands? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('nothing run')
            return 1
    os.makedirs(os.path.join(QUEUE, 'done'), exist_ok=True)
    for job in pending:
        folder = os.path.join(QUEUE, job['id'])
        before = set(os.listdir(folder))
        job['runs'] = []
        for command, cwd in _commands(job, folder):
            try:
                done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors='replace', timeout=args.timeout)
                job['runs'].append({'command': command, 'exit': done.returncode, 'stdout': done.stdout[-6000:], 'stderr': done.stderr[-3000:]})
            except subprocess.TimeoutExpired:
                job['runs'].append({'command': command, 'exit': 'timeout', 'stdout': '', 'stderr': f'stopped after {args.timeout} s'})
            except OSError as error:
                job['runs'].append({'command': command, 'exit': 'not started', 'stdout': '', 'stderr': str(error)})
        job['files'] = sorted(n for n in os.listdir(folder) if n not in before)
        job['finished'] = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        with open(os.path.join(QUEUE, 'done', job['id'] + '.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(job, f, indent=1)
        os.remove(os.path.join(QUEUE, 'pending', job['id'] + '.json'))
        print(f"{job['id']}: exit {', '.join(str(r['exit']) for r in job['runs'])}; new files: {', '.join(job['files']) or 'none'}")
    return 0


def _done(job_id):
    matches = [j for j in _jobs('done') if j['id'] == job_id or j['id'].startswith(job_id)]
    if not matches:
        raise SystemExit(f'no finished job {job_id} (python ToolJobs.py list)')
    return matches[-1]


def show(args):
    job = _done(args.job)
    print(json.dumps({k: v for k, v in job.items() if k != 'runs'}, indent=1))
    for r in job['runs']:
        print('---', ' '.join(r['command'][-2:]), '-> exit', r['exit'])
        print((r['stdout'] + r['stderr']).strip()[-2500:])


def read_obj(path):
    """(vertex count, triangle count, box) of a Wavefront OBJ."""
    import numpy as np
    points, triangles = [], 0
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('v '):
                points.append([float(x) for x in line.split()[1:4]])
            elif line.startswith('f '):
                triangles += max(0, len(line.split()) - 3)
    p = np.array(points) if points else np.zeros((0, 3))
    return len(points), triangles, (p.min(0).round(4).tolist(), p.max(0).round(4).tolist()) if len(p) else None


def read_smd(path):
    """({bone number: (name, parent number)}, triangle count, bones used by vertices) of a Valve SMD."""
    bones, triangles, used = {}, 0, set()
    section = None
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = [line.strip() for line in f]
    k = 0
    while k < len(lines):
        line = lines[k]
        if line in ('nodes', 'skeleton', 'triangles'):
            section = line
        elif line == 'end':
            section = None
        elif section == 'nodes' and line:
            number, rest = line.split(None, 1)
            name = rest[rest.index('"') + 1:rest.rindex('"')]
            bones[int(number)] = (name, int(rest[rest.rindex('"') + 1:].split()[0]))
        elif section == 'triangles' and line:
            triangles += 1                                   # a material line, then three vertex lines
            for vertex in lines[k + 1:k + 4]:
                parts = vertex.split()
                used.add(int(parts[0]))
                if len(parts) > 9:
                    for j in range(int(parts[9])):
                        used.add(int(parts[10 + 2 * j]))
            k += 3
        k += 1
    return bones, triangles, used


def compare(args):
    """What Noesis wrote for a queued model against what the toolkit's own reader sees in it."""
    import numpy as np
    sys.path.insert(0, HERE)
    import Granny
    import GrannyMesh
    job = _done(args.job)
    if job['tool'] != 'noesis-export':
        raise SystemExit('compare is for noesis-export jobs')
    folder = os.path.join(QUEUE, job['id'])
    with open(os.path.join(folder, job['copy']), 'rb') as f:
        tree = Granny.read(f.read()).root()
    meshes = list(tree.get('Meshes') or [])
    mine = {'triangles': sum(len(m['PrimaryTopology']['Indices16'] or m['PrimaryTopology']['Indices']) // 3 for m in meshes),
            'vertices': sum(len(m['PrimaryVertexData']['Vertices']['$items']) for m in meshes),
            'bones': [b['Name'] for b in tree['Skeletons'][0]['Bones']] if tree.get('Skeletons') else []}
    if meshes:
        boxes = [GrannyMesh._Geometry(tree, m).positions for m in meshes]
        every = np.concatenate(boxes)
        mine['box'] = (every.min(0).round(4).tolist(), every.max(0).round(4).tolist())
    print(f"{job['copy']}: Granny.py reads {mine['vertices']} vertices, {mine['triangles']} triangles, {len(mine['bones'])} bones, box {mine.get('box')}")
    stem = os.path.splitext(job['copy'])[0]
    seen = False
    obj = os.path.join(folder, stem + '.obj')
    if os.path.isfile(obj):
        seen = True
        vertices, triangles, box = read_obj(obj)
        print(f'  Noesis OBJ: {vertices} vertices, {triangles} triangles, box {box}')
        print(f"    triangles {'agree' if triangles == mine['triangles'] else 'DIFFER'}"
              f" (a vertex count may differ: exporters split or join vertices; the box may differ by Noesis' own axis and unit choice)")
    smd = os.path.join(folder, stem + '.smd')
    if os.path.isfile(smd):
        seen = True
        bones, triangles, used = read_smd(smd)
        names = [bones[k][0] for k in sorted(bones)]
        missing = [n for n in mine['bones'] if n not in names]
        extra = [n for n in names if n not in mine['bones']]
        print(f'  Noesis SMD: {len(names)} bones, {triangles} triangles, {len(used)} bones used by vertices')
        print(f"    bone names {'agree' if not missing and not extra else 'DIFFER'}"
              + (f'; missing in Noesis: {missing[:8]}' if missing else '') + (f'; only in Noesis: {extra[:8]}' if extra else ''))
        parents = {bones[k][0]: (bones[bones[k][1]][0] if bones[k][1] in bones else None) for k in bones}
        own = tree['Skeletons'][0]['Bones'] if tree.get('Skeletons') else []
        wrong = [b['Name'] for b in own if b['Name'] in parents and parents[b['Name']] != (own[b['ParentIndex']]['Name'] if b['ParentIndex'] >= 0 else None)]
        print(f"    bone parents {'agree' if not wrong else 'DIFFER for ' + ', '.join(wrong[:8])}")
    if not seen:
        print('  no OBJ or SMD in the job folder: Noesis wrote nothing readable (python ToolJobs.py show ' + job['id'] + ')')


def main(argv):
    parser = argparse.ArgumentParser(description='Queue jobs for the downloaded community tools; a person runs them.')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('tools')
    a = sub.add_parser('add')
    a.add_argument('tool')
    a.add_argument('file')
    a.add_argument('--to', help='noesis-export: formats, e.g. obj,smd')
    a.add_argument('--note')
    sub.add_parser('list')
    r = sub.add_parser('run')
    r.add_argument('--yes', action='store_true', help='do not ask before starting the programs')
    r.add_argument('--timeout', type=int, default=180)
    s = sub.add_parser('show')
    s.add_argument('job')
    c = sub.add_parser('compare')
    c.add_argument('job')
    args = parser.parse_args(argv)
    if args.command == 'tools':
        for name, tool in TOOLS.items():
            there = os.path.isfile(os.path.join(THIRD, tool['exe']))
            print(f"{name:18} {tool['about']}\n{'':18} {tool['exe']} ({'found' if there else 'NOT FOUND'})")
        return 0
    return {'add': add, 'list': listing, 'run': run, 'show': show, 'compare': compare}[args.command](args) or 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
