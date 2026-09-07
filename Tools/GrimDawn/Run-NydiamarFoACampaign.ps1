# Nydiamar + FoA unified Custom Game pipeline (quest remap + Editor checklist).
param(
    [string]$Game = "",
    [string]$Source = "",
    [string]$Out = "",
    [string]$Profile = "",
    [string]$Work = "",
    [string]$Arzedit = "",
    [string]$OllamaModel = "",
    [ValidateSet("", "devils_crossing", "homestead", "fort_ikon", "malmouth", "asterkarn")]
    [string]$PortalHub = "",
    [switch]$NoDungeons,
    [switch]$NoCompat,
    [switch]$DryRunNames,
    [switch]$SkipNames,
    [switch]$SkipQuestRemap,
    [switch]$SkipEditorStitch,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Tools "nydiamar_campaign.py"

$argsList = @($Py)
if ($Game) { $argsList += @("--game", $Game) }
if ($Source) { $argsList += @("--source", $Source) }
if ($Out) { $argsList += @("--out", $Out) }
if ($Profile) { $argsList += @("--profile", $Profile) }
if ($Work) { $argsList += @("--work", $Work) }
if ($Arzedit) { $argsList += @("--arzedit", $Arzedit) }
if ($OllamaModel) { $argsList += @("--ollama-model", $OllamaModel) }
if ($PortalHub) { $argsList += @("--portal-hub", $PortalHub) }
if ($NoDungeons) { $argsList += "--no-dungeons" }
if ($NoCompat) { $argsList += "--no-compat" }
if ($DryRunNames) { $argsList += "--dry-run-names" }
if ($SkipNames) { $argsList += "--skip-names" }
if ($SkipQuestRemap) { $argsList += "--skip-quest-remap" }
if ($SkipEditorStitch) { $argsList += "--skip-editor-stitch" }
if ($Rebuild) { $argsList += "--rebuild" }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
