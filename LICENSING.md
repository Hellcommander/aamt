# Licensing

This tree is **Asset & Mod Tools (AAMT)** by Gregory Armstrong (Arendeth). Licenses are
split so original tools stay permissive, third-party code keeps its own terms,
and nothing in this repo can relicense someone else's mod, game, or generated
output.

Read this file before copying code between folders or publishing a fork.

## Layers

| Layer | License | In git? |
|---|---|---|
| Original AAMT tools, docs, and MIT-marked Qud Lab UI/helpers | [MIT](LICENSE) | Yes |
| Mods / assets / plugins **this toolkit generates** | **Yours** (or the target game's mod terms). AAMT does not attach. | Generated dirs are gitignored |
| Qud Lab restricted simulator, SimHost, Unity LoadFrom host | [Proprietary](Tools/Qud/QudLab/LICENSE-PROPRIETARY.md) | **No** — download-only after access is granted |
| Vendored / cloned third-party sources (xEdit, FrankyCLI, TranscendenceDev, Pixelorama, arzedit, RenoDX, …) | **Upstream license unchanged** | **No** — you clone or install them |
| Game installs, DLLs, art, **dumps**, decompiled sources | Game publisher / mod author | **Never** |

MIT is used because it is permissive. It does **not** copyleft, share-alike, or
force downstream mods onto AAMT's license. Do not add GPL, AGPL, LGPL, MPL, or
CC-BY-SA code into original AAMT sources — those terms would conflict with MIT
and with proprietary game tooling.

## No warranty

AAMT is **unofficial experimental tooling**, provided **AS IS** with **no warranty**
of any kind (see [LICENSE](LICENSE)). It is not a finished or perfect toolset.
Use at your own risk. Keep backups of game installs and mods. The authors are
not liable for data loss, broken mods, ToS issues, or anything else that
follows from using these tools.

## Generated output

Running these tools does not place AAMT's MIT license (or Qud Lab's proprietary
license) on the files you produce. You choose the license for your mods. You
still must respect the **game's** EULA and any third-party assets you ingested.

## Qud Lab dual license

Open components (CLI UX, Unity shell UI, AI adapters, templates, public stubs)
are MIT: [Tools/Qud/QudLab/LICENSE-MIT.md](Tools/Qud/QudLab/LICENSE-MIT.md).

The **restricted Caves of Qud simulator** and related host code are proprietary
and **not shipped in the public tree**. Granting git access to AAMT does not
grant the simulator. Granted users unpack a **compiled DLL zip** via
`Fetch-PrivatePack.ps1`; maintainers build it with `Build-PrivatePack.ps1`
(see [THIRD_PARTY.md](THIRD_PARTY.md) and
`Tools/Qud/QudLab/src/QudLab.Simulator/README.md`).

That split exists so the simulator cannot be used as a standalone Qud runtime
and so Caves of Qud assemblies/assets are never redistributed.

## What not to commit

- Game `Managed` / `StreamingAssets` / TDB dumps / obsolete-API JSON dumps /
  FunctionList extracts / decompiled `EmbarkBuilder` / `GameObject` sources
  / workshop reports — all gitignored. Refresh dumps from your own install.
- **Generated assets** — `Output/`, `Shared/Concepts/`, `*.glb`, per-game staging
  (`ElinAssets/`, `CDDAMods/`, `TerrariaPortals/`), runtime registries, spell-art
  catalogs. Regenerate locally; keeps the public repo ~22 MB instead of tens of GB.
- Machine-local settings — copy from `*.example` via `Tools/Copy-LocalSettings.ps1`
- Workshop or LocalLow mods you do not own
- Private Qud Lab simulator sources and `pack/private/` DLLs (download-only)
- Third-party clones listed in [THIRD_PARTY.md](THIRD_PARTY.md)
- Secrets, Hugging Face tokens, Ollama keys

Fetch public third-party trees with `Tools/Fetch-ThirdParty.ps1`.
Build a Qud Lab private DLL pack with `Tools/Qud/QudLab/Build-PrivatePack.ps1`
(maintainer only). Granted users install with `Fetch-PrivatePack.ps1`.
