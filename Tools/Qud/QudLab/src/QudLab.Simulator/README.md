# Qud Lab restricted simulator (download-only)

Scenario implementations (`RestrictedSimulator.cs`, `*Scenario.cs`) are **not** in
the public git tree. They are proprietary
([LICENSE-PROPRIETARY.md](../../LICENSE-PROPRIETARY.md)).

Granting clone access to AAMT does **not** grant the simulator. The public tree
builds MIT **PublicStubs** plus `SimulatorFactory.cs`, which loads a compiled
private pack at runtime or refuses to simulate.

## Why compiled DLLs, not source or git

The restricted simulator can load Caves of Qud Managed assemblies and run
scenario logic that could be repurposed into a standalone arena runtime. Publishing
that as `.cs` in git would make reverse engineering trivial.

The pack is therefore:

- **Compiled** portable `net8.0` IL (not simulator source)
- **Out-of-band** — you receive a zip from the maintainer, not `git pull`
- **Gitignored** — `pack/`, `*.dll`, and `QudLab-private*.zip` never ship with the repo

This does not make decompilation impossible (dnSpy / dotPeek still apply), but it
keeps the public tree source-free, limits who has the binary, and preserves an
explicit grant: repo access ≠ sim access. See also the no-arena restrictions in
[LICENSE-PROPRIETARY.md](../../LICENSE-PROPRIETARY.md).

## Granted users (compiled pack — preferred)

You receive a zip with **portable `net8.0` IL** (Windows, Linux, or macOS with
the .NET 8 runtime — not Windows-only native code):

- `QudLab.Simulator.Private.dll`
- `QudLab.SimHost.Private.dll`

Install:

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
.\Fetch-PrivatePack.ps1 -Archive C:\path\to\QudLab-private.zip
dotnet build QudLab.sln -c Release
```

DLLs land in `pack\private\` and are copied beside CLI/SimHost outputs.
`SimulatorFactory` loads them via reflection — **no simulator source** is required.

Optional: Unity LoadFrom host scripts in the zip (`-IncludeUnityScripts` when the
maintainer built the pack). Those are still `.cs`, not a compiled Unity assembly.

You must own Caves of Qud (Steam or GOG). Do not copy game DLLs into this repo.

## Maintainers (build the pack)

With gitignored sources present locally:

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
.\Build-PrivatePack.ps1                    # writes QudLab-private-YYYYMMDD.zip
# optional: -IncludeUnityScripts -Runtime win-x64
```

Builds `QudLab.Simulator.Private` and `QudLab.SimHost.Private` (not in
`QudLab.sln`). Distribute the zip to granted users only — **do not commit** the
zip or DLLs; they stay gitignored.

## Legacy source zip

`Fetch-PrivatePack.ps1` still accepts a source archive (`RestrictedSimulator.cs`
+ scenarios) for maintainer rebuilds. End users should receive the **compiled**
zip instead.

## Public tree only

`qudlab simulate` and SimHost refuse until the pack is installed. UI, compile,
cache, and AI adapters still work under MIT.
