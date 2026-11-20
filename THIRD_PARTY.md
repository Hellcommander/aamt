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
| `Tools/DiabloII/thirdparty/ooz` | https://github.com/powzix/ooz (`bitknit.cpp`, the BitKnit decoder) | No licence file upstream (checked 2026-11-13); the Diablo II notes treat it as GPLv3. Not MIT either way | `Fetch-ThirdParty.ps1 -BitKnit` (reference source only) |
| `%LOCALAPPDATA%\D2RModAssets\thirdparty\bitknit.py` (outside the repo) | Python port of that decoder, `decompress(data, size)`; `Tools/DiabloII/Granny.py` and `GrannyFile.py` load it to unpack D2R's Granny files | Derived from the above; same terms | Make or place it yourself; `D2R_BITKNIT` names another folder |
| `%LOCALAPPDATA%\D2RModAssets\thirdparty\TripoSR` (outside the repo) | https://github.com/VAST-AI-Research/TripoSR, `git clone --depth 1`; weights `stabilityai/TripoSR` from Hugging Face on first use (about 1.7 GB, in the Hugging Face cache) | MIT (code and weights) | `Tools/DiabloII/SpriteMeshAI.py` imports it from there; its `torchmcubes` and `rembg` imports are replaced by stand-ins in that file, so nothing needs compiling. pip: omegaconf, einops, transformers, trimesh, scikit-image |
| `%LOCALAPPDATA%\D2RModAssets\pluginsdk\<ref>-<commit>` (outside the repo) | https://github.com/D2RLoader/PluginSDK, downloaded by `Tools/DiabloII/PluginSdk.py` (zip from codeload); `apply` copies its `include\`, `README.md` and `LICENSE` into the game's `mods\SkillTab4\sdk` | MIT (D2RLoader contributors) | `Update-D2RPlugins.ps1 -SdkDiff` / `-SdkApply` (downloads on use) |
| Python package `meshlib` (pip; checked with 3.2.0.29) | https://github.com/MeshInspector/MeshLib, mesh processing. `Tools/DiabloII/MeshImport.py` uses its quadric edge collapse (`mrmeshpy.decimateMesh`) to make the lower LODs of an imported body; without it the importer falls back to its own grid merge. A source clone for reading sits in `Tools/Shared/third_party/MeshLib` (v3.2.0.29-28-g6b25f5f31), not built, not used at run time | MeshLib licence (`LicenseRef-MeshLib`): free for non-commercial and educational use, a paid licence for commercial use. Nothing of it is copied into this repository | `pip install meshlib` |
| `Tools/Shared/third_party/pmp-library` (source clone, 3.0.0-310-gfc0bfd7a) | https://github.com/pmp-library/pmp-library, C++ mesh processing (decimation, remeshing, hole filling, smoothing, subdivision, parameterization). `Tools/Shared/pmp_wrap` (the toolkit's own C interface and CMake file) builds it statically into `Tools/Shared/third_party/pmp-build/pmpwrap.dll`; `Tools/Shared/pmp_lib.py` calls that, and `Tools/DiabloII/MeshUnwrap.py` uses its conformal map to unwrap meshes that have no UVs. Neither the clone nor the DLL is in the repository | MIT (bundles Eigen 5.0.1, MPL-2.0, and Shewchuk's predicates, public domain) | `git clone https://github.com/pmp-library/pmp-library Tools/Shared/third_party/pmp-library`, then `Tools/Shared/pmp_wrap/Build-PmpWrap.ps1` (CMake 3.20+, MSVC) |
| `Tools/DiabloII/third_party` (downloads, git-ignored, 952 MB) | Community tools from https://www.d2rmodding.com/#downloads, fetched by the user 2026-11-19: Noesis with a GR2 reader script (Jayn23, v1.3.5) and D2R sprite / texture scripts, RAD's `granny2.dll`, MoPaH 0.4 (Bonesy: model converter, GR2 viewer), SpriteEditor 2.0, AnimData editor and DS1 editor (Paul Siramy), AFJ Sheet Edit, D2TxtCompare, D2RBinTool (excel `.bin` compiler ported from a decompilation of `D2R.exe`), Ladik's CASC Viewer, PKBlaster, an upscaled sprite pack, icon PSDs, two PowerShell scripts | Each tool's own terms; mostly closed freeware with no licence text. `granny2.dll` is RAD Game Tools' proprietary runtime. D2RBinTool is derived from the game's decompiled code. None of it may be copied into this repository or shipped | Reference only. Nothing here is run by a toolkit script. Read as text so far: the Noesis scripts (confirmed texture format 0x39 = BC1, and that normal maps keep x in alpha) |
| Python package `capstone` (pip) | https://www.capstone-engine.org, x86-64 disassembler used by `Tools/DiabloII/PluginAddresses.py` to mask relative operands when finding moved game routines | BSD-3-Clause | `pip install capstone` |
| `Tools/Logs/pixelorama/pxo_src` | Do **not** vendor. Install Pixelorama. | MIT (Orama Interactive) | Install to `D:\tools\Orama Interactive\Pixelorama` |
| `Tools/Transcendence/_x64_workspace` | Official TranscendenceDev tree | Kronosaur (non-commercial; keep notice) | `Prepare-X64Workspace.py --api-root <official>` |
| `Tools/ReferenceAssets` | Optional art/reference packs | Each pack's own file | Copy locally; never required to run tools |
| `Tools/Shared/third_party/node/node_modules/rea-agents` | https://www.npmjs.com/package/rea-agents (REA, Reverse Engineer Anything; source https://github.com/morluto/rea) and its npm dependencies | MIT (dependencies MIT / ISC / Apache-2.0 / BSD / BlueOak) | `Fetch-ThirdParty.ps1 -AgentBridge`; started as an MCP server by the agent bridge at run time, never bundled into the `.vsix` |
| `Tools/Shared/third_party/node/node_modules/pdfjs-dist` | https://github.com/mozilla/pdf.js (npm `pdfjs-dist`) | Apache-2.0 (Mozilla) | `Fetch-ThirdParty.ps1 -AgentBridge`; imported by the agent bridge's `AnalyzeFile` at run time, never bundled |
| 7-Zip (installed program, outside the repo) | https://www.7-zip.org | LGPL-2.1 + unRAR restriction | Install it yourself; the agent bridge only runs `7z.exe` as a separate process (no code linked or copied) |
| `Tools/CortexIDE/local-agent-bridge/media/react*.production.min.js` | React 18.3.1 UMD builds (https://unpkg.com/react@18.3.1, `react-dom@18.3.1`) | MIT (Meta) | `Tools/CortexIDE/local-agent-bridge/Build-Vsix.ps1` (SHA-256 pinned; shipped inside the built `.vsix`) |

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

## Design credits (ideas only, no code copied)

| AAMT files | Inspired by | License | What was taken |
|---|---|---|---|
| `Tools/CortexIDE/local-agent-bridge/lib/permissions.js`, `agents.js`, `commands.js`, `instructions.js`, `tool-output.js` | opencode, https://github.com/anomalyco/opencode | MIT, Copyright (c) 2025 opencode | Design of permission rules (last match wins, allow / ask / deny), named build / plan / explore agents and Markdown agent files, Markdown slash commands (`$ARGUMENTS`, `$1`, `` !`cmd` ``), `AGENTS.md` instruction loading, saving cut tool output to a file. Written from opencode's documentation; each file names opencode in its header. Not affiliated with or endorsed by opencode. |

## Notices already in-tree

- Grim Dawn pipeline credits: `Tools/GrimDawn/NOTICE.md` (includes MIT from grim_dawn_mod_merger)
- Qud Lab MIT vs proprietary: `Tools/Qud/QudLab/LICENSE-MIT.md`, `LICENSE-PROPRIETARY.md`
