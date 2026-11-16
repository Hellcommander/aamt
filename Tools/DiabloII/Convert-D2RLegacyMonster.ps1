<#
.SYNOPSIS
    Gives an original-graphics (sprite) monster an HD version built from the closest HD monster (see README.md).
.EXAMPLE
    .\Convert-D2RLegacyMonster.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Token sk -Donors
.EXAMPLE
    .\Convert-D2RLegacyMonster.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -DataDir '<mod>\data' -Token zz -Name my_monster -OutDir '<D2RMM>\mods\MyMod'
.EXAMPLE
    .\Convert-D2RLegacyMonster.ps1 -Name my_monster -OutDir '<D2RMM>\mods\MyMod' -Encode
#>
[CmdletBinding()]
param(
    [string]$GamePath = $env:D2R_PATH,
    [string]$DataDir,
    [string]$Token,
    [string]$Name,
    [string]$OutDir,
    [string]$Donor,
    [double]$Scale,
    [string]$CascLib = $env:D2R_CASCLIB,
    [switch]$Strip,
    [switch]$Donors,
    [switch]$Measure,
    [switch]$Encode
)
$ErrorActionPreference = 'Stop'

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$command = if ($Encode) { 'encode' } elseif ($Donors) { 'donors' } elseif ($Measure) { 'measure' } else { 'build' }
$arguments = @((Join-Path $PSScriptRoot 'LegacyToHd.py'), $command)
if ($command -ne 'encode') {
    if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }
    if (-not $Token) { throw 'Pass -Token (the monster''s legacy animation token, monstats Code).' }
    $arguments += @('--game', $GamePath, '--token', $Token)
    if ($DataDir) { $arguments += @('--data', $DataDir) }
    if ($CascLib) { $arguments += @('--casclib', $CascLib) }
}
if ($Name) { $arguments += @('--name', $Name) }
if ($OutDir) { $arguments += @('--out', $OutDir) }
if ($Donor) { $arguments += @('--donor', $Donor) }
if ($Scale) { $arguments += @('--scale', $Scale) }
if ($Strip) { $arguments += '--strip' }
& $python @arguments
exit $LASTEXITCODE
