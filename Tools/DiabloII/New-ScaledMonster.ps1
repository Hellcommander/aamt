<#
.SYNOPSIS
    Builds scaled HD monster definitions for a Diablo II: Resurrected mod (see README.md).
.EXAMPLE
    .\New-ScaledMonster.ps1 -GamePath 'D:\games\Diablo II Resurrected' -OutDir '<D2RMM>\mods\QuillRatDruid'
.EXAMPLE
    .\New-ScaledMonster.ps1 -GamePath 'D:\games\Diablo II Resurrected' -Audit
#>
[CmdletBinding()]
param(
    [string]$GamePath = $env:D2R_PATH,
    [string]$OutDir,
    [string]$Preset = (Join-Path $PSScriptRoot 'Presets\quillrat_pack.json'),
    [string]$CascLib = $env:D2R_CASCLIB,
    [switch]$Audit
)
$ErrorActionPreference = 'Stop'
if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }
if (-not $Audit -and -not $OutDir) { throw 'Pass -OutDir (the mod folder), or -Audit to only report.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'ScaledMonster.py'), '--preset', $Preset, '--game', $GamePath)
if ($CascLib) { $arguments += @('--casclib', $CascLib) }
if ($Audit) { $arguments += '--audit' } else { $arguments += @('--out', $OutDir) }
& $python @arguments
exit $LASTEXITCODE
