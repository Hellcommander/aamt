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
if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'ModConverter.py'), '--game', $GamePath, '--port', $Port)
if ($D2RMM) { $arguments += @('--d2rmm', $D2RMM) }
if ($NoBrowser) { $arguments += '--no-browser' }
& $python @arguments
exit $LASTEXITCODE
