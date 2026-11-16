# CYF layer templates

Editable art for layered Choose Your Fighter tiles (`qud_fighter_tile_generator.py --layered`,
`ChooseYourFighter.ps1 -Layered`, the in-game pack `Arendeth_CYFTiles`).

## What is here

| File | What it is |
|---|---|
| `<style>/<plan>.png` | One template sheet per head style and body plan. The 12 styles are cat, plain, canine, equine, avian, reptile, insect, fish, robot, skull, fungal and plant. A bake uses the folder of the fighter's head style (see `CHOOSE_YOUR_FIGHTER.md`, "Head styles"). |
| `templates.json` | Row order (`rows`), key colour per role (`roles`), alpha of see-through roles, frame count. |
| `legend.png` | Every role's key colour with its hex code. |
| `preview/<style>_<plan>.png` | Each sheet in game colours with row labels, and a faint body under every layer. |
| `content_map.json` | Body plan for every anatomy in vanilla and the enabled mods, and the layers each mutation turns on. Written by `cyf_scan_content.py`. |
| `coverage.md` | Readable version of the content map: which anatomy uses which plan, which mutation shows on which layer, which mutations have no picture. |

There are 15 plans: quadruped, biped, serpent, fish, blob, radial, robot, tree, flower,
fungus, cactus, chair, table, door, vessel.

A sheet is 8 frame columns of 16×24. Row 0 is the plan's body; every other row is one layer, in the order of `templates.json` `rows`. That order is the same as `_LAYER_DEFS` in the generator, without the `phase` fade layer.

The layers fall into these groups:

- **Limbs**: wings, tail, roots, legs, arms2, arms, fin, tentacles, head1–head4.
- **Body coverings**: astral, carapace, scales, leaves, fur, feathers, muscle, slime, heart, humps, quills.
- **Head parts**: ears, horns, beak, gills, fangs, tongue, glow_eyes, third_eye, spectacles, blink, breath, halo, psi.
- **Auras and effects**: gas_toxic, gas_mind, gas_steam, shadow, speed, levitate, webs, flames, frost, sparks, light, regen, orbit, force, vortex.
- **Other**: apron, brood, conjoined, claws, hooks, tendril, stinger, albino, albino_head, antenna.

## Painting

- Paint with the **key colours** in `legend.png`. Each key colour is a role (body, belly, eye, horn, flame…). When a fighter is baked, every key colour becomes that fighter's own colour for the role, and the pixel keeps its alpha. So one template serves every fighter.
- Any colour that is not a key colour is used exactly as painted.
- A transparent cell means "nothing". A row left empty in a plan is skipped. If you paint into an empty row, that layer appears for every fighter baked afterwards.
- Animation repeats every 8 frames. Fighters with fewer frames use the first columns; those with more wrap around.
- Untouched templates bake byte-for-byte the same as the generator's built-in drawing.
- The head rows (`head1`–`head4` and the head parts) differ per style folder. Edit the
  folder of the style you want to change; the other layers are the same in every folder.
- Adding a role (as `mandible` was for the insect head) changes the key colours, so
  regenerate with `--force-templates` before painting, or repaint edited cells.

## Commands

From `Tools/Qud`:

```bash
python qud_fighter_tile_generator.py --write-templates
```

This writes any missing sheets and refreshes `templates.json`, `legend.png` and the previews. It keeps edited sheets. Add `--force-templates` to start over from the built-in drawing.

```bash
python cyf_scan_content.py
```

This rescans vanilla plus every enabled mod (local `Mods` and Workshop, as `ModSettings.json` enables them) and rewrites `content_map.json` and `coverage.md`. Run it after adding mods, then bake the fighter again so its `Fighters.xml` lists the new anatomies. To put an anatomy on a different plan, add it to `"manual"` in `content_map.json` (for example `"MyMod_Hound": "quadruped"`); rescans keep that block.

A layered bake uses this folder automatically:

- `--templates DIR` uses another pack.
- `--no-templates` ignores the pack.

## How the game uses it

`Arendeth_CYFTiles` picks the plan from the player's anatomy:
1. It first looks for the anatomy name in each plan's list (vanilla and scanned mods).
2. If no plan lists it, it decides by limbs: roots → tree, 3+ legs → quadruped, arms or legs → biped, fins → fish, head and tail → serpent, a chassis → robot, anything else → blob.

Limb layers count limbs by class: `#head`, `#arm`, `#leg`, `#tail`, `#fin`, `#tentacle`, `#roots`, `#wing`. The class comes from each body part's own variant name, so modded parts such as Spider-Leg, Hypha Head or Doll-Like Biocybernetic Arm count. Legs are counted two ways, which are then added together:
- foot parts compared with paired foot slots;
- leg parts compared with "Legs" slots.

So an insect has 6, a humanoid with Multiple Legs has 4, and an uplifted horse has 4.

Mutation layers match lowercase tokens against the mutation's class and name. A plan can have at most 64 layers, because the mod keeps them in a 64-bit mask. The generator refuses to bake more.
