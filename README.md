# Asset & Mod Tools (AAMT)

Unofficial tools to **make mods, manage them, and use beside installed games**
(planners, choosers, labs). Original AAMT sources are MIT; generated mods are
yours; Qud Lab's simulator pack and third-party clones are not MIT and are not
in this repo. See [LICENSING.md](LICENSING.md).

**No warranty.** This is experimental, unofficial tooling — not a finished or
perfect toolset. Use at your own risk. Keep backups. The authors are not liable
for broken installs, lost data, or anything you do with it.

The public tree is ~**22 MB** of scripts and docs. A full local workspace can be
**tens of GB** (generated assets, reference art, third-party clones). Git ignores
that bulk — clone the factory, hydrate locally.

- License policy: [LICENSING.md](LICENSING.md)
- Download-yourself / access-gated pieces: [THIRD_PARTY.md](THIRD_PARTY.md)
- Tool docs and setup: [Tools/README_AAMT.md](Tools/README_AAMT.md)

## First clone

```powershell
cd Tools
.\Copy-LocalSettings.ps1              # *.example → machine-local settings
# Edit TranscendenceTools.ini, AssetGenerationSettings.ps1, Qud\settings.json

.\Fetch-ThirdParty.ps1                # optional upstream clones (xEdit, arzedit, …)
# Qud Lab simulator (only if you were granted the private pack):
.\Qud\QudLab\Fetch-PrivatePack.ps1 -Archive C:\path\to\QudLab-private.zip
```

Generated mods, meshes, and PNGs stay under gitignored `Output/`, `Shared/Concepts/`,
and per-game staging folders — regenerate with the tools, do not commit them.

Before your first commit: `cd Tools; .\Verify-PublicShare.ps1` (fails if large/binary
files would leak into the public tree).
