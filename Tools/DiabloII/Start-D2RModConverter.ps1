<#
.SYNOPSIS
    Opens the mod converter in the browser: data mods (whole-file overrides) into D2RMM mods with a
    switch per feature and per D2RLoader plugin, and updates of converted mods from new downloads
    (see README.md, "Mod converter").
.EXAMPLE
    .\Start-D2RModConverter.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected'
#>
[CmdletBinding()]
param(
    [string]$GamePath = $env:D2R_PATH,
    [string]$D2RMM,
    [int]$Port = 8766,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
$GamePath = Resolve-D2RGamePath $GamePath
$D2RMM = Resolve-D2RMMPath $D2RMM $GamePath
$python = Resolve-D2RPython

$arguments = @((Join-Path $PSScriptRoot 'ModConverter.py'), '--game', $GamePath, '--d2rmm', $D2RMM, '--port', $Port)
if ($NoBrowser) { $arguments += '--no-browser' }
& $python @arguments
exit $LASTEXITCODE
