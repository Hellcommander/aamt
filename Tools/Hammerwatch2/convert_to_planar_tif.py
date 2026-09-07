"""
Convert images to Hammerwatch 2 planar TIFs.

Pipeline (GIMP cannot write PlanarConfiguration=2 natively):
  1. GIMP opens source and exports a contiguous TIFF
     (keeps alpha / transparent pixel color values)
  2. ImageMagick `magick in.tif -interlace plane out.tif`
     or LibTIFF `tiffcp -p separate in.tif out.tif`

GIMP root default: D:\\tools\\GIMP
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_GIMP_ROOT = Path(r"D:\tools\GIMP")
DEFAULT_MAGICK_CANDIDATES = [
	Path(r"E:\tools\ImageMagick\magick.exe"),
	Path(r"D:\tools\ImageMagick\magick.exe"),
]
DEFAULT_TIFS_ROOT = Path(r"F:\SteamLibrary\steamapps\common\Hammerwatch 2\hw2_tgas")


def find_gimp_console(gimp_root: Path) -> Path:
	bin_dir = gimp_root / "bin"
	for name in (
		"gimp-console-3.exe",
		"gimp-console-3.0.exe",
		"gimp-console.exe",
	):
		p = bin_dir / name
		if p.exists():
			return p
	raise FileNotFoundError(f"No gimp-console under {bin_dir}")


def find_tool(names: list[str], extra_paths: list[Path] | None = None) -> str | None:
	if extra_paths:
		for p in extra_paths:
			if p.exists():
				return str(p)
	for name in names:
		path = shutil.which(name)
		if path:
			return path
	return None


def gimp_export_contiguous_tif(gimp: Path, src: Path, dst: Path) -> None:
	"""Batch: open src in GIMP, export contiguous TIFF with transparent color values kept."""
	src_uri = src.resolve().as_uri()
	dst_uri = dst.resolve().as_uri()
	# GIMP 3 python-fu-eval batch. file-tiff-export keeps contiguous planar config;
	# save-transparent-color-values preserves masking/recolor data.
	script = f"""
import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
from gi.repository import Gimp, Gio, GLib

src = Gio.File.new_for_uri({src_uri!r})
dst = Gio.File.new_for_uri({dst_uri!r})
image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, src)
if image is None:
    raise RuntimeError('GIMP failed to load ' + {str(src)!r})
image.flatten()
procedure = Gimp.get_pdb().lookup_procedure('file-tiff-export')
config = procedure.create_config()
config.set_property('image', image)
config.set_property('file', dst)
config.set_property('raw', False)
try:
    config.set_property('bigtiff', False)
except Exception:
    pass
try:
    config.set_property('cmyk', False)
except Exception:
    pass
for key, val in (
    ('save-transparent', True),
    ('save-transp-pixels', True),
    ('keep-transparent', True),
):
    try:
        config.set_property(key, val)
    except Exception:
        pass
try:
    config.set_property('compression', 'none')
except Exception:
    pass
result = procedure.run(config)
image.delete()
status = result.index(0) if hasattr(result, 'index') else result[0]
if int(status) != int(Gimp.PDBStatusType.SUCCESS):
    raise RuntimeError('file-tiff-export failed for ' + {str(src)!r})
"""
	cmd = [
		str(gimp),
		"-nidfs",
		"--batch-interpreter",
		"python-fu-eval",
		"-b",
		script,
		"-b",
		"import sys; sys.exit(0)",
	]
	env = os.environ.copy()
	# Prefer GIMP's own runtime libs
	bin_dir = str(gimp.parent)
	env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
	r = subprocess.run(cmd, capture_output=True, text=True, env=env)
	if r.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
		raise RuntimeError(
			"GIMP export failed\n"
			f"cmd: {' '.join(cmd[:4])} ...\n"
			f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
		)


def to_planar(magick: str | None, tiffcp: str | None, src: Path, dst: Path) -> str:
	"""Reformat contiguous TIFF → planar (PlanarConfiguration=2)."""
	tmp = dst.with_suffix(".planar_tmp.tif")
	if magick:
		r = subprocess.run(
			[magick, str(src), "-interlace", "plane", str(tmp)],
			capture_output=True,
			text=True,
		)
		if r.returncode != 0 or not tmp.exists():
			raise RuntimeError(f"ImageMagick planar convert failed:\n{r.stderr}")
		tmp.replace(dst)
		return "imagemagick"
	if tiffcp:
		r = subprocess.run(
			[tiffcp, "-p", "separate", str(src), str(tmp)],
			capture_output=True,
			text=True,
		)
		if r.returncode != 0 or not tmp.exists():
			raise RuntimeError(f"tiffcp planar convert failed:\n{r.stderr}")
		tmp.replace(dst)
		return "tiffcp"
	raise RuntimeError(
		"Need ImageMagick (`magick`) or LibTIFF (`tiffcp`) for planar post-process."
	)


def convert_one(
	gimp: Path,
	magick: str | None,
	tiffcp: str | None,
	src: Path,
	dst: Path,
	workdir: Path,
) -> str:
	dst.parent.mkdir(parents=True, exist_ok=True)
	contig = workdir / (src.stem + ".contig.tif")
	# If source is already a TIFF from GIMP/manual export, still re-open via GIMP
	# so transparent color values are preserved consistently.
	gimp_export_contiguous_tif(gimp, src, contig)
	tool = to_planar(magick, tiffcp, contig, dst)
	return tool


def collect_sources(path: Path, recurse: bool) -> list[Path]:
	exts = {".png", ".tif", ".tiff", ".bmp", ".jpg", ".jpeg", ".webp"}
	if path.is_file():
		return [path]
	pattern_iter = path.rglob("*") if recurse else path.glob("*")
	return sorted(p for p in pattern_iter if p.is_file() and p.suffix.lower() in exts)


def main() -> int:
	ap = argparse.ArgumentParser(description="GIMP export + planar TIFF post-process for HW2")
	ap.add_argument("path", help="Source file or folder")
	ap.add_argument(
		"--out-dir",
		default="",
		help="Output folder (default: same as each source, .tif extension)",
	)
	ap.add_argument("--gimp-root", default=str(DEFAULT_GIMP_ROOT))
	ap.add_argument("--recurse", action="store_true")
	ap.add_argument(
		"--in-place",
		action="store_true",
		help="Overwrite .tif next to source (or replace source if it is already .tif)",
	)
	args = ap.parse_args()

	src_root = Path(args.path)
	if not src_root.exists():
		print(f"Path not found: {src_root}", file=sys.stderr)
		return 1

	gimp = find_gimp_console(Path(args.gimp_root))
	magick = find_tool(["magick"], DEFAULT_MAGICK_CANDIDATES)
	tiffcp = find_tool(["tiffcp"])
	if not magick and not tiffcp:
		print(
			"Install ImageMagick (magick) or LibTIFF (tiffcp). "
			"GIMP alone cannot write planar TIFs.\n"
			"For vanilla sheets, prefer Copy-Hw2Tifs.ps1 from hw2_tgas instead.",
			file=sys.stderr,
		)
		return 1

	sources = collect_sources(src_root, args.recurse)
	if not sources:
		print("No source images found.")
		return 0

	out_dir = Path(args.out_dir) if args.out_dir else None
	print(f"GIMP: {gimp}")
	print(f"Planar tool: {'magick' if magick else 'tiffcp'}")
	print(f"Converting {len(sources)} file(s)...")

	with tempfile.TemporaryDirectory(prefix="hw2_planar_") as tmp:
		tmpdir = Path(tmp)
		for src in sources:
			if out_dir:
				dst = out_dir / (src.stem + ".tif")
			elif args.in_place or src.suffix.lower() in {".tif", ".tiff"}:
				dst = src.with_suffix(".tif")
			else:
				dst = src.with_suffix(".tif")
			try:
				tool = convert_one(gimp, magick, tiffcp, src, dst, tmpdir)
				print(f"  OK [{tool}] {src.name} -> {dst}")
			except Exception as exc:
				print(f"  FAIL {src}: {exc}", file=sys.stderr)
				return 1

	print("Done.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
