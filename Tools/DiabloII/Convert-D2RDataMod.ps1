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
.EXAMPLE
    # from where the mod is (a <Name>.mpq folder, a mod folder, .zip/.7z/.rar or packed .mpq): copied into
    # <D2RMM>\mods\<Mod>, converted and checked, and the source remembered, so
    # Update-D2RConvertedMod.ps1 -Mod Reimagined redoes it when the mod there is updated
    .\Convert-D2RDataMod.ps1 -Source 'D:\games\Steam\steamapps\common\Diablo II Resurrected\Reimagined.mpq' -Mod Reimagined
#>
[CmdletBinding()]
param(
    [string]$Mod,
    # where the mod comes from; remembered in d2rmm\convert.json for Update-D2RConvertedMod.ps1
    [string]$Source,
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
    # D2RMM's folder (default: the one -Mod sits in, <D2RMM>\mods\<mod>)
    [string]$D2RMM,
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
$GamePath = Resolve-D2RGamePath $GamePath
$python = Resolve-D2RPython

if ($Source) {
    # the converter window's Convert, without the window (always checked)
    $D2RMM = Resolve-D2RMMPath $D2RMM $GamePath
    $arguments = @((Join-Path $PSScriptRoot 'ModConverter.py'), '--game', $GamePath, '--d2rmm', $D2RMM, '--convert', $Source,
                   '--rows', $Rows, '--conflicts', $Conflicts, '--files', $Files)
    if ($Mod) { $arguments += @('--id', (Split-Path $Mod -Leaf)) }
    if ($Author) { $arguments += @('--author', $Author) }
    if ($Name) { $arguments += @('--name', $Name) }
    if ($Version) { $arguments += @('--version', $Version) }
    & $python @arguments
    exit $LASTEXITCODE
}
if (-not $Mod) { throw 'Pass -Mod (the mod folder in D2RMM), or -Source (where the mod is).' }

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
if ($D2RMM) { $arguments += @('--d2rmm', $D2RMM) }
$arguments += @('--rows', $Rows, '--conflicts', $Conflicts, '--files', $Files)
if ($Check) { $arguments += '--check' }
& $python @arguments
exit $LASTEXITCODE
