<#
.SYNOPSIS
    Command line of the particle effect editor: list, show, apply a recipe (see README.md).
.EXAMPLE
    .\Edit-D2REffect.ps1 -Root 'D:\games\Diablo II Resurrected' show data/hd/vfx/particles/missiles/mephisto_missile/vfx_mephisto_missile.particles
.EXAMPLE
    .\Edit-D2REffect.ps1 -Root 'D:\games\Diablo II Resurrected' apply recipe.json -OutDir 'D:\mods\MyMod'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet('list', 'missiles', 'show', 'apply')][string]$Command,
    [Parameter(Position = 1)][string]$Target,
    [string]$Root = $env:D2R_PATH,
    [string]$OutDir,
    [switch]$Json,
    [switch]$Scripts
)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not (Test-Path $Root)) { throw 'Pass -Root (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'EffectEdit.py'), $Command)
if ($Target) { $arguments += $Target }
$arguments += @('--game', $Root)
if ($OutDir) { $arguments += @('--out', $OutDir) }
if ($Json) { $arguments += '--json' }
if ($Scripts) { $arguments += '--scripts' }
& $python @arguments
exit $LASTEXITCODE
