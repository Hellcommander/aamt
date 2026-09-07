#Requires -Version 5.1
<#
.SYNOPSIS
  Clone third-party sources that AAMT must not vendor (license isolation).
.DESCRIPTION
  Does not fetch the Qud Lab private simulator pack.
#>
param(
    [switch]$All,
    [switch]$TES5Edit,
    [switch]$FrankyCLI,
    [switch]$Arzedit,
    [switch]$RenoDx,
    [string]$ToolsRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
if (-not ($TES5Edit -or $FrankyCLI -or $Arzedit -or $RenoDx -or $All)) {
    $All = $true
}
if ($All) {
    $TES5Edit = $true
    $FrankyCLI = $true
    $Arzedit = $true
}

function Invoke-GitClone([string]$Url, [string]$Dest, [string]$Branch = '') {
    if (Test-Path (Join-Path $Dest '.git')) {
        Write-Host "Already cloned: $Dest"
        git -C $Dest pull --ff-only
        return
    }
    if ((Test-Path $Dest) -and (Get-ChildItem $Dest -Force | Where-Object { $_.Name -ne 'README.md' })) {
        Write-Host "Skip clone (folder not empty): $Dest"
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    if ($Branch) {
        git clone --depth 1 --branch $Branch --single-branch $Url $Dest
    } else {
        git clone --depth 1 $Url $Dest
    }
}

Write-Host "AAMT third-party fetch (gitignored; licenses stay upstream). Qud Lab sim is NOT included."

if ($TES5Edit) {
    Write-Host "`n[TES5Edit MPL-2.0]"
    $sync = Join-Path $ToolsRoot 'XEdit\Sync-TES5Edit.ps1'
    if (-not (Test-Path $sync)) { throw "Missing $sync" }
    & $sync
    Write-Host "Place xEdit64.exe / SF1Edit64.exe (4.1.5q+) in Tools\XEdit\bin yourself."
}

if ($FrankyCLI) {
    Write-Host "`n[FrankyCLI MIT — Bryn Stringer]"
    Invoke-GitClone 'https://github.com/kaosnyrb/FrankyCLI.git' (Join-Path $ToolsRoot 'FrankyCLI')
}

if ($Arzedit) {
    Write-Host "`n[arzedit — QuasiMod]"
    Invoke-GitClone 'https://gitlab.com/QuasiMod/arzedit.git' (Join-Path $ToolsRoot 'GrimDawn\arzedit\arzedit-master')
}

if ($RenoDx) {
    Write-Host "`n[RenoDX MIT — plus nested third-party]"
    Invoke-GitClone 'https://github.com/clshortfuse/renodx.git' (Join-Path $ToolsRoot 'GrimDawn\renodx-src')
}

Write-Host @"

Done. Not fetched (on purpose):
  - Caves of Qud / other game installs
  - Qud Lab private simulator (Fetch-PrivatePack.ps1 after access is granted)
  - Pixelorama (install to D:\tools\Orama Interactive\Pixelorama)
  - TranscendenceDev (Prepare-X64Workspace.py --api-root <official tree>)
  - Ollama / SD weights / Hugging Face caches

See ../LICENSING.md and ../THIRD_PARTY.md
"@
