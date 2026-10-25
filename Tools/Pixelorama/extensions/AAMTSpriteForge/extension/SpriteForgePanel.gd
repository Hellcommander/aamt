extends ScrollContainer
## "Sprite Forge" dock panel: Starbound export, import candidates, palette/outline,
## and the opt-in SD img2img assist. Built in code (no .tscn) to stay editor-free.

const Forge := preload("res://src/Extensions/AAMTSpriteForge/Forge.gd")
const CFG := "AAMTSpriteForge"
const DEFAULT_HELPER := "D:/games/Ai assisted toolkit/Tools/Pixelorama/extensions/AAMTSpriteForge/tools/sf_ai_assist.py"

var _box: VBoxContainer
var _status: Label
# export
var _sheet_path: LineEdit
var _layout: OptionButton
var _columns: SpinBox
var _scale: SpinBox
var _anim: CheckBox
var _state_type: LineEdit
# import
var _fit: CheckBox
var _bg: CheckBox
var _snap_pal: CheckBox
# palette / outline
var _pal_path: LineEdit
var _colors: SpinBox
var _outline_color: ColorPickerButton
# ai
var _ai_enable: CheckBox
var _ai_prompt: LineEdit
var _ai_strength: SpinBox
var _ai_steps: SpinBox
var _ai_python: LineEdit
var _ai_helper: LineEdit
var _ai_button: Button
var _ai_timer: Timer
var _ai_job := {}

var _dialog: FileDialog
var _dialog_cb: Callable


func _ready() -> void:
	custom_minimum_size = Vector2(220, 120)
	horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_box = VBoxContainer.new()
	_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	add_child(_box)

	_header("Starbound export")
	_sheet_path = _path_row("Sheet .png", "", func(): _browse(FileDialog.FILE_MODE_SAVE_FILE, ["*.png"], func(p): _sheet_path.text = p))
	_layout = OptionButton.new()
	for item in ["rows (one row per tag)", "strip", "grid"]:
		_layout.add_item(item)
	_row("Layout", _layout)
	_columns = _spin(0, 64, 0)
	_row("Grid columns", _columns)
	_scale = _spin(1, 8, 1)
	_row("Scale", _scale)
	_anim = CheckBox.new()
	_anim.text = "Also write .animation stub"
	_box.add_child(_anim)
	_state_type = LineEdit.new()
	_state_type.text = "body"
	_row("State type / part", _state_type)
	_button("Export current project", export_current)

	_header("Import candidates")
	_fit = _check("Fit + pixelize to canvas", true)
	_bg = _check("Remove light background", true)
	_snap_pal = _check("Snap to palette below", false)
	_button("Add images as layers (current frame)...", func(): pick_candidates(true))
	_button("Add images as new frames...", func(): pick_candidates(false))

	_header("Palette & outline")
	_pal_path = _path_row("Palette", "", func(): _browse(FileDialog.FILE_MODE_OPEN_FILE, ["*.gpl", "*.pal", "*.hex", "*.json", "*.png"], func(p): _pal_path.text = p))
	_pal_path.placeholder_text = "file, Pixelorama palette name, or auto"
	_colors = _spin(2, 256, 16)
	_row("Colours (auto)", _colors)
	_button("Apply palette to visible cels", apply_palette_current)
	_outline_color = ColorPickerButton.new()
	_outline_color.color = Color(0.08, 0.05, 0.1)
	_outline_color.custom_minimum_size = Vector2(40, 24)
	_row("Outline colour", _outline_color)
	_button("Add outline layer", add_outline_current)

	_header("AI assist (SD img2img - uses GPU)")
	var cfg: ConfigFile = Global.config_cache
	_ai_enable = _check("Enable (opt-in; needs SD server :1338)", cfg.get_value(CFG, "ai_enabled", false))
	_ai_enable.toggled.connect(_on_ai_toggled)
	_ai_prompt = LineEdit.new()
	_ai_prompt.text = cfg.get_value(CFG, "ai_prompt", "pixel art game sprite, arcane magitech, clean shapes")
	_row("Prompt", _ai_prompt)
	_ai_strength = _spin(0.05, 1.0, cfg.get_value(CFG, "ai_strength", 0.45), 0.05)
	_row("Strength", _ai_strength)
	_ai_steps = _spin(4, 60, cfg.get_value(CFG, "ai_steps", 24))
	_row("Steps", _ai_steps)
	_ai_python = LineEdit.new()
	_ai_python.text = cfg.get_value(CFG, "python", "python")
	_row("Python", _ai_python)
	_ai_helper = LineEdit.new()
	_ai_helper.text = cfg.get_value(CFG, "helper", DEFAULT_HELPER)
	_row("Helper", _ai_helper)
	_ai_button = _button("Send current frame to img2img", ai_assist_current)
	_ai_button.disabled = not _ai_enable.button_pressed
	_ai_timer = Timer.new()
	_ai_timer.wait_time = 1.0
	_ai_timer.timeout.connect(_poll_ai)
	add_child(_ai_timer)

	_status = Label.new()
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_status.text = "AAMT Sprite Forge %s ready" % Forge.VERSION
	_box.add_child(_status)


# --- UI helpers -------------------------------------------------------------


func _header(text: String) -> void:
	var sep := HSeparator.new()
	_box.add_child(sep)
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", Color(0.95, 0.75, 0.45))
	_box.add_child(l)


func _row(label: String, control: Control) -> void:
	var h := HBoxContainer.new()
	var l := Label.new()
	l.text = label
	l.custom_minimum_size.x = 96
	h.add_child(l)
	control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(control)
	_box.add_child(h)


func _path_row(label: String, value: String, browse: Callable) -> LineEdit:
	var h := HBoxContainer.new()
	var l := Label.new()
	l.text = label
	l.custom_minimum_size.x = 96
	h.add_child(l)
	var e := LineEdit.new()
	e.text = value
	e.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(e)
	var b := Button.new()
	b.text = "..."
	b.pressed.connect(browse)
	h.add_child(b)
	_box.add_child(h)
	return e


func _spin(mn: float, mx: float, val: float, step := 1.0) -> SpinBox:
	var s := SpinBox.new()
	s.min_value = mn
	s.max_value = mx
	s.step = step
	s.value = val
	return s


func _check(text: String, on: bool) -> CheckBox:
	var c := CheckBox.new()
	c.text = text
	c.button_pressed = on
	_box.add_child(c)
	return c


func _button(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(cb)
	_box.add_child(b)
	return b


func _say(text: String) -> void:
	if is_instance_valid(_status):
		_status.text = text
	print("AAMT Sprite Forge: " + text)


func _browse(mode: int, filters: Array, cb: Callable) -> void:
	if not is_instance_valid(_dialog):
		_dialog = FileDialog.new()
		_dialog.access = FileDialog.ACCESS_FILESYSTEM
		_dialog.size = Vector2i(900, 600)
		_dialog.file_selected.connect(func(p): _dialog_done([p]))
		_dialog.files_selected.connect(func(ps): _dialog_done(Array(ps)))
		_dialog.canceled.connect(func(): ExtensionsApi.dialog.dialog_open(false))
		ExtensionsApi.dialog.get_dialogs_parent_node().add_child(_dialog)
	_dialog.file_mode = mode
	_dialog.filters = PackedStringArray(filters)
	_dialog_cb = cb
	var project = Global.current_project
	if project.save_path != "":
		_dialog.current_dir = project.save_path.get_base_dir()
	ExtensionsApi.dialog.dialog_open(true)
	_dialog.popup_centered()


func _dialog_done(paths: Array) -> void:
	ExtensionsApi.dialog.dialog_open(false)
	if paths.is_empty() or not _dialog_cb.is_valid():
		return
	if _dialog.file_mode == FileDialog.FILE_MODE_OPEN_FILES:
		_dialog_cb.call(paths)
	else:
		_dialog_cb.call(paths[0])


func _current_palette() -> PackedColorArray:
	var spec := _pal_path.text.strip_edges()
	if spec == "":
		return PackedColorArray()
	if spec.to_lower() == "auto":
		var comps := []
		var p = Global.current_project
		for fi in p.frames.size():
			comps.append(Forge.composite_frame(p, fi))
		return Forge.median_cut(comps, int(_colors.value))
	var path := Forge.resolve_palette_path(spec)
	return Forge.load_palette_file(path) if path != "" else PackedColorArray()


# --- actions ----------------------------------------------------------------


func export_current() -> void:
	var project = Global.current_project
	var path := _sheet_path.text.strip_edges()
	if path == "":
		var base: String = project.save_path.get_base_dir() if project.save_path != "" else str(project.export_profile.directory_path)
		path = base.path_join(str(project.name) + ".png")
		_sheet_path.text = path
	var tags := Forge.tags_from_project(project)
	var layouts := ["rows", "strip", "grid"]
	var st := _state_type.text.strip_edges()
	var r := Forge.export_starbound(project, path, tags, {
		"layout": layouts[_layout.selected], "columns": int(_columns.value), "scale": int(_scale.value),
		"animation": "auto" if _anim.button_pressed else "", "state_type": st if st != "" else "body",
		"part": st if st != "" else "body",
	})
	if r.get("ok", false):
		_say("Exported %s  grid %s  cell %s  frames %s" % [r.sheet.get_file(), r.grid, r.cell, ", ".join(r.frame_names)])
	else:
		_say("Export failed: " + str(r.get("error")))


func pick_candidates(as_layers: bool) -> void:
	_browse(FileDialog.FILE_MODE_OPEN_FILES, ["*.png, *.webp, *.jpg, *.jpeg ; Images"], func(paths): import_candidates(paths, as_layers))


func import_candidates(paths: Array, as_layers: bool) -> void:
	var project = Global.current_project
	var pal := _current_palette() if _snap_pal.button_pressed else PackedColorArray()
	var opts := {"fit": _fit.button_pressed, "bg": "auto" if _bg.button_pressed else "none"}
	var n := 0
	for p in paths:
		var img := Forge.load_image(str(p))
		if img == null:
			continue
		var prepared := Forge.prepare_candidate(img, project.size, opts, pal)
		if as_layers:
			OpenSave.open_image_as_new_layer(prepared, "Cand " + str(p).get_file().get_basename(), project.current_frame)
		else:
			OpenSave.open_image_as_new_frame(prepared, project.current_layer)
		n += 1
	_say("Imported %d candidate(s) as %s" % [n, "layers" if as_layers else "frames"])


## Undoable: quantize every visible pixel cel to the chosen palette.
func apply_palette_current() -> void:
	var project = Global.current_project
	var pal := _current_palette()
	if pal.is_empty():
		_say("Pick a palette file / name / 'auto' first")
		return
	var undo_data := {}
	var redo_data := {}
	var cache := {}
	project.undo_redo.create_action("Sprite Forge: apply palette")
	for fi in project.frames.size():
		for li in Forge.pixel_layer_indices(project):
			if not project.layers[li].visible:
				continue
			var cel = project.frames[fi].cels[li]
			var ci = cel.get_image()
			ci.add_data_to_dictionary(undo_data)
			var tmp := Image.new()
			tmp.copy_from(ci)
			tmp.convert(Image.FORMAT_RGBA8)
			Forge.quantize(tmp, pal, cache)
			tmp.convert(ci.get_format())
			ci.copy_from_custom(tmp, project.is_indexed())
			ci.add_data_to_dictionary(redo_data)
	project.deserialize_cel_undo_data(redo_data, undo_data)
	project.undo_redo.add_do_method(Global.undo_or_redo.bind(false))
	project.undo_redo.add_undo_method(Global.undo_or_redo.bind(true))
	project.undo_redo.commit_action()
	_say("Palette applied (%d colours)" % pal.size())


## Undoable: new bottom layer with the outer outline of each frame's composite.
func add_outline_current() -> void:
	var project = Global.current_project
	var layer := PixelLayer.new(project, "Outline")
	var cels := []
	for fi in project.frames.size():
		var o := Forge.outline_only(Forge.composite_frame(project, fi), _outline_color.color)
		o.convert(project.get_image_format())
		cels.append(layer.new_cel_from_image(o))
	project.undo_redo.create_action("Sprite Forge: add outline layer")
	project.undo_redo.add_do_method(project.add_layers.bind([layer], PackedInt32Array([0]), [cels]))
	project.undo_redo.add_do_method(project.change_cel.bind(project.current_frame, 0))
	project.undo_redo.add_do_method(Global.undo_or_redo.bind(false))
	project.undo_redo.add_undo_method(project.remove_layers.bind(PackedInt32Array([0])))
	project.undo_redo.add_undo_method(project.change_cel.bind(project.current_frame, project.current_layer))
	project.undo_redo.add_undo_method(Global.undo_or_redo.bind(true))
	project.undo_redo.commit_action()
	_say("Outline layer added")


func ai_assist_current() -> void:
	if not _ai_enable.button_pressed:
		_say("AI assist is off (opt-in)")
		return
	if not _ai_job.is_empty():
		_say("AI assist already running...")
		return
	var project = Global.current_project
	var cfg: ConfigFile = Global.config_cache
	cfg.set_value(CFG, "ai_prompt", _ai_prompt.text)
	cfg.set_value(CFG, "ai_strength", _ai_strength.value)
	cfg.set_value(CFG, "ai_steps", _ai_steps.value)
	cfg.set_value(CFG, "python", _ai_python.text)
	cfg.set_value(CFG, "helper", _ai_helper.text)
	cfg.save(Global.CONFIG_PATH)
	var work := ProjectSettings.globalize_path("user://spriteforge_ai")
	DirAccess.make_dir_recursive_absolute(work)
	var stamp := str(Time.get_unix_time_from_system()).replace(".", "_")
	var inp := work.path_join("in_%s.png" % stamp)
	var outp := work.path_join("out_%s.png" % stamp)
	var status := work.path_join("status_%s.json" % stamp)
	Forge.composite_frame(project, project.current_frame).save_png(inp)
	var args := PackedStringArray([
		_ai_helper.text, "--in", inp, "--out", outp, "--status", status,
		"--prompt", _ai_prompt.text, "--strength", str(_ai_strength.value), "--steps", str(int(_ai_steps.value)),
	])
	var pid := OS.create_process(_ai_python.text, args)
	if pid <= 0:
		_say("Could not start %s (check Python / helper path)" % _ai_python.text)
		return
	_ai_job = {"pid": pid, "out": outp, "status": status, "frame": project.current_frame, "project": project, "t": Time.get_ticks_msec()}
	_ai_button.disabled = true
	_ai_timer.start()
	_say("img2img running (GPU lock + SD server)...")


func _poll_ai() -> void:
	if _ai_job.is_empty():
		_ai_timer.stop()
		return
	if not FileAccess.file_exists(_ai_job.status):
		if not OS.is_process_running(_ai_job.pid):
			_finish_ai("AI helper exited without a status file")
		elif Time.get_ticks_msec() - int(_ai_job.t) > 1800000:
			_finish_ai("AI assist timed out (still running in background)")
		return
	var st = JSON.parse_string(FileAccess.get_file_as_string(_ai_job.status))
	if typeof(st) == TYPE_DICTIONARY and st.get("ok", false):
		var img := Forge.load_image(_ai_job.out)
		if img != null and _ai_job.project == Global.current_project:
			OpenSave.open_image_as_new_layer(img, "AI img2img", int(_ai_job.frame))
			_finish_ai("AI layer added (%ss)" % st.get("secs", "?"))
		else:
			_finish_ai("AI result saved to %s (project changed, not imported)" % _ai_job.out)
	else:
		_finish_ai("AI assist failed: %s" % (st.get("error", "bad status") if typeof(st) == TYPE_DICTIONARY else "bad status"))


func _on_ai_toggled(on: bool) -> void:
	var cfg: ConfigFile = Global.config_cache
	cfg.set_value(CFG, "ai_enabled", on)
	cfg.save(Global.CONFIG_PATH)
	if is_instance_valid(_ai_button):
		_ai_button.disabled = not on


func _finish_ai(msg: String) -> void:
	_ai_timer.stop()
	_ai_job = {}
	_ai_button.disabled = not _ai_enable.button_pressed
	_say(msg)
