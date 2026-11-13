# Diablo II: Resurrected tools

Unofficial, read-only against the game: nothing here writes to the game folder.
Output goes into a mod folder (normally a D2RMM mod) that you install yourself.

## Scaled monster pipeline

`New-ScaledMonster.ps1` / `.bat` (wrapper) → `ScaledMonster.py`

Builds new HD monster definitions from an existing monster at a different size,
and audits which animations the donor really has.

```powershell
# report only
.\New-ScaledMonster.ps1 -GamePath 'D:\games\Diablo II Resurrected' -Audit

# build into a D2RMM mod folder
.\New-ScaledMonster.ps1 -GamePath 'D:\games\Diablo II Resurrected' -OutDir '<D2RMM>\mods\QuillRatDruid'
```

`-GamePath` can also come from `D2R_PATH`. CascLib.dll is found under the game
folder (D2RMM ships one in `tools\`), or pass `-CascLib` / set `D2R_CASCLIB`.

### What it writes

| File | What it is |
|---|---|
| `hd/character/enemy/<name>.json` | the donor's HD definition with its root entity scaled, plus any attached props |
| `hd/character/props/<prop>.json` | one small definition per prop used |
| `scaled_monsters.report.json` | variants built, plus the animation audit of every monster in the preset |

The scale is a `TransformDefinitionComponent` on the root entity, the same way
Blizzard resizes `brute2` (1.15), `colossal1` (1.25) or `baaltentacle1` (2.0).
Model, skeleton, textures, animations and state machine stay the donor's, so no
game art is copied into the mod.

Legacy graphics are sprites and are not scaled: in legacy mode the new monster
looks like its donor.

### Presets

`Presets/*.json`:

```json
{
  "name": "Quill Rat pack (Quill Rat Druid mod)",
  "variants": [
    { "name": "qr_giant_quillrat", "donor": "quillrat2", "scale": 1.9 },
    { "name": "qr_pack_quillrat", "donor": "quillrat2", "scale": 0.8 }
  ],
  "auditOnly": ["quillbear1"]
}
```

- `donor` is a `monstats.txt` Id. It must have an HD model in the archive.
- `name` is the new definition's file name. Avoid names that end in a digit.
- `auditOnly` monsters are only reported.

### Kitbashing: a new body from existing parts

The pipeline cannot write D2R's HD model, skeleton or animation files (a
proprietary binary format), so it cannot make a monster from nothing. It can
build a new-looking body out of what the archive already has:

- **Per-axis scale.** `"scale": { "x": 2.3, "y": 2.0, "z": 2.1 }` stretches the
  donor instead of only resizing it. `y` is up.
- **Attached props.** Any model in the archive can be fixed to one of the
  donor's bones. This is the game's own mechanism for monster weapons
  (`UnitAttachmentComponent`, as in `fallenshaman1.json`), so the prop follows
  the bone through every animation.

```json
{
  "props": {
    "qr_bone_spine": {
      "model": "hd/vfx/meshes/lit_mesh/bonewall/model_source/fx_mesh_bone_tusk",
      "textures": ["hd/vfx/meshes/lit_mesh/bonewall/texture_source/bonewall_props_alb.texture"]
    }
  },
  "variants": [
    {
      "name": "qr_quill_bear", "donor": "quillrat2",
      "scale": { "x": 2.3, "y": 2.0, "z": 2.1 },
      "attach": [
        { "prop": "qr_bone_spine", "bone": "L_leg_01_bind_jnt", "scale": 0.45,
          "burst": { "count": 12, "scaleJitter": 0.5 } }
      ]
    }
  ]
}
```

- `props.<name>.model` is the archive path without `.model` (a `_lod0.model`
  file counts). Each prop becomes `hd/character/props/<name>.json`.
- An `attach` entry is one prop on one `bone`, with optional `translation`,
  `rotation` (degrees) and `scale` (number or per axis), all in the bone's space.
- `burst` repeats the entry `count` times, spread evenly over a sphere, or only
  within `spread` degrees of the entry's own rotation. `scaleJitter` varies the
  size. Use it to bristle a body with spines when you do not know which way the
  bone's axes point: the spines that point inward are hidden by the body.

Limits, all from not being able to read the binary files:

- **Bone names.** Skeleton files are compressed, so the only bone names known
  are the ones a definition's JSON mentions. For the Quill Rat family that is
  the hind legs: `L_/R_leg_01_bind_jnt` (hip), `_02_` (knee), `_04_` (foot).
- **Prop size and axis** are not known until it is seen in game. Start with a
  burst, look, then narrow `spread` and set `rotation`, `translation`, `scale`.
- An attachment on a bone name that does not exist has not been tested.

The `qr_quill_bear` variant in `Presets/quillrat_pack.json` is a first guess
made without seeing it: a Spike Fiend stretched bulkier, with a burst of 12
bone tusks on each hip.

### Using the output in a D2RMM mod

```js
D2RMM.copyFile('hd', 'hd', true);                       // the generated definitions
const map = D2RMM.readJson('hd\\character\\monsters.json');
map.mynewmonster = 'qr_giant_quillrat';                 // monstats Id -> definition
D2RMM.writeJson('hd\\character\\monsters.json', map);
```

The monster itself is a new `monstats.txt` row cloned from the donor (keep its
`Code` and `MonStatsEx`, so it has the donor's animation modes).

### The animation audit

For each monster the report lists every animation mode with: the `monstats2`
flag, the legacy COF (frames, speed, the frame that triggers the hit or the
missile), the sprite files, and whether an HD model and animations exist.

Findings for the Quill Rat family (D2R 3.4.95032):

- **Spike Fiend (`quillrat2`, token SI)** plays DT NU WL GH A1 A2 DD. A1 is the
  melee claw (hit on frame 11 of 16), A2 shoots a quill (launch on frame 5 of 13).
- **Quill Bear (`quillbear1`, token S7)** has no HD model, skeleton or
  animations at all, so it is invisible in HD graphics. In legacy graphics it
  plays DT NU WL GH A1 DD; A1 is a melee attack. Its quill-shooting sprites
  (`S7TRLITA2HTH.dcc`, 12 frames) are still in the archive, but the COF and the
  AnimData record were cut, so the game cannot play them.

That is why the Quill Rat Druid mod uses a scaled-up Spike Fiend instead of the
Quill Bear: it has both attacks and a real HD body.

## Files

- `d2r_casc.py` - read-only archive access (`D2RArchive.read`, `.exists`, `.list`)
- `ScaledMonster.py` - the pipeline
- `ModAssets.py`, `ModHarness.js` - the mod test pipeline (below)
- `Presets/` - one JSON per job

## D2RMM package size limit

`Set-D2rmmLimit.ps1` / `.bat` (wrapper) → `D2rmmLimit.py`

D2RMM refuses D2RLoader packages over 512 MiB in total ("Resource byte limit
exceeded by ..."), which blocks big mods such as shattered (~1.1 GB). The limit
is hard-coded in `resources/app.asar`; this rewrites it in place with a value of
the same length (default `4e9`), so nothing else in the archive moves. This one
does write outside a mod folder: it patches the D2RMM install.

Rerun it after every D2RMM update; an install that is already patched is left
alone. Double-clicking the `.bat` patches every D2RMM install under the game
folder.

```powershell
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Diablo II Resurrected' -Check     # report only
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Diablo II Resurrected'            # patch
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Diablo II Resurrected' -Restore   # put app.asar.bak back
```

It refuses to patch while D2RMM is running, or if the D2RMM build turns on
Electron's asar integrity fuse (the app would no longer start). It stops with an
error if a D2RMM update changes the limits code so the pattern no longer matches.
The unpatched file is saved as `app.asar.bak` next to `app.asar`.

## Mod test pipeline (gets the game files a mod needs by itself)

`Test-D2RMod.ps1` / `.bat` (wrapper) → `ModHarness.js` (node) + `ModAssets.py`

Runs D2RMM mod scripts without the game, against the game's own files, with a
mock `D2RMM`, and checks what they produce. There is no list of "files this mod
needs" to keep: every game file a script reads is taken from the archive the
moment it asks for it and kept in a cache (`%LOCALAPPDATA%\D2RModAssets\vanilla`,
outside the repo; `-Refresh` after a game update). Rows a mod adds are found by
comparing with the game's tables, so the checks need no naming convention.

```powershell
# one mod
.\Test-D2RMod.ps1 -GamePath 'D:\games\Diablo II Resurrected' -Mod '<D2RMM>\mods\DruidPoisonDisaster'

# several mods in load order (clashes between mods show up this way), an option overridden,
# and the list of files it took written down
.\Test-D2RMod.ps1 -Mod '<D2RMM>\mods\QuillRatDruid','<D2RMM>\mods\DruidPoisonDisaster' `
    -Config 'testMode=true' -Manifest .\needed_files.json

.\Test-D2RMod.ps1 -Mod '<mod>' -Dump        # also print every row the mods added (-DumpBase: classic-rules tables)
```

Exit code 0 = no problems, 1 = problems, 2 = a mod script threw. Mod options come
from `mod.json` defaults, then the mod's `config.json`, then `-Config`.

### What it checks

- **Skills** (new rows in `skills.txt`, both `global\excel` and `global\excel\base`):
  row id, prerequisites (exist, same class, same page), missiles, summon and pet type,
  states, stats, every `skill('..')` / `miss('..')` / `stat('..')` in a calc, the
  skilldesc row and its strings, tree cell (inside 6 x 3, not shared, not on a stock skill).
- **Extra skill pages** (SkillTab4 plugin): page not above the plugin's highest
  (`-MaxPage`, default 15), `ListRow` names the parent tab, each page number used by one
  class only, `Tab<N>` and `TextTab<N>` in the layout with an existing label string.
  A warning when a skill sits where the parent tab has no skill (no frame in the picture).
- **Missiles**: names without spaces or a trailing digit, `Skill`, sub-missiles,
  same row number in the main and the classic-rules table. A warning when a new
  skill's missile takes its damage from another skill. Lists new missiles without an HD entry.
- **Monsters and pets**: row index, AI name, skills, missiles, name string, pet type, HD body.
- **Strings**: new keys and ids not already in use.
- **HD**: every texture, particle file, model or definition an HD definition written by a
  mod names must be in a mod folder or in the archive; same for the textures named inside
  particle files copied from a mod folder. (Animations and skeletons are not checked.)
- **PetAI rules**: format, and that each rule matches its monster's skill slot.

It cannot tell whether anything works in the game: it checks that every name points at
something, not what the engine does with it.

### The manifest (`-Manifest`)

`readFromGame` (the game files the scripts read: what is needed to produce the mod's
output), `askedButMissing`, `written`, `copiedFromModFolder`, `gameFilesDependedOn`
(game files the written HD definitions rely on).

### Looking things up while designing (`ModAssets.py`)

```powershell
$env:D2R_PATH = 'D:\games\Diablo II Resurrected'
python ModAssets.py show skills "Baal Nova,Cold Fissure"          # non-empty columns of rows (first column = name)
python ModAssets.py show missiles "frogpois" --base               # the classic-rules table
python ModAssets.py find monstats pois --cols El1Type,AI,MissA1   # rows where one of the columns matches
python ModAssets.py find missiles "rock|debris"
python ModAssets.py deps hd/missiles/expansion_tornado.json       # definition -> particles, models -> textures
python ModAssets.py fetch --out .\dump --deps hd/missiles/icebolt.json global/excel/skills.txt
python ModAssets.py ls "hd/missiles/.*nova"
```

## Recoloured effect pipeline

`New-RecoloredEffect.ps1` / `.bat` (wrapper) → `RecolorEffect.py`

Gives a new skill its own-looking HD effect by recolouring an existing one, so
it is not the donor monster's or skill's exact effect.

```powershell
# report only: which textures of each effect can be recoloured
.\New-RecoloredEffect.ps1 -GamePath 'D:\games\Diablo II Resurrected' -Audit

# build into a D2RMM mod folder and rewrite the manifest block in its mod.js
.\New-RecoloredEffect.ps1 -GamePath 'D:\games\Diablo II Resurrected' -OutDir '<D2RMM>\mods\DarknessMagicNecro' -PatchMod
```

### How it works

An HD missile definition (`hd/missiles/<name>.json`) points at `.particles`
files (compiled binaries). A particle file names its textures by path, and most
of an effect's colour comes from small uncompressed gradient textures.

1. Every texture the effect's particle files name is read. Uncompressed (RGBA8)
   textures that really hold colour are recoloured and written under a new file
   name **of the same length** (the first characters become the look's `tag`).
2. The particle file is copied under a new name with those paths swapped. The
   length is unchanged, so nothing else in the binary moves.
3. A manifest (old particle path → new, plus the new textures) is written into
   the mod's `mod.js` between the `<recolor-manifest>` markers (`-PatchMod`).

### What it writes

| File | What it is |
|---|---|
| `hd/vfx/textures/.../<tag>....texture` | recoloured textures |
| `hd/vfx/particles/.../<tag>....particles` | particle files that use them |
| `recolored_effects.report.json` | per look: what was recoloured and what was left alone |

### Presets

`Presets/*.json` (default `darkness_magic_effects.json`):

```json
{
  "skipFolders": ["distortion"],
  "looks": [
    { "name": "sanguineskull", "tag": "dmM", "source": "vampire_missile",
      "color": { "hue": 355, "minSat": 0.8, "value": 0.85 } }
  ]
}
```

- `source` is a file in `hd/missiles` without `.json`; `name` is what the mod refers to.
- `tag` must be unique per look (3 characters is enough) and shorter than the file names it replaces.
- `color`: `hue` (0-360) gives every pixel that hue, `minSat` then lifts washed-out
  pixels to that saturation; `hueShift` rotates instead; `sat` and `value` multiply.

### Limits

- **Grey data ramps are left alone** (alpha remap, fresnel, linear gradients):
  their channels are numbers, not colour.
- **Block-compressed textures are left alone.** The format codes seen are
  0x3f (8 bytes per block, single-channel masks), 0x3d / 0x3e / 0x41 (16 bytes
  per block). BC1 / BC3 recolouring is implemented but off, because the codes
  have not been matched to formats: enable it per code with
  `"blockFormats": { "0x3e": "bc3" }` only once that is known.
- **Colour set inside the particle file** (a constant, not a texture) is not
  changed. `poison_sparks` is such an effect; `poison_smoke_puff` recolours.
- Models keep their own textures (`bone_spirit`'s skull, the Death Mauler's fingers).
- Run `-Audit` first: an effect with nothing to recolour comes out unchanged.

### Using the output in a D2RMM mod

```js
// <recolor-manifest> generated by RecolorEffect.py, do not edit by hand
const RECOLORED = {};
// </recolor-manifest>
D2RMM.copyFile('hd', 'hd', true);   // the generated textures and particle files
// in the missile's HD definition, for a look:
//   VfxDefinitionComponent.filename = RECOLORED[look].particles[filename] || filename
//   and add the new particle and texture paths to `dependencies`
```

`DarknessMagicNecro\mod.js` (`buildHdMissile`) is the worked example.

## Particle effect decoder (edit an effect, not only its colours)

`PopcornBaked.py` (+ `PopcornBaked.schema.json`), `PopcornVm.py`

The game's `.particles` files are PopcornFX baked effects (runtime 2.9.5). There is no public
editor for them and the PopcornFX editor is a paid product, so the format was decoded from the
game's own 1991 files (2026-11-13). The module reads a file into objects, lets a script change
the parts that are plain data, and writes it back. All 1991 files come out byte for byte the
same when nothing is changed.

- Editable: renderer properties (texture and mesh paths, numbers, modes), curve keys,
  attribute defaults, strings (new ones are added at the end), and the constants of the
  compiled scripts (the literal numbers a script uses: sizes, lifetimes, speeds, colours).
- Decoded (`PopcornVm.py`): the instructions of the compiled scripts, which say how particles
  are spawned, moved, sized and coloured. All 11241 distinct scripts of the game decode with
  the instruction count their header gives and encode back to the same bytes. The listing
  shows loads and stores by name, arithmetic, comparisons, vector building, and calls with the
  function's own name (`self.kill_bool_pCtxS`, `effect.age_pCtxI`, `samplerCurve1:sample_float`).
- Not identified yet: most one-argument math functions (shown as `fn1_XX`), the three-argument
  ones, and the exact order of the four inequality tests. The module's docstring marks what
  is presumed.
- Not tested in the game: a script whose instructions were changed (only constants so far).
- Confirmed in the game (2026-11-13): an edited file with added strings, a changed length and
  textures drawn from scratch loads and shows.

```
python PopcornBaked.py props <file.particles>       renderers and their properties (PC copy)
python PopcornBaked.py code <file.particles>        compiled scripts: the names they use and their constants
python PopcornBaked.py dis <file.particles> [n ...]  compiled scripts as readable instructions
python PopcornBaked.py dump <file.particles> [--class <name>]
python PopcornBaked.py roundtrip <file or folder>
```

The layout and the known field meanings are in the module's docstring. First use:
`SorceressSecondPages\devuild_effects.py`, which draws its own RGBA8 textures (one mip, the
gradient textures' layout) and points an effect's layers at them.

## Particle effect editor (GUI and command line)

`Start-D2REffectEditor.ps1` / `.bat` -> `EffectEditor.py` + `EffectEditor.html` (the GUI)
`Edit-D2REffect.ps1` / `.bat` -> `EffectEdit.py` (the command line and the shared core)
`HdTexture.py` (the game's `.texture` files <-> PNG)

Built on the decoder above. An effect is shown as its named layers ("Root", "tail",
"headglow" ...). Each layer has renderers (what is drawn, with textures and settings),
scripts (the compiled code that spawns and updates its particles, with the numbers it uses)
and samplers (curves and others).

**GUI.** `Start-D2REffectEditor.ps1 -Root <game> -OutDir <mod folder>` starts a server on this
computer only and opens the page:

- find any of the game's effects by name; pick a layer on the left;
- middle: a preview and the layer's renderers. Change a texture with the picker (search the
  game's effect textures, or use your own PNG, which becomes a new texture), type new numbers
  into settings;
- right: the layer's scripts with their constants (editable) and their code (read only), and
  its curves (keys editable, with a plot);
- changed values turn orange; Undo steps back; Save writes the new `.particles` file, the
  textures made from PNGs and the recipe into the mod folder, and shows what the mod script
  needs.

The preview is an approximate still picture: base texture times blend texture, cut by the
masks, coloured by the gradient map. It does not run the effect, so movement, distortion,
particle count, size and timing are not shown. Mesh, light and decal renderers are listed but
not drawn.

**Command line (for scripts and bots).** Everything the GUI does is a *recipe*, a JSON file:

```
.\Edit-D2REffect.ps1 list mephisto                 particle files whose path matches
.\Edit-D2REffect.ps1 missiles "^meph"              missile name -> HD definition -> particle files
.\Edit-D2REffect.ps1 show <effect> [-Json] [-Scripts]
.\Edit-D2REffect.ps1 apply recipe.json -OutDir <mod folder>
```

`show -Json` gives the full description (layers, properties, constants, curves) to read
programmatically; `apply` prints the manifest as JSON and exits 1 with a one-line reason when
an edit does not fit (unknown layer, wrong value type ...). The recipe format, with every
edit kind (`property`, `replace-texture`, `constant`, `curve`, `attribute`) and the
`textures` made from PNG files, is in the docstring of `EffectEdit.py`. A recipe saved by
the GUI gives the same bytes when applied from the command line.

Edits address the PC copy of an effect (the file also holds Switch, PS4 and PS5 copies, often
with fewer layers); `replace-texture` changes all copies.

Checked 2026-11-13: GUI driven in a browser (open, texture pick, PNG import, constant edit,
code view, undo, save), and the saved recipe re-applied from the command line byte for byte.
Not yet checked in the game: an effect saved by the editor (the same kind of file, made by a
script, does load and show).

## Loader log reader (what the game itself complained about)

`Get-D2RLoaderLog.ps1` / `.bat` (wrapper) -> `LoaderLog.py`

D2RLoader writes every failed game check to `<game>\d2rloader\logs\d2rloader.log`: the
source file of the check and, for data tables, the file, row, column and cell value. The log
covers the last game session. **Read it first when something misbehaves in the game** - it
usually names the cause, and it shows which build was actually running (compare the session
start with the time of the last install and of the last edit).

```
.\Get-D2RLoaderLog.ps1 -Root 'D:\games\Diablo II Resurrected'            one entry per distinct check
.\Get-D2RLoaderLog.ps1 -Root 'D:\games\Diablo II Resurrected' -All -Plugins
```

Seen so far (2026-11-13):

| Check | Meaning |
|---|---|
| `nSize < NUM_COLLISION_SIZES` (Collisn.cpp) | a missile or unit with a collision size above 3. `missiles.txt` `Size` is 1-3; with 4 every tile counts as blocked, so the missile dies where it is cast and hits nothing. |
| `pfFuncOperandsMatchFunc` (BBE.cpp), with TXT / row / cell | a formula cell calls a function with the wrong number of arguments, e.g. `skill('X')` without `.blvl`. |
| `data_.f.flags & kUintFlag` (RapidJSON) | a JSON number read as unsigned is negative, fractional or too large. The log does not say which file. |

The game logs each distinct check once per session, so one entry does not mean it happened once.

## Automatic testing in the game (bot harness)

`Invoke-D2RBotTest.ps1` / `.bat` (wrapper) + the BotHarness D2RLoader plugin
(`D:\games\Diablo II Resurrected\mods\BotHarness`, its README has the command list)

Starts the game with a script that drives it (console cheats, UI messages, keys,
mouse) and collects what happened (game events, monster deaths, screenshots) in
a run folder under `<game>\d2rloader\botharness\runs\`.

```powershell
.\Invoke-D2RBotTest.ps1 -Root 'D:\games\Diablo II Resurrected' -Script .\BotScripts\smoke-menu.txt
.\Invoke-D2RBotTest.ps1 -Root 'D:\games\Diablo II Resurrected' -Commands 'waitfor menu','screenshot menu' -NoWait   # step by step
```

Exit code 0 = `RESULT PASS`, 1 = `RESULT FAIL`, 2 = no result (crash, timeout,
plugin not loaded). The plugin must be enabled in D2RMM and installed first, the
game must not be running, and the game window has to stay in front during a run.

- `BotScripts/smoke-menu.txt` - reaches the main menu, takes a screenshot, exits
- `BotScripts/ingame-test.txt` - enters a game, cheats, spawns monsters, fights, checks
  the kill count, exits (cheats change the character: throwaway characters only)
- `Send-D2RBotCommand.ps1` - after `-NoWait`: appends lines to the newest run's script and
  returns what the plugin logged for them

`-Character <name>` makes the launcher refuse to start unless that character was
played last: the menu selects the last played character and `ui MainMenuHD:Play`
enters it, and a script cannot read the name.

Both scripts passed in the game on 2026-11-13 (plugin 0.2.0); the plugin README
has what the runs showed.
