# OSF UI generator

Turns a plugin INI into an in-game settings page and optional HTML view for [OSF UI 1.5](https://www.nexusmods.com/starfield/mods/).

FrankyCLI writes Starfield records. This tool writes the UI those records sit behind.

## Layout OSF UI actually reads

```
Data/SFSE/Plugins/OSFUI/settings/<author>.<mod>.json
Data/SFSE/Plugins/OSFUI/views/<author>.<mod>/<view>/
    manifest.json  index.html  main.js  style.css
```

Mod ids look like `arendeth.arcane-conduit`. A single word like `SFMAG` is rejected.

## Commands

```bat
python osfui_gen.py from-ini path\to\Mod.ini --mod-id arendeth.mod --title "Mod Name" -o specs\arendeth.mod.json
python osfui_gen.py validate specs\arendeth.mod.json
python osfui_gen.py install specs\arendeth.mod.json
python osfui_gen.py preview specs\arendeth.mod.json --open
python generate_all.py --install --preview
```

## Setting types

`bool` `int` `float` `enum` `flags` `string` `key`, plus `action` for a button.

String color pickers use `"widget": "color"`. Numbers can use `"widget": "stepper"`.

Keys and labels are plain English (`Essence.MaxEssence`, "Max essence"). INI prefixes like `fMaxEssence` stay in the INI; they never become UI names.
