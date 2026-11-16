<#
.SYNOPSIS
    Keeps the D2RLoader plugin sources (<game>\mods\<plugin>\plugin) in step with D2RLoader: the
    plugin SDK they build against, and the game addresses they hook (see README.md, "Updating the
    plugins for a new D2RLoader").
.DESCRIPTION
    Without a switch it only reports: SDK installed / upstream / whether the upstream headers fit the
    newest published loader, and whether every hooked address is still where the plugins expect it.
.EXAMPLE
    .\Update-D2RPlugins.ps1 -Root 'D:\games\Steam\steamapps\common\Diablo II Resurrected'
.EXAMPLE
    # after a new loader is out: what changes, a trial build, then the swap and rebuild
    .\Update-D2RPlugins.ps1 -SdkDiff
    .\Update-D2RPlugins.ps1 -SdkTrial
    .\Update-D2RPlugins.ps1 -SdkApply
.EXAMPLE
    # after a new dump (SkillTab4 Probe run once): put moved addresses into the plugin sources
    .\Update-D2RPlugins.ps1 -FixAddresses
#>
[CmdletBinding()]
param(
    [string]$Root = $env:D2R_PATH,
    [string]$Ref = 'master',
    [switch]$SdkDiff,
    [switch]$SdkTrial,
    [switch]$SdkApply,
    [switch]$Force,
    [switch]$SdkRestore,
    [string]$To,
    [switch]$Rebuild,
    [switch]$FixAddresses,
    [switch]$SelfTest,
    [string]$OldImage,
    [string]$NewImage
)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not (Test-Path (Join-Path $Root 'mods'))) { throw 'Pass -Root (or set D2R_PATH) to the game folder (it holds D2R.exe and mods\).' }
$mods = Join-Path $Root 'mods'

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}
$sdk = Join-Path $PSScriptRoot 'PluginSdk.py'
$addr = Join-Path $PSScriptRoot 'PluginAddresses.py'
$images = @()
if ($OldImage) { $images += @('--old', $OldImage) }
if ($NewImage) { $images += @('--new', $NewImage) }

function Invoke-Py([string[]]$arguments) {
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($SdkDiff) { Invoke-Py @($sdk, 'diff', '--mods', $mods, '--ref', $Ref); exit 0 }
if ($SdkTrial) { Invoke-Py @($sdk, 'trial', '--mods', $mods, '--ref', $Ref); exit 0 }
if ($SdkApply) {
    $a = @($sdk, 'apply', '--mods', $mods, '--ref', $Ref)
    if ($Force) { $a += '--force' }
    Invoke-Py $a; exit 0
}
if ($SdkRestore) {
    $a = @($sdk, 'restore', '--mods', $mods)
    if ($To) { $a += @('--to', $To) }
    Invoke-Py $a; exit 0
}
if ($Rebuild) { Invoke-Py @($sdk, 'rebuild', '--mods', $mods); exit 0 }
if ($SelfTest) { Invoke-Py (@($addr, 'selftest', '--mods', $mods) + $images); exit 0 }
if ($FixAddresses) { Invoke-Py (@($addr, 'check', '--mods', $mods, '--write') + $images); exit 0 }

# report only
& $python $sdk status --mods $mods --ref $Ref
Write-Host ''
& $python $addr check --mods $mods @images
exit $LASTEXITCODE
