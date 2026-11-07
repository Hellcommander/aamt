# Conjoined Extended — Spring Molting UI picker

`D:\games\Ai assisted toolkit\Tools\Qud\ConjoinedUI`

The Conjoined mutation's mid-game creature picker used to be a legacy console screen
(`ScreenBuffer` drawn into the text overlay). Conjoined Extended 1.19 replaces it, on the
modern "Spring Molting" UI, with a real window: a tile grid you can drive with mouse, keyboard
or controller, a markup detail panel, search, and the game's own hotkey bar. The chargen
picker was already a modern window (`CategoryMenusScroller`) and is unchanged.

The window's layout is a Unity prefab shipped as an asset bundle. This folder builds it.

## What goes where

| Piece | Location | Notes |
|---|---|---|
| Layout spec (the source of the prefab) | `..\SpringUI\specs\conjoined_picker.springui.json` | Edit this, not the prefab. Theme `..\SpringUI\themes\qud-dark.theme.json`. |
| Pipeline | `..\SpringUI\New-QudSpringUI.ps1`, see [../SpringUI/QUD_SPRING_UI_PIPELINE.md](../SpringUI/QUD_SPRING_UI_PIPELINE.md) | Lint, PNG preview, Unity build, install. |
| Build shortcut | `Build-ConjoinedUIBundle.bat` / `.ps1` | Runs the pipeline on the picker spec with `-Build -Install`. |
| Staged Unity project | `Tools\Output\QudSpringUI\_unity` | Shared by all specs; `-OpenProject` to inspect. Not committed. |
| Bundles (output) | `Mods\Arendeth_Conjoined_Extended\Bundles\<platform>\conjoined_ui_<platform>` | windows always; osx/linux when those build modules are installed. |
| Runtime | `Mods\Arendeth_Conjoined_Extended\UI\*.cs` | `ConjoinedPickerBundle` (load), `ConjoinedPickerScreen` (window), `ConjoinedTileControl` (grid cell), `CreatureChoice` (data). |

## Build

```bat
Build-ConjoinedUIBundle.bat
```

Runs the Spring UI pipeline on `..\SpringUI\specs\conjoined_picker.springui.json`: lint against the
`conjoined_picker` runtime contract, PNG mock-up at `Tools\Output\QudSpringUI\conjoined_ui\previews\ConjoinedPicker.png`,
Unity build (6000.0.77f1), install into the mod's `Bundles`. Log: `Tools\Logs\QudSpringUI_conjoined_ui_<timestamp>.log`.

## Editing the layout

Edit the spec and rerun the pipeline (without `-Build` for a quick PNG check). Lint enforces the runtime's object
names (`python -I ..\SpringUI\qud_spring_ui.py contract conjoined_picker`). Text objects are empty RectTransforms;
the mod adds TextMeshPro + UITextSkin at runtime. The grid's column count is computed at runtime from the viewport
width and the GridLayoutGroup cell size, so resizing the panel or the cells just works. Do not add components
from the game's assemblies; the mod adds FrameworkScroller, FrameworkUnityScrollChild, UIThreeColorProperties,
FrameworkHoverable and FrameworkClickToAccept itself.

## How the runtime works

- `Patches\SelectorDetailPatches.cs` intercepts `ConjoinedMenu.Show`. On the modern UI, with the bundle present
  and the "legacy console picker" option off, it calls `ConjoinedPickerScreen.TryRunMidGamePicker`, otherwise the
  enhanced console picker runs as before.
- `ConjoinedPickerScreen` is a `SingletonWindowBase` tagged `[UIView("ConjoinedPicker", UICanvas: "ConjoinedPicker")]`.
  On first use it instantiates the prefab under the game's `UIManager`, registers it in `windowsByName`, and from then on
  `GameManager.PushGameView("ConjoinedPicker")` shows it exactly like a vanilla screen.
- The game thread blocks on the UI task (`NavigationController.SuspendContextWhile` + `Task.Result`), the same bridge
  the vanilla pick-object screen uses. The result is a list of blueprint names; the patch then calls
  `Conjoined.CreateCreature` / `SpawnCreature` per slot.
- Input: grid = `FrameworkScroller` with a dual-axis `ScrollContext` (left/right ±1, up/down ±columns); the hotkey bar
  reuses the vanilla `PickGameObjectScreen` menu-option prefab; `Cancel` undoes the last pick or clears the search;
  `CmdFilter` opens the search popup; `CmdChargenRandom` (if bound) picks randomly; Page Up/Down scroll the detail panel.
- Any failure (bundle missing, wrong Unity version, UI not initialised) logs one line
  `[Conjoined Extended] Spring-UI picker: ...` in Player.log and falls back to the console picker.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Player.log: `no bundle at ...Bundles\windows\conjoined_ui_windows` | Run the build; check `Tools\Logs`. |
| Player.log: `bundle would not load (built with a different Unity version...)` | Unity Hub editor version must equal the game's. Delete `Tools\Output\ConjoinedUI\_unity\Library` after switching editors. |
| Player.log: `prefab is missing required objects` (during build) | Something was renamed in the prefab; run **Validate picker prefab** in the editor. |
| Window shows but no tiles | The grid's `TileTemplate` must stay **active** inside the inactive `Templates` container (clones copy its active state). |
| Text invisible | Text objects must not carry a legacy `UnityEngine.UI.Text`; leave them empty for the runtime. |
