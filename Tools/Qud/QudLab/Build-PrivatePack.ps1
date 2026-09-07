#Requires -Version 5.1
<#
.SYNOPSIS
  Build a portable compiled Qud Lab private pack (no simulator source).
.DESCRIPTION
  Compiles gitignored simulator / SimHost sources to net8.0 IL (runs on Windows,
  Linux, and macOS with the .NET 8 runtime — not a Windows-only native binary).
  Optional -Runtime publishes a native host RID in addition to the portable DLLs.

  The zip is what you give granted users. They never receive .cs.
#>
param(
    [string]$LabRoot = $PSScriptRoot,
    [string]$Configuration = 'Release',
    [string]$OutputZip,
    [string]$Runtime = '',
    [switch]$IncludeUnityScripts
)

$ErrorActionPreference = 'Stop'
$simCs = Join-Path $LabRoot 'src\QudLab.Simulator\RestrictedSimulator.cs'
if (-not (Test-Path -LiteralPath $simCs)) {
    throw "Private simulator sources not found at $simCs. This script is for the maintainer tree."
}

$privateSim = Join-Path $LabRoot 'src\QudLab.Simulator.Private\QudLab.Simulator.Private.csproj'
$privateHost = Join-Path $LabRoot 'src\QudLab.SimHost.Private\QudLab.SimHost.Private.csproj'
if (-not (Test-Path $privateSim)) { throw "Missing $privateSim" }

Write-Host "Building portable net8.0 private libraries ($Configuration)..."
dotnet build $privateSim -c $Configuration --nologo
if ($LASTEXITCODE -ne 0) { throw "Simulator.Private build failed" }
dotnet build $privateHost -c $Configuration --nologo
if ($LASTEXITCODE -ne 0) { throw "SimHost.Private build failed" }

$packDir = Join-Path $LabRoot 'pack\private'
New-Item -ItemType Directory -Force -Path $packDir | Out-Null

$simDll = Join-Path $LabRoot "artifacts\bin\QudLab.Simulator.Private\$Configuration\net8.0\QudLab.Simulator.Private.dll"
$hostDll = Join-Path $LabRoot "artifacts\bin\QudLab.SimHost.Private\$Configuration\net8.0\QudLab.SimHost.Private.dll"
if (-not (Test-Path $simDll)) { throw "Missing $simDll" }
Copy-Item $simDll $packDir -Force
Copy-Item $hostDll $packDir -Force

if ($Runtime) {
    Write-Host "Also publishing RID $Runtime (optional native host)..."
    dotnet publish $privateHost -c $Configuration -r $Runtime --self-contained false --nologo
}

$stage = Join-Path $env:TEMP ("QudLab-private-pack-" + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item (Join-Path $packDir 'QudLab.Simulator.Private.dll') $stage -Force
Copy-Item (Join-Path $packDir 'QudLab.SimHost.Private.dll') $stage -Force
Copy-Item (Join-Path $LabRoot 'LICENSE-PROPRIETARY.md') $stage -Force -ErrorAction SilentlyContinue

@"
Qud Lab private pack (compiled, portable net8.0 IL)
===================================================
Requires: .NET 8 runtime on Windows, Linux, or macOS.
Does not include Caves of Qud, game DLLs, or simulator source.

Install:
  .\Fetch-PrivatePack.ps1 -Archive <this.zip>

NO WARRANTY. Use at your own risk. See LICENSE-PROPRIETARY.md.
Do not use as a standalone Qud runtime or arena game.
"@ | Set-Content (Join-Path $stage 'README.txt') -Encoding UTF8

if ($IncludeUnityScripts) {
    $unityDest = Join-Path $stage 'Unity'
    New-Item -ItemType Directory -Path $unityDest | Out-Null
    $unitySrc = Join-Path $LabRoot 'UnityProject\Assets\QudLab\Scripts'
    foreach ($name in @('QudManagedHost.cs', 'QudRestrictedObjectSim.cs', 'QudZoneGetProbe.cs')) {
        $p = Join-Path $unitySrc $name
        if (Test-Path $p) { Copy-Item $p $unityDest -Force }
    }
}

if (-not $OutputZip) {
    $OutputZip = Join-Path $LabRoot ("QudLab-private-{0:yyyyMMdd}.zip" -f (Get-Date))
}

if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $OutputZip
Remove-Item $stage -Recurse -Force

Write-Host "Wrote $OutputZip"
Write-Host "Give this zip to granted users. It contains DLLs only (unless -IncludeUnityScripts)."
