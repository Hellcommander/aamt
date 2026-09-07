# Survival Mode power-level playground:
# full DLC classes + mod class lines + items/content from other mods.
param(
    [string]$Game = "",
    [string]$Mod = "survivalmode",
    [string]$Out = "SurvivalPlayground",
    [string]$Profile = "",
    [string[]]$ClassMods = @(),
    [string[]]$ContentMods = @(),
    [string[]]$PortalMods = @(),
    [string[]]$Mods = @(),
    [string]$Work = "",
    [string]$VanillaCache = "",
    [string]$Arzedit = "",
    [string]$OllamaModel = "",
    [switch]$IncludeSounds,
    [switch]$SkipResources,
    [switch]$DryRunNames,
    [switch]$SkipNames,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Tools "patch_survival_classes.py"

$argsList = @("-u", $Py)
# Default: use survivalmode.json profile when no explicit mod lists
if (-not $Profile -and $ClassMods.Count -eq 0 -and $ContentMods.Count -eq 0 -and $Mods.Count -eq 0 -and $PortalMods.Count -eq 0) {
    $Profile = "survivalmode.json"
}
if ($Profile) { $argsList += @("--profile", $Profile) }
else {
    $argsList += @("--mod", $Mod, "--out", $Out)
}
if ($Game) { $argsList += @("--game", $Game) }
if ($Work) { $argsList += @("--work", $Work) }
if ($VanillaCache) { $argsList += @("--vanilla-cache", $VanillaCache) }
if ($Arzedit) { $argsList += @("--arzedit", $Arzedit) }
if ($OllamaModel) { $argsList += @("--ollama-model", $OllamaModel) }
if ($ClassMods.Count -gt 0) { $argsList += @("--class-mods") + $ClassMods }
if ($ContentMods.Count -gt 0) { $argsList += @("--content-mods") + $ContentMods }
if ($PortalMods.Count -gt 0) { $argsList += @("--portal-mods") + $PortalMods }
if ($Mods.Count -gt 0) { $argsList += @("--mods") + $Mods }
if ($IncludeSounds) { $argsList += "--include-sounds" }
if ($SkipResources) { $argsList += "--skip-resources" }
if ($DryRunNames) { $argsList += "--dry-run-names" }
if ($SkipNames) { $argsList += "--skip-names" }
if ($Rebuild) { $argsList += "--rebuild" }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
