"""Two Worlds II animation tools, run from the toolkit.

The tools themselves live with the mod, in <TW2>\\_modding\\tools, because the WorldMerge Reforged patcher
(tw2patch) runs them at build time and players only get that folder. This dispatcher finds that folder
(TW2_MODDING, else the Steam paths below) and runs the tool in place, so there is one copy of the code.

usage:
  python tw2anim.py chm   info|roundtrip|tree|export|append ...   .chm skeleton/animation files (chm.py)
  python tw2anim.py pose  sheet|check ...                          pose a skeleton, contact sheets (chm_pose.py)
  python tw2anim.py clip  make FILE.chm PRESET.json OUT.json [--sheet OUT.png]   new clips (chm_clip.py)
  python tw2anim.py where                                          print the _modding folder in use

Contact sheets need Pillow (the toolkit's Python has it); the tools themselves are pure Python.
"""
import os, runpy, sys

CANDIDATES = [
    os.environ.get('TW2_MODDING', ''),
    r'D:\games\Steam\steamapps\common\Two Worlds II\_modding',
    r'E:\SteamLibrary\steamapps\common\Two Worlds II\_modding',
]
TOOLS = {'chm': 'chm.py', 'pose': 'chm_pose.py', 'clip': 'chm_clip.py'}


def modding():
    for c in CANDIDATES:
        if c and os.path.isfile(os.path.join(c, 'tools', 'chm.py')):
            return c
    raise SystemExit('Two Worlds II _modding folder not found: set TW2_MODDING')


def main(a):
    if not a or a[0] not in TOOLS and a[0] != 'where':
        print(__doc__); return 2
    m = modding()
    if a[0] == 'where':
        print(m); return 0
    tools = os.path.join(m, 'tools')
    sys.path.insert(0, tools)
    sys.argv = [os.path.join(tools, TOOLS[a[0]])] + a[1:]
    runpy.run_path(sys.argv[0], run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
