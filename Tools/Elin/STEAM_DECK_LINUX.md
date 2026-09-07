# Steam Deck / Linux Compatibility (Elin)

## Why this matters

Elin includes **BepInEx** pre-built. On **Windows**, custom code mods (`.dll` plugins / injectors) load normally.

On **Linux / Steam Deck** under **Proton**, Wine must be told to use the native `winhttp` DLL so BepInEx can inject. Without that, mods show up in the Workshop / Package folder but **custom scripts never load**.

## Required Steam launch option

For any code-based Elin mod distributed via Steam Workshop (or local Package), tell Linux/Steam Deck players to set Elin's Steam **Launch Options** to this **exact** text:

```bash
WINEDLLOVERRIDES="winhttp=n,b" %command%
```

### How to set it (Steam Deck / Desktop Linux)

1. Steam Library → **Elin** → Properties (gear) → **General**
2. **Launch Options** → paste the line above
3. Launch the game once and confirm BepInEx/plugins load (mod UI / log)

## What needs this

| Content type | Needs `WINEDLLOVERRIDES`? |
|--------------|---------------------------|
| BepInEx / Harmony plugins (`.dll`) | **Yes** |
| Injectors / custom scripts | **Yes** |
| XML / Excel / textures / AssetBundles only | No |

CustomRaceClassCreator is a **code-based** mod — include this note in Workshop descriptions and README when distributing.

## Workshop blurb (copy/paste)

```text
Steam Deck / Linux: Elin has BepInEx built in. Add this exact Steam launch option
so custom scripts load under Proton:

WINEDLLOVERRIDES="winhttp=n,b" %command%
```

## See also

- Mod README: `Elin\Package\Mod\CustomRaceClassCreator\README.md`
- `TROUBLESHOOTING.md` — plugin-not-loading checklist
