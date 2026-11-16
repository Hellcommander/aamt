<#
.SYNOPSIS
    Rebuilds (or checks) a mod's copy of the game's HD model index, hd\model_lod_desc.bin (see README.md, "The model index").
.DESCRIPTION
    A mod that adds a model at a new path ships the game's model index with its own entries added. The index belongs to
    one game build, so after a game patch it has to be rebuilt: this reads the game's current index, works out its
    layout from the file, copies each donor's current entry for the mod's models (listed in the mod's model_index.json)
    and writes hd\model_lod_desc.bin and model_index.json back into the mod folder. Then install the mod again.
.EXAMPLE
    .\Update-D2RModelIndex.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Mod '<D2RMM>\mods\QuillRatDruid'
.EXAMPLE
    .\Update-D2RModelIndex.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Mod '<D2RMM>\mods\QuillRatDruid' -Check
    Exit code 0 = up to date, 1 = rebuild needed, 2 = the index format changed in a way the tool cannot follow.
#>
[CmdletBinding()]
param(
    [string]$GamePath = $env:D2R_PATH,
    [Parameter(Mandatory)][string]$Mod,
    [string]$CascLib = $env:D2R_CASCLIB,
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }
if (-not (Test-Path $Mod)) { throw "Mod folder not found: $Mod" }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$command = if ($Check) { 'check' } else { 'update' }
$arguments = @((Join-Path $PSScriptRoot 'ModelLodDesc.py'), $command, '--game', $GamePath, '--mod', $Mod)
if ($CascLib) { $arguments += @('--casclib', $CascLib) }
& $python @arguments
exit $LASTEXITCODE
