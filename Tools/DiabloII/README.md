# Diablo II: Resurrected tools

Unofficial, read-only against the game: nothing here writes to the game folder.
Output goes into a mod folder (normally a D2RMM mod) that you install yourself.

## Scaled monster pipeline

`New-ScaledMonster.ps1` / `.bat` (wrapper) → `ScaledMonster.py`

Builds new HD monster definitions from an existing monster at a different size,
and audits which animations the donor really has.

```powershell
# report only
.\New-ScaledMonster.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Audit

# build into a D2RMM mod folder
.\New-ScaledMonster.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -OutDir '<D2RMM>\mods\QuillRatDruid'
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

- `bones` repeats an entry once per listed bone (`scaleJitter` varies the size).
- Attachment `rotation` is Euler X, Y, Z in **degrees** (Blizzard's own files use
  values such as 22.5 and -10 / 20).

Bone names, bone directions and prop sizes come from the HD files themselves:
see "Reading HD models" below. For the Quill Rat family the skeleton has 155
bones, among them 62 quill joints `spike_01_jnt` .. `spike_62_jnt` (1-19 on the
neck, 20-49 on the upper back, 50-62 on the lower back). A back quill points
along its joint's local -X.

The `qr_quill_bear` variant in `Presets/quillrat_pack.json` is a Spike Fiend
stretched bulkier with a bone tusk on every second back quill joint. It was
laid out with the offline preview and has not been seen in game.

## Reading HD models (Granny)

D2R's `.model`, `.skeleton` and `.animations` files are **Granny 3D** files
(version 7, 64-bit little endian, type tag 0x80000039) with BitKnit2-compressed
sections. They use Granny's standard `granny_file_info` layout and describe
their own data, so everything in them can be read.

- `GrannyFile.py` - the reader: sections, pointer fixups, the type tree and a
  generic walk of the object graph. `python GrannyFile.py <file>` prints the
  file's type tree.
- `GrannyPreview.py` - decodes meshes and bones and draws a still picture of a
  body with props attached to its bones (`build_scene`, `draw`), so a kitbash
  can be looked at without starting the game. Needs numpy and Pillow.

What the files hold, as found in the Quill Rat (2026-11-13):

| Part | Details |
|---|---|
| Skeleton | bone name, parent, local transform, inverse world matrix. World axes: +Y up, +Z towards the head, units are feet (3.28 per metre) |
| Mesh vertices | `Position` int16 x 4, normalised, times `VertexScale` from the mesh's extended data; `BoneWeights` / `BoneIndices` uint8 x 4; `Normal` and `Tangent` int8 x 4; `TextureCoordinates0` half x 2. 28 bytes per skinned vertex, 20 for a static prop |
| Mesh topology | 16-bit triangle indices, material groups, a bone binding list by bone name |
| Mesh extras | `bbMin`, `bbMax`, `VertexScale`, `meshRenderLayer`; the model carries `lodLevel` |
| Animations | Granny track groups with curve data (not decoded yet) |

**The BitKnit2 decoder is not in this repository.** The decoders that exist are
GPL (powzix/ooz and ports of it), which LICENSING.md keeps out of AAMT. A
Python port lives in `%LOCALAPPDATA%\D2RModAssets\thirdparty\bitknit.py` on the
machine it was made on; `GrannyFile.py` loads it from there, or from the folder
named by `D2R_BITKNIT`. Without it only uncompressed Granny files can be read.

### Writing and editing models

- `GrannyFile.py` can write a file back with every section stored uncompressed
  (`Granny.to_bytes()`, `.save(path)`). The layout is kept: section contents are
  edited in place, pointers stay valid because section sizes do not change, and
  the header checksum (CRC-32 of everything after the first 104 bytes) is
  recomputed. A mesh, a body model, a skeleton and an animation file all
  round-trip with identical sections, tables and object graph.
- `GrannyMesh.py` edits vertex positions on top of that: `Model(path).meshes`,
  `mesh.positions()`, `mesh.weights()`, `mesh.set_positions()`, `model.save()`.
  Positions are requantised only when the mesh outgrows its old range, and the
  bounding box is recomputed. Vertex count, triangles, skin weights and the
  skeleton are untouched, so the result plays the donor's animations.
- `GrannyMesh.reshape` is the edit behind the Quill Bear: quills (the vertices
  that follow a `spike_NN_jnt` joint) are stretched along the quill and
  thickened, and the torso is made heavier in proportion to how much each
  vertex follows the spine, pelvis, neck and shoulders.

In a preset a variant asks for it with `"reshape"`:

```json
"reshape": {
  "quills": { "prefix": "spike_", "length": 1.55, "thickness": 1.7, "first": 20, "last": 62 },
  "bulk": { "bones": ["spine_", "pelvis", "neck"], "x": 1.35, "y": 1.22, "z": 1.05, "pivot": [0, 2.2, 0.6] }
}
```

`"shape"` (a list) is a graded edit: like `bulk` (scale about a pivot) or an
`offset`, but its strength ramps along an `axis` from `from` to `to` (`power`
bends the ramp) and fades out with distance along the `within` axes. That is
how the Giant Raven (`Presets/giant_raven.json`) gets a hooked beak tip, a
throat ruff and a wedge tail longer in the middle than at the sides.

A variant with `"reshape"` can also wear its own textures: `"retexture"`
entries (`from`, `to`, `format` bc1/bc3/rgba8, `recolor` as in the recoloured
effect pipeline) write a recoloured copy (block by block, so format and mips
stay) and point the rewritten models at it. The new path must be as long as the
old one, because the model's texture name is swapped in place.

A preset's `"modelIndexIncludes": ["../OtherMod"]` carries another mod's added
models (from its `model_index.json`, bounding boxes from its own model files) in
this mod's `hd/model_lod_desc.bin`; the entries keep `"source"`. Both mods ship
the whole index and the one installed last wins, so the including mod must be
installed after the other, and rebuilt when the other's models change.

The pipeline then writes the donor's models, edited, to
`hd/character/enemy/<name>/<part>_lodN.model` (every LOD) and points the new
definition at them. These files are edited copies of game art: keep them in
your own mod folder and out of this repository.

Two readers exist side by side for now: `GrannyFile.py` (this one, in-place
rewrite, used by `GrannyMesh.py` and `GrannyPreview.py`) and `Granny.py` +
`HdSkeleton.py` from the skeleton work, whose `Writer` lays a whole object tree
out again and can therefore add or remove bones. The mesh tools should move
onto `Granny.py` once that settles.

Seen in the game (2026-11-13): **D2R loads an uncompressed model rewritten by
`GrannyFile.py`** (the Sorceress's five head models, bone numbers edited; see
"Skeleton decoder and sprite-monster converter"), and a model with reshaped
vertices: the Quill Bear body is drawn and animates next to a stock Spike
Fiend, with its tusk props on the quill joints (`UnitAttachmentComponent`
accepts any skeleton bone name).

**The model index.** The game only draws a model whose path is listed in
`hd/model_lod_desc.bin` (bounding boxes and LOD rows for every model; without an
entry the model is silently skipped: props attached to the body show, the body
does not, and nothing is logged). A model that replaces a stock file at the
stock path needs nothing. A model at a new path needs an entry, so the mod has
to ship the index with its entries added. The pipeline does this for every
`"reshape"` variant; the mod copies it with the rest of `hd`.

The index belongs to one game build. After a game patch a mod that still ships
the old one hides whatever models the patch added, so the index is never the
source of truth:

- The mod folder gets `model_index.json`: the models it adds, each one's donor,
  and which stock index (build, size, SHA-256) the shipped file was built from.
- `Update-D2RModelIndex.ps1 -GamePath <game> -Mod <mod folder> -Check` says
  whether the game's index has changed since (exit code 1 = rebuild needed).
  Without `-Check` it rebuilds: it reads the game's current index, copies each
  donor's current entry, takes the bounding boxes from the mod's own model
  files, and writes the index and the manifest back. Then install the mod again.
- `ModelLodDesc.py` does not assume this build's layout. It reads the three
  tables from the header, derives the record sizes, and finds the fields it
  needs by what must be true of them (the hash is the one sorted column, the
  LOD count adds up to the number of LOD rows, a link lands on rows, a bounding
  box is six floats with min <= max). Everything else in a record is carried
  along and copied from the donor. Tested against re-laid-out copies of the
  stock index (fields reordered, records grown, header grown, models removed):
  the fields are found and the result reads back. When a rule finds no column or
  more than one, or the stock models are no longer found under the path hash
  (FNV-1a 32 of `data/hd/.../torso.model`), it stops with the reason instead of
  writing a file the game would misread.
- `python ModelLodDesc.py layout <index>` prints what it found;
  `show <index> <data/hd/...model>` prints an entry.

Limits: D2RMM gives a mod no way to read a binary game file, so the rebuild
cannot happen at install time and nothing warns you in D2RMM itself: run the
check after a game patch. Two mods that both ship the index overwrite each
other. A patch that changes the donor's mesh count makes the rebuild stop,
because the reshaped copy no longer matches its donor; rebuild the model then.

### Animations: new clips, own skeleton, size from the sprite

`GrannyAnim.py` reads a monster's clips (`<monster>/animation/combined.animations`,
one Granny Animation per clip), poses a mesh with them, and writes new clips
(through `Granny.py`'s writer). Stock curves are decoded exactly (quantised
B-spline formats D4nK16uC15u, D4nK8uC7u, D3K16uC16u, D3K8uC8u, D3I1K*, the
constants and DaK32fC32f) and then treated as keyframes; new clips are written
as plain linear float keys. `clip.pose(t)`, `GrannyAnim.skin(...)` and
`GrannyPreview.draw` give a still of any clip at any time.

A variant in a preset can ask for its own animation set:

```json
"scale": { "sprite": "s7" },
"animations": [
  { "name": "cast", "base": "neutral", "duration": 0.8, "edits": [
      { "rotate": "spine_01_bind_jnt", "axis": [1, 0, 0], "degrees": [[0, 0], [0.35, -34], [0.6, -34], [1, 0]] },
      { "scale": { "prefix": "spike_", "first": 1, "last": 62 }, "factor": [[0, 1], [0.5, 1.32], [1, 1]] },
      { "move": "pelvis_bind_jnt", "offset": [[0, [0, 0, 0]], [0.5, [0, -0.2, 0]], [1, [0, 0, 0]]] } ] }
]
```

- `"animations"`: each clip starts from a stock clip (`base`, optionally a piece
  of it with `from`/`to`, retimed with `duration`, or one pose of it held with
  `"at": <seconds>` for `duration` at `fps` keys a second) and is edited with `rotate`
  (a bone and everything below it, about a model-space axis), `scale` (bones in
  place) and `move` (a bone, by a model-space offset). Curves are
  `[progress 0..1, value]` pairs, eased (`"ease": "linear"` on an edit: straight
  lines, e.g. an even 0-360 turn); an edit can add
  `"wave": {"cycles", "amplitude", "fade", "phase"}` (`"fade": false` keeps full
  size, so whole cycles loop seamlessly; `phase` in degrees lags a joint behind
  its parent for follow-through). The pipeline writes
  `hd/character/enemy/<name>/animation/combined.animations` (stock clips plus
  the new ones), a copy of the donor's state machine pointed at it and a copy of
  the donor's skeleton, and points the definition at all three. The state
  machine already has a state for every mode, bound to a clip name: `neutral`
  NU, `walk` WL, `run` RN, `attack1` A1, `attack2` A2, `gethit` GH, `block` BL,
  `cast` SC, `skill1`-`skill4` S1-S4, `knockback` KB, `death` DT, `dead` DD.
  A mode has an HD animation as soon as a clip of that name exists.
  A clip spec with `"mode": "S3"` (and optionally `"loop": true`) binds that mode's state to the clip under
  its own name instead, e.g. a clip called `charge` on S3. Every added clip is listed as an
  `AnimationItem` (`<folder>/animation/<clip>.animation`) in the copied state machine, bound or not,
  so a mod can bind it by name in states it adds itself (skill-indexed states, for example).
- Offline stills of a clip: `GrannyPreview.clip_sheet(models, skeleton, animations, clip, [0, 0.3, 0.55, 0.8], out.png)`
  draws one picture per view and moment with a fixed camera per view (so motion shows), wings or
  other parts coloured by bone (`colours`), and a floor square (`ground`) to show the height.
  `posed_parts` gives a posed body for `draw`, and `draw(..., frame=frame_of(...))` keeps a camera.
- `Presets/giant_raven.json` is a worked example of a flying body: the Druid's Raven (`druidhawk`)
  reshaped and x4.0 as a shapeshift form, every clip lowered with a `move` on the pelvis (the stock
  clips hover 13.5 model ft up, which a root scale multiplies), `hover` / `fly` / `fall` on
  NU / WL / DT, wing-gesture clips built from a held glide pose with follow-through on the wing
  chain, and loops made of whole wave cycles. Its notes list the skeleton's axes.
- `"scale": {"sprite": "<token>"}` sizes the body from a sprite monster: its
  neutral height over the donor's own sprite height (COF boxes), corrected for
  a reshape that made the mesh taller. The Quill Bear (s7, 72 px) over the
  Spike Fiend (si, 35 px) gives 2.06, 1.86 after the longer quills.

Seen in the game on 2026-11-13 (bot harness): a monster with its own skeleton,
state machine and a rewritten animation file at new paths loads and plays its
stock clips; with idle temporarily bound to the new clips, `cast` (rearing up),
`run` and `skill1` play. Not seen: the new clips reached through their real
modes (RN, SC, S1, S2, BL). The Spike Fiend's legacy token has descriptors
(COF) only for NU WL A1 A2 GH DT DD, and whether the game enters an HD state
for a mode with no legacy descriptor is untested.

What "sprite to HD" does not do: it does not make a mesh from sprites. The body
is the donor's mesh, reshaped; the sprite gives the size.

### Sprite monster to HD mesh: sprites, a template, and an AI model

For a sprite monster with no HD model whose HD relative looks like it (the Quill
Bear, really a Spike Giant, token `s7`, next to the Spike Fiend):

- `LegacySprite.py` decodes the legacy DCC sprites: every frame of every view
  direction, with the act palette. `sheet` writes a contact sheet, `views` one
  PNG per direction going round the monster. (Written from the published format
  description; the Quill Bear's idle decodes cleanly in all 8 directions.)
- `SpriteFit.py fit` takes the relative's HD mesh as a template, poses it with
  its own neutral clip, draws its outline from the sprite's eight directions
  (orthographic camera; it finds the elevation, 30 degrees, the scale, the turn
  direction and mirroring by itself) and searches for the body-part proportions
  (torso, head, tail, fore and hind legs: long / tall / wide; back and neck
  quills: length / thickness) that make the eight outlines overlap the sprite's
  best. It writes `fit.json`, whose `"reshape"` block goes into a preset
  variant, and `fit.png` (sprite, before, after, per view). Because the result
  is the template's own mesh with moved vertices, the model stays valid:
  triangles, skin weights, UVs, materials and all LODs are the template's.
  `"reshape"` accepts a list of `bulk` parts and a list of `quills` for this.
- `SpriteMeshAI.py make` runs an AI image-to-3D model (TripoSR, MIT, local, on
  the GPU) on one sprite view and writes the mesh it imagines (`ai_mesh.obj`).
  That mesh is a rough reference, not a game model; `SpriteFit.py fit --ai-mesh`
  uses its width and height against its length as a second target, for the
  depth an outline only hints at. TripoSR and its weights stay outside the
  repository (`THIRD_PARTY.md`).
- `GrannyPart.py quill` cuts one part out of a body mesh (the vertices that
  follow one joint, e.g. the largest `spike_NN_jnt`) and writes it as a
  standalone static mesh model laid out like the game's quill missile mesh
  (long along X, root at -X), keeping the body's UVs, so a missile can be a copy
  of a quill on the monster's back and wear the body's own textures. This is
  the first tool here that writes a mesh with new vertex and triangle counts
  (through `Granny.py`'s writer). Remember `<name>_lod0.model` and the model
  index.

Status on 2026-11-14: the sprite decoder, the fit and the part cutter run and
their results were looked at offline (outline overlap for the Quill Bear rises
from 0.53 to about 0.6 in one pass; the rest is mostly the pose difference
between the sprite's idle and the HD idle). The AI step is written but has not
been run here. None of it has been seen in the game yet.

### Skill tree page pictures

`SkillTreeArt.py draw --spec page.json --out <mod>/hd [--class dr] [--name qrskilltree]` redraws a
class's skill tree picture for a custom page: a stock frame and level box in every occupied cell,
and prerequisite arrows (built from the stock shaft and arrowhead, any direction). The picture is
an uncompressed sprite (version 31: 40-byte header, RGBA, three pages side by side, a tab strip on
top of each); the tool keeps the strips and replaces the grid of every page, and writes the
`.lowend` copy too. `page.json`: `{"cells": [[row, col], ...], "arrows": [[[row, col], [row, col]], ...]}`.
An arrow that would cross another occupied cell is left out and reported. Grid (icon top-left in
the picture): columns 121, 383, 643; rows 136, 318, 494, 674, 854, 1030. Point a layout
`ImageWidget` at it with `filename: 'Spells\Skill_Trees\<name>'`. Not seen in game yet
(2026-11-14).

Not done yet:

1. **Changing vertex or triangle counts** (new geometry): needs the structural
   writer in `Granny.py`.
2. **Normals** are left as they were after a reshape; large edits will shade
   slightly wrong until they are recomputed.
3. **Animation curves**, to change or add animations.

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

## Skeleton decoder and sprite-monster converter

`HdSkeleton.py` turns a `.skeleton` into JSON and back (`Granny.py` does the
container work; `.animations` and `.model` files decode with the same commands):

```powershell
python HdSkeleton.py info   hd/character/enemy/fallen1/skeleton/fallen1.skeleton --game 'D:\games\Steam\steamapps\common\Diablo II Resurrected'
python HdSkeleton.py decode <file> out.json [--strip]     # --strip leaves out the Maya attribute dumps
python HdSkeleton.py encode out.json new.skeleton
python HdSkeleton.py check  <file> ...                    # decode, encode, decode again, compare
```

A skeleton file holds one skeleton and one model entry that names it. Each bone
has `Name`, `ParentIndex`, `Transform` (rest pose), `InverseWorldTransform`
(the bind matrix, row vectors, translation in the last row), `LODError` and
`ExtendedData` (every Maya attribute of the joint, most of the file).
The JSON keeps the file's own type description next to the data, so `encode`
needs nothing else; a member name that repeats in a type gets `#2`, `#3`.

`LegacyToHd.py` (`Convert-D2RLegacyMonster.ps1`) gives an original-graphics
monster an HD version. Sprites have no bones, so it starts from the HD monster
closest to the sprite one:

```powershell
# how big the sprite monster is, and which HD monsters are closest
.\Convert-D2RLegacyMonster.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -DataDir '<mod>\data' -Token zz -Donors
# build: donor definition + skeleton copy under a new name, sized to the sprite
.\Convert-D2RLegacyMonster.ps1 -GamePath '...' -DataDir '<mod>\data' -Token zz -Name my_monster -OutDir '<D2RMM>\mods\MyMod'
# after editing skeleton_src\my_monster.skeleton.json
.\Convert-D2RLegacyMonster.ps1 -Name my_monster -OutDir '<D2RMM>\mods\MyMod' -Encode
```

- **Size** comes from the COF files (`global/monsters/<token>/cof`): each holds
  the box its sprites fill. The height of the neutral pose above the feet,
  divided by the donor's, is the scale. `-Scale` overrides it.
- **Closeness** (`closeness` in `LegacyToHd.py`, smaller is closer): one point
  per animation mode the donor lacks, plus the difference in outline shape,
  composite layers, frame counts and size. `-Donor <monstats Id>` overrides it.
- **What goes where.** The game's animations set every bone's position,
  rotation and scale on every frame (root, `translate` and `anim` included),
  and editing bone numbers in the skeleton or in a model's own copy of the
  bones showed nothing in the game (table below). The body scale is therefore
  put on the definition's root entity, as `ScaledMonster.py` does. The skeleton
  copy is the place for the bone list (names, parents); proportions have to be
  made in the mesh vertices (`GrannyMesh.py`) or the animations.
- Output: `hd/character/enemy/<name>.json`, `hd/character/enemy/<name>/skeleton/<name>.skeleton`,
  `skeleton_src/<name>.skeleton.json` (edit this, then `-Encode`) and
  `<name>.legacy_to_hd.json` (what was chosen and why). Hook it up as under
  "Using the output in a D2RMM mod".

Checked (2026-11-13): all 727 stock skeletons decode, encode and decode again
to the same data; `GrannyFile.py` reads the encoded files.

Seen in the game (2026-11-13, bot harness, the Sorceress on the character
screen, file placed at `hd/character/player/sorceress/skeleton/sorceress.skeleton`
in the installed mod output):

| Skeleton file | Result |
|---|---|
| encoded by `HdSkeleton.py` (unpacked sections, 558 KB) | loads; the body stands and animates as with the stock file |
| same, `head` bind matrix (`InverseWorldTransform`) x 1.6 | no visible change |
| same, `head` rest-pose scale x 1.6 | no visible change |
| same, `head` rest-pose position moved 0.6 along the neck | no visible change |
| encoded with `--strip` (no Maya attributes, 48 KB) | loads; no visible change |
| 1 KB of junk | the body collapses, so the file at that path is the one the game reads |

The same was done to the head models (`head_lod0` to `head_lod4.model`, rewritten
in place with `GrannyFile.py`, sections unpacked), editing the copy of the bones
each model carries:

| Head models | Result |
|---|---|
| every bind matrix scaled 1.5 about the head joint | loads; no visible change |
| `head` rest-pose scale x 0.6 | no visible change |
| `head` rest-pose position moved 0.6 | no visible change |
| 1 KB of junk each | the head and the skin are gone, so these files are read |

So D2R accepts unpacked, rewritten Granny skeletons and models, and a skeleton
without its Maya attributes. None of the bone numbers tried (bind matrix,
rest-pose scale, rest-pose position, in the skeleton or in the model) shapes the
body on the character screen; where the game takes its bind pose from is not
known. Not tried: bone orientation, renaming, adding or removing bones, and a
monster in a game (only the character screen).
Encoded files are unpacked, so several times the size of the stock ones
(fallen1: 43 KB stock, 330 KB encoded; `-Strip` drops the Maya attributes: 33 KB).
They are edited copies of game art: keep them in your mod, out of this repository.

## Files

- `Granny.py`, `HdSkeleton.py` - Granny files as editable trees; skeleton decode / encode
- `LegacyToHd.py`, `Convert-D2RLegacyMonster.ps1` - HD version of a sprite monster from the closest HD one
- `d2r_casc.py` - read-only archive access (`D2RArchive.read`, `.exists`, `.list`)
- `GrannyFile.py`, `GrannyPreview.py`, `GrannyMesh.py` - read, preview, rewrite and reshape HD models
- `ModelLodDesc.py`, `Update-D2RModelIndex.ps1` - read, extend, check and rebuild the game's model index, needed for any model at a new path
- `GrannyAnim.py` - read, pose, author and write animation clips
- `LegacySprite.py`, `SpriteFit.py`, `SpriteMeshAI.py` - legacy sprites to images, fit an HD template to them, AI mesh reference
- `GrannyPart.py` - cut a part (a quill) out of a body mesh into its own model
- `SkillTreeArt.py` - skill tree page pictures with frames and arrows for a custom page
- `ScaledMonster.py` - the pipeline
- `ModAssets.py`, `ModHarness.js` - the mod test pipeline (below)
- `ConvertDataMod.py`, `ConvertDataModCheck.js`, `MpqArchive.py`, `Convert-D2RDataMod.ps1` - data mod (or packed .mpq) to D2RMM mod (below)
- `Update-D2RConvertedMod.ps1`, `MergeCompiledMod.py` - update converted mods from a new download (VanillaDeluxe, Rebirth; below)
- `TreePlacement.js`, `TreePlacement.py` - shared tree-cell placement for the skill-page mods, also on reworked class trees (below)
- `StockRows.js`, `StockRows.py` - the plain game's template rows embedded in the skill-page mods, so total conversions do not leak into their new rows (below)
- `LeakCheck.js` - finds what a total conversion changes in the rows other mods add (below)
- `PluginSdk.py`, `PluginAddresses.py`, `Update-D2RPlugins.ps1` - keep the D2RLoader plugin sources in step with D2RLoader: SDK and hooked addresses (below)
- `HdMatch.py` - HD art for mod monsters and items that only have legacy sprites (below)
- `Presets/` - one JSON per job

## HD art for mod content without it (`HdMatch.py`)

The D2R port of D2NX's "match classic sprites to HD art by content". D2R chooses HD art through
name tables (`hd/character/monsters.json`, `hd/items/items.json`, `uniques.json`, `sets.json`); a
mod row missing from them is drawn with its legacy 256-colour sprite even when its graphics are
vanilla ones.

```
# what is missing and what would be matched (reads what D2RMM last installed)
python HdMatch.py report --game "D:\games\Steam\steamapps\common\Diablo II Resurrected"
# write the D2RMM mod HdArtMatch (D2RMM Custom 2.0.2\mods\HdArtMatch); enable it LAST in D2RMM
python HdMatch.py build --game "D:\games\Steam\steamapps\common\Diablo II Resurrected"
```

- Monsters: a row with no HD model gets the model of a row with the same animation token. A
  token the mod brought itself is compared with the HD monsters' sprites (standing frame, all
  layers); a copy or recolour gets that monster's model. Placeholder tokens (`xx`) are skipped.
- Items: base items, uniques and set items with no HD entry get the HD picture of a vanilla item
  with the same inventory picture (`invfile`), or with a picture the mod's DC6 copies or recolours.
- Match rule for pictures: same size within 2 px and at least 92% overlap of the opaque pixels.
- The name and token matching runs in the mod's `mod.js` at install time, so it follows the
  mod list. Only the picture matches are stored (alias tables); re-run `build` after adding mods
  that bring their own sprites. `hdmatch.report.json` in the mod lists every decision.
- First run (2026-11-14, current D2RMM list): 7 monsters (evilhole2-5, wolfrider1-3), 1 base
  item and 142 uniques (the R72/R74 uniques) got HD art; the mod.js was checked offline against
  the merged data with a stand-in for the D2RMM API. Not yet seen in the game.
- Monsters with really new art (no match) still need `LegacyToHd.py` / `ScaledMonster.py`.

## Data mod to D2RMM mod

`Convert-D2RDataMod.ps1` / `.bat` (wrapper) → `ConvertDataMod.py` (+ `ConvertDataModCheck.js`,
`MpqArchive.py`)

A data mod ships whole game files (`<mod>\<Name>.mpq\data\...` with `modinfo.json`, or
`<mod>\data\...`, maybe with a `d2rloader\` folder of plugins). D2RMM can install that as it is,
but every file then replaces the game's outright: other mods' changes to the same tables are lost,
and the tables stay at the game version the mod was made for. The converter leaves the mod's files
where they are and adds `mod.json`, a generated `mod.js`, `README.md` and `d2rmm\` (patches and a
report) to the mod folder:

- tables the game also has (`global\excel\**\*.txt`) become row patches: rows are matched by their
  first column and the how-many-th row with that name, and a row the mod renamed in place (game
  rows replaced by as many mod rows at the same spot, e.g. Frankenstein's Poison Dagger → Poison
  Weapon) counts as a change of that row. How rows are merged (`-Rows`):
  - `keep` (default since 2026-11-14): every row stays where it is (row numbers are what saves,
    plugins such as Classless's and other tables point at), rows the mod deleted stay too, the mod's
    new rows go at the end, and row numbers in the mod's cells follow their rows (`missiletype` in
    weapons/misc/armor, skill numbers in item properties). The conversion can sit anywhere in the
    list; mods made for it go below it.
  - `rebuild`: the table takes the mod's own row order (the data mod exactly), rows earlier mods
    added go after it, deleted rows go. Only for a conversion used alone or at the very top.
- every change belongs to a feature (inventory, cube recipes, runewords, uniques and sets, affixes,
  item bases, drops, monsters, areas, skills, characters, vendors, interface, visuals; tables and
  text everything depends on are "core") and every D2RLoader plugin (DLL with its .mpq/.ini and its
  `config\<name>.toml`) and patch is a unit: each gets an on/off switch in the converted mod's D2RMM
  settings. `-Plugins packages` (Python `--plugins packages`) writes plugins and patches as their own
  D2RLoader packages instead: zips in D2RMM's `d2rloader\` folder, which D2RMM imports on start or
  Plugins > Refresh (hand-made package folders or edited manifests make D2RMM refuse to start).
  A plugin that one of D2RMM's own packages already installs with different bytes starts switched
  off (D2RMM refuses two different files at one place).
- Plugins built from source on this machine are left out (no entry, no switch, no package; the
  mod's settings and README point to the source build). Prebuilt DLLs in downloads have been found
  infected (VanillaDeluxe's and the D2RLoader Hub's `d2rl-merc-gear-models.dll`, user 2026-11-14). A
  source workspace is any `<game>\mods\<name>\` with `packages\*.zip` (the builds) and
  `upstream\plugins\<plugin>\` (the sources), such as `WildHealer-D2R-Tools`; a downloaded plugin
  matches by DLL name, or by `d2rl-<plugin>`, or through that folder's optional
  `source-built-aliases.json`. `--source-built <folder>` names other workspaces, `--source-built none`
  turns it off. `--d2rmm <folder>` names D2RMM's folder (default: the one the mod is in), whose
  packages are checked for plugins installed already. Files listed but no longer on disk (a virus
  scanner removed them) are left out with a warning.
- string files the game also has (`local\lng\**\*.json`) are merged by Key (and occurrence: the
  game's own files repeat some Keys).
- everything else is copied as it is; files identical to the game's are skipped.
- `d2rloader\` (plugins, config, patches, sounds...) goes to D2RMM's d2rloader output, as D2RMM does
  for data mods; logs, backups and the package's `metadata.json` stay out.

```powershell
.\Convert-D2RDataMod.ps1 -GamePath '<game>' -Mod '<D2RMM>\mods\Reimagined' -Author ScottieKnowz -Check

# a packed archive (a real .mpq file, as D2RLoader packages ship): extracted into -Mod first
.\Convert-D2RDataMod.ps1 -GamePath '<game>' -Archive '<download>\FMMP-Experimental-R67\FMMP-Experimental-R67.mpq' `
    -Mod '<D2RMM>\mods\FrankensteinMod' -Author ALvl4Ninja -Check

python MpqArchive.py list <archive.mpq>      # what is inside, flags, compression
```

`-Check` proves the result: every patch applied in Python to the game's file must give the mod's
file, then mod.js itself runs in a mock D2RMM and every table and string file it writes is compared
with the mod's (copies are counted). Patches reach mod.js through `D2RMM.copyFile` into a scratch
file plus `D2RMM.readJson` (D2RMM has no call to read a mod's own files; D2RMM keeps copied files in
memory and reads them back); the scratch file `d2rmm-convert\<id>.json` is left empty in the output.

In `keep` mode `-Check` compares by row instead: the game's rows at their places with the mod's
values, the mod's new rows appended in its order, and moved row numbers pointing at the same rows as
in the mod's own files. `d2rmm\convert.json` keeps the settings the mod was converted with
(`settings`: name, author, version, rows, plugins, source), which an update reuses; a rerun keeps
the name and version in `mod.json` unless `-Name` / `-Version` are given.

Notes:
- Mods built on the stock skill trees (the skill-page mods) go below a conversion and fit
  themselves to its trees; run `Test-D2RMod.ps1 -KeepGoing` on the whole list (a mod that throws is rolled back and the
  rest still run, as in D2RMM).
- Total conversions that add levels cannot be stacked: Reimagined (138-165), VanillaDeluxe
  (137-294) and Frankenstein (138-259) put their new levels on the same level numbers, and
  VanillaDeluxe's maps plugin checks its own level and cube-recipe layout.
- A mod that ships its tables only as compiled `global\excel\*.bin` (Rebirth) cannot be patched:
  D2RMM runs the game on `.txt` tables, so those files are copied but do nothing. The converter
  warns; such tables have to be decompiled to `.txt` first.
- `MpqArchive.py` is written from the MPQ format description: format 0-1, encrypted / fix-key /
  single-unit files, zlib, bzip2 and PKWARE DCL implode (mask 0x08 and the old IMPLODE flag;
  decoder written from the format description). D2RLoader packages hash names as written
  (`data/global/...` with forward slashes); the reader tries that and the backslash form.

### Mod converter (window)

`Start-D2RModConverter.ps1` / `.bat` → `ModConverter.py` + `ModConverter.html` (local web page on
`127.0.0.1:8766`)

```powershell
.\Start-D2RModConverter.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected'
```

- **Convert a mod**: a folder, a `.zip` / `.7z` / `.rar` download (needs 7-Zip) or a packed `.mpq`.
  "Look inside" extracts it (into D2RMM's `converter-work\`), unpacks packed `.mpq` files found in
  it, finds the mod data and its `d2rloader` folder, and shows the files per feature, the plugins and
  patches, the D2RLoader binaries it leaves out (D2RMM brings its own loader) and tables that exist
  only as `.bin`. Then it puts the mod into D2RMM's `mods\` and converts it with `-Check`.
- **Update a converted mod**: the new download of a mod converted before. The old data folder and
  `d2rloader` go to `<mod>\d2rmm\previous`, the new ones take their place, and the conversion runs
  again with the saved settings (the switches set in D2RMM keep their ids). The log lists the
  features whose file count changed. If the conversion fails, the old files are put back.
- **Converted mods**: what is in D2RMM's mods folder, how it was converted and from where.
- A mod the converter cannot redo itself (one made from compiled `.bin` tables, such as Rebirth Skill
  Versions) can name its own updater in `<mod>\dev\update.json` (`{"script": "update_x.py", ...}`):
  Update then runs `python <script> <download> --game <D2R folder>` and shows its log.
- Tables that are not UTF-8 or have duplicate column names, and string files whose repeated Keys
  cannot be rebuilt, are copied whole; `d2rmm\convert.json` lists them.
- Update also packages the download's **other** `d2rloader` folder (a D2RLoader setup has one
  beside `mods\`, e.g. VanillaDeluxe's item-quality-backgrounds and rune-gamble-gheed): each plugin
  (DLL + its `.mpq` + its `config\*.toml`) and patch becomes a zip `<mod>-<plugin>.zip` in
  `<D2RMM>\d2rloader` (D2RMM imports it on start or Plugins > Refresh). Left out: loader settings,
  what an installed package already puts there with the same bytes, a different file another
  package puts at the same place, plugins with a source build. Noted in `convert.json`
  (`extraLoaderFolders`).
- A mod made from compiled tables with a full conversion (Rebirth) has `<mod>\d2rmm\update.json`
  with `"method": "merge-compiled"` and `"mpqName"`: Update extracts the new packed `<name>.mpq`,
  merges its tables onto the game's (`MergeCompiledMod.py`, below), takes the version from
  modinfo.json / its "Mod Version:" line, and converts with the saved settings (rows rebuild).
- **Row matching** (Convert and Update panes; `ConvertDataMod.py` flags; saved in `convert.json`
  `settings`, so an update keeps them; mods converted before they existed get the defaults):
  - *Row names: spaces around them* - `--match-trim` (default) / `--no-match-trim`. The game's
    `cubemain` has a recipe description with trailing spaces that VanillaDeluxe's copy lacks; matched
    exactly, the game's recipe stayed (ilvl 75) and the mod's came in as a new row.
  - *Rows that share a name* - `--duplicates content` (default) / `order`. The game's 8 `Rainbow Facet`
    rows are matched to the mod's rows by what is in them (most alike first, ties by order), and
    left-over ones to the mod's new rows whose name starts with theirs (`Rainbow Facet Cold`, 3/4 of
    the cells alike). By order, VanillaDeluxe's facets came out as 10 that drop instead of 4.
  - *Rows the mod deleted* (rows keep only) - `--deleted disable` (default) / `leave`. Keep mode never
    removes a row (row numbers); with disable the row is switched off: `spawnable` 0 in uniqueitems,
    setitems, magicprefix/suffix, automagic; `enabled` 0 in cubemain; `complete` 0 in runes.
    `-Check` verifies it. Counts per table: `convert.json` `rowMatching`.
- **Load order** (a *Load order* section in the converted mod's D2RMM settings; the converter only
  sets the defaults: `--rows`, `--conflicts`, `--files`, also in the Convert/Update panes, saved in
  `convert.json` `settings`):
  - *Rows* - keep / rebuild, switchable at install time (the patches serve both; deleted rows carry
    their switch-off column either way). A mod converted with rebuild warns that keep cannot move
    every row number it relies on. In rebuild, the install log warns when a mod comes before it.
  - *Conflicts with mods above* - `--conflicts mod` (default, this mod's value) / `earlier` (the mod
    above keeps its value; this mod only changes what nobody touched). The patches hold the game's
    value of each changed cell (`=` entries' 4th element) and each changed string entry, so mod.js
    can tell; strings now change only the fields the mod changed (an earlier mod's other languages
    stay), and a new Key an earlier mod also added is one entry. The install log lists every clash.
  - *Files a mod above already put in* - `--files overwrite` (default) / `keep` (`copyFile` without
    overwrite).
  - Test without D2RMM: `node ConvertDataModCheck.js <mod> <cache> <out> '{"loadorderCells":"earlier"}' <earlier folder>`
    (files in `<earlier folder>` stand for what mods above left; `CHECK_MODLIST` fakes the mod list).

  `Update-D2RConvertedMod.ps1 -MatchTrim $false -Duplicates order -Deleted leave` overrides them.

Without the page (same code), for one or more mods; no `-Source` = the download in `convert.json`,
which also redoes a conversion after a game patch:

```powershell
.\Update-D2RConvertedMod.ps1 -Mod VanillaDeluxe, Rebirth
.\Update-D2RConvertedMod.ps1 -Mod Rebirth -Source "$env:USERPROFILE\Downloads\Rebirth-Re.zip"
```

`MergeCompiledMod.py <extracted mod> <out mod folder> [--name Rebirth]` on its own: three-way merge
of a mod's `.bin` tables (game `.bin` and mod `.bin` decompiled the same way, only differing cells
taken onto the game's `.txt`, new rows from the mod, the mod's row order, `levels` + `leveldefs`),
written as `<out>\<name>.mpq` with the mod's other files and `merge-report.json`.

## Compiled tables back to text (`.bin` decompiler)

`BinTables.py` + `BinCalc.py`

Some mods ship their tables only compiled (`global\excel\*.bin`, e.g. Rebirth). D2RMM runs the game
on `.txt` tables, so such changes do nothing there until they are text again. The record layouts
are not documented and move with patches, so `BinTables.py infer` works them out from the game: the
archive has every table as `.txt` and `.bin`, and each column is matched against every byte place
of the records (ints of each width, -1 kept in unsigned fields, flags and 2-3 bit fields, char
arrays, 4-letter codes, rows of other tables by any of their first three columns, language-file
string ids, learned enums such as `range`, and formulas). Fields are naturally aligned; what the
game's data cannot tell apart is settled by elimination, the rest marked `guessed`.

```powershell
python BinTables.py roundtrip skills skilldesc missiles states   # decompile the game's .bin, compare with its .txt
python BinTables.py decompile <mod data folder> --out <folder> skills skilldesc missiles states itemstatcost
python BinTables.py report skills                                 # where each column sits
```

Formulas (calc columns) are offsets into `skillscode.bin`, `misscode.bin`, `skilldesccode.bin`;
`BinCalc.py` turns the bytecode back into text, fully parenthesised. D2R's bytecode, as checked on
the game's tables: 7/8/9 numbers, 4/5/6 a keyword (row of skillcalc / misscalc), `1 f n` a call
with an argument count (1.14d has none), 10-15 comparisons, 16-20 `+ - * / ^`, 22 negate, 23 `?:`
(1.14d: 21/22), 2 a stray `(` from unbalanced text where the game stops. Inside `skill('X'.code)`
the code is a skillcalc row also in missile formulas. Reference for the evaluator: Redivivus
(github.com/jaenster/redivivus, MIT), used as a map only.

Round trip on 3.4.95041 (cells identical): skills 99.97%, skilldesc 99.8%, missiles 99.3%,
itemstatcost, states, overlay, pettype 100%, monstats2 99.9%, properties 99.8%; monstats 98.2%
(NameStr and Sk*mode not found yet). Rows the compiler drops (`Expansion`) are left out of row
numbers. Layouts are cached in `%LOCALAPPDATA%\D2RModAssetsinlayouts` (delete after a patch).

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
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Check     # report only
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected'            # patch
.\Set-D2rmmLimit.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Restore   # put app.asar.bak back
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
.\Test-D2RMod.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Mod '<D2RMM>\mods\DruidPoisonDisaster'

# several mods in load order (clashes between mods show up this way), an option overridden,
# and the list of files it took written down
.\Test-D2RMod.ps1 -Mod '<D2RMM>\mods\QuillRatDruid','<D2RMM>\mods\DruidPoisonDisaster' `
    -Config 'testMode=true' -Manifest .\needed_files.json

.\Test-D2RMod.ps1 -Mod '<mod>' -Dump        # also print every row the mods added (-DumpBase: classic-rules tables)

# every file the mods wrote, saved as written, to compare two runs byte for byte (before/after a refactor)
node ModHarness.js --game '<game>' --out .\run-before '<mod>'
```

Exit code 0 = no problems, 1 = problems, 2 = a mod script threw. Mod options come
from `mod.json` defaults, then the mod's `config.json`, then `-Config`. Files a mod copies
in with `D2RMM.copyFile` are read back from the mod folder by later reads, as D2RMM does.

### Skill-page mods on reworked class trees (`TreePlacement.py`)

The skill-page mods put each new skill in the tree cell of a stock skill of the parent tab
(its `slot`) and copy that skill's level, prerequisites and icon. Total conversions move or
remove stock skills, so the shared `placeOnTree` (`TreePlacement.js`) picks, per new skill:
the slot skill if it is a class skill on the parent tab (the plain game: always, so the
output there does not change), else the skill now in the slot's stock cell, else another
skill of the parent tab not yet taken, else an empty cell with the stock level and icon.
Prerequisites that no longer lead to a new skill of the page are left out, with a warning.

`TreePlacement.py` writes the code and each mod's `STOCK_CELLS` table (stock cell, level,
icon and prerequisites of its slot skills, read from the game's own tables) into marked
blocks of the mod.js; rerun it after changing `TreePlacement.js` or a mod's slots:

```powershell
python TreePlacement.py --game '<game>' '<D2RMM>\mods\SorceressSecondPages' '<D2RMM>\mods\BarbarianSpiritsShaman'
python TreePlacement.py --game '<game>' --check '<D2RMM>\mods\SorceressSecondPages'    # report only
```

Used by Sorceress pages, Venom Calling/Disasters, Alchemy Tools, Knife Arts, Blood Magic and
the Barbarian pages (not by Quill Rat Druid and Darkness Magic, which place their skills
their own way).

### Template rows from the plain game (`StockRows.py`)

The page mods build their rows (skills, descriptions, missiles, states, monsters, pet types,
sounds, items) from copies of stock rows and fill in their own columns. Every column they leave
alone keeps what the installed table has, so a total conversion above them leaked its edits
of those stock rows into the new skills (with Frankenstein: its Bone Spear volley on five
Darkness Magic skills, cooldowns, lost `KeepCursorStateOnKill`, monster group sizes...).
`StockRows.js` has the helper `stockRow(tsv, col, name, file, set)`, which returns a copy of
the plain game's row in the table's own columns (or undefined when the mod does not embed
it); a mod's template copy (its `cloneRow`) asks it first and falls back to the live row, and
sets `stockSet = 'main' | 'base'` for each set of tables. Tree placement (`placeOnTree`) still
reads the live tables, so cells, levels and prerequisites follow the conversion.

`StockRows.py` writes the code and each mod's `STOCK_ROWS` / `STOCK_ROWS_BASE` tables (classic
rows only where they differ) into marked blocks of the mod.js, in front of `function findRow(`.
It finds the rows a mod copies by running it with `ModHarness.js` on the plain game with the
option `recordStockRows` on (stockRow then logs every name it is asked for), once with the
default options and once for every other checkbox and list value in its `mod.json`; the rows
come from the harness cache. Rerun it after a game patch or when a mod copies other rows:

```powershell
python StockRows.py --game '<game>' '<D2RMM>\mods\DarknessMagicNecro' '<D2RMM>\mods\DruidGiantRaven'
python StockRows.py --game '<game>' --check '<D2RMM>\mods\DarknessMagicNecro'    # report only
```

The key column tells the table (`skill`, `skilldesc`, `Missile`, `state`, `pet type`, `Id` =
monstats, `Sound`, `Code` = itemtypes, `code` = weapons); other tables pass `file` (Wild Boar's
monsounds copy passes `'monsounds'`). Used by the same page mods plus Darkness Magic, Giant
Raven, Wild Boar and Weather Magic (2026-11-14); Quill Rat Druid has its own older
`dev\stock_rows.py`. On the plain game every mod's output stayed byte for byte the same.

To check for leaks, `LeakCheck.js` runs the mods with the harness on the plain game and with a
conversion first, and compares every row the mods add, cell by cell (tree placement, `maxlvl`
and `InTown` left out; `--ignore` changes that). Columns holding row numbers computed from the
installed tables (the bombs' `missiletype`, the forms' `gfxclass`, classic missile pads) differ
for good reason. Exit 1 when something differs, 2 when a mod fails:

```powershell
node LeakCheck.js --game '<game>' --python <python> --conversion '<D2RMM>\mods\FrankensteinMod' '<D2RMM>\mods\DarknessMagicNecro' '<D2RMM>\mods\DruidGiantRaven'
```

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
$env:D2R_PATH = 'D:\games\Steam\steamapps\common\Diablo II Resurrected'
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
.\New-RecoloredEffect.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Audit

# build into a D2RMM mod folder and rewrite the manifest block in its mod.js
.\New-RecoloredEffect.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -OutDir '<D2RMM>\mods\DarknessMagicNecro' -PatchMod
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

## Updating the plugins for a new D2RLoader

`Update-D2RPlugins.ps1` / `.bat` (wrapper) → `PluginSdk.py` + `PluginAddresses.py`

The plugins in `<game>\mods\<plugin>\plugin` (SkillTab4, PetAI, BloodCost, HybridScale, DualThrow,
Alchemy, BotHarness, SkillTrace, ReachableDrops, and SkillTab4's probe) depend on D2RLoader twice:

- **the SDK** they compile against: one shared copy, `<game>\mods\SkillTab4\sdk` (D2RLoader's public
  PluginSDK, MIT; 0.3.0 matches loader 1.3.1-beta);
- **the game addresses** they hook (`constexpr std::uint64_t <Name>Rva`, mostly with the bytes they
  expect there, `<Name>Expected[]`) in the game image the loader runs.

```powershell
.\Update-D2RPlugins.ps1 -Root '<game>'          # report only: SDK status and the address check
.\Update-D2RPlugins.ps1 -SdkDiff                # what changed in the upstream headers, which plugins use it
.\Update-D2RPlugins.ps1 -SdkTrial               # build every plugin against upstream in a temp folder
.\Update-D2RPlugins.ps1 -SdkApply [-Force]      # keep the old copy as sdk-<version>, swap, rebuild all
.\Update-D2RPlugins.ps1 -SdkRestore [-To 0.3.0] # put a kept copy back
.\Update-D2RPlugins.ps1 -FixAddresses           # write moved addresses into the plugin sources
.\Update-D2RPlugins.ps1 -SelfTest               # proves the address search on a shifted copy of the dump
```

**SDK.** The PluginSDK repository runs ahead of the loader: its `master` describes the next loader
release (0.4.0 on 2026-11-14 while the newest loader, on d2rloader.net, was still 1.3.1-beta of
2026-09-23). `status` compares the installed copy, upstream, the installed loader (log and
`D2RLoader.exe` date) and the newest published loader (the official installer's manifest,
`https://d2rloader.net/download/manifest.json`). What decides whether rebuilt plugins keep working
on an older loader are the service size checks (`HasXServiceField(x, XServiceRequiredSize)`): the
tool computes every `...RequiredSize` of both copies by compiling a small program (MSVC), since a
definition can change while its value stays (0.4.0 grew `WidgetService` from 64 to 208 bytes but
kept `WidgetServiceRequiredSize` at 64, so SkillTab4 still finds the widget service on 1.3.1-beta).
`apply` refuses (unless `-Force`) only when a size a plugin checks really grew while the newest
published loader is still the installed one. Measured on 2026-11-14: all 10 plugins build against
0.4.0 unchanged and no checked size changed; 0.4.0 only adds `ItemDetails` and
`KeyListenerRegistration` (new features of the next loader). `apply` never installs anything:
the rebuilt DLLs land in each plugin's `dist\`; copy them to `mods\D2RMM\d2rloader\plugins` and to
D2RMM's `d2rloader\<name>\source\` (with the new SHA-256 in its `manifest.json`) when ready.

**Addresses.** Needs a dump of the running game image from the SkillTab4 probe
(`<game>\d2rloader\data\skilltab4-probe\image-<build>.bin`, file offset = address). For every
address: same bytes as expected → ok; otherwise it takes the function that holds the address in the
old dump (from the image's `.pdata` table), masks what changes when code moves (relative calls and
jumps, rip-relative operands), finds it in the new dump and reports the new address (and new
expected bytes if they differ); identical copies of a function are told apart by their neighbours.
Not covered: addresses in `D2RCore.dll` (names with `Core`; not in the dump) and in data sections,
and addresses kept in tables (PetAI's AI routines, HybridScale's) which are only checked for changes:
those are listed for checking by hand. The old dump defaults to the one matching the plugins'
expected bytes best, the new one to the newest dump. `-SelfTest` inserts 0x1230 bytes before the
first hooked routine and must find all 38 code addresses at their moved place (it does). Needs the
`capstone` Python module.

**When the next loader comes out:**
1. Install it with the official installer (the game closed).
2. `Update-D2RPlugins.ps1`: `loader published` shows the new version; check the SDK verdict.
3. D2RMM, Plugins tab: enable **SkillTab4 Probe**, install, start the game to the menu once, close
   it, disable the probe again. A new `image-<build>.bin` appears.
4. `Update-D2RPlugins.ps1` again: the address check now compares against that dump. If addresses
   moved, `-FixAddresses`, then read the diff of the plugin sources.
5. `-SdkTrial`, then `-SdkApply`. Fix any plugin that fails, or `-SdkRestore`.
6. Copy the rebuilt DLLs into D2RMM (see above), install, and read the loader log
   (`Get-D2RLoaderLog.ps1 -Plugins`): every plugin must report its patches as applied.

## Loader log reader (what the game itself complained about)

`Get-D2RLoaderLog.ps1` / `.bat` (wrapper) -> `LoaderLog.py`

D2RLoader writes every failed game check to `<game>\d2rloader\logs\d2rloader.log`: the
source file of the check and, for data tables, the file, row, column and cell value. The log
covers the last game session. **Read it first when something misbehaves in the game** - it
usually names the cause, and it shows which build was actually running (compare the session
start with the time of the last install and of the last edit).

```
.\Get-D2RLoaderLog.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected'            one entry per distinct check
.\Get-D2RLoaderLog.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -All -Plugins
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
(`D:\games\Steam\steamapps\common\Diablo II Resurrected\mods\BotHarness`, its README has the command list)

Starts the game with a script that drives it (console cheats, UI messages, keys,
mouse) and collects what happened (game events, monster deaths, screenshots) in
a run folder under `<game>\d2rloader\botharness\runs\`.

```powershell
.\Invoke-D2RBotTest.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Script .\BotScripts\smoke-menu.txt
.\Invoke-D2RBotTest.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Commands 'waitfor menu','screenshot menu' -NoWait   # step by step
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
