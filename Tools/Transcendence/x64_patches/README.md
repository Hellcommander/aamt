# x64 overlay patcher (opt-in)

Official Kronosaur / `TranscendenceDev-integration-APIxx` trees stay clean.

## Model

1. **Official tree** — upstream / human source (not rewritten by the patcher each build).
2. **Workspace** — `Tools/Transcendence/_x64_workspace/<ApiFolderName>/`  
   Copied from official; overlays applied here only.
3. **Deploy** — only `Transcendence.exe` / tools / `zlib1.dll` into the game folder (SteamAPI left disabled).

Anyone who later runs this patcher can mix whatever overlays they want into *their* local build.

## Scripts

| Script | Role |
|--------|------|
| `Prepare-X64Workspace.py` | Copy official → workspace |
| `Fix-TranscendenceX64.py` | v2: Kernel INT_PTR containers, mathRound |
| `Fix-TranscendenceX64V3.py` | v3: TLisp GetIntPtrValue, CObject/DXSparseMask, capacity, **va_list strPatternSubst**, **dibGetInfo BYTE***, **ASSERT→AssertFail.log (no DebugBreak)**, **CInteractionLevel clamp**, **uncappedFrameRate + CFixedSimClock** |
| `Fix-Api59BuildProjects.py` | JPEG Contributors configs, CSimViewer x64 (`--api-root`) |
| `Fix-Api59X64Deps.py` | zlib toolset / JPEG itemdefs (`--api-root`) |
| `Audit-X64Libs.py` | Reject x86-only `.lib` on x64 builds |
| `Fix-TranscendenceJobSystem.py` | Persistent `CJobSystem` + wreck-image prefetch |
| `Fix-TranscendenceForkGaps.py` | Runs for every platform. **features:** sealed sound archive (`Resources\sounds.mtsa`; overlay `fork_overlays/Mammoth/Include/SealedArchive.h`; `SealedKey.h` is generated from `Tools/Shared/audio_seal.key` and never stored) and the `isBound` TLisp primitive. **upstream-fixes** (optional, kept until upstream fixes them): CCAtomTable/CArchiver INT_PTR, ICCItem refcount pointer-sized, WndProc LRESULT, TLisp object refs pointer-sized (sysFindObject lists, gSource/gPlayerShip/gScreen, DefineSpaceObject: without it any object above 4 GB is a wild pointer, e.g. Eternity Port "No adventure defined"), nebula CTile section pointers (save format unchanged), smart-pointer NULL compares. **diagnostics:** native crashes inside TLisp primitives log `[crash] fn: exception at file:line` with a stack. **build-config:** LibJPEGTurboUtil, zlibstat CRT, TSUI Hexarc stub x64, sln mapping. Leave groups out with `"ForkGapsSkip": ["upstream-fixes"]` in `ApiSwitcher.config.json` |
| `Fix-ExtensionApi59Warnings.py` | Run on `Transcendence/TransCore` by the switcher (maxInSystem etc.) |
| `TranscendenceApiSwitcher.ps1` | `-Platform x64` uses workspace by default |

**Multiverse:** Hexarc username/password needs proprietary `HexarcKeys.h` (not in source). For Steam Multiverse use `-Configuration SteamRelease` and keep `steam_api.dll` (omit `-DisableSteamApi`).

## Typical command

```bat
TranscendenceApiSwitcher.bat -Api 59 -Platform x64 -Deploy -CompileTdb -DeployTools -ForceX64Autofix -NonInteractive
```

Steam Multiverse-capable deploy:

```bat
TranscendenceApiSwitcher.bat -Api 59 -Platform x64 -Configuration SteamRelease -Deploy -DeployTools -ForceX64Autofix -NonInteractive
```
# (SteamRelease defaults to leaving steam_api.dll enabled)
Refresh workspace from official after an upstream pull:

```bat
TranscendenceApiSwitcher.bat -Api 59 -SyncX64Workspace -ForceX64Autofix -Deploy -NonInteractive
```
