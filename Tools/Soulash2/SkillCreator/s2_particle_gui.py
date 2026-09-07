#!/usr/bin/env python3
"""Native desktop producer for Soulash 2 skill FX.

Clones core_2 motion, tints vanilla particles32 glyphs, and binds them to a
skill spec. Does not copy or extend the global particles32 atlas.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"Tkinter is required for the particle producer: {exc}") from exc

from s2_animations import PRESETS, compose_animation, recolor_animation
from s2_assets import load_animation, search_animations
from s2_particle_art import (
    PARTICLE_TILE,
    THEMES,
    AtlasCache,
    infer_theme,
    particle_rgba,
    pil_to_photo,
    playback_span,
    set_particle_rgba,
    theme_rgba,
)
from s2_paths import output_root
from s2_schema import slug_name
from s2_skill_spec import add_animation, list_staged_specs, load_spec, save_spec

_BG = "#141618"
_PANEL = "#1e2226"
_INK = "#e8e4d9"
_MUTED = "#9a9588"
_ACCENT = "#7aa8c4"
_SCALE = 5
_PAGE = 64


def _dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _num(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


class ParticleProducer(tk.Tk):
    def __init__(self, spec_path: Optional[Path] = None) -> None:
        super().__init__()
        self.title("Soulash 2 — Particle FX Producer")
        self.geometry("1320x860")
        self.minsize(1020, 680)
        self.configure(bg=_BG)

        self.atlas = AtlasCache()
        self.spec: Optional[Dict[str, Any]] = None
        self.spec_path: Optional[Path] = spec_path
        self.working: Optional[Dict[str, Any]] = None
        self.source_id = ""
        self.in_spec = False
        self.dirty = False
        self.selected_part = 0
        self.playing = False
        self.play_t = 0.0
        self.play_job = None
        self.atlas_page = 0
        self._photos: List[Any] = []
        self._ignore = False
        self._drawing = False

        self.search_var = tk.StringVar()
        self.preset_var = tk.StringVar(value="bolt")
        self.theme_var = tk.StringVar(value="water")
        self.spec_var = tk.StringVar()
        self.bind_var = tk.StringVar()
        self.clone_impact = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Load a spec, pick a vanilla FX, tint, then add it.")

        self._theme()
        self._menus()
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(60, self._boot)

    def _theme(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=_BG, foreground=_INK, fieldbackground=_PANEL)
        style.configure("TFrame", background=_BG)
        style.configure("Panel.TFrame", background=_PANEL)
        style.configure("TLabel", background=_BG, foreground=_INK)
        style.configure("Muted.TLabel", background=_BG, foreground=_MUTED)
        style.configure("Accent.TLabel", background=_BG, foreground=_ACCENT)
        style.configure("TButton", background=_PANEL, foreground=_INK, padding=4)
        style.configure("TCheckbutton", background=_BG, foreground=_INK)
        style.configure("TEntry", fieldbackground=_PANEL, foreground=_INK)
        style.configure("TCombobox", fieldbackground=_PANEL, background=_PANEL, foreground=_INK)
        style.configure("Treeview", background=_PANEL, fieldbackground=_PANEL, foreground=_INK, rowheight=22)
        style.configure("Treeview.Heading", background="#243038", foreground=_ACCENT)
        style.map("Treeview", background=[("selected", "#2a4050")], foreground=[("selected", _ACCENT)])
        style.configure("Horizontal.TScale", background=_BG)

    def _menus(self) -> None:
        menubar = tk.Menu(self)
        file_m = tk.Menu(menubar, tearoff=0)
        file_m.add_command(label="Open spec…", command=self._open_spec, accelerator="Ctrl+O")
        file_m.add_command(label="Save spec", command=self._save_spec, accelerator="Ctrl+S")
        file_m.add_separator()
        file_m.add_command(label="Copy FX JSON", command=self._copy_json)
        file_m.add_command(label="Export preview PNGs…", command=self._export_preview, accelerator="Ctrl+E")
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self._close)
        menubar.add_cascade(label="File", menu=file_m)
        help_m = tk.Menu(menubar, tearoff=0)
        help_m.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_m)
        self.config(menu=menubar)
        self.bind("<Control-o>", lambda e: self._open_spec())
        self.bind("<Control-s>", lambda e: self._save_spec())
        self.bind("<Control-e>", lambda e: self._export_preview())
        self.bind("<space>", lambda e: self._toggle_play())

    def _layout(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(bar, text="Spec").pack(side=tk.LEFT)
        self.spec_combo = ttk.Combobox(bar, textvariable=self.spec_var, width=28, state="readonly")
        self.spec_combo.pack(side=tk.LEFT, padx=4)
        self.spec_combo.bind("<<ComboboxSelected>>", lambda e: self._load_named_spec())
        ttk.Button(bar, text="Open…", command=self._open_spec).pack(side=tk.LEFT, padx=2)

        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Label(bar, text="Preset").pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(
            bar, textvariable=self.preset_var, values=sorted(PRESETS), width=12, state="readonly"
        )
        self.preset_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Load preset", command=self._load_preset).pack(side=tk.LEFT)

        ttk.Label(bar, text="Theme").pack(side=tk.LEFT, padx=(10, 0))
        self.theme_combo = ttk.Combobox(
            bar, textvariable=self.theme_var, values=sorted(THEMES), width=10, state="readonly"
        )
        self.theme_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Apply tint", command=self._apply_theme).pack(side=tk.LEFT)
        ttk.Button(bar, text="Pick color…", command=self._pick_color).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(bar, text="Clone impact", variable=self.clone_impact).pack(side=tk.LEFT, padx=8)

        ttk.Button(bar, text="Export PNGs", command=self._export_preview).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bar, text="Add to spec", command=self._add_to_spec).pack(side=tk.RIGHT)
        ttk.Button(bar, text="Save spec", command=self._save_spec).pack(side=tk.RIGHT, padx=4)

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        left = ttk.Frame(paned, width=280)
        center = ttk.Frame(paned)
        right = ttk.Frame(paned, width=340)
        paned.add(left, weight=0)
        paned.add(center, weight=1)
        paned.add(right, weight=0)

        ttk.Label(left, text="Vanilla / workshop FX", style="Accent.TLabel").pack(anchor=tk.W, padx=4, pady=(4, 2))
        ttk.Entry(left, textvariable=self.search_var).pack(fill=tk.X, padx=4)
        self.search_var.trace_add("write", lambda *_: self.after(180, self._fill_search))
        self.search_tv = ttk.Treeview(left, columns=("src",), show="tree headings", selectmode="browse", height=12)
        self.search_tv.heading("#0", text="FX")
        self.search_tv.heading("src", text="From")
        self.search_tv.column("#0", width=170)
        self.search_tv.column("src", width=80)
        self.search_tv.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.search_tv.bind("<<TreeviewSelect>>", lambda e: self._pick_search())

        ttk.Label(left, text="This spec", style="Accent.TLabel").pack(anchor=tk.W, padx=4)
        self.spec_tv = ttk.Treeview(left, columns=("parts",), show="tree headings", selectmode="browse", height=8)
        self.spec_tv.heading("#0", text="Animation")
        self.spec_tv.heading("parts", text="P")
        self.spec_tv.column("#0", width=180)
        self.spec_tv.column("parts", width=40, anchor=tk.CENTER)
        self.spec_tv.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.spec_tv.bind("<<TreeviewSelect>>", lambda e: self._pick_spec_anim())

        ttk.Label(left, text="Bind ability").pack(anchor=tk.W, padx=4)
        self.bind_combo = ttk.Combobox(left, textvariable=self.bind_var, width=28)
        self.bind_combo.pack(fill=tk.X, padx=4, pady=(0, 6))

        stage = ttk.Frame(center)
        stage.pack(fill=tk.BOTH, expand=True)
        self.preview = tk.Canvas(stage, bg="#0c0e10", highlightthickness=0, height=280)
        self.preview.pack(fill=tk.BOTH, expand=True, pady=4)
        self.preview.bind("<Configure>", lambda e: self._draw_preview())
        strip = ttk.Frame(center)
        strip.pack(fill=tk.X)
        ttk.Button(strip, text="Play", command=self._toggle_play).pack(side=tk.LEFT)
        ttk.Button(strip, text="Reset", command=self._reset_play).pack(side=tk.LEFT, padx=4)
        self.time_var = tk.DoubleVar(value=0)
        self.time_scale = ttk.Scale(
            strip, from_=0, to=800, orient=tk.HORIZONTAL, variable=self.time_var, command=self._scrub
        )
        self.time_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.time_label = ttk.Label(strip, text="0", style="Muted.TLabel")
        self.time_label.pack(side=tk.LEFT)

        self.timeline = tk.Canvas(center, bg=_PANEL, highlightthickness=0, height=88)
        self.timeline.pack(fill=tk.X, pady=4)
        self.timeline.bind("<Button-1>", self._click_timeline)

        atlas_bar = ttk.Frame(center)
        atlas_bar.pack(fill=tk.X)
        ttk.Label(atlas_bar, text="particles32 glyphs (top-left index 0)", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Button(atlas_bar, text="◀", command=lambda: self._page(-1), width=3).pack(side=tk.RIGHT)
        self.page_label = ttk.Label(atlas_bar, text="1")
        self.page_label.pack(side=tk.RIGHT, padx=6)
        ttk.Button(atlas_bar, text="▶", command=lambda: self._page(1), width=3).pack(side=tk.RIGHT)
        self.atlas_canvas = tk.Canvas(center, bg=_PANEL, highlightthickness=0, height=148)
        self.atlas_canvas.pack(fill=tk.X)
        self.atlas_canvas.bind("<Button-1>", self._click_atlas)
        self.atlas_canvas.bind("<Configure>", lambda e: self._draw_atlas())

        form = ttk.Frame(right)
        form.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(form, text="Working FX", style="Accent.TLabel").grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.fields: Dict[str, tk.StringVar] = {}
        rows = (
            ("id", "Id"),
            ("name", "Name"),
            ("animation", "Inner FX"),
            ("sound", "Sound id"),
        )
        for i, (key, label) in enumerate(rows, start=1):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky=tk.W, pady=1)
            var = tk.StringVar()
            self.fields[key] = var
            ttk.Entry(form, textvariable=var, width=28).grid(row=i, column=1, sticky=tk.EW, pady=1)
            var.trace_add("write", lambda *_: self._from_fields())
        form.columnconfigure(1, weight=1)
        self.chain = tk.BooleanVar()
        self.roof = tk.BooleanVar()
        self.blocking = tk.BooleanVar()
        flags = ttk.Frame(right)
        flags.pack(fill=tk.X, padx=6)
        ttk.Checkbutton(flags, text="chain_particles", variable=self.chain, command=self._from_fields).pack(anchor=tk.W)
        ttk.Checkbutton(flags, text="ignore_roof", variable=self.roof, command=self._from_fields).pack(anchor=tk.W)
        ttk.Checkbutton(flags, text="blocking", variable=self.blocking, command=self._from_fields).pack(anchor=tk.W)

        ttk.Label(right, text="Particles", style="Accent.TLabel").pack(anchor=tk.W, padx=6, pady=(8, 2))
        self.part_tv = ttk.Treeview(
            right, columns=("tile", "delay", "life"), show="tree headings", selectmode="browse", height=8
        )
        self.part_tv.heading("#0", text="#")
        self.part_tv.heading("tile", text="Tile")
        self.part_tv.heading("delay", text="Delay")
        self.part_tv.heading("life", text="Life")
        self.part_tv.column("#0", width=36)
        self.part_tv.column("tile", width=60)
        self.part_tv.column("delay", width=70)
        self.part_tv.column("life", width=70)
        self.part_tv.pack(fill=tk.BOTH, expand=True, padx=6)
        self.part_tv.bind("<<TreeviewSelect>>", lambda e: self._pick_part())

        inspector = ttk.Frame(right)
        inspector.pack(fill=tk.X, padx=6, pady=6)
        self.part_fields: Dict[str, tk.StringVar] = {}
        for i, (key, label) in enumerate(
            (
                ("tile_id", "tile_id"),
                ("delay", "delay"),
                ("life", "life"),
                ("flags", "flags"),
                ("velocity", "velocity"),
                ("height", "height"),
                ("elevation", "elevation"),
                ("on_impact", "on_impact"),
                ("color", "color R,G,B,A"),
            )
        ):
            ttk.Label(inspector, text=label).grid(row=i, column=0, sticky=tk.W)
            var = tk.StringVar()
            self.part_fields[key] = var
            ttk.Entry(inspector, textvariable=var, width=22).grid(row=i, column=1, sticky=tk.EW, pady=1)
            var.trace_add("write", lambda *_: self._from_part_fields())
        inspector.columnconfigure(1, weight=1)
        ttk.Button(right, text="Use selected glyph", command=self._assign_glyph).pack(anchor=tk.W, padx=6, pady=(0, 8))

        ttk.Label(self, textvariable=self.status, style="Muted.TLabel").pack(fill=tk.X, padx=8, pady=(0, 6))

    def _boot(self) -> None:
        specs = [p.parent.name for p in list_staged_specs()]
        self.spec_combo["values"] = specs
        if self.spec_path and self.spec_path.is_file():
            self._load_path(self.spec_path)
        elif specs:
            self.spec_var.set(specs[0])
            self._load_named_spec()
        self._fill_search()
        self._draw_atlas()
        self._load_preset()

    def _about(self) -> None:
        messagebox.showinfo(
            "Particle FX Producer",
            "Every particle tile_id is a glyph on the global particles32 atlas.\n"
            "This tool clones core_2 motion and tints those glyphs.\n"
            "It does not copy particles.png or append extra rows — extra skills would fight over that name.\n"
            "Space plays the preview. Click a glyph to assign it to the selected particle.",
        )

    def _close(self) -> None:
        if self.dirty and not messagebox.askokcancel("Quit", "Unsaved FX edits. Quit anyway?"):
            return
        self.destroy()

    def _open_spec(self) -> None:
        path = filedialog.askopenfilename(
            title="Open skill spec",
            initialdir=str(output_root()),
            filetypes=[("skill.json", "skill.json"), ("JSON", "*.json")],
        )
        if path:
            self._load_path(Path(path))

    def _load_named_spec(self) -> None:
        name = self.spec_var.get().strip()
        if not name:
            return
        path = output_root() / name / "skill.json"
        if path.is_file():
            self._load_path(path)

    def _load_path(self, path: Path) -> None:
        try:
            spec = load_spec(path)
        except Exception as exc:
            messagebox.showerror("Open spec", str(exc))
            return
        self.spec = spec
        self.spec_path = path
        self.spec_var.set(path.parent.name)
        self.dirty = False
        abilities = [str(a.get("id") or "") for a in spec.get("abilities") or [] if a.get("id")]
        self.bind_combo["values"] = abilities
        if abilities and not self.bind_var.get():
            self.bind_var.set(abilities[0])
        self._fill_spec_anims()
        self.status.set(f"Loaded {path.parent.name}  ({len(spec.get('animations') or [])} FX)")

    def _save_spec(self) -> None:
        if not self.spec or not self.spec_path:
            messagebox.showinfo("Save", "Open a skill spec first.")
            return
        if self.working and self.in_spec:
            self._commit_working()
        save_spec(self.spec, self.spec_path)
        self.dirty = False
        self.status.set(f"Saved {self.spec_path}")

    def _fill_search(self) -> None:
        q = self.search_var.get()
        for iid in self.search_tv.get_children():
            self.search_tv.delete(iid)
        try:
            hits = search_animations(q, limit=60 if q else 40)
        except Exception as exc:
            self.status.set(str(exc))
            return
        for hit in hits:
            self.search_tv.insert("", tk.END, iid=f"v:{hit['id']}", text=hit["name"], values=(hit["source"],))

    def _fill_spec_anims(self) -> None:
        for iid in self.spec_tv.get_children():
            self.spec_tv.delete(iid)
        if not self.spec:
            return
        for anim in self.spec.get("animations") or []:
            aid = str(anim.get("id") or "")
            self.spec_tv.insert(
                "",
                tk.END,
                iid=f"s:{aid}",
                text=str(anim.get("name") or aid),
                values=(len(anim.get("particles") or []),),
            )

    def _pick_search(self) -> None:
        sel = self.search_tv.selection()
        if not sel:
            return
        aid = sel[0].split(":", 1)[-1]
        try:
            anim = load_animation(aid)
        except FileNotFoundError as exc:
            self.status.set(str(exc))
            return
        self.source_id = aid
        self.in_spec = False
        self.working = deepcopy(anim)
        self.working.pop("_cloned_from", None)
        self.selected_part = 0
        self._reset_play()
        self._sync_fields()
        self._draw_all()
        self.status.set(f"Preview {anim.get('name')} [{aid}] — Add to spec to keep a tinted clone.")

    def _pick_spec_anim(self) -> None:
        sel = self.spec_tv.selection()
        if not sel or not self.spec:
            return
        aid = sel[0].split(":", 1)[-1]
        anim = next((a for a in self.spec.get("animations") or [] if str(a.get("id")) == aid), None)
        if not anim:
            return
        self.source_id = aid
        self.in_spec = True
        self.working = anim
        self.selected_part = 0
        self._reset_play()
        self._sync_fields()
        self._draw_all()
        self.status.set(f"Editing spec FX {aid}")

    def _load_preset(self) -> None:
        key = self.preset_var.get()
        meta = PRESETS.get(key) or {}
        source = meta.get("clone")
        if not source:
            return
        try:
            anim = load_animation(source)
        except FileNotFoundError as exc:
            messagebox.showerror("Preset", str(exc))
            return
        self.source_id = source
        self.in_spec = False
        self.working = deepcopy(anim)
        self.working.pop("_cloned_from", None)
        guessed = infer_theme(str(anim.get("name") or key), fallback=self.theme_var.get())
        self.theme_var.set(guessed)
        self.selected_part = 0
        self._reset_play()
        self._sync_fields()
        self._draw_all()
        self.status.set(f"Preset {key} <- {source}  ({meta.get('blurb') or ''})")

    def _apply_theme(self) -> None:
        if not self.working:
            return
        rgba = theme_rgba(self.theme_var.get())
        recolor_animation(self.working, rgba)
        self.dirty = True
        self._sync_fields()
        self._draw_all()

    def _pick_color(self) -> None:
        rgb, _ = colorchooser.askcolor(title="Particle tint")
        if not rgb or not self.working:
            return
        recolor_animation(self.working, [int(rgb[0]), int(rgb[1]), int(rgb[2]), 255])
        self.dirty = True
        self._sync_fields()
        self._draw_all()

    def _new_id(self) -> str:
        name = self.fields["name"].get() or self.preset_var.get() or "fx"
        prefix = (self.spec or {}).get("skill_id") or (self.spec_path.parent.name if self.spec_path else "fx")
        return f"{prefix}_{slug_name(name).lower()}"

    def _add_to_spec(self) -> None:
        if not self.spec or not self.spec_path:
            messagebox.showinfo("Add", "Open a skill spec first.")
            return
        if not self.working:
            return
        new_id = self.fields["id"].get().strip() or self._new_id()
        name = self.fields["name"].get().strip() or new_id
        try:
            rows = compose_animation(
                source=self.source_id or str(self.working.get("id")),
                new_id=new_id,
                name=name,
                color=particle_rgba((self.working.get("particles") or [{}])[0]) if self.working.get("particles") else None,
                clone_impact=bool(self.clone_impact.get()),
            )
        except (FileNotFoundError, KeyError, ValueError) as exc:
            messagebox.showerror("Add FX", str(exc))
            return
        main = rows[0]
        if self.working.get("particles"):
            main["particles"] = deepcopy(self.working["particles"])
        for key in ("chain_particles", "ignore_roof", "blocking", "animation", "sound", "camera_shake"):
            if key in self.working:
                main[key] = deepcopy(self.working[key])
        bind = self.bind_var.get().strip() or None
        try:
            for extra in rows[1:]:
                add_animation(self.spec, extra)
            add_animation(self.spec, main, bind_ability=bind)
        except KeyError as exc:
            messagebox.showerror("Bind", str(exc))
            return
        self.in_spec = True
        self.working = main
        self.source_id = str(main.get("id"))
        self.fields["id"].set(str(main.get("id")))
        self.dirty = True
        self._fill_spec_anims()
        self._sync_fields()
        extra = f" + {len(rows) - 1} impact" if len(rows) > 1 else ""
        bound = f" bound to {bind}" if bind else ""
        self.status.set(f"Added {main.get('id')}{extra}{bound}. Save spec to keep it.")

    def _commit_working(self) -> None:
        if not self.spec or not self.working or not self.in_spec:
            return
        add_animation(self.spec, self.working)

    def _copy_json(self) -> None:
        if not self.working:
            return
        text = json.dumps(self.working, indent=2)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Copied FX JSON")

    def _export_preview(self) -> None:
        if not self.working:
            messagebox.showinfo("Export", "Load an FX first.")
            return
        from s2_fx_preview import preview_root, write_preview_pack

        dest = preview_root(self.spec_path) / slug_name(str(self.working.get("id") or "fx")).lower()
        pack = write_preview_pack(
            self.working,
            dest,
            theme=self.theme_var.get(),
            plan={"preset": self.preset_var.get(), "look": (PRESETS.get(self.preset_var.get()) or {}).get("look")},
            compare=True,
            name=str(self.working.get("name") or ""),
        )
        self.status.set(f"Preview {pack['files'].get('strip')}")
        messagebox.showinfo("Preview written", "\n".join(f"{k}: {v}" for k, v in pack["files"].items()))

    def _sync_fields(self) -> None:
        if not self.working:
            return
        self._ignore = True
        self.fields["id"].set(str(self.working.get("id") or ""))
        self.fields["name"].set(str(self.working.get("name") or ""))
        self.fields["animation"].set(str(self.working.get("animation") or ""))
        sound = self.working.get("sound") or {}
        self.fields["sound"].set(str(sound.get("id") or "") if isinstance(sound, dict) else "")
        self.chain.set(bool(self.working.get("chain_particles")))
        self.roof.set(bool(self.working.get("ignore_roof")))
        self.blocking.set(bool(self.working.get("blocking")))
        span = max(80.0, playback_span(self._preview_source() or self.working))
        self.time_scale.configure(to=span)
        self._fill_parts()
        self._sync_part_fields()
        self._ignore = False

    def _from_fields(self) -> None:
        if self._ignore or not self.working:
            return
        self.working["id"] = self.fields["id"].get().strip() or self.working.get("id")
        self.working["name"] = self.fields["name"].get().strip() or self.working.get("name")
        inner = self.fields["animation"].get().strip()
        if inner:
            self.working["animation"] = inner
        else:
            self.working.pop("animation", None)
        sound = dict(self.working.get("sound") or {"volume": 100})
        sound["id"] = self.fields["sound"].get().strip()
        self.working["sound"] = sound
        self.working["chain_particles"] = bool(self.chain.get())
        self.working["ignore_roof"] = bool(self.roof.get())
        self.working["blocking"] = bool(self.blocking.get())
        self.dirty = True

    def _fill_parts(self) -> None:
        for iid in self.part_tv.get_children():
            self.part_tv.delete(iid)
        if not self.working:
            return
        for i, part in enumerate(self.working.get("particles") or []):
            if not isinstance(part, dict):
                continue
            self.part_tv.insert(
                "",
                tk.END,
                iid=str(i),
                text=str(i),
                values=(part.get("tile_id"), part.get("delay") or 0, part.get("life") or ""),
            )
        kids = self.part_tv.get_children()
        if kids:
            want = str(min(self.selected_part, len(kids) - 1))
            if self.part_tv.exists(want):
                self.part_tv.selection_set(want)

    def _pick_part(self) -> None:
        if self._ignore:
            return
        sel = self.part_tv.selection()
        if not sel:
            return
        self.selected_part = int(sel[0])
        self._sync_part_fields()
        self._draw_all()

    def _part(self) -> Optional[Dict[str, Any]]:
        if not self.working:
            return None
        parts = [p for p in (self.working.get("particles") or []) if isinstance(p, dict)]
        if not parts:
            return None
        idx = max(0, min(self.selected_part, len(parts) - 1))
        return parts[idx]

    def _sync_part_fields(self) -> None:
        part = self._part()
        self._ignore = True
        if not part:
            for var in self.part_fields.values():
                var.set("")
            self._ignore = False
            return
        self.part_fields["tile_id"].set(str(part.get("tile_id") or 0))
        self.part_fields["delay"].set(str(part.get("delay") or 0))
        self.part_fields["life"].set(str(part.get("life") or ""))
        self.part_fields["flags"].set(str(part.get("flags") or 0))
        self.part_fields["velocity"].set("" if part.get("velocity") is None else str(part.get("velocity")))
        self.part_fields["height"].set("" if part.get("height") is None else str(part.get("height")))
        self.part_fields["elevation"].set("" if part.get("elevation") is None else str(part.get("elevation")))
        self.part_fields["on_impact"].set(str(part.get("on_impact") or ""))
        self.part_fields["color"].set(",".join(str(x) for x in particle_rgba(part)))
        self._ignore = False

    def _from_part_fields(self) -> None:
        if self._ignore:
            return
        part = self._part()
        if not part:
            return
        try:
            part["tile_id"] = int(float(self.part_fields["tile_id"].get() or 0))
        except ValueError:
            return
        delay = self.part_fields["delay"].get().strip()
        if delay:
            part["delay"] = _num(delay)
        else:
            part.pop("delay", None)
        life = self.part_fields["life"].get().strip()
        if life:
            part["life"] = _num(life)
        flags = self.part_fields["flags"].get().strip()
        if flags:
            try:
                part["flags"] = int(float(flags))
            except ValueError:
                pass
        for key in ("velocity", "height", "elevation"):
            raw = self.part_fields[key].get().strip()
            if raw:
                part[key] = _num(raw)
            else:
                part.pop(key, None)
        impact = self.part_fields["on_impact"].get().strip()
        if impact:
            part["on_impact"] = impact
        else:
            part.pop("on_impact", None)
        color_raw = self.part_fields["color"].get().strip()
        if color_raw:
            bits = [int(x.strip()) for x in color_raw.split(",") if x.strip()]
            if len(bits) >= 3:
                set_particle_rgba(part, bits)
        self.dirty = True
        if self.working:
            span = max(80.0, playback_span(self.working))
            self.time_scale.configure(to=span)
        self._draw_preview()
        self._draw_timeline()

    def _assign_glyph(self) -> None:
        part = self._part()
        if not part:
            return
        try:
            part["tile_id"] = int(float(self.part_fields["tile_id"].get() or 0))
        except ValueError:
            return
        self.dirty = True
        self._fill_parts()
        self._draw_all()

    def _page(self, delta: int) -> None:
        pages = max(1, (self.atlas.count + _PAGE - 1) // _PAGE)
        self.atlas_page = max(0, min(pages - 1, self.atlas_page + delta))
        self._draw_atlas()

    def _click_atlas(self, event: tk.Event) -> None:
        cell = 16 * _SCALE // 5 + 4
        cols = max(1, int(self.atlas_canvas.winfo_width() or 640) // cell)
        col = event.x // cell
        row = event.y // cell
        idx = self.atlas_page * _PAGE + row * cols + col
        if idx < 0 or idx >= self.atlas.count:
            return
        self.part_fields["tile_id"].set(str(idx))
        part = self._part()
        if part:
            part["tile_id"] = idx
            self.dirty = True
            self._fill_parts()
            self._draw_all()

    def _click_timeline(self, event: tk.Event) -> None:
        if not self.working:
            return
        parts = [p for p in (self.working.get("particles") or []) if isinstance(p, dict)]
        if not parts:
            return
        w = max(1, self.timeline.winfo_width())
        idx = int(event.x / w * len(parts))
        self.selected_part = max(0, min(len(parts) - 1, idx))
        self._fill_parts()
        self._sync_part_fields()
        self._draw_all()

    def _preview_source(self) -> Optional[Dict[str, Any]]:
        if not self.working:
            return None
        parts = self.working.get("particles") or []
        inner = self.working.get("animation")
        if parts or not inner:
            return self.working
        try:
            child = load_animation(str(inner))
        except FileNotFoundError:
            return self.working
        return child

    def _toggle_play(self) -> None:
        self.playing = not self.playing
        if self.playing:
            self._tick()
        elif self.play_job:
            self.after_cancel(self.play_job)
            self.play_job = None

    def _reset_play(self) -> None:
        self.playing = False
        if self.play_job:
            self.after_cancel(self.play_job)
            self.play_job = None
        self.play_t = 0.0
        self.time_var.set(0)
        self._draw_all()

    def _scrub(self, _raw: str = "") -> None:
        if self._ignore:
            return
        self.play_t = float(self.time_var.get() or 0)
        self._draw_preview()
        self.time_label.config(text=str(int(self.play_t)))

    def _tick(self) -> None:
        if not self.playing or not self.working:
            return
        span = max(80.0, playback_span(self._preview_source() or self.working))
        self.play_t = (self.play_t + 30) % span
        self._ignore = True
        self.time_var.set(self.play_t)
        self._ignore = False
        self._draw_preview()
        self.time_label.config(text=str(int(self.play_t)))
        self.play_job = self.after(30, self._tick)

    def _draw_all(self) -> None:
        if self._drawing:
            return
        self._drawing = True
        try:
            self._photos = []
            self._draw_preview()
            self._draw_timeline()
            self._draw_atlas()
        finally:
            self._drawing = False

    def _draw_preview(self) -> None:
        if not hasattr(self, "preview"):
            return
        self.preview.delete("all")
        anim = self._preview_source()
        if not anim:
            self.preview.create_text(20, 20, anchor=tk.NW, fill=_MUTED, text="No FX loaded")
            return
        w = max(40, self.preview.winfo_width() or 640)
        h = max(40, self.preview.winfo_height() or 260)
        t = self.play_t
        alive = []
        for i, part in enumerate(anim.get("particles") or []):
            if not isinstance(part, dict):
                continue
            delay = float(part.get("delay") or 0)
            life = float(part.get("life") or 80)
            if delay <= t < delay + max(life, 1):
                alive.append((i, part))
        if not alive:
            parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
            if parts:
                idx = min(self.selected_part, len(parts) - 1)
                alive = [(idx, parts[idx])]
        n = max(1, len(alive))
        gap = min(w / n, PARTICLE_TILE * _SCALE + 16)
        start = (w - gap * n) / 2 + gap / 2
        for slot, (i, part) in enumerate(alive):
            tid = int(part.get("tile_id") or 0)
            img = self.atlas.tinted(tid, particle_rgba(part), scale=_SCALE)
            photo = pil_to_photo(img, tk)
            self._photos.append(photo)
            x = start + slot * gap
            y = h / 2
            self.preview.create_image(x, y, image=photo)
            if i == self.selected_part:
                half = PARTICLE_TILE * _SCALE / 2 + 4
                self.preview.create_rectangle(x - half, y - half, x + half, y + half, outline=_ACCENT)
            label = f"{tid}"
            if part.get("on_impact"):
                label += f" → {part['on_impact']}"
            self.preview.create_text(x, y + PARTICLE_TILE * _SCALE / 2 + 12, fill=_MUTED, text=label)
        name = self.working.get("name") or self.working.get("id")
        extra = "  chain" if self.working.get("chain_particles") else ""
        if anim is not self.working:
            extra += f"  inner {anim.get('id')}"
        self.preview.create_text(12, 12, anchor=tk.NW, fill=_ACCENT, text=f"{name}{extra}")

    def _draw_timeline(self) -> None:
        self.timeline.delete("all")
        anim = self._preview_source()
        if not anim:
            return
        parts = [p for p in (anim.get("particles") or []) if isinstance(p, dict)]
        if not parts:
            return
        w = max(40, self.timeline.winfo_width() or 640)
        cell = max(28, w / len(parts))
        for i, part in enumerate(parts):
            x = i * cell + 4
            tid = int(part.get("tile_id") or 0)
            img = self.atlas.tinted(tid, particle_rgba(part), scale=2)
            photo = pil_to_photo(img, tk)
            self._photos.append(photo)
            self.timeline.create_image(x + 16, 28, image=photo)
            if i == self.selected_part:
                self.timeline.create_rectangle(x, 4, x + 36, 52, outline=_ACCENT)
            self.timeline.create_text(x + 16, 64, fill=_MUTED, text=str(tid), font=("Segoe UI", 8))

    def _draw_atlas(self) -> None:
        self.atlas_canvas.delete("all")
        w = max(40, self.atlas_canvas.winfo_width() or 640)
        cell = 16 * 2 + 4
        cols = max(8, w // cell)
        start = self.atlas_page * _PAGE
        pages = max(1, (self.atlas.count + _PAGE - 1) // _PAGE)
        self.page_label.config(text=f"{self.atlas_page + 1}/{pages}")
        current = None
        part = self._part()
        if part:
            try:
                current = int(part.get("tile_id") or 0)
            except (TypeError, ValueError):
                current = None
        for n in range(_PAGE):
            tid = start + n
            if tid >= self.atlas.count:
                break
            col = n % cols
            row = n // cols
            x = col * cell + 18
            y = row * cell + 18
            img = self.atlas.tinted(tid, [255, 255, 255, 255], scale=2)
            photo = pil_to_photo(img, tk)
            self._photos.append(photo)
            self.atlas_canvas.create_image(x, y, image=photo)
            if current == tid:
                self.atlas_canvas.create_rectangle(x - 18, y - 18, x + 18, y + 18, outline=_ACCENT)


def run_gui(*, spec_id: Optional[str] = None, spec_path: Optional[str] = None) -> int:
    _dpi()
    path = Path(spec_path) if spec_path else None
    if spec_id and not path:
        path = output_root() / spec_id / "skill.json"
    app = ParticleProducer(path if path and path.is_file() else None)
    app.mainloop()
    return 0


if __name__ == "__main__":
    spec = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(run_gui(spec_id=spec))
