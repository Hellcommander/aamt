extends Node
## AAMT Sprite Forge entry node (instantiated by Pixelorama's extension loader).
##
## Headless/CLI:  Pixelorama.exe --headless -- spriteforge cmd=... | job=...
##   runs Cli.gd synchronously inside _ready (so it also completes under Godot's
##   --quit, which stops after the first frame) and quits with its exit code.
## GUI: adds a "Sprite Forge" dock panel and two Project-menu entries.

const Cli := preload("res://src/Extensions/AAMTSpriteForge/Cli.gd")
const PANEL_PATH := "res://src/Extensions/AAMTSpriteForge/SpriteForgePanel.gd"


class MenuAction:
	extends RefCounted
	var callback: Callable

	func _init(cb: Callable) -> void:
		callback = cb

	func menu_item_clicked() -> void:
		callback.call()


var panel: Control
var _menu_ids := []
var _menu_actions := []


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if "spriteforge" in args:
		var out = Cli.run(args)
		var code := 3
		if typeof(out) == TYPE_DICTIONARY:
			code = int(out.get("exit_code", 1))
		else:
			print("AAMT_SF_RESULT {\"ok\": false, \"exit_code\": 3, \"error\": \"internal script error\"}")
		get_tree().quit(code)
		return
	if DisplayServer.get_name() == "headless":
		return
	_setup_gui()


func _setup_gui() -> void:
	var script = load(PANEL_PATH)
	if script == null:
		push_error("AAMT Sprite Forge: panel script failed to load")
		return
	panel = script.new()
	panel.name = "Sprite Forge"
	ExtensionsApi.panel.add_node_as_tab(panel)
	_add_menu("Sprite Forge: Export Starbound Sheet", func(): panel.export_current())
	_add_menu("Sprite Forge: Import Candidates as Layers...", func(): panel.pick_candidates(true))


func _add_menu(label: String, cb: Callable) -> void:
	var action := MenuAction.new(cb)
	_menu_actions.append(action)
	_menu_ids.append(ExtensionsApi.menu.add_menu_item(ExtensionsApi.menu.PROJECT, label, action))


func _exit_tree() -> void:
	for id in _menu_ids:
		ExtensionsApi.menu.remove_menu_item(ExtensionsApi.menu.PROJECT, id)
	_menu_ids.clear()
	if is_instance_valid(panel):
		ExtensionsApi.panel.remove_node_from_tab(panel)
