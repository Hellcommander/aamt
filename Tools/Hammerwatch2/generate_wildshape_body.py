"""
Generate player-compatible wildshape body units for Druidic Warden.

Forms: shambler, wolf, boar, spider
Each maps wizard/player scene names onto beast sheets and synthesizes
missing anims (dash/skill/beam/grimoire/...).

Texture modes:
  absolute (default) — paths into res/assets.bin
  local              — ./ TIFs copied from hw2_tgas beside each unit
"""
from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass, field
from pathlib import Path

DIRS = 8
MAT = 'material="system/default.mats:player"'
DEFAULT_TIFS_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Hammerwatch 2\hw2_tgas")
DEFAULT_MOD = Path(r"F:\SteamLibrary\steamapps\common\Hammerwatch 2\Druidic_Warden")
DEFAULT_TOOLS = Path(
	r"D:\games\Steam\steamapps\common\Transcendence\Tools\Hammerwatch2\GeneratedAssets\wildshape"
)


@dataclass
class Sheet:
	abs_path: str
	local_name: str
	hw2_rel: str
	size: int
	origin: str


@dataclass
class FormDef:
	id: str
	unit_subdir: str
	unit_filename: str
	idle: Sheet
	move: Sheet
	attack: Sheet
	dash: Sheet
	# move sheet layout
	move_rows: list[int] = field(default_factory=list)
	move_times: list[int] = field(default_factory=list)
	attack_rows: list[int] = field(default_factory=list)
	attack_times: list[int] = field(default_factory=list)
	dash_rows: list[int] = field(default_factory=list)
	dash_times: list[int] = field(default_factory=list)
	skill_rows: list[int] = field(default_factory=list)
	skill_times: list[int] = field(default_factory=list)


def xs(size: int) -> list[int]:
	return [i * size for i in range(DIRS)]


FORMS: list[FormDef] = [
	FormDef(
		id="shambler",
		unit_subdir="shamblers",
		unit_filename="shambler_wildshape_body.unit",
		idle=Sheet(
			"actors/beasts/shamblers/shambler_small/shambler_small.tif",
			"shambler_small.tif",
			"actors/beasts/shamblers/shambler_small/shambler_small.tif",
			64,
			"32 42",
		),
		move=Sheet(
			"actors/beasts/shamblers/shambler_small/shambler_small_move.tif",
			"shambler_small_move.tif",
			"actors/beasts/shamblers/shambler_small/shambler_small_move.tif",
			64,
			"32 42",
		),
		attack=Sheet(
			"actors/beasts/shamblers/shambler_small/shambler_small_lunge.tif",
			"shambler_small_lunge.tif",
			"actors/beasts/shamblers/shambler_small/shambler_small_lunge.tif",
			80,
			"40 50",
		),
		dash=Sheet(
			"actors/beasts/shamblers/shambler_small/shambler_small_charge.tif",
			"shambler_small_charge.tif",
			"actors/beasts/shamblers/shambler_small/shambler_small_charge.tif",
			64,
			"32 42",
		),
		move_rows=[0, 64, 128, 192, 256, 320, 384, 448],
		move_times=[120, 90, 120, 90, 120, 90, 120, 90],
		attack_rows=[0, 80, 160, 240, 320, 400, 480, 560],
		attack_times=[150, 150, 150, 100, 50, 50, 300, 200],
		dash_rows=[64, 320, 384],
		dash_times=[200, 200, 200],
		skill_rows=[0, 64, 128, 192, 256],
		skill_times=[100, 100, 120, 120, 150],
	),
	FormDef(
		id="wolf",
		unit_subdir="wolves",
		unit_filename="wolf_wildshape_body.unit",
		idle=Sheet(
			"actors/beasts/wolves/wolf_worg/wolf_worg.tif",
			"wolf_worg.tif",
			"actors/beasts/wolves/wolf_worg/wolf_worg.tif",
			80,
			"41 48",
		),
		move=Sheet(
			"actors/beasts/wolves/wolf_worg/wolf_worg_walk.tif",
			"wolf_worg_walk.tif",
			"actors/beasts/wolves/wolf_worg/wolf_worg_walk.tif",
			80,
			"41 48",
		),
		attack=Sheet(
			"actors/beasts/wolves/wolf_worg/wolf_worg_attack.tif",
			"wolf_worg_attack.tif",
			"actors/beasts/wolves/wolf_worg/wolf_worg_attack.tif",
			80,
			"41 48",
		),
		dash=Sheet(
			"actors/beasts/wolves/wolf_worg/wolf_worg_run.tif",
			"wolf_worg_run.tif",
			"actors/beasts/wolves/wolf_worg/wolf_worg_run.tif",
			80,
			"41 48",
		),
		move_rows=[0, 80, 160, 240, 320, 400, 480, 560, 640, 720, 800, 880],
		move_times=[80] * 12,
		attack_rows=[0, 80, 160, 240, 320, 400, 480, 560],
		attack_times=[100, 150, 100, 100, 100, 100, 200, 100],
		dash_rows=[0, 80, 160, 240, 320, 400, 480, 560],
		dash_times=[60] * 8,
		skill_rows=[0, 80, 160, 240, 320],
		skill_times=[100, 120, 120, 100, 150],
	),
	FormDef(
		id="boar",
		unit_subdir="boars",
		unit_filename="boar_wildshape_body.unit",
		idle=Sheet(
			"actors/beasts/boars/boar_razorback/boar_razorback.tif",
			"boar_razorback.tif",
			"actors/beasts/boars/boar_razorback/boar_razorback.tif",
			64,
			"32 32",
		),
		move=Sheet(
			"actors/beasts/boars/boar_razorback/boar_razorback_move.tif",
			"boar_razorback_move.tif",
			"actors/beasts/boars/boar_razorback/boar_razorback_move.tif",
			64,
			"32 32",
		),
		attack=Sheet(
			"actors/beasts/boars/boar_razorback/boar_razorback_attack.tif",
			"boar_razorback_attack.tif",
			"actors/beasts/boars/boar_razorback/boar_razorback_attack.tif",
			64,
			"32 32",
		),
		dash=Sheet(
			"actors/beasts/boars/boar_razorback/boar_razorback_move.tif",
			"boar_razorback_move.tif",
			"actors/beasts/boars/boar_razorback/boar_razorback_move.tif",
			64,
			"32 32",
		),
		move_rows=[0, 64, 128, 192, 256, 320],
		move_times=[100] * 6,
		attack_rows=[384, 448, 512, 576, 640, 704, 768],
		attack_times=[400, 100, 100, 150, 150, 100, 50],
		# run columns live at x+512 on move sheet; dash uses attack charge_start rows
		dash_rows=[0, 64, 128, 192, 256, 320],
		dash_times=[60] * 6,
		skill_rows=[0, 64, 128, 192, 256, 320],
		skill_times=[90] * 6,
	),
	FormDef(
		id="spider",
		unit_subdir="spiders",
		unit_filename="spider_wildshape_body.unit",
		idle=Sheet(
			"actors/beasts/spiders/spider_black/spider_black.tif",
			"spider_black.tif",
			"actors/beasts/spiders/spider_black/spider_black.tif",
			64,
			"32 32",
		),
		move=Sheet(
			"actors/beasts/spiders/spider_black/spider_black.tif",
			"spider_black.tif",
			"actors/beasts/spiders/spider_black/spider_black.tif",
			64,
			"32 32",
		),
		attack=Sheet(
			"actors/beasts/spiders/spider_black/spider_black.tif",
			"spider_black.tif",
			"actors/beasts/spiders/spider_black/spider_black.tif",
			64,
			"32 32",
		),
		dash=Sheet(
			"actors/beasts/spiders/spider_black/spider_black.tif",
			"spider_black.tif",
			"actors/beasts/spiders/spider_black/spider_black.tif",
			64,
			"32 32",
		),
		move_rows=[64, 128, 192, 256],
		move_times=[100] * 4,
		attack_rows=[320, 384, 448, 512],
		attack_times=[100, 100, 150, 350],
		dash_rows=[64, 128, 192, 256],
		dash_times=[70] * 4,
		skill_rows=[576, 640, 704],
		skill_times=[100, 100, 400],
	),
]


def tex(sheet: Sheet, local: bool) -> str:
	return f"./{sheet.local_name}" if local else sheet.abs_path


def scene_idle(lines: list[str], form: FormDef, local: bool) -> None:
	t = tex(form.idle, local)
	s = form.idle.size
	for i, x in enumerate(xs(s)):
		lines.append(f'\t\t<scene name="idle-{i}">')
		lines.append(f'\t\t\t<sprite origin="{form.idle.origin}" looping="true" texture="{t}" {MAT}>')
		lines.append(f"\t\t\t\t<frame>{x} 0 {s} {s}</frame>")
		lines.append("\t\t\t</sprite>")
		lines.append("\t\t</scene>")


def scene_strip(
	lines: list[str],
	name: str,
	sheet: Sheet,
	rows: list[int],
	times: list[int],
	local: bool,
	looping: bool,
	x_offset: int = 0,
) -> None:
	t = tex(sheet, local)
	s = sheet.size
	loop = "true" if looping else "false"
	for i, x in enumerate(xs(s)):
		xx = x + x_offset
		lines.append(f'\t\t<scene name="{name}-{i}">')
		lines.append(
			f'\t\t\t<sprite origin="{sheet.origin}" looping="{loop}" texture="{t}" {MAT}>'
		)
		for row, tm in zip(rows, times):
			lines.append(f'\t\t\t\t<frame time="{tm}">{xx} {row} {s} {s}</frame>')
		lines.append("\t\t\t</sprite>")
		lines.append("\t\t</scene>")


def scene_jump_blink(lines: list[str], form: FormDef, local: bool) -> None:
	t = tex(form.idle, local)
	s = form.idle.size
	for name, x in (("jump_start", 0), ("jump_fall", s), ("jump_land", 0)):
		lines.append(f'\t\t<scene name="{name}">')
		lines.append(f'\t\t\t<sprite origin="{form.idle.origin}" looping="true" texture="{t}" {MAT}>')
		lines.append(f"\t\t\t\t<frame>{x} 0 {s} {s}</frame>")
		lines.append("\t\t\t</sprite>")
		lines.append("\t\t</scene>")
	td = tex(form.dash, local)
	lines.append('\t\t<scene name="blink">')
	lines.append(f'\t\t\t<sprite origin="{form.dash.origin}" looping="true" texture="{td}" {MAT}>')
	lines.append('\t\t\t\t<frame time="30">0 0 0 0</frame>')
	lines.append("\t\t\t</sprite>")
	lines.append("\t\t</scene>")


def build_unit(form: FormDef, local: bool) -> str:
	lines = [
		f"<!-- Auto-generated wildshape body ({form.id}) — re-run generate_wildshape_body.py -->",
		'<unit netsync="position" slot="actor">',
		'\t<scenes start="idle-0 idle-1 idle-2 idle-3 idle-4 idle-5 idle-6 idle-7">',
		"",
	]
	scene_idle(lines, form, local)
	lines.append("")
	scene_strip(lines, "walk", form.move, form.move_rows, form.move_times, local, True)
	lines.append("")
	scene_strip(lines, "attack", form.attack, form.attack_rows, form.attack_times, local, False)
	lines.append("")
	scene_strip(lines, "attack_walk", form.attack, form.attack_rows, form.attack_times, local, False)
	lines.append("")
	# boar dash uses run columns on move sheet (x+512)
	dash_x = 512 if form.id == "boar" else 0
	dash_sheet = form.move if form.id == "boar" else form.dash
	dash_rows = form.move_rows if form.id == "boar" else form.dash_rows
	dash_times = form.dash_times
	scene_strip(lines, "dash", dash_sheet, dash_rows, dash_times, local, True, dash_x)
	lines.append("")
	scene_strip(lines, "skill", form.dash if form.id != "spider" else form.attack, form.skill_rows, form.skill_times, local, False)
	lines.append("")
	scene_strip(lines, "skill_walk", form.dash if form.id != "spider" else form.attack, form.skill_rows, form.skill_times, local, False)
	lines.append("")
	# short cast = first two skill frames
	short_rows = form.skill_rows[:2] or form.attack_rows[:2]
	short_times = form.skill_times[:2] or [100, 100]
	scene_strip(lines, "skill_short", form.dash if form.id != "spider" else form.attack, short_rows, short_times, local, False)
	lines.append("")
	scene_strip(lines, "skill_short_walk", form.dash if form.id != "spider" else form.attack, short_rows, short_times, local, False)
	lines.append("")
	scene_strip(lines, "beam", dash_sheet, dash_rows, dash_times, local, True, dash_x)
	lines.append("")
	scene_strip(lines, "beam_walk", form.move, form.move_rows, form.move_times, local, True)
	lines.append("")
	scene_strip(lines, "grimoire", dash_sheet, dash_rows, dash_times, local, True, dash_x)
	lines.append("")
	scene_strip(lines, "grimoire_walk", form.move, form.move_rows, form.move_times, local, True)
	lines.append("")
	scene_strip(lines, "item_skill", form.attack, form.attack_rows, form.attack_times, local, False)
	lines.append("")
	scene_strip(lines, "item_skill_walk", form.attack, form.attack_rows, form.attack_times, local, False)
	lines.append("")
	scene_jump_blink(lines, form, local)
	lines.append("\t</scenes>")
	lines.append("</unit>")
	lines.append("")
	return "\n".join(lines)


def stage_form_tifs(form: FormDef, tifs_root: Path, dest: Path) -> list[str]:
	notes: list[str] = []
	dest.mkdir(parents=True, exist_ok=True)
	seen: set[str] = set()
	for sheet in (form.idle, form.move, form.attack, form.dash):
		if sheet.local_name in seen:
			continue
		seen.add(sheet.local_name)
		src = tifs_root / Path(sheet.hw2_rel)
		if not src.exists():
			# wolf walk/run live next to wolf_worg.tif in hw2_tgas/wolves flat
			alt = tifs_root / "actors" / "beasts" / "wolves" / sheet.local_name
			src = alt if alt.exists() else src
		if not src.exists():
			notes.append(f"Missing {sheet.hw2_rel}")
			continue
		shutil.copy2(src, dest / sheet.local_name)
		notes.append(f"Staged {sheet.local_name}")
	return notes


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--mod-root", default=str(DEFAULT_MOD))
	ap.add_argument("--tools-out", default=str(DEFAULT_TOOLS))
	ap.add_argument("--tifs-root", default=str(DEFAULT_TIFS_ROOT))
	ap.add_argument("--texture-mode", choices=("absolute", "local"), default="absolute")
	ap.add_argument("--forms", default="shambler,wolf,boar,spider")
	args = ap.parse_args()

	mod_root = Path(args.mod_root)
	tools_out = Path(args.tools_out)
	tifs_root = Path(args.tifs_root)
	local = args.texture_mode == "local"
	wanted = {x.strip() for x in args.forms.split(",") if x.strip()}

	tools_out.mkdir(parents=True, exist_ok=True)
	all_notes: list[str] = [f"texture-mode={args.texture_mode}"]

	for form in FORMS:
		if form.id not in wanted:
			continue
		unit_dir = mod_root / "players" / "druidic_warden" / "units" / form.unit_subdir
		unit_dir.mkdir(parents=True, exist_ok=True)
		stage_dir = tools_out / "tifs_from_hw2_tgas" / form.id
		all_notes.extend(stage_form_tifs(form, tifs_root, stage_dir))
		if local:
			all_notes.extend(stage_form_tifs(form, tifs_root, unit_dir))
		text = build_unit(form, local)
		body = unit_dir / form.unit_filename
		body.write_text(text, encoding="utf-8")
		(tools_out / form.unit_filename).write_text(text, encoding="utf-8")
		print(f"Wrote {body}")

	(tools_out / "GENERATOR_NOTES.txt").write_text("\n".join(all_notes) + "\n", encoding="utf-8")
	(tools_out / "ANIM_MAP.md").write_text(
		"\n".join(
			[
				"# Wildshape forms",
				"",
				"| Form | Role | Sheets |",
				"|---|---|---|",
				"| shambler | Tank / lightning | shambler_small_* |",
				"| wolf | Skirmish / bleed | wolf_worg_* |",
				"| boar | Bruiser / charge | boar_razorback_* |",
				"| spider | Venom / control (armored) | spider_black.tif atlas |",
				"",
				"Wasp was rejected as too fragile; spider covers poison/control instead.",
				"",
			]
		),
		encoding="utf-8",
	)
	for n in all_notes:
		print(n)


if __name__ == "__main__":
	main()
