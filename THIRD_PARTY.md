# Third-party and download-only components

These are **not** AAMT MIT code. They stay out of git so their licenses cannot
be mixed into, or mistaken for, this toolkit. Clone or install them locally.

Run from `Tools/`:

```powershell
.\Fetch-ThirdParty.ps1
```

Qud Lab's restricted simulator is **not** fetched by that script. It is
access-gated. See `Tools/Qud/QudLab/Fetch-PrivatePack.ps1`.

## Third-party sources (you clone)

| Local path (gitignored) | Upstream | License | Fetch |
|---|---|---|---|
| `Tools/XEdit/vendor/TES5Edit` | https://github.com/TES5Edit/TES5Edit (`dev-4.1.6`) | MPL-2.0 | `Tools/XEdit/Sync-TES5Edit.ps1` |
| `Tools/XEdit/bin` | TES5Edit / SF1Edit **binary** (Discord `#xedit-builds`, 4.1.5q+) | TES5Edit terms | Place `xEdit64.exe` / `SF1Edit64.exe` yourself |
| `Tools/FrankyCLI` | https://github.com/kaosnyrb/FrankyCLI | MIT (Bryn Stringer) | `Fetch-ThirdParty.ps1 -FrankyCLI` |
| `Tools/GrimDawn/arzedit/arzedit-master` | https://gitlab.com/QuasiMod/arzedit | Upstream (see clone) | `Fetch-ThirdParty.ps1 -Arzedit` |
| `Tools/GrimDawn/renodx-src` | https://github.com/clshortfuse/renodx | MIT + nested third-party | `Fetch-ThirdParty.ps1 -RenoDx` |
| `Tools/Logs/pixelorama/pxo_src` | Do **not** vendor. Install Pixelorama. | MIT (Orama Interactive) | Install to `D:\tools\Orama Interactive\Pixelorama` |
| `Tools/Transcendence/_x64_workspace` | Official TranscendenceDev tree | Kronosaur (non-commercial; keep notice) | `Prepare-X64Workspace.py --api-root <official>` |
| `Tools/ReferenceAssets` | Optional art/reference packs | Each pack's own file | Copy locally; never required to run tools |

MPL-2.0 (TES5Edit) is file-level copyleft. Do not copy `.pas` definitions into
AAMT C# and relicense them as MIT. Read them; wrap them.

Kronosaur Transcendence source/art is **not** MIT and is **not** commercial
without their permission. Do not fold it into AAMT sources.

## Runtime tools (installers, not this repo)

Ollama, Python, ImageMagick, Blender, Stable Diffusion / Hugging Face weights,
Unity Editor, Conda — see `Tools/SETUP_REQUIRED_TOOLS.md`. Weights and
installers never belong in git.

## Qud Lab private pack (access-gated)

**Granted users** receive a zip of portable **`net8.0` IL** (not simulator source):

| File in zip | Installed to | License |
|---|---|---|
| `QudLab.Simulator.Private.dll` | `pack/private/` (+ CLI bin dirs) | [LICENSE-PROPRIETARY.md](Tools/Qud/QudLab/LICENSE-PROPRIETARY.md) |
| `QudLab.SimHost.Private.dll` | same | Same |
| Optional Unity `QudManagedHost.cs`, … | `UnityProject/Assets/QudLab/Scripts/` | Same |

| Maintainer-only (gitignored) | What |
|---|---|
| `Tools/Qud/QudLab/src/QudLab.Simulator/*.cs` (except `SimulatorFactory.cs`) | Simulator source compiled into the private DLL |
| `Tools/Qud/QudLab/src/QudLab.SimHost/Program.cs` | SimHost source compiled into the private DLL |
| `Tools/Qud/QudLab/pack/private/` | Local installed DLLs |

```powershell
# Maintainer (sources present):
Tools\Qud\QudLab\Build-PrivatePack.ps1

# Granted user:
Tools\Qud\QudLab\Fetch-PrivatePack.ps1 -Archive C:\path\to\QudLab-private.zip
```

Public clones build MIT stubs + `SimulatorFactory` (simulate refuses until the
pack is installed). Granting a git clone of AAMT does **not** grant the pack.

Requires a legitimate Steam or GOG Caves of Qud install. Never bundle game DLLs.

## Dumps (always gitignored)

Refresh from your own game install. Do not commit:

- Qud `obsolete_api_dump.json` (active, by-version, backups)
- Decompiled CoQ `.cs` in `Tools/Qud/` (EmbarkBuilder, etc.)
- Transcendence TDB dumps, FunctionList extracts, UNID/armorclass CSVs
- Soulash 2 `exe_strings.json` and similar exe extracts
- Migrator `reports/` of other people's mods
- Machine-local settings: `TranscendenceTools.ini`, `AssetGenerationSettings.ps1`, `Qud/settings.json`, `ApiSwitcher.config.json` (copy from `*.example` via `Copy-LocalSettings.ps1`)
- Game-derived charts/API maps: `Qud/data/charts/`, `Transcendence/api_rules*.json`, `VanillaDesignTypeMap.json`
- Elin spell-art catalogs: `spell_art_catalog.json`, `spell_art_queue.json`, `spell_art_chunks/`

## Generated assets (always gitignored)

The public repo stays ~22 MB; local workspaces can be tens of GB. Do not commit:

- `Output/`, `GeneratedAssets/`, `AI_Generated_Assets/`, `RegistryGeneratedAssets/`
- `Shared/Concepts/`, all `*.glb`
- Per-tool default staging: `Elin/ElinAssets/`, `CDDA/CDDAMods/`, `Terraria/TerrariaPortals/`
- Runtime generator registries under `Transcendence/*_registry.json`
- Soulash workshop fix snapshots under `SkillCreator/workshop_patches/`

Regenerate with the tools on your machine.

## Notices already in-tree

- Grim Dawn pipeline credits: `Tools/GrimDawn/NOTICE.md` (includes MIT from grim_dawn_mod_merger)
- Qud Lab MIT vs proprietary: `Tools/Qud/QudLab/LICENSE-MIT.md`, `LICENSE-PROPRIETARY.md`
