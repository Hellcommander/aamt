# Two Worlds II tools

Tools for Two Worlds II (Reality Pump), made for WorldMerge Reforged (2026-11-21):

- **Asset tools** (`tw2tex.py`, `tw2mesh.py`, `tw2texgen.py`, below): textures, meshes and AI-regenerated
  textures of Reforged's own.
- **Animation tools** (`tw2anim.py`, further down).

All of them read the game's archives through the archive and tree readers in `<TW2>\_modding\tools` (`wdtool.py`,
`chm.py`). The patcher (`tw2patch`) runs those at build time, so they live with the mod. `TW2_MODDING` points at
the `_modding` folder; otherwise the Steam paths in `tw2common.py` are used.

The tools only read the game. Output goes to `Output\` here (gitignored) and to tw2patch patch folders, never
`WDFiles`.

## Asset tools

```powershell
python tw2tex.py find WP_SWORD_1                      # textures by path: format, size, mips, archive
python tw2tex.py info WP_SWORD_109_bump.dds           # header + normal-map packing
python tw2tex.py export WP_SWORD_109.dds --out DIR    # -> PNG (+ _spec.png for AG normals) + .json sidecar
python tw2tex.py import DIR\WP_SWORD_109.png --out PATCH   # -> PATCH\files\Textures\WP_SWORD_109.DDS
python tw2tex.py index                                # once: texture -> meshes (Output\cache\texrefs.tsv)
python tw2tex.py uses WP_SWORD_109.dds                # which meshes, shaders and slots use it
python tw2mesh.py info  Models\EQ\WP\WP_SWORDS\WP_SWORD_20.vdf   # meshes, shader, texture slots and roles
python tw2mesh.py export ROBE_004_PA.chv out.glb      # glTF with base colour + normal textures (Blender, viewers)
python tw2mesh.py uvmap  Models\EQ\WP\WP_SWORDS\WP_SWORD_20.vdf  # UV wireframe over the texture
python tw2texgen.py gen WP_SWORD_109.dds --preview    # SD3.5 regeneration -> Output\patch (tw2patch patch)
python tw2texgen.py mesh Models\EQ\WP\WP_SWORDS\WP_SWORD_20.vdf  # every base texture of a mesh
python tw2texgen.py build WP_SWORD_109                # re-pack after editing Output\texgen\WP_SWORD_109\base.png
```

Any tool takes `--stock` to leave `Mods\*.wd` out, so it reads the unmodded game. Otherwise it reads what the
game loads, WorldMerge included.

- **`import` keeps the original's layout.** The DDS it writes has the original's format, header and mip
  layout. `--size` may change the resolution (keep powers of two).
  - Normal maps go back into the packing the game's shader reads.
  - A round trip of stock textures gives byte-identical headers and sizes, with under one colour level of mean
    error.
  - Compression is `texconv` (`Shared\tool_paths.texconv_exe`) when found, else Pillow.
- **`tw2texgen` repaints with img2img.** Most textures are unwrapped atlases, so it uses the stock texture as
  the layout reference (`--strength`, default 0.45). That keeps every UV island in place.
  - Afterwards it upscales (`--scale 2`), pulls the colours towards the stock palette (`--match`) and restores
    the stock alpha.
  - Wall, ground and bark textures are wrapped to tile; force this with `--tile` / `--no-tile`.
  - The normal map is kept by default (same UVs). `--normal derive` adds the new texture's detail to the stock
    normal map.
  - Every step's images and a `recipe.json` stay in `Output\texgen\<NAME>\`, per the toolkit's
    template-and-refine approach.
  - The patch folder gets a `mod.json` (off by default). Copy it to `<TW2>\_modding\patches\` and turn it on
    with tw2patch.
  - The new textures are our own files, so Reforged may ship them.
  - `--no-sd` runs the chain without SD, for testing.

### Asset formats (decoded 2026-11-21)

**Archive load order.** The tools read archives in the order the `_modding` build assumes: WDFiles sorted by
name (DLCs the game lacks are left out), then `Mods\*.wd`, with the later copy winning. This is not confirmed in
game.

**Meshes: `.vdf` (static) and `.chv` (skinned).** Both use the same tagged tree as `.chm` (below). Shader
`.efo` files and `.DX9` files use it too.

- **What a mesh container holds:**
  - `Vertexes`, `Faces` (u16 triangle indices), `NumVertexes`, `NumFaces` (the index count), `VertexFormat`,
    `Skinned`, `LODLevel`.
  - One material container (tag `0xFFFFFF03`): `ShaderName` (`*.efx`), `TexS0`..`TexS4`, `SpecColor`,
    `DestColor`, `AFactor`, fur and dest parameters.
- **Vertex layouts:**

| Layout | Stride | Contents |
|---|---|---|
| Static, format 1 | 36 bytes | position f32×3, normal u8 (z y x 0), tangent u8 (z y x sign), UV0, UV1 |
| Static, format 2 | 44 bytes | as format 1, plus UV2 (lightmaps) |
| Skinned (`.chv`) | 52 bytes | position, weights f32×3, bone indices u8×4, normal, tangent, UV0, UV1 |

- **Skinned meshes** also hold `NumBones`, `BoneIDS` (a 512-byte name per bone) and `BindMatrix`.
- **Face morph meshes** (`Models\FACE`) use 16 bytes per vertex and have no faces. The tools skip them.
- **Coordinates:**
  - Normals are D3DCOLOR-packed, and their direction agrees with the face winding.
  - Y is up and the space is left-handed (the glTF export negates Z).
  - V runs up the texture: v = 0 is the bottom row.

**Textures are DDS.** In a sample of 6,026 textures:

- **Formats:** DXT1 53%, DXT5 42%, A8R8G8B8 3%; DXT3, R8G8B8 and cube maps are rare.
- **Mips:** a full mip chain (79%) or one level (21%).
- **Lookup:** meshes name textures by bare file name, and the same name can sit in several folders. A
  replacement therefore keeps the original's full path.

**What each texture slot means.** The shaders' `.efo` files keep the Cg compiler's GLSL, which is where these
were read from. `tw2tex.slot_roles()` has the table.

- **`TexS0`: base colour.** Its alpha means different things per shader:
  - cut-out for `*_alpha`, leaves and grass;
  - reflection mask for `chrome*`;
  - unused otherwise.
- **`TexS1`: normal map.** Both packings are +Y up; this was checked against the paired base colours.
  - **AG** (`_BUMP`, DXT5): X in alpha, Y in green, specular in red, blue 0. Used by `metal`, `metal_char`,
    `lightmap*` and `chrome*`.
  - **RGB** (`_NORMAL`, and `_BDX1` in DXT1): a plain tangent-space normal. Used by `metalcity`, the most used
    shader, and by `lightmapcity`, `paralax` and `metal_wind*`.
- **`TexS2`:**
  - lightmap on UV2 (`lightmap*`);
  - dye mask on UV2 (`metal_char*`: four dye colours weighted by the mask's RGBA tint the base colour);
  - cube map (`chrome`).
- **`TexS3`:** extra colour (`chrome*`, `metal_blend`).

**Known bad file.** WorldMerge's `Models\MONSTERS\CYCLOP\OGRILOPS_01.chv` (in `Mods\WorldMerge_*.wd`) has one
material container whose size was never updated, and the tree reader rejects it. The stock game has no such
file.

## Animation tools

Made for the WorldMerge Reforged ostrich mounts. `tw2anim.py` runs the `_modding\tools` animation code in place.

## Animation formats (decoded 2026-11-21)

**`.chm` animation and `.chv` skin**: one tagged tree. `u32` magic `9F 99 66 F6`, then nodes: `u8 kind`,
`u32 size` (counts itself and the rest of the node). A container (kind 2) has a `u32 tag` and child nodes. A
value (kind 1) has a `u8 type`, a `u32` name length, the name and the value. Types: `0x11` u32, `0x12` i32,
`0x14` 4×f32, `0x15` 4×4 matrix (column-major), `0x16` string, `0x17` key array.

- **Scene nodes** are bones and Maya helpers. Each holds ParentID, SelfID, Name and optionally JointOrient.
  Its first child container (tag `0xFFFFFF01`) holds either a `SelfMatrix` or the tracks:
  `FramedataTNM/SNM/RNM` (key counts) and `FramedataTRN/SCL/ROT` (20-byte keys: `u32 frame` + 4×f32;
  rotations are quaternions xyzw).
- **The rotation keys already include the joint orient:** local = T·R·S, world = parent·local. Y is up and the
  creature faces +Z.
- **The whole file is one timeline** (`FirstFrame`..`LastFrame`). Every clip in an action set is a frame
  range on it.
- Names ending in `_` (`Tail_`, `RightWing_`) are tracked Maya control handles, not bones.

**`.act` action set** (XML): skins, bindpose, and one `ACTION` per state of the machine named in
`machine=`. An action holds a clip (`file`, `from`/`to` = absolute timeline frames, `start = -from × 10/3`),
speed data (`velocity`, `linearSpeedZ`, root-motion `FRAMES`/`FRAME`, `VELOCITYMUL`), `HOTSPOT`s (strikes
`HSA_STRIKE_*` on a bone, footsteps, breakables) and `LINK`s (blend-in per source state).

**`.smt` state machine** (XML): `STATE`s (numbered ids) and `LINK`s whose transitions use the engine's
inputs (`td`, `pf`, `vl` speed, `jump`, `action`, `use`, `landed`, ...). The exe names none of the states,
so a creature can have its own machine.

## Tools

```powershell
python tw2anim.py chm info  ANI_OST_01.chm                 # timeline, bones, key counts
python tw2anim.py chm roundtrip ANI_OST_01.chm             # byte-identical rewrite (also .chv)
python tw2anim.py pose sheet ANI_OST_01.chm out.png 450 490 # contact sheet of a frame range
python tw2anim.py clip make ANI_OST_01.chm kick.json kick_clip.json --sheet kick.png
python tw2anim.py chm append ANI_OST_01.chm kick_clip.json ANI_NEW.chm
```

**Clip presets** (`chm_clip.py`) are modelled on the Diablo II preset editor here (`Tools\DiabloII`):
- start from a stock range (resampled or looped);
- shape it with `rotate` (a bone about a world axis, eased degree keys), `exaggerate` (scale motion against
  a reference frame), `layer` (another range's motion on a bone subtree) and `seamless`.

The ostrich's presets are in `<TW2>\_modding\patches\MountOstrich\anim\`. Each was checked on contact sheets.

## AI-made clips (next step, not built yet)

`Tools\Shared\anim_client.py` can film and fit new motions, but it rigs its own skeleton (UniRig), and
nothing retargets that onto a game skeleton. The clean bridge skips UniRig and fits directly on the game
rig:

1. Decode the `.chv` mesh (same tree as `.chm`: vertices, bone weights) and write a `.glb` with the game
   skeleton and skin (the `Tools\DiabloII\Gltf.py` `write_rigged` pattern).
2. Give `anim_client` that rig as `rig.npz` (joints, parents, names, weights). Then run only
   `render,video,fit` with the ostrich prompts (`--body biped`).
3. Convert `clips/<clip>.npz` (wxyz rotations relative to the rest pose, plus root translation) into
   `chm.py` JSON clips: local = rest × delta. Append them with `chm.py append`.
