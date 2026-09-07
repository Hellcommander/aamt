<#
.SYNOPSIS
  Auto-update a mod to new API version
  
.DESCRIPTION
  Automatically updates a mod to match the current API version by:
  - Updating apiVersion attributes
  - Replacing deprecated functions
  - Generating report of manual fixes needed
  
.EXAMPLE
  .\UpdateModToApi.ps1 -ModPath "..\1237_UpgradedWingmen"
  .\UpdateModToApi.ps1 -ModPath "..\MyMod" -TargetApiVersion 59 -DryRun
  .\UpdateModToApi.ps1 -AllMods
#>

param(
    [string]$ModPath = $null,
    
    [int]$TargetApiVersion = 0,  # 0 = auto-detect from source
    
    [switch]$AllMods,
    [switch]$DryRun,
    [switch]$Backup
)

# Load the auto-update module
$updateModule = Join-Path $PSScriptRoot 'TranscendenceModTools_AutoUpdate.ps1'
if (Test-Path $updateModule) {
    . $updateModule
}
else {
    Write-Host "ERROR: Auto-Update module not found: $updateModule" -ForegroundColor Red
    exit 1
}

# Load API rules module
$apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
if (Test-Path $apiRulesModule) {
    . $apiRulesModule
}

# Determine target API version
if ($TargetApiVersion -eq 0) {
    $TargetApiVersion = $script:DefaultApiVersion
    Write-Host "Using auto-detected API version: $TargetApiVersion" -ForegroundColor Cyan
    Write-Host ""
}

if ($AllMods) {
    Update-AllModsToApiVersion -TargetApiVersion $TargetApiVersion -DryRun:$DryRun
}
elseif ($ModPath) {
    Update-ModToApiVersion -ModPath $ModPath -TargetApiVersion $TargetApiVersion -DryRun:$DryRun -Backup:$Backup
}
else {
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  .\UpdateModToApi.ps1 -ModPath `"..\YourMod`"" -ForegroundColor White
    Write-Host "  .\UpdateModToApi.ps1 -AllMods" -ForegroundColor White
    Write-Host "  .\UpdateModToApi.ps1 -ModPath `"..\YourMod`" -DryRun" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -ModPath          Path to mod folder" -ForegroundColor White
    Write-Host "  -AllMods          Update all mods in Extensions folder" -ForegroundColor White
    Write-Host "  -TargetApiVersion Target API version (default: auto-detect)" -ForegroundColor White
    Write-Host "  -DryRun           Show what would change without making changes" -ForegroundColor White
    Write-Host "  -Backup           Create backup before updating" -ForegroundColor White
}

