# Sacred 2 Remaster tools

Assets for **S2X custom classes** (the class framework lives in the game folder: `Mods\S2X.md`, section "Custom
classes"; a class is the s2mm mod `Mods\mods\class-<id>` built from its `class.json`).

## s2r_class_assets.py - art icons and class portraits

```
Run-S2RClassAssets.bat plan     --class druid      what gets a picture, and the prompts
Run-S2RClassAssets.bat all      --class druid      generate what is missing (SD3.5), pack, write the manifest
Run-S2RClassAssets.bat icons    --class druid --only "Plague Bolt" --seed 7 --overwrite      re-roll one icon
Run-S2RClassAssets.bat portrait --class druid --overwrite --seed 3                            re-roll the portrait
Run-S2RClassAssets.bat import   --class druid --art "Plague Bolt" --png my.png               use your own picture
Run-S2RClassAssets.bat pack     --class druid      rebuild sheet + DDS from the finished cells
```

Then, in the game folder: `Mods\S2X-Classes.bat build druid` and deploy with `Mods\S2ModManager.bat`.

What it makes

| Asset | Game format | Where it goes |
|---|---|---|
| combat-art icon | 278 x 272 medallion (disc radius 103, gold ring) + 172 x 163 ringless buff version, sprites of a DXT5 sheet 1024 wide, no mips | `class-<id>\files\Remaster\Textures\S2X\<id>_arts.dds` |
| class portrait | 232 x 264 bust in a round frame (the size of the seven hero buttons) | `class-<id>\files\Remaster\Textures\S2X\<id>_class.dds` |
| manifest | which art sits where | `class-<id>\assets\icons.json`, read by `s2x-classes.py build` |

The builder turns the manifest into two `@spritesheet` blocks (appended to `Remaster\ui\Ingame\spells.rcss` and
`Remaster\ui\Global\mainMenuHeroElements.rcss` by patches of the class mod); a sprite is named after the art's
spell, which is how the game finds a combat art's icon.

Prompts come from `class.json`: per art `"art"` (what the emblem shows) and `"art_color"`, at the top level
`"art_colors"` (one disc colour per aspect tab) and `"portrait"`. Without `"art"` the art's name and description
are used. Only arts with their own `"name"` or `"art"` get a picture; `--all-arts` includes plain borrowed arts.

Pixels: SD3.5 through `Shared/sd_art.py` (:1338, GPU lock, cached raw images). The ring, disc mask, vignette,
sheet layout and DDS (texconv, `BC3_UNORM -m 1`) are done here; nothing is taken from the game's textures.
Working files and `preview.png` are under `Tools\Output\Sacred2\<id>\` - **look at preview.png after every run**
and re-roll what does not read as an emblem.

Not covered yet: effect textures / particle scripts for new arts, models, sounds.
