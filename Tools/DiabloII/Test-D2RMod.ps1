<#
.SYNOPSIS
    Runs D2RMM mod scripts without the game and checks what they produce (see README.md, "Mod test pipeline").
    Game files are taken from the archive as the mods ask for them and cached.
.EXAMPLE
    .\Test-D2RMod.ps1 -GamePath 'D:\games\Diablo II Resurrected' -Mod '<D2RMM>\mods\DruidPoisonDisaster'
.EXAMPLE
    # several mods together, in load order (page number clashes between mods show up this way)
    .\Test-D2RMod.ps1 -Mod '<D2RMM>\mods\QuillRatDruid','<D2RMM>\mods\DruidPoisonDisaster' -Config 'testMode=false' -Manifest .\needed_files.json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Mod,
    [string]$GamePath = $env:D2R_PATH,
    [string[]]$Config = @(),
    [string]$Cache,
    [string]$Manifest,
    [int]$MaxPage = 15,
    [switch]$Refresh,
    [switch]$Dump,
    [switch]$DumpBase
)
$ErrorActionPreference = 'Stop'
if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'ModHarness.js'), '--game', $GamePath, '--python', $python, '--max-page', $MaxPage)
if ($Cache) { $arguments += @('--cache', $Cache) }
if ($Manifest) { $arguments += @('--manifest', $Manifest) }
if ($Refresh) { $arguments += '--refresh' }
if ($DumpBase) { $arguments += @('--dump', 'base') } elseif ($Dump) { $arguments += '--dump' }
foreach ($c in $Config) { $arguments += @('--config', $c) }
$arguments += $Mod
& node @arguments
exit $LASTEXITCODE
