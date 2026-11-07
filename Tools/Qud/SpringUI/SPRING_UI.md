# Arendeth Spring UI — shared Spring Molting list window

`D:\games\Ai assisted toolkit\Tools\Qud\SpringUI`

One generic modern-UI window, shipped as the library mod `Mods\Arendeth_SpringUI`, that Arendeth's other mods
use for their dense menus instead of console overlays or plain popups:

- **Mountwright** — Mount Anchoring (Ctrl+M: node list, anatomy header, per-node detail, Attach / Detach /
  Reassign / Info in the hotkey bar) and Mounted Orders (Ctrl+R: greyed rows carry their disable reason).
- **Broodmother Mutation** — every `PickOption` menu (birth type, instincts, commands, biomods, evolution, nests,
  brood-meals, maturity, level-up…) goes through `BroodmotherUI.PickOption`, a drop-in that opens the window.

Composition (per the mod's own instructions file): title, one status strip, optional header block, one
scrollable list, a detail pane, one button bar. Keyboard (arrows, letter hotkeys, Enter, Esc, bound command
keys for extra actions), mouse (hover highlights, click accepts, wheel scrolls) and controller (list → bar).

## What goes where

| Piece | Location |
|---|---|
| Library mod (window, row control, API, bundle loader, option) | `Mods\Arendeth_SpringUI\*.cs`, `Options.xml`, `manifest.json` |
| Layout spec (the source of the prefab) | `specs\springmenu.springui.json` + `themes\qud-dark.theme.json` |
| Pipeline (lint, preview, Unity build, install) | `New-QudSpringUI.ps1` / `qud_spring_ui.py` / `Editor\BuildQudUI.cs`, see [QUD_SPRING_UI_PIPELINE.md](QUD_SPRING_UI_PIPELINE.md) |
| Build shortcut | `Build-SpringUIBundle.bat` (= pipeline on the spec with `-Build -Install`) |
| Staged Unity project | `Tools\Output\QudSpringUI\_unity` (`-OpenProject` to inspect) |
| Bundles (output) | `Mods\Arendeth_SpringUI\Bundles\<platform>\arendeth_springui_<platform>` |

## Build

```bat
Build-SpringUIBundle.bat
```

That runs the Spring UI pipeline on `specs\springmenu.springui.json`: lint against the `springmenu` runtime contract,
inline the theme, render `Tools\Output\QudSpringUI\arendeth_springui\previews\SpringMenu.png`, build the prefab and
windows/osx/linux bundles with Unity 6000.0.77f1, install into the library mod. Options, spec format and the
preview-first workflow: [QUD_SPRING_UI_PIPELINE.md](QUD_SPRING_UI_PIPELINE.md).

## Using it from a mod

Add `"Arendeth_SpringUI": "*"` to the manifest's `Dependencies` and `LoadAfter`, then:

```csharp
using Arendeth.SpringUI;

// Drop-in for Popup.PickOption (falls back to the popup itself when the window is unavailable):
int pick = SpringMenu.PickOption("Title", Intro: "...", Options: options, AllowEscape: true);

// Full control (returns Unavailable when you must run your own fallback):
var req = new SpringMenuRequest { Title = "...", Status = "...", Header = "...", Intro = "...", AllowEscape = true };
req.Add("Row label", "muted second line", "detail pane text", tag);
req.Actions.Add(new SpringMenuAction("detach", "Detach", "CmdDelete"));   // Command = game input id → key glyph
SpringMenuResult r = SpringMenu.Show(req);
if (r.Unavailable) { /* legacy path */ } else if (r.Picked) { /* r.Index, r.ActionId */ }
```

Rules: option text "Label\nDescription" splits into label + muted secondary + detail; rows whose stripped text
starts/ends with `===` or `---` are section headers (not selectable). Index semantics match `Popup.PickOption`,
so existing `if (choice == cancelIndex)` logic keeps working.

## Editing the layout

Edit the spec, run the pipeline without `-Build` to see the PNG mock-up, then `-Build -Install`. Keep the object
names (lint checks them; `python -I qud_spring_ui.py contract springmenu` lists them). Text objects stay empty; the
runtime adds TextMeshPro + UITextSkin. `Accent*` images take the caller's accent color (`SpringMenuRequest.Accent`).

## Troubleshooting

Player.log lines start with `[Arendeth Spring UI]`. "no bundle at …" → run the build. "bundle would not load" →
Unity version mismatch; delete `Tools\Output\SpringUI\_unity\Library` after switching editors. The option
**Arendeth Spring UI: Use popup menus instead of Spring-UI windows** forces the popup path for every dependent mod.
