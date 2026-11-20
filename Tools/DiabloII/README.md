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

**Removing geometry** (2026-11-16): `"remove"` in `"reshape"` is a list of rules, applied to
every LOD file after the edits above (`GrannyMesh.remove_geometry`; the file is rebuilt through
`Granny.py`, so vertex and triangle counts can change):

```json
"remove": [
  { "bones": "spike_", "below": true, "weight": 0.6 },
  { "box": { "min": [-1, 0, 2.5], "max": [1, 1.5, 4] }, "mesh": "QuillratShape" }
]
```

- `bones`: triangles whose three vertices follow those bones (a name, a name start, a list, or
  `{"prefix", "first", "last"}`; `"below": true` adds every bone under them) by at least
  `weight` in all (default 0.5). A lower weight also takes the parts where they join the body.
- `box`: triangles whose vertices lie in a model-space box (bind pose); `"outside": true` takes
  the rest. `"any": true` on a rule takes a triangle when one vertex is selected, not all three.
  `"mesh"` limits a rule to one mesh.
- Unused vertices are dropped and renumbered; material groups, the mesh box and each bone
  binding's box are recomputed (checked: the formula reproduces the stock boxes to 0.0001). The
  bone bindings stay, so the skin and the donor's animations still fit.
- `"cap": true` on a rule closes the holes that rule opens (2026-11-19): each hole gets a fan
  of triangles from its rim to a new vertex in the middle, which copies the skin weights of the
  nearest rim vertex, takes the mean of the rim's UVs (the texture smears over the cap) and
  faces out of the hole. Without it the opening stays open. Edges that are open in the stock
  mesh are left alone, and a rim that does not close into a ring is reported and left open. A
  fan suits roundish openings (a stump, a limb cut across); a long or bent cut gets a rough cap.
- A mesh may not lose every triangle (drop the model instead).
- Command line: `python GrannyMesh.py remove <in.model> <out.model> '<rules JSON or file>'`.
- Tested 2026-11-16, offline only: the Spike Fiend body without its quills (27541 -> 22312
  triangles in LOD 0, all five LODs through a preset), and a box cut; not seen in the game.
  Capping tested 2026-11-19, offline only, on the same body: 60 quill stumps closed with 303
  triangles, and a box cut across the torso and four legs closed; no edge shared by more than
  two triangles, caps wind like the stock faces, the file reads and writes back equal.

**Adding geometry** (2026-11-19): `"add"` in `"reshape"` is a list of parts put into the body
(`GrannyMesh.add_geometry`), applied to every LOD file after the vertex edits and before
`"remove"`, so a remove rule can trim an added part too:

```json
"add": [
  { "from": "hd/vfx/meshes/lit_mesh/bonewall/model_source/fx_mesh_bone_tusk",
    "bone": "jaw_bind_jnt", "space": "bone", "origin": "center",
    "scale": 0.5, "rotate": [0, 0, 20], "translate": [0.3, 0.1, 0.3], "twin": "x",
    "uv": [0.02, 0.02, 0.2, 0.2] },
  { "pick": { "bones": { "prefix": "spike_", "first": 30, "last": 40 }, "weight": 0.6 },
    "translate": [0, -0.2, -1.2] }
]
```

- `from`: the model the part comes from, an archive path with or without `_lodN.model` (a stem
  takes the body file's LOD, or the nearest more detailed one the part has). Left out: the body
  itself, as it was before any rule. `mesh` takes one mesh of it, `pick` some of its triangles
  (a remove rule's `bones` / `box` selection); `to` / `group` choose the body mesh and material
  group (default: the first).
- `bone`: the body bone that carries the part (every added vertex follows it alone; a bone the
  mesh did not use gets a bone binding). Left out: the part keeps its own skin weights and its
  bones are found by name in the body's skeleton, which is what a copy of the body's own part,
  or a part from a model on the same skeleton, needs.
- Placement: `origin` (a point, `"center"`, or a source bone), then `scale`, `rotate` (degrees,
  X then Y then Z), `translate`; `"space": "bone"` places it in the bone's bind-pose frame, as
  attachments are placed, otherwise in model space. `"mirror": "x"` reflects the placed part to
  the other side; `"twin": "x"` adds the part and its mirror image.
- Textures: the part wears the **body's** material (every stock model has one material and one
  group per mesh). `"uv": [u0, v0, u1, v1]` fits its UVs into a patch of the body's texture;
  without it the UVs stay, which is right for a copy of the body's own part. For a part with
  textures of its own, write it as its own model on the body's skeleton:
  `add_geometry(..., alone=True, textures={old: new})` or `GrannyMesh.py add ... --alone
  --textures '{...}'` keeps only the added parts (with their skin) and renames texture paths (any
  length). The pipeline does not list such a second model in the definition yet.
- Normals and tangents turn with the part, a mirrored part gets its winding flipped, boxes are
  recomputed. When a part reaches past the mesh's `VertexScale` the scale grows and the stock
  vertices are stored again (they move by less than 0.0001). At most 65535 vertices per mesh.
- An added part is not welded to the skin: it pokes out of the body like a prop, but it is part
  of the mesh, so it is drawn in one piece with the body and can bend with several bones.
- Command line: `python GrannyMesh.py add <in.model> <out.model> '<rules JSON or file>' [--game
  <D2R folder>] [--alone] [--textures '<JSON>']`.
- Tested 2026-11-19, offline only, on the Spike Fiend body: a static quill mesh rigid on the
  head, the Act 5 barbarian's horns and the bone wall's tusk from the archive (twin), a copy of
  ten of its own quills with their skin, a mirrored part, `--alone`, and a preset with `add` +
  `remove` through all five LODs. Every result reads and writes back equal, has no edge shared
  by more than two triangles, weights that sum to 1 and faces wound like the stock ones. Not
  posed with an animation, not seen in the game.

`Granny.py`'s writer could not write a model with materials before this: a member whose type is
the struct around it (a material map's `Map`, a material) was not handled. The reader now marks
it `'$recursive'` / `'$recursive:N'` (N structs further out) and the writer resolves both; 45
character models read and write back equal. The same fix makes animation files the toolkit
writes carry the same type table as the game's own (before, one such member pointed at the
wrong type; the game played those files anyway). Clip data is unchanged.

A variant with `"reshape"` can also wear its own textures: `"retexture"`
entries (`from`, `to`, `format` bc1/bc3/rgba8, `recolor` as in the recoloured
effect pipeline) write a recoloured copy (block by block, so format and mips
stay) and point the rewritten models at it. The new path must be as long as the
old one, because the model's texture name is swapped in place.

`"detail": {"kind": "feathers", "scale": 2, ...}` on a retexture entry redraws a
feather-card albedo instead (`TextureDetail.py`, 2026-11-19): twice the size,
the recolour applied per texel, and per stock card (found from the alpha mask:
axis, tip, rachis) barbs angled to the tip in clumps with a few vane splits, a
soft sheen (`glossColour`), a rachis highlight, and alpha with the texel steps
smoothed and the margins slightly frayed, so a scaled-up body shows no saw-tooth
card edges. It is written in the game's layout (BC3 sRGB, header as
`HdTexture.from_image_bc3`, full mip chain) through DirectXTex texconv
(`--keep-coverage 0.5` keeps cutout cards from thinning in the mips; Pillow when
texconv is missing) and read back before it is kept. `python TextureDetail.py
feathers <stock.texture> <out.texture> --png <preview.png>` runs it alone. Used by
the Giant Raven (2048 from the 1024 `druidhawk_feather_alb`); not seen in game.

A preset's `"modelIndexIncludes": ["../OtherMod"]` only matters for a mod that
still ships the whole index (`model_index.json` `"index": "whole"`): it carries
the other mod's models in this mod's `hd/model_lod_desc.bin` (entries keep
`"source"`). With the AssetMerge plugin (the default since 2026-11-15, see "The
model index") each mod lists only its own models and the includes are dropped.

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

**AssetMerge (2026-11-15, the default).** A whole index (or `global/animdata.d2`)
shipped by several mods means the one installed last hides the others' entries.
The AssetMerge D2RLoader plugin (`<game>\mods\AssetMerge`, README there: RVAs,
fragment format) merges text fragments into both files when the game loads them:
`global/excel/d2rloader/assetmerge/models.txt` (model, donor, lod, mesh, box)
and `animdata.txt` (name, source, frames, speed, events). `AssetMerge.py models
--mod <mod>` writes a mod's rows into its mod.js as a generated block plus the
shared `assetMergeWrite`; the mod calls `assetMergeWrite(assetMergeModels())`.
`ModelLodDesc.py update`/`check` and `ScaledMonster.py` do the same for a mod
whose `model_index.json` has `"index": "assetmerge"` (the default for any mod
without `"index": "whole"`), and remove a stale `hd/model_lod_desc.bin`. Timing
rows come from a build script through `AssetMerge.write_block(mod_js,
'animdata', rows)`. `ModHarness.js` checks the merged fragments and warns when a
mod still copies either whole file. Block markers are whole lines written by the
tool; never start a comment line with `// <assetmerge:` (2026-11-15: such a
comment made the first version of the replace delete a stretch of a mod.js; the
marker match is now anchored and refuses blocks holding other code).

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
B-spline formats D4nK16uC15u, D4nK8uC7u, D3K16uC16u, D3K8uC8u, D3I1K*, D9I1K*,
D9I3K*, DaK16uC16u, DaK8uC8u, the constants, DaK32fC32f and D3I1K32fC32f) and
then treated as keyframes; new clips are written as plain linear float keys.
Checked 2026-11-16: every curve of the game's 245 HD character animation files
decodes (DaK8uC8u / DaK16uC16u had kept the Skeleton, the Act 5 barbarians and
others from being used as a base). `clip.pose(t)`, `GrannyAnim.skin(...)` and
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
- More clip options (2026-11-16):
  - `"reverse": true` plays a clip or part backwards; `"mirror": true` has the other side of the
    body do it (a right-hand claw becomes a left-hand one; `Keys.mirrored`).
  - A `layer` edit lays another clip over a bone and everything below it, at the same progress:
    `{"layer": "attack1", "bones": "spine_01_bind_jnt", "weight": [[0, 0], [0.15, 1], [0.85, 1], [1, 0]]}`
    on a `walk` base gives a claw attack on the move (legs keep walking). `from`/`to` take a piece
    of the other clip, `"at"` one pose of it, `"only": true` the named bones alone.
  - `"seamless": 0.25` bends the last quarter of a clip into its first pose, for loops.
  - `"hit"` in a curve: the point of the clip where the legacy animation of its mode deals the hit
    or launches the missile (the COF's trigger frame over its frame count; the Spike Fiend's A1:
    frame 11 of 16 = 0.69). `["hit", -30]`, `["hit-0.1", 0]`, `["hit+0.05", ...]`. The pipeline
    reads it from the donor's audit for the clip's mode (`mode`, or a clip named after one);
    `"hit": 0.6` on a clip sets it by hand. The report lists the value used. Presumed, not seen:
    stock HD clips are not as long as their legacy animations (ratios 0.8 to 4 measured on the
    Zombie, Fallen and Spike Fiend), so the game stretches the clip over the legacy span and the
    hit lands at that fraction of it.
  - A curve may be one number (`"weight": 0.5`).
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

### A body made outside the game (`MeshImport.py`)

For a creature that is new from the ground up (2026-11-19): a mesh from Blender, a sculpt or an
image-to-3D model takes a donor's place in the game: its skeleton, bone bindings, material slot
and LOD files, so the donor's clips (and clips authored on its skeleton) move it. The skin is
carried over by position: every new vertex gets the bone weights of the donor surface nearest
to it. So the mesh is modelled around the donor in its bind pose.

```
python MeshImport.py reference --game <D2R> --donor hd/character/enemy/pig/torso --out <folder>
python MeshImport.py build spec.json --game <D2R> --out <mod folder>
```

- `reference` writes `donor.obj` (bind pose, +Y up, +Z to the head, one unit = a foot),
  `donor.png` (its colour texture) and `bones.json` (joint positions): import the OBJ in Blender
  and build the new body over it, legs on legs, head on head.
- `build` reads anything `trimesh` reads (`.obj`, `.glb`, `.gltf`, `.ply`, ...) with UVs. Spec:
  `name`, `mesh`, `donor`, `albedo` (a picture; a `.glb`'s own base colour is the default),
  optional `normal` / `orm`, `axes` (`{"up": "+z", "forward": "-y"}` for a file in Blender's own
  space; its glTF and OBJ exports are the default +y / +z), `fit` (`"donor"`: scaled to the
  donor's length, stood on the ground, centred; `"none"`: already in game space), `scale` /
  `rotate` / `translate`, `skin`, `lods`, `texture_size`.
- Skin: nearest donor surface points (the donor's vertices plus 150,000 points spread over its
  triangles), near ones counting most and surfaces facing the other way hardly at all (the inside
  of a mouth behind a lip), evened out over the new mesh's own edges (`"smooth"`, default 2),
  the four strongest bones kept. `"ignore": ["tongue_"]` gives the weight of bones the new body
  has no part for to the bone above them.
- Textures: the colour picture becomes a BC3 sRGB texture with a full mip chain, the layout of
  the game's own body textures (`HdTexture.from_image_bc3`; the header matches a stock file's
  byte for byte). A normal or ORM map that is not given is written as one flat colour, the
  donor map's average, so the body is smooth there instead of wearing the donor's detail on the
  wrong UVs. The model's texture names are changed to the new files.
- Tangents are computed from the UVs the way the stock bodies store them (direction of u, sign
  from v; checked against the pig: same handedness on 99.7 % of vertices). Lower LODs are made
  by merging vertices on a grid, to the donor's own triangle ratios: crude, but there is no
  decimator on this machine.
- In a preset a variant takes the spec as `"import"` (name and donor come from the variant, the
  mesh path is relative to the preset); `"reshape"` with `"add"` / `"remove"` then works on the
  imported body, and the definition, texture dependencies and model index entry are written as
  for any reshaped variant. `HdToLegacy.py` draws its legacy sprites from that definition.
- Checked 2026-11-19, offline only. The pig written out by `reference` and imported back gets
  the stock weights to within 1 % (without smoothing); pushed 0.05 to 0.15 units off the surface
  and posed with every pig clip, its vertices land within 0.02 units on average of where the
  stock skin puts them (body 7.7 long). A stand-in body built from primitives in Blender's axes
  and metres, with its own texture, imported through a preset (plus added tusks), walks with the
  pig's clip in rendered stills and went through `HdToLegacy.py`. **Not seen in the game.** The
  stand-in is a test shape, not art.
- **Own rig** (2026-11-19): `reference` also writes `donor.glb`, the donor with its armature,
  skin and texture (`Gltf.py`). A mesh weighted to those bones in Blender and exported as glTF
  keeps its own weights on import (`"skin": {"from": "auto"}`: the file's rig when one of its
  joints is a game bone; `"file"` / `"donor"` force it). `.glb` / `.gltf` files are read by
  `Gltf.py`, which keeps the rig; other formats still go through `trimesh` and get the donor's
  skin by position.
- **New bones**: a joint the game skeleton lacks, parented under one of its bones, is added to
  every model file's skeleton and to a copy of the donor's `.skeleton`
  (`hd/character/enemy/<name>/skeleton/<name>.skeleton`; a preset points the definition at it,
  and `own_animations` extends the variant's skeleton the same way). Stock clips have no track
  for it, so it holds its bind pose on its parent until a clip poses it.
- **Surface maps**: the game's normal map keeps x in alpha and y in green (red full, blue
  empty, z worked out), with green running down the picture; its ORM map has occlusion in red
  and roughness in green (blue is empty in the creature maps looked at). A `.glb`'s own normal,
  metallic-roughness and occlusion pictures are converted to that, as are `"normal"` / `"orm"`
  pictures in the usual layouts (`"normal_green": "down"` for a DirectX-style map).
  `"normal": "from_albedo"` guesses relief from the colour picture when there is no map.
- **LODs**: with the `meshlib` package (pip; non-commercial licence, see `THIRD_PARTY.md`) the
  lower LODs are made by quadric edge collapse that only keeps existing vertices and leaves open
  edges alone, so UVs, normals and skin stay exact and UV seams do not crack; when that stops
  more than half above the target (seams stay dense) the grid merge finishes the job. Without
  the package the grid merge does it all (`"simplify": "grid"` forces that).
- Checked 2026-11-19, offline only: `donor.glb` opened in Blender 5.2.3, a sixth tail bone added
  there and 41 vertices given to it, exported and imported: weights within 1.2 % of the stock
  pig's (the new bone folded back), 63 bones in every model and 66 in the skeleton file, and
  posed with every stock clip the body stays within 0.006 units of the stock pig. On the pig,
  MeshLib LODs keep all 420 open edges (grid merge: 190 at the same size, i.e. seams welded
  shut or torn) and far fewer edges shared by three faces (10 against 255 at 6,800 triangles,
  46 against 188 at 3,000). A `.glb` with normal, roughness and
  occlusion pictures comes out with the channels where the game has them. **Not seen in the
  game**, new bones least of all: whether the game accepts a model whose skeleton has more bones
  than its donor's index entry expects is unknown.
- **No donor at all** (2026-11-19): leave `"donor"` out (or set `"skeleton": "file"`) and the
  body is the file's own: its armature becomes the skeleton (every joint, any names), its
  weights the skin, its animations the clips (`<name>/animation/combined.animations`, sampled at
  `"fps"`, default 30) and a matching `<name>/skeleton/<name>.skeleton` is written. A stock
  model (`"template"`, default the Sand Leaper, `hd/character/enemy/sandleaper1/torso`) only
  lends the file format, the material slot and the LOD file count; it must be a one-mesh body
  with 16-bit indices in every LOD file (Quill Rat, Baboon, Scorpion and others qualify; the
  Spirit Wolf and Druid Bear do not). Checked offline with the pig's shape re-rigged under 62 made-up bone names
  and two clips of its own written as a `.glb`: no stock bone name is left, the rest pose
  reproduces the mesh exactly, and posed with the converted clips every vertex lands within
  0.005 units of where the file's own animation puts it (the clips move vertices by up to 0.85).
  **Not seen in the game.**
- **Donor-free in a preset** (2026-11-19): a variant with no `"donor"` whose `"import"` file
  has a rig is built the same way through `ScaledMonster.py`:

  ```json
  { "name": "my_beast", "template": "sandleaper1", "scale": 1.1,
    "import": { "mesh": "beast.glb", "modes": { "NU": "idle", "WL": "walk", "A1": "bite" } } }
  ```

  `"template"` (default `sandleaper1`; any stock monster with a one-mesh body) lends the definition's layout, the state
  machine's states and transitions, and the file formats. The models, the `.skeleton`, the
  animation file and the state machine's clip list are the file's own. Each state plays the
  clip `"modes"` names for its mode; failing that a file clip called like the state's stock
  clip (`walk`); failing that the idle clip as a stand-in, so no state is without motion
  (`"fallback": false` leaves such states as the template has them). `"animations"` clip specs
  build on the file's clips. The template's `IKComponent` is dropped (it names the template's
  bones). The model index row copies the template's record layout (LOD and mesh counts) with
  the body's own boxes. Checked offline: the definition, state machine (17 states, three bound by
  `"modes"`, the rest to the idle stand-in), skeleton and index rows are written, and `HdToLegacy.py`
  drew three modes of legacy sprites from that definition with the body's own clips.
- **First real run** (2026-11-19): the AI boar from the toolkit's animate stage
  (`Tools/Output/D2RBoar/boar2_anim.glb`: UniRig skeleton of 34 joints, eight fitted clips) built
  with `{"name": "wb_druid_boar", "mesh": "boar2_anim.glb", "template":
  "hd/character/enemy/sandleaper1/torso", "scale": 5.5, "normal": "from_albedo"}`: five model
  files, textures, skeleton and `combined.animations` with all eight clips; `GrannyPreview.clip_sheet`
  on the written files shows the clips moving the mesh. Two fixes came out of it: vertices are
  welded on import (`"weld"`, default on: Blender's export had split every triangle's corners,
  76,298 vertices for 25,434 triangles, over the 65,535 a mesh holds; 28,500 after), and the
  meshlib LOD step now maps the vertices meshlib splits at non-manifold points back to ours.
  The mesh inside the files keeps the template's mesh name. **Not seen in the game.**
- **No UVs** (2026-11-19): a file without UVs is unwrapped (`MeshUnwrap.py`): faces that look
  the same way and are connected form a chart, each chart is flattened by pmp-library's least
  squares conformal map, scaled to its surface area and packed in rows; vertex colours are
  baked into the colour texture. On the pig stripped of its UVs: 321 charts, no flipped and no
  overlapping triangles, 0.2 s. It is an automatic layout with many small charts and seams
  wherever the facing changes; a hand unwrap is better where there is one.
- Versions used are listed at the end of `MeshImport.py`'s header.
- Limits: one mesh and one material per body; without a rig in the file, a part far from
  anything the donor has (wings on a pig) gets guessed weights; a new bone needs clips that pose
  it before it does more than follow its parent.

### HD monster to legacy sprites (the look with HD graphics off)

In legacy graphics the game draws a monster from the sprite files of its `monstats.txt` `Code`
(a two-letter token): per animation mode a DCC file (every frame from every direction, palette
indices) and a COF file (frames, directions, speed, event frames). A new HD monster has none of
its own and shows as its donor's token (the Wild Boar form as a Werebear). `HdToLegacy.py` makes
them from the HD files (2026-11-19):

```
python HdToLegacy.py build spec.json --game <D2R> --mod <mod folder> [--out <folder>] [--modes nu,wl]
                                     [--sheets <folder>] [--frames-only]
```

```json
{ "token": "wb", "like": "tg",
  "definition": "hd/character/enemy/wb_wild_boar.json",
  "albedo": { "torso": "hd/character/enemy/wb_wild_boar/boaralb.texture" },
  "clips": { "nu": "neutral", "wl": "walk", "rn": "run", "a1": "attack", "gh": "gethit" },
  "lod": 2 }
```

- It reads the definition (mod folder first, then the game): its models at the chosen LOD, the
  props attached to its bones, its scale, and the clips of its state machine. `"clips"` names the
  clip per mode when the state machine on disk is not the one the mod installs.
- `"like"` copies a stock token's set of modes with their frame counts, directions (8 or 16),
  speed and event frames, so the new token is timed exactly like the old one; `"modes"` adds or
  changes one (`{"dt": {"clip": "death", "frames": 16, "directions": 8, "speed": 256}}`).
- Every frame is posed (`GrannyAnim`), drawn with the albedo texture and a fixed screen light by
  a small z-buffer rasteriser (4 x supersampled), fitted to the act palette and encoded.
- The camera was found by fitting stock HD bodies to their own sprites: 30 degrees down,
  8 * sqrt(2) = 11.3 pixels per model unit (a model unit is a foot; a subtile is two), mirrored
  left to right. Directions are stored in the game's order (`LegacySprite.VIEW_ORDER`).
- Output: `global/monsters/<token>/tr/<token>trlit<mode>hth.dcc`, `.../cof/<token><mode>hth.cof`,
  an unshifted `palshift.dat`, a picture per mode (`--sheets`) and `legacy_<token>.report.json`,
  whose `"animdata"` rows go to `AssetMerge.py animdata` (the game only enters a mode its token
  has timing for). The mod then sets the monster's `Code` to the token and copies `global`.
- DC6 (interface pictures: skill icons, portraits): `LegacySprite.Dc6(data)` reads, `encode_dc6(directions)`
  writes (frames read from a file are written back byte for byte); `python LegacySprite.py dc6test --game <D2R>`
  round-trips the game's `global/ui` DC6 files (2026-11-20: 520 files, 501 also recoded byte for byte).
- `LegacySprite.py` got the writers: `encode(directions, origin, palette)` (DCC),
  `encode_cof(...)`, `dc6_size`, `limit_cell_colours`. A DCC cell (4 x 4 pixels) holds at most
  four colours, transparent included; the encoder reduces a cell that has more to its four most
  used. Every frame of a direction is stored on one box and an unchanged cell costs one bit.
- Checked 2026-11-19, offline only: four stock files (Spike Fiend, Fallen, Skeleton) decoded,
  encoded and decoded again differ in under 0.2 % of pixels (the cell limit on a shifted grid)
  and a second pass is byte-identical; the per-frame and file size numbers in the headers are
  the frame's size in the older DC6 coding, and the formula reproduces Blizzard's value for all
  336 frames tried. A test build from the pig-based Wild Boar gave 11 modes (16, 8 and 1
  directions, 1,208 frames, 2.1 MB) in 4.5 minutes, all decoding back. **Not seen in the game:**
  whether the game accepts these files, and whether the size and facing match the HD body in
  play, is untested. Unknown too: the second layer of a morph mode (the Werebear's `S1` has an
  `S1` effect layer; only `TR` is written).

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

The frame halves and the arrow are cut from one stock page: `--ref-page 3 --top 1,3 --bottom 6,2
--arrow 1,3` by default (the Druid picture); the Warlock picture needs `--ref-page 1 --top 1,3
--bottom 6,3 --arrow 1,3`. A page that is its parent tab plus a cell or two can keep the stock grid
(`"keep": true`): frames are added only in listed cells that have none, only the listed arrows are
drawn, and the stock's bent arrows stay. `"redraw": [[from, to], ...]` erases those stock arrows and
draws them straight again (needs scipy), e.g. when a new arrow leaves the same cell. Example:
Warlock Archetypes' Vanguard page (Eldritch plus Possess; its README has the command). The
harness counts a page whose `Tab<N>` shows a picture a mod ships as framed in every cell.

Not done yet:

1. **Welding and own rigs.** Geometry can be removed (`"remove"`, with `"cap"`), added from
   other models (`"add"`) and brought in whole from outside (`MeshImport.py`), but an added part
   is not joined to the skin, and a part with its own textures (`alone`) is not yet listed in
   the definition by the pipeline. New bones from an imported rig are written but unproven in
   the game, and no tool authors clips for them yet beyond `GrannyAnim`'s clip specs.
   Layout of written files (corrected 2026-11-19): stock files keep all data in section 0 and
   the types in section 6, exactly as `Granny.py`'s writer does. What differed was only the
   section table: sections 1 and 3 (always empty) declare 32-byte alignment, and every variant
   whose elements hold numbers that are not 32 bits wide (vertex arrays, animation curves) has
   a marshalling record. The writer now writes both; rewritten stock models, a skeleton and an
   animation file have the same alignments and the same kinds of records as the originals. What
   still differs: stock files store equal objects twice where the writer shares one copy.
   **Two model entries per file** (found the same day): a `_lodN.model` file holds its own LOD
   level and, for N = 0, 1, 2, a second model entry for level N + 1 with a mesh and skeleton of
   its own that the root mesh list does not show. Until this was found, `reshape`, `remove`,
   `add` and the importer edited only the first entry, so the next level kept the donor's
   stock mesh. All of them now edit every entry (`GrannyMesh.all_meshes`, `bone_lists`,
   `Model.next_level`); the importer gives the next level a simpler copy by the stock ratio.
   Mods built before 2026-11-19 with `reshape` have the stock mesh in that second entry and
   should be rebuilt.
2. **Normals** are left as they were after a reshape; large edits will shade
   slightly wrong until they are recomputed.

(Animation curves, once on this list, are handled by `GrannyAnim.py`.)

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

## Licensed sounds in a mod (SealedAudio plugin)

The licensed libraries in `D:\assets\audio` allow their clips only embedded in a production, never as loose files
anyone can copy out. Sealing is how a mod complies: no loose audio ships, the game still plays every sound on every
player's machine, and nobody can edit the sealed archive. The SealedAudio D2RLoader plugin
(`Tools/SealedAudio/hosts/d2rloader`) serves sealed archives (`*.mtsa`) to the game as if their files sat loose in the mod's `data` folder, so `sounds.txt` rows and paths stay exactly as for loose `.flac` files.

1. Make the mod as usual with the sounds loose (`<Mod>.mpq\data\hd\global\sfx\<mod>\hit_hd.flac`, legacy copies under
   `global\sfx\...`, rows in `global\excel\sounds.txt`) and check it in game.
2. Seal the sounds, with the paths relative to `data` and the loose copies removed from what you ship:
   `Tools\SealedAudio\hosts\d2rloader\Seal-LocalAudio.ps1 -Data "<mod>\<Mod>.mpq\data" -Archive "<mod>\d2rloader\SealedAudio\<mod>.mtsa" -Remove -Pin`
   It seals `hd\global\sfx` and `global\sfx` (`-Include` for others) as MTSA2: the audio is encrypted with the plugin's
   key, so the game decrypts it in memory on any machine, and the archive is signed with
   `%LOCALAPPDATA%\SealedAudio\keys\<mod>.signkey`, made on first use and never shipped (`-KeyName` picks another name;
   reuse it to sign new versions). The plugin refuses an archive changed by even one byte; `-Pin` rebuilds the plugin so
   it also refuses an archive re-signed by anyone else. Instead of loose files in the mod, `-Map sounds.json`
   (`{"/hd/global/sfx/<mod>/hit_hd.flac": "D:/assets/audio/..."}`) seals straight from the library, so licensed files
   are never copied into the mod; library files are never deleted. The script then fails if any loose audio
   (`.wav .ogg .flac .mp3`) or any key file is left in the mod. Back the signing key up privately.
   `audio_seal.py verify <archive>` checks an archive and names its signer.
3. Build the plugin and copy it into the mod: `Tools\SealedAudio\hosts\d2rloader\build.bat "<mod>\d2rloader\plugins"`
   (or `<game>\d2rloader\plugins` for every mod). Archives go in the same scope's `d2rloader\SealedAudio\`
   (or `d2rloader\plugins\SealedAudio\`, which the plugin checks next).
   With D2RMM (Custom), which rebuilds its output mod on every install, pack both instead and import the zip in its
   D2RLoader plugin manager:
   `Tools\SealedAudio\hosts\d2rloader\New-D2rmmPackage.ps1 -Archives "<mod>\d2rloader\SealedAudio" -Out "<somewhere>\sealedaudio-<mod>.zip"`
   (or `-Package <zip>` on step 2's script, which also checks the zip for keys and loose audio). The zip holds
   `d2rloader\plugins\sealedaudio.dll` and `d2rloader\plugins\SealedAudio\*.mtsa`, which D2RMM deploys into the output
   mod unchanged, and never a key file. Players need nothing else.
4. Start through D2RLoader. `d2rloader\logs\SealedAudio.log` says how many sounds were mounted and how many functions were
   hooked; `Get-D2RLoaderLog.ps1 -Plugins` shows the plugin's summary lines. If a sound stays silent, set
   `log_probes = true` in `<scope>\d2rloader\config\sealedaudio.toml`: every open under `hd\global\sfx` (and the other
   `probe_prefixes`) is logged as served, loose or not found. A loose file at the same path always wins.

**Seen in game (2026-11-18), fixed in 1.4.1:** with SealedAudio 1.4.0 every sound effect went silent (music kept
playing) from the first sealed sound on. D2R reads files through an I/O completion port (its `aio` library:
`CreateIoCompletionPort`, overlapped `ReadFile`, `GetQueuedCompletionStatusEx`); the stand-in handle of a sealed file
could not be attached to the port and its reads posted no completion packet, so the loader waited for that read forever
and every later sound queued behind it (`d2rloader.log`: `BC_ASSERT: existingPort == instance->iocp`, aio.win32.cpp).
1.4.1 emulates the port for sealed files (association, one packet per read, `CancelIoEx`); `iocp_test.bat` /
`iocp_test.cpp` in `Tools/SealedAudio/hosts/d2rloader` reproduce the failure on 1.4.0 and pass on 1.4.1 (an ordinary
file through the same port is checked too). Not yet re-tested in a running game.

**Signer pin:** the plugin is built pinned to the `aamt` signing key (`src/SealedSigner.h`); an archive signed by any
other key is refused at load (`SealedAudio.log`: "signed by someone other than the signer this plugin was built for").
Seal with `-KeyName aamt`. Every package must carry the identical `sealedaudio.dll` (D2RMM refuses differing copies),
so after a plugin rebuild re-pack every `sealedaudio-*.zip`.

The packed game imports no file functions, so the plugin uses the core's `patch_system` (kernel32's file stubs are
redirected process-wide) plus the import table of D2RLoader's `D2RCore.dll`. Tested so far by loading the built plugin
through a mock loader with the SDK's own structures (sealed `.flac` served to a caller that resolved `CreateFileW`
through kernel32, config written, clean exit), with archives made by the step 2 command (both `hd\global\sfx` and
`global\sfx`) in either archive folder, and the step 3 zip through D2RMM's own package importer (all files mapped to
`d2rloader\plugins\...`, no warnings); not yet in a running game. MTSA2 (step 2) was tested through the mock loader with
files from `D:\assets\audio\made`, on a "player" profile with no keys at all: served byte-identical to the library
files; refused after one byte of audio or of the index was changed; an archive unpacked and re-signed with another key
was accepted by the unpinned plugin and refused by the pinned one; no RIFF/WAVE bytes appear in the archive; the
library was untouched by `-Remove`; the script's zip held only the dll and the archive, and a stray `.wav` in the mod
stopped it.

## Files

- `ModOrder\ModOrder.js`, `ModOrder\masterlist.json`, `Sort-D2RMods.ps1` - sort and check a D2RMM mod list like LOOT (see "Mod list sorter")
- `ConvertReplaceMod.py`, `Convert-D2RReplaceMod.ps1` - make a mod that replaces whole tables / string files merge them row by row
- `Granny.py`, `HdSkeleton.py` - Granny files as editable trees; skeleton decode / encode
- `LegacyToHd.py`, `Convert-D2RLegacyMonster.ps1` - HD version of a sprite monster from the closest HD one
- `d2r_casc.py` - read-only archive access (`D2RArchive.read`, `.exists`, `.list`)
- `GrannyFile.py`, `GrannyPreview.py`, `GrannyMesh.py` - read, preview, rewrite and reshape HD models
- `ModelLodDesc.py`, `Update-D2RModelIndex.ps1` - read, extend, check and rebuild the game's model index, needed for any model at a new path
- `AssetMerge.py` - fragment rows for the AssetMerge plugin (new models for `hd/model_lod_desc.bin`, timing for `global/animdata.d2`) written into a mod's mod.js
- `GrannyAnim.py` - read, pose, author and write animation clips
- `LegacySprite.py`, `SpriteFit.py`, `SpriteMeshAI.py` - legacy sprites to images, fit an HD template to them, AI mesh reference
- `GrannyPart.py` - cut a part (a quill) out of a body mesh into its own model
- `MeshImport.py` - a mesh made outside the game (OBJ / glTF) as a skinned body on a donor's skeleton, with its own textures, rig and new bones
- `Gltf.py` - small glTF reader / writer that keeps the rig and animations (used by `MeshImport.py`)
- `GrannyCrossCheck.py <files>` - reads a Granny file the way the community Noesis GR2 reader lays it out (sections end to end, relocations as 4-byte offsets, 44-byte type members) and compares that view with `Granny.py`'s: a second opinion on files the toolkit writes
- `ToolJobs.py` (+ `Drop\Queue Noesis check.bat`, `Drop\Run tool jobs.bat`) - a job queue for the downloaded community tools in `third_party` (Noesis export, AnimData editor): jobs are queued by script or assistant, a person runs them, results come back as files; `compare` checks what Noesis read against `Granny.py`
- `MeshUnwrap.py` - UVs for a mesh without them (charts + pmp-library's conformal map), vertex colours baked to a texture
- `HdToLegacy.py` - legacy sprites (DCC + COF) drawn from an HD monster's models and clips; `LegacySprite.py` encodes them
- `SkillTreeArt.py` - skill tree page pictures with frames and arrows for a custom page
- `ScaledMonster.py` - the pipeline
- `ModAssets.py`, `ModHarness.js` - the mod test pipeline (below)
- `ConvertDataMod.py`, `ConvertDataModCheck.js`, `MpqArchive.py`, `Convert-D2RDataMod.ps1` - data mod (or packed .mpq) to D2RMM mod (below)
- `Update-D2RConvertedMod.ps1`, `MergeCompiledMod.py` - update converted mods from a new download (Rebirth, Reimagined; below)
- `Update-D2RNativeMod.ps1`, `NativeModUpdate.py` - install and update mods that already are D2RMM mods (Relics of Sanctuary; below)
- `TreePlacement.js`, `TreePlacement.py` - shared tree-cell placement for the skill-page mods, also on reworked class trees (below)
- `StockRows.js`, `StockRows.py` - the plain game's template rows embedded in the skill-page mods, so total conversions do not leak into their new rows (below)
- `LeakCheck.js` - finds what a total conversion changes in the rows other mods add (below)
- `PluginSdk.py`, `PluginAddresses.py`, `Update-D2RPlugins.ps1` - keep the D2RLoader plugin sources in step with D2RLoader: SDK and hooked addresses (below)
- `HdMatch.py` - HD art for mod monsters and items that only have legacy sprites (below)
- `Ds1Presets.py` - list or move the monster spots of a `.ds1` map (below)
- `Presets/` - one JSON per job

## Monster spots in a map (`Ds1Presets.py`)

A `.ds1` map places a monster by number: the how-many-th row of the map's own act in
`global\excel\monpreset.txt`. A map editor numbers the monsters it adds from the plain game's row
count (Act 3: 39, Act 4: 28). A mod that adds rows to the same act uses the same numbers
(Reimagined: Act 3 ids 39-42, Act 4 ids 28-33), and a D2RMM mod cannot rewrite a map at install
time. So a map's added monsters are moved to high, fixed ids once, and the mod's `mod.js` fills
the act up to them with `place_nothing` rows (The Abyss 4.2.1: `extraMonsters.firstId` 64).

```
# what the maps use: act, objects, spots per monster id
python Ds1Presets.py abyss2.ds1 abyss3.ds1
# an Act 3 map from the editor: ids 39-63 go up by 25 (39 -> 64), in place
python Ds1Presets.py abyss2.ds1 --move 39:64
# an Act 4 map: 28 -> 64
python Ds1Presets.py abyss3.ds1 --move 28:64
```

- `--move FROM:TO` only touches ids FROM to TO - 1, so a second run changes nothing. The file
  keeps its size (only the id bytes change). Keep a backup outside the mod's `tiles` folder, which
  D2RMM copies whole.
- Run it again after every export of the map from the editor: the export has the editor's ids.
- First use (2026-11-17): The Abyss failed to install below Reimagined ("Act 3 has 43 rows, the
  map expects 39"). Checked with `ModHarness.js` (Reimagined, then The Abyss); not yet seen in
  the game.
- Converted data mods (`ConvertDataMod.py` / `ConvertReplaceMod.py` mod.js, both row modes) keep
  `monpreset.txt` one block per act and put each new row at the number the mod's own file gives it
  (`actBlocks`), so the converted mod's own maps keep their monsters: Reimagined's endgame map
  bosses (Act 5 ids 58-117 `rmap_*_warden`, 118 Azmodan), Belial/Cydaea (Act 3 40/42), the forge
  and Izual bosses (Act 4 28-33), the Act 1/2 additions (Pitzilla, the Smith, Maghda...). Before, 'keep' appended new rows
  at the end of the table, after Act 5, and the game ("first row of the act + number", as in
  D2MOO) read the wrong rows. Mods above that already use those numbers get a warning; put the
  converted mod above them. Checked 2026-11-17 with `ModHarness.js`: all 678 monster spots of
  Reimagined's maps resolve to its rows, alone and with The Abyss below.

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
- string files (`local\lng\strings\*.json`) are merged by Key. The mod's new entries get the next
  free ids from `D2RMM.getNextStringID()` at install time, not the ids the data mod picked (since
  2026-11-19): those were free only in the game files the mod was made for, and collided with the
  game's newer strings, with the other conversion and with every mod that numbers from the counter.
  Changed entries keep their id. `local\lng\next_string_id.txt` (that counter) and
  `global\dataversionbuild.txt` (D2RMM writes the game's own at the start of an install) are never
  copied from a data mod: Rebirth's counter said 65535, so every later mod's strings got ids past
  65535, which the game's 16-bit string references wrap onto ids 0+ (the stock NPC dialog of
  `vo.json`): "dialog text swapped around". `ConvertDataMod.py --refresh-js <mod folder>...` puts
  the current mod.js code around an existing conversion's generated data (old one in
  `d2rmm\mod.js.before-refresh`), for code fixes without converting again.
- every change belongs to a feature (inventory, cube recipes, runewords, uniques and sets, affixes,
  item bases, drops, monsters, areas, skills, characters, vendors, interface, visuals; tables and
  text everything depends on are "core") and every D2RLoader plugin (DLL with its .mpq/.ini and its
  `config\<name>.toml`) and patch is a unit: each gets an on/off switch in the converted mod's D2RMM
  settings. `-Plugins packages` (Python `--plugins packages`) writes plugins and patches as their own
  D2RLoader packages instead: zips in D2RMM's `d2rloader\` folder, which D2RMM imports on start or
  Plugins > Refresh (hand-made package folders or edited manifests make D2RMM refuse to start).
  A plugin that one of D2RMM's own packages already installs with different bytes starts switched
  off (D2RMM refuses two different files at one place).
- Switching a feature off must not leave rows naming rows that are gone. The converter reads its
  own patches (`feature_links`): a cell counts as a reference only in a column that names another
  table (`LINK_REFS`: cube inputs/outputs and TC items on item codes and unique names, monster
  `Skill1-8` / `TreasureClass*` / level `mon1-25` / hireling and character skills, item property
  parameters that take a skill, `runes`/affix `itype`...), and only against rows the mod adds
  (names the game's table already has don't count). From that, each feature's setting text lists
  what it **uses** (with the number of references and an example), what **uses it**, and whether it
  is **always on**. `mod.js` (`NEEDS`, `FORCED`) then switches a feature off together with every
  feature that uses its new rows (the install log says which and why), and ignores the switch of
  a feature that always-installed tables use (`missiles.txt` `Skill` -> new skills) and of
  whatever that feature needs in turn (a warning says so). The links are in `convert.json`
  (`featureLinks`, `featuresForcedOn`). Limit: a link of a few cells still takes the whole feature
  along; blanking just those cells is not done. Test: `node ConvertDataModCheck.js <mod> <cache>
  <out> '{"itembases":false}'` and read the log.
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
# from where the mod is: copied into <D2RMM>\mods\Reimagined, converted, checked, and the source
# remembered (convert.json), so Update-D2RConvertedMod.ps1 -Mod Reimagined redoes it after the mod updates
.\Convert-D2RDataMod.ps1 -Source '<game>\Reimagined.mpq' -Mod Reimagined -Author ScottieKnowz

# a mod already in D2RMM's mods folder
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
values, the mod's new rows appended in its order (`monpreset.txt`: at their number within their
act, see "Monster spots in a map"), and moved row numbers pointing at the same rows as
in the mod's own files. `d2rmm\convert.json` keeps the settings the mod was converted with
(`settings`: name, author, version, rows, plugins, source), which an update reuses; a rerun keeps
the name and version in `mod.json` unless `-Name` / `-Version` are given.

Notes:
- Mods built on the stock skill trees (the skill-page mods) go below a conversion and fit
  themselves to its trees; run `Test-D2RMod.ps1 -KeepGoing` on the whole list (a mod that throws is rolled back and the
  rest still run, as in D2RMM).
- Conversions that add levels can be stacked in `keep` mode: the lower one's new levels (every Id
  above the game's own top level, 137) move behind the levels the mods above it added, at install
  time, and so do the numbers that point at them in its own tables: `levels.txt` Id/Depend/Vis,
  `lvlmaze.txt` Level, `lvlprest.txt` LevelId, `lvlwarp.txt`, and cube recipes that open a portal
  (`Red Portal,lvl=139` in `output`, `output b`, `output c`). Example: Reimagined, then Rebirth
  (rows keep) puts Rebirth's levels 138-141 on 288-291. Numbers built into a mod's D2RLoader DLLs
  cannot move, so the mod with plugins that know its levels (Reimagined: its maps) goes above. A
  `rebuild` conversion keeps its own numbers and must be first. VanillaDeluxe is not supported.
- Mods that look up plain-game rows by name (Necromancer_V1.6: Confuse, Poison Dagger) go ABOVE a
  conversion that renames or replaces those rows (Reimagined replaces 19 stock skills in place);
  below it they stop. The conversion's "My mod list" rules keep their other changes.
- HD registries are merged key by key, not copied whole: `hd/missiles/missiles.json`,
  `hd/character/monsters.json`, `hd/items/items.json`, `uniques.json`, `sets.json` and
  `hd/overlays/overlays.json` (one object of key -> value, or a list of single-key objects). The
  mod's changed and new keys go in, keys the mods above added stay, and "Load order > Conflicts"
  decides a key both changed. Other JSON (layouts, models, presets) is still copied whole.
  `convert.json` lists them under `jsonMerged`; `-Check` compares them like the tables.
- Two conversions stacked: put the one with the most new content above and set the lower one's
  "Load order > Conflicts" to `earlier`, so it only fills what the upper one left alone. With
  Reimagined above Rebirth on `mod`, Rebirth's stock-based values replaced about 3,600 of
  Reimagined's (treasure classes, mercenaries, skill values and descriptions, its new arrows'
  visuals); ModOrder warns about that setting.
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
  features whose file count changed. If the conversion fails, the old files are put back; when it
  passes its check, `previous` is removed.
- A source can also be a `<Name>.mpq` folder itself (e.g. `<game>\Reimagined.mpq`): it is copied
  whole, with its `modinfo.json`. Without the page: `ModConverter.py --convert <source> [--id <mod>]`
  (or `Convert-D2RDataMod.ps1 -Source`).
- **Converted mods**: what is in D2RMM's mods folder, how it was converted and from where.
- A mod the converter cannot redo itself (one made from compiled `.bin` tables, such as Rebirth Skill
  Versions) can name its own updater in `<mod>\dev\update.json` (`{"script": "update_x.py", ...}`):
  Update then runs `python <script> <download> --game <D2R folder>` and shows its log.
- Tables that are not UTF-8 or have duplicate column names, and string files whose repeated Keys
  cannot be rebuilt, are copied whole; `d2rmm\convert.json` lists them.
- Update also packages the download's **other** `d2rloader` folder (a D2RLoader setup has one
  beside `mods\`, e.g. Frankenstein's): each plugin
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
    `cubemain` has a recipe description with trailing spaces that a mod's copy can lack; matched
    exactly, the game's recipe stayed (ilvl 75) and the mod's came in as a new row.
  - *Rows that share a name* - `--duplicates content` (default) / `order`. The game's 8 `Rainbow Facet`
    rows are matched to the mod's rows by what is in them (most alike first, ties by order), and
    left-over ones to the mod's new rows whose name starts with theirs (`Rainbow Facet Cold`, 3/4 of
    the cells alike). By order, a mod's facets can come out as 10 that drop instead of 4.
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
- **My mod list** and **Options** (sections in the converted mod's D2RMM settings) come from a rules
  file: `--modlist-rules <json>` (default `<D2RMM>\mods\modlist-rules.json` when it exists, `none` =
  no section; format and notes in `modlist-rules.example.json`). Each rule becomes a checkbox;
  `mods` names the converted mods it is for (none = all), and only the parts that touch something
  the mod has are kept (`convert.json` `modListRules`). Rerun Update after editing the file.
  - A *My mod list* rule is off by default and acts only when ticked **and** a mod in `when` is
    enabled in D2RMM (`"above": true`: only when it comes before the converted mod). Actions:
    `earlier` (table/string paths where mods above keep their values, as *Conflicts: earlier* for
    those paths only), `skip` (regex on the mod's file/table paths, e.g. a whole
    `hd\global\ui\panel\inventory` folder copy), `switches` (switch ids turned off, e.g. a plugin the
    partner mod replaces). The install log says per ticked rule whether it was used and why not.
  - An *Options* rule (`"option": true`) is a part of the mod itself: on by default, no `when`, and
    its actions apply when it is switched **off**. `props` takes item property codes off every item
    (uniques, sets, runewords: later properties move up; set bonus slots keep their place; an affix
    or automagic row left with nothing stops spawning).
  - Harness test of ticked rules: config `'{"listClassless":true}'`, `CHECK_MODLIST` with the partner
    mod above, and an `<earlier folder>` holding the partner's changed table.
- A download that is a folder holding the mod as a packed `.mpq` (Frankenstein's
  `FMMP-Experimental-R67\FMMP-Experimental-R67.mpq`) is staged by Update into `converter-work` (the
  `.mpq` unpacked, with the `d2rloader` folder beside it); the download stays as it is.
- A plugin an installed D2RMM package already ships with exactly the same files is left out of
  mod.js (`convert.json` `loaderProvidedByPackage`), e.g. Frankenstein's plugins, which its own
  package `d2rloader\FMMP-Experimental-R67` ships patched to run under `-mod D2RMM`.

  `Update-D2RConvertedMod.ps1 -MatchTrim $false -Duplicates order -Deleted leave` overrides them.

Without the page (same code), for one or more mods; no `-Source` = the download in `convert.json`,
which also redoes a conversion after a game patch:

```powershell
.\Update-D2RConvertedMod.ps1 -Mod Reimagined, Rebirth
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
numbers. Layouts are cached in `%LOCALAPPDATA%\D2RModAssets\binlayouts` (delete after a patch).

## Mods that already are D2RMM mods (install and update)

`Update-D2RNativeMod.ps1` → `NativeModUpdate.py` (+ `ModHarness.js`)

A download with its own `mod.json` + `mod.js` (Relics of Sanctuary, by Cpp) patches rows at install
time and has its own settings; running it through the data-mod converter would throw that away.
This tool installs it as it is, with the same safety as the converter's Update:

```powershell
# first time: a folder, .zip, .7z or .rar (7-Zip for the last two) -> <D2RMM>\mods\<Id>
.\Update-D2RNativeMod.ps1 -Install '<game>\RelicsOfSanctuary 745 3.5.0 2026-11-09T22-15Z xzHHu6uYW' -Id RelicsOfSanctuary

# after the mod updates: the newest download with the same Nexus name
.\Update-D2RNativeMod.ps1 -Mod RelicsOfSanctuary
.\Update-D2RNativeMod.ps1 -Mod RelicsOfSanctuary -Source '<download>'   # this one instead
.\Update-D2RNativeMod.ps1 -Mod RelicsOfSanctuary -DryRun                # stage, patch, test; mods\ untouched
```

- The download is unpacked and staged in `<D2RMM>\converter-work\<id>.new`, patched, and run alone
  through `ModHarness.js`. Only a run where the script does not throw replaces `mods\<id>`; the old
  folder waits in `converter-work\<id>.previous` and comes back if putting the new one in fails.
  Harness problems the mod has on its own are counted, not fatal (see them with `Test-D2RMod.ps1`).
- Settings stay: D2RMM keys them by the folder name (kept) and stores them in `<mod>\config.json`,
  which is carried over.
- `<mod>\d2rmm\native.json` remembers the download, version, Nexus name and id, the folders to look
  in and the patches applied. Without `-Source`, `-Mod` takes the download whose name starts with the
  same Nexus name (`<Name> <nexus id> <version> <date> <x>`) and has the highest version (then the
  newest), from the folder the last one came from, the game folder, the D2RMM folder and Downloads.
- Patches, redone on every install so they survive updates:
  - *pause-menu*: a mod that copies its own `global\ui\layouts\pauselayoutgardenhd.json` with
    `D2RMM.copyFile(..., true)` replaces the pause menu every mod above it built (Frankenstein,
    Item Dictionary, Loot Guide Companion). The copy is moved to
    `d2rmm\original-pauselayoutgardenhd.json` and the mod's own button tables are merged into the
    installed menu from mod.js instead, right of the main buttons and below buttons other mods put
    there. The mod's own switch for them still works. The test run fails the install if the merged
    menu lost the game's `PauseTable` / `PauseTableExtra`.
  - *affix-guard*: Relics of Sanctuary's `applyAffixRework` changes magic affixes matched by row
    position + name. Below a total conversion that keeps the names but rescales the values
    (Reimagined: Lucky, Jagged) a change that sets only a max left the min above it, and Charming
    Vendors stopped the install ("Unsupported stat range in magicprefix.txt"). The guard skips such
    a change; on the plain game's tables nothing changes. If a new version no longer has the one
    `Object.assign(target, entry.changes);` the guard goes around, the update stops and the
    installed version stays, so the patch is never dropped silently.
- Opt-in patches, asked for once with `-Patch <name>` on `-Install`, kept in `native.json` and
  redone on every update:
  - *layout-guard*: for a mod that expects every UI layout widget to have `fields` and a `rect`.
    Total conversions (Reimagined with its Inventory feature on) ship layouts whose widgets are bare
    `{type, name}` (fields inherited from the base layout), and the mod stops ("Cannot set
    properties of undefined (setting 'filename')"). The mod's whole script runs in a block where
    `D2RMM.readJson` on `global\ui\layouts` files gives bare widgets fields (saved once something
    is written into them) and a missing rect a stand-in that takes writes but is never saved, so
    the inherited rect stays; assigning a new rect saves it. It does not depend on the mod's code.
- A mod with no download kept installs from its own folder:
  `-Install '<D2RMM>\mods\<id>' -Id <id> [-Patch ...]`. Its next update needs `-Source`.
- Inventory 10x8 1.1.0 (Bandit, Nexus 1327; no download on disk) was installed that way with
  `-Patch layout-guard` (2026-11-20). Update it with
  `.\Update-D2RNativeMod.ps1 -Mod Inventory10x8 -Source <download>`. Harness, Reimagined with
  `--config inventory=true`: the plain script stops as above; the guarded plain script and the old
  hand edit (still in its mod.js, now redundant) write byte-identical files; on the plain game the
  guard changes nothing.
- Relics of Sanctuary 3.5.0 (2026-11-15): installed and updated with this; its test run flags the
  copied Druid skills "Mythic Armageddon / Hurricane" sharing a tree cell with the originals (the
  author's design). It goes above BestOf in the D2RMM list. Reinstalled 2026-11-19 with the
  affix-guard, which replaces the hand edit of 2026-11-15; checked with Reimagined + Relics +
  Charming Vendors in the harness (patched: no mod stops; the plain download: Charming Vendors
  stops on Lucky). Not yet seen in the game.

## Drag and drop (`Drop\`)

Every tool that works on a file or folder has a batch file in `Drop\`: drag the files or folders
onto it in Explorer (several at once where the tool takes several). The window stays open at the
end; a batch file opened without anything dropped on it says what to drop. Game, D2RMM and Python
are found the same way as for the other launchers (`D2RToolPaths.ps1`); the routing is in
`Drop\_drop.ps1`.

| Batch file | Drop | Runs |
|---|---|---|
| `Test mods.bat` | D2RMM mod folders | `Test-D2RMod.ps1 -KeepGoing`, all of them together, in the order dropped |
| `Make mods merge.bat` | mod folders that copy whole tables | `Convert-D2RReplaceMod.ps1` |
| `Convert data mod.bat` | a data mod (.mpq folder, packed .mpq, .zip, .7z, .rar) | `Convert-D2RDataMod.ps1`: `-Mod` when it is already in D2RMM's mods folder, else `-Source` (asks for the folder name) |
| `Update converted mod.bat` | converted mod folders | `Update-D2RConvertedMod.ps1` |
| `Install D2RMM mod.bat` | a download that is a D2RMM mod (.zip, .7z, .rar, folder) | `Update-D2RNativeMod.ps1 -Install` |
| `Update model index.bat` | mod folders with HD models | `Update-D2RModelIndex.ps1` |
| `Extract MPQ.bat` | .mpq archives | `MpqArchive.py extract` into `<name>-extracted` beside it |
| `Check mod list.bat` | a saved mod list (.json, e.g. `<D2RMM>\modorder-backups\`) | ModOrder on that list; changes nothing |
| `Restore mod list.bat` | a saved mod list | puts it back into D2RMM (asks first) |
| `Run bot test.bat` | a bot script (.txt) | `Invoke-D2RBotTest.ps1 -Script` |
| `Rebuild HD Art Match.bat` | a merged mod data folder | `HdMatch.py build --data`, into `<D2RMM>\mods\HdArtMatch` |

A merged data folder for HD Art Match without installing: `node ModHarness.js --game <D2R>
--keep-going --out <folder> --out-copied "^(global/(monsters|items)/|hd/(items|character)/)" <mods
in list order, without HdArtMatch>` (`--out-copied` also saves the copied files the pattern names).

How long a mod takes in D2RMM: `node ModHarness.js --game <D2R> --quickjs <D2RMM source>\node_modules
<mods>` runs each mod in QuickJS, the script engine D2RMM uses, rather than Node's much faster V8.
For each mod it prints the time split into the script itself, D2RMM calls, and values copied into
QuickJS. The harness's own `writeTsv` is slower than D2RMM's, so read that part loosely. A D2RMM
install uses one core: mods run one after another, each on the files the mods above it left. More
threads would not help much; a slow mod's script is what to fix. That is how the converted mods'
`remap` came down from 135 s to 3 s of Reimagined's install.

## Mods that replace whole files (`ConvertReplaceMod.py`)

Some D2RMM mods copy their whole copy of a game table or string file over the output
(`copyFile('data', 'data')`, or a preset's `ui.json`): every change the mods above made to that
file is lost. Below Reimagined, Better and New Unique Items wiped about 48,000 of its unique item
values that way. The converter makes such a mod merge instead:

```
Convert-D2RReplaceMod.ps1 -Mod 'Better and New Unique Items', 'Better Body Armors__Shields__Weapons'
Convert-D2RReplaceMod.ps1 -Mod 'Better and New Unique Items' -Undo      # its own mod.js back
```

- Every table (`global\excel\**.txt`) and string file (`local\lng\strings*\*.json`) the mod ships,
  in any folder (presets included), is compared with the game's copy, and the difference is stored
  as a row patch in `<mod>\d2rmm\patches\` (the data-mod converter's format and merge code, rows
  "keep": rows stay in place, new rows go at the end).
- The mod's `mod.js` moves to `d2rmm\original-mod.js`. The new `mod.js` runs it unchanged with a
  D2RMM whose `copyFile`, when a copy includes one of those files, puts the file back as the mods
  above left it and merges the mod's patch into it. Its settings, other files and code work as
  before.
- The mod's own changes still win cell by cell; the rows, cells and strings it does not touch keep
  what the mods above wrote. The install log names the merged files and the cells both changed.
- `-Check` (on by default) runs the converted mod alone in ModHarness. Run alone, the output is
  the mod's own files (checked on Better and New Unique Items and Better Body Armors: same rows and
  strings). Rerun after the mod updates; it always wraps `d2rmm\original-mod.js`, never itself.
- ModOrder knows converted mods (`d2rmm\replace.json`): they leave the "whole-file" group, so they
  can sit below the conversions and merge into their tables; unconverted ones get a pointer here.

## Mod list sorter (`ModOrder`, like LOOT)

Sorts a D2RMM mod list and checks it, the way LOOT does for Bethesda games. Node.js 22 or later,
nothing else.

```
Sort-D2RMods.bat                     # report and the sorted order; changes nothing
Sort-D2RMods.ps1 gui                 # the same in a browser window, with an Apply button
Sort-D2RMods.ps1 apply               # put the sorted order into D2RMM (old list saved first)
Sort-D2RMods.ps1 restore <file>      # put a saved list back
Sort-D2RMods.ps1 audit [-Sorted]     # ModHarness on the list: what each mod loses to mods below it
```

What it reads:

- **Your list**, straight from D2RMM's storage (`%APPDATA%\d2rmm\Local Storage`, a LevelDB it
  copies and reads; only the mod list, the last installed list and the plugin switches, never the
  rest). D2RMM may be open or closed. `--from <saved list.json>` uses a saved list instead.
- **The masterlist**, `ModOrder\masterlist.json`: one entry per known mod with its group, load-after
  / load-before rules, required mods and D2RLoader plugins (with minimum versions), mods it breaks
  with, and messages. Rules can depend on other ticked mods or on the mod's own settings. The
  `_readme` at its top describes the format.
- **Your own rules**, `<D2RMM>\modorder-userlist.json` (same format, merged over the masterlist;
  `ModOrder\userlist.example.json` shows how).
- **The mods folder**: each mod's `mod.json`, settings, README and `mod.js`, and the plugins D2RMM
  imported into `d2rloader\` (their versions read from the DLLs).

How it sorts: groups first (`top`, `whole-file`, `early`, `default`, `late`, `patch`, `final`),
then the after/before rules between ticked mods. Everything else keeps your order: a mod a rule
needs higher is pulled up to just above the mod that needs it, so only what a rule names moves.
Each move is shown with its reason. A rule that goes against the groups, or rules that go in a
circle, are reported and left out.

What it reports: required mods or plugins missing, turned off or too old; mods that break each
other (from the masterlist, and on its own when two converted data mods put levels on the same
level numbers); mods that copy whole tables or string files over what the mods above them wrote;
the same mod ticked twice under two folder names; ticked mods whose folder is gone; mods newer than
the masterlist knows; mods it does not know (it guesses their group from their README: "put it
last", a converted mod's rows mode) and plugins their README names that are not imported; and
that the list changed since the last Install Mods.

`apply` talks to D2RMM over Chrome remote debugging (port 9333): it starts D2RMM with
`--remote-debugging-port=9333` when D2RMM is closed (with D2RMM open without it, close D2RMM first
or pass `-Restart`), saves the list it had in `<D2RMM>\modorder-backups\`, writes the new list,
reloads the window and reads the list back to check it. Then Install Mods with the game closed.

Best Of (the compatibility patch mod) takes its order rules from the masterlist:
`node ModOrder\ModOrder.js bestof-rules` writes them into its `mod.js` RULES block.

Keep the masterlist up to date when a mod is added or updated: the `checked` version, its rules,
and failures the harness finds (`audit`, or `Test-D2RMod.ps1 -KeepGoing` on a list).

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

`D2RMM.getNextStringID()` works like D2RMM's (since 2026-11-19; it was a fixed 90000): the counter
is the number in `local\lng\next_string_id.txt` when a mod first asks (the game's, or a copy a mod
put in), written back after each call. The string check covers all 21 string files: a new entry
with an id past 65535 (the game's 16-bit string references show `id & 0xFFFF` instead, from 65536
on the stock NPC dialog) or with an id another Key has after the install is a PROBLEM.

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
  (`-MaxPage`, default 126 since SkillTab4 0.7.0), `ListRow` names the parent tab, each page
  number used by one class only, `Tab<N>` and `TextTab<N>` in the layout with an existing label string.
- **Tab labels per class**: the layout is shared but SkillTab4 shows a class only its own pages,
  so for each class its labels (`TextTab<N>` rect, `Tab<N>` click area, a `TabPlate<N>` plate)
  must not overlap each other, the stock tab strip, the tree picture or the right hinge, and must
  stay on screen (panel 0-1507 high, screen edge at panel x 1394): problems. A label that reaches
  the middle of the skill counter's line, or whose text needs more lines than its box holds
  (22 pt, about 12 px a letter), is a warning. `$Variable` fields are read from `_profilehd.json`
  (Skill Tab Layout writes positions there); one it does not define is a problem. Prints one
  `tabs <class>:` line with every page's position.
  A warning when a skill sits where the parent tab has no skill (no frame in the picture),
  unless the page's `Tab<N>` shows a picture a mod ships (`SkillTreeArt.py`); a problem when
  that picture is neither shipped nor a class tree picture.
- **ID limits**: a skill row above 32767 (problem); a class skill past the item width of
  `item_singleskill` (9 bits, 511: needs the SkillLimits plugin); `states.txt` past 511 rows
  (needs D2RCore and the StateLimits plugin) or past 32768 (problem); an item, set or cube
  `state` property (in tables a mod wrote) naming a state past the width of stat 98 `state`
  (8 bits, 255: needs StateLimits 0.2.0+), or a state that does not exist (problem).
- **Missiles**: names without spaces or a trailing digit, `Skill`, sub-missiles,
  same row number in the main and the classic-rules table. A warning when a new
  skill's missile takes its damage from another skill. Lists new missiles without an HD entry.
- **Monsters and pets**: row index, AI name, skills, missiles, name string, pet type, HD body.
- **Strings**: new keys and ids not already in use.
- **HD**: every texture, particle file, model or definition an HD definition written by a
  mod names must be in a mod folder or in the archive; same for the textures named inside
  particle files copied from a mod folder. (Animations and skeletons are not checked.)
- **PetAI tables** (rules, nearrules, springrules, commandrules, tactics): format and header, the values the plugin would skip, monster/skill/state rows, `Skill<slot>` with a mode, spring skills with `summon`/`pettype`, command skills with `srvdofunc` 179; prints what each rule and tactic does.

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

1. Every texture the effect's particle files name is read. Textures that really
   hold colour, uncompressed (RGBA8) or block-compressed (BC1, BC3), are recoloured
   and written under a new file name (the first characters become the look's `tag`).
2. The particle file is copied under a new name with those paths swapped, through
   `PopcornBaked.py`; the copy must pass its `check`.
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
  their channels are numbers, not colour. Block textures get the same test on
  their blocks' end points (`White`, `Black`, `Default_AlphaMap` stay).
- **Normal, material and distortion maps are left alone**, by name (`_NRM`, `_N`,
  `NMap`, `_ORM`, `Distort`, `debug`): their channels are not grey but are not
  colour either. Every such texture the game's effects use has one of these names.
- **Block formats** (codes from `HdTexture.py`, 2026-11-16): 0x3A BC1 and 0x3D / 0x3E
  BC3 are recoloured (end points of each block, every mip); 0x3F BC4 and 0x41 BC5
  (one or two channels: masks, noise, distortion) are left alone. A preset can
  override a code: `"blockFormats": { "0x3d": "keep" }` (or `"bc1"`, `"bc3"`).
  The three presets here come out as before: the BC3 textures their effects use
  are all grey or data. Effects with BC3 colour (`_ALB` decals and models,
  `T_FX_Geo_Ice`, `_C` blood) now recolour, e.g. `glacial_spike`.
- **Colour set inside the particle file** (a constant, not a texture) is not
  changed. `poison_sparks` is such an effect; `poison_smoke_puff` recolours.
  The scripts store into numbered particle-stream slots and the field names are
  not in the file, so which constant is a colour (not a speed) is not known yet;
  see the `CLayerCompileCacheField` notes in `PopcornBaked.py`.
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
- Rechecked 2026-11-16 on the game's current 2206 files (11849 distinct scripts): all round-trip
  and pass `check`. They added opcode 76, integer division by a constant (one script, in
  `rmagan\manashielddir00_overlay`).
- Script headers: words 6-8 are the registers each bank uses. `set_program` (and
  `set_instructions`) recompute them and the instruction count from the code, so an edited
  script never gets fewer registers than it uses.
- `check` (`Baked.validate()`) catches what an edit can break: header counts, constants,
  externals or functions a script uses that are not there, references to missing objects,
  curves whose keys, values and tangents disagree, the class table. `EffectEdit.py` runs it on
  every file it writes and refuses one that fails.
- Not tested in the game: a script whose instructions were changed (only constants so far).
- Confirmed in the game (2026-11-13): an edited file with added strings, a changed length and
  textures drawn from scratch loads and shows.

```
python PopcornBaked.py props <file.particles> [--platform PC]  renderers and their properties
python PopcornBaked.py code <file.particles>        compiled scripts: the names they use and their constants
python PopcornBaked.py dis <file.particles> [n ...]  compiled scripts as readable instructions
python PopcornBaked.py dump <file.particles> [--class <name>]
python PopcornBaked.py diff <old.particles> <new.particles>   what an edit changed, by object and field
python PopcornBaked.py check <file or folder> ...   consistency checks (exit 1 on problems)
python PopcornBaked.py roundtrip <file or folder> ... [--check]
```

The layout and the known field meanings are in the module's docstring. First use:
`SorceressSecondPages\dev\build_effects.py`, which draws its own RGBA8 textures (one mip, the
gradient textures' layout) and points an effect's layers at them.

## Effect looks from rules (`EffectLooks.py`)

A mod's own HD effects, built from stock missile effects by a list of rules per look. Every
effect mod's `dev\build_effects.py` had its own copy of this loop (about a dozen copies, in
several versions); `EffectLooks.Builder` is the newest one (DruidGiantRaven's), so a build script
can keep only its drawings and its `LOOKS` (example names below are illustrative):

```python
import EffectLooks as L
LOOKS = {'crescent': ('holy_bolt', [L.tex(L.BASE, 'holybolt_core', 'pdo_crescent'),
                                    L.tint((0.9, 0.8, 0.3), (1.0, 0.85, 0.4))], [])}
builder = L.Builder(game, MOD, 'pdo', drawn=TEXTURES, atlas=ATLAS)   # atlas optional
manifest = builder.build(LOOKS)          # runs a recipe per particle file, fails on rules that fit nothing
builder.clean()                          # drops drawn textures, particle files and recipes no look uses
L.write_block(os.path.join(MOD, 'mod.js'), START, END, 'AUTHORED', manifest)
```

Rules: `tex` (a texture slot: property or feature, part of the old texture's name or `*`, drawn
art or a `data/...` path, layers), `mesh` (a mesh layer's model), `tint` (f3/f4 colour constants
near a colour), `vec` (a colour a script builds from three numbers), `prop` (a renderer setting),
`num` (single-number constants of a value). The tuple forms the mods already use are accepted as
they are. `on_effect` gets the descriptions before and after each file, for stills. The module
docstring has the details.

Checked 2026-11-16 on copies of two mods (the user's mods were not changed): DruidGiantRaven built
through `EffectLooks` gives byte-identical particle files, textures, recipes and manifest;
PaladinOaths (an older copy of the loop) the same, plus `"models": []` per look in its `mod.js`
block, which its install script does not read.

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
