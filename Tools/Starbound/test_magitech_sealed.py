"""Run the mod's installed postLoad script under a Lua runtime with a mock `assets`, and compare every unsealed sound
with the loose backup."""
import os, sys, time
from lupa import LuaRuntime
M = r"F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
B = r"F:\Games\OpenStarbound\dev\Magi-Tech\audio_loose"
script = open(os.path.join(M, "scripts", "magitech", "audio_unseal.lua"), encoding="utf-8").read()
blob = open(os.path.join(M, "sfx", "magitech", "sounds.mtsa"), "rb").read()
added = {}
logs = []
L = LuaRuntime(unpack_returned_tuples=True, encoding=None)
g = L.globals()
g[b"assets"] = L.table_from({b"bytes": lambda path: blob, b"add": lambda path, data: added.__setitem__(path.decode("utf-8"), bytes(data))})
g[b"print"] = lambda *a: logs.append(b" ".join(x if isinstance(x, bytes) else str(x).encode() for x in a).decode())
t = time.time(); L.execute(script); dt = time.time() - t
print("\n".join(logs), f"| {dt:.2f} s")
bad = 0
for path, data in added.items():
    rel = path.lstrip("/")
    disk = os.path.join(B, rel) if rel.startswith("sfx") else os.path.join(B, "interface_magitech_sounds", os.path.basename(rel))
    if not os.path.exists(disk) or open(disk, "rb").read() != data:
        bad += 1
print(f"{len(added)} sounds unsealed by the installed script, {bad} differ from the backup")
