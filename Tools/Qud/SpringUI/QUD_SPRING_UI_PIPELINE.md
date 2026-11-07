# Qud Spring UI pipeline

`Tools\Qud\SpringUI` turns a small JSON layout spec into a **Spring Molting (modern UI) window prefab** for a
Caves of Qud mod: lint it offline, look at a PNG mock-up, build the prefab and per-platform asset bundles with the
game-matched Unity, and drop them into the mod. The mod's C# then wires the prefab by object name at runtime
(TextMeshPro + UITextSkin, FrameworkScroller rows / grids, UIThreeColorProperties tiles, the vanilla hotkey bar).

```
spec.springui.json
   │  qud_spring_ui.py generate            (python; no Unity)
   │     lint: schema, unique names, rects, layout groups, the runtime object-name contract
   ├─► <out>\<Prefab>.resolved.json        theme tokens inlined — what the Unity builder reads
   ├─► <out>\previews\<Prefab>.png         Pillow mock-up at the reference size (fonts/sizes approximate)
   ├─► <out>\contract.txt                  the names the runtime looks up
   ├─► <out>\manifest.json                 for the build / install steps
   │
   │  New-QudSpringUI.ps1 -Build           (Unity 6000.0.77f1 batch mode; Editor\BuildQudUI.cs reads the resolved spec)
   ├─► <out>\Bundles\windows\<bundle>_windows  (+ osx, linux when those build modules are installed)
   │
   │  qud_spring_ui.py install             (copies the bundles)
   └─► <mod>\Bundles\<platform>\<bundle>_<platform>
```

`<out>` is `Tools\Output\QudSpringUI\<bundle>` (gitignored) unless `-OutDir` says otherwise. The shared staged
Unity project lives at `Tools\Output\QudSpringUI\_unity`; generated prefabs land in its `Assets\QudUI`.

## Quick start

```powershell
cd Tools\Qud\SpringUI

# lint + resolve + preview (seconds, no Unity)
.\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json

# build the prefab + bundles with Unity and install into the mod (restart the game afterwards)
.\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json -Build -Install
.\New-QudSpringUI.ps1 -Spec specs\conjoined_picker.springui.json -Build -Install

# look at the generated prefab in the Unity editor (edit the spec, not the prefab, to keep changes)
.\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json -OpenProject
```

Each step on its own:

```powershell
python -I qud_spring_ui.py lint specs\springmenu.springui.json
python -I qud_spring_ui.py generate specs\springmenu.springui.json --preview
python -I qud_spring_ui.py preview specs\springmenu.springui.json --scale 1.5
python -I qud_spring_ui.py install ..\..\Output\QudSpringUI\arendeth_springui
python -I qud_spring_ui.py contract springmenu
python -I qud_spring_ui.py schema
```

`Build-SpringUIBundle.bat` and `..\ConjoinedUI\Build-ConjoinedUIBundle.bat` are thin wrappers that run the
pipeline with the right spec and `-Build -Install`.

## Shipped specs

| Spec | Prefab / bundle | Mod | Runtime |
|---|---|---|---|
| `specs\springmenu.springui.json` | `SpringMenu` / `arendeth_springui` | `Arendeth_SpringUI` (library used by Mountwright and Broodmother) | `SpringMenuWindow.cs` (`kind: springmenu`) |
| `specs\conjoined_picker.springui.json` | `ConjoinedPicker` / `conjoined_ui` | `Arendeth_Conjoined_Extended` | `UI\ConjoinedPickerScreen.cs` (`kind: conjoined_picker`) |

Themes: `themes\qud-dark.theme.json` (the game look, default) and `themes\biomutation.theme.json` (Broodmother
magenta/chitin, for a Broodmother-only window). The shared SpringMenu stays qud-dark and tints its `Accent*`
images at runtime with the caller's palette letter (`SpringMenuRequest.Accent`: Broodmother `'M'`, Mountwright `'C'`).

## The spec

`python -I qud_spring_ui.py schema` prints the full reference. The short version:

```json
{
  "mod": "Arendeth_SpringUI", "modFolder": "Arendeth_SpringUI",
  "bundle": "arendeth_springui", "prefab": "SpringMenu", "kind": "springmenu",
  "theme": "qud-dark", "reference": [1600, 900],
  "root": {
    "name": "SpringMenu", "type": "panel", "rect": {"stretch": [0, 0, 0, 0]}, "fill": "backdrop", "raycast": true,
    "children": [ ... ]
  }
}
```

Node types: `panel` (RectTransform + optional fill / border / layout group), `text` (empty; the runtime adds
TextMeshPro), `scroll` (ScrollRect with named `viewport` / `content` descendants), `image` (icon slot),
`template` (inactive container whose child is cloned at runtime). Rects: `stretch`, `anchors`, `top`, `bottom`,
`left`, `right`, `topStretch` (scroll content), `size` (fixed). Layout groups: `vertical`, `horizontal`, `grid`.
`element` is a LayoutElement, `fitter` a ContentSizeFitter, `mask` a RectMask2D. `text.sample` and `preview`
only affect the PNG mock-up.

## Rules the runtime relies on (lint enforces them per `kind`)

- Object names are unique and match the runtime contract (`contract <kind>` lists them).
- `scroll` nodes that a FrameworkScroller drives (list, grid, hotkey bar) carry an `element` (LayoutElement) and
  their content uses `topStretch` with a layout group (`vertical` list, `grid` tiles, `horizontal` bar).
- Text objects are empty `text` nodes.
- The template container is `active: false`; the template itself stays active (clones copy its state).
- `accent: true` images are named `Accent*` (springmenu kind only).

Adding a new window kind: add its runtime class in the mod (model it on `SpringMenuWindow.cs`), add the name list
to `CONTRACTS` in `qud_spring_ui.py`, write a spec with that `kind`.

## Requirements

| Step | Needs |
|---|---|
| lint / generate / install | Python 3.8+ |
| preview | Pillow (the toolkit's Python); uses `consola.ttf` when present |
| build | Unity matching the game (6000.0.77f1) via `Shared\UnityVersionResolver`; Windows build support (macOS / Linux for those bundles) |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `LINT ERROR: [springmenu] missing required object ...` | A contract name was renamed or dropped; `contract springmenu` lists them. |
| `QUDUI warning: scroll content '...' not found` (build log) | `scroll.content` must be a descendant of the scroll node. |
| Game log `bundle would not load` | Unity version mismatch; delete `Tools\Output\QudSpringUI\_unity\Library` after switching editors. |
| Window shows, rows missing | The template must stay `active: true` inside the inactive `Templates` container. |
| Text invisible in game | Leave `text` nodes empty; the runtime attaches the font, size and markup conversion. |
