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

The GUI checkbox **From detailed art / SD** (on by default) copies after Generate Tile. Pick the tile in CYF’s menu (group **Arendeth CYF Tiles**). Existing saves also apply when the player **name** matches a fighter **and** they still have the default kitty tile.

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
