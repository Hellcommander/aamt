# Merge Grim Dawn mods (later wins) into one Custom Game folder.
param(
    [string]$Game = "",
    [Parameter(Mandatory = $true)]
    [string]$Out,
    [Parameter(Mandatory = $true)]
    [string[]]$Mods,
    [string]$Arzedit = "",
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Tools "merge_mod_databases.py"

$argsList = @($Py, "--out", $Out, "--mods") + $Mods
if ($Game) { $argsList += @("--game", $Game) }
if ($Arzedit) { $argsList += @("--arzedit", $Arzedit) }
if ($Rebuild) { $argsList += "--rebuild" }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
