extends RefCounted
## AAMT Sprite Forge headless runner.
##
##   Pixelorama.exe --headless -- spriteforge cmd=<cmd> key=value ... [result=<file.json>]
##   Pixelorama.exe --headless -- spriteforge job=<jobs.json> [result=<file.json>]
##
## User args must NOT start with "-" (Pixelorama quits on unknown options) and
## must not be bare existing file paths (Pixelorama would open them), hence key=value.
## Commands: create | apply | export | info | palette | batch (job file)
## Exit codes: 0 ok, 1 a job failed, 2 bad arguments / unreadable job file.
## Output: one stdout line "AAMT_SF_RESULT {json}" + the same JSON in result=<file>.

const Forge := preload("res://src/Extensions/AAMTSpriteForge/Forge.gd")
const COMMANDS := ["create", "apply", "import", "export", "render", "ai", "info", "palette", "batch", "selftest"]
const DEFAULT_HELPER := "D:/games/Ai assisted toolkit/Tools/Pixelorama/extensions/AAMTSpriteForge/tools/sf_ai_assist.py"
const LIST_SPLIT := ";"


static func parse_args(args: PackedStringArray) -> Dictionary:
	var kv := {}
	var started := false
	for a in args:
		if not started:
			started = a == "spriteforge"
			continue
		var eq := a.find("=")
		if eq > 0:
			kv[a.substr(0, eq).strip_edges().to_lower().replace("-", "_")] = a.substr(eq + 1)
		elif a in COMMANDS and not kv.has("cmd"):
			kv["cmd"] = a
	return kv


static func run(args: PackedStringArray) -> Dictionary:
	var t0 := Time.get_ticks_msec()
	var kv := parse_args(args)
	var out := {
		"ok": false, "tool": Forge.EXT_NAME, "version": Forge.VERSION,
		"pixelorama": str(Global.current_version), "api": ExtensionsApi.get_api_version(),
		"jobs": [],
	}
	var code := 0
	var jobs := []
	var defaults := {}
	if kv.has("job"):
		var path := Forge.norm_path(kv.job)
		var text := FileAccess.get_file_as_string(path)
		var data = JSON.parse_string(text) if text != "" else null
		if data == null:
			out["error"] = "cannot read/parse job file: " + path
			return _finish(out, 2, kv, t0)
		if typeof(data) == TYPE_DICTIONARY and data.has("jobs"):
			jobs = data.jobs
			defaults = data.get("defaults", {})
		elif typeof(data) == TYPE_ARRAY:
			jobs = data
		elif typeof(data) == TYPE_DICTIONARY:
			jobs = [data]
		# CLI key=values (other than job/result) act as defaults for every job
		for k in kv:
			if k not in ["job", "result", "cmd"]:
				defaults[k] = kv[k]
	else:
		if not kv.has("cmd"):
			out["error"] = "missing cmd= (one of %s) or job=<file.json>" % [", ".join(COMMANDS)]
			out["usage"] = "Pixelorama.exe --headless -- spriteforge cmd=create source=<png> cell=32x32 frames=4 tags=idle:1-4:6 palette=auto pxo=<out.pxo> sheet=<out.png> result=<res.json>"
			return _finish(out, 2, kv, t0)
		jobs = [kv]
	for i in jobs.size():
		var job: Dictionary = defaults.duplicate()
		if typeof(jobs[i]) == TYPE_DICTIONARY:
			job.merge(jobs[i], true)
		job["_index"] = i
		var jt := Time.get_ticks_msec()
		var r = run_job(job)
		if typeof(r) != TYPE_DICTIONARY:
			r = {"ok": false, "error": "script error inside job (see %APPDATA%/pixelorama/logs/godot.log)"}
		r["id"] = str(job.get("id", r.get("id", "job%d" % i)))
		r["ms"] = Time.get_ticks_msec() - jt
		out.jobs.append(r)
		if not r.get("ok", false):
			code = 1
	out.ok = code == 0
	return _finish(out, code, kv, t0)


static func _finish(out: Dictionary, code: int, kv: Dictionary, t0: int) -> Dictionary:
	out["exit_code"] = code
	out["ms"] = Time.get_ticks_msec() - t0
	if kv.has("result"):
		Forge.write_json(Forge.norm_path(kv.result), out)
	print("AAMT_SF_RESULT " + JSON.stringify(out, "", false))
	return out


static func _list(v) -> PackedStringArray:
	var out := PackedStringArray()
	if v == null:
		return out
	if v is Array or v is PackedStringArray:
		for x in v:
			out.append(Forge.norm_path(x))
	else:
		for x in str(v).split(LIST_SPLIT, false):
			out.append(Forge.norm_path(x))
	return out


static func _src_type(job: Dictionary, src: String) -> String:
	var t := str(job.get("type", "")).to_lower()
	if t != "":
		return t
	if DirAccess.dir_exists_absolute(src):
		return "frames"
	var ext := src.get_extension().to_lower()
	if ext == "pxo":
		return "pxo"
	if job.has("grid") or job.has("frame") or job.has("frames_json"):
		return "sheet"
	if FileAccess.file_exists(src.get_basename() + ".frames"):
		return "sheet"
	return "still"


## Loads source images (+ optional tags derived from a Starbound .frames file).
static func _load_source(job: Dictionary, src: String, type: String, warnings: Array) -> Dictionary:
	var images := []
	var tags_from_frames := []
	match type:
		"still":
			var img := Forge.load_image(src)
			if img == null:
				return {"error": "cannot load still: " + src}
			images.append(img)
		"frames":
			var files := PackedStringArray()
			if DirAccess.dir_exists_absolute(src):
				files = Forge.list_images(src, str(job.get("glob", "*")))
			else:
				files = _list(src)
			for f in files:
				var img := Forge.load_image(f)
				if img == null:
					warnings.append("skipped unreadable frame " + f)
					continue
				images.append(img)
			if images.is_empty():
				return {"error": "no frame images found in " + src}
			# frames of different size: pad to the largest, bottom-centre
			var mx := Vector2i.ZERO
			for img: Image in images:
				mx = Vector2i(maxi(mx.x, img.get_width()), maxi(mx.y, img.get_height()))
			for i in images.size():
				var img: Image = images[i]
				if img.get_size() != mx:
					var pad := Image.create_empty(mx.x, mx.y, false, Image.FORMAT_RGBA8)
					pad.blit_rect(img, Rect2i(Vector2i.ZERO, img.get_size()), Vector2i((mx.x - img.get_width()) / 2, mx.y - img.get_height()))
					images[i] = pad
		"sheet":
			var sheet := Forge.load_image(src)
			if sheet == null:
				return {"error": "cannot load sheet: " + src}
			var fsize := Forge.to_size(job.get("frame", null))
			var grid := Forge.to_size(job.get("grid", null))
			var names := []
			var fj := str(job.get("frames_json", ""))
			if fj == "" and FileAccess.file_exists(src.get_basename() + ".frames"):
				fj = src.get_basename() + ".frames"
			if fj != "" and fsize == Vector2i.ZERO and grid == Vector2i.ZERO:
				var doc = JSON.parse_string(FileAccess.get_file_as_string(Forge.norm_path(fj)))
				if typeof(doc) == TYPE_DICTIONARY and doc.has("frameGrid"):
					var fg: Dictionary = doc.frameGrid
					fsize = Forge.to_size(fg.get("size"))
					grid = Forge.to_size(fg.get("dimensions"))
					names = fg.get("names", [])
			if grid == Vector2i.ZERO and fsize != Vector2i.ZERO:
				grid = Vector2i(sheet.get_width() / fsize.x, sheet.get_height() / fsize.y)
			if fsize == Vector2i.ZERO and grid != Vector2i.ZERO:
				fsize = Vector2i(sheet.get_width() / grid.x, sheet.get_height() / grid.y)
			if fsize == Vector2i.ZERO:
				# horizontal strip of square cells
				fsize = Vector2i(sheet.get_height(), sheet.get_height())
				grid = Vector2i(maxi(1, sheet.get_width() / fsize.x), 1)
			var skip_empty := Forge.to_bool(job.get("skip_empty", true), true)
			var tag_order := []
			var tag_ranges := {}
			for row in grid.y:
				for col in grid.x:
					var nm = null
					if row < names.size() and typeof(names[row]) == TYPE_ARRAY and col < names[row].size():
						nm = names[row][col]
					var cell := sheet.get_region(Rect2i(col * fsize.x, row * fsize.y, fsize.x, fsize.y))
					if not names.is_empty() and nm == null:
						continue
					if names.is_empty() and skip_empty and cell.get_used_rect().size == Vector2i.ZERO:
						continue
					images.append(cell)
					if nm != null:
						var s := str(nm)
						var tag := s.get_basename() if s.get_extension().is_valid_int() else s
						if not tag_ranges.has(tag):
							tag_order.append(tag)
							tag_ranges[tag] = [images.size(), images.size()]
						tag_ranges[tag][1] = images.size()
			for tg in tag_order:
				tags_from_frames.append({"name": tg, "from": tag_ranges[tg][0], "to": tag_ranges[tg][1]})
			if images.is_empty():
				return {"error": "sheet produced no frames (frame=%s grid=%s)" % [fsize, grid]}
		_:
			return {"error": "unknown source type: " + type}
	return {"images": images, "tags": tags_from_frames}


static func _resolve_palette(job: Dictionary, frames: Array, warnings: Array) -> Dictionary:
	var spec := str(job.get("palette", "")).strip_edges()
	var colors := Forge.to_int(job.get("colors", 16), 16)
	if spec == "" or spec.to_lower() == "none":
		return {"colors": PackedColorArray(), "source": "none"}
	if spec.to_lower() == "auto" or spec.to_lower() == "source":
		return {"colors": Forge.median_cut(frames, colors), "source": "sampled from source (%d)" % colors}
	if spec.to_lower().begins_with("sample:") or job.has("palette_sample"):
		var paths := _list(job.get("palette_sample", spec.substr(7)))
		var refs := []
		for p in paths:
			var files := Forge.list_images(p) if DirAccess.dir_exists_absolute(p) else PackedStringArray([p])
			for f in files:
				var img := Forge.load_image(f)
				if img == null:
					warnings.append("palette ref unreadable: " + f)
					continue
				img = Forge.cap_working_size(img, 256)
				refs.append(Forge.remove_background(img, str(job.get("bg", "auto"))))
		if refs.is_empty():
			return {"error": "no readable palette reference images"}
		return {"colors": Forge.median_cut(refs, colors), "source": "sampled from %d reference image(s)" % refs.size()}
	var path := Forge.resolve_palette_path(spec)
	if path == "":
		return {"error": "palette not found (file or Pixelorama palette name): " + spec}
	var cols := Forge.load_palette_file(path)
	if cols.is_empty():
		return {"error": "palette has no colours: " + path}
	return {"colors": cols, "source": path}


static func _palette_summary(pal: PackedColorArray, source: String) -> Dictionary:
	var hexes := []
	for c in pal:
		hexes.append(Forge.color_hex(c))
	return {"count": pal.size(), "source": source, "colors": hexes}


static func run_job(job: Dictionary) -> Dictionary:
	var cmd := str(job.get("cmd", "create")).to_lower()
	var warnings := []
	var res := {"ok": false, "cmd": cmd, "outputs": {}, "warnings": warnings}
	if cmd == "selftest":
		var scripts := {}
		for s in ["Forge.gd", "Cli.gd", "Main.gd", "SpriteForgePanel.gd"]:
			var sc = load("res://src/Extensions/AAMTSpriteForge/" + s)
			scripts[s] = sc != null and sc.can_instantiate()
		res["scripts"] = scripts
		res["palette_dirs"] = Forge.palette_search_dirs()
		res.ok = not (false in scripts.values())
		return res
	if cmd == "palette":
		return _job_palette(job, res)
	var src := Forge.norm_path(job.get("source", job.get("input", "")))
	if src == "":
		res["error"] = "source= is required"
		return res
	var type := _src_type(job, src)
	res["type"] = type
	if cmd in ["apply", "import", "export", "render", "ai", "info"] and type != "pxo":
		res["error"] = "%s needs a .pxo source" % cmd
		return res
	var fps := Forge.to_float(job.get("fps", 0), 0.0)
	var project = null
	var tags := []
	var pal := PackedColorArray()
	var pal_info := {}
	if type == "pxo":
		project = Forge.open_pxo(src)
		if project == null:
			res["error"] = "cannot open pxo: " + src
			return res
		if job.has("tags"):
			var dfps: float = fps if fps > 0 else float(project.fps)
			tags = Forge.parse_tags(job.tags, project.frames.size(), dfps, str(job.get("default_tag", "idle")))
			_apply_tags(project, tags, fps)
		if cmd != "import" and (cmd == "apply" or job.has("palette") or job.has("outline")):
			var r := _ops_on_project(job, project, warnings)
			if r.has("error"):
				res["error"] = r.error
				return res
			pal = r.get("palette", PackedColorArray())
			pal_info = r.get("palette_info", {})
		if cmd == "render":
			var rr := _job_render(job, project)
			if rr.has("error"):
				res["error"] = rr.error
				return res
			res.outputs["frames"] = rr.files
			res["project"] = Forge.project_info(project)
			res.ok = true
			return res
		if cmd == "ai":
			var ar := _job_ai(job, project, warnings)
			if ar.has("error"):
				res["error"] = ar.error
				res["ai"] = ar.get("ai", {})
				return res
			res["ai"] = ar.ai
		if cmd == "import":
			var ir := _job_import(job, project, warnings)
			if ir.has("error"):
				res["error"] = ir.error
				return res
			res["imported"] = ir.imported
	else:
		var loaded := _load_source(job, src, type, warnings)
		if loaded.has("error"):
			res["error"] = loaded.error
			return res
		var built := _build_from_images(job, src, type, loaded, warnings)
		if built.has("error"):
			res["error"] = built.error
			return res
		project = built.project
		tags = built.tags
		pal = built.palette
		pal_info = built.palette_info
		res["fit"] = built.fit
	if not pal.is_empty():
		res["palette"] = pal_info
		var pal_out := str(job.get("palette_out", ""))
		if pal_out != "":
			pal_out = Forge.norm_path(pal_out)
			if pal_out.get_extension().to_lower() == "json":
				Forge.write_json(pal_out, Forge.palette_dict(pal), " ")
			else:
				Forge.write_gpl(pal, pal_out, str(job.get("id", "AAMT Sprite Forge")))
			res.outputs["palette"] = pal_out
	# save
	var pxo_out := str(job.get("pxo", job.get("out_pxo", "")))
	if pxo_out == "" and cmd == "apply" and Forge.to_bool(job.get("in_place", false)):
		pxo_out = src
	if cmd == "import" and pxo_out == "" and Forge.to_bool(job.get("in_place", false)):
		pxo_out = src
	if cmd == "ai" and pxo_out == "" and Forge.to_bool(job.get("in_place", false)):
		pxo_out = src
	if cmd in ["apply", "import", "ai"] and pxo_out == "":
		res["error"] = "%s needs pxo=<out.pxo> or in_place=true" % cmd
		return res
	if pxo_out != "" and cmd != "info" and cmd != "export":
		pxo_out = Forge.norm_path(pxo_out)
		if not Forge.save_pxo(project, pxo_out):
			res["error"] = "failed to save " + pxo_out
			return res
		res.outputs["pxo"] = pxo_out
	# export
	var sheet := str(job.get("sheet", job.get("out", "") if cmd == "export" else ""))
	if sheet != "":
		if tags.is_empty():
			tags = Forge.tags_from_project(project, str(job.get("default_tag", "idle")))
		var ex := Forge.export_starbound(project, sheet, tags, {
			"layout": job.get("layout", "rows"), "columns": job.get("columns", 0),
			"scale": job.get("scale", 1), "frames": job.get("frames_file", true),
			"animation": job.get("animation", ""), "state_type": job.get("state_type", "body"),
			"part": job.get("part", "body"), "image_ref": job.get("image_ref", ""),
		})
		if not ex.get("ok", false):
			res["error"] = ex.get("error", "export failed")
			return res
		res["export"] = ex
		res.outputs["sheet"] = ex.sheet
		if ex.has("frames_file"):
			res.outputs["frames"] = ex.frames_file
		if ex.has("animation_file"):
			res.outputs["animation"] = ex.animation_file
	elif cmd == "export":
		res["error"] = "export needs sheet=<out.png>"
		return res
	res["project"] = Forge.project_info(project)
	res.ok = true
	return res


static func _apply_tags(project, tags: Array, fps: float) -> void:
	var base := fps
	if base <= 0:
		for t in tags:
			base = maxf(base, t.fps)
	if base <= 0:
		base = project.fps
	project.fps = base
	var tag_objs: Array[AnimationTag] = []
	for i in tags.size():
		var t = tags[i]
		tag_objs.append(AnimationTag.new(t.name, Forge.TAG_COLORS[i % Forge.TAG_COLORS.size()], t.from, t.to))
		for fi in range(t.from - 1, t.to):
			project.frames[fi].duration = base / maxf(0.0001, t.fps)
	project.animation_tags = tag_objs


## palette + outline on an existing project (all pixel layers / composite outline)
static func _ops_on_project(job: Dictionary, project, warnings: Array) -> Dictionary:
	var out := {}
	var layers := Forge.pixel_layer_indices(project)
	if job.has("palette") and str(job.palette) != "" and str(job.palette).to_lower() != "none":
		var comps := []
		for fi in project.frames.size():
			comps.append(Forge.composite_frame(project, fi))
		var pr := _resolve_palette(job, comps, warnings)
		if pr.has("error"):
			return {"error": pr.error}
		var pal: PackedColorArray = pr.colors
		var cache := {}
		var all_layers := Forge.to_bool(job.get("all_layers", false))
		for fi in project.frames.size():
			for li in layers:
				if not all_layers and not project.layers[li].visible:
					continue  # keep hidden reference layers (e.g. "Source (unpaletted)") untouched
				var img := Forge.cel_canvas_image(project, project.frames[fi].cels[li])
				Forge.quantize(img, pal, cache)
				Forge.set_cel_image(project, fi, li, img)
		out["palette"] = pal
		out["palette_info"] = _palette_summary(pal, pr.source)
		if Forge.to_bool(job.get("embed_palette", true), true):
			Forge.embed_palette(project, pal, str(job.get("palette_name", "AAMT " + str(project.name))))
	var oc := str(job.get("outline", "")).strip_edges()
	if oc != "" and oc.to_lower() != "none" and oc.to_lower() != "false":
		var col := Forge.darkest(out.get("palette", PackedColorArray())) if oc.to_lower() in ["auto", "true"] else Forge.parse_color(oc)
		var imgs := []
		for fi in project.frames.size():
			imgs.append(Forge.outline_only(Forge.composite_frame(project, fi), col, Forge.to_bool(job.get("outline_diagonal", false))))
		Forge.insert_layer(project, 0, "Outline", imgs)
	return out


static func _build_from_images(job: Dictionary, src: String, type: String, loaded: Dictionary, warnings: Array) -> Dictionary:
	var images: Array = loaded.images
	var bg := str(job.get("bg", "auto"))
	var work_max := Forge.to_int(job.get("work_max", 512), 512)
	for i in images.size():
		var img: Image = Forge.cap_working_size(images[i], work_max)
		images[i] = Forge.remove_background(img, bg, Forge.to_float(job.get("bg_tol", 0.12), 0.12), job.get("bg_color", null), Forge.to_float(job.get("bg_lum", 0.70), 0.70))
	var first: Image = images[0]
	var cell := Forge.to_size(job.get("cell", job.get("size", null)))
	if cell == Vector2i.ZERO:
		var used := Forge.union_used_rect(images)
		var s := used.size if used.size != Vector2i.ZERO else first.get_size()
		if maxi(s.x, s.y) <= 128:
			cell = Vector2i(int(ceil(s.x / 8.0)) * 8, int(ceil(s.y / 8.0)) * 8)
		else:
			cell = Vector2i(64, 64)
			warnings.append("cell= not given; source is large, defaulted to 64x64")
	var style := str(job.get("style", "")).to_lower()
	var count := Forge.to_int(job.get("frames", 0), 0)
	if type == "still":
		if count <= 0:
			count = 4 if style != "" and style != "none" else 1
		if style == "":
			style = "bob" if count > 1 else "none"
	var outline_spec := str(job.get("outline", "")).strip_edges().to_lower()
	var want_outline := outline_spec != "" and outline_spec != "none" and outline_spec != "false"
	var motion_pad := 0
	if type == "still":
		motion_pad = {"bob": 1, "sway": 1, "flutter": 1, "float": 2}.get(style, 0)
	var margin_default := (1 if want_outline else 0) + motion_pad
	var fit_opts := {
		"trim": job.get("trim", true), "margin": job.get("margin", margin_default),
		"anchor": job.get("anchor", "bottom"), "resample": job.get("resample", "box"),
		"alpha_threshold": job.get("alpha_threshold", 128), "upscale": job.get("upscale", false),
	}
	var fit := Forge.fit_frames(images, cell, fit_opts)
	var frames: Array = fit.images
	var source_frames := []
	for f: Image in frames:
		var c := Image.new()
		c.copy_from(f)
		source_frames.append(c)
	if type == "still":
		frames = Forge.make_motion(frames[0], count, style)
		var sf := []
		for i in frames.size():
			sf.append(source_frames[0])
		source_frames = sf
	# palette
	var pr := _resolve_palette(job, frames, warnings)
	if pr.has("error"):
		return {"error": pr.error}
	var pal: PackedColorArray = pr.colors
	if not pal.is_empty():
		var cache := {}
		for f: Image in frames:
			Forge.quantize(f, pal, cache)
	# outline
	var outline_imgs := []
	if want_outline:
		var col := Forge.darkest(pal) if outline_spec in ["auto", "true"] else Forge.parse_color(job.outline)
		for f: Image in frames:
			outline_imgs.append(Forge.outline_only(f, col, Forge.to_bool(job.get("outline_diagonal", false))))
	# tags / fps
	var dfps := Forge.to_float(job.get("fps", 8), 8.0)
	var tag_spec = job.get("tags", null)
	if tag_spec == null and not loaded.tags.is_empty():
		tag_spec = loaded.tags
	var tags := Forge.parse_tags(tag_spec if tag_spec != null else "", frames.size(), dfps, str(job.get("default_tag", "idle")))
	var base_fps := Forge.to_float(job.get("fps", 0), 0.0)
	if base_fps <= 0:
		for t in tags:
			base_fps = maxf(base_fps, t.fps)
	# layers bottom -> top
	var layers := []
	if Forge.to_bool(job.get("keep_source_layer", true), true):
		layers.append({"name": "Source (unpaletted)", "frames": source_frames, "hidden": true})
	if want_outline:
		if Forge.to_bool(job.get("outline_layer", true), true):
			layers.append({"name": "Outline", "frames": outline_imgs})
		else:
			for i in frames.size():
				var merged: Image = outline_imgs[i]
				merged.blend_rect(frames[i], Rect2i(Vector2i.ZERO, cell), Vector2i.ZERO)
				frames[i] = merged
	layers.append({"name": "Sprite", "frames": frames})
	var pname := str(job.get("id", job.get("name", "")))
	if pname == "":
		var pxo_name := str(job.get("pxo", ""))
		pname = pxo_name.get_file().get_basename() if pxo_name != "" else src.get_file().get_basename()
	var project = Forge.build_project(pname, cell, layers, tags, base_fps)
	for li in layers.size():
		if layers[li].get("hidden", false):
			project.layers[li].visible = false
	if not pal.is_empty() and Forge.to_bool(job.get("embed_palette", true), true):
		Forge.embed_palette(project, pal, str(job.get("palette_name", "AAMT " + pname)))
	fit.erase("images")
	fit["cell"] = [cell.x, cell.y]
	fit["style"] = style
	return {
		"project": project, "tags": tags, "palette": pal,
		"palette_info": _palette_summary(pal, pr.get("source", "none")) if not pal.is_empty() else {},
		"fit": fit,
	}


static func _job_palette(job: Dictionary, res: Dictionary) -> Dictionary:
	var warnings: Array = res.warnings
	var spec := job.duplicate()
	if not spec.has("palette_sample") and spec.has("sample"):
		spec["palette_sample"] = spec.sample
	if not spec.has("palette"):
		spec["palette"] = "sample:"
	var pr := _resolve_palette(spec, [], warnings)
	if pr.has("error"):
		res["error"] = pr.error
		return res
	var pal: PackedColorArray = pr.colors
	var out_path := Forge.norm_path(job.get("out", job.get("palette_out", "")))
	if out_path != "":
		if out_path.get_extension().to_lower() == "json":
			Forge.write_json(out_path, Forge.palette_dict(pal), " ")
		else:
			Forge.write_gpl(pal, out_path, str(job.get("name", "AAMT Sprite Forge")))
		res.outputs["palette"] = out_path
	res["palette"] = _palette_summary(pal, pr.source)
	res.ok = true
	return res


## Candidates (SD outputs, Unity-derived frames...) -> hidden layers on one frame,
## or appended frames, for hand-picking in the GUI.
static func _job_import(job: Dictionary, project, warnings: Array) -> Dictionary:
	var files := PackedStringArray()
	for p in _list(job.get("images", job.get("candidates", ""))):
		if DirAccess.dir_exists_absolute(p):
			files.append_array(Forge.list_images(p, str(job.get("glob", "*"))))
		else:
			files.append(p)
	if files.is_empty():
		return {"error": "import needs images=<a.png;b.png|folder>"}
	var pal := PackedColorArray()
	var pal_spec := str(job.get("palette", ""))
	if pal_spec != "" and pal_spec.to_lower() != "none":
		var pr := _resolve_palette(job, [], warnings) if pal_spec.to_lower() != "auto" else {"colors": PackedColorArray()}
		if pr.has("error"):
			return {"error": pr.error}
		pal = pr.colors
	var mode := str(job.get("as", "layers")).to_lower()
	var at_frame := clampi(Forge.to_int(job.get("at_frame", 1), 1), 1, project.frames.size()) - 1
	var visible := Forge.to_bool(job.get("candidates_visible", false))
	var imported := []
	for f in files:
		var img := Forge.load_image(f)
		if img == null:
			warnings.append("candidate unreadable: " + f)
			continue
		var prepared := Forge.prepare_candidate(img, project.size, job, pal)
		var label := "Cand %s" % f.get_file().get_basename()
		if mode == "frames":
			var target := Forge.to_int(job.get("layer", -1), -1)
			if target < 0:
				var pls := Forge.pixel_layer_indices(project)
				target = pls[pls.size() - 1]
			Forge.append_frame(project, target, prepared)
			imported.append({"file": f, "frame": project.frames.size()})
		else:
			var imgs := []
			imgs.resize(project.frames.size())
			imgs[at_frame] = prepared
			Forge.insert_layer(project, project.layers.size(), label, imgs)
			project.layers[project.layers.size() - 1].visible = visible
			imported.append({"file": f, "layer": label, "frame": at_frame + 1})
	return {"imported": imported}



## 1-based "3", "2-4", "all" -> 0-based indices
static func _frame_list(spec, count: int) -> Array:
	var s := str(spec if spec != null else "all").strip_edges().to_lower()
	var out := []
	if s == "" or s == "all":
		return range(count)
	for part in s.split(",", false):
		var r := part.split("-")
		var a := clampi(Forge.to_int(r[0], 1), 1, count)
		var b := clampi(Forge.to_int(r[1], a), a, count) if r.size() > 1 else a
		for i in range(a, b + 1):
			out.append(i - 1)
	return out


## Composite PNG per frame (what Starbound will show), e.g. for previews / SD input.
static func _job_render(job: Dictionary, project) -> Dictionary:
	var out := Forge.norm_path(job.get("out", ""))
	if out == "":
		return {"error": "render needs out=<file.png|folder>"}
	var frames := _frame_list(job.get("frame", job.get("frames", "all")), project.frames.size())
	var scale := maxi(1, Forge.to_int(job.get("scale", 1), 1))
	var files := []
	for fi in frames:
		var img := Forge.composite_frame(project, fi)
		if scale > 1:
			img.resize(img.get_width() * scale, img.get_height() * scale, Image.INTERPOLATE_NEAREST)
		var path := out
		if out.get_extension().to_lower() != "png":
			path = out.path_join("%s_%d.png" % [str(project.name), fi + 1])
		elif frames.size() > 1:
			path = "%s_%d.png" % [out.get_basename(), fi + 1]
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		if img.save_png(path) != OK:
			return {"error": "cannot write " + path}
		files.append(path)
	return {"files": files}


## Opt-in SD img2img (uses the GPU): frame composite -> tools/sf_ai_assist.py (blocking)
## -> result imported as a new layer on that frame. Pass gpu_lock_held=true when the
## caller (pixelorama_client sf-ai) already holds the AAMT GPU lock.
static func _job_ai(job: Dictionary, project, warnings: Array) -> Dictionary:
	var helper := Forge.norm_path(job.get("helper", DEFAULT_HELPER))
	if not FileAccess.file_exists(helper):
		return {"error": "AI helper not found: " + helper}
	var frames := _frame_list(job.get("frame", "1"), project.frames.size())
	var work := ProjectSettings.globalize_path("user://spriteforge_ai")
	DirAccess.make_dir_recursive_absolute(work)
	var results := []
	for fi in frames:
		var stamp := "%d_%d" % [Time.get_ticks_usec(), fi + 1]
		var inp := work.path_join("in_%s.png" % stamp)
		var outp := Forge.norm_path(job.get("ai_out_dir", work)).path_join("ai_%s_%d.png" % [str(project.name), fi + 1])
		var status := work.path_join("status_%s.json" % stamp)
		Forge.composite_frame(project, fi).save_png(inp)
		var args := PackedStringArray([helper, "--in", inp, "--out", outp, "--status", status])
		for k in ["prompt", "negative", "strength", "steps", "guidance", "seed", "sd_size", "api", "min_vram_mb", "wait_idle"]:
			if job.has(k):
				args.append_array(["--" + k.replace("_", "-"), str(job[k])])
		var pal_spec := str(job.get("palette", ""))
		if pal_spec != "" and pal_spec.get_extension().to_lower() == "gpl":
			args.append_array(["--palette", Forge.norm_path(pal_spec)])
		if Forge.to_bool(job.get("gpu_lock_held", false)):
			args.append("--no-gpu-lock")
		var output := []
		var code := OS.execute(str(job.get("python", "python")), args, output, true)
		var st = JSON.parse_string(FileAccess.get_file_as_string(status)) if FileAccess.file_exists(status) else null
		if typeof(st) != TYPE_DICTIONARY or not st.get("ok", false):
			var msg: String = st.get("error", "") if typeof(st) == TYPE_DICTIONARY else ""
			if msg == "":
				msg = "helper exit %d: %s" % [code, "\n".join(output).right(400)]
			return {"error": "AI assist failed on frame %d: %s" % [fi + 1, msg], "ai": results}
		var img := Forge.load_image(outp)
		if img == null:
			return {"error": "AI result unreadable: " + outp, "ai": results}
		var imgs := []
		imgs.resize(project.frames.size())
		imgs[fi] = img
		var label := "AI img2img f%d" % (fi + 1)
		Forge.insert_layer(project, project.layers.size(), label, imgs)
		project.layers[project.layers.size() - 1].visible = Forge.to_bool(job.get("candidates_visible", false))
		st["frame"] = fi + 1
		st["layer"] = label
		results.append(st)
	return {"ai": results}