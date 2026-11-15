# Fighter Studio

One window for the Choose Your Fighter art pipeline: pick a character from
`CavesOfQud/Characters`, get the picture prompt written from its build, bring the picture
back, turn it into a layered portrait, fit the gear, tune the 16x24 tile, install.

Start it with `Tools\Qud\FighterStudio.bat` (or `python fighter_studio.py` in this folder).

It adds no art code of its own beyond keying a backdrop and swapping tile colours. Every
other step runs the existing scripts in `Tools\Qud` and `Tools\Shared`, so their documents
(`CHOOSE_YOUR_FIGHTER.md`, `Shared\REFART.md`) still describe what happens underneath.
Each fighter's files stay in `Tools\Output\Fighters\<id>\`, in the layout those scripts use.

## Characters without an export

The list also shows characters that were never exported: fighter files in `Output\Fighters`
that were made from a build code (Yashrala), and `CavesOfQud\lastcharacter.txt` (the last
character built in the game). *Open another export...* takes a build code or fighter file too.
A build code holds the choices only, so for these the body comes from the chosen body plan,
stats are not used, gear is only what the fighter file lists, and gear fitting is off (no body
slots). An export of the same character replaces the entry once it exists.

## The tabs

| Tab | What it does | Runs |
|---|---|---|
| 1 Character | Shows the export and a table of how each mutation and body part looks. Orange rows are mutations the table does not know: write how they look, tick them, and optionally save the wording for every later character. | `traits.json` |
| 2 Prompt | Writes the prompt. *designer* is sentences for Microsoft Designer; *sdxl* is short tags plus a negative prompt for the local generator. *base* asks for the bare body (gear is layered on later); *dressed* is one picture with the worn gear. The text box is yours to edit; your wording is kept per fighter. | `studio_core.build_prompt`, optional `refart_client.py generate` |
| 3 Art | Imports the picture, finds the figure and the backdrop, and makes the one-layer portrait. The right side is a refart spec of the parts worth cutting into their own layers (tail, horns, extra heads, eye glow). | in-process keying; `refart_client.py layers` |
| 4 Gear | Lists equipped items and whether each has fitted art, and paints the missing ones onto the portrait. | `cyf_portrait_items.py --fitted` |
| 5 Tile 16x24 | Bakes the layer sheets, shows the tile as this character wears it (animated, at game size too), swaps colours, and moves layers to the portrait only. | `qud_fighter_tile_generator.py --layered`, `cyf_compose_fighter.py` |
| 6 Install | What exists so far, and the install into `Mods/Arendeth_CYFTiles`. | `ChooseYourFighter.ps1 -Action Install` |

Steps marked GPU ask first, say when the game is running (they are several times slower
then), and run one at a time through the toolkit's GPU lock.

## What the prompt is built from

- **Mutations**: `Name` + `Variant`, matched against `traits.json` the same way the layered
  tile matches them (lowercase substring, longest token wins).
- **Natural body items** (`<Behavior Blueprint=...>`, such as Pedestrian Paws or an Ovipositor).
- **Body parts**: counted by class the way the mod counts them (heads, arms, legs, tails,
  wings, tentacles). A part with its own rule (WM Gelatinous Form's Oral Arm) is described from
  its side and children.
- **Stats**: only the extremes (a slight frame, a powerful build) and only when no mutation
  already sets the build.
- **Tile colours**: used as the colour scheme when no mutation names a colour.
- **The fighter file's `hideLayers`**: a trait on a hidden layer starts unticked.
- Mental mutations are taken as invisible. Auras and emissions are listed as effect layers and
  never asked for in the base picture.

Parts marked *Separate* get a sentence telling the generator to keep them clear of the body, so
they can be cut into their own layers.

## Tile tools

The template tiles are flat two-tone pixel art with few colours, so two small tools go a long way:

- **Colours**: the list shows every colour on the rows this character shows. *Suggest from the
  portrait* moves the tile's two main colour families onto the portrait's two main colours and
  keeps each colour's own light or dark step. Click a right-hand swatch to choose a colour by
  hand. The preview updates at once; *Apply to the sheet* writes it (sheet backed up first).
- **Layers**: every layer the build matches, and whether it is on the tile or on the portrait
  only. *All effects: portrait only* clears auras off the tile in one go.

Baking again redraws every sheet from the templates. The window warns and copies the current
sheets to `_backup` first, because hand-drawn sheets live in the same files.

## Things to know

- The Gear tab has no prompt preview; it shows which items have art and asks before painting.
  (`cyf_portrait_items.py --fitted --dry-run` prints the prompts without a GPU job since
  2026-11-10, but still writes its work pictures, so run it on a copy of the portrait folder.)
- Designer cuts long prompts off, so *Short wording* is on by default and the counter warns
  past 800 characters. Untick traits or trim the text to get under it.
- Hair follows the house rule: a shaved head only for slime bodies, short cropped hair for
  everyone else, never a beard.
- A fighter file may carry `conceptNotes` (your wording rules for the character) and
  `designerPrompt` (the exact text that made the approved base). The Prompt tab shows the rules
  in its notes and opens on the approved text. The Studio keeps both keys when it rewrites the
  fighter file and never changes them.
- A fighter with a hand-made cut spec (`portrait_spec.json`, as Yashrala has) should be rebuilt
  from that spec; *Make portrait* warns before replacing it with a single keyed layer.
- Ask for a **dark teal** backdrop. A black one is as dark as the ink outline, so the outer
  line merges with it and pockets of backdrop enclosed by the body stay in. The Art tab says so
  when it sees one.
- *Make portrait* replaces `base.png` and `portrait.xml`. On a fighter that already has a
  layered portrait this drops the other layers from the list, so the window asks and copies the
  portrait folder to `_backup` first.
- Backups: `<work folder>\_backup\<name>.<date_time>` for work files,
  `CavesOfQud\_backups\Arendeth_CYFTiles_<date>studio_<time>` for the mod's copy before an install,
  `FighterStudio\_backup` for `traits.json`.
- `<id>.studio.json` in the work folder holds this window's settings for the fighter (prompt
  options, your wording, trait edits).

## Command line

```
python studio_core.py list
python studio_core.py traits <Characters\Name.date.xml>
python studio_core.py prompt <Characters\Name.date.xml> [--concept TEXT] [--subject TEXT]
       [--target designer|sdxl] [--picture base|dressed] [--outfit bare|wrap] [--backdrop "dark teal"] [--compact]
```
