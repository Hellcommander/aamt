# Qud Lab restricted simulator (download-only)

This folder's **scenario implementations** (`RestrictedSimulator.cs` and `*Scenario.cs`)
are **not** in the public git tree. They are proprietary
([LICENSE-PROPRIETARY.md](../../LICENSE-PROPRIETARY.md)).

Granting clone access to AAMT does **not** grant this code. The MIT files in
`PublicStubs/` compile a refusing stub so CLI / assistant still build.

## If you were granted the pack

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
.\Fetch-PrivatePack.ps1 -Archive C:\path\to\QudLab-private.zip
```

Drop these next to this README (gitignored):

- `RestrictedSimulator.cs`
- scenario / helper `*.cs` files from the pack

MSBuild then ignores `PublicStubs/` automatically.

You must own Caves of Qud (Steam or GOG). Do not copy game DLLs into this repo.

## If you only have the public tree

`qudlab simulate` and Unity LoadFrom host refuse until the pack is installed.
UI, compile, cache, and AI adapters still work under MIT.
