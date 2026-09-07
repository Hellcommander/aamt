# XEdit CLR (TES5Edit / SF1Edit)

AI-facing .NET 8 library + CLI for Bethesda plugin work. Record layouts come from the **current TES5Edit Starfield tree**, not the old 4.1.5f GitHub release.

## Fork (required)

| | |
|---|---|
| Repo | https://github.com/TES5Edit/TES5Edit |
| Branch | `dev-4.1.6` (default, 2026-08-10+) |
| Starfield defs | `Core/wbDefinitionsSF1.pas` |
| Why not 4.1.5f | Last packaged GitHub/Nexus zip is **4.1.5f** (2024-04). It cannot edit Starfield `.esp`, does not know small/medium/blueprint TES4 flags correctly for current masters, and is missing later DLC records. |

`dev-4.1.6` / **4.1.5q+** adds:

- Starfield `.esp` editing (with restrictions)
- Small / medium masters (252 full, 4095 light, 254 medium)
- Blueprint master rules (cannot save a module that has a blueprint master)
- Current official DLC list including Shattered Space and BlueprintShips-SFBGS050
- Reflection definitions (`wbDefinitionsReflection.pas`)

Vendor clone: `Tools/XEdit/vendor/TES5Edit` (sparse `Core`). Update with:

```
xedit-assist sync
```

or `Sync-TES5Edit.ps1`.

Put a **4.1.5q+** `xEdit64.exe` / `SF1Edit64.exe` in `Tools/XEdit/bin`. Discord `#xedit-builds` is where those binaries ship; this repo vendors **source definitions**, not the Delphi binary.

## CLI

```
cd "d:\games\Ai assisted toolkit\Tools\XEdit"
dotnet run --project XEdit.Assist -- locate
dotnet run --project XEdit.Assist -- fork
dotnet run --project XEdit.Assist -- defs --signature ALCH
dotnet run --project XEdit.Assist -- header Starfield.esm
dotnet run --project XEdit.Assist -- records poisons.esm --signature ALCH
```

`xedit-assist.bat` wraps the built exe.

Fast commands never launch xEdit. `dump` / `set` / `copy-override` / `add-record` do.

## Library

```csharp
using XEdit.Clr;
var x = new XEditClient();
var cat = x.Defs("ALCH");       // wbDefinitionsSF1.pas
var hdr = x.Header("MyMod.esm"); // Small/Medium/Blueprint flags
x.RunJob(new XEditJob { Op = "dump", Plugin = "MyMod.esm", EditorId = "MyPotion" });
```

New Starfield plugins should be **`.esm`**. Do not add `BlueprintShips-Starfield.esm` as a master unless you intend a blueprint-only file (xEdit will refuse to save mixed blueprint masters).
