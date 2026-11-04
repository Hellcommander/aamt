#!/usr/bin/env python3
"""Pixelorama AI host: headless CLI plus a live, screenshotable GUI.

Install (this machine):
  D:\\tools\\Orama Interactive\\Pixelorama\\Pixelorama.exe

Pixelorama is a Godot editor. Agents drive it the same way as Material Maker /
xEdit: JSON in/out from this module, optional visible window so vision can see
the real UI.

  python pixelorama_client.py status
  python pixelorama_client.py version
  python pixelorama_client.py inspect sprite.pxo
  python pixelorama_client.py export sprite.pxo --out out.png
  python pixelorama_client.py spritesheet sprite.pxo --out sheet.png
  python pixelorama_client.py json sprite.pxo --out project.json
  python pixelorama_client.py open [sprite.pxo]     # visible Pixelorama GUI
  python pixelorama_client.py see [--out shot.png]  # screenshot that GUI
  python pixelorama_client.py focus
  python pixelorama_client.py quit
  python pixelorama_client.py gui                   # operator panel (drag-drop)
  python pixelorama_client.py scaffold still.png --out proj/   # AI: frames+sheet
  python pixelorama_client.py pack frames/ --out sheet.png
  python pixelorama_client.py split sheet.png --out frames/ --fw 16 --fh 24
  python pixelorama_client.py sf-status | sf-install | sf-selftest   # AAMT Sprite Forge extension
  python pixelorama_client.py sf-create still.png --cell 32x32 --frames 4 --tags idle:1-4:6 \
      --palette auto --outline auto --pxo x.pxo --sheet x.png --animation auto
  python pixelorama_client.py sf-apply|sf-import|sf-export|sf-render|sf-ai|sf-info|sf-palette|sf-batch ...

CLI shape (Pixelorama / Godot):
  Pixelorama.exe [SYSTEM] -- [USER] [FILES]
  SYSTEM: --headless --quit
  USER:   --export / --spritesheet / --output / --scale / --frames / --json ...
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

PROCESS_NAME = "Pixelorama.exe"
DEFAULT_INSTALL = Path(r"D:\tools\Orama Interactive\Pixelorama\Pixelorama.exe")
PW_RENDERFULLCONTENT = 2
SW_RESTORE = 9

try:
    from gpu_hub import acquire_gpu
except Exception:
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------


def pixelorama_exe() -> Optional[Path]:
    try:
        from tool_paths import pixelorama_exe as _exe

        found = _exe()
        if found and found.is_file():
            return found
    except Exception:
        pass
    return DEFAULT_INSTALL if DEFAULT_INSTALL.is_file() else None


def is_available() -> bool:
    return pixelorama_exe() is not None


def _running_processes() -> List[Any]:
    try:
        import psutil  # type: ignore
    except Exception:
        psutil = None
    if psutil is not None:
        hits = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name == PROCESS_NAME.lower():
                    hits.append(proc)
            except Exception:
                continue
        return hits

    # Fallback: tasklist (no psutil required)
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {PROCESS_NAME}", "/FO", "CSV", "/NH"],
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0].lower() == PROCESS_NAME.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                continue
    return pids


def gui_running() -> Dict[str, Any]:
    pids = _pixelorama_pids()
    hwnd, title = find_window()
    return {
        "running": bool(pids),
        "pids": pids,
        "hwnd": hwnd,
        "title": title,
    }


def status() -> Dict[str, Any]:
    exe = pixelorama_exe()
    gui = gui_running()
    return {
        "available": exe is not None,
        "exe": str(exe) if exe else None,
        "install": str(exe.parent) if exe else str(DEFAULT_INSTALL.parent),
        "kind": "godot-cli + visible-gui",
        "gpu": True,
        "docs": "https://www.pixelorama.org/user_manual/cli/",
        "repo": "https://github.com/Orama-Interactive/Pixelorama",
        "gui": gui,
        "commands": [
            "status",
            "version",
            "inspect",
            "export",
            "spritesheet",
            "json",
            "open",
            "see",
            "focus",
            "quit",
            "gui",
            "scaffold",
            "pack",
            "split",
        ],
        "agent_helpers": ["scaffold", "pack", "split"],
    }


# ---------------------------------------------------------------------------
# window find / screenshot (so the agent can see the real editor)
# ---------------------------------------------------------------------------


def _user32():
    if sys.platform != "win32":
        return None
    import ctypes

    return ctypes.windll.user32


def _pixelorama_pids() -> List[int]:
    pids: List[int] = []
    for p in _running_processes():
        pids.append(int(p.pid) if hasattr(p, "pid") else int(p))
    return pids


def find_window() -> Tuple[int, str]:
    """Return (hwnd, title) for the Pixelorama.exe window, or (0, '')."""
    u32 = _user32()
    if u32 is None:
        return 0, ""

    import ctypes
    from ctypes import wintypes

    pids = set(_pixelorama_pids())
    found = {"hwnd": 0, "title": ""}
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    pid_buf = wintypes.DWORD()

    def _cb(hwnd, _lparam):
        if not u32.IsWindowVisible(hwnd):
            return True
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
        owned = int(pid_buf.value) in pids if pids else False
        if not owned:
            return True
        length = u32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            u32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or ""
        if title:
            found["hwnd"] = int(hwnd)
            found["title"] = title
            return False
        if not found["hwnd"]:
            found["hwnd"] = int(hwnd)
            found["title"] = title
        return True

    u32.EnumWindows(EnumWindowsProc(_cb), 0)
    return found["hwnd"], found["title"]


def focus_gui() -> Dict[str, Any]:
    u32 = _user32()
    hwnd, title = find_window()
    if not hwnd:
        return {"ok": False, "error": "Pixelorama window not found (is the GUI open?)", "hwnd": 0}
    if u32 is not None:
        if u32.IsIconic(hwnd):
            u32.ShowWindow(hwnd, SW_RESTORE)
        else:
            u32.ShowWindow(hwnd, 5)  # SW_SHOW
        u32.SetForegroundWindow(hwnd)
    return {"ok": True, "hwnd": hwnd, "title": title}


def _save_png(path: Path, width: int, height: int, bgra: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # type: ignore

        img = Image.frombytes("RGBX", (width, height), bgra, "raw", "BGRX")
        img.convert("RGB").save(path)
        return
    except Exception:
        pass
    # Uncompressed BMP fallback (no Pillow).
    import struct

    row = ((width * 3 + 3) // 4) * 4
    pixels = bytearray(row * height)
    for y in range(height):
        src = (height - 1 - y) * width * 4
        dst = y * row
        for x in range(width):
            b, g, r = bgra[src + x * 4], bgra[src + x * 4 + 1], bgra[src + x * 4 + 2]
            pixels[dst + x * 3 : dst + x * 3 + 3] = bytes((b, g, r))
    dib = 40
    off = 14 + dib
    size = off + len(pixels)
    bmp = path.with_suffix(".bmp")
    with bmp.open("wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", size, 0, 0, off))
        f.write(struct.pack("<IiiHHIIiiII", dib, width, height, 1, 24, 0, len(pixels), 0, 0, 0, 0))
        f.write(pixels)
    if path.suffix.lower() != ".bmp":
        # Keep the requested name as a copy so callers still get --out.
        path.write_bytes(bmp.read_bytes())


def screenshot_gui(out: Optional[Path] = None, *, wait: float = 0.35) -> Dict[str, Any]:
    """Capture the Pixelorama HWND so an agent can see the live editor."""
    if sys.platform != "win32":
        return {"ok": False, "error": "window capture is Windows-only"}

    import ctypes
    from ctypes import wintypes

    focused = focus_gui()
    if not focused.get("ok"):
        return focused
    hwnd = int(focused["hwnd"])
    time.sleep(max(0.0, wait))

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    u32 = ctypes.windll.user32
    gdi = ctypes.windll.gdi32
    rect = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 1 or height <= 1:
        return {"ok": False, "error": f"Pixelorama window is {width}x{height}"}

    hwnd_dc = u32.GetWindowDC(hwnd)
    mem_dc = gdi.CreateCompatibleDC(hwnd_dc)
    hbmp = gdi.CreateCompatibleBitmap(hwnd_dc, width, height)
    gdi.SelectObject(mem_dc, hbmp)
    printed = u32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
    if not printed:
        printed = u32.PrintWindow(hwnd, mem_dc, 0)
    if not printed:
        # BitBlt from screen as last resort (needs the window on-screen).
        screen_dc = u32.GetDC(0)
        gdi.BitBlt(mem_dc, 0, 0, width, height, screen_dc, rect.left, rect.top, 0x00CC0020)
        u32.ReleaseDC(0, screen_dc)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height  # top-down
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    buf = (ctypes.c_char * (width * height * 4))()
    gdi.GetDIBits(mem_dc, hbmp, 0, height, buf, ctypes.byref(info), 0)

    gdi.DeleteObject(hbmp)
    gdi.DeleteDC(mem_dc)
    u32.ReleaseDC(hwnd, hwnd_dc)

    if out is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = _SHARED.parent / "Logs" / "pixelorama" / f"see-{stamp}.png"
    out = Path(out)
    _save_png(out, width, height, bytes(buf))
    return {
        "ok": True,
        "path": str(out.resolve()),
        "width": width,
        "height": height,
        "hwnd": hwnd,
        "title": focused.get("title"),
    }


# ---------------------------------------------------------------------------
# process control
# ---------------------------------------------------------------------------


def open_gui(project: Optional[Path] = None) -> Dict[str, Any]:
    """Launch visible Pixelorama (not headless) so the agent/user can see it."""
    exe = pixelorama_exe()
    if not exe:
        return {"ok": False, "error": f"Pixelorama.exe not found (expected {DEFAULT_INSTALL})"}
    already = gui_running()
    if already.get("running") and not project:
        focused = focus_gui()
        return {"ok": True, "started": False, **already, **focused}

    cmd = [str(exe)]
    if project:
        project = Path(project)
        if not project.is_file():
            return {"ok": False, "error": f"missing project: {project}"}
        cmd.append(str(project.resolve()))
    proc = subprocess.Popen(
        cmd,
        cwd=str(exe.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Godot needs a moment to create the HWND.
    hwnd, title = 0, ""
    for _ in range(40):
        time.sleep(0.25)
        hwnd, title = find_window()
        if hwnd:
            break
    if hwnd:
        focus_gui()
    return {
        "ok": True,
        "started": True,
        "pid": proc.pid,
        "hwnd": hwnd,
        "title": title,
        "project": str(project) if project else None,
    }


def quit_gui() -> Dict[str, Any]:
    killed: List[int] = []
    for p in _running_processes():
        pid = int(p.pid) if hasattr(p, "pid") else int(p)
        try:
            if hasattr(p, "terminate"):
                p.terminate()
            else:
                subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, timeout=10)
            killed.append(pid)
        except Exception:
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True, timeout=10)
                killed.append(pid)
            except Exception:
                pass
    return {"ok": True, "killed": killed}


# ---------------------------------------------------------------------------
# headless Pixelorama CLI
# ---------------------------------------------------------------------------


def _run_cli(
    user_args: Sequence[str],
    files: Sequence[Path],
    *,
    timeout: float = 180.0,
    gpu_label: str = "Pixelorama",
) -> Dict[str, Any]:
    exe = pixelorama_exe()
    if not exe:
        return {"ok": False, "error": f"Pixelorama.exe not found (expected {DEFAULT_INSTALL})"}

    cmd = [str(exe), "--headless", "--quit", "--", *user_args]
    for f in files:
        cmd.append(str(Path(f).resolve()))

    try:
        with acquire_gpu(gpu_label):
            proc = subprocess.run(
                cmd,
                cwd=str(exe.parent),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Pixelorama timed out after {timeout:.0f}s", "cmd": cmd}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "cmd": cmd,
    }


def version() -> Dict[str, Any]:
    result = _run_cli(["--version"], [], timeout=30.0, gpu_label="Pixelorama version")
    text = result.get("stdout") or result.get("stderr") or ""
    result["version"] = text.splitlines()[0] if text else None
    return result


def inspect(project: Path) -> Dict[str, Any]:
    project = Path(project)
    if not project.is_file():
        return {"ok": False, "error": f"missing project: {project}"}
    size = _run_cli(["--size"], [project], timeout=60.0, gpu_label=f"Pixelorama size {project.name}")
    frames = _run_cli(["--framecount"], [project], timeout=60.0, gpu_label=f"Pixelorama frames {project.name}")
    return {
        "ok": bool(size.get("ok") and frames.get("ok")),
        "project": str(project.resolve()),
        "size": (size.get("stdout") or "").strip() or None,
        "framecount": (frames.get("stdout") or "").strip() or None,
        "size_raw": size,
        "frames_raw": frames,
    }


def export_project(
    project: Path,
    out: Path,
    *,
    spritesheet: bool = False,
    scale: Optional[int] = None,
    frames: Optional[str] = None,
    direction: Optional[int] = None,
    split_layers: bool = False,
    as_json: bool = False,
    timeout: float = 300.0,
) -> Dict[str, Any]:
    """Headless export. Output format is taken from --out extension (png/gif/webp/json).

    Pixelorama v1.2.3 ignores the --output *file name* and writes `<project name>.<ext>`
    (or `<project name>_0001.<ext>`... per frame); fixed upstream in v1.2.4 (#1635).
    So we export into a fresh staging folder next to `out` and move whatever landed
    there to the requested name (works on both versions, no version sniffing):
      - one file             -> exactly `out`
      - several (per frame / split layers) -> `<out stem><suffix>.<ext>` next to `out`
    JSON (`--out x.json` or as_json): Pixelorama only writes JSON alongside an image
    export, so this runs --export --json; the .json goes to `out`, the frame images
    next to it. ok is True only if the requested file (or numbered set) exists.
    """
    import os
    import shutil

    project = Path(project)
    out = Path(out)
    if not project.is_file():
        return {"ok": False, "error": f"missing project: {project}"}
    if out.suffix.lower() == ".json":
        as_json = True
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = out.parent / f".pxexport_{time.strftime('%Y%m%d-%H%M%S')}_{os.getpid()}"
    stage.mkdir(parents=True, exist_ok=True)
    image_ext = ".png" if as_json else (out.suffix.lower() or ".png")
    # Godot/Pixelorama join paths poorly with backslashes on some builds.
    out_arg = (stage / (out.stem + image_ext)).resolve().as_posix()

    user: List[str] = []
    if spritesheet:
        user.extend(["--spritesheet", "--export"])
    else:
        user.append("--export")
    if as_json:
        user.append("--json")
    user.extend(["--output", out_arg])
    if scale is not None:
        user.extend(["--scale", str(int(scale))])
    if frames:
        user.extend(["--frames", str(frames)])
    if direction is not None:
        user.extend(["--direction", str(int(direction))])
    if split_layers:
        user.append("--split-layers")

    vram = _wait_vram(timeout=float(os.environ.get("AAMT_SPRITEFORGE_VRAM_WAIT", "300")))
    if not vram["vram_ok"]:
        try:
            stage.rmdir()
        except OSError:
            pass
        return {"ok": False, "retryable": True, **vram,
                "error": f"not enough free VRAM ({vram['vram_free_mb']} MB < {SPRITEFORGE_MIN_VRAM_MB}); retry later"}
    result = _run_cli(user, [project], timeout=timeout, gpu_label=f"Pixelorama export {project.name}")
    produced = sorted(p for p in stage.rglob("*") if p.is_file())
    proj_stem = project.stem
    want_ext = ".json" if as_json else image_ext
    # If Pixelorama could not open the .pxo it silently exports its empty default
    # project ("untitled..."). Files not named after out/project are rejected.
    foreign = [p for p in produced if not (p.stem.startswith(out.stem) or p.stem.startswith(proj_stem))]
    if foreign:
        rejects = _SHARED.parent / "Logs" / "pixelorama" / "export_rejects" / stage.name
        rejects.mkdir(parents=True, exist_ok=True)
        for p in produced:
            shutil.move(str(p), str(rejects / p.name))  # may cross drives
        for d in sorted((x for x in stage.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
        try:
            stage.rmdir()
        except OSError:
            pass
        result.update({
            "ok": False, "outputs": [], "written": [], "exact": False,
            "project": str(project.resolve()), "output": str(out),
            "error": f"Pixelorama did not export {project.name} (could not open it?); "
                     f"got {[p.name for p in foreign]} - moved to {rejects}",
        })
        return result
    mains = [p for p in produced if p.suffix.lower() == want_ext]
    moved: List[str] = []
    for p in produced:
        rel_parent = p.parent.relative_to(stage)
        stem = p.stem
        for prefix in (out.stem, proj_stem):  # v1.2.4+ uses out.stem, v1.2.3 the project name
            if stem.startswith(prefix):
                stem = out.stem + stem[len(prefix):]
                break
        if p.suffix.lower() == want_ext and len(mains) == 1:
            dest = out  # the single requested file
        else:
            dest = out.parent / rel_parent / (stem + p.suffix)
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(p, dest)
        moved.append(str(dest))
    # staging folder is empty now (only folders we created) - tidy it
    for d in sorted((x for x in stage.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    try:
        stage.rmdir()
    except OSError:
        pass
    outputs = [m for m in moved if Path(m).suffix.lower() == want_ext]
    result["project"] = str(project.resolve())
    result["output"] = str(out) if out.is_file() else (outputs[0] if outputs else str(out))
    result["outputs"] = outputs
    result["written"] = moved
    result["exact"] = out.is_file()
    result["ok"] = bool(outputs) and all(Path(m).is_file() for m in outputs)
    if result["ok"]:
        result.pop("error", None)
    elif not result.get("error"):
        result["error"] = (
            f"export produced no {want_ext} file for {out} "
            f"(Pixelorama rc={result.get('returncode')}, staged={[p.name for p in produced]})"
        )
    return result


# ---------------------------------------------------------------------------
# operator GUI (drag-drop + buttons; AI can also --see the Pixelorama window)
# ---------------------------------------------------------------------------


def run_operator_gui(initial: Optional[Path] = None) -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        print(f"[ERROR] tkinter required for --gui: {exc}", file=sys.stderr)
        return 2

    root = tk.Tk()
    root.title("AAMT Pixelorama host")
    root.geometry("720x520")
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    project_var = tk.StringVar(value=str(initial) if initial else "")
    out_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="idle")

    def log(msg: str) -> None:
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        root.update_idletasks()

    def dump(result: Dict[str, Any]) -> None:
        log(json.dumps(result, indent=2))
        status_var.set("ok" if result.get("ok") else "error")

    def current_project() -> Optional[Path]:
        raw = project_var.get().strip().strip('"')
        return Path(raw) if raw else None

    def browse() -> None:
        path = filedialog.askopenfilename(
            title="Pixelorama project",
            filetypes=[("Pixelorama", "*.pxo"), ("All", "*.*")],
        )
        if path:
            project_var.set(path)

    def do_status() -> None:
        dump(status())

    def do_open() -> None:
        dump(open_gui(current_project()))

    def do_see() -> None:
        dump(screenshot_gui())

    def do_inspect() -> None:
        p = current_project()
        if not p:
            messagebox.showerror("Pixelorama", "Pick a .pxo first")
            return
        dump(inspect(p))

    def do_export(sheet: bool = False) -> None:
        p = current_project()
        if not p:
            messagebox.showerror("Pixelorama", "Pick a .pxo first")
            return
        dest = out_var.get().strip().strip('"')
        if not dest:
            dest = filedialog.asksaveasfilename(
                title="Export as",
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("GIF", "*.gif"), ("WebP", "*.webp"), ("All", "*.*")],
            )
            if not dest:
                return
            out_var.set(dest)
        dump(export_project(p, Path(dest), spritesheet=sheet))

    def do_quit() -> None:
        dump(quit_gui())

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")
    ttk.Label(top, text="Install: D:\\tools\\Orama Interactive\\Pixelorama").pack(anchor="w")
    ttk.Label(top, textvariable=status_var).pack(anchor="w")

    row = ttk.Frame(root, padding=8)
    row.pack(fill="x")
    ttk.Entry(row, textvariable=project_var).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="Browse .pxo", command=browse).pack(side="left", padx=4)

    btns = ttk.Frame(root, padding=8)
    btns.pack(fill="x")
    for label, cmd in (
        ("Status", do_status),
        ("Open GUI", do_open),
        ("See GUI", do_see),
        ("Inspect", do_inspect),
        ("Export", lambda: do_export(False)),
        ("Spritesheet", lambda: do_export(True)),
        ("Quit GUI", do_quit),
    ):
        ttk.Button(btns, text=label, command=cmd).pack(side="left", padx=3)

    log_box = tk.Text(root, wrap="word", height=18)
    log_box.pack(fill="both", expand=True, padx=8, pady=8)

    def on_drop(event: Any) -> None:
        data = (event.data or "").strip().strip("{}")
        if data:
            project_var.set(data)

    try:
        root.tk.call("tk", "windowingsystem")
        root.drop_target_register("DND_Files")  # type: ignore[attr-defined]
        root.dnd_bind("<<Drop>>", on_drop)  # type: ignore[attr-defined]
    except Exception:
        pass

    dump(status())
    root.mainloop()
    return 0


# ---------------------------------------------------------------------------
# Agent sprite edit helpers (no Godot required)
# Frames / sheets so AIs can iterate without a hand-saved .pxo first.
# ---------------------------------------------------------------------------


def _pil():
    try:
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Pillow required for sheet/frame helpers") from exc
    return Image


def make_idle_frames(
    still: Path,
    *,
    count: int = 4,
    style: str = "bob",
) -> List[Any]:
    """Return N RGBA frames derived from a still (pixel idle motion).

    Styles are tuned for CoQ 16x24 creature tiles — motion must read at cell size
    without looking like a teleport.
    """
    Image = _pil()
    still = Path(still)
    base = Image.open(still).convert("RGBA")
    w, h = base.size

    def _shift(src: Any, dx: int, dy: int) -> Any:
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.paste(src, (dx, dy))
        return out

    def _brighten(src: Any, add: int = 18) -> Any:
        out = src.copy()
        p = out.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = p[x, y]
                if a < 16:
                    continue
                p[x, y] = (
                    min(255, r + add),
                    min(255, g + add),
                    min(255, b + add),
                    a,
                )
        return out

    def _nudge_band(src: Any, y0: int, y1: int, dx: int, dy: int = 0) -> Any:
        """Shift only a horizontal band of opaque pixels (antenna / stinger / wings)."""
        out = src.copy()
        band = src.crop((0, y0, w, y1))
        # Clear band then paste shifted
        clear = Image.new("RGBA", (w, y1 - y0), (0, 0, 0, 0))
        out.paste(clear, (0, y0))
        out.paste(band, (dx, y0 + dy), band)
        return out

    def _nudge_top(src: Any, rows: int = 5, dx: int = 1) -> Any:
        return _nudge_band(src, 0, min(h, rows), dx, 0)

    def _nudge_bottom(src: Any, rows: int = 6, dy: int = 1) -> Any:
        y0 = max(0, h - rows)
        return _nudge_band(src, y0, h, 0, dy)

    frames: List[Any] = []
    if style == "flutter":
        # Wings: vertical bob + slight lateral + tip flicker
        seq = [
            base.copy(),
            _shift(base, 0, -1),
            _nudge_top(_shift(base, 1, 0), rows=max(4, h // 3), dx=1),
            _shift(base, 0, 1),
        ]
    elif style == "pulse":
        # Glow / crystal / flux: luminance throb (no position jump)
        seq = [
            base.copy(),
            _brighten(base, 22),
            base.copy(),
            _brighten(base, 10),
        ]
    else:  # bob — ground crawlers: body bob + antenna/maw twitch
        seq = [
            base.copy(),
            _shift(base, 0, -1),
            _nudge_top(base, rows=max(4, h // 4), dx=1),
            _shift(base, 0, 1),
        ]

    for i in range(max(1, count)):
        frames.append(seq[i % len(seq)].copy())
    return frames


def write_frames(frames: Sequence[Any], out_dir: Path, stem: str) -> List[Path]:
    """Write frame_001.png … under out_dir. Returns paths."""
    Image = _pil()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for i, fr in enumerate(frames, start=1):
        if not hasattr(fr, "save"):
            fr = Image.open(fr).convert("RGBA")
        path = out_dir / f"{stem}_{i:03d}.png"
        fr.save(path)
        paths.append(path)
    return paths


def make_spritesheet(
    frames: Sequence[Any],
    out: Path,
    *,
    columns: Optional[int] = None,
) -> Dict[str, Any]:
    """Pack frames into a horizontal (or grid) PNG spritesheet."""
    Image = _pil()
    out = Path(out)
    imgs = []
    for fr in frames:
        if hasattr(fr, "save"):
            imgs.append(fr.convert("RGBA") if fr.mode != "RGBA" else fr)
        else:
            imgs.append(Image.open(fr).convert("RGBA"))
    if not imgs:
        return {"ok": False, "error": "no frames"}
    fw, fh = imgs[0].size
    n = len(imgs)
    cols = int(columns) if columns else n
    cols = max(1, min(cols, n))
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))
    for i, im in enumerate(imgs):
        if im.size != (fw, fh):
            im = im.resize((fw, fh), Image.Resampling.NEAREST)
        sheet.paste(im, ((i % cols) * fw, (i // cols) * fh))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {
        "ok": True,
        "path": str(out.resolve()),
        "frame_size": [fw, fh],
        "columns": cols,
        "rows": rows,
        "frames": n,
    }


def split_spritesheet(
    sheet: Path,
    out_dir: Path,
    *,
    frame_width: int,
    frame_height: int,
    stem: str = "frame",
) -> Dict[str, Any]:
    """Slice a sheet into individual frame PNGs."""
    Image = _pil()
    sheet = Path(sheet)
    im = Image.open(sheet).convert("RGBA")
    w, h = im.size
    if frame_width <= 0 or frame_height <= 0:
        return {"ok": False, "error": "frame_width/height must be > 0"}
    cols = w // frame_width
    rows = h // frame_height
    if cols < 1 or rows < 1:
        return {"ok": False, "error": f"sheet {w}x{h} smaller than frame {frame_width}x{frame_height}"}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []
    idx = 1
    for y in range(rows):
        for x in range(cols):
            cell = im.crop(
                (
                    x * frame_width,
                    y * frame_height,
                    (x + 1) * frame_width,
                    (y + 1) * frame_height,
                )
            )
            # Skip fully transparent trailing cells
            if cell.getbbox() is None:
                continue
            path = out_dir / f"{stem}_{idx:03d}.png"
            cell.save(path)
            paths.append(str(path.resolve()))
            idx += 1
    return {
        "ok": bool(paths),
        "frames": paths,
        "columns": cols,
        "rows": rows,
        "frame_size": [frame_width, frame_height],
    }


def scaffold_from_still(
    still: Path,
    out_dir: Path,
    *,
    frame_count: int = 4,
    style: str = "bob",
    stem: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an AI-editable animation folder from a still PNG.

    Layout:
      <out_dir>/
        meta.json          — sizes, style, CoQ TileAnimationFrames hint
        frames/*.png       — discrete frames
        sheet.png          — horizontal spritesheet (import into Pixelorama)
        still.png          — copy of source

    Open sheet.png in Pixelorama GUI to refine; re-split with `split`.
    """
    still = Path(still)
    if not still.is_file():
        return {"ok": False, "error": f"missing still: {still}"}
    out_dir = Path(out_dir)
    stem = stem or still.stem
    frames = make_idle_frames(still, count=frame_count, style=style)
    frame_dir = out_dir / "frames"
    paths = write_frames(frames, frame_dir, stem)
    # Frame 001 must match the still bytes (Pillow re-encode would diverge).
    if paths:
        paths[0].write_bytes(still.read_bytes())
    sheet_path = out_dir / "sheet.png"
    # Rebuild sheet from disk so frame1 matches still
    sheet_info = make_spritesheet([str(p) for p in paths], sheet_path)
    still_copy = out_dir / "still.png"
    still_copy.write_bytes(still.read_bytes())

    fw, fh = frames[0].size
    # CoQ AnimatedMaterialGeneric hint (tick → tile path; fill in install root later)
    tick_step = max(1, 80 // max(1, len(paths)))
    tile_hint = ",".join(
        f"{i * tick_step}=Creatures/{stem}_{i + 1}.png" for i in range(len(paths))
    )
    meta = {
        "stem": stem,
        "source": str(still.resolve()),
        "frame_size": [fw, fh],
        "frame_count": len(paths),
        "style": style,
        "frames": [str(p.resolve()) for p in paths],
        "sheet": str(sheet_path.resolve()),
        "coq": {
            "AnimationLength": tick_step * len(paths),
            "TileAnimationFrames": tile_hint,
            "note": "Install numbered frames next to still; merge AnimatedMaterialGeneric.",
        },
    }
    meta_path = out_dir / "meta.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "project_dir": str(out_dir.resolve()),
        "meta": str(meta_path.resolve()),
        "sheet": sheet_info,
        "frames": [str(p.resolve()) for p in paths],
        "coq_hint": meta["coq"],
    }


# ---------------------------------------------------------------------------
# AAMT Sprite Forge (Pixelorama extension, headless) - added 2026-10-24
# Source: Tools/Pixelorama/extensions/AAMTSpriteForge (build.py packages it).
# Always headless: Pixelorama.exe --headless --quit -- spriteforge key=value ...
# ---------------------------------------------------------------------------

SPRITEFORGE_NAME = "AAMTSpriteForge"
SPRITEFORGE_SRC = _SHARED.parent / "Pixelorama" / "extensions" / SPRITEFORGE_NAME
SPRITEFORGE_USER_DIR = Path(
    __import__("os").environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
) / "pixelorama"
SPRITEFORGE_COMMANDS = (
    "create", "apply", "import", "export", "render", "ai", "info", "palette", "selftest",
)
SPRITEFORGE_MIN_VRAM_MB = 2048


def _free_vram_mb() -> Optional[int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            text=True, timeout=15,
        )
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def _wait_vram(min_mb: int = SPRITEFORGE_MIN_VRAM_MB, timeout: float = 900.0) -> Dict[str, Any]:
    """Wait (bounded) until >= min_mb VRAM is free (Godot needs ~2 GB). Call WITHOUT the GPU lock."""
    t0 = time.time()
    free = _free_vram_mb()
    while free is not None and free < min_mb and time.time() - t0 < timeout:
        print(f"[spriteforge] waiting for VRAM: {free} MB free < {min_mb} MB", file=sys.stderr, flush=True)
        time.sleep(max(0.5, min(10.0, timeout - (time.time() - t0))))
        free = _free_vram_mb()
    return {"vram_free_mb": free, "vram_ok": free is None or free >= min_mb,
            "vram_waited_s": round(time.time() - t0, 1)}


def _sf_value(v: Any) -> str:
    if isinstance(v, Path):
        return v.resolve().as_posix()
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return ";".join(_sf_value(x) for x in v)
    s = str(v)
    # Windows paths -> forward slashes (Godot), but leave colours/tags alone
    return s.replace("\\", "/") if ("\\" in s) else s


def spriteforge_status() -> Dict[str, Any]:
    """Is the extension built, installed and enabled? (no Pixelorama launch)"""
    meta: Dict[str, Any] = {}
    try:
        meta = json.loads((SPRITEFORGE_SRC / "extension" / "extension.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    installed = SPRITEFORGE_USER_DIR / "extensions" / f"{SPRITEFORGE_NAME}.zip"
    cfg = SPRITEFORGE_USER_DIR / "config.ini"
    enabled = False
    try:
        text = cfg.read_text(encoding="utf-8")
        sect = text.split("[extensions]", 1)[1].split("\n[", 1)[0] if "[extensions]" in text else ""
        enabled = f"{SPRITEFORGE_NAME}=true" in sect.replace(" ", "")
    except Exception:
        pass
    return {
        "ok": installed.is_file() and enabled,
        "source": str(SPRITEFORGE_SRC),
        "version": meta.get("version"),
        "supported_api_versions": meta.get("supported_api_versions"),
        "installed": str(installed) if installed.is_file() else None,
        "enabled": enabled,
        "commands": list(SPRITEFORGE_COMMANDS) + ["batch"],
        "hint": None if installed.is_file() and enabled else "python pixelorama_client.py sf-install",
    }


def spriteforge_install(enable: bool = True) -> Dict[str, Any]:
    """Package the extension source and copy it to %APPDATA%/pixelorama/extensions."""
    cmd = [sys.executable, str(SPRITEFORGE_SRC / "build.py"), "--install"]
    if enable:
        cmd.append("--enable")
    if _pixelorama_pids() and enable:
        return {"ok": False, "error": "close Pixelorama first (it rewrites config.ini on exit)"}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        info = json.loads(proc.stdout)
    except Exception:
        info = {"ok": False, "stdout": proc.stdout, "stderr": proc.stderr}
    info["ok"] = bool(info.get("ok")) and proc.returncode == 0
    return info


def spriteforge(
    cmd: Optional[str] = None,
    *,
    job_file: Optional[Path] = None,
    timeout: float = 600.0,
    lock_timeout: Optional[float] = None,
    vram_wait: Optional[float] = None,
    **params: Any,
) -> Dict[str, Any]:
    """Run one Sprite Forge command (or a batch job file) headless.

    spriteforge("create", source=Path("still.png"), cell="32x32", frames=4,
                tags="idle:1-4:6", palette="auto", outline="auto",
                pxo=Path("x.pxo"), sheet=Path("x.png"), animation="auto")
    spriteforge(job_file=Path("jobs.json"))

    Returns the extension's JSON ({ok, exit_code, jobs:[...]}) plus returncode/cmd.
    Waits (without the lock) for >= 2 GB free VRAM, then holds the AAMT GPU lock while
    Godot runs. Both waits are bounded: vram_wait / lock_timeout seconds (default 300,
    env AAMT_SPRITEFORGE_VRAM_WAIT / AAMT_SPRITEFORGE_LOCK_TIMEOUT); on expiry the result
    is {"ok": false, "retryable": true, "error": ...}. Result JSONs are kept under
    Tools/Logs/pixelorama/spriteforge/.
    """
    exe = pixelorama_exe()
    if not exe:
        return {"ok": False, "error": f"Pixelorama.exe not found (expected {DEFAULT_INSTALL})"}
    st = spriteforge_status()
    if not st.get("installed") or not st.get("enabled"):
        return {"ok": False, "error": "AAMT Sprite Forge not installed/enabled", "status": st}
    if cmd is None and job_file is None:
        return {"ok": False, "error": "need cmd or job_file"}
    if cmd == "ai":
        params.setdefault("gpu_lock_held", True)  # we hold the lock; helper must not re-take it
    log_dir = _SHARED.parent / "Logs" / "pixelorama" / "spriteforge"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{__import__('os').getpid()}"
    result_file = log_dir / f"result_{stamp}_{cmd or 'batch'}.json"
    user = ["spriteforge"]
    if job_file is not None:
        user.append(f"job={Path(job_file).resolve().as_posix()}")
    if cmd:
        user.append(f"cmd={cmd}")
    for k, v in params.items():
        if v is None:
            continue
        user.append(f"{k}={_sf_value(v)}")
    user.append(f"result={result_file.resolve().as_posix()}")
    bad = [a for a in user if a.startswith("-")]
    if bad:
        return {"ok": False, "error": f"user args may not start with '-': {bad}"}
    argv = [str(exe), "--headless", "--quit", "--", *user]
    label = f"Pixelorama SpriteForge {cmd or Path(job_file).name}"
    env = __import__("os").environ
    if vram_wait is None:
        vram_wait = float(env.get("AAMT_SPRITEFORGE_VRAM_WAIT", "300"))
    if lock_timeout is None:
        lock_timeout = float(env.get("AAMT_SPRITEFORGE_LOCK_TIMEOUT", "300"))
    deadline = time.time() + vram_wait
    proc = None
    vram: Dict[str, Any] = {}
    try:
        while proc is None:
            # Wait for VRAM WITHOUT the lock (an SD batch may need the lock to finish),
            # then take the lock (bounded) and re-check before launching Godot.
            vram = _wait_vram(timeout=max(0.0, deadline - time.time()))
            if not vram["vram_ok"]:
                return {"ok": False, "retryable": True, **vram,
                        "error": f"not enough free VRAM ({vram['vram_free_mb']} MB < {SPRITEFORGE_MIN_VRAM_MB}) "
                                 f"after {vram_wait:.0f}s; GPU busy (SD batch?) - retry later"}
            with acquire_gpu(label, timeout=lock_timeout):
                free = _free_vram_mb()
                if free is not None and free < SPRITEFORGE_MIN_VRAM_MB:
                    if time.time() < deadline:
                        continue  # lost the race; release the lock and wait again
                    return {"ok": False, "retryable": True, "vram_free_mb": free,
                            "error": f"not enough free VRAM ({free} MB < {SPRITEFORGE_MIN_VRAM_MB}); retry later"}
                vram["vram_free_mb"] = free
                proc = subprocess.run(argv, cwd=str(exe.parent), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Pixelorama timed out after {timeout:.0f}s", "cmd": argv}
    except TimeoutError as exc:
        holder = None
        try:
            from gpu_hub import current_holder  # type: ignore

            holder = current_holder()
        except Exception:
            pass
        return {"ok": False, "retryable": True, "holder": holder,
                "error": f"GPU lock not acquired within {lock_timeout:.0f}s ({exc}); retry later"}
    out: Dict[str, Any] = {}
    try:
        out = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        for line in (proc.stdout or "").splitlines():
            if line.startswith("AAMT_SF_RESULT "):
                try:
                    out = json.loads(line[len("AAMT_SF_RESULT "):])
                except Exception:
                    pass
    out["result_file"] = str(result_file) if result_file.is_file() else None
    if len(out) == 1:
        errs = [l for l in (proc.stderr or "").splitlines() if "SCRIPT ERROR" in l or "EXTENSION" in l]
        out = {"ok": False, "error": "no Sprite Forge result (extension not loaded?)", "stderr_tail": errs[-20:]}
    out["returncode"] = proc.returncode
    out["cmd"] = argv
    out.update(vram)
    out["ok"] = bool(out.get("ok")) and proc.returncode == 0
    return out


def _add_spriteforge_parsers(sub: Any) -> None:
    def common(p: Any) -> None:
        p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                       help="any extra Sprite Forge key (repeatable), e.g. --set bg=none")
        p.add_argument("--timeout", type=float, default=600.0)
        p.add_argument("--lock-timeout", type=float, default=None,
                       help="max seconds to wait for the GPU lock (default 300)")
        p.add_argument("--vram-wait", type=float, default=None,
                       help="max seconds to wait for >= 2 GB free VRAM (default 300)")

    sub.add_parser("sf-status", help="Sprite Forge: installed/enabled? (no launch)")
    p = sub.add_parser("sf-install", help="Sprite Forge: build + install + enable the extension")
    p.add_argument("--no-enable", action="store_true")
    p = sub.add_parser("sf-selftest", help="Sprite Forge: load check, headless")
    common(p)

    p = sub.add_parser("sf-create", help="still / frames folder / sheet -> .pxo (+ Starbound sheet)")
    p.add_argument("source", type=Path)
    p.add_argument("--type", choices=("still", "frames", "sheet"), default=None)
    p.add_argument("--pxo", type=Path, default=None)
    p.add_argument("--sheet", type=Path, default=None)
    p.add_argument("--cell", default=None, help="target cell WxH, e.g. 32x32")
    p.add_argument("--frames", type=int, default=None, help="still: number of frames to generate")
    p.add_argument("--style", default=None, help="still motion: none|bob|float|sway|pulse|flutter")
    p.add_argument("--tags", default=None, help="name:from-to:fps[:mode[:transition]],...")
    p.add_argument("--fps", type=float, default=None)
    p.add_argument("--palette", default=None, help="file | Pixelorama palette name | auto | sample:a.png;b.png")
    p.add_argument("--colors", type=int, default=None)
    p.add_argument("--outline", default=None, help="auto | #rrggbb | none")
    p.add_argument("--animation", default=None, help="auto | path.animation")
    p.add_argument("--layout", default=None, choices=("rows", "strip", "grid"))
    p.add_argument("--scale", type=int, default=None)
    p.add_argument("--grid", default=None, help="sheet source: COLSxROWS")
    p.add_argument("--frame", default=None, help="sheet source: frame WxH")
    common(p)

    p = sub.add_parser("sf-apply", help="palette / outline / tags on an existing .pxo")
    p.add_argument("source", type=Path)
    p.add_argument("--pxo", type=Path, default=None)
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--palette", default=None)
    p.add_argument("--colors", type=int, default=None)
    p.add_argument("--outline", default=None)
    p.add_argument("--tags", default=None)
    p.add_argument("--fps", type=float, default=None)
    p.add_argument("--sheet", type=Path, default=None)
    p.add_argument("--animation", default=None)
    common(p)

    p = sub.add_parser("sf-import", help="candidates (SD / Unity frames) -> layers or frames of a .pxo")
    p.add_argument("source", type=Path)
    p.add_argument("--images", nargs="+", required=True, type=Path, help="files or folders")
    p.add_argument("--as", dest="as_", choices=("layers", "frames"), default="layers")
    p.add_argument("--at-frame", type=int, default=None)
    p.add_argument("--palette", default=None)
    p.add_argument("--pxo", type=Path, default=None)
    p.add_argument("--in-place", action="store_true")
    common(p)

    p = sub.add_parser("sf-export", help=".pxo -> Starbound sheet + .frames (+ .animation)")
    p.add_argument("source", type=Path)
    p.add_argument("--sheet", type=Path, required=True)
    p.add_argument("--animation", default=None)
    p.add_argument("--layout", default=None, choices=("rows", "strip", "grid"))
    p.add_argument("--columns", type=int, default=None)
    p.add_argument("--scale", type=int, default=None)
    common(p)

    p = sub.add_parser("sf-render", help=".pxo frame composites -> PNG")
    p.add_argument("source", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--frame", default=None, help="1, 2-4 or all")
    p.add_argument("--scale", type=int, default=None)
    common(p)

    p = sub.add_parser("sf-ai", help="OPT-IN, uses GPU: frame -> SD img2img -> new layer")
    p.add_argument("source", type=Path)
    p.add_argument("--prompt", required=True)
    p.add_argument("--frame", default="1")
    p.add_argument("--strength", type=float, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--palette", default=None, help=".gpl to snap the result to")
    p.add_argument("--pxo", type=Path, default=None)
    p.add_argument("--in-place", action="store_true")
    common(p)

    p = sub.add_parser("sf-info", help=".pxo layers/frames/tags/fps as JSON")
    p.add_argument("source", type=Path)
    common(p)

    p = sub.add_parser("sf-palette", help="sample a palette from reference sprites -> .gpl/.json")
    p.add_argument("sample", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--colors", type=int, default=16)
    common(p)

    p = sub.add_parser("sf-batch", help="run a Sprite Forge JSON job file")
    p.add_argument("job", type=Path)
    common(p)


def _dispatch_spriteforge(args: Any) -> int:
    cmd = args.cmd
    if cmd == "sf-status":
        return _print(spriteforge_status())
    if cmd == "sf-install":
        return _print(spriteforge_install(enable=not args.no_enable))
    extra: Dict[str, Any] = {}
    for kv in getattr(args, "set", []) or []:
        if "=" in kv:
            k, v = kv.split("=", 1)
            extra[k.strip()] = v
    skip = {"cmd", "set", "timeout", "status", "gui", "source", "in_place", "as_", "job", "sample",
            "images", "at_frame", "no_enable", "lock_timeout", "vram_wait"}
    params: Dict[str, Any] = {k: v for k, v in vars(args).items() if k not in skip and v is not None}
    if hasattr(args, "source"):
        params["source"] = args.source
    if getattr(args, "in_place", False):
        params["in_place"] = True
    if getattr(args, "as_", None):
        params["as"] = args.as_
    if getattr(args, "images", None):
        params["images"] = list(args.images)
    if getattr(args, "at_frame", None):
        params["at_frame"] = args.at_frame
    if getattr(args, "sample", None):
        params["sample"] = list(args.sample)
    params.update(extra)
    waits = {"timeout": getattr(args, "timeout", 600.0),
             "lock_timeout": getattr(args, "lock_timeout", None),
             "vram_wait": getattr(args, "vram_wait", None)}
    if cmd == "sf-batch":
        return _print(spriteforge(job_file=args.job, **waits, **params))
    return _print(spriteforge(cmd[3:], **waits, **params))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print(result: Dict[str, Any]) -> int:
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AAMT Pixelorama host (headless CLI + visible GUI screenshots)",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status")
    sub.add_parser("version")
    sub.add_parser("focus")
    sub.add_parser("quit")
    sub.add_parser("gui")

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("project", type=Path)

    p_export = sub.add_parser("export")
    p_export.add_argument("project", type=Path)
    p_export.add_argument("--out", type=Path, required=True)
    p_export.add_argument("--scale", type=int, default=None)
    p_export.add_argument("--frames", default=None, help="range like 1-8")
    p_export.add_argument("--direction", type=int, choices=(0, 1, 2), default=None)
    p_export.add_argument("--split-layers", action="store_true")

    p_sheet = sub.add_parser("spritesheet")
    p_sheet.add_argument("project", type=Path)
    p_sheet.add_argument("--out", type=Path, required=True)
    p_sheet.add_argument("--scale", type=int, default=None)
    p_sheet.add_argument("--frames", default=None)
    p_sheet.add_argument("--split-layers", action="store_true")

    p_json = sub.add_parser("json")
    p_json.add_argument("project", type=Path)
    p_json.add_argument("--out", type=Path, required=True)

    p_open = sub.add_parser("open")
    p_open.add_argument("project", type=Path, nargs="?")

    p_see = sub.add_parser("see")
    p_see.add_argument("--out", type=Path, default=None)

    p_scaffold = sub.add_parser(
        "scaffold",
        help="AI helper: still PNG → frames/ + sheet.png + meta.json (no .pxo required)",
    )
    p_scaffold.add_argument("still", type=Path)
    p_scaffold.add_argument("--out", type=Path, required=True, help="project folder")
    p_scaffold.add_argument("--frames", type=int, default=4)
    p_scaffold.add_argument(
        "--style",
        choices=("bob", "flutter", "pulse"),
        default="bob",
    )
    p_scaffold.add_argument("--stem", default=None)

    p_pack = sub.add_parser("pack", help="AI helper: pack frame PNGs into a spritesheet")
    p_pack.add_argument("frames_dir", type=Path)
    p_pack.add_argument("--out", type=Path, required=True)
    p_pack.add_argument("--glob", default="*.png")
    p_pack.add_argument("--columns", type=int, default=None)

    p_split = sub.add_parser("split", help="AI helper: slice spritesheet → frame PNGs")
    p_split.add_argument("sheet", type=Path)
    p_split.add_argument("--out", type=Path, required=True)
    p_split.add_argument("--fw", type=int, required=True, help="frame width")
    p_split.add_argument("--fh", type=int, required=True, help="frame height")
    p_split.add_argument("--stem", default="frame")

    _add_spriteforge_parsers(sub)  # AAMT Sprite Forge sf-* commands

    parser.add_argument("--status", action="store_true", help="alias of 'status'")
    parser.add_argument("--gui", action="store_true", help="alias of 'gui'")
    args = parser.parse_args(argv)

    cmd = args.cmd
    if args.status or cmd is None:
        cmd = "status"
    if args.gui:
        cmd = "gui"

    if cmd == "status":
        info = status()
        info["agent_helpers"] = ["scaffold", "pack", "split"]
        print(json.dumps(info, indent=2))
        return 0 if info.get("available") else 1
    if cmd == "version":
        return _print(version())
    if cmd == "inspect":
        return _print(inspect(args.project))
    if cmd == "export":
        return _print(
            export_project(
                args.project,
                args.out,
                scale=args.scale,
                frames=args.frames,
                direction=args.direction,
                split_layers=args.split_layers,
            )
        )
    if cmd == "spritesheet":
        return _print(
            export_project(
                args.project,
                args.out,
                spritesheet=True,
                scale=args.scale,
                frames=args.frames,
                split_layers=args.split_layers,
            )
        )
    if cmd == "json":
        return _print(export_project(args.project, args.out, as_json=True))
    if cmd == "open":
        return _print(open_gui(args.project))
    if cmd == "see":
        return _print(screenshot_gui(args.out))
    if cmd == "focus":
        return _print(focus_gui())
    if cmd == "quit":
        return _print(quit_gui())
    if cmd == "gui":
        return run_operator_gui()
    if cmd == "scaffold":
        return _print(
            scaffold_from_still(
                args.still,
                args.out,
                frame_count=args.frames,
                style=args.style,
                stem=args.stem,
            )
        )
    if cmd == "pack":
        frames_dir = Path(args.frames_dir)
        paths = sorted(frames_dir.glob(args.glob))
        return _print(make_spritesheet(paths, args.out, columns=args.columns))
    if cmd == "split":
        return _print(
            split_spritesheet(
                args.sheet,
                args.out,
                frame_width=args.fw,
                frame_height=args.fh,
                stem=args.stem,
            )
        )
    if cmd and cmd.startswith("sf-"):
        return _dispatch_spriteforge(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
