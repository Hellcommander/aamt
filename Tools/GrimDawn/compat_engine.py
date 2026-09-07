"""Bidirectional FoA/v1.3 compatibility engine for Grim Dawn mods."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from archive_tool import ArchiveTool
from dbr_io import get_list_field, merge_records, read_dbr, write_dbr
from gd_paths import CLASS_HUB_RELATIVE, GamePaths


BERSERKER_HINTS = (
    "playerclass10",
    "class10",
    "berserker",
    "skillctrlpane10",
)

# GD uses camelCase numbered fields (skillTree1, skillCtrlPane1)
CLASS_LIST_PREFIXES = ("skillTree", "skillCtrlPane")

# Class-selection UI stores mastery buttons as semicolon lists
CLASS_SELECTION_SEMICOLON_KEYS = (
    "masteryMasteryButtons",
    "masteryMasterySelectedBitmapNames",
    "masteryMasterySelectedDescriptionTags",
    "masteryMasteryText",
)

# Skill/UI trees that define selectable class lines
CLASS_TREE_GLOBS = (
    "records/skills/playerclass*",
    "records/ui/skills/class*",
)


@dataclass
class CompatReport:
    imported: List[str] = field(default_factory=list)
    merged_hubs: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    class_lines: List[str] = field(default_factory=list)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Compat report", ""]
        lines.append(f"## Imported ({len(self.imported)})")
        lines.extend(f"- {x}" for x in self.imported[:500])
        if len(self.imported) > 500:
            lines.append(f"- ... and {len(self.imported) - 500} more")
        lines.append("")
        lines.append(f"## Merged hubs ({len(self.merged_hubs)})")
        lines.extend(f"- {x}" for x in self.merged_hubs)
        lines.append("")
        lines.append(f"## Class lines on PC hubs ({len(self.class_lines)})")
        lines.extend(f"- {x}" for x in self.class_lines)
        lines.append("")
        lines.append(f"## Conflicts ({len(self.conflicts)})")
        lines.extend(f"- {x}" for x in self.conflicts[:200])
        lines.append("")
        lines.append("## Notes")
        lines.extend(f"- {x}" for x in self.notes)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class CompatEngine:
    def __init__(
        self,
        game: GamePaths,
        mod_database: Path,
        cache_dir: Path,
        categories: Optional[List[str]] = None,
    ) -> None:
        self.game = game
        self.mod_db = Path(mod_database)
        self.cache_dir = Path(cache_dir)
        self.categories = categories or ["ui", "skills", "creatures/pc", "quests"]
        self.tool = ArchiveTool(game.game_dir)
        self.report = CompatReport()
        self._layer_roots: Dict[str, Path] = {}

    def ensure_layers_extracted(self) -> None:
        for arz in self.game.layer_arz_files():
            name = arz.stem.lower()
            dest = self.cache_dir / "layers" / name
            marker = dest / ".extracted"
            if marker.is_file():
                self._layer_roots[name] = dest
                continue
            print(f"Extracting layer {arz} ...", flush=True)
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True)
            self.tool.extract_database(arz, dest)
            marker.write_text("ok", encoding="utf-8")
            self._layer_roots[name] = dest

    def _find_in_layers(self, rel: str) -> Optional[Path]:
        order = ["gdx3", "gdx2", "gdx1", "database"]
        for key in order:
            root = self._layer_roots.get(key)
            if not root:
                continue
            candidate = root / rel
            if candidate.is_file():
                return candidate
        return None

    def _iter_layer_records(self, layer_key: str = "gdx3") -> List[Path]:
        root = self._layer_roots.get(layer_key)
        if not root:
            return []
        files = []
        for p in root.rglob("*.dbr"):
            rel = p.relative_to(root).as_posix().lower()
            if any(cat in rel for cat in self.categories) or any(
                h in rel for h in BERSERKER_HINTS
            ):
                files.append(p)
        return files

    def _copy_tree_if_missing(
        self, src: Path, dest: Path, label: str, *, overwrite: bool = False
    ) -> None:
        if not src.exists():
            return
        if src.is_file():
            existed = dest.exists()
            if not existed or overwrite:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                self.report.imported.append(
                    f"{label} (overwrite)" if existed and overwrite else label
                )
            return
        for path in src.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(src)
            target = dest / rel
            existed = target.exists()
            if existed and not overwrite:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            suffix = " (overwrite)" if existed and overwrite else ""
            self.report.imported.append(f"{label}/{rel.as_posix()}{suffix}")

    def import_class_trees_from_root(
        self, root: Path, label: str, *, overwrite: bool = False
    ) -> int:
        """Copy playerclass* / ui/skills/class* trees from a database root (mod or DLC)."""
        before = len(self.report.imported)
        skills = root / "records" / "skills"
        if skills.is_dir():
            for child in skills.iterdir():
                if child.is_dir() and child.name.lower().startswith("playerclass"):
                    self._copy_tree_if_missing(
                        child,
                        self.mod_db / "records" / "skills" / child.name,
                        f"{label}:{child.name}",
                        overwrite=overwrite,
                    )
        ui_skills = root / "records" / "ui" / "skills"
        if ui_skills.is_dir():
            for child in ui_skills.iterdir():
                name = child.name.lower()
                if child.is_dir() and (
                    name.startswith("class")
                    or name in ("classcommon", "classselection", "devotion", "skillselectwheel")
                ):
                    self._copy_tree_if_missing(
                        child,
                        self.mod_db / "records" / "ui" / "skills" / child.name,
                        f"{label}:ui/{child.name}",
                        overwrite=overwrite,
                    )
            for dbr in ui_skills.glob("*.dbr"):
                dest = self.mod_db / "records" / "ui" / "skills" / dbr.name
                existed = dest.exists()
                if not existed or overwrite:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dbr, dest)
                    self.report.imported.append(
                        f"{label}:ui/{dbr.name}"
                        + (" (overwrite)" if existed and overwrite else "")
                    )
        return len(self.report.imported) - before

    def merge_class_hubs(self, *, vanilla_first_lists: bool = False) -> None:
        """
        Merge class hubs so stock/DLC panes exist AND mod class lines are kept.

        Default: mod skillTree / skillCtrlPane entries first, then append missing DLC.
        vanilla_first_lists=True: DLC first then mod extras (rarely needed).
        """
        for rel in CLASS_HUB_RELATIVE:
            vanilla = self._find_in_layers(rel)
            mod_path = self.mod_db / rel
            if vanilla is None:
                self.report.notes.append(f"Hub missing in vanilla layers: {rel}")
                continue
            if not mod_path.exists():
                mod_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(vanilla, mod_path)
                self.report.imported.append(rel)
                self.report.merged_hubs.append(f"{rel} (copied full DLC hub)")
                continue
            try:
                mod_data = read_dbr(mod_path)
                van_data = read_dbr(vanilla)
                semi = (
                    CLASS_SELECTION_SEMICOLON_KEYS
                    if "classselection" in rel.lower()
                    else None
                )
                if vanilla_first_lists:
                    # DLC roster first, then append mod-only class lines
                    merged = merge_records(
                        van_data,
                        mod_data,
                        list_prefixes=CLASS_LIST_PREFIXES,
                        semicolon_keys=semi,
                    )
                else:
                    # Mod class lines first, then fill missing DLC slots
                    merged = merge_records(
                        mod_data,
                        van_data,
                        list_prefixes=CLASS_LIST_PREFIXES,
                        semicolon_keys=semi,
                    )
                write_dbr(mod_path, merged)
                self.report.merged_hubs.append(rel)
            except Exception as exc:
                self.report.conflicts.append(f"{rel}: {exc}")

        # Snapshot class lines from male PC if present
        pc = self.mod_db / "records/creatures/pc/malepc01.dbr"
        if pc.is_file():
            trees = get_list_field(read_dbr(pc), "skillTree")
            self.report.class_lines = trees
            self.report.notes.append(f"PC skillTree count: {len(trees)}")

    def unlock_full_classes(self, extra_class_dbs: Optional[Iterable[Path]] = None) -> CompatReport:
        """
        Ensure full stock/DLC class roster + any mod class lines.

        - Import DLC/base class trees (playerclass01-10, UI class panes, Berserker)
        - Optionally overlay class lines from other mods' unpacked databases
        - Merge hubs keeping mod class lines, filling missing DLC slots
        """
        self.ensure_layers_extracted()
        self.mod_db.mkdir(parents=True, exist_ok=True)

        for layer in ("database", "gdx1", "gdx2", "gdx3"):
            root = self._layer_roots.get(layer)
            if root:
                n = self.import_class_trees_from_root(root, layer)
                if n:
                    self.report.notes.append(f"Imported {n} class-tree files from {layer}")

        for extra in extra_class_dbs or []:
            extra = Path(extra)
            if extra.is_dir():
                # Later extras (higher priority) overwrite overlapping class trees
                n = self.import_class_trees_from_root(extra, extra.name, overwrite=True)
                self.report.notes.append(
                    f"Imported {n} class-tree files from mod class DB {extra}"
                )
                # Merge that mod's hubs into ours (extra class lines first)
                for rel in CLASS_HUB_RELATIVE:
                    src = extra / rel
                    dest = self.mod_db / rel
                    if not src.is_file():
                        continue
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)
                        continue
                    try:
                        write_dbr(
                            dest,
                            merge_records(
                                read_dbr(src),
                                read_dbr(dest),
                                list_prefixes=CLASS_LIST_PREFIXES,
                                semicolon_keys=CLASS_SELECTION_SEMICOLON_KEYS
                                if "classselection" in rel.lower()
                                else None,
                            ),
                        )
                        self.report.merged_hubs.append(f"{rel} (+{extra.name})")
                    except Exception as exc:
                        self.report.conflicts.append(f"extra {extra.name} {rel}: {exc}")

        self.merge_class_hubs(vanilla_first_lists=False)
        self.report.notes.append(
            "unlock_full_classes: DLC roster + mod class lines merged (mod lines preserved)."
        )
        return self.report

    def pass_a_patch_mod_for_dlc(self, *, full_classes: bool = False) -> CompatReport:
        """Import missing DLC records and merge class hubs so Berserker / DLC classes appear."""
        self.ensure_layers_extracted()
        self.mod_db.mkdir(parents=True, exist_ok=True)

        for layer in ("gdx3", "gdx2", "gdx1", "database"):
            root = self._layer_roots.get(layer)
            if not root:
                continue
            for src in self._iter_layer_records(layer) if layer != "database" else root.rglob("*.dbr"):
                if layer == "database":
                    rel_path = src.relative_to(root)
                    rel = rel_path.as_posix().lower()
                    if not (
                        any(cat in rel for cat in self.categories)
                        or any(h in rel for h in BERSERKER_HINTS)
                    ):
                        continue
                else:
                    rel_path = src.relative_to(root)
                dest = self.mod_db / rel_path
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    self.report.imported.append(rel_path.as_posix())

        if full_classes:
            self.unlock_full_classes()
        else:
            self.merge_class_hubs()
            for hint in ("records/ui/skills/class10", "records/skills/playerclass10"):
                src_root = self._layer_roots.get("gdx3")
                if not src_root:
                    break
                src_dir = src_root / hint
                if src_dir.is_dir():
                    dest_dir = self.mod_db / hint
                    if not dest_dir.exists():
                        shutil.copytree(src_dir, dest_dir)
                        self.report.imported.append(hint + "/")
                        self.report.notes.append(f"Copied Berserker tree {hint}")

        self.report.notes.append(
            "Pass A complete: missing DLC records imported; class hubs merged (mod class lines kept)."
        )
        return self.report

    def pass_b_patch_dlc_for_mod(self) -> CompatReport:
        """Apply mod deltas onto imported DLC records that share paths."""
        self.ensure_layers_extracted()
        if not self.mod_db.is_dir():
            self.report.notes.append("No mod database to reconcile.")
            return self.report

        for mod_file in self.mod_db.rglob("*.dbr"):
            rel = mod_file.relative_to(self.mod_db).as_posix()
            vanilla = self._find_in_layers(rel)
            if vanilla is None:
                continue
            try:
                mod_data = read_dbr(mod_file)
                van_data = read_dbr(vanilla)
                merged = merge_records(
                    mod_data,
                    van_data,
                    list_prefixes=CLASS_LIST_PREFIXES,
                    semicolon_keys=CLASS_SELECTION_SEMICOLON_KEYS
                    if "classselection" in rel.lower()
                    else None,
                )
                write_dbr(mod_file, merged)
            except Exception as exc:
                self.report.conflicts.append(f"Pass B {rel}: {exc}")

        self.report.notes.append(
            "Pass B complete: shared DLC records reconciled; mod class lines preserved."
        )
        return self.report

    def full_compat(
        self,
        *,
        full_classes: bool = False,
        extra_class_dbs: Optional[Iterable[Path]] = None,
    ) -> CompatReport:
        self.pass_a_patch_mod_for_dlc(full_classes=full_classes)
        if extra_class_dbs:
            self.unlock_full_classes(extra_class_dbs=extra_class_dbs)
        self.pass_b_patch_dlc_for_mod()
        return self.report
