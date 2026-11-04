extends RefCounted
## AAMT Sprite Forge core: image ops, palettes, Pixelorama project build/save,
## Starbound sheet + .frames + .animation export. Static functions only, so the
## CLI runner and the GUI panel share one implementation.
##
## Written against Pixelorama v1.2.3 (ExtensionsAPI 9, pxo v7). Projects are
## built from Pixelorama's own classes and saved through OpenSave.save_pxo_file,
## so the .pxo matches whatever Pixelorama build is running.

const VERSION := "1.0.0"
const EXT_NAME := "AAMTSpriteForge"
const TAG_COLORS := [
	Color(0.85, 0.35, 0.35), Color(0.35, 0.75, 0.4), Color(0.35, 0.55, 0.9),
	Color(0.9, 0.75, 0.3), Color(0.7, 0.4, 0.85), Color(0.3, 0.8, 0.8)
]
const IMAGE_EXTS := ["png", "webp", "jpg", "jpeg", "bmp", "tga"]

# ---------------------------------------------------------------------------
# small value parsers (CLI strings and JSON values both land here)
# ---------------------------------------------------------------------------


static func norm_path(p) -> String:
	return str(p).strip_edges().replace("\\", "/")


static func to_bool(v, fallback := false) -> bool:
	if v == null:
		return fallback
	if v is bool:
		return v
	if v is int or v is float:
		return v != 0
	var s := str(v).strip_edges().to_lower()
	if s in ["1", "true", "yes", "on", "y"]:
		return true
	if s in ["0", "false", "no", "off", "n", "none", ""]:
		return false
	return fallback


static func to_int(v, fallback := 0) -> int:
	if v == null:
		return fallback
	if v is int:
		return v
	if v is float:
		return int(round(v))
	var s := str(v).strip_edges()
	if s.is_valid_int():
		return s.to_int()
	if s.is_valid_float():
		return int(round(s.to_float()))
	return fallback


static func to_float(v, fallback := 0.0) -> float:
	if v == null:
		return fallback
	if v is int or v is float:
		return float(v)
	var s := str(v).strip_edges()
	if s.is_valid_float():
		return s.to_float()
	return fallback


## "32x48", "32", [32, 48], {"x":..,"y":..} -> Vector2i (fallback when unparsable).
static func to_size(v, fallback := Vector2i.ZERO) -> Vector2i:
	if v == null:
		return fallback
	if v is Vector2i:
		return v
	if v is Vector2:
		return Vector2i(v)
	if v is Array and v.size() >= 2:
		return Vector2i(to_int(v[0]), to_int(v[1]))
	if v is int or v is float:
		return Vector2i(int(v), int(v))
	var s := str(v).strip_edges().to_lower().replace("*", "x").replace(",", "x")
	if s.is_valid_int():
		return Vector2i(s.to_int(), s.to_int())
	var parts := s.split("x")
	if parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int():
		return Vector2i(parts[0].to_int(), parts[1].to_int())
	return fallback


static func parse_color(v, fallback := Color(0, 0, 0, 1)) -> Color:
	if v == null:
		return fallback
	if v is Color:
		return v
	if v is Array and v.size() >= 3:
		var comps := []
		for c in v:
			comps.append(to_float(c))
		var scale := 255.0 if (comps.max() > 1.0) else 1.0
		var a: float = comps[3] if comps.size() > 3 else scale
		return Color(comps[0] / scale, comps[1] / scale, comps[2] / scale, a / scale)
	var s := str(v).strip_edges()
	if s.begins_with("("):
		var parsed = str_to_var("Color" + s)
		if parsed is Color:
			return parsed
	if Color.html_is_valid(s):
		return Color.html(s)
	return fallback


static func color_hex(c: Color) -> String:
	return "#" + c.to_html(c.a < 1.0)


static func color_key(c: Color) -> int:
	return (c.r8 << 16) | (c.g8 << 8) | c.b8


# ---------------------------------------------------------------------------
# image loading
# ---------------------------------------------------------------------------


static func load_image(path: String) -> Image:
	path = norm_path(path)
	if not FileAccess.file_exists(path):
		return null
	var img := Image.load_from_file(path)
	if img == null or img.is_empty():
		return null
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	return img


static func is_image_path(path: String) -> bool:
	return path.get_extension().to_lower() in IMAGE_EXTS


## Sorted (natural order) image files in a folder.
static func list_images(dir_path: String, pattern := "*") -> PackedStringArray:
	dir_path = norm_path(dir_path)
	var out := PackedStringArray()
	if not DirAccess.dir_exists_absolute(dir_path):
		return out
	var names := Array(DirAccess.get_files_at(dir_path))
	names.sort_custom(func(a: String, b: String) -> bool: return a.naturalnocasecmp_to(b) < 0)
	for n: String in names:
		if is_image_path(n) and n.matchn(pattern):
			out.append(dir_path.path_join(n))
	return out


static func has_transparency(img: Image) -> bool:
	var data := img.get_data()
	var i := 3
	var n := data.size()
	# Stride-sample big images; any fully transparent pixel counts.
	var step := 4 * maxi(1, (n / 4) / 20000)
	while i < n:
		if data[i] < 250:
			return true
		i += step
	return false


## Shrinks very large opaque sources before background keying (keeps BFS fast).
static func cap_working_size(img: Image, max_side: int) -> Image:
	if max_side <= 0:
		return img
	var s := img.get_size()
	var m := maxi(s.x, s.y)
	if m <= max_side:
		return img
	var out := Image.new()
	out.copy_from(img)
	var f := float(max_side) / float(m)
	out.resize(maxi(1, int(round(s.x * f))), maxi(1, int(round(s.y * f))), Image.INTERPOLATE_LANCZOS)
	return out


# ---------------------------------------------------------------------------
# background removal (Unity stills are opaque RGB on white / baked checkerboard)
# ---------------------------------------------------------------------------


## mode: "auto" (only if no alpha; flood-fills light, low-saturation pixels from the
## border), "light" (same, forced), "color" (flood-fill pixels near key_color, default
## top-left pixel), "none".
static func remove_background(
	src: Image, mode := "auto", tolerance := 0.12, key_color = null, lum_min := 0.70
) -> Image:
	mode = mode.to_lower()
	if mode == "none" or mode == "":
		return src
	if mode == "auto":
		if has_transparency(src):
			return src
		mode = "light"
	var img := Image.new()
	img.copy_from(src)
	var w := img.get_width()
	var h := img.get_height()
	var data := img.get_data()
	var key := Color(1, 1, 1)
	if mode == "color":
		key = parse_color(key_color, img.get_pixel(0, 0)) if key_color != null else img.get_pixel(0, 0)
	var kr := key.r8
	var kg := key.g8
	var kb := key.b8
	var sat_tol := int(tolerance * 255.0)
	var lum_floor := int(lum_min * 255.0)
	var col_tol2 := int(pow(tolerance * 255.0 * 1.7320508, 2.0))
	var visited := PackedByteArray()
	visited.resize(w * h)
	var stack := PackedInt32Array()
	for x in w:
		stack.append(x)
		stack.append((h - 1) * w + x)
	for y in h:
		stack.append(y * w)
		stack.append(y * w + w - 1)
	var removed := 0
	while not stack.is_empty():
		var i := stack[stack.size() - 1]
		stack.resize(stack.size() - 1)
		if visited[i] != 0:
			continue
		visited[i] = 1
		var o := i * 4
		var r := data[o]
		var g := data[o + 1]
		var b := data[o + 2]
		var a := data[o + 3]
		var is_bg := a < 16
		if not is_bg:
			if mode == "color":
				var dr := r - kr
				var dg := g - kg
				var db := b - kb
				is_bg = dr * dr + dg * dg + db * db <= col_tol2
			else:
				var mx := maxi(r, maxi(g, b))
				var mn := mini(r, mini(g, b))
				is_bg = (mx - mn) <= sat_tol and (r + g + b) / 3 >= lum_floor
		if not is_bg:
			continue
		data[o + 3] = 0
		removed += 1
		var x := i % w
		var y := i / w
		if x > 0:
			stack.append(i - 1)
		if x < w - 1:
			stack.append(i + 1)
		if y > 0:
			stack.append(i - w)
		if y < h - 1:
			stack.append(i + w)
	img.set_data(w, h, false, Image.FORMAT_RGBA8, data)
	return img


# ---------------------------------------------------------------------------
# fit / pixelize
# ---------------------------------------------------------------------------


## Alpha-weighted area average (good default for big -> small pixel art).
static func downscale_box(src: Image, out_w: int, out_h: int) -> Image:
	var sw := src.get_width()
	var sh := src.get_height()
	var sd := src.get_data()
	var od := PackedByteArray()
	od.resize(out_w * out_h * 4)
	var fx := float(sw) / float(out_w)
	var fy := float(sh) / float(out_h)
	for oy in out_h:
		var y0 := int(floor(oy * fy))
		var y1 := mini(sh, maxi(y0 + 1, int(floor((oy + 1) * fy))))
		for ox in out_w:
			var x0 := int(floor(ox * fx))
			var x1 := mini(sw, maxi(x0 + 1, int(floor((ox + 1) * fx))))
			var ar := 0
			var ag := 0
			var ab := 0
			var aa := 0
			var n := 0
			for yy in range(y0, y1):
				var row := yy * sw
				for xx in range(x0, x1):
					var o := (row + xx) * 4
					var a := sd[o + 3]
					ar += sd[o] * a
					ag += sd[o + 1] * a
					ab += sd[o + 2] * a
					aa += a
					n += 1
			var d := (oy * out_w + ox) * 4
			if aa > 0 and n > 0:
				od[d] = clampi(ar / aa, 0, 255)
				od[d + 1] = clampi(ag / aa, 0, 255)
				od[d + 2] = clampi(ab / aa, 0, 255)
				od[d + 3] = clampi(aa / n, 0, 255)
	return Image.create_from_data(out_w, out_h, false, Image.FORMAT_RGBA8, od)


static func resample(src: Image, out_w: int, out_h: int, method := "box") -> Image:
	if src.get_width() == out_w and src.get_height() == out_h:
		var same := Image.new()
		same.copy_from(src)
		return same
	var upscale := out_w > src.get_width() or out_h > src.get_height()
	if method == "box" and not upscale:
		return downscale_box(src, out_w, out_h)
	var out := Image.new()
	out.copy_from(src)
	var interp := Image.INTERPOLATE_NEAREST
	if method == "lanczos" and not upscale:
		interp = Image.INTERPOLATE_LANCZOS
	elif method == "bilinear" and not upscale:
		interp = Image.INTERPOLATE_BILINEAR
	out.resize(out_w, out_h, interp)
	return out


static func threshold_alpha(img: Image, thr: int) -> void:
	if thr < 0:
		return
	var data := img.get_data()
	var i := 3
	while i < data.size():
		data[i] = 255 if data[i] >= thr else 0
		i += 4
	img.set_data(img.get_width(), img.get_height(), false, Image.FORMAT_RGBA8, data)


static func union_used_rect(images: Array) -> Rect2i:
	var r := Rect2i()
	var first := true
	for img: Image in images:
		var u := img.get_used_rect()
		if u.size == Vector2i.ZERO:
			continue
		if first:
			r = u
			first = false
		else:
			r = r.merge(u)
	return r


## Fits every frame into a cell with ONE shared scale/offset (keeps animation aligned).
## opts: trim(bool), margin(int), anchor("bottom"|"center"|"top"), resample(str),
##       alpha_threshold(int, -1 keeps soft alpha), upscale(bool, integer nearest only)
static func fit_frames(images: Array, cell: Vector2i, opts: Dictionary) -> Dictionary:
	var trim := to_bool(opts.get("trim", true), true)
	var margin := to_int(opts.get("margin", 1), 1)
	var anchor := str(opts.get("anchor", "bottom")).to_lower()
	var method := str(opts.get("resample", "box")).to_lower()
	var thr := to_int(opts.get("alpha_threshold", 128), 128)
	var allow_up := to_bool(opts.get("upscale", false))
	if images.is_empty():
		return {"images": [], "scale": 0.0}
	var src_size: Vector2i = (images[0] as Image).get_size()
	var rect := Rect2i(Vector2i.ZERO, src_size)
	if trim:
		var u := union_used_rect(images)
		if u.size != Vector2i.ZERO:
			rect = u
	var inner := cell - Vector2i(margin * 2, margin * 2)
	inner = Vector2i(maxi(1, inner.x), maxi(1, inner.y))
	var scale := minf(float(inner.x) / rect.size.x, float(inner.y) / rect.size.y)
	if scale > 1.0:
		scale = floorf(scale) if allow_up else 1.0
	var out_size := Vector2i(
		maxi(1, int(round(rect.size.x * scale))), maxi(1, int(round(rect.size.y * scale)))
	)
	out_size = Vector2i(mini(out_size.x, inner.x), mini(out_size.y, inner.y))
	var pos := Vector2i((cell.x - out_size.x) / 2, 0)
	match anchor:
		"top":
			pos.y = margin
		"center":
			pos.y = (cell.y - out_size.y) / 2
		_:
			pos.y = cell.y - margin - out_size.y
	var out := []
	for img: Image in images:
		var region := img.get_region(rect)
		var small := resample(region, out_size.x, out_size.y, method)
		threshold_alpha(small, thr)
		var canvas := Image.create_empty(cell.x, cell.y, false, Image.FORMAT_RGBA8)
		canvas.blit_rect(small, Rect2i(Vector2i.ZERO, out_size), pos)
		out.append(canvas)
	return {"images": out, "scale": scale, "source_rect": [rect.position.x, rect.position.y, rect.size.x, rect.size.y], "placed": [pos.x, pos.y, out_size.x, out_size.y]}


# ---------------------------------------------------------------------------
# idle motion from a single still
# ---------------------------------------------------------------------------


static func _shift(img: Image, d: Vector2i) -> Image:
	var out := Image.create_empty(img.get_width(), img.get_height(), false, Image.FORMAT_RGBA8)
	out.blit_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), d)
	return out


static func _brighten(img: Image, amount: float) -> Image:
	var out := Image.new()
	out.copy_from(img)
	for y in out.get_height():
		for x in out.get_width():
			var c := out.get_pixel(x, y)
			if c.a > 0.0:
				out.set_pixel(x, y, Color(minf(1, c.r + amount), minf(1, c.g + amount), minf(1, c.b + amount), c.a))
	return out


## Shift only rows [y0, y1) horizontally (antenna / wing-tip flick).
static func _nudge_band(img: Image, y0: int, y1: int, dx: int) -> Image:
	var out := Image.new()
	out.copy_from(img)
	var w := img.get_width()
	var band := img.get_region(Rect2i(0, y0, w, y1 - y0))
	out.fill_rect(Rect2i(0, y0, w, y1 - y0), Color(0, 0, 0, 0))
	out.blit_rect(band, Rect2i(Vector2i.ZERO, band.get_size()), Vector2i(dx, y0))
	return out


## style: none | bob | float | sway | pulse | flutter
static func make_motion(base: Image, count: int, style := "bob") -> Array:
	var seq := []
	var used := base.get_used_rect()
	var top := used.position.y
	var band := maxi(2, used.size.y / 4)
	match style.to_lower():
		"bob":
			seq = [base, _shift(base, Vector2i(0, -1)), base, _shift(base, Vector2i(0, 1))]
		"float":
			seq = [base, _shift(base, Vector2i(0, -1)), _shift(base, Vector2i(0, -2)), _shift(base, Vector2i(0, -1))]
		"sway":
			seq = [base, _shift(base, Vector2i(1, 0)), base, _shift(base, Vector2i(-1, 0))]
		"pulse":
			seq = [base, _brighten(base, 0.09), _brighten(base, 0.16), _brighten(base, 0.07)]
		"flutter":
			seq = [
				base,
				_shift(base, Vector2i(0, -1)),
				_nudge_band(_shift(base, Vector2i(0, -1)), maxi(0, top - 1), mini(base.get_height(), top - 1 + band), 1),
				_shift(base, Vector2i(0, 0))
			]
		_:
			seq = [base]
	var out := []
	for i in maxi(1, count):
		var f := Image.new()
		f.copy_from(seq[i % seq.size()])
		out.append(f)
	return out


# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------


static func palette_search_dirs() -> PackedStringArray:
	var dirs := PackedStringArray(["user://Palettes"])
	var g = Engine.get_main_loop().root.get_node_or_null("/root/Global")
	if g and "data_directories" in g:
		for d in g.data_directories:
			dirs.append(str(d).path_join("Palettes"))
	dirs.append(OS.get_executable_path().get_base_dir().path_join("pixelorama_data/Palettes"))
	return dirs


## Resolves a palette by file path or by Pixelorama palette name ("DawnBringer 32").
static func resolve_palette_path(spec: String) -> String:
	spec = norm_path(spec)
	if FileAccess.file_exists(spec):
		return spec
	for d in palette_search_dirs():
		for ext in ["json", "gpl", "pal", "hex", "png"]:
			var p := d.path_join("%s.%s" % [spec, ext])
			if FileAccess.file_exists(p):
				return p
	return ""


static func load_palette_file(path: String) -> PackedColorArray:
	var cols := PackedColorArray()
	var ext := path.get_extension().to_lower()
	if is_image_path(path):
		var img := load_image(path)
		if img == null:
			return cols
		return unique_colors([img], 256)
	var text := FileAccess.get_file_as_string(path)
	if ext == "json":
		var data = JSON.parse_string(text)
		if typeof(data) != TYPE_DICTIONARY or not data.has("colors"):
			return cols
		var entries: Array = data.colors
		entries.sort_custom(func(a, b) -> bool: return to_int(a.get("index", 0)) < to_int(b.get("index", 0)))
		for e in entries:
			if typeof(e) == TYPE_DICTIONARY and e.has("color"):
				cols.append(parse_color(e.color))
		return cols
	var lines := text.split("\n")
	if ext == "pal":
		# JASC-PAL: header, version, count, then "r g b"
		for i in range(3, lines.size()):
			var p := lines[i].strip_edges().split(" ", false)
			if p.size() >= 3 and p[0].is_valid_int():
				cols.append(Color8(p[0].to_int(), p[1].to_int(), p[2].to_int()))
		return cols
	if ext == "hex" or ext == "txt":
		for l in lines:
			var s := l.strip_edges().trim_prefix("#")
			if s.length() >= 6 and Color.html_is_valid(s):
				cols.append(Color.html(s))
		return cols
	# GIMP .gpl (default)
	for l in lines:
		var s := l.strip_edges()
		if s.is_empty() or s.begins_with("#") or s.begins_with("GIMP") or s.contains(":"):
			continue
		var p := s.replace("\t", " ").split(" ", false)
		if p.size() >= 3 and p[0].is_valid_int() and p[1].is_valid_int() and p[2].is_valid_int():
			cols.append(Color8(p[0].to_int(), p[1].to_int(), p[2].to_int()))
	return cols


static func unique_colors(images: Array, limit := 256) -> PackedColorArray:
	var seen := {}
	var out := PackedColorArray()
	for img: Image in images:
		var d := img.get_data()
		var i := 0
		while i < d.size():
			if d[i + 3] >= 128:
				var k := (d[i] << 16) | (d[i + 1] << 8) | d[i + 2]
				if not seen.has(k):
					seen[k] = true
					out.append(Color8(d[i], d[i + 1], d[i + 2]))
					if out.size() > limit:
						return median_cut(images, limit)
			i += 4
	return out


## Median-cut palette from the opaque pixels of `images` (subsampled to ~40k px).
static func median_cut(images: Array, count: int) -> PackedColorArray:
	var px := PackedInt64Array()
	var total := 0
	for img: Image in images:
		total += img.get_width() * img.get_height()
	var step := maxi(1, total / 40000)
	var k := 0
	for img: Image in images:
		var d := img.get_data()
		var i := 0
		while i < d.size():
			if k % step == 0 and d[i + 3] >= 128:
				px.append((d[i] << 16) | (d[i + 1] << 8) | d[i + 2])
			k += 1
			i += 4
	var out := PackedColorArray()
	if px.is_empty():
		return out
	var boxes := [px]
	while boxes.size() < count:
		# split the box with the widest channel range (ties: most pixels)
		var best := -1
		var best_score := -1
		var best_ch := 0
		for bi in boxes.size():
			var b: PackedInt64Array = boxes[bi]
			if b.size() < 2:
				continue
			var mins := [255, 255, 255]
			var maxs := [0, 0, 0]
			for v in b:
				for ch in 3:
					var c := (v >> (16 - ch * 8)) & 0xFF
					mins[ch] = mini(mins[ch], c)
					maxs[ch] = maxi(maxs[ch], c)
			for ch in 3:
				var score: int = (maxs[ch] - mins[ch]) * 100000 + b.size()
				if maxs[ch] - mins[ch] > 0 and score > best_score:
					best_score = score
					best = bi
					best_ch = ch
		if best < 0:
			break
		var box: PackedInt64Array = boxes[best]
		var shift := 16 - best_ch * 8
		var keyed := PackedInt64Array()
		keyed.resize(box.size())
		for i in box.size():
			keyed[i] = (((box[i] >> shift) & 0xFF) << 24) | box[i]
		keyed.sort()
		var half := keyed.size() / 2
		var a := PackedInt64Array()
		var b2 := PackedInt64Array()
		for i in keyed.size():
			var v := keyed[i] & 0xFFFFFF
			if i < half:
				a.append(v)
			else:
				b2.append(v)
		boxes[best] = a
		boxes.append(b2)
	for b: PackedInt64Array in boxes:
		if b.is_empty():
			continue
		var sr := 0
		var sg := 0
		var sb := 0
		for v in b:
			sr += (v >> 16) & 0xFF
			sg += (v >> 8) & 0xFF
			sb += v & 0xFF
		out.append(Color8(sr / b.size(), sg / b.size(), sb / b.size()))
	return sort_by_luma(out)


static func sort_by_luma(cols: PackedColorArray) -> PackedColorArray:
	var arr := Array(cols)
	arr.sort_custom(func(a: Color, b: Color) -> bool: return a.get_luminance() < b.get_luminance())
	return PackedColorArray(arr)


static func _nearest(c: Color, pal: PackedColorArray) -> Color:
	# "redmean" weighted RGB distance: cheap and close to perceptual for small palettes
	var best := pal[0]
	var bd := INF
	var r1 := c.r8
	var g1 := c.g8
	var b1 := c.b8
	for p in pal:
		var rm := (r1 + p.r8) / 2.0
		var dr := r1 - p.r8
		var dg := g1 - p.g8
		var db := b1 - p.b8
		var d := (2.0 + rm / 256.0) * dr * dr + 4.0 * dg * dg + (2.0 + (255.0 - rm) / 256.0) * db * db
		if d < bd:
			bd = d
			best = p
	return best


## Maps every non-transparent pixel to its nearest palette colour (alpha kept).
static func quantize(img: Image, pal: PackedColorArray, cache := {}) -> void:
	if pal.is_empty():
		return
	for y in img.get_height():
		for x in img.get_width():
			var c := img.get_pixel(x, y)
			if c.a <= 0.0:
				continue
			var k := color_key(c)
			var m: Color
			if cache.has(k):
				m = cache[k]
			else:
				m = _nearest(c, pal)
				cache[k] = m
			img.set_pixel(x, y, Color(m.r, m.g, m.b, c.a))


static func write_gpl(pal: PackedColorArray, path: String, pal_name := "AAMT Sprite Forge") -> bool:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string("GIMP Palette\nName: %s\nColumns: 8\n#\n" % pal_name)
	for c in pal:
		f.store_string("%3d %3d %3d\t%s\n" % [c.r8, c.g8, c.b8, c.to_html(false)])
	f.close()
	return true


## Pixelorama palette JSON payload (same shape Palette.serialize() writes).
static func palette_dict(pal: PackedColorArray) -> Dictionary:
	var width := 8
	var height := maxi(1, int(ceil(pal.size() / 8.0)))
	var colors := []
	for i in pal.size():
		var c := pal[i]
		colors.append({"color": "(%s, %s, %s, %s)" % [c.r, c.g, c.b, c.a], "index": i})
	return {"comment": "AAMT Sprite Forge", "colors": colors, "width": width, "height": height}


## Embeds the palette in the project (shows up as a project palette in the GUI).
static func embed_palette(project, pal: PackedColorArray, pal_name: String) -> bool:
	if pal.is_empty() or not ("palettes" in project):
		return false
	var script = load("res://src/Palette/Palette.gd")
	if script == null:
		return false
	var p = script.new(pal_name, 8, maxi(1, int(ceil(pal.size() / 8.0))))
	if not p.has_method("deserialize"):
		return false
	p.deserialize(JSON.stringify(palette_dict(pal)))
	project.palettes[pal_name] = p
	if "project_current_palette_name" in project:
		project.project_current_palette_name = pal_name
	return true


# ---------------------------------------------------------------------------
# outline
# ---------------------------------------------------------------------------


## Returns an image containing ONLY the outline pixels (outer outline of `img`).
static func outline_only(img: Image, color: Color, diagonal := false) -> Image:
	var w := img.get_width()
	var h := img.get_height()
	var out := Image.create_empty(w, h, false, Image.FORMAT_RGBA8)
	var d := img.get_data()
	var dirs := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]
	if diagonal:
		dirs += [Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]
	for y in h:
		for x in w:
			if d[(y * w + x) * 4 + 3] > 0:
				continue
			for dv: Vector2i in dirs:
				var nx := x + dv.x
				var ny := y + dv.y
				if nx >= 0 and ny >= 0 and nx < w and ny < h and d[(ny * w + nx) * 4 + 3] > 0:
					out.set_pixel(x, y, color)
					break
	return out


static func darkest(pal: PackedColorArray, fallback := Color(0.08, 0.06, 0.1)) -> Color:
	if pal.is_empty():
		return fallback
	var best := pal[0]
	for c in pal:
		if c.get_luminance() < best.get_luminance():
			best = c
	return best


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------


## Accepts "idle:1-4:6:loop,fire:5-8:12" or [{"name","from","to","fps","mode"}].
## from/to are 1-based inclusive (Pixelorama convention).
static func parse_tags(v, frame_count: int, default_fps: float, default_name := "idle") -> Array:
	var out := []
	if v is Array:
		for t in v:
			if typeof(t) == TYPE_DICTIONARY:
				out.append({
					"name": str(t.get("name", default_name)),
					"from": to_int(t.get("from", 1), 1),
					"to": to_int(t.get("to", frame_count), frame_count),
					"fps": to_float(t.get("fps", default_fps), default_fps),
					"mode": str(t.get("mode", "loop")),
					"transition": str(t.get("transition", "")),
				})
			elif t is String:
				out.append_array(parse_tags(t, frame_count, default_fps, default_name))
	elif v is String and not v.strip_edges().is_empty():
		for chunk: String in str(v).split(",", false):
			var p := chunk.strip_edges().split(":")
			var t := {"name": p[0], "from": 1, "to": frame_count, "fps": default_fps, "mode": "loop", "transition": ""}
			if p.size() > 1 and not p[1].is_empty():
				var r := p[1].split("-")
				t.from = to_int(r[0], 1)
				t.to = to_int(r[1], t.from) if r.size() > 1 else t.from
			if p.size() > 2 and not p[2].is_empty():
				t.fps = to_float(p[2], default_fps)
			if p.size() > 3 and not p[3].is_empty():
				t.mode = p[3]
			if p.size() > 4:
				t.transition = p[4]
			out.append(t)
	if out.is_empty():
		out.append({"name": default_name, "from": 1, "to": frame_count, "fps": default_fps, "mode": "loop", "transition": ""})
	for t in out:
		t.from = clampi(t.from, 1, frame_count)
		t.to = clampi(t.to, t.from, frame_count)
		if t.fps <= 0:
			t.fps = default_fps
	return out


## Tags (with per-tag fps) read back from a Pixelorama project.
static func tags_from_project(project, default_name := "idle") -> Array:
	var out := []
	var base_fps: float = project.fps if project.fps > 0 else 8.0
	for t in project.animation_tags:
		var dur_sum := 0.0
		for i in range(t.from - 1, t.to):
			dur_sum += project.frames[i].duration
		var n: int = t.to - t.from + 1
		var mean_dur := dur_sum / maxf(1.0, n)
		out.append({
			"name": t.name, "from": t.from, "to": t.to,
			"fps": base_fps / maxf(0.0001, mean_dur), "mode": "loop", "transition": "",
			"cycle": dur_sum / base_fps,
		})
	if out.is_empty():
		var nf: int = project.frames.size()
		var dur_all := 0.0
		for f in project.frames:
			dur_all += f.duration
		out.append({"name": default_name, "from": 1, "to": nf, "fps": base_fps * nf / maxf(0.0001, dur_all), "mode": "loop", "transition": "", "cycle": dur_all / base_fps})
	return out


static func sanitize_tag(s: String) -> String:
	var out := ""
	for ch in s.strip_edges():
		out += ch if (ch.is_valid_identifier() or ch.is_valid_int() or ch == "_") else "_"
	return out if not out.is_empty() else "frame"


# ---------------------------------------------------------------------------
# Pixelorama project build / open / save
# ---------------------------------------------------------------------------


## layers: [{"name": String, "frames": [Image...]}] bottom -> top. All frames
## must already be `size`. tags: parse_tags() output. Returns the Project.
static func build_project(proj_name: String, size: Vector2i, layers: Array, tags: Array, base_fps: float):
	var frame_count := 0
	for ld in layers:
		frame_count = maxi(frame_count, ld.frames.size())
	var project := Project.new([], proj_name, size)
	project.fps = base_fps
	for li in layers.size():
		var layer := PixelLayer.new(project, str(layers[li].name))
		layer.index = li
		project.layers.append(layer)
	var frame_fps := []
	frame_fps.resize(frame_count)
	frame_fps.fill(base_fps)
	for t in tags:
		for i in range(t.from - 1, t.to):
			frame_fps[i] = t.fps
	for fi in frame_count:
		var frame := Frame.new()
		for li in layers.size():
			var frames: Array = layers[li].frames
			if fi < frames.size() and frames[fi] != null:
				var img: Image = frames[fi]
				img.convert(project.get_image_format())
				frame.cels.append(project.layers[li].new_cel_from_image(img))
			else:
				frame.cels.append(project.layers[li].new_empty_cel())
		frame.duration = base_fps / maxf(0.0001, float(frame_fps[fi]))
		project.frames.append(frame)
	var tag_objs: Array[AnimationTag] = []
	for i in tags.size():
		var t = tags[i]
		tag_objs.append(AnimationTag.new(t.name, TAG_COLORS[i % TAG_COLORS.size()], t.from, t.to))
	project.animation_tags = tag_objs
	if project.has_method("order_layers"):
		project.order_layers()
	project.current_layer = layers.size() - 1
	project.selected_cels = [[0, project.current_layer]]
	Global.projects.append(project)
	return project


## Snapshot of the config keys OpenSave touches, so CLI runs don't rewrite the
## user's recent-projects list / last directory.
static func config_snapshot() -> Dictionary:
	var cfg: ConfigFile = Global.config_cache
	var snap := {}
	for key in ["current_dir", "last_project_path", "recent_projects"]:
		snap[key] = cfg.get_value("data", key) if cfg.has_section_key("data", key) else null
	return snap


static func config_restore(snap: Dictionary) -> void:
	var cfg: ConfigFile = Global.config_cache
	for key in snap:
		if snap[key] == null:
			if cfg.has_section_key("data", key):
				cfg.erase_section_key("data", key)
		else:
			cfg.set_value("data", key, snap[key])
	cfg.save(Global.CONFIG_PATH)


static func save_pxo(project, path: String, keep_config := true) -> bool:
	path = norm_path(path)
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var snap := config_snapshot() if keep_config else {}
	var ok: bool = OpenSave.save_pxo_file(path, false, false, project)
	if keep_config:
		config_restore(snap)
	return ok and FileAccess.file_exists(path)


## Opens a .pxo as a new project tab and returns it (null on failure).
static func open_pxo(path: String, keep_config := true):
	path = norm_path(path)
	if not FileAccess.file_exists(path):
		return null
	var before: int = Global.projects.size()
	var snap := config_snapshot() if keep_config else {}
	OpenSave.open_pxo_file(path, false, false)
	if keep_config:
		config_restore(snap)
	if Global.projects.size() > before:
		return Global.projects[Global.projects.size() - 1]
	return null


static func pixel_layer_indices(project) -> Array:
	var out := []
	for i in project.layers.size():
		if project.layers[i] is PixelLayer:
			out.append(i)
	return out


## Canvas-space image of a cel (handles v1.2.4+ cel offsets when present).
static func cel_canvas_image(project, cel) -> Image:
	var src: Image = cel.get_image()
	var out := Image.create_empty(project.size.x, project.size.y, false, Image.FORMAT_RGBA8)
	if src == null or src.is_empty():
		return out
	var tmp := Image.new()
	tmp.copy_from(src)
	tmp.convert(Image.FORMAT_RGBA8)
	var off := Vector2i.ZERO
	if "offset" in cel:
		off = Vector2i(cel.offset)
	out.blit_rect(tmp, Rect2i(Vector2i.ZERO, tmp.get_size()), off)
	return out


## Normal-blend composite of the visible pixel layers of one frame.
static func composite_frame(project, frame_index: int) -> Image:
	var out := Image.create_empty(project.size.x, project.size.y, false, Image.FORMAT_RGBA8)
	var frame = project.frames[frame_index]
	for li in project.layers.size():
		var layer = project.layers[li]
		if not (layer is PixelLayer):
			continue
		if layer.has_method("is_visible_in_hierarchy") and not layer.is_visible_in_hierarchy():
			continue
		var cel = frame.cels[li]
		var img := cel_canvas_image(project, cel)
		var opacity: float = float(layer.opacity) * float(cel.opacity)
		if opacity < 0.999:
			var d := img.get_data()
			var i := 3
			while i < d.size():
				d[i] = int(d[i] * opacity)
				i += 4
			img.set_data(img.get_width(), img.get_height(), false, Image.FORMAT_RGBA8, d)
		out.blend_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), Vector2i.ZERO)
	return out


## Replaces a cel's pixels (canvas-sized image).
static func set_cel_image(project, frame_index: int, layer_index: int, img: Image) -> void:
	var cel = project.frames[frame_index].cels[layer_index]
	var ci = cel.get_image()
	img.convert(ci.get_format())
	if "offset" in cel:
		# v1.2.4+ cels may be cropped/offset; store a canvas-sized image at 0,0
		cel.offset = Vector2i.ZERO
	if ci.has_method("copy_from_custom"):
		ci.copy_from_custom(img, project.is_indexed())
	else:
		ci.copy_from(img)
	if cel.has_method("update_texture"):
		cel.update_texture()


## Adds a pixel layer at `index` with one image per frame (null = empty).
static func insert_layer(project, index: int, layer_name: String, images: Array) -> void:
	var layer := PixelLayer.new(project, layer_name)
	var cels := []
	for fi in project.frames.size():
		var img = images[fi] if fi < images.size() else null
		if img == null:
			cels.append(layer.new_empty_cel())
		else:
			(img as Image).convert(project.get_image_format())
			cels.append(layer.new_cel_from_image(img))
	project.add_layers([layer], PackedInt32Array([index]), [cels])
	for i in project.layers.size():
		project.layers[i].index = i
	if project.has_method("order_layers"):
		project.order_layers()


# ---------------------------------------------------------------------------
# Starbound export
# ---------------------------------------------------------------------------


## layout: "rows" (one row per tag; Starbound convention), "strip" (one row,
## timeline order), "grid" (timeline order wrapped at `columns`).
static func plan_sheet(project, tags: Array, layout := "rows", columns := 0) -> Dictionary:
	var n: int = project.frames.size()
	var tag_of := []
	tag_of.resize(n)
	tag_of.fill(-1)
	for ti in tags.size():
		for i in range(tags[ti].from - 1, tags[ti].to):
			if tag_of[i] == -1:
				tag_of[i] = ti
	var cells := []  # [{frame, col, row, name}]
	var counters := {}
	var name_of := func(fi: int) -> String:
		var tname := "frame" if tag_of[fi] == -1 else sanitize_tag(tags[tag_of[fi]].name)
		counters[tname] = counters.get(tname, 0) + 1
		return "%s.%d" % [tname, counters[tname]]
	var cols := 1
	var rows := 1
	match layout:
		"strip", "grid":
			cols = n if layout == "strip" or columns <= 0 else mini(columns, n)
			rows = int(ceil(float(n) / cols))
			for fi in n:
				cells.append({"frame": fi, "col": fi % cols, "row": fi / cols, "name": name_of.call(fi)})
		_:
			var row := 0
			cols = 1
			for ti in tags.size():
				var col := 0
				for i in range(tags[ti].from - 1, tags[ti].to):
					if tag_of[i] != ti:
						continue
					cells.append({"frame": i, "col": col, "row": row, "name": name_of.call(i)})
					col += 1
				cols = maxi(cols, col)
				if col > 0:
					row += 1
			var col := 0
			for fi in n:
				if tag_of[fi] == -1:
					cells.append({"frame": fi, "col": col, "row": row, "name": name_of.call(fi)})
					col += 1
			cols = maxi(cols, col)
			rows = row + (1 if col > 0 else 0)
	rows = maxi(1, rows)
	return {"cells": cells, "columns": cols, "rows": rows}


## Writes <sheet>.png, <sheet>.frames and (optionally) an .animation stub.
## opts: layout, columns, scale(int), frames(bool), animation(path|"" ), state_type,
##       part, image_ref, default_tag, outline(Color|null), outline_diagonal
static func export_starbound(project, sheet_path: String, tags: Array, opts: Dictionary) -> Dictionary:
	sheet_path = norm_path(sheet_path)
	if sheet_path.get_extension().to_lower() != "png":
		sheet_path += ".png"
	var layout := str(opts.get("layout", "rows")).to_lower()
	var scale := maxi(1, to_int(opts.get("scale", 1), 1))
	var plan := plan_sheet(project, tags, layout, to_int(opts.get("columns", 0)))
	var cell: Vector2i = project.size * scale
	var sheet := Image.create_empty(cell.x * plan.columns, cell.y * plan.rows, false, Image.FORMAT_RGBA8)
	var names := []
	for r in plan.rows:
		var row := []
		row.resize(plan.columns)
		row.fill(null)
		names.append(row)
	var composites := {}
	for c in plan.cells:
		var img: Image
		if composites.has(c.frame):
			img = composites[c.frame]
		else:
			img = composite_frame(project, c.frame)
			if scale > 1:
				img.resize(cell.x, cell.y, Image.INTERPOLATE_NEAREST)
			composites[c.frame] = img
		sheet.blit_rect(img, Rect2i(Vector2i.ZERO, cell), Vector2i(c.col * cell.x, c.row * cell.y))
		names[c.row][c.col] = c.name
	DirAccess.make_dir_recursive_absolute(sheet_path.get_base_dir())
	var err := sheet.save_png(sheet_path)
	if err != OK:
		return {"ok": false, "error": "save_png failed (%s) %s" % [error_string(err), sheet_path]}
	var result := {
		"ok": true, "sheet": sheet_path, "cell": [cell.x, cell.y],
		"grid": [plan.columns, plan.rows], "sheet_size": [sheet.get_width(), sheet.get_height()],
		"frame_names": [], "states": [],
	}
	for c in plan.cells:
		result.frame_names.append(c.name)
	var first_name: String = plan.cells[0].name if not plan.cells.is_empty() else "default"
	if to_bool(opts.get("frames", true), true):
		var aliases := {"default": first_name}
		for t in tags:
			var tn := sanitize_tag(t.name)
			if tn + ".1" in result.frame_names and not aliases.has(tn):
				aliases[tn] = tn + ".1"
		var frames_doc := {
			"frameGrid": {
				"size": [cell.x, cell.y],
				"dimensions": [plan.columns, plan.rows],
				"names": names,
			},
			"aliases": aliases,
		}
		var frames_path := sheet_path.get_basename() + ".frames"
		if not write_json(frames_path, frames_doc):
			return {"ok": false, "error": "cannot write " + frames_path}
		result["frames_file"] = frames_path
	var states := []
	for t in tags:
		var n: int = t.to - t.from + 1
		var cycle: float = t.get("cycle", n / maxf(0.0001, t.fps))
		var st := {"name": sanitize_tag(t.name), "frames": n, "fps": snappedf(t.fps, 0.001), "cycle": snappedf(cycle, 0.0001), "mode": str(t.get("mode", "loop"))}
		if str(t.get("transition", "")) != "":
			st["transition"] = t.transition
		states.append(st)
	result.states = states
	var anim_path := str(opts.get("animation", ""))
	if anim_path == "auto":
		anim_path = sheet_path.get_basename() + ".animation"
	if anim_path != "":
		anim_path = norm_path(anim_path)
		var image_ref := str(opts.get("image_ref", ""))
		if image_ref == "":
			image_ref = sheet_path.get_file()
		var state_type := str(opts.get("state_type", "body"))
		var part := str(opts.get("part", "body"))
		var st_states := {}
		var part_states := {}
		for s in states:
			var sd := {"frames": s.frames, "cycle": s.cycle, "mode": s.mode}
			if s.has("transition"):
				sd["transition"] = s.transition
			elif s.mode == "transition":
				sd["transition"] = states[0].name
			st_states[s.name] = sd
			part_states[s.name] = {"properties": {"image": "%s:%s.<frame>" % [image_ref, s.name]}}
		var anim := {
			"animatedParts": {
				"stateTypes": {state_type: {"default": states[0].name if not states.is_empty() else "idle", "states": st_states}},
				"parts": {part: {"properties": {"centered": true, "zLevel": 0, "offset": [0, 0]}, "partStates": {state_type: part_states}}},
			}
		}
		if not write_json(anim_path, anim):
			return {"ok": false, "error": "cannot write " + anim_path}
		result["animation_file"] = anim_path
	return result


static func write_json(path: String, data, indent := "  ") -> bool:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(data, indent, false) + "\n")
	f.close()
	return true


static func project_info(project) -> Dictionary:
	var layers := []
	for l in project.layers:
		layers.append({"name": l.name, "type": l.get_class_name() if l.has_method("get_class_name") else str(l.get_layer_type()), "visible": l.visible, "opacity": l.opacity})
	var tags := []
	for t in project.animation_tags:
		tags.append({"name": t.name, "from": t.from, "to": t.to})
	var durations := []
	for f in project.frames:
		durations.append(f.duration)
	return {
		"name": project.name, "size": [project.size.x, project.size.y], "frames": project.frames.size(),
		"fps": project.fps, "durations": durations, "layers": layers, "tags": tags,
	}


# ---------------------------------------------------------------------------
# candidates (SD outputs / Unity-derived frames) -> canvas-sized images
# ---------------------------------------------------------------------------


## opts: bg, bg_tol, bg_color, bg_lum, work_max, fit(bool), trim, margin, anchor,
##       resample, alpha_threshold, upscale
static func prepare_candidate(img: Image, size: Vector2i, opts: Dictionary, pal := PackedColorArray()) -> Image:
	var work := cap_working_size(img, to_int(opts.get("work_max", 512), 512))
	work = remove_background(
		work, str(opts.get("bg", "auto")), to_float(opts.get("bg_tol", 0.12), 0.12),
		opts.get("bg_color", null), to_float(opts.get("bg_lum", 0.70), 0.70)
	)
	var out: Image
	if to_bool(opts.get("fit", true), true):
		var fit_opts := opts.duplicate()
		if not fit_opts.has("margin"):
			fit_opts["margin"] = 0
		out = fit_frames([work], size, fit_opts).images[0]
	else:
		out = Image.create_empty(size.x, size.y, false, Image.FORMAT_RGBA8)
		out.blit_rect(work, Rect2i(Vector2i.ZERO, work.get_size()), (size - work.get_size()) / 2)
	if not pal.is_empty():
		quantize(out, pal)
	return out


## Appends a frame whose `layer_index` cel holds `img` (other layers empty).
static func append_frame(project, layer_index: int, img: Image, duration := 1.0) -> void:
	var frame := Frame.new()
	for li in project.layers.size():
		if li == layer_index and project.layers[li] is PixelLayer:
			img.convert(project.get_image_format())
			frame.cels.append(project.layers[li].new_cel_from_image(img))
		else:
			frame.cels.append(project.layers[li].new_empty_cel())
	frame.duration = duration
	project.add_frames([frame], PackedInt32Array([project.frames.size()]))
