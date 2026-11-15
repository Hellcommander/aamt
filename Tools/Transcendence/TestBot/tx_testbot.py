#!/usr/bin/env python3
"""
tx_testbot.py - drive Transcendence with the TX Test Bot and report what broke.

Needs a game exe built with Fix-TranscendenceForkGaps.py "features" (TX_TESTBOT test mode: no menus) and
"diagnostics" (TxCrash.log, on-demand TxHang.log).

Modes:
  ships  (default) one short game per starting ship the new-game screen offers in the adventure: the bot checks the
         player ship (class, image, installed armor and devices) and that the game keeps running for --survive
         seconds. A crash or popup is pinned to that ship.
  full   one game that runs every bot phase: extensions, all types, focus items (create/add/install), focus ship
         classes (spawned in fighting pairs), focus stations, WeaponLabs custom builds, stargate jumps.
  both   ships, then full.

Every run:
  - refuses to start while the game is running
  - backs up Settings.xml (also as Settings.xml.txbot_backup in the game folder; an interrupted run is restored
    first next time) and lowers it for testing: windowed 1024x768, minimum graphics, no 3D extras, no music/sound,
    no network downloads; adds this folder's extension\\ to the extension folders
  - starts Transcendence.exe /windowed /1024 /nosound /debug without taking focus, with TX_TESTBOT set
  - stops on TXBOT: DONE, a popup, an engine crash, the game exiting, a stall (then asks for a hang dump) or a timeout
  - ALWAYS restores Settings.xml at the end
  - writes report.md / summary.json: one line per distinct problem with a count and the source, grouped into
    engine crashes, popups, bot check failures, mod script errors and warnings

Usage:
  python tx_testbot.py [--mode ships|full|both] [--adventure 0x200000] [--ship 0x3801] [--survive 20]
                       [--focus E1270000-E127FFFF] [--expect E1271000] [--hops 3] [--timeout 900]

Exit code 0 = no engine crash, popup or bot failure; 1 = problems found; 2 = did not run.
"""
from __future__ import annotations

import argparse, json, os, re, shutil, subprocess, sys, time
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_GAME = Path(r"D:\games\Steam\steamapps\common\Transcendence")
OUT_ROOT = HERE.parent.parent / "Output" / "Transcendence" / "testbot"
BOT_UNID = "E7E57000"
BACKUP_SIDECAR = "Settings.xml.txbot_backup"

# CrossMod and its libraries, WeaponLabs 51
DEFAULT_FOCUS = ["E1270000-E127FFFF", "D7897000-D78970FF"]
DEFAULT_EXPECT = ["E1271000", "D7897000"]

LOW_SETTINGS = {
    "windowedMode": "true", "force1024": "true", "force1280": "false", "force600": "false",
    "maxResolution": "768", "graphicsQuality": "minimum", "no3DExtras": "true", "no3DSystemMap": "true",
    "noMusic": "true", "noSound": "true", "uncappedFrameRate": "false",
    "noAutoUpdate": "true", "noCollectionDownload": "true",
}

ENGINE_CRASH = re.compile(r"Unable to continue due to program error|^\s*Crash in |CException:|\[crash\] \S+: exception")
NOISE = re.compile(r"Unable to initialize sound manager|MCI ERROR|Armor segments do not cover|^\s*\[crash\]\s+\d+:", re.I)
SCRIPT = re.compile(r"###|Unknown function|No binding for symbol|Invalid property|Exception in ")
WARNING = re.compile(r"WARNING|deprecated", re.I)
ISSUE = re.compile(r"error|exception|unable|cannot|crash|failed|invalid|unknown|warning|deprecated", re.I)


# ---------------------------------------------------------------- settings

def game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Transcendence.exe"], capture_output=True, text=True).stdout
    return "Transcendence.exe" in out


def set_option(xml: str, name: str, value: str) -> str:
    pat = re.compile(r'(<Option name="' + re.escape(name) + r'"\s+value=")[^"]*(")')
    if pat.search(xml):
        return pat.sub(lambda m: m.group(1) + value + m.group(2), xml, count=1)
    return xml.replace("</TranscendenceSettings>", f'\t<Option name="{name}"\tvalue="{value}"/>\n</TranscendenceSettings>', 1)


def lowered_settings(raw: bytes, ext_folder: Path) -> bytes:
    bom = raw.startswith(b"\xef\xbb\xbf")
    xml = raw[3 if bom else 0:].decode("utf-8")
    for k, v in LOW_SETTINGS.items():
        xml = set_option(xml, k, v)
    tag = f'\t<ExtensionFolder path="{ext_folder}"/>\n'
    if tag not in xml:
        xml = re.sub(r"(<TranscendenceSettings>\s*\n)", lambda m: m.group(1) + tag, xml, count=1)
    return (b"\xef\xbb\xbf" if bom else b"") + xml.encode("utf-8")


# ---------------------------------------------------------------- bot config

def unid(s: str) -> int:
    return int(s, 16)


def tlisp_hex(v: int) -> str:
    return f"0x{v:08X}"


def write_config(path: Path, mode: str, focus: list[str], expect: list[str], hops: int, ship: int | None, survive: int,
                 immortal: bool = True) -> None:
    ranges = []
    for f in focus:
        lo, _, hi = f.partition("-")
        ranges.append(f"(list {tlisp_hex(unid(lo))} {tlisp_hex(unid(hi or lo))})")
    body = (f'(setq txBotMode "{mode}")\n'
            f"(setq txBotShip {tlisp_hex(ship) if ship else 'Nil'})\n"
            f"(setq txBotSurvive {survive})\n"
            f"(setq txBotImmortal {'True' if immortal else 'Nil'})\n"
            f"(setq txBotFocus (list {' '.join(ranges)}))\n"
            f"(setq txBotExpect (list {' '.join(tlisp_hex(unid(e)) for e in expect)}))\n"
            f"(setq txBotHops {hops})\n")
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<!-- written by tx_testbot.py for each run -->\n'
                    "<TranscendenceModule>\n<Globals>\n(block Nil\n" + body + ")\n</Globals>\n</TranscendenceModule>\n",
                    encoding="utf-8")


# ---------------------------------------------------------------- logs

def hexify(line: str) -> str:
    return re.sub(r"#(-?\d+)", lambda m: f"0x{int(m.group(1)) & 0xFFFFFFFF:08X}", line)


def read_text(p: Path, offset: int = 0) -> str:
    """Debug.log is appended to across sessions: read only what this run wrote (from offset)."""
    try:
        with open(p, "rb") as f:
            f.seek(offset)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def strip_time(line: str) -> str:
    return re.sub(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\t", "", line)


def signature(line: str) -> str:
    """Same problem, different numbers/objects -> same key."""
    s = strip_time(line)
    s = re.sub(r"0x[0-9a-fA-F]+|\b[0-9a-fA-F]{8}\b|-?\d+(\.\d+)?", "#", s)
    return s[:220]


def source_of(line: str) -> str:
    m = re.search(r"\[([0-9a-fA-F]{6,8})\]", line)
    if m:
        return "0x" + m.group(1).upper().zfill(8)
    m = re.search(r"\[([^\]]+?)\]:", line)
    return m.group(1) if m else ""


def classify(log: str) -> "OrderedDict[str, Counter]":
    groups: "OrderedDict[str, Counter]" = OrderedDict((k, Counter()) for k in
        ("engine crash", "popup", "bot check failed", "mod script error", "warning", "other"))
    sources: dict[str, str] = {}
    for raw in log.splitlines():
        line = strip_time(raw)
        if NOISE.search(line) or not line.strip():
            continue
        if "TXBOT:" in line:
            body = hexify(line.split("TXBOT:", 1)[1].strip())
            if body.startswith("POPUP"):
                groups["popup"][body] += 1
            elif body.startswith("FAIL"):
                groups["bot check failed"][body] += 1
            continue
        if ENGINE_CRASH.search(line):
            key = "engine crash"
        elif SCRIPT.search(line):
            key = "mod script error"
        elif WARNING.search(line):
            key = "warning"
        elif ISSUE.search(line):
            key = "other"
        else:
            continue
        sig = signature(line)
        groups[key][sig] += 1
        sources.setdefault(sig, source_of(line))
    groups["_sources"] = sources  # type: ignore[assignment]
    return groups


def hang_dump(pid: int, hang_log: Path) -> None:
    """Ask the game (diagnostics build, TX_TESTBOT set) to write every thread's stack to TxHang.log."""
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.OpenEventW.restype = ctypes.c_void_p
    h = k32.OpenEventW(0x0002, False, f"Local\\TxHangDump_{pid}")   # EVENT_MODIFY_STATE
    if not h:
        print("[testbot] no hang-dump event in the game (exe built without diagnostics?)")
        return
    k32.SetEvent(ctypes.c_void_p(h))
    k32.CloseHandle(ctypes.c_void_p(h))
    for _ in range(30):
        time.sleep(1)
        if "=== end ===" in read_text(hang_log):
            print("[testbot] hang dump written")
            return
    print("[testbot] hang dump did not finish in 30 s")


# ---------------------------------------------------------------- one game

def run_game(game: Path, env: dict, out: Path, label: str, timeout: int, stall: int, quiet: bool) -> dict:
    exe = game / "Transcendence.exe"
    debug_log = game / "Debug.log"
    crash_log = game / "TxCrash.log"
    hang_log = game / "TxHang.log"
    log_start = debug_log.stat().st_size if debug_log.exists() else 0
    crash_start = crash_log.stat().st_size if crash_log.exists() else 0
    if hang_log.exists():
        hang_log.unlink()

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 4   # SW_SHOWNOACTIVATE: keys typed into other windows must not reach the test game
    started = time.time()
    proc = subprocess.Popen([str(exe), "/windowed", "/1024", "/nosound", "/debug"], cwd=str(game), env=env, startupinfo=si)
    status, seen, last_new = "unknown", 0, time.time()
    try:
        while True:
            time.sleep(2)
            log = read_text(debug_log, log_start)
            lines = [l for l in log.splitlines() if "TXBOT:" in l]
            if not quiet:
                for l in lines[seen:]:
                    print("   ", hexify(l.split("TXBOT:", 1)[1].strip()))
            if len(lines) > seen:
                seen, last_new = len(lines), time.time()
            if any("TXBOT: DONE" in l for l in lines):
                status = "done"
            elif any("TXBOT: POPUP" in l for l in lines):
                status = "popup"
            elif "Unable to continue due to program error" in log:
                status = "engine crash"
            elif proc.poll() is not None:
                status = f"game exited (code {proc.returncode})"
            elif time.time() - started > timeout:
                status = "timeout"
            elif time.time() - last_new > stall:
                status = "stalled"
            else:
                continue
            break
        if status in ("timeout", "stalled") and proc.poll() is None:
            hang_dump(proc.pid, hang_log)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(30)
        time.sleep(1)

    log = read_text(debug_log, log_start)
    run_dir = out / label
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "Debug.log").write_text(log, encoding="utf-8")
    crash_text = read_text(crash_log, crash_start)
    if crash_text.strip():
        (run_dir / "TxCrash.log").write_text(crash_text, encoding="utf-8")
    if hang_log.exists():
        shutil.move(str(hang_log), run_dir / "TxHang.log")
    bot = [hexify(l.split("TXBOT:", 1)[1].strip()) for l in log.splitlines() if "TXBOT:" in l]
    return {"label": label, "status": status, "seconds": round(time.time() - started), "bot": bot, "log": log,
            "native_crash_log": bool(crash_text.strip()), "dir": str(run_dir)}


# ---------------------------------------------------------------- report

def write_report(out: Path, runs: list[dict], ship_names: dict[int, str]) -> bool:
    all_log = "\n".join(r["log"] for r in runs)
    groups = classify(all_log)
    sources = groups.pop("_sources")  # type: ignore[arg-type]
    bad = any(groups[k] for k in ("engine crash", "popup", "bot check failed"))

    md = [f"# TX Test Bot report {out.name}", ""]
    ship_runs = [r for r in runs if r["label"].startswith("ship_")]
    if ship_runs:
        md += ["## Ship selection", "", "| ship | result | time | notes |", "|---|---|---|---|"]
        for r in ship_runs:
            u = int(r["label"][5:], 16)
            notes = [b for b in r["bot"] if b.startswith(("FAIL", "POPUP", "SHIP"))]
            res = "ok" if r["status"] == "done" and not any(b.startswith(("FAIL", "POPUP")) for b in r["bot"]) else r["status"]
            if r["native_crash_log"]:
                res += " + native crash"
            md.append(f"| 0x{u:08X} {ship_names.get(u, '')} | {res} | {r['seconds']} s | {'; '.join(notes)[:300]} |")
        md.append("")
    for r in runs:
        if not r["label"].startswith("ship_"):
            md += [f"## Run {r['label']}: {r['status']} ({r['seconds']} s)", "", "```", *r["bot"], "```", ""]
    titles = {"engine crash": "Engine crashes", "popup": "Popups (game could not continue)",
              "bot check failed": "Bot check failures", "mod script error": "Mod script errors (distinct)",
              "warning": "Warnings (distinct)", "other": "Other log lines (distinct)"}
    for k, c in groups.items():
        md += [f"## {titles[k]}: {len(c)} distinct, {sum(c.values())} total", ""]
        for sig, n in c.most_common(200 if k != "warning" else 40):
            src = sources.get(sig, "")
            md.append(f"- {n}x {('[' + src + '] ') if src else ''}{sig}")
        md.append("")
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    summary = {"output": str(out), "problems": bad,
               "counts": {k: {"distinct": len(c), "total": sum(c.values())} for k, c in groups.items()},
               "runs": [{k: r[k] for k in ("label", "status", "seconds", "native_crash_log", "dir")} for r in runs]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("[testbot] " + ", ".join(f"{k}: {len(c)} distinct" for k, c in groups.items()))
    print(f"[testbot] report: {out / 'report.md'}")
    return bad



# ---------------------------------------------------------------- saves and lock

def snapshot_saves(games: Path) -> dict[str, tuple[int, float]]:
    return {f.name: (f.stat().st_size, f.stat().st_mtime) for f in games.glob("*.sav")} if games.is_dir() else {}


def collect_test_saves(games: Path, before: dict[str, tuple[int, float]], dest: Path) -> list[str]:
    """Test games autosave into the player's Games folder: move what this run created or changed out of it (the
    player's own saves are left alone; one a test run changed is kept as a copy in dest and restored)."""
    moved = []
    for f in sorted(games.glob("*.sav")) if games.is_dir() else []:
        st = (f.stat().st_size, f.stat().st_mtime)
        if before.get(f.name) == st:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        if f.name in before:
            shutil.copy2(f, dest / f.name)          # an existing save changed: keep the test's copy, leave the file
            moved.append(f"{f.name} (changed by the test; copy kept)")
        else:
            shutil.move(str(f), dest / f.name)
            moved.append(f.name)
    return moved


class RunLock:
    """One test run at a time on this machine (they share Settings.xml, Debug.log and the Games folder)."""
    def __enter__(self):
        import ctypes
        self.k32 = ctypes.windll.kernel32
        self.k32.CreateMutexW.restype = ctypes.c_void_p
        self.h = self.k32.CreateMutexW(None, False, "Global\\TxTestBot")
        if self.k32.WaitForSingleObject(ctypes.c_void_p(self.h), 0) not in (0, 0x80):      # free or abandoned
            print("[testbot] another test run holds the lock; waiting")
            self.k32.WaitForSingleObject(ctypes.c_void_p(self.h), 0xFFFFFFFF)
        return self

    def __exit__(self, *exc):
        self.k32.ReleaseMutex(ctypes_void(self.h))
        self.k32.CloseHandle(ctypes_void(self.h))


def ctypes_void(h):
    import ctypes
    return ctypes.c_void_p(h)

# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=str(DEFAULT_GAME))
    ap.add_argument("--mode", choices=("ships", "full", "both"), default="ships")
    ap.add_argument("--adventure", default="0x200000", help="adventure UNID (default Stars of the Pilgrim)")
    ap.add_argument("--ship", action="append", help="test only these starting ships (hex UNID, repeatable)")
    ap.add_argument("--survive", type=int, default=20, help="seconds each ship must keep the game running")
    ap.add_argument("--focus", action="append", help="full mode: UNID range LO-HI of types to exercise (repeatable)")
    ap.add_argument("--expect", action="append", help="full mode: extension UNID that must be loaded (repeatable)")
    ap.add_argument("--hops", type=int, default=3, help="full mode: stargate jumps at the end")
    ap.add_argument("--timeout", type=int, default=0, help="seconds per game (default 240 per ship, 900 full)")
    ap.add_argument("--stall", type=int, default=120, help="seconds without a new TXBOT line before stopping")
    ap.add_argument("--mortal", action="store_true", help="let the player die (default: damage is counted, then repaired)")
    a = ap.parse_args()

    game = Path(a.game)
    settings = game / "Settings.xml"
    if not (game / "Transcendence.exe").exists() or not settings.exists():
        print(f"[testbot] no game at {game}")
        return 2
    side = game / BACKUP_SIDECAR
    if side.exists():
        print("[testbot] restoring Settings.xml from an interrupted run")
        shutil.copy2(side, settings)
        side.unlink()
    if game_running():
        print("[testbot] Transcendence.exe is running; close it first")
        return 2

    out = OUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    backup = out / "Settings.xml.before"
    shutil.copy2(settings, backup)
    shutil.copy2(settings, side)
    ext_folder = HERE / "extension"
    config = ext_folder / "TxTestBot" / "TxTestBotConfig.xml"
    focus, expect = a.focus or DEFAULT_FOCUS, a.expect or DEFAULT_EXPECT

    base_env = dict(os.environ)
    base_env.update({"TX_TESTBOT": "1", "TX_TESTBOT_ADVENTURE": a.adventure.lower().replace("0x", ""),
                     "TX_TESTBOT_EXTENSIONS": BOT_UNID})
    runs: list[dict] = []
    ship_names: dict[int, str] = {}
    games = game / "Games"
    saves_before = snapshot_saves(games)
    lock = RunLock().__enter__()
    try:
        settings.write_bytes(lowered_settings(backup.read_bytes(), ext_folder))
        print(f"[testbot] settings lowered for testing (backup: {backup})")

        if a.mode in ("ships", "both"):
            wanted = [int(s, 16) for s in a.ship] if a.ship else None
            queue, done = list(wanted or []), set()
            first = True
            while first or queue:
                ship = queue.pop(0) if queue else None
                write_config(config, "ship", focus, expect, a.hops, ship, a.survive, not a.mortal)
                env = dict(base_env)
                if ship:
                    env["TX_TESTBOT_SHIP"] = f"{ship:x}"
                r = run_game(game, env, out, f"ship_{ship:08x}" if ship else "ship_default", a.timeout or 240, a.stall, quiet=True)
                # the offered list and the ship actually used come from the log
                offered = next((l for l in r["bot"] if l.startswith("SHIPS")), "")
                used = next((l for l in r["bot"] if l.startswith("creating game with ship")), "")
                used_unid = int(used.split()[-1], 16) if used else None
                if r["label"] == "ship_default" and used_unid:
                    r["label"] = f"ship_{used_unid:08x}"
                start = next((l for l in r["bot"] if l.startswith("START")), "")
                if used_unid and ", ship " in start:
                    ship_names[used_unid] = start.split(", ship ", 1)[1].split(" ", 1)[-1]
                if used_unid:
                    done.add(used_unid)
                runs.append(r)
                fails = [b for b in r["bot"] if b.startswith(("FAIL", "POPUP"))]
                print(f"[testbot] ship {r['label'][5:]}: {r['status']}{' + native crash' if r['native_crash_log'] else ''}"
                      f"{'; ' + fails[0] if fails else ''}")
                if first and not wanted:
                    queue = [int(x, 16) for x in offered.split()[1:] if int(x, 16) not in done]
                    print(f"[testbot] starting ships offered: {len(offered.split()) - 1}; testing each")
                first = False

        if a.mode in ("full", "both"):
            write_config(config, "full", focus, expect, a.hops, None, a.survive, not a.mortal)
            r = run_game(game, dict(base_env), out, "full", a.timeout or 900, a.stall, quiet=False)
            runs.append(r)
            print(f"[testbot] full run: {r['status']}")
    finally:
        shutil.copy2(backup, settings)
        if side.exists():
            side.unlink()
        print("[testbot] Settings.xml restored")
        moved = collect_test_saves(games, saves_before, out / "test_saves")
        if moved:
            print(f"[testbot] {len(moved)} test save(s) moved out of Games to {out / 'test_saves'}")
        lock.__exit__(None, None, None)

    bad = write_report(out, runs, ship_names)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
