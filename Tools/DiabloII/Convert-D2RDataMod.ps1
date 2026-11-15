<#
.SYNOPSIS
    Turns a D2R data mod (an .mpq folder, or a packed .mpq archive) into a D2RMM mod that patches
    tables and strings instead of replacing whole files (see README.md, "Data mod to D2RMM mod").
.EXAMPLE
    # a data mod already in D2RMM's mods folder (<mod>\<Name>.mpq\data or <mod>\data)
    .\Convert-D2RDataMod.ps1 -GamePath 'D:\games\Steam\steamapps\common\Diablo II Resurrected' -Mod '<D2RMM>\mods\Reimagined' -Author ScottieKnowz -Check
.EXAMPLE
    # a packed archive (D2RLoader package): extracted into -Mod first, with the d2rloader folder next to it
    .\Convert-D2RDataMod.ps1 -Archive '<download>\FMMP-Experimental-R67\FMMP-Experimental-R67.mpq' -Mod '<D2RMM>\mods\FrankensteinMod' -Author ALvl4Ninja -Check
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Mod,
    [string]$GamePath = $env:D2R_PATH,
    [string]$Archive,
    [string]$Author,
    [string]$Name,
    [string]$Version,
    [string]$Cache,
    [ValidateSet('keep', 'rebuild')][string]$Rows = 'keep',
    # defaults of the converted mod's Load order settings in D2RMM
    [ValidateSet('mod', 'earlier')][string]$Conflicts = 'mod',
    [ValidateSet('overwrite', 'keep')][string]$Files = 'overwrite',
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
if (-not $GamePath -or -not (Test-Path $GamePath)) { throw 'Pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

if ($Archive) {
    if (-not (Test-Path $Archive -PathType Leaf)) { throw "-Archive must be an .mpq file: $Archive" }
    $packed = Join-Path $Mod ((Split-Path $Archive -LeafBase) + '.mpq')
    if (Test-Path $packed) { throw "$packed already exists; remove it to extract again." }
    & $python (Join-Path $PSScriptRoot 'MpqArchive.py') extract $Archive $Mod
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $loader = Join-Path (Split-Path $Archive -Parent) 'd2rloader'
    if ((Test-Path $loader) -and -not (Test-Path (Join-Path $Mod 'd2rloader'))) {
        Copy-Item $loader (Join-Path $Mod 'd2rloader') -Recurse
    }
}

$arguments = @((Join-Path $PSScriptRoot 'ConvertDataMod.py'), '--game', $GamePath, '--mod', $Mod, '--python', $python)
if ($Author) { $arguments += @('--author', $Author) }
if ($Name) { $arguments += @('--name', $Name) }
if ($Version) { $arguments += @('--version', $Version) }
if ($Cache) { $arguments += @('--cache', $Cache) }
$arguments += @('--rows', $Rows, '--conflicts', $Conflicts, '--files', $Files)
if ($Check) { $arguments += '--check' }
& $python @arguments
exit $LASTEXITCODE
