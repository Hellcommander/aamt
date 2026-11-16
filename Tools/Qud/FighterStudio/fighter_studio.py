#!/usr/bin/env python3
"""Fighter Studio: one window for the whole Choose Your Fighter art pipeline.

Pick a character export, get the picture prompt written from its build, bring the picture back,
turn it into a layered portrait, fit the gear, bake and recolour the 16x24 tile, install.
Every step runs the existing scripts (see studio_core.py); nothing here draws art itself.

  python fighter_studio.py            (or FighterStudio.bat in the folder above)
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageTk

import studio_core as core

QUD_GROUND = (15, 59, 58)
PAD = {"padx": 6, "pady": 4}


class Runner:
    """Runs one command at a time off the UI thread; output lines come back through a queue."""

    def __init__(self, app: "App"):
        self.app = app
        self.q: "queue.Queue[Tuple[str, object]]" = queue.Queue()
        self.pending: List[Tuple[str, List[str], Optional[Callable[[int], None]]]] = []
        self.proc: Optional[subprocess.Popen] = None
        self.label = ""
        app.after(100, self._pump)

    @property
    def busy(self) -> bool:
        return self.proc is not None or bool(self.pending)

    def run(self, label: str, argv: List[str], done: Optional[Callable[[int], None]] = None) -> None:
        self.pending.append((label, argv, done))
        if self.proc is None:
            self._next()

    def stop(self) -> None:
        self.pending.clear()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def _next(self) -> None:
        if not self.pending:
            self.app.set_busy("")
            return
        label, argv, done = self.pending.pop(0)
        self.label = label
        self.app.set_busy(label)
        self.app.log(f"\n> {label}\n  {subprocess.list2cmdline(argv)}\n")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        try:
            self.proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                         errors="replace", env=env, cwd=str(core.QUD),
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self.app.log(f"could not start: {e}\n")
            self.proc = None
            if done:
                done(-1)
            self._next()
            return

        def read(p=self.proc, cb=done):
            for line in p.stdout:
                self.q.put(("line", line))
            self.q.put(("done", (p.wait(), cb)))

        threading.Thread(target=read, daemon=True).start()

    def _pump(self) -> None:
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "line":
                    self.app.log(val)
                else:
                    rc, cb = val
                    self.app.log(f"[{self.label}: {'done' if rc == 0 else f'FAILED, exit code {rc}'}]\n")
                    self.proc = None
                    if rc != 0:
                        self.pending.clear()      # later steps depend on this one
                    if cb:
                        cb(rc)
                    self._next()
        except queue.Empty:
            pass
        self.app.after(100, self._pump)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Fighter Studio - Caves of Qud portraits and tiles")
        self.geometry("1240x900")
        self.minsize(1040, 720)
        self.table = core.load_table()
        self.cmap = core.load_content_map()
        self.chars: List[core.Character] = []
        self.ch: Optional[core.Character] = None
        self.project: Optional[core.Project] = None
        self.traits: List[core.Trait] = []
        self.result: Optional[core.PromptResult] = None
        self.art_info: Optional[Dict] = None
        self.tile: Optional[core.Tile] = None
        self.mapping: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        self.frames: List[ImageTk.PhotoImage] = []
        self.frame_i = 0
        self._keep: Dict[str, ImageTk.PhotoImage] = {}
        self._build()
        self.runner = Runner(self)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.refresh_characters()
        self.after(160, self._animate)
        self.after(500, self._env_check)

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        outer = ttk.Panedwindow(self, orient="vertical")
        outer.pack(fill="both", expand=True)
        top = ttk.Panedwindow(outer, orient="horizontal")
        outer.add(top, weight=5)

        left = ttk.Frame(top)
        top.add(left, weight=1)
        ttk.Label(left, text="Characters (exports, then build codes)").pack(anchor="w", **PAD)
        self.lst = tk.Listbox(left, width=40, exportselection=False)
        self.lst.pack(fill="both", expand=True, **PAD)
        self.lst.bind("<<ListboxSelect>>", lambda e: self.select_character())
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Refresh", command=self.refresh_characters).pack(side="left", **PAD)
        ttk.Button(row, text="Open another export...", command=self.browse_character).pack(side="left", **PAD)

        self.nb = ttk.Notebook(top)
        top.add(self.nb, weight=4)
        for title, builder in (("1 Character", self._tab_character), ("2 Prompt", self._tab_prompt), ("3 Art", self._tab_art),
                               ("4 Gear", self._tab_gear), ("5 Tile 16x24", self._tab_tile), ("6 Install", self._tab_install)):
            f = ttk.Frame(self.nb)
            self.nb.add(f, text=title)
            builder(f)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())

        bottom = ttk.Frame(outer)
        outer.add(bottom, weight=2)
        bar = ttk.Frame(bottom)
        bar.pack(fill="x")
        self.busy_var = tk.StringVar(value="Idle")
        self.env_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.busy_var).pack(side="left", **PAD)
        ttk.Button(bar, text="Stop", command=lambda: self.runner.stop()).pack(side="left", **PAD)
        ttk.Label(bar, textvariable=self.env_var, foreground="#666").pack(side="right", **PAD)
        self.logbox = tk.Text(bottom, height=9, wrap="word", font=("Consolas", 9), state="disabled")
        sb = ttk.Scrollbar(bottom, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.logbox.pack(fill="both", expand=True, **PAD)

    def _tab_character(self, f: ttk.Frame) -> None:
        self.summary = tk.Text(f, height=9, wrap="word", font=("Consolas", 9), state="disabled")
        self.summary.pack(fill="x", **PAD)
        ttk.Label(f, text="How the build shows in the art. Ticked rows go into the prompt; effects become portrait layers, "
                          "not part of the base picture.").pack(anchor="w", **PAD)
        cols = ("use", "kind", "sep", "source", "phrase", "note")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=11, selectmode="browse")
        for c, w, t in (("use", 36, "Use"), ("kind", 50, "Kind"), ("sep", 62, "Separate"), ("source", 190, "From"),
                        ("phrase", 360, "Shows as"), ("note", 170, "Note")):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, minwidth=30, stretch=c in ("phrase", "note"))
        self.tree.tag_configure("unknown", foreground="#b05a00")
        self.tree.tag_configure("off", foreground="#888")
        self.tree.pack(fill="both", expand=True, **PAD)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._trait_selected())
        ed = ttk.Frame(f)
        ed.pack(fill="x")
        self.t_phrase = tk.StringVar()
        self.t_kind = tk.StringVar(value="body")
        self.t_sep = tk.BooleanVar()
        self.t_use = tk.BooleanVar(value=True)
        ttk.Label(ed, text="Shows as:").grid(row=0, column=0, sticky="w", **PAD)
        ttk.Entry(ed, textvariable=self.t_phrase).grid(row=0, column=1, columnspan=6, sticky="ew", **PAD)
        ttk.Label(ed, text="Kind:").grid(row=1, column=0, sticky="w", **PAD)
        ttk.Combobox(ed, textvariable=self.t_kind, values=("body", "part", "effect", "none"), width=8,
                     state="readonly").grid(row=1, column=1, sticky="w", **PAD)
        ttk.Checkbutton(ed, text="Use in prompt", variable=self.t_use).grid(row=1, column=2, **PAD)
        ttk.Checkbutton(ed, text="Keep clear of the body (own layer)", variable=self.t_sep).grid(row=1, column=3, **PAD)
        ttk.Button(ed, text="Apply to this character", command=self.apply_trait).grid(row=1, column=4, **PAD)
        ttk.Button(ed, text="Also save to the table", command=lambda: self.apply_trait(save=True)).grid(row=1, column=5, **PAD)
        ed.columnconfigure(1, weight=1)
        ed.columnconfigure(6, weight=1)

    def _tab_prompt(self, f: ttk.Frame) -> None:
        g = ttk.Frame(f)
        g.pack(fill="x")
        self.o_subject = tk.StringVar()
        self.o_concept = tk.StringVar()
        self.o_target = tk.StringVar(value="designer")
        self.o_picture = tk.StringVar(value="base")
        self.o_outfit = tk.StringVar(value="bare")
        self.o_backdrop = tk.StringVar(value="dark teal")
        self.o_colors = tk.BooleanVar(value=True)
        self.o_compact = tk.BooleanVar(value=True)
        ttk.Label(g, text="Subject:").grid(row=0, column=0, sticky="w", **PAD)
        ttk.Entry(g, textvariable=self.o_subject).grid(row=0, column=1, columnspan=7, sticky="ew", **PAD)
        ttk.Label(g, text="Concept:").grid(row=1, column=0, sticky="w", **PAD)
        ttk.Entry(g, textvariable=self.o_concept).grid(row=1, column=1, columnspan=7, sticky="ew", **PAD)
        for col, (label, var, vals) in enumerate((
                ("Written for", self.o_target, ("designer", "sdxl")),
                ("Picture", self.o_picture, ("base", "dressed")),
                ("Base wears", self.o_outfit, ("bare", "wrap")),
                ("Backdrop", self.o_backdrop, tuple(core.BACKDROPS)))):
            ttk.Label(g, text=label + ":").grid(row=2, column=col * 2, sticky="w", **PAD)
            cb = ttk.Combobox(g, textvariable=var, values=vals, width=11, state="readonly")
            cb.grid(row=2, column=col * 2 + 1, sticky="w", **PAD)
            cb.bind("<<ComboboxSelected>>", lambda e: self.rebuild_prompt())
        ttk.Checkbutton(g, text="Use the tile's colours when the build names none", variable=self.o_colors,
                        command=self.rebuild_prompt).grid(row=3, column=0, columnspan=4, sticky="w", **PAD)
        ttk.Checkbutton(g, text="Short wording", variable=self.o_compact,
                        command=self.rebuild_prompt).grid(row=3, column=4, columnspan=2, sticky="w", **PAD)
        g.columnconfigure(7, weight=1)
        ttk.Label(f, text="designer = sentences for Microsoft Designer; sdxl = short tags plus a negative prompt for the local "
                          "generator.  base = bare body for layering; dressed = one picture with the worn gear.",
                  foreground="#666", wraplength=900, justify="left").pack(anchor="w", **PAD)
        self.prompt = tk.Text(f, height=13, wrap="word", font=("Segoe UI", 10), undo=True)
        self.prompt.pack(fill="both", expand=True, **PAD)
        self.prompt.bind("<<Modified>>", self._prompt_edited)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.count_var = tk.StringVar()
        ttk.Button(row, text="Rebuild from character", command=self.rebuild_prompt).pack(side="left", **PAD)
        ttk.Button(row, text="Copy prompt", command=lambda: self.copy(self.prompt.get("1.0", "end").strip())).pack(side="left", **PAD)
        ttk.Button(row, text="Open Microsoft Designer", command=lambda: webbrowser.open(core.DESIGNER_URL)).pack(side="left", **PAD)
        ttk.Button(row, text="Copy negative", command=lambda: self.copy(self.result.negative if self.result else "")).pack(side="left", **PAD)
        ttk.Button(row, text="Generate locally (GPU)", command=self.generate_local).pack(side="left", **PAD)
        ttk.Label(row, textvariable=self.count_var).pack(side="right", **PAD)
        self.notes = tk.Text(f, height=7, wrap="word", font=("Consolas", 9), state="disabled")
        self.notes.pack(fill="x", **PAD)

    def _tab_art(self, f: ttk.Frame) -> None:
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text="Import picture...", command=self.import_art).pack(side="left", **PAD)
        ttk.Button(row, text="Make portrait (key the background)", command=self.quick_portrait).pack(side="left", **PAD)
        ttk.Button(row, text="Show current portrait", command=self.show_portrait).pack(side="left", **PAD)
        self.art_var = tk.StringVar(value="No picture yet. Make one from the prompt, then import it here.")
        ttk.Label(f, textvariable=self.art_var, wraplength=900, justify="left").pack(anchor="w", **PAD)
        body = ttk.Panedwindow(f, orient="horizontal")
        body.pack(fill="both", expand=True)
        self.art_canvas = tk.Canvas(body, background="#15191e", highlightthickness=0, width=420)
        body.add(self.art_canvas, weight=3)
        right = ttk.Frame(body)
        body.add(right, weight=2)
        ttk.Label(right, text="Parts to cut into their own layers (refart spec, edit freely):").pack(anchor="w", **PAD)
        self.spec = tk.Text(right, wrap="none", font=("Consolas", 9), width=48, undo=True)
        self.spec.pack(fill="both", expand=True, **PAD)
        r2 = ttk.Frame(right)
        r2.pack(fill="x")
        ttk.Button(r2, text="Spec from character", command=self.fill_spec).pack(side="left", **PAD)
        ttk.Button(r2, text="Cut parts (GPU)", command=self.auto_layers).pack(side="left", **PAD)
        ttk.Button(r2, text="Use the cut layers", command=self.use_auto_layers).pack(side="left", **PAD)
        self.art_canvas.bind("<Configure>", lambda e: self._draw_art())

    def _tab_gear(self, f: ttk.Frame) -> None:
        ttk.Label(f, text="Equipped items. Each is painted onto the portrait as its own layer (FLUX Kontext, several minutes "
                          "per item); items without art fall back to their game tile.", wraplength=900,
                  justify="left").pack(anchor="w", **PAD)
        self.gear = tk.Listbox(f, height=12, font=("Consolas", 10))
        self.gear.pack(fill="both", expand=True, **PAD)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.g_force = tk.BooleanVar()
        ttk.Button(row, text="Fit gear onto the portrait (GPU)", command=self.fit_gear).pack(side="left", **PAD)
        ttk.Checkbutton(row, text="Redo items that already have art", variable=self.g_force).pack(side="left", **PAD)

    def _tab_tile(self, f: ttk.Frame) -> None:
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.h_style = tk.StringVar(value="auto")
        self.h_bright = tk.BooleanVar()
        self.h_outline = tk.BooleanVar(value=True)
        ttk.Label(row, text="Head:").pack(side="left", **PAD)
        ttk.Combobox(row, textvariable=self.h_style, values=core.HEAD_STYLES, width=9, state="readonly").pack(side="left", **PAD)
        ttk.Checkbutton(row, text="Bright Qud palette", variable=self.h_bright).pack(side="left", **PAD)
        ttk.Button(row, text="Bake layer sheets", command=self.bake).pack(side="left", **PAD)
        ttk.Button(row, text="Compose for this character", command=self.compose).pack(side="left", **PAD)
        ttk.Checkbutton(row, text="Show ink outline (as in game, roughly)", variable=self.h_outline,
                        command=self.load_tile).pack(side="left", **PAD)
        self.tile_var = tk.StringVar(value="No layer sheets yet.")
        ttk.Label(f, textvariable=self.tile_var, wraplength=900, justify="left").pack(anchor="w", **PAD)
        body = ttk.Frame(f)
        body.pack(fill="both", expand=True)
        self.tile_canvas = tk.Canvas(body, width=470, height=330, background="#%02x%02x%02x" % QUD_GROUND, highlightthickness=0)
        self.tile_canvas.pack(side="left", anchor="n", **PAD)
        pal = ttk.Frame(body)
        pal.pack(side="left", fill="both", expand=True, anchor="n")
        ttk.Label(pal, text="Colours on the tile (left) and what they become (right; click to pick).").pack(anchor="w", **PAD)
        self.pal_frame = ttk.Frame(pal)
        self.pal_frame.pack(anchor="w", **PAD)
        r2 = ttk.Frame(pal)
        r2.pack(anchor="w")
        ttk.Button(r2, text="Suggest from the portrait", command=self.suggest_palette).pack(side="left", **PAD)
        ttk.Button(r2, text="Reset", command=lambda: self._set_mapping({})).pack(side="left", **PAD)
        ttk.Button(r2, text="Apply to the sheet", command=self.apply_palette).pack(side="left", **PAD)
        ttk.Label(pal, text="Layers this build shows. Too many on 16x24 turn into noise: move auras and effects to the "
                            "portrait only.", wraplength=430, justify="left").pack(anchor="w", **PAD)
        self.lay_list = tk.Listbox(pal, height=9, selectmode="extended", exportselection=False, font=("Consolas", 9))
        self.lay_list.pack(fill="x", **PAD)
        r3 = ttk.Frame(pal)
        r3.pack(anchor="w")
        ttk.Button(r3, text="Selected: portrait only", command=lambda: self.move_layers(True)).pack(side="left", **PAD)
        ttk.Button(r3, text="Selected: back on the tile", command=lambda: self.move_layers(False)).pack(side="left", **PAD)
        ttk.Button(r3, text="All effects: portrait only", command=self.effects_off_tile).pack(side="left", **PAD)

    def _tab_install(self, f: ttk.Frame) -> None:
        self.status = ttk.Treeview(f, columns=("stage", "state", "detail"), show="headings", height=7)
        for c, w, t in (("stage", 190, "Step"), ("state", 70, "State"), ("detail", 560, "What is there")):
            self.status.heading(c, text=t)
            self.status.column(c, width=w, stretch=c == "detail")
        self.status.pack(fill="x", **PAD)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Button(row, text="Refresh", command=self.refresh_status).pack(side="left", **PAD)
        ttk.Button(row, text="Write the fighter file", command=self.save_fighter).pack(side="left", **PAD)
        ttk.Button(row, text="Open the work folder", command=self.open_folder).pack(side="left", **PAD)
        ttk.Button(row, text="Install into Arendeth_CYFTiles", command=self.install).pack(side="left", **PAD)
        ttk.Label(f, text="Install copies this fighter's tile, layer sheets and portrait into the mod (the mod's current copy "
                          "is saved under CavesOfQud/_backups first). The game picks the files up at its next start; choose "
                          "the fighter in Choose Your Fighter.", wraplength=900, justify="left").pack(anchor="w", **PAD)

    # ------------------------------------------------------------------ helpers
    def log(self, text: str) -> None:
        self.logbox.configure(state="normal")
        self.logbox.insert("end", text)
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def set_busy(self, label: str) -> None:
        self.busy_var.set(f"Running: {label}" if label else "Idle")

    def copy(self, text: str) -> None:
        if not text:
            messagebox.showinfo("Fighter Studio", "Nothing to copy (the designer prompt has no negative).")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log(f"copied {len(text)} characters\n")

    def _fill(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _env_check(self) -> None:
        bits = ["game running: GPU steps will be slow" if core.game_running() else "game not running",
                "refart ready" if core.refart_ready() else "refart venv missing: GPU steps unavailable"]
        self.env_var.set("   |   ".join(bits))
        self.after(30000, self._env_check)

    def _need(self, art: bool = False) -> bool:
        if not self.project:
            messagebox.showinfo("Fighter Studio", "Pick a character first.")
            return False
        if self.runner.busy:
            messagebox.showinfo("Fighter Studio", "Another step is still running.")
            return False
        if art and not self.project.source_art():
            messagebox.showinfo("Fighter Studio", "Import the character's picture first (Art tab).")
            return False
        return True

    def _gpu_ok(self, what: str) -> bool:
        if not core.refart_ready():
            messagebox.showerror("Fighter Studio", f"refart is not installed at {core.REFART_PY}.")
            return False
        note = "\n\nThe game is running, so this will take several times longer." if core.game_running() else ""
        return messagebox.askokcancel("Fighter Studio", f"{what}\n\nThis uses the graphics card and can take many minutes.{note}")

    # ------------------------------------------------------------------ characters
    def refresh_characters(self) -> None:
        self.chars = core.list_characters()
        self.lst.delete(0, "end")
        for c in self.chars:
            self.lst.insert("end", self._row(c))
        if self.chars and not self.ch:
            self.lst.selection_set(0)
            self.select_character()

    @staticmethod
    def _row(c: core.Character) -> str:
        d = c.date
        when = "build code" if c.source != "export" else f"{d[4:6]}-{d[6:8]} {d[8:10]}:{d[10:12]}" if len(d) >= 12 else d
        return f"{c.name}  L{c.level}  {when}  {core.imp.humanize_token(c.subtype)}"

    def browse_character(self) -> None:
        p = filedialog.askopenfilename(initialdir=str(core.CHARACTERS), filetypes=[
            ("Export, build code or fighter file", "*.xml *.txt *.json"), ("All", "*.*")])
        if not p:
            return
        try:
            ch = core.parse_character(Path(p)) if p.lower().endswith(".xml") else core.parse_build_source(Path(p))
        except Exception as e:
            messagebox.showerror("Fighter Studio", f"Could not read {p}:\n{e}")
            return
        self.chars.insert(0, ch)
        self.lst.insert(0, self._row(ch))
        self.lst.selection_clear(0, "end")
        self.lst.selection_set(0)
        self.select_character()

    def select_character(self) -> None:
        sel = self.lst.curselection()
        if not sel:
            return
        if self.runner.busy:
            messagebox.showinfo("Fighter Studio", "A step is still running for the current character.")
            return
        self._save_state()
        self.ch = self.chars[sel[0]]
        self.project = core.Project(self.ch)
        o = self.project.state.get("options", {})
        for var, key, default in ((self.o_subject, "subject", core.subject_of(self.ch)), (self.o_concept, "concept", ""),
                                  (self.o_target, "target", "designer"), (self.o_picture, "picture", "base"),
                                  (self.o_outfit, "outfit", "bare"), (self.o_backdrop, "backdrop", "dark teal"),
                                  (self.o_colors, "tile_colors", True), (self.o_compact, "compact", True),
                                  (self.h_style, "head_style", "auto")):
            var.set(o.get(key, default))
        self._show_summary()
        self.reload_traits()
        saved = self.project.state.get("prompt", "") or self.project.approved()[1]
        self.rebuild_prompt(keep=saved)
        self.refresh_gear()
        self.art_info = None
        src = self.project.source_art()
        if src:
            self._analyze(src)
        else:
            self.art_var.set("No picture yet. Make one from the prompt, then import it here.")
            self._draw_art()
        self.spec.delete("1.0", "end")
        auto = self.project.dir / f"{self.ch.id}.autolayers.json"
        if auto.exists():
            self.spec.insert("1.0", auto.read_text(encoding="utf-8"))
        else:
            self.fill_spec()
        self.load_tile()
        self.refresh_status()

    def _show_summary(self) -> None:
        c = self.ch
        st = c.stats
        lines = [f"{c.name}   level {c.level}   {c.genotype} / {c.subtype}" + (f"   species: {c.species}" if c.species else ""),
                 "Str {Strength} Agi {Agility} Tou {Toughness} Int {Intelligence} Wil {Willpower} Ego {Ego}".format(
                     **{k: st.get(k, "?") for k in ("Strength", "Agility", "Toughness", "Intelligence", "Willpower", "Ego")}),
                 "Body: " + (", ".join(f"{v} {k[1:]}" for k, v in sorted(c.limbs.items())) or "not read"),
                 "Mutations: " + ", ".join(core.imp.humanize_token(n) + (f" {lv}" if lv > 1 else "") for n, _, lv in c.mutations),
                 "Equipped: " + (", ".join(f"{b} ({s})" for s, b in c.items) or "nothing"),
                 "Companions: " + (", ".join(c.companions) or "none"),
                 f"Work folder: {self.project.dir}" + ("" if self.project.dir.exists() else "   (new)")]
        if c.source != "export":
            lines.insert(1, f"FROM A BUILD CODE ({c.path.name}), not an export: body from the '{c.anatomy or 'default'}' body "
                            "plan, no stats, gear only as the fighter file lists it. Export the character when you can.")
        self._fill(self.summary, "\n".join(lines))

    def reload_traits(self) -> None:
        self.traits = core.resolve_traits(self.ch, self.table, self.cmap, self.project.state.get("overrides"),
                                          self.project.hidden_layers())
        self.tree.delete(*self.tree.get_children())
        for t in self.traits:
            tags = ("unknown",) if (not t.known and t.kind != "none" and not t.include) else ("off",) if (
                not t.include or t.kind == "none") else ()
            self.tree.insert("", "end", iid=t.key, tags=tags, values=(
                "yes" if t.include and t.kind != "none" else "", t.kind, "yes" if t.separate else "", ", ".join(t.sources),
                t.phrase, t.note))

    def _trait_selected(self) -> None:
        t = self._trait()
        if t:
            self.t_phrase.set(t.phrase)
            self.t_kind.set(t.kind)
            self.t_sep.set(t.separate)
            self.t_use.set(t.include)

    def _trait(self) -> Optional[core.Trait]:
        sel = self.tree.selection()
        return next((t for t in self.traits if sel and t.key == sel[0]), None)

    def apply_trait(self, save: bool = False) -> None:
        t = self._trait()
        if not t or not self.project:
            return
        o = {"phrase": self.t_phrase.get().strip(), "kind": self.t_kind.get(), "separate": bool(self.t_sep.get()),
             "include": bool(self.t_use.get())}
        self.project.state.setdefault("overrides", {})[t.key] = o
        if save:
            if not t.key.startswith("unknown:"):
                messagebox.showinfo("Fighter Studio", "This row already comes from the table (traits.json); edit it there to "
                                                      "change every character. The change is applied to this character.")
            else:
                for f in ("phrase", "kind", "separate"):
                    setattr(t, f, o[f])
                core.save_trait_to_table(t.key.split(":", 1)[1], t)
                self.table = core.load_table()
                self.project.state["overrides"].pop(t.key, None)
                self.log(f"saved '{t.key.split(':', 1)[1]}' to {core.TRAITS_FILE.name}\n")
        key = t.key
        self.reload_traits()
        if self.tree.exists(key):
            self.tree.selection_set(key)
        self.rebuild_prompt()

    # ------------------------------------------------------------------ prompt
    def _options(self) -> core.PromptOptions:
        return core.PromptOptions(concept=self.o_concept.get(), target=self.o_target.get(), picture=self.o_picture.get(),
                                  outfit=self.o_outfit.get(), backdrop=self.o_backdrop.get(), tile_colors=bool(self.o_colors.get()),
                                  subject=self.o_subject.get(), compact=bool(self.o_compact.get()))

    def rebuild_prompt(self, keep: str = "") -> None:
        if not self.ch:
            return
        self.result = core.build_prompt(self.ch, self.traits, self._options(), self.table)
        self.prompt.delete("1.0", "end")
        self.prompt.insert("1.0", keep or self.result.prompt)
        self.prompt.edit_modified(False)
        self._count()
        r = self.result
        notes = []
        if r.negative:
            notes.append("NEGATIVE PROMPT: " + r.negative)
        if r.separate:
            notes.append("Kept clear of the body, to become their own layers: " + ", ".join(r.separate))
        if r.effects:
            notes.append("Effect layers (drawn separately, never asked for in the base picture):\n  " + "\n  ".join(r.effects))
        if r.unknown:
            notes.append("LEFT OUT, no description yet (Character tab, orange rows):\n  " + "\n  ".join(r.unknown))
        rules, approved = self.project.approved() if self.project else ([], "")
        if keep and keep.strip() != r.prompt.strip():
            notes.insert(0, ("Showing the Designer text that made this fighter's approved base (fighter file, designerPrompt)."
                             if keep.strip() == approved.strip() else "Showing your saved wording.")
                         + " 'Rebuild from character' replaces it here; the fighter file keeps the approved text.")
        if rules:
            notes.insert(0, "YOUR WORDING RULES FOR THIS CHARACTER (fighter file, conceptNotes):\n  " + "\n  ".join(rules))
        self._fill(self.notes, "\n".join(notes))

    def _prompt_edited(self, _e=None) -> None:
        if self.prompt.edit_modified():
            self._count()
            self.prompt.edit_modified(False)

    def _count(self) -> None:
        n = len(self.prompt.get("1.0", "end").strip())
        over = self.o_target.get() == "designer" and n > core.DESIGNER_LIMIT
        self.count_var.set(f"{n} characters" + (f": over {core.DESIGNER_LIMIT}, Designer may cut the end off" if over else ""))

    def _save_state(self) -> None:
        if not self.project:
            return
        o = self._options()
        self.project.state["options"] = {"subject": o.subject, "concept": o.concept, "target": o.target, "picture": o.picture,
                                         "outfit": o.outfit, "backdrop": o.backdrop, "tile_colors": o.tile_colors,
                                         "compact": o.compact, "head_style": self.h_style.get()}
        text = self.prompt.get("1.0", "end").strip()
        keep = self.result and text not in (self.result.prompt.strip(), self.project.approved()[1].strip())
        self.project.state["prompt"] = text if keep else ""
        touched = self.project.dir.exists() or self.project.state["prompt"] or self.project.state.get("overrides") or o.concept
        if touched:
            self.project.save_state()

    def generate_local(self) -> None:
        if not self._need():
            return
        if self.o_target.get() != "sdxl":
            if not messagebox.askyesno("Fighter Studio", "The local generator reads short tag prompts. Switch the prompt to "
                                                         "'sdxl' wording first?"):
                return
            self.o_target.set("sdxl")
            self.rebuild_prompt()
        if not self._gpu_ok("Generate a candidate picture locally (SDXL)."):
            return
        out = self.project.dir / "candidates" / f"{self.ch.id}_local_{core.stamp()}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        prompt = self.prompt.get("1.0", "end").strip()

        def done(rc: int) -> None:
            if rc == 0 and out.exists():
                self.log(f"candidate: {out}\nImport it on the Art tab if you want to use it.\n")
                self._show_image(out, f"Local candidate {out.name} (not imported).")
                self.nb.select(2)

        self.runner.run("generate picture", self.project.cmd_generate(prompt, self.result.negative, out), done)

    # ------------------------------------------------------------------ art
    def import_art(self) -> None:
        if not self._need():
            return
        p = filedialog.askopenfilename(title="The character's picture", initialdir=str(self.project.dir if self.project.dir.exists()
                                                                                      else Path.home() / "Downloads"),
                                       filetypes=[("Pictures", "*.png *.webp *.jpg *.jpeg"), ("All", "*.*")])
        if not p:
            return
        old = self.project.source_art()
        if old and Path(p).resolve() != old.resolve() and not messagebox.askyesno(
                "Fighter Studio", f"{old.name} is this fighter's picture now. Replace it? (The old one is kept in _backup.)"):
            return
        self._save_state()
        self.project.save_state()
        src = self.project.import_art(Path(p))
        self._analyze(src)
        self.fill_spec()
        self.refresh_status()

    def _analyze(self, src: Path) -> None:
        try:
            self.art_info = core.analyze_art(src)
        except Exception as e:
            self.art_info = None
            self.art_var.set(f"{src.name}: could not read ({e})")
            return
        i = self.art_info
        x0, y0, x1, y1 = i["crop"]
        msg = (f"{src.name}: {i['size'][0]}x{i['size'][1]}, backdrop rgb{tuple(i['background'])}; "
               f"portrait canvas {x1 - x0}x{y1 - y0} (yellow box), figure in the green box.")
        if i["warnings"]:
            msg += "  CHECK: " + "; ".join(i["warnings"]) + "."
        self.art_var.set(msg)
        self._show_image(src, None, boxes=True)

    def _show_image(self, path: Path, caption: Optional[str], boxes: bool = False) -> None:
        self._art_shown = (path, boxes)
        if caption:
            self.art_var.set(caption)
        self._draw_art()

    def _draw_art(self) -> None:
        c = self.art_canvas
        c.delete("all")
        shown = getattr(self, "_art_shown", None)
        if not shown or not shown[0].exists() or not self.project:
            return
        path, boxes = shown
        try:
            im = Image.open(path).convert("RGBA")
        except Exception:
            return
        back = Image.new("RGBA", im.size, (21, 25, 30, 255))
        back.alpha_composite(im)
        if boxes and self.art_info:
            d = ImageDraw.Draw(back)
            lw = max(2, im.width // 300)
            d.rectangle(self.art_info["figure"], outline=(80, 220, 120, 255), width=lw)
            d.rectangle(self.art_info["crop"], outline=(240, 210, 60, 255), width=lw)
        cw, chh = max(50, c.winfo_width()), max(50, c.winfo_height())
        back.thumbnail((cw - 8, chh - 8))
        self._keep["art"] = ImageTk.PhotoImage(back)
        c.create_image(cw // 2, chh // 2, image=self._keep["art"])

    def quick_portrait(self) -> None:
        if not self._need(art=True) or not self.art_info:
            return
        pd = self.project.portrait_dir
        have = len(list(pd.glob("*.png"))) if pd.exists() else 0
        if have > 1 or (pd / "items").exists():
            if not messagebox.askyesno("Fighter Studio", f"This fighter already has a layered portrait ({have} layers"
                                       + (", fitted gear" if (pd / "items").exists() else "") + ").\n\nMaking a new one "
                                       "replaces base.png and portrait.xml, so the other layers stop showing until they are "
                                       "listed again. The current folder is copied to _backup first.\n\nGo on?", icon="warning"):
                return
        spec = self.project.hand_spec()
        if spec and not messagebox.askyesno(
                "Fighter Studio", f"This fighter has a hand-made cut spec ({spec.name}).\n\nIts portrait should be rebuilt from that "
                "spec with cyf_portrait_layers.py, not from a plain background key, or its cut layers are lost.\n\n"
                "Replace the portrait with a single keyed layer anyway?", icon="warning", default="no"):
            return
        if pd.exists():
            self.log(f"backup: {self.project.backup(pd)}\n")
        try:
            out = self.project.make_base_portrait(self.art_info)
        except Exception as e:
            messagebox.showerror("Fighter Studio", f"Could not make the portrait:\n{e}")
            return
        self.log(f"portrait: {out} (one layer; cut parts and fit gear to add more)\n")
        self.show_portrait()
        self.refresh_gear()
        self.refresh_status()

    def show_portrait(self) -> None:
        if not self.project:
            return
        pd = self.project.portrait_dir
        prev = self.project.dir / "preview" / f"{self.ch.id}_portrait_all.png"
        pick = prev if prev.exists() and (pd / "base.png").exists() and prev.stat().st_mtime >= (pd / "base.png").stat().st_mtime \
            else pd / "base.png"
        if not pick.exists():
            messagebox.showinfo("Fighter Studio", "No portrait yet.")
            return
        self._show_image(pick, f"Portrait: {pick}")

    def fill_spec(self) -> None:
        if not self.project:
            return
        spec = self.project.auto_spec(self.traits, self.art_info)
        self.spec.delete("1.0", "end")
        self.spec.insert("1.0", json.dumps(spec, indent=1))

    def auto_layers(self) -> None:
        if not self._need(art=True):
            return
        try:
            spec = json.loads(self.spec.get("1.0", "end"))
        except ValueError as e:
            messagebox.showerror("Fighter Studio", f"The spec is not valid JSON:\n{e}")
            return
        if not spec.get("parts"):
            messagebox.showinfo("Fighter Studio", "The spec names no parts to cut. Use 'Make portrait' for a single layer.")
            return
        if not self._gpu_ok(f"Find and cut {len(spec['parts'])} kinds of parts out of the picture."):
            return
        spec["source"] = self.project.source_art().name
        path = self.project.dir / f"{self.ch.id}.autolayers.json"
        self.project.backup(path)
        path.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")

        def done(rc: int) -> None:
            if rc == 0:
                sheet = next(iter(sorted((self.project.dir / "autolayers_preview").glob("*sheet*.png"))), None)
                if sheet:
                    self._show_image(sheet, "Cut layers preview. 'Use the cut layers' makes them this fighter's portrait.")

        self.runner.run("cut parts", self.project.cmd_auto_layers(path), done)

    def use_auto_layers(self) -> None:
        if not self._need():
            return
        hits = list((self.project.dir / "autolayers").rglob("portrait.xml"))
        if not hits:
            messagebox.showinfo("Fighter Studio", "No cut layers yet (run 'Cut parts' first).")
            return
        src, pd = hits[0].parent, self.project.portrait_dir
        if not messagebox.askyesno("Fighter Studio", f"Replace this fighter's portrait layers with the cut layers from\n{src}?\n\n"
                                                     "Fitted gear art is kept. The current folder is copied to _backup first."):
            return
        if pd.exists():
            self.log(f"backup: {self.project.backup(pd)}\n")
        pd.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file() and f.suffix.lower() in (".png", ".xml"):
                shutil.copy2(f, pd / f.name)
        self.log(f"portrait layers <- {src}\n")
        self.refresh_status()

    # ------------------------------------------------------------------ gear
    def refresh_gear(self) -> None:
        self.gear.delete(0, "end")
        if self.project:
            for slot, bp, has in self.project.gear_status():
                self.gear.insert("end", f"{slot:8} {bp:44} {'has art' if has else 'no art yet (game tile is used)'}")

    def fit_gear(self) -> None:
        if not self._need():
            return
        if not (self.project.portrait_dir / "portrait.xml").exists():
            messagebox.showinfo("Fighter Studio", "Make the portrait first (Art tab): gear is painted onto it.")
            return
        if self.ch.source != "export":
            messagebox.showinfo("Fighter Studio", "Fitting gear needs the character's export: a build code does not say "
                                                  "which body slot each item is worn in.")
            return
        if not self.ch.items:
            messagebox.showinfo("Fighter Studio", "This character has nothing equipped.")
            return
        todo = [bp for _, bp, has in self.project.gear_status() if self.g_force.get() or not has]
        if not todo:
            messagebox.showinfo("Fighter Studio", "Every equipped item already has art. Tick 'Redo' to paint them again.")
            return
        if not self._gpu_ok(f"Paint {len(todo)} equipped items onto the portrait, one at a time:\n" + ", ".join(todo)):
            return
        subject = self.o_subject.get().strip() or core.subject_of(self.ch)
        self.runner.run("fit gear", self.project.cmd_gear(subject, bool(self.g_force.get())),
                        lambda rc: (self.refresh_gear(), self.refresh_status()))

    # ------------------------------------------------------------------ tile
    def save_fighter(self) -> Optional[Path]:
        if not self.project:
            return None
        self._save_state()
        try:
            p = self.project.save_fighter_json(self.h_style.get(), self.o_concept.get())
        except Exception as e:
            messagebox.showerror("Fighter Studio", f"Could not write the fighter file:\n{e}")
            return None
        self.project.save_state()
        self.log(f"fighter file: {p}\n")
        self.reload_traits()
        self.refresh_status()
        return p

    def bake(self) -> None:
        if not self._need():
            return
        ld = self.project.layers_dir
        if ld.exists() and any(ld.glob("*.png")):
            if not messagebox.askyesno("Fighter Studio", "This fighter already has layer sheets.\n\nBaking redraws every sheet "
                                       "from the templates, so hand-drawn changes and applied palettes are lost. The current "
                                       "sheets are copied to _backup first.\n\nBake again?", icon="warning"):
                return
            self.log(f"backup: {self.project.backup(ld)}\n")
        if not self.save_fighter():
            return
        self._compose(("bake layer sheets", self.project.cmd_bake(self.h_style.get(), bool(self.h_bright.get()))))

    def compose(self) -> None:
        if not self._need():
            return
        if not self.project.tile_json.exists():
            messagebox.showinfo("Fighter Studio", "Bake the layer sheets first.")
            return
        self._compose()

    def _compose(self, first: Optional[Tuple[str, List[str]]] = None) -> None:
        """Rewrite the fighter's plain tile from its layers, after `first` if given. An export goes through
        cyf_compose_fighter.py; a build-code character has no export for it, so that is done here."""
        def after(rc: int = 0) -> None:
            self.load_tile()
            self.refresh_status()

        if self.ch.source == "export":
            if first:
                self.runner.run(*first)
            self.runner.run("compose tile", self.project.cmd_compose(), after)
            return

        def local(rc: int = 0) -> None:
            if rc == 0:
                try:
                    self.log(f"tile + frames -> {core.Tile(self.project).write_static()}\n")
                except Exception as e:
                    self.log(f"compose failed: {e}\n")
            after()

        if first:
            self.runner.run(first[0], first[1], local)
        else:
            local()

    def load_tile(self) -> None:
        self.tile = None
        self.frames = []
        self.tile_canvas.delete("all")
        for w in self.pal_frame.winfo_children():
            w.destroy()
        self.lay_list.delete(0, "end")
        if not self.project or not self.project.tile_json.exists():
            self.tile_var.set("No layer sheets yet. 'Bake layer sheets' draws them from the templates for this fighter.")
            return
        try:
            self.tile = core.Tile(self.project)
        except Exception as e:
            self.tile_var.set(f"Could not read the layer set: {e}")
            return
        t = self.tile
        self.tile_var.set(f"Body plan {t.plan['id']}: {len(t.layers)} layers on the tile, "
                          f"{len(t.matched) - len(t.layers)} on the portrait only."
                          + (f"  Never shown: {', '.join(t.never)}." if t.never else ""))
        for l in t.matched:
            where = "portrait only" if l["id"] in t.off_tile else "on the tile"
            self.lay_list.insert("end", f"{l['id']:14} {where:14} {'effect' if core.is_effect_layer(l['id']) else ''}")
        self._set_mapping({k: v for k, v in self.mapping.items() if k in dict(t.palette())} if self.mapping else {})

    def _set_mapping(self, mapping: Dict) -> None:
        self.mapping = dict(mapping)
        for w in self.pal_frame.winfo_children():
            w.destroy()
        if not self.tile:
            return
        for i, (col, n) in enumerate(self.tile.palette()):
            to = self.mapping.get(col, col)
            r, c = i % 7, (i // 7) * 4
            tk.Label(self.pal_frame, width=4, background="#%02x%02x%02x" % col, relief="solid", borderwidth=1).grid(row=r, column=c, padx=2, pady=2)
            ttk.Label(self.pal_frame, text="->").grid(row=r, column=c + 1)
            tk.Button(self.pal_frame, width=4, background="#%02x%02x%02x" % to, relief="raised",
                      command=lambda k=col: self._pick(k)).grid(row=r, column=c + 2, padx=2, pady=2)
            ttk.Label(self.pal_frame, text=f"{n} px   ").grid(row=r, column=c + 3, sticky="w")
        self._render_tile()

    def _pick(self, col: Tuple[int, int, int]) -> None:
        cur = self.mapping.get(col, col)
        rgb, _ = colorchooser.askcolor(color="#%02x%02x%02x" % cur, title="Colour on the tile")
        if rgb:
            m = dict(self.mapping)
            m[col] = tuple(int(v) for v in rgb)
            self._set_mapping(m)

    def _render_tile(self) -> None:
        t = self.tile
        if not t:
            return
        frames = t.frames()
        if self.mapping:
            for f in frames:
                px = f.load()
                for y in range(f.height):
                    for x in range(f.width):
                        r, g, b, a = px[x, y]
                        if a and (r, g, b) in self.mapping:
                            px[x, y] = self.mapping[(r, g, b)] + (a,)
        if self.h_outline.get():
            frames = [core.ink_outline(f) for f in frames]
        self._tile_small = [ImageTk.PhotoImage(frames[0].resize((t.w * s, t.h * s), Image.Resampling.NEAREST)) for s in (1, 2, 3)]
        self.frames = [ImageTk.PhotoImage(f.resize((t.w * 12, t.h * 12), Image.Resampling.NEAREST)) for f in frames]
        self.frame_i = 0

    def _animate(self) -> None:
        c = self.tile_canvas
        if self.frames:
            c.delete("all")
            self.frame_i = (self.frame_i + 1) % len(self.frames)
            c.create_image(16, 16, anchor="nw", image=self.frames[self.frame_i])
            x = 16 + self.tile.w * 12 + 30
            c.create_text(x, 16, anchor="nw", fill="#b1c9c3", text="game size, x2, x3")
            y = 40
            for im in self._tile_small:
                c.create_image(x, y, anchor="nw", image=im)
                y += im.height() + 14
        self.after(160, self._animate)

    def move_layers(self, off: bool) -> None:
        if not self._need() or not self.tile:
            return
        picked = {self.tile.matched[i]["id"] for i in self.lay_list.curselection()}
        if not picked:
            messagebox.showinfo("Fighter Studio", "Select layers in the list first.")
            return
        cur = set(self.tile.off_tile)
        self._set_off_tile((cur | picked) if off else (cur - picked))

    def effects_off_tile(self) -> None:
        if not self._need() or not self.tile:
            return
        self._set_off_tile(set(self.tile.off_tile) | {l["id"] for l in self.tile.matched if core.is_effect_layer(l["id"])})

    def _set_off_tile(self, ids: set) -> None:
        if ids == set(self.tile.off_tile):
            return
        self.tile.set_off_tile(sorted(ids))
        self.log(f"portrait-only layers: {', '.join(sorted(ids)) or 'none'}\n")
        self._compose()

    def suggest_palette(self) -> None:
        if not self.tile:
            return
        src = self.project.portrait_dir / "base.png"
        if not src.exists():
            src = self.project.source_art() or self.project.pinned_base
        if not src or not src.exists():
            messagebox.showinfo("Fighter Studio", "No portrait or picture to take colours from yet.")
            return
        m = core.suggest_palette(self.tile.palette(), core.portrait_palette(src))
        if not m:
            messagebox.showinfo("Fighter Studio", "The tile already matches, or no clear body colour was found.")
            return
        self.log(f"palette suggested from {src.name}: {len(m)} colours change (not applied yet)\n")
        self._set_mapping(m)

    def apply_palette(self) -> None:
        if not self._need() or not self.tile:
            return
        if not {k: v for k, v in self.mapping.items() if k != v}:
            messagebox.showinfo("Fighter Studio", "No colour is changed yet.")
            return
        bak = self.tile.apply_palette(self.mapping)
        self.log(f"palette applied to {self.tile.sheet_path.name} (backup: {bak})\n")
        self.mapping = {}
        self._compose()

    # ------------------------------------------------------------------ install
    def refresh_status(self) -> None:
        self.status.delete(*self.status.get_children())
        if not self.project:
            return
        for stage, done, detail in self.project.status():
            self.status.insert("", "end", values=(stage, "ready" if done else "-", detail))

    def open_folder(self) -> None:
        if self.project:
            self.project.dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.project.dir))  # noqa: S606 (the fighter's own work folder)

    def install(self) -> None:
        if not self._need():
            return
        if not self.project.tile_json.exists():
            messagebox.showinfo("Fighter Studio", "There is no tile to install yet (Tile tab).")
            return
        if not messagebox.askyesno("Fighter Studio", f"Install '{self.ch.id}' into\n{core.MOD}?\n\nThe mod's current files for this "
                                                     "fighter are copied to CavesOfQud/_backups first."):
            return
        bak = self.project.backup_installed()
        self.log(f"mod backup: {bak or 'nothing installed for this fighter yet'}\n")
        self.runner.run("install", self.project.cmd_install(), lambda rc: self.refresh_status())

    # ------------------------------------------------------------------ misc
    def _tab_changed(self) -> None:
        if self.nb.index("current") == 5:
            self.refresh_status()

    def _close(self) -> None:
        if self.runner.busy and not messagebox.askyesno("Fighter Studio", "A step is still running. Stop it and close?"):
            return
        self.runner.stop()
        try:
            self._save_state()
        finally:
            self.destroy()


def main() -> int:
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
