# Choose Your Fighter (CoQ) — player tile + unfiltered detailed art

Import a real character (Recur export or save), then:

1. Generate an **in-game tile** by downscaling **detailed** art (SD draft or `--from-image`). Truecolor keeps those colors. Classic still maps the same painting onto black/white/transparent. The old 2-color silhouette stamp is opt-in (`--allow-silhouette`) and will lack detail.
2. Generate **unfiltered detailed art** via `Tools\UncensoredCharacterImageGenerator` — what the character really looks like, including broodlings / conjoined in-scene
3. Optionally generate **separate art for minions** (broodlings, conjoined mates, and normal followers)

## Quick start

```batch
ChooseYourFighter-GUI.bat
```

### Unfiltered art options (GUI)

| Option | Effect |
|--------|--------|
| Detailed fighter art | Full scene of the PC via unfiltered generator |
| Include broodlings in scene | Mentions a few broodlings around a Broodmother |
| Include conjoined in scene | Shows fused mates on the body |
| Separate art for minions/followers | One image each for companions |
| Minion set | All / followers only / broodlings only / conjoined only |

## CLI

```powershell
# Import
.\ChooseYourFighter.ps1 -Action Import -Path "...\Characters\Name.xml" -Pretty -Output ..\Output\Fighters\name\name.fighter.json

# Tile from detailed art (truecolor default; starts SD if needed)
.\ChooseYourFighter.ps1 -Action Tile -Path ..\Output\Fighters\name\name.fighter.json -TileSize vanilla -ColorMode truecolor -Animated

# Tile from an existing painting / SD draft
.\ChooseYourFighter.ps1 -Action Tile -Path ..\Output\Fighters\name\name.fighter.json -ColorMode truecolor -FromImage ..\Output\Fighters\name\fighter_Name.png -Animated -InstallMod

# Copy an existing CYF output folder into the tile pack
.\ChooseYourFighter.ps1 -Action Install -Path ..\Output\Fighters\oshwoyushur

# Unfiltered art: fighter scene + each follower/minion
.\ChooseYourFighter.ps1 -Action Art -Path ..\Output\Fighters\name\name.fighter.json -GenerateDetailedArt -GenerateMinionArt

# Followers only (normal companions — e.g. Maxatony)
.\ChooseYourFighter.ps1 -Action Art -Path ..\Output\Fighters\name\name.fighter.json -GenerateMinionArt -MinionFilter followers
```

Art payloads only (no SD run):

```powershell
python .\qud_fighter_import.py art "path\to\file.fighter.json" --pretty --minions
```

## Drop-in tile pack (requires Kernelmethod CYF)

Player tiles install into local pack **`Arendeth_CYFTiles`**, which **Requires** Workshop **Choose Your Fighter** (`Kernelmethod_ChooseYourFighter`):

`%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Arendeth_CYFTiles\`

- `Textures/Creatures/` — PNG tiles + animation frames
- `ChooseYourFighter.xml` — Kernelmethod CYF picker group (rebuilt by `-Action Install`)
- `Fighters/<id>/` — `*.tile.json` + optional `*.fighter.json`
- `Fighters.xml` — idle animation apply
- `modconfig.json` — `shaderMode: 1` for truecolor

The GUI checkbox **From detailed art / SD** (on by default) copies after Generate Tile. Pick the tile in CYF’s menu (group **Arendeth Character Looks**). Existing saves also apply when the player **name** matches a fighter **and** they still have the default kitty tile.

## Pairing with Truecolor Status Aura

For truecolor in-game tiles (`shaderMode: 1`), enable the local mod **`Arendeth_TruecolorStatus`** so HP stays glanceable without washing the sprite white. Classic dual-color CYF tiles still use stock HP recolor.

Companions are classified as:

- **broodling** — blueprint/name matches broodling patterns
- **conjoined** — conjoin / fusion markers
- **follower** — normal party companions (proselytes, pets, etc.)

Recur exports are required for reliable companion lists.

## Related: Atlas map art

For translating **Atlas of Qud** Automap tiles into non-tile illustrated maps (SD img2img), see `ATLAS_ART_TRANSLATOR.md` / `AtlasArtTranslator-GUI.bat`.

## Outputs

`Tools\Output\Fighters\<id>\`

- `Textures/Creatures/<id>.png` (+ frames if animated)
- `fighter_<name>.png` — unfiltered detailed art
- `minion_<name>.png` — per companion when enabled
- `art_payloads.json` — prompts/mutations/traits sent to the generator

## Character-sheet portrait

Arendeth_CYFTiles shows a large portrait of the player on the character sheet
(Attributes & Powers tab). The portrait is meant to be **detailed art**, showing the
character as they really look, since the UI is not held to the 16x24 tile. The mod
loads it at full size with mipmaps and scales it down smoothly in game, so install
the art as it is (for example 768x1024 SD output). Match the game's look: Bright Qud /
Choose Your Fighter, front-facing, chunky, bold dark outline, simple shaded materials.
With no picture the portrait is the live tile scaled up, so a layered fighter's
portrait still follows body, mutations and gear.

```powershell
# detailed art: SD art from -Action Art (fighter_<name>.png) or your own painting
.\ChooseYourFighter.ps1 -Action Install -Path <work_dir> -PortraitImage <png>
# pixel-art alternative: the character's layer composite enlarged 8x (classic fighters in their own colours)
python cyf_compose_fighter.py <work_dir> <Characters\Name.date.xml> --portrait [--portrait-scale 8]
.\ChooseYourFighter.ps1 -Action Install -Path <work_dir>   # copies <work_dir>\Textures\Portraits\<id>.png
```

**Layered portrait** (follows the character like the layered tile): split the art with a spec
that says where the removable parts are, then install:

```powershell
python cyf_portrait_layers.py <work_dir>\<id>.portrait.json <work_dir> --preview <work_dir>\preview
.\ChooseYourFighter.ps1 -Action Install -Path <work_dir>   # copies Textures\Portraits\<id>\
```

The spec (see the script's docstring; `Output/Fighters/rhomustos/rhomustos.portrait.json` is a
worked example) lists:
- `horns`: bone-coloured parts lifted off, scalp refilled under them;
- `eyes`: glow lifted off, dark sockets left in the base;
- `cuts`: polygons such as extra heads, with an outline "stump" layer shown when the part is gone;
- `sacks`: polygons traced along what stands in front, such as a brood sack;
- `order`: the draw order.

Each layer's `follow` names the tile layer IDs it goes with (`head2`, `!head2`, `glow_eyes,head2`).
`--preview` writes the composite with each optional part removed, and a contact sheet.

The picture lands in `Mods/Arendeth_CYFTiles/Textures/Portraits/<id>.png`. A PNG in
`CavesOfQud/CYFPortraits/<id>.png` wins over it and survives reinstalls. In game, wish
`cyfportrait <file>` picks a picture for the current character (`cyfportrait clear` undoes
it). Options: show the portrait, picture or live tile, and size.

## Layered fighters (`-Layered` / `--layered`)

`-Layered` (GUI checkbox **Mutation layers**) also writes `Textures/Layers/<id>/<plan>.png`,
one sheet per body plan (quadruped, biped, serpent, fish, blob, radial, robot, tree,
flower, fungus, cactus, chair, table, door, vessel), and a `layerSet` block in
`<id>.tile.json`. Row 0 of a sheet is the body; each further row is one layer (heads,
arms, legs, tail, fins, tentacles, roots, wings, horns, carapace, quills, claws, brood
sack, spectacles, ...); columns are frames, and a row whose frames are all the same
has one column. `<id>_layers_preview.png` shows per plan: body only, body with its
natural limbs, and every layer at once.

Install copies the sheets to `Mods/Arendeth_CYFTiles/Textures/Layers/<id>/` and writes
`<plan>`/`<layer>` entries into `Fighters.xml`. In game the pack picks the plan from the
player's anatomy and limbs and stacks the layers that match their limbs, mutations,
worn items and effects (see the pack's README).

`-BrightPalette` (GUI: **Bright Qud palette**, truecolor only) bakes the tile in Bright
Qud's palette so the fighter matches a Bright Qud world.

### Head styles

Layered sheets draw one of 12 heads: `cat`, `plain`, `canine`, `equine`, `avian`,
`reptile`, `insect`, `fish`, `robot`, `skull`, `fungal`, `plant`. Head parts (fangs,
tongue, breath, beak, spectacles, blinking, glowing eyes, albino) follow the chosen
head's eyes and mouth.

The style is picked in this order:
1. `-HeadStyle <style>` (GUI: **Head**, next to the bake button), or `"headStyle"` in
   the fighter JSON.
2. `cat` for feline fighters.
3. The first style with a keyword among the words of the fighter's name, genotype,
   subtype, mutations or description: robot (robot, android, golem, chromeling…),
   skull (skeleton, undead, ghoul…), insect (insect, beetle, ant, spider…), fish
   (fish, shark, merfolk…), avian (bird, owl, harpy…), reptile (lizard, snake,
   dragon, frog…), canine (dog, wolf, fox…), equine (horse, goat, camel, dromad…),
   fungal (fungus, mushroom, spore…), plant (plant, flower, vine, tree…). The full
   lists are `keywords` in `_HEAD_STYLES` in the generator.
4. Otherwise `plain`.

The grids live in `_HEAD_STYLES` (one character per pixel; the comment above it
lists the characters), so a new style is a new entry plus `--write-templates`.

### Templates and mod content

Layer art comes from the editable template pack `CYFTemplates/` (one sheet per body
plan and head style, painted in role key colours; see `CYFTemplates/README.md`).
`python qud_fighter_tile_generator.py --write-templates` writes missing sheets and
refreshes the legend and previews; `--templates DIR` / `--no-templates` pick another
pack or none.

`python cyf_scan_content.py` scans vanilla plus every enabled mod for mutations and
anatomies and writes `CYFTemplates/content_map.json` (anatomy → body plan, used by
`--layered` for each plan's anatomy list; a `"manual"` block overrides) and
`CYFTemplates/coverage.md` (which mutation shows on which layer). Rescan after adding
mods, then re-bake and Install.
