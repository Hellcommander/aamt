# Bidirectional FoA / latest-patch compatibility for any Grim Dawn mod.
# -Latest = compat + all classes + class UI + combo names (add -Ollama for AI names).
param(
    [string]$Game = "",
    [Parameter(Mandatory = $true)]
    [string]$Mod,
    [string]$Out = "",
    [string]$Work = "",
    [string]$Arzedit = "",
    [string[]]$ClassMods = @(),
    [string]$OllamaModel = "",
    [switch]$FullCompat,
    [switch]$PassBOnly,
    [switch]$Latest,
    [switch]$Ollama,
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
if ($Latest -and -not $PassBOnly) { $argsList += "--latest" }
if ($Ollama -and -not $PassBOnly) { $argsList += "--ollama" }
if ($OllamaModel -and -not $PassBOnly) { $argsList += @("--ollama-model", $OllamaModel) }
if ($Rebuild -and -not $PassBOnly) { $argsList += "--rebuild" }
if ($ClassMods.Count -gt 0 -and -not $PassBOnly) { $argsList += @("--class-mods") + $ClassMods }

Write-Host "Running: python $($argsList -join ' ')"
& python @argsList
exit $LASTEXITCODE
