# Bidirectional FoA / v1.3 compatibility for any Grim Dawn mod.
param(
    [string]$Game = "",
    [Parameter(Mandatory = $true)]
    [string]$Mod,
    [string]$Out = "",
    [string]$Work = "",
    [string]$Arzedit = "",
    [switch]$FullCompat,
    [switch]$PassBOnly,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($PassBOnly) {
    $Py = Join-Path $Tools "patch_dlc_for_mod.py"
} else {
    $Py = Join-Path $Tools "patch_mod_for_dlc.py"
}

$argsList = @($Py, "--mod", $Mod)
if ($Game) { $argsList += @("--game", $Game) }
if ($Work) { $argsList += @("--work", $Work) }
if ($Out -and -not $PassBOnly) { $argsList += @("--out", $Out) }
if ($Arzedit) { $argsList += @("--arzedit", $Arzedit) }
if ($FullCompat -and -not $PassBOnly) { $argsList += "--full-compat" }
if ($Rebuild -and -not $PassBOnly) { $argsList += "--rebuild" }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
