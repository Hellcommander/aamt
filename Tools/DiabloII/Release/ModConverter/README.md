# D2R Mod Converter

Turns Diablo II: Resurrected **data mods** (mods that ship whole game files, such as
`<Name>.mpq\data\...` with `modinfo.json`) into **D2RMM mods**. Instead of replacing whole tables,
the converted mod only writes the cells, rows and strings the mod really changed, so it can be
stacked with other D2RMM mods and survives game patches much better.

The converter also updates converted mods when a new version of the original comes out, keeping the
settings you picked.

**The converter puts no conditions on the mods it makes**; they are yours to use, edit and share.
A converted mod still contains the original author's work, so before uploading a conversion of
someone else's mod, check that author's permissions. Mod authors are welcome to ship an official
D2RMM version of their own mod made with it. See `PERMISSIONS.md`.

## Requirements

| What | Needed for | Link |
|---|---|---|
| Windows 10/11 | everything | |
| Python 3.10 or newer | everything | https://www.python.org/downloads/windows/ (tick "Add python.exe to PATH") |
| Node.js (LTS) | every conversion (the window always runs the check) | https://nodejs.org/en/download |
| D2RMM 1.9 or newer | installing the converted mods | https://www.nexusmods.com/diablo2resurrected/mods/169 |
| D2RMM Custom (D2RLoader edition) | only mods that bring D2RLoader plugins (DLLs) | https://github.com/yinyin333333/d2rmm/releases |
| 7-Zip | only `.7z` / `.rar` downloads (`.zip` and folders work without it) | https://www.7-zip.org/ |
| numpy | only mods that ship compiled `.bin` tables (Rebirth-style) | `python -m pip install numpy` |

Diablo II: Resurrected must be installed (Steam or Battle.net). The converter only **reads** the
game's archive (through D2RMM's own `tools\CascLib.dll`); it never writes to the game folder.

## Install

1. Extract this zip anywhere, for example `Documents\D2R Mod Converter`.
2. Double-click **`Start-D2RModConverter.bat`**.
3. The first time, it looks for Python, the game and D2RMM by itself (the Steam / Battle.net install
   entries, and D2RMM in or beside the game folder). If it can't find one, it asks you to paste the
   folder. What it finds is remembered in `%LOCALAPPDATA%\D2RModAssets\paths.json`.
4. The converter opens in your browser (a local page on `http://127.0.0.1:8766`; nothing goes
   online). Close the console window to stop it.

## Converting a mod

1. In **Convert a mod**, pick the mod's download: a folder, a `.zip` / `.7z` / `.rar`, or a packed
   `.mpq`.
2. **Look inside** unpacks it into `<D2RMM>\converter-work\` (safe to delete later) and shows what the
   mod changes per feature, its D2RLoader plugins, and anything it can't convert.
3. Pick the options (below) and **Convert**. The mod goes into `<D2RMM>\mods\<name>` and is checked:
   the generated `mod.js` is run against the game's own files and must rebuild the mod's tables and
   strings exactly. The log ends with "0 differ" when it does.
4. In D2RMM: **Refresh List** (and **Plugins > Refresh** in D2RMM Custom when the mod had plugins),
   tick the mod, set its options, **Install Mods** with the game closed.

## What a converted mod has in its D2RMM settings

- **A switch per feature**: inventory, cube recipes, runewords, uniques and sets, affixes, item bases,
  drops, monsters, areas, skills, characters, vendors, interface, visuals. Tables everything depends on
  are "core" and always on.
- **A switch per D2RLoader plugin and patch** that the mod brings.
- **Load order**:
  - *Rows*: **Keep** (every game row stays at its number, the mod's new rows go at the end; works
    anywhere in the list) or **Rebuild** (the mod's own row order; put the mod at the top).
  - *Conflicts with mods above*: **This mod wins**, or **Mods above win** (this mod only changes what
    no earlier mod touched). The install log lists every clash either way.
  - *Files a mod above already put in*: **Overwrite** or **Keep**.
- **My mod list** / **Options**: only when you give the converter a rules file (see below).

## Converter options

| Option | Default | What it does |
|---|---|---|
| Rows | keep | Keep or Rebuild, as above (the default the mod starts with). |
| Row names: spaces around them | ignore | A row named `X ` matches the game's `X`. |
| Rows that share a name | match by content | Rows with the same name (the game's 8 `Rainbow Facet` rows) are paired by what is in them, not by order. |
| Rows the mod deleted (Keep mode) | switch off | A row the mod removed stays (row numbers) but can't drop or be crafted: `spawnable` 0 for items and affixes, `enabled` 0 for cube recipes, `complete` 0 for runewords. |
| Conflicts / Files | this mod wins / overwrite | Defaults of the Load order settings. |

## Updating a converted mod

When a new version of the original mod comes out, use **Update a converted mod** in the window (or
`Update-D2RConvertedMod.bat -Mod <name> -Source <new download>`). The old files go to
`<mod>\d2rmm\previous`, the conversion runs again with the saved options, and if it fails the old
files are put back. Run Update without a new download after a **game patch**, so the mod is rebuilt
against the patched game.

## Rules for your own mod list (optional)

Copy `modlist-rules.example.json` to `<D2RMM>\mods\modlist-rules.json` and edit it. Each rule
becomes a checkbox in the converted mod's settings:

- **My mod list** rules are off by default and only act when ticked **and** the partner mod is
  enabled in D2RMM (optionally only when it is above). They can let the mods above keep their values
  for some tables, leave out some of this mod's files (for example its inventory panel when you use an
  inventory mod), or turn off one of its plugins.
- **Options** rules are parts of the mod itself that you can switch off, for example removing one item
  property from every item.

The example file explains every field. Run Update on the mod after editing the rules.

## Command line

```bat
Convert-D2RDataMod.bat -Mod "<D2RMM>\mods\SomeMod" -Author "Someone" -Check
Convert-D2RDataMod.bat -Archive "<download>\SomeMod.mpq" -Mod "<D2RMM>\mods\SomeMod" -Check
Update-D2RConvertedMod.bat -Mod SomeMod, OtherMod
Update-D2RConvertedMod.bat -Mod SomeMod -Source "%USERPROFILE%\Downloads\SomeMod-2.0.zip"
Update-D2RConvertedMod.bat -Mod SomeMod -Conflicts earlier -Files keep
```

All launchers take `-GamePath` and `-D2RMM` if the automatic search picks the wrong folder. You can
also set the environment variables `D2R_PATH`, `D2RMM_PATH` and `D2R_PYTHON`.

## Good to know

- **Total conversions that add levels can't be stacked** with each other (for example two mods that
  both put new areas on the same level numbers). Pick one.
- **Mods made of compiled `.bin` tables** (Rebirth) are decompiled and merged onto the game's text
  tables. Columns the compiled files don't store are filled with sensible values; gameplay is not
  affected.
- **Plugin DLLs**: the converter copies the mod's D2RLoader plugins as they are. It does not scan them;
  only use mods from authors you trust.
- **Caches** live in `%LOCALAPPDATA%\D2RModAssets` (game files the converter compared against). They
  refresh themselves after a game patch; you can delete the folder at any time.
- `<D2RMM>\converter-work\` and each mod's `d2rmm\previous` folder can be deleted once the mod works.
- `ConverterReference.md` has the full technical notes.

## Troubleshooting

- **"Python 3 not found"**: install Python from the link above with "Add python.exe to PATH" ticked,
  or set `D2R_PYTHON` to your `python.exe`.
- **"node not found" / the check stops**: install Node.js and start the converter again.
- **"CascLib.dll not found"**: point the launcher at your D2RMM folder with `-D2RMM "<folder>"`.
- **Port in use**: `Start-D2RModConverter.bat -Port 8767`.
- **Wrong game or D2RMM folder remembered**: delete `%LOCALAPPDATA%\D2RModAssets\paths.json`.

## License

- **The converter:** MIT (`LICENSE.txt`). Use, change, fork, re-upload or bundle it; keep
  `LICENSE.txt` with copies of the code.
- **Converted mods:** an extra permission in `LICENSE.txt` frees everything the converter writes
  (the generated `mod.js` and the rest) from any condition, credit included. The original mod's
  author decides whether a conversion of their mod can be shared.
- **Other software:** CascLib (MIT, through D2RMM's copy), D2RMM (MIT), Python, numpy, Node.js and
  7-Zip are used from your own installs and none is included; see `THIRD-PARTY-NOTICES.txt`.

`PERMISSIONS.md` explains all of this in plain words, with the matching Nexus permission settings.
