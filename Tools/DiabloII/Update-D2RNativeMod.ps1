<#
.SYNOPSIS
    Installs or updates a mod that already is a D2RMM mod (mod.json + mod.js, e.g. Relics of
    Sanctuary) with NativeModUpdate.py: staged, patched so it does not overwrite other mods'
    pause-menu buttons, test-run, then put in place with its D2RMM settings kept.
.DESCRIPTION
    -Install takes a download (folder, .zip, .7z, .rar) and puts it in <D2RMM>\mods\<-Id>.
    -Mod updates a mod installed that way: from -Source, or else the newest download with the
    same Nexus name in the folder the last one came from, the game or D2RMM folder or Downloads.
    The old version comes back if anything fails. -DryRun stops before touching mods\.
.EXAMPLE
    .\Update-D2RNativeMod.ps1 -Install 'D:\games\Steam\steamapps\common\Diablo II Resurrected\RelicsOfSanctuary 745 3.5.0 2026-11-09T22-15Z xzHHu6uYW' -Id RelicsOfSanctuary
.EXAMPLE
    .\Update-D2RNativeMod.ps1 -Mod RelicsOfSanctuary
.EXAMPLE
    .\Update-D2RNativeMod.ps1 -Mod RelicsOfSanctuary -Source "$env:USERPROFILE\Downloads\RelicsOfSanctuary 745 3.6.0 2026-12-01T10-00Z abc.zip"
#>
[CmdletBinding(DefaultParameterSetName = 'Update')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Update')][string]$Mod,
    [Parameter(ParameterSetName = 'Update')][string]$Source,
    [Parameter(Mandatory, ParameterSetName = 'Install')][string]$Install,
    [Parameter(ParameterSetName = 'Install')][string]$Id,
    [string]$GamePath = $env:D2R_PATH,
    [string]$D2RMM,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
$GamePath = Resolve-D2RGamePath $GamePath
$D2RMM = Resolve-D2RMMPath $D2RMM $GamePath
$python = Resolve-D2RPython

$arguments = @((Join-Path $PSScriptRoot 'NativeModUpdate.py'), '--game', $GamePath, '--d2rmm', $D2RMM)
if ($Install) {
    $arguments += @('--install', $Install)
    if ($Id) { $arguments += @('--id', $Id) }
} else {
    $arguments += @('--update', $Mod)
    if ($Source) { $arguments += @('--source', $Source) }
}
if ($DryRun) { $arguments += '--dry-run' }
& $python @arguments
exit $LASTEXITCODE
