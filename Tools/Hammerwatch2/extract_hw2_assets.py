"""
Extract named files from Hammerwatch 2 res/assets.bin (HW2R + LZ4 blocks).

Usage:
  python extract_hw2_assets.py --assets ".../res/assets.bin" --out OutDir --path actors/.../file.tif
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

try:
	import lz4.block
except ImportError as exc:  # pragma: no cover
	raise SystemExit("pip install lz4") from exc


def read_cstring(data: bytes, offset: int) -> tuple[str, int]:
	end = data.find(b"\0", offset)
	if end < 0:
		raise ValueError(f"unterminated string at {offset}")
	return data[offset:end].decode("utf-8", errors="replace"), end + 1


def parse_hw2r(data: bytes) -> dict[str, bytes]:
	if data[:4] != b"HW2R":
		raise ValueError(f"bad magic {data[:4]!r}")

	# Layout observed in HW2 assets.bin:
	# HW2R
	# uint32 version?
	# uint32 entry_count
	# then entries: path\0, uint32 offset, uint32 compressed_size, uint32 uncompressed_size, uint32 flags?
	# Actual layouts vary by build; probe flexibly.
	off = 4
	version = struct.unpack_from("<I", data, off)[0]
	off += 4
	count = struct.unpack_from("<I", data, off)[0]
	off += 4

	# Heuristic: if count is huge, this isn't the right header interpretation.
	if count <= 0 or count > 500000:
		# Fallback: scan for path-like strings followed by size/offset triples near known files.
		return parse_by_scan(data)

	entries: list[tuple[str, int, int, int]] = []
	try:
		for _ in range(count):
			path, off = read_cstring(data, off)
			# Try common 3x uint32: offset, csize, usize
			vals = struct.unpack_from("<III", data, off)
			off += 12
			# Optional flags
			# Some builds have an extra uint32
			entries.append((path.replace("\\", "/"), vals[0], vals[1], vals[2]))
	except Exception:
		return parse_by_scan(data)

	# Validate first few offsets
	ok = 0
	for path, offset, csize, usize in entries[:20]:
		if 0 <= offset < len(data) and csize > 0 and offset + csize <= len(data):
			ok += 1
	if ok < 5:
		return parse_by_scan(data)

	out: dict[str, bytes] = {}
	for path, offset, csize, usize in entries:
		blob = data[offset : offset + csize]
		try:
			if usize and usize != csize:
				payload = lz4.block.decompress(blob, uncompressed_size=usize)
			else:
				try:
					payload = lz4.block.decompress(blob)
				except Exception:
					payload = blob
		except Exception:
			payload = blob
		out[path] = payload
	print(f"Parsed {len(out)} entries (version={version})")
	return out


def parse_by_scan(data: bytes) -> dict[str, bytes]:
	"""
	Fallback: find path strings and assume nearby metadata points at compressed blobs.
	This is only used to extract requested paths, not rebuild the whole archive.
	"""
	# Prefer table-based parse via known index near start if present.
	# Many HW2 builds store a TOC of: uint32 path_hash / or path then 4 ints.
	# As a robust approach for extraction: locate path string, then search forward
	# for an offset that points to an lz4 frame containing file signature.
	raise ValueError(
		"Could not parse HW2R TOC with the simple header layout. "
		"Use absolute vanilla texture paths in the mod instead of extracting, "
		"or provide a known-good TOC parser."
	)


def extract_requested(archive: dict[str, bytes], paths: list[str], out_dir: Path) -> None:
	# Normalize keys
	norm = {k.replace("\\", "/").lstrip("/"): v for k, v in archive.items()}
	for raw in paths:
		key = raw.replace("\\", "/").lstrip("/")
		if key not in norm:
			# try case-insensitive
			matches = [k for k in norm if k.lower() == key.lower()]
			if not matches:
				print(f"MISSING: {key}")
				continue
			key = matches[0]
		payload = norm[key]
		dest = out_dir / key
		dest.parent.mkdir(parents=True, exist_ok=True)
		dest.write_bytes(payload)
		print(f"OK: {key} ({len(payload)} bytes) -> {dest}")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--assets", required=True)
	ap.add_argument("--out", required=True)
	ap.add_argument("--path", action="append", dest="paths", required=True)
	args = ap.parse_args()

	data = Path(args.assets).read_bytes()
	# Try full parse; if TOC parse fails, attempt single-path carve using string index.
	try:
		archive = parse_hw2r(data)
		extract_requested(archive, args.paths, Path(args.out))
		return
	except Exception as exc:
		print(f"TOC parse failed: {exc}")
		print("Falling back to path-local carve (best effort)...")

	out_dir = Path(args.out)
	for raw in args.paths:
		key = raw.replace("\\", "/").lstrip("/")
		needle = key.encode("utf-8")
		idx = data.find(needle)
		if idx < 0:
			print(f"MISSING string: {key}")
			continue
		# Look for uint32 triples around the path occurrence in TOC.
		# Scan a window before the string for plausible offset/size.
		window_start = max(0, idx - 64)
		window = data[window_start : idx + len(needle) + 64]
		found = False
		for rel in range(0, max(0, len(window) - 12)):
			offset, csize, usize = struct.unpack_from("<III", window, rel)
			if csize <= 0 or csize > 50_000_000:
				continue
			if offset <= 0 or offset + csize > len(data):
				continue
			blob = data[offset : offset + csize]
			payload = None
			for candidate_usize in (usize, None):
				try:
					if candidate_usize:
						payload = lz4.block.decompress(blob, uncompressed_size=candidate_usize)
					else:
						payload = lz4.block.decompress(blob)
					break
				except Exception:
					continue
			if payload is None:
				# Accept raw if it looks like png/tif
				if blob[:8] == b"\x89PNG\r\n\x1a\n" or blob[:2] in (b"II", b"MM") or blob[:4] == b"RIFF":
					payload = blob
				else:
					continue
			dest = out_dir / key
			dest.parent.mkdir(parents=True, exist_ok=True)
			dest.write_bytes(payload)
			print(f"OK(carve): {key} ({len(payload)} bytes) -> {dest}")
			found = True
			break
		if not found:
			print(f"FAILED carve: {key} (string at {idx})")


if __name__ == "__main__":
	main()
