#!/usr/bin/env python3
"""
Grim Dawn Mod Tools — desktop GUI launcher.

Double-click Run-GdToolsGui.bat or: python gd_tools_gui.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except ImportError as exc:
    raise SystemExit(f"Tkinter required for the GUI: {exc}") from exc


def default_game_dir() -> Path:
    for key in ("GD_GAME_DIR", "GRIM_DAWN_DIR"):
        v = os.environ.get(key)
        if v and Path(v).is_dir():
            return Path(v)
    cand = Path(r"D:\games\Steam\steamapps\common\Grim Dawn")
    if cand.is_dir():
        return cand
    return Path()


class GdToolsGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Grim Dawn Mod Tools")
        self.geometry("920x680")
        self.minsize(720, 520)

        self.game_var = tk.StringVar(value=str(default_game_dir()))
        self.mod_var = tk.StringVar(value="grimarillion")
        self.out_var = tk.StringVar(value="SurvivalPlayground")
        self.skip_resources = tk.BooleanVar(value=True)
        self.dry_run_names = tk.BooleanVar(value=True)
        self._proc: Optional[subprocess.Popen] = None
        self._busy = False

        self._build()
        self._refresh_rules()

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        top = ttk.Frame(self)
        top.pack(fill=tk.X, **pad)

        ttk.Label(top, text="Game folder").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.game_var, width=70).grid(
            row=0, column=1, sticky=tk.EW, padx=4
        )
        ttk.Button(top, text="Browse…", command=self._browse_game).grid(row=0, column=2)
        top.columnconfigure(1, weight=1)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, **pad)

        nb.add(self._tab_survival(nb), text="Survival playground")
        nb.add(self._tab_compat(nb), text="FoA compat")
        nb.add(self._tab_nydiamar(nb), text="Nydiamar")
        nb.add(self._tab_merge(nb), text="Mod merge")
        nb.add(self._tab_rules(nb), text="Merge rules")
        nb.add(self._tab_apps(nb), text="Apps / folders")

        log_frame = ttk.LabelFrame(self, text="Output")
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)
        self.log = scrolledtext.ScrolledText(log_frame, height=16, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, **pad)
        self.status = ttk.Label(bar, text="Ready")
        self.status.pack(side=tk.LEFT)
        ttk.Button(bar, text="Stop", command=self._stop).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bar, text="Clear log", command=lambda: self.log.delete("1.0", tk.END)).pack(
            side=tk.RIGHT
        )

    def _tab_survival(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        opts = ttk.Frame(f)
        opts.pack(fill=tk.X, padx=8, pady=8)
        ttk.Checkbutton(
            opts, text="Skip resource ARCs (faster DB-only)", variable=self.skip_resources
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            opts, text="Placeholder combo names (no Ollama)", variable=self.dry_run_names
        ).pack(anchor=tk.W)
        ttk.Label(
            f,
            text="1) Build SurvivalPlayground (merge staging). "
            "2) Pack BOTH archives: Survival DLC (survivalmode4) for Crucible, "
            "and CampaignKitchenSink Custom Game for main campaign. "
            "survivalmode* never loads in campaign — you need both packs.",
            wraplength=700,
        ).pack(anchor=tk.W, padx=8, pady=4)
        btns = ttk.Frame(f)
        btns.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(
            btns,
            text="Build SurvivalPlayground (staging)",
            command=self._run_survival,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btns,
            text="Pack both archives (Survival DLC + Campaign)",
            command=self._run_dual_archives,
        ).pack(side=tk.LEFT, padx=4)
        btns2 = ttk.Frame(f)
        btns2.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(
            btns2,
            text="Deploy Crucible layer only (survivalmode4)",
            command=self._run_survival_dlc,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btns2, text="Open survivalmode*", command=self._open_survival_layers
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btns2,
            text="Open CampaignKitchenSink",
            command=lambda: self._open_mod("CampaignKitchenSink"),
        ).pack(side=tk.LEFT, padx=4)
        btns3 = ttk.Frame(f)
        btns3.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(
            btns3,
            text="Build .arz (arzedit CLI)",
            command=self._run_build_arz,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btns3,
            text="Re-apply class UI (up to 120)",
            command=self._run_patch_class_ui,
        ).pack(side=tk.LEFT, padx=4)
        return f

    def _tab_compat(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        row = ttk.Frame(f)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Mod folder name").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.mod_var, width=40).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Browse mods…", command=self._browse_mod).pack(side=tk.LEFT)
        ttk.Label(
            f, text="Pass A + B FoA/v1.3 compatibility (Berserker / DLC class hubs).", wraplength=700
        ).pack(anchor=tk.W, padx=8)
        ttk.Button(f, text="Run FoA full compat", command=self._run_foa).pack(
            anchor=tk.W, padx=8, pady=8
        )
        return f

    def _tab_nydiamar(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        ttk.Label(
            f,
            text="Nydiamar → FoA unified Custom Game (quest remap, portal stubs, checklist).",
            wraplength=700,
        ).pack(anchor=tk.W, padx=8, pady=8)
        ttk.Button(
            f, text="Run Nydiamar campaign pipeline", command=self._run_nydiamar
        ).pack(anchor=tk.W, padx=8, pady=4)
        ttk.Button(
            f, text="Open NydiamarIntegrated", command=lambda: self._open_mod("NydiamarIntegrated")
        ).pack(anchor=tk.W, padx=8, pady=4)
        return f

    def _tab_merge(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        row = ttk.Frame(f)
        row.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(row, text="Output name").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.out_var, width=28).pack(side=tk.LEFT, padx=6)
        ttk.Label(
            f,
            text="Simple later-wins merge. For Survival kitchen-sink with rules, use the Survival tab.",
            wraplength=700,
        ).pack(anchor=tk.W, padx=8)
        ttk.Label(f, text="Mods (one per line):").pack(anchor=tk.W, padx=8, pady=(8, 0))
        self.merge_mods = scrolledtext.ScrolledText(f, height=8, width=60, font=("Consolas", 9))
        self.merge_mods.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.merge_mods.insert("1.0", "grimarillion\nRebirth\n")
        ttk.Button(f, text="Run mod merger", command=self._run_merger).pack(
            anchor=tk.W, padx=8, pady=8
        )
        return f

    def _tab_rules(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        ttk.Label(
            f, text="Per-mod merge rules (priority / field-merge / skips). Edit JSON, then rebuild.",
            wraplength=700,
        ).pack(anchor=tk.W, padx=8, pady=8)
        cols = ("priority", "class", "enabled", "mode", "id", "notes")
        self.rules_tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (70, 55, 60, 70, 140, 360)):
            self.rules_tree.heading(c, text=c)
            self.rules_tree.column(c, width=w, stretch=(c == "notes"))
        self.rules_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        bar = ttk.Frame(f)
        bar.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(bar, text="Refresh", command=self._refresh_rules).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Open rules folder", command=self._open_rules).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            bar, text="Open Grim↔Rebirth notes", command=self._open_grim_rebirth_notes
        ).pack(side=tk.LEFT, padx=4)
        return f

    def _tab_apps(self, parent) -> ttk.Frame:
        f = ttk.Frame(parent)
        ttk.Label(f, text="External apps and useful folders.").pack(anchor=tk.W, padx=8, pady=8)
        grid = ttk.Frame(f)
        grid.pack(anchor=tk.W, padx=8, pady=4)
        actions = [
            ("GD Stash", self._launch_gdstash),
            ("Asset Manager", self._launch_am),
            ("Open mods folder", self._open_mods),
            ("Open Tools folder", lambda: self._open_path(TOOLS_DIR)),
            ("Open work logs", lambda: self._open_path(TOOLS_DIR / "work")),
        ]
        for i, (label, cmd) in enumerate(actions):
            ttk.Button(grid, text=label, command=cmd, width=28).grid(
                row=i // 2, column=i % 2, padx=4, pady=4, sticky=tk.W
            )
        return f

    # --- helpers ---

    def _browse_game(self) -> None:
        d = filedialog.askdirectory(initialdir=self.game_var.get() or str(Path.home()))
        if d:
            self.game_var.set(d)

    def _browse_mod(self) -> None:
        mods = Path(self.game_var.get()) / "mods"
        d = filedialog.askdirectory(initialdir=str(mods if mods.is_dir() else self.game_var.get()))
        if d:
            self.mod_var.set(Path(d).name)

    def _game(self) -> Path:
        return Path(self.game_var.get().strip())

    def _open_path(self, path: Path) -> None:
        path = Path(path)
        if not path.exists():
            messagebox.showwarning("Missing", f"Not found:\n{path}")
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _open_mod(self, name: str) -> None:
        self._open_path(self._game() / "mods" / name)

    def _open_mods(self) -> None:
        self._open_path(self._game() / "mods")

    def _open_rules(self) -> None:
        self._open_path(TOOLS_DIR / "profiles" / "merge_rules")

    def _open_grim_rebirth_notes(self) -> None:
        p = TOOLS_DIR / "profiles" / "merge_rules" / "GRIM_REBIRTH_CONFLICTS.md"
        if p.is_file():
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Notes", "GRIM_REBIRTH_CONFLICTS.md not found.")

    def _refresh_rules(self) -> None:
        if not hasattr(self, "rules_tree"):
            return
        for i in self.rules_tree.get_children():
            self.rules_tree.delete(i)
        try:
            from merge_rules import load_all_rules

            rules = sorted(load_all_rules(), key=lambda r: (-r.priority, r.id))
            for r in rules:
                note = (r.notes or "")[:120]
                self.rules_tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.priority,
                        r.class_priority,
                        r.enabled,
                        r.mode,
                        r.id,
                        note,
                    ),
                )
        except Exception as exc:
            self._append(f"Rules load error: {exc}\n")

    def _append(self, text: str) -> None:
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self._busy = busy
        self.status.config(text=status or ("Running…" if busy else "Ready"))

    def _stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._append("\n[stopped]\n")
            self._set_busy(False, "Stopped")

    def _run_python(self, args: List[str], title: str) -> None:
        if self._busy:
            messagebox.showinfo("Busy", "A job is already running. Stop it first.")
            return
        game = self._game()
        if not game.is_dir():
            messagebox.showerror("Game folder", f"Invalid game folder:\n{game}")
            return
        cmd = [sys.executable, "-u", *args]
        if "--game" not in args and "-g" not in args:
            # most scripts accept --game
            cmd.extend(["--game", str(game)])
        self._append(f"\n=== {title} ===\n$ {' '.join(cmd)}\n")
        self._set_busy(True, title)

        def worker() -> None:
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=str(TOOLS_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                assert self._proc.stdout is not None
                for line in self._proc.stdout:
                    self.after(0, self._append, line)
                code = self._proc.wait()
                self.after(0, self._append, f"\n[exit {code}]\n")
                self.after(0, self._set_busy, False, f"Done (exit {code})")
            except Exception as exc:
                self.after(0, self._append, f"\nERROR: {exc}\n")
                self.after(0, self._set_busy, False, "Error")

        threading.Thread(target=worker, daemon=True).start()

    def _run_survival(self) -> None:
        args = [
            str(TOOLS_DIR / "patch_survival_classes.py"),
            "--profile",
            "survivalmode.json",
        ]
        if self.skip_resources.get():
            args.append("--skip-resources")
        if self.dry_run_names.get():
            args.append("--dry-run-names")
        cache = TOOLS_DIR / "work" / "nydiamar" / "_vanilla_cache"
        if cache.is_dir():
            args.extend(["--vanilla-cache", str(cache)])
        self._run_python(args, "SurvivalPlayground")

    def _run_survival_dlc(self) -> None:
        src = self._game() / "mods" / "SurvivalPlayground"
        if not src.is_dir():
            messagebox.showwarning(
                "Missing",
                "Build SurvivalPlayground first (Survival tab), then deploy.",
            )
            return
        self._run_python(
            [
                str(TOOLS_DIR / "pack_survival_dlc_layer.py"),
                "--source",
                "SurvivalPlayground",
                "--layer",
                "survivalmode4",
            ],
            "Deploy survivalmode4",
        )

    def _run_dual_archives(self) -> None:
        src = self._game() / "mods" / "SurvivalPlayground"
        if not src.is_dir():
            messagebox.showwarning(
                "Missing",
                "Build SurvivalPlayground first (Survival tab), then pack both archives.",
            )
            return
        self._run_python(
            [
                str(TOOLS_DIR / "pack_dual_archives.py"),
                "--source",
                "SurvivalPlayground",
            ],
            "Pack Survival DLC + Campaign",
        )

    def _run_build_arz(self) -> None:
        arz = TOOLS_DIR / "bin" / "arzedit.exe"
        if not arz.is_file():
            messagebox.showwarning(
                "Missing arzedit",
                f"Build arzedit first:\n{TOOLS_DIR / 'Build-Arzedit.bat'}",
            )
            return
        self._run_python(
            [str(TOOLS_DIR / "build_mod_arz.py")],
            "Build SurvivalMode4 + CampaignKitchenSink .arz",
        )

    def _run_patch_class_ui(self) -> None:
        self._run_python(
            [
                str(TOOLS_DIR / "patch_class_ui.py"),
                "--max-classes",
                "120",
            ],
            "Re-apply class UI (120 cap)",
        )

    def _open_survival_layers(self) -> None:
        # Open game root; user can browse survivalmode1–4
        self._open_path(self._game())
        try:
            from gd_paths import survival_layer_dirs

            layers = survival_layer_dirs(self._game())
            self._append(
                "Survival DLC layers: "
                + (", ".join(p.name for p in layers) if layers else "(none)")
                + "\n"
            )
        except Exception as exc:
            self._append(f"Layer list error: {exc}\n")

    def _run_foa(self) -> None:
        mod = self.mod_var.get().strip()
        if not mod:
            messagebox.showwarning("Mod", "Enter a mod folder name.")
            return
        self._run_python(
            [str(TOOLS_DIR / "patch_mod_for_dlc.py"), "--mod", mod, "--full-compat"],
            f"FoA compat: {mod}",
        )

    def _run_nydiamar(self) -> None:
        self._run_python(
            [
                str(TOOLS_DIR / "nydiamar_campaign.py"),
                "--portal-hub",
                "asterkarn",
                "--dry-run-names",
            ],
            "Nydiamar campaign",
        )

    def _run_merger(self) -> None:
        out = self.out_var.get().strip() or "MergedMod"
        mods = [
            ln.strip()
            for ln in self.merge_mods.get("1.0", tk.END).splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not mods:
            messagebox.showwarning("Mods", "List at least one mod.")
            return
        args = [str(TOOLS_DIR / "merge_mod_databases.py"), "--out", out, "--mods", *mods]
        self._run_python(args, f"Merge → {out}")

    def _launch_gdstash(self) -> None:
        bat = self._game() / "GD Stash" / "gdstash.bat"
        if not bat.is_file():
            messagebox.showerror("GD Stash", f"Not found:\n{bat}")
            return
        subprocess.Popen(["cmd", "/c", str(bat)], cwd=str(bat.parent))
        self._append(f"Launched GD Stash: {bat}\n")

    def _launch_am(self) -> None:
        am = self._game() / "AssetManager.exe"
        if not am.is_file():
            messagebox.showerror("Asset Manager", f"Not found:\n{am}")
            return
        subprocess.Popen([str(am)], cwd=str(self._game()))
        self._append(f"Launched Asset Manager: {am}\n")


def main() -> int:
    app = GdToolsGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
