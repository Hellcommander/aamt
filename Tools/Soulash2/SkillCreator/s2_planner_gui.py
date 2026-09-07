#!/usr/bin/env python3
"""Native desktop GUI for the Soulash 2 skill path planner."""

from __future__ import annotations

import json
import queue
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"Tkinter is required for the planner GUI: {exc}") from exc

from s2_planner import (
    FLOOR,
    STAGES,
    STARTING_BONUS,
    STARTING_COUNT,
    crop_skill_tile,
    empty_stage_plans,
    evaluate_stages,
    list_available_mods,
    load_overlay,
    normalize_stage_plans,
    plans_dir,
    save_plan,
    set_stage_allocation,
    skill_tooltip_text,
    tree_row_tooltip_text,
)

_COLOR = re.compile(r"\[/?color(?:=[^\]]+)?\]", re.I)
_BG = "#141618"
_PANEL = "#1e2226"
_INK = "#e8e4d9"
_MUTED = "#9a9588"
_ACCENT = "#7aa8c4"
_OK = "#5a8f7b"
_OFF = "#c45a5a"
_UTIL = "#c4a35a"
_KIND_FILTERS = (
    ("All", "all"),
    ("Combat", "combat"),
    ("Weapon", "weapon"),
    ("Magic", "magic"),
    ("Use", "use"),
    ("Craft", "craft"),
    ("Starting", "starting"),
    ("Planned", "planned"),
)
_ICON_PX = 24


def _plain(text: str, limit: int = 0) -> str:
    raw = _COLOR.sub("", str(text or "")).replace("::elder_age", "elder age")
    raw = " ".join(raw.split())
    if limit and len(raw) > limit:
        return raw[: limit - 1] + "…"
    return raw


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


class HoverTip:
    """Delayed tooltip for Treeview rows and other planner widgets."""

    def __init__(self, widget: tk.Widget, lookup, *, delay_ms: int = 400, wrap: int = 380) -> None:
        self.widget = widget
        self.lookup = lookup
        self.delay_ms = delay_ms
        self.wrap = wrap
        self._after: Optional[str] = None
        self._win: Optional[tk.Toplevel] = None
        self._text = ""
        widget.bind("<Motion>", self._motion, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<MouseWheel>", self._hide, add="+")

    def _motion(self, event: tk.Event) -> None:
        text = ""
        try:
            text = (self.lookup(event) or "").strip()
        except Exception:
            text = ""
        if text == self._text:
            return
        self._cancel()
        self._close()
        self._text = text
        if not text:
            return
        self._after = self.widget.after(self.delay_ms, lambda e=event: self._show(e, text))

    def _show(self, event: tk.Event, text: str) -> None:
        self._after = None
        if not self.widget.winfo_exists() or self._text != text:
            return
        self._close()
        win = tk.Toplevel(self.widget)
        win.wm_overrideredirect(True)
        try:
            win.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        win.configure(bg="#3a424a")
        label = tk.Label(
            win,
            text=text,
            justify=tk.LEFT,
            wraplength=self.wrap,
            background="#2a3036",
            foreground=_INK,
            font=("Segoe UI", 9),
            padx=8,
            pady=6,
            borderwidth=0,
        )
        label.pack(padx=1, pady=1)
        x = event.x_root + 16
        y = event.y_root + 18
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        if x + w > sw - 8:
            x = max(8, event.x_root - w - 12)
        if y + h > sh - 8:
            y = max(8, event.y_root - h - 12)
        win.geometry(f"+{x}+{y}")
        self._win = win

    def _cancel(self) -> None:
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def _close(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None

    def _hide(self, _event: Optional[tk.Event] = None) -> None:
        self._text = ""
        self._cancel()
        self._close()


class PlannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Soulash 2 — Skill Path Planner")
        self.geometry("1280x800")
        self.minsize(980, 620)
        self.configure(bg=_BG)

        self.all_mods: List[Dict[str, Any]] = []
        self.overlay: Optional[Dict[str, Any]] = None
        self.evald: Optional[Dict[str, Any]] = None
        self.starting: List[str] = []
        self.stage_plans: Dict[str, Dict[str, int]] = {s: {} for s in STAGES}
        self.selected = ""
        self.stage = tk.StringVar(value="elder")
        self.filter_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="all")
        self.race_var = tk.StringVar()
        self.plan_name = tk.StringVar(value="plan")
        self._busy = False
        self._mod_vars: Dict[str, tk.BooleanVar] = {}
        self._race_ids: List[str] = []
        self._ignore = False
        self._scale_dragging = False
        self._pending_race = ""
        self._jobs: queue.Queue = queue.Queue()
        self._icon_photos: Dict[Tuple[str, int], Any] = {}
        self._tree_tips: Dict[str, str] = {}
        self._skill_tips: Dict[str, str] = {}
        self._mod_tips: Dict[str, str] = {}
        self._tips: List[HoverTip] = []
        self._mod_hover: List[HoverTip] = []

        self._theme()
        self._menus()
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(40, self._poll_jobs)
        self.after(80, self._boot)

    def _poll_jobs(self) -> None:
        try:
            while True:
                fn = self._jobs.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(50, self._poll_jobs)

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
        style.configure("Panel.TLabel", background=_PANEL, foreground=_INK)
        style.configure("Accent.TLabel", background=_BG, foreground=_ACCENT)
        style.configure("Ok.TLabel", background=_BG, foreground=_OK)
        style.configure("Bad.TLabel", background=_BG, foreground=_OFF)
        style.configure("Warn.TLabel", background=_BG, foreground=_UTIL)
        style.configure("TButton", background=_PANEL, foreground=_INK, padding=5)
        style.configure("TRadiobutton", background=_BG, foreground=_INK)
        style.configure("TCheckbutton", background=_PANEL, foreground=_INK)
        style.configure("TLabelframe", background=_BG, foreground=_ACCENT)
        style.configure("TLabelframe.Label", background=_BG, foreground=_ACCENT)
        style.configure("TNotebook", background=_BG)
        style.configure("TNotebook.Tab", background=_PANEL, foreground=_MUTED, padding=(10, 4))
        style.map("TNotebook.Tab", foreground=[("selected", _ACCENT)])
        style.configure(
            "Treeview",
            background=_PANEL,
            fieldbackground=_PANEL,
            foreground=_INK,
            rowheight=28,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", background="#243038", foreground=_ACCENT)
        style.map(
            "Treeview",
            background=[("selected", "#2a4050")],
            foreground=[("selected", _ACCENT)],
        )
        try:
            style.layout(
                "Treeview.Item",
                [
                    (
                        "Treeitem.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("Treeitem.image", {"side": "left", "sticky": ""}),
                                ("Treeitem.text", {"side": "left", "sticky": ""}),
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=_PANEL, background=_PANEL, foreground=_INK)
        style.configure("Horizontal.TProgressbar", background=_OK, troughcolor="#2a3036")
        style.configure("Over.Horizontal.TProgressbar", background=_OFF, troughcolor="#2a3036")
        style.configure("TScale", background=_BG)
        style.configure("TSpinbox", fieldbackground=_PANEL, foreground=_INK)
        style.configure("TEntry", fieldbackground=_PANEL, foreground=_INK)
        style.configure("TPanedwindow", background=_BG)
        style.configure("TSeparator", background="#33383e")

    def _menus(self) -> None:
        menubar = tk.Menu(self)
        file_m = tk.Menu(menubar, tearoff=0)
        file_m.add_command(label="New plan", command=self._new_plan, accelerator="Ctrl+N")
        file_m.add_command(label="Open…", command=self._open_plan, accelerator="Ctrl+O")
        file_m.add_command(label="Save", command=self._save_plan, accelerator="Ctrl+S")
        file_m.add_command(label="Save as…", command=self._save_plan_as)
        file_m.add_separator()
        file_m.add_command(label="Copy summary", command=self._copy_summary)
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_m)

        mods_m = tk.Menu(menubar, tearoff=0)
        mods_m.add_command(label="Reload overlay", command=self._apply_mods, accelerator="F5")
        mods_m.add_command(label="Use in-game enabled list", command=self._use_enabled)
        menubar.add_cascade(label="Mods", menu=mods_m)

        help_m = tk.Menu(menubar, tearoff=0)
        help_m.add_command(label="About potential", command=self._about)
        help_m.add_command(label="About tooltips", command=self._about_tips)
        menubar.add_cascade(label="Help", menu=help_m)
        self.config(menu=menubar)

        self.bind("<Control-n>", lambda e: self._new_plan())
        self.bind("<Control-o>", lambda e: self._open_plan())
        self.bind("<Control-s>", lambda e: self._save_plan())
        self.bind("<F5>", lambda e: self._apply_mods())

    def _layout(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(toolbar, text="Race").pack(side=tk.LEFT)
        self.race_combo = ttk.Combobox(toolbar, textvariable=self.race_var, width=28, state="readonly")
        self.race_combo.pack(side=tk.LEFT, padx=6)
        self.race_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_eval())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        for label, value in (("Young", "young"), ("Middle +30", "middle"), ("Elder +60", "elder")):
            ttk.Radiobutton(
                toolbar, text=label, value=value, variable=self.stage, command=self._on_stage_change
            ).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Copy → next", command=self._copy_forward).pack(side=tk.LEFT, padx=6)

        ttk.Button(toolbar, text="Apply mods", command=self._apply_mods).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text="In-game list", command=self._use_enabled).pack(side=tk.RIGHT, padx=4)

        budget = ttk.Frame(self)
        budget.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.budget_cards: Dict[str, Dict[str, Any]] = {}
        for key, title in (("young", "Young adult"), ("middle", "Middle-aged"), ("elder", "Elder")):
            card = ttk.Frame(budget, style="Panel.TFrame")
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
            ttk.Label(card, text=title, style="Panel.TLabel").pack(anchor=tk.W, padx=8, pady=(6, 0))
            value = ttk.Label(card, text="—", style="Accent.TLabel")
            value.pack(anchor=tk.W, padx=8)
            bar = ttk.Progressbar(card, mode="determinate", maximum=100)
            bar.pack(fill=tk.X, padx=8, pady=(0, 8))
            self.budget_cards[key] = {"value": value, "bar": bar}

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        left = ttk.Frame(paned, style="Panel.TFrame", width=280)
        center = ttk.Frame(paned)
        right = ttk.Frame(paned, style="Panel.TFrame", width=340)
        paned.add(left, weight=0)
        paned.add(center, weight=1)
        paned.add(right, weight=0)

        ttk.Label(left, text="Mods", style="Accent.TLabel").pack(anchor=tk.W, padx=8, pady=(8, 2))
        ttk.Label(
            left,
            text="Checked mods overlay core_2 the same way the game loads them.",
            style="Muted.TLabel",
            wraplength=250,
        ).pack(anchor=tk.W, padx=8, pady=(0, 4))
        mod_wrap = ttk.Frame(left, style="Panel.TFrame")
        mod_wrap.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.mod_canvas = tk.Canvas(mod_wrap, bg=_PANEL, highlightthickness=0, bd=0)
        mod_scroll = ttk.Scrollbar(mod_wrap, orient=tk.VERTICAL, command=self.mod_canvas.yview)
        self.mod_inner = ttk.Frame(self.mod_canvas, style="Panel.TFrame")
        self.mod_inner.bind(
            "<Configure>",
            lambda e: self.mod_canvas.configure(scrollregion=self.mod_canvas.bbox("all")),
        )
        self.mod_canvas.create_window((0, 0), window=self.mod_inner, anchor=tk.NW)
        self.mod_canvas.configure(yscrollcommand=mod_scroll.set)
        self.mod_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mod_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mod_canvas.bind(
            "<MouseWheel>",
            lambda e: self.mod_canvas.yview_scroll(int(-e.delta / 120), "units"),
        )

        ttk.Label(left, text="Race at this stage", style="Accent.TLabel").pack(anchor=tk.W, padx=8, pady=(8, 2))
        self.age_hint = ttk.Label(left, text="", style="Muted.TLabel", wraplength=250)
        self.age_hint.pack(anchor=tk.W, padx=8)
        self.stats_box = tk.Text(
            left, height=8, wrap=tk.WORD, bg=_PANEL, fg=_INK, bd=0, highlightthickness=0, font=("Segoe UI", 9)
        )
        self.stats_box.pack(fill=tk.X, padx=8, pady=(4, 8))
        self.stats_box.configure(state=tk.DISABLED)

        head = ttk.Frame(center)
        head.pack(fill=tk.X)
        ttk.Label(head, text="Skills", style="Accent.TLabel").pack(side=tk.LEFT)
        self.start_hint = ttk.Label(head, text="Pick 3 starting skills (they begin at 20).", style="Muted.TLabel")
        self.start_hint.pack(side=tk.LEFT, padx=8)
        self.filter_count = ttk.Label(head, text="", style="Muted.TLabel")
        self.filter_count.pack(side=tk.RIGHT)

        filters = ttk.Frame(center)
        filters.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(filters, text="Show", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        for label, value in _KIND_FILTERS:
            ttk.Radiobutton(
                filters,
                text=label,
                value=value,
                variable=self.kind_var,
                command=self._fill_skills,
            ).pack(side=tk.LEFT, padx=2)
        ttk.Entry(filters, textvariable=self.filter_var, width=22).pack(side=tk.RIGHT)
        self.filter_var.trace_add("write", lambda *_: self._fill_skills())

        strip = ttk.Frame(center)
        strip.pack(fill=tk.X, pady=(4, 2))
        ttk.Label(strip, text="Allocate potential").pack(side=tk.LEFT)
        self.plan_spin = ttk.Spinbox(strip, from_=10, to=50, width=5, command=self._spin_changed)
        self.plan_spin.pack(side=tk.LEFT, padx=6)
        self.plan_spin.bind("<Return>", lambda e: self._spin_changed())
        self.plan_spin.bind("<FocusOut>", lambda e: self._spin_changed())
        self.plan_scale = ttk.Scale(strip, from_=10, to=50, orient=tk.HORIZONTAL, command=self._scale_changed)
        self.plan_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(strip, text="−5", width=3, command=lambda: self._nudge(-5)).pack(side=tk.LEFT, padx=2)
        ttk.Button(strip, text="+5", width=3, command=lambda: self._nudge(5)).pack(side=tk.LEFT, padx=2)
        ttk.Button(strip, text="Toggle start", command=self._toggle_selected_start).pack(side=tk.RIGHT)
        ttk.Label(
            center,
            text="Each age stage has its own plan (young ≤ middle ≤ elder). Switch stage to edit that plan. Copy → next seeds the next stage from this one.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 2))

        list_wrap = ttk.Frame(center)
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=4)
        cols = ("start", "kind", "planned", "max", "pool", "unlocks")
        self.skill_tv = ttk.Treeview(list_wrap, columns=cols, show="tree headings", selectmode="browse", takefocus=True)
        self.skill_tv.heading("#0", text="Skill")
        self.skill_tv.heading("start", text="Start")
        self.skill_tv.heading("kind", text="Kind")
        self.skill_tv.heading("planned", text="Plan")
        self.skill_tv.heading("max", text="Max")
        self.skill_tv.heading("pool", text="Pool")
        self.skill_tv.heading("unlocks", text="Unlocks")
        self.skill_tv.column("#0", width=248)
        self.skill_tv.column("start", width=50, anchor=tk.CENTER)
        self.skill_tv.column("kind", width=70)
        self.skill_tv.column("planned", width=50, anchor=tk.CENTER)
        self.skill_tv.column("max", width=44, anchor=tk.CENTER)
        self.skill_tv.column("pool", width=50, anchor=tk.CENTER)
        self.skill_tv.column("unlocks", width=70, anchor=tk.CENTER)
        skill_scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.skill_tv.yview)
        self.skill_tv.configure(yscrollcommand=skill_scroll.set)
        self.skill_tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        skill_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.skill_tv.bind("<<TreeviewSelect>>", self._on_skill_select)
        self.skill_tv.bind("<Button-1>", self._on_skill_click)
        self.skill_tv.bind("<Left>", lambda e: self._nudge(-1) or "break")
        self.skill_tv.bind("<Right>", lambda e: self._nudge(1) or "break")
        self.skill_tv.bind("<Shift-Left>", lambda e: self._nudge(-5) or "break")
        self.skill_tv.bind("<Shift-Right>", lambda e: self._nudge(5) or "break")
        self.skill_tv.tag_configure("weapon", foreground="#d8b07a")
        self.skill_tv.tag_configure("magic", foreground=_ACCENT)
        self.skill_tv.tag_configure("use", foreground=_OK)
        self.skill_tv.tag_configure("craft", foreground=_INK)
        self.plan_scale.bind("<ButtonPress-1>", lambda e: setattr(self, "_scale_dragging", True))
        self.plan_scale.bind("<ButtonRelease-1>", self._scale_released)

        ttk.Label(right, text="Skill tree", style="Accent.TLabel").pack(anchor=tk.W, padx=8, pady=(8, 2))
        self.preview_title = ttk.Label(right, text="Select a skill", style="Muted.TLabel")
        self.preview_title.pack(anchor=tk.W, padx=8)
        ttk.Label(
            right,
            text="Hover a skill or unlock, or click a tree row, to see what it does.",
            style="Muted.TLabel",
            wraplength=310,
        ).pack(anchor=tk.W, padx=8, pady=(0, 2))
        self.tree_tv = ttk.Treeview(right, columns=("kind", "name"), show="tree headings", selectmode="browse", takefocus=True)
        self.tree_tv.heading("#0", text="Lv")
        self.tree_tv.heading("kind", text="Kind")
        self.tree_tv.heading("name", text="Unlock")
        self.tree_tv.column("#0", width=48)
        self.tree_tv.column("kind", width=80)
        self.tree_tv.column("name", width=200)
        self.tree_tv.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.tree_tv.tag_configure("lock", foreground="#666")
        self.tree_tv.tag_configure("ability", foreground="#c45a5a")
        self.tree_tv.tag_configure("amplifier", foreground=_ACCENT)
        self.tree_tv.tag_configure("passive", foreground=_OK)
        self.tree_tv.tag_configure("stat", foreground="#c9b227")
        self.tree_tv.tag_configure("recipe", foreground=_UTIL)
        self.tree_tv.tag_configure("production_action", foreground=_UTIL)
        self.tree_tv.tag_configure("action", foreground=_UTIL)
        self.tree_tv.tag_configure("control_action", foreground=_UTIL)
        self.tree_tv.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.detail_box = tk.Text(
            right,
            height=8,
            wrap=tk.WORD,
            bg=_PANEL,
            fg=_INK,
            bd=0,
            highlightthickness=0,
            font=("Segoe UI", 9),
            padx=6,
            pady=4,
        )
        self.detail_box.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.detail_box.configure(state=tk.DISABLED)
        self._bind_hover_tips()

        status = ttk.Frame(self)
        status.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.status = ttk.Label(status, text="Loading…", style="Muted.TLabel")
        self.status.pack(side=tk.LEFT)
        ttk.Label(status, textvariable=self.plan_name, style="Muted.TLabel").pack(side=tk.RIGHT)

    def _bind_hover_tips(self) -> None:
        self._tips = [
            HoverTip(self.skill_tv, self._skill_hover_text),
            HoverTip(self.tree_tv, self._tree_hover_text),
            HoverTip(self.preview_title, lambda e: self._skill_tips.get(self.selected, ""), wrap=420),
            HoverTip(self.race_combo, self._race_hover_text, wrap=420),
            HoverTip(self.stats_box, self._race_hover_text, wrap=420),
        ]
        for key, card in self.budget_cards.items():
            self._tips.append(HoverTip(card["value"].master, lambda e, k=key: self._budget_hover_text(k), delay_ms=250, wrap=320))

    def _skill_hover_text(self, event: tk.Event) -> str:
        if self.skill_tv.identify_region(event.x, event.y) == "heading":
            return ""
        row = self.skill_tv.identify_row(event.y)
        if not row:
            return ""
        hit = self._skill_tips.get(row)
        if hit:
            return hit
        skill = next((s for s in (self.overlay or {}).get("skills") or [] if s["id"] == row), None)
        return str((skill or {}).get("tooltip") or skill_tooltip_text(skill or {"id": row}))

    def _tree_hover_text(self, event: tk.Event) -> str:
        if self.tree_tv.identify_region(event.x, event.y) == "heading":
            return ""
        row = self.tree_tv.identify_row(event.y)
        return self._tree_tips.get(row or "", "")

    def _race_hover_text(self, _event: Optional[tk.Event] = None) -> str:
        if not self.evald:
            return ""
        race = self.evald.get("race") or {}
        name = str(race.get("name") or "")
        desc = _plain(race.get("tooltip") or race.get("description") or "")
        if not desc:
            return name
        return f"{name}\n{desc}" if name else desc

    def _budget_hover_text(self, stage: str) -> str:
        if stage == "young":
            return (
                "Young adult is character creation. Each skill starts at 10 for free. "
                "The 3 starting skills begin at 20 (30 from the shared pool). "
                "This budget is character.json max_potential with no age bonus."
            )
        if stage == "middle":
            return (
                "Middle-aged adds +30 max potential. Race ages.adult is the year this stage hits. "
                "A skill's planned level here cannot be lower than young."
            )
        return (
            "Elder adds another +30 (60 over a lifetime). Race ages.elder is the year this stage hits. "
            "Vampires and similar races with huge adult/elder ages never see these bonuses."
        )

    def _set_detail(self, text: str) -> None:
        self.detail_box.configure(state=tk.NORMAL)
        self.detail_box.delete("1.0", tk.END)
        self.detail_box.insert("1.0", text.strip() or "Select a skill or tree unlock.")
        self.detail_box.configure(state=tk.DISABLED)

    def _on_tree_select(self, _event: Optional[tk.Event] = None) -> None:
        sel = self.tree_tv.selection()
        if not sel:
            return
        text = self._tree_tips.get(sel[0], "")
        if text:
            self._set_detail(text)

    def _boot(self) -> None:
        try:
            self.all_mods = list_available_mods()
        except Exception as exc:
            messagebox.showerror("Planner", f"Could not list mods:\n{exc}")
            return
        enabled = [m["id"] for m in self.all_mods if m.get("enabled")] or ["core_2"]
        self._fill_mods(enabled)
        self._load_overlay(enabled)

    def _fill_mods(self, checked: List[str]) -> None:
        for child in self.mod_inner.winfo_children():
            child.destroy()
        self._mod_vars = {}
        self._mod_hover: List[HoverTip] = []
        want = set(checked)
        for mod in self.all_mods:
            always = mod["id"] == "core_2"
            var = tk.BooleanVar(value=always or mod["id"] in want)
            self._mod_vars[mod["id"]] = var
            bits = [mod.get("origin") or ""]
            if mod.get("has_skills"):
                bits.append("skills")
            if mod.get("has_character"):
                bits.append("character")
            text = f"{mod.get('name') or mod['id']}  [{mod['id']}]"
            cb = ttk.Checkbutton(
                self.mod_inner,
                text=text,
                variable=var,
                style="TCheckbutton",
                state="disabled" if always else "normal",
            )
            cb.pack(anchor=tk.W, padx=4, pady=1)
            tip = _plain(mod.get("description") or "", 0)
            if not tip:
                tip = f"{mod.get('name') or mod['id']} ({mod.get('origin') or 'mod'})"
            else:
                tip = f"{mod.get('name') or mod['id']}\n{tip}"
            meta = ttk.Label(self.mod_inner, text=" · ".join(b for b in bits if b), style="Muted.TLabel")
            meta.pack(anchor=tk.W, padx=22)
            self._mod_hover.append(HoverTip(cb, lambda e, t=tip: t, wrap=360))
            self._mod_hover.append(HoverTip(meta, lambda e, t=tip: t, wrap=360))

    def _checked_mods(self) -> List[str]:
        ids = [mid for mid, var in self._mod_vars.items() if var.get()]
        if "core_2" not in ids:
            ids.insert(0, "core_2")
        return ids

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self._busy = busy
        self.config(cursor="watch" if busy else "")
        if text:
            self.status.config(text=text)
        self.update_idletasks()

    def _load_overlay(self, mods: List[str]) -> None:
        if self._busy:
            return
        self._set_busy(True, "Loading mods and milestones…")
        snapshot = list(mods)

        def work() -> None:
            err: Optional[BaseException] = None
            overlay = None
            try:
                overlay = load_overlay(snapshot)
            except BaseException as exc:  # noqa: BLE001 — surface any load failure in the UI
                err = exc
            self._jobs.put(lambda o=overlay, e=err: self._on_overlay(o, e))

        threading.Thread(target=work, daemon=True).start()

    def _on_overlay(self, overlay: Optional[Dict[str, Any]], err: Optional[BaseException]) -> None:
        self._set_busy(False)
        if err or overlay is None:
            messagebox.showerror("Planner", f"Failed to load overlay:\n{err}")
            self.status.config(text="Load failed")
            return
        self.overlay = overlay
        skills = overlay.get("skills") or []
        keep = {s["id"] for s in skills}
        self.starting = [s for s in self.starting if s in keep][:STARTING_COUNT]
        self.stage_plans = normalize_stage_plans(skills, self.starting, self.stage_plans)
        self._fill_races()
        self._refresh_eval()
        missing = overlay.get("missing") or []
        extra = f"  Missing: {', '.join(missing)}" if missing else ""
        self.status.config(
            text=f"Loaded {len(skills)} skills, {len(overlay.get('races') or [])} races, pool {overlay.get('max_potential')}{extra}"
        )

    def _current_stage(self) -> str:
        stage = self.stage.get()
        return stage if stage in STAGES else "elder"

    def _allocations(self) -> Dict[str, int]:
        return self.stage_plans.setdefault(self._current_stage(), {})

    def _planned_for(self, sid: str) -> int:
        return int(self._allocations().get(sid, FLOOR))

    def _on_stage_change(self) -> None:
        self._refresh_eval(rebuild_list=True)
        if self.selected:
            self._sync_selected_controls()

    def _copy_forward(self) -> None:
        stage = self.stage.get() if self.stage.get() in STAGES else "elder"
        idx = STAGES.index(stage)
        if idx >= len(STAGES) - 1:
            messagebox.showinfo("Copy forward", "Elder is the last stage — nothing to copy into.")
            return
        nxt = STAGES[idx + 1]
        if not self.overlay:
            return
        skills = self.overlay.get("skills") or []
        src = dict(self.stage_plans.get(stage) or {})
        for sid, val in src.items():
            set_stage_allocation(
                self.stage_plans,
                stage=nxt,
                skill_id=sid,
                value=int(val),
                skills=skills,
                starting=self.starting,
            )
        self.stage.set(nxt)
        self._refresh_eval(rebuild_list=True)
        self.status.config(text=f"Copied {stage} plan → {nxt}")

    def _fill_races(self) -> None:
        if not self.overlay:
            return
        races = self.overlay.get("races") or []
        playable = [r for r in races if r.get("playable")]
        rest = [r for r in races if not r.get("playable")]
        ordered = playable + rest
        self._race_ids = [r["id"] for r in ordered]
        labels = [f"{r.get('name')} ({r['id']})" + ("" if r.get("playable") else " — NPC") for r in ordered]
        self.race_combo["values"] = labels
        if self._pending_race:
            pending = self._pending_race
            self._pending_race = ""
            self._select_race(pending)
            if self.race_var.get() in labels:
                return
        current = self.race_var.get()
        if current in labels:
            return
        if playable:
            self.race_var.set(f"{playable[0].get('name')} ({playable[0]['id']})")
        elif labels:
            self.race_var.set(labels[0])

    def _race_id(self) -> str:
        label = self.race_var.get()
        try:
            idx = list(self.race_combo["values"]).index(label)
            return self._race_ids[idx]
        except (ValueError, IndexError):
            return (self._race_ids[0] if self._race_ids else "0")

    def _refresh_eval(self, *, rebuild_list: bool = True) -> None:
        if not self.overlay or self._ignore:
            return
        try:
            self.evald = evaluate_stages(
                self.overlay,
                race_id=self._race_id(),
                starting=self.starting,
                stage_plans=self.stage_plans,
                stage=self.stage.get(),
            )
            if self.evald.get("stage_plans"):
                self.stage_plans = self.evald["stage_plans"]
        except Exception as exc:
            self.status.config(text=str(exc))
            return
        self._fill_budget()
        if rebuild_list:
            self._fill_skills()
        elif self.selected:
            self._update_skill_row(self.selected)
        self._fill_preview()
        self._fill_race_panel()

    def _skill_icon(self, skill: Dict[str, Any]) -> Optional[tk.PhotoImage]:
        path = str(skill.get("icon_file") or "")
        if not path:
            return None
        try:
            index = int(skill.get("image") or 0)
        except (TypeError, ValueError):
            index = 0
        key = (path, index)
        hit = self._icon_photos.get(key)
        if hit is not None:
            return hit
        crop = crop_skill_tile(
            path,
            index,
            int(skill.get("icon_cols") or 1),
            int(skill.get("icon_rows") or 1),
        )
        if crop is None:
            return None
        try:
            from io import BytesIO
            from PIL import Image

            rgba = crop.convert("RGBA")
            if rgba.size != (_ICON_PX, _ICON_PX):
                rgba = rgba.resize((_ICON_PX, _ICON_PX), Image.Resampling.NEAREST)
            canvas = Image.new("RGB", rgba.size, (30, 34, 38))
            canvas.paste(rgba, mask=rgba.split()[3])
            buf = BytesIO()
            canvas.save(buf, format="PPM")
            photo = tk.PhotoImage(data=buf.getvalue())
        except Exception:
            return None
        self._icon_photos[key] = photo
        return photo

    def _fill_budget(self) -> None:
        if not self.evald:
            return
        active = self.stage.get()
        for key, card in self.budget_cards.items():
            row = self.evald["budgets"][key]
            rem = row["remaining"]
            spent = int(row.get("spent", self.evald["spent"]))
            avail = max(int(row["available"]), 1)
            pct = min(100, int(100 * spent / avail))
            label_style = "Accent.TLabel" if key == active else "Panel.TLabel"
            card["value"].master.winfo_children()[0].configure(style=label_style)  # title
            if rem < 0:
                card["value"].configure(text=f"{abs(rem)} over  ({spent}/{row['available']})", style="Bad.TLabel")
                card["bar"].configure(style="Over.Horizontal.TProgressbar", value=100)
            else:
                style = "Warn.TLabel" if rem <= 30 else "Ok.TLabel"
                card["value"].configure(text=f"{rem} left  ({spent}/{row['available']})", style=style)
                card["bar"].configure(style="Horizontal.TProgressbar", value=pct)
        ev = self.evald
        self.status.config(
            text=(
                f"{ev['race']['name']} · editing {ev['stage']} · pool {ev['pool']}+{ev['age_bonus']} "
                f"· spent {ev['spent']} · gold ~{ev['gold']} · {ev['full_skills_left']} more 40-pt skills"
            )
        )
        self.start_hint.config(text=f"Starting skills {len(self.starting)}/{STARTING_COUNT} (they begin at 20).")

    def _fill_race_panel(self) -> None:
        if not self.evald:
            return
        age = self.evald["age"]
        race = self.evald["race"]
        if age["practical_aging"]:
            hint = (
                f"Starts ~{age['start']}. Middle-aged at {age['middle_at']} (+{age['middle']['bonus']}). "
                f"Elder at {age['elder_at']} (+{age['elder']['bonus']} more)."
            )
        else:
            hint = (
                f"{race['name']} adult/elder ages are {age['middle_at']}/{age['elder_at']} — "
                "age bonuses will not arrive in a normal lifetime."
            )
        self.age_hint.config(text=hint)
        stats = self.evald.get("stats_at_stage") or {}
        lines = [_plain(race.get("description") or "", 420)]
        if stats:
            lines.append("")
            lines.append("  ".join(f"{k} {v}" for k, v in stats.items()))
        self.stats_box.configure(state=tk.NORMAL)
        self.stats_box.delete("1.0", tk.END)
        self.stats_box.insert("1.0", "\n".join(lines))
        self.stats_box.configure(state=tk.DISABLED)

    def _skill_kind(self, skill: Dict[str, Any]) -> str:
        return str(skill.get("kind") or "use")

    def _visible_skills(self) -> List[Dict[str, Any]]:
        if not self.overlay:
            return []
        q = (self.filter_var.get() or "").strip().lower()
        filt = (self.kind_var.get() or "all").strip().lower()
        eval_by = {r["id"]: r for r in (self.evald or {}).get("skills") or []}
        rows = []
        for skill in self.overlay.get("skills") or []:
            kind = self._skill_kind(skill)
            sid = skill["id"]
            if filt == "combat" and kind not in ("weapon", "magic"):
                continue
            if filt in ("weapon", "magic", "craft", "use") and kind != filt:
                continue
            if filt == "starting" and sid not in self.starting:
                continue
            if filt == "planned":
                row = eval_by.get(sid) or {}
                planned = int(row.get("from_pool") or max(0, int(self._planned_for(sid)) - FLOOR))
                if planned <= 0:
                    continue
            hay = f"{skill.get('name')} {sid}".lower()
            if q and q not in hay:
                continue
            rows.append(skill)
        return rows

    def _fill_skills(self) -> None:
        if self._ignore:
            return
        selected = self.selected
        for iid in self.skill_tv.get_children():
            self.skill_tv.delete(iid)
        self._skill_tips = {}
        eval_by = {r["id"]: r for r in (self.evald or {}).get("skills") or []}
        for skill in self._visible_skills():
            sid = skill["id"]
            row = eval_by.get(sid) or {}
            planned = int(row["planned"]) if "planned" in row else self._planned_for(sid)
            kind = self._skill_kind(skill)
            row_kw: Dict[str, Any] = {
                "iid": sid,
                "text": str(skill.get("name") or sid),
                "values": (
                    "Yes" if sid in self.starting else "",
                    kind,
                    planned,
                    skill.get("max_level"),
                    row.get("from_pool", max(0, planned - FLOOR)),
                    f"{row.get('unlocked', 0)}/{len(skill.get('tree') or [])}",
                ),
                "tags": (kind,),
            }
            icon = self._skill_icon(skill)
            if icon is not None:
                row_kw["image"] = icon
            self.skill_tv.insert("", tk.END, **row_kw)
            self._skill_tips[sid] = str(skill.get("tooltip") or skill_tooltip_text(skill))
        shown = len(self.skill_tv.get_children())
        total = len((self.overlay or {}).get("skills") or [])
        filt = self.kind_var.get() or "all"
        extra = f" · {filt}" if filt != "all" else ""
        self.filter_count.config(text=f"{shown}/{total}{extra}")
        if selected and self.skill_tv.exists(selected):
            self.skill_tv.selection_set(selected)
            self.skill_tv.focus(selected)
            self.skill_tv.see(selected)
        elif not self.skill_tv.selection():
            kids = self.skill_tv.get_children()
            if kids:
                self.skill_tv.selection_set(kids[0])
                self.skill_tv.focus(kids[0])
                self.selected = kids[0]
                self._sync_selected_controls()

    def _update_skill_row(self, sid: str) -> None:
        if not sid or not self.skill_tv.exists(sid) or not self.evald:
            return
        row = next((r for r in self.evald.get("skills") or [] if r["id"] == sid), None)
        skill = next((s for s in (self.overlay or {}).get("skills") or [] if s["id"] == sid), None)
        if not row or not skill:
            return
        self.skill_tv.item(
            sid,
            values=(
                "Yes" if sid in self.starting else "",
                self._skill_kind(skill),
                row.get("planned"),
                skill.get("max_level"),
                row.get("from_pool"),
                f"{row.get('unlocked', 0)}/{len(skill.get('tree') or [])}",
            ),
        )

    def _on_skill_click(self, event: tk.Event) -> Optional[str]:
        region = self.skill_tv.identify_region(event.x, event.y)
        col = self.skill_tv.identify_column(event.x)
        row = self.skill_tv.identify_row(event.y)
        if not row:
            return None
        self.skill_tv.selection_set(row)
        self.skill_tv.focus(row)
        self.skill_tv.focus_set()
        if self.selected != row:
            self.selected = row
            self._sync_selected_controls()
            self._fill_preview()
        if region == "cell" and col == "#1":
            self._toggle_start(row)
        return "break"

    def _on_skill_select(self, _event: Optional[tk.Event] = None) -> None:
        sel = self.skill_tv.selection()
        if not sel:
            return
        self.selected = sel[0]
        self._sync_selected_controls()
        self._fill_preview()

    def _sync_selected_controls(self, *, touch_scale: bool = True) -> None:
        sid = self.selected
        if not sid or not self.overlay:
            return
        skill = next((s for s in self.overlay["skills"] if s["id"] == sid), None)
        if not skill:
            return
        cap = int(skill.get("max_level") or 50)
        planned = self._planned_for(sid)
        self._ignore = True
        self.plan_spin.configure(from_=FLOOR, to=cap)
        self.plan_spin.set(planned)
        # Reconfiguring the scale mid-drag resets ttk.Scale on Windows and kills the thumb.
        if not self._scale_dragging:
            self.plan_scale.configure(from_=FLOOR, to=cap)
            if touch_scale:
                self.plan_scale.set(planned)
        self._ignore = False

    def _scale_changed(self, raw: str) -> None:
        if self._ignore or not self.selected:
            return
        self._scale_dragging = True
        self._set_planned(self.selected, int(float(raw)), source="scale")

    def _scale_released(self, _event: Optional[tk.Event] = None) -> None:
        self._scale_dragging = False
        if self.selected:
            self._sync_selected_controls(touch_scale=True)

    def _spin_changed(self) -> None:
        if self._ignore or not self.selected:
            return
        try:
            value = int(self.plan_spin.get())
        except ValueError:
            return
        self._set_planned(self.selected, value, source="spin")

    def _nudge(self, delta: int) -> None:
        if not self.selected:
            return
        self._set_planned(self.selected, self._planned_for(self.selected) + int(delta), source="nudge")

    def _set_planned(self, sid: str, value: int, *, source: str = "") -> None:
        skills = (self.overlay or {}).get("skills") or []
        if not any(s["id"] == sid for s in skills):
            return
        before = self._planned_for(sid)
        set_stage_allocation(
            self.stage_plans,
            stage=self._current_stage(),
            skill_id=sid,
            value=int(value),
            skills=skills,
            starting=self.starting,
        )
        planned = self._planned_for(sid)
        if planned == before:
            if source == "scale":
                self._ignore = True
                self.plan_spin.set(planned)
                self._ignore = False
            return
        self._refresh_eval(rebuild_list=False)
        # Never reset the scale while the user is dragging it — that made allocation feel broken.
        self._sync_selected_controls(touch_scale=source != "scale")

    def _toggle_selected_start(self) -> None:
        if self.selected:
            self._toggle_start(self.selected)

    def _toggle_start(self, sid: str) -> None:
        if sid in self.starting:
            self.starting = [s for s in self.starting if s != sid]
        else:
            if len(self.starting) >= STARTING_COUNT:
                messagebox.showinfo("Starting skills", f"Character creation only picks {STARTING_COUNT} skills.")
                return
            self.starting.append(sid)
            if self.overlay:
                set_stage_allocation(
                    self.stage_plans,
                    stage=self._current_stage(),
                    skill_id=sid,
                    value=max(self._planned_for(sid), FLOOR + STARTING_BONUS),
                    skills=self.overlay.get("skills") or [],
                    starting=self.starting,
                )
        self._refresh_eval()

    def _fill_preview(self) -> None:
        for iid in self.tree_tv.get_children():
            self.tree_tv.delete(iid)
        self._tree_tips = {}
        if not self.overlay or not self.selected:
            self.preview_title.config(text="Select a skill")
            self._set_detail("Select a skill to preview its tree and what each unlock does.")
            return
        skill = next((s for s in self.overlay["skills"] if s["id"] == self.selected), None)
        if not skill:
            return
        planned = self._planned_for(skill["id"])
        self.preview_title.config(text=f"{skill.get('name')}  @ {planned}")
        self._set_detail(str(skill.get("tooltip") or skill_tooltip_text(skill)))
        for i, row in enumerate(skill.get("tree") or []):
            level = row.get("level")
            open_ = level == "innate" or (isinstance(level, int) and level <= planned)
            lv = "inn" if level == "innate" else str(level)
            kind = str(row.get("kind") or "stat")
            name = str(row.get("name") or "")
            if row.get("reward"):
                name = f"{name}  [{row['reward']}]"
            tags = [kind if kind else "stat"]
            if not open_:
                tags.append("lock")
            iid = f"t{i}"
            self.tree_tv.insert("", tk.END, iid=iid, text=f"L{lv}", values=(kind, name), tags=tuple(tags))
            self._tree_tips[iid] = str(row.get("tooltip") or tree_row_tooltip_text(row))

    def _plan_payload(self) -> Dict[str, Any]:
        return {
            "name": self.plan_name.get() or "plan",
            "mods": self._checked_mods(),
            "race_id": self._race_id(),
            "starting": list(self.starting),
            "allocations": dict(self._allocations()),
            "stage_plans": {s: dict(self.stage_plans.get(s) or {}) for s in STAGES},
            "stage": self.stage.get(),
        }

    def _plans_from_file(self, plan: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
        raw = plan.get("stage_plans")
        if isinstance(raw, dict):
            return {stage: dict(raw.get(stage) or {}) for stage in STAGES}
        legacy = plan.get("allocations") or {}
        if isinstance(legacy, dict) and legacy:
            seeded = {str(k): int(v) for k, v in legacy.items()}
            return {stage: dict(seeded) for stage in STAGES}
        return {stage: {} for stage in STAGES}

    def _new_plan(self) -> None:
        self.starting = []
        self.plan_name.set("plan")
        skills = (self.overlay or {}).get("skills") or []
        self.stage_plans = empty_stage_plans(skills, self.starting)
        self._refresh_eval()

    def _save_plan(self) -> None:
        name = (self.plan_name.get() or "plan").strip()
        path = save_plan(name, self._plan_payload())
        self.status.config(text=f"Saved {path}")

    def _save_plan_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save plan",
            defaultextension=".json",
            initialdir=str(plans_dir()),
            filetypes=[("Plan JSON", "*.json")],
        )
        if not path:
            return
        dest = Path(path)
        payload = self._plan_payload()
        payload["name"] = dest.stem
        self.plan_name.set(dest.stem)
        dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.status.config(text=f"Saved {dest}")

    def _open_plan(self) -> None:
        path = filedialog.askopenfilename(
            title="Open plan",
            initialdir=str(plans_dir()),
            filetypes=[("Plan JSON", "*.json")],
        )
        if not path:
            return
        try:
            plan = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Open plan", str(exc))
            return
        if not isinstance(plan, dict):
            messagebox.showerror("Open plan", "File is not a plan object")
            return
        self.plan_name.set(str(plan.get("name") or Path(path).stem))
        self.starting = list(plan.get("starting") or [])
        self.stage_plans = self._plans_from_file(plan)
        self.stage.set(str(plan.get("stage") or "elder"))
        mods = list(plan.get("mods") or self._checked_mods())
        self._fill_mods(mods)
        race_id = str(plan.get("race_id") or "")
        if race_id:
            self._pending_race = race_id
        self._load_overlay(mods)

    def _select_race(self, race_id: str) -> None:
        for i, rid in enumerate(self._race_ids):
            if rid == race_id:
                values = list(self.race_combo["values"])
                if i < len(values):
                    self.race_var.set(values[i])
                    self._refresh_eval()
                return

    def _copy_summary(self) -> None:
        if not self.evald:
            return
        ev = self.evald
        lines = [
            f"{ev['race']['name']} {ev['stage']} · pool {ev['pool']}+{ev['age_bonus']} · spent {ev['spent']} · {ev['remaining']} left · gold ~{ev['gold']}",
            "Starting: " + ", ".join(self.starting) if self.starting else "Starting: (none)",
        ]
        for row in ev.get("skills") or []:
            if int(row.get("from_pool") or 0) <= 0:
                continue
            mark = " *" if row.get("starting") else ""
            lines.append(f"{row['name']}{mark}  {row['planned']}/{row['max_level']}  pool {row['from_pool']}")
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.config(text="Copied summary")

    def _apply_mods(self) -> None:
        self._load_overlay(self._checked_mods())

    def _use_enabled(self) -> None:
        enabled = [m["id"] for m in self.all_mods if m.get("enabled")] or ["core_2"]
        self._fill_mods(enabled)
        self._load_overlay(enabled)

    def _about(self) -> None:
        messagebox.showinfo(
            "Potential",
            "Each skill starts at 10 potential (free).\n"
            "Character creation picks 3 skills at 20 (30 from the shared pool).\n"
            "character.json max_potential is the shared pool (200 vanilla, 275 with the +75 overlay).\n"
            "Middle-aged and elder each add +30 (60 over a lifetime).\n"
            "Race ages.adult / ages.elder are the years those stages hit.\n"
            "A milestone and +1 statistic may share a level.",
        )

    def _about_tips(self) -> None:
        messagebox.showinfo(
            "Tooltips",
            "Hover a skill in the list to read its description and how it is trained.\n"
            "Hover a tree unlock for the ability, amplifier, passive, recipe, or world action.\n"
            "Click a tree row to pin that text in the details box under the tree.\n"
            "Passives have no in-game description; the planner shows their effects instead.",
        )


def run_gui() -> int:
    _dpi()
    app = PlannerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_gui())
