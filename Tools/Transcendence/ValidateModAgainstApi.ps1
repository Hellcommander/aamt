<#
.SYNOPSIS
  Validate a mod against the API rules
  
.DESCRIPTION
  Checks a mod for deprecated tags, functions, and unknown API usage.
  
.EXAMPLE
  .\ValidateModAgainstApi.ps1 -ModPath "..\1237_UpgradedWingmen"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath
)

# Load the API rules module
$apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
if (Test-Path $apiRulesModule) {
    . $apiRulesModule
}
else {
    Write-Host "ERROR: API Rules module not found: $apiRulesModule" -ForegroundColor Red
    exit 1
}

# Resolve path
$resolvedPath = Resolve-Path $ModPath -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
    Write-Host "ERROR: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

Write-Host "Validating mod against API rules..." -ForegroundColor Cyan
Write-Host "Mod: $resolvedPath" -ForegroundColor Yellow
Write-Host ""

# Validate
$issues = Test-ModAgainstApiRules -ModPath $resolvedPath.Path

if ($issues.Count -eq 0) {
    Write-Host "No API issues found!" -ForegroundColor Green
}
else {
    Write-Host "Found $($issues.Count) API issue(s):" -ForegroundColor Yellow
    Write-Host ""
    
    # Group by type
    $byType = $issues | Group-Object Type
    
    foreach ($group in $byType) {
        Write-Host "$($group.Name) ($($group.Count)):" -ForegroundColor Cyan
        foreach ($issue in $group.Group | Select-Object -First 10) {
            $color = switch ($issue.Severity) {
                'Error' { 'Red' }
                'Warning' { 'Yellow' }
                default { 'Gray' }
            }
            Write-Host "  [$($issue.Severity)] $($issue.File): $($issue.Message)" -ForegroundColor $color
        }
        if ($group.Count -gt 10) {
            Write-Host "  ... and $($group.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
}

