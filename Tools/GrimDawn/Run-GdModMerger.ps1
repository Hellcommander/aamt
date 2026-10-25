# Merge Grim Dawn mods into one Custom Game folder (merge rules + field-level merge).
param(
    [string]$Game = "",
    [Parameter(Mandatory = $true)]
    [string]$Out,
    [Parameter(Mandatory = $true)]
    [string[]]$Mods,
    [string]$Arzedit = "",
    [ValidateSet("none", "hubs", "rules", "all")]
    [string]$FieldMerge = "rules",
    [switch]$KeepOrder,
    [switch]$Latest,
    [switch]$Ollama,
    [switch]$SkipResources,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Tools "merge_mod_databases.py"

$argsList = @($Py, "--out", $Out, "--field-merge", $FieldMerge, "--mods") + $Mods
if ($Game) { $argsList += @("--game", $Game) }
if ($Arzedit) { $argsList += @("--arzedit", $Arzedit) }
if ($KeepOrder) { $argsList += "--keep-order" }
if ($Latest) { $argsList += "--latest" }
if ($Ollama) { $argsList += "--ollama" }
if ($SkipResources) { $argsList += "--skip-resources" }
if ($Rebuild) { $argsList += "--rebuild" }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
