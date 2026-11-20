<#
.SYNOPSIS
    Makes a D2RMM mod that replaces whole tables or string files merge them row by row instead
    (ConvertReplaceMod.py; see README.md, "Mods that replace whole files").
.EXAMPLE
    .\Convert-D2RReplaceMod.ps1 -Mod 'Better and New Unique Items', 'Better Body Armors__Shields__Weapons'
.EXAMPLE
    .\Convert-D2RReplaceMod.ps1 -Mod 'Better and New Unique Items' -Undo   # its own mod.js back
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Mod,
    [string]$GamePath = $env:D2R_PATH,
    [string]$D2RMM,
    [switch]$Undo,
    [switch]$NoCheck
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
$GamePath = Resolve-D2RGamePath $GamePath
$D2RMM = Resolve-D2RMMPath $D2RMM $GamePath
$python = Resolve-D2RPython
foreach ($m in $Mod) {
    $folder = if (Test-Path $m) { $m } else { Join-Path $D2RMM "mods\$m" }
    if (-not (Test-Path (Join-Path $folder 'mod.json'))) { throw "not a D2RMM mod: $folder" }
    $arguments = @((Join-Path $PSScriptRoot 'ConvertReplaceMod.py'), '--game', $GamePath, '--mod', $folder, '--d2rmm', $D2RMM, '--python', $python)
    if ($Undo) { $arguments += '--undo' } elseif (-not $NoCheck) { $arguments += '--check' }
    & $python @arguments
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
}
