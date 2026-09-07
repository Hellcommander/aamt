<#
.SYNOPSIS
    Fixes Join-Path operations that might have null path errors.
    
.DESCRIPTION
    Adds validation before Join-Path operations with $ModPath or $OutputDir.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Common patterns to fix:
# 1. $outputDir = Join-Path $ModPath "assets"
# 2. OutputDir = (Join-Path $ModPath "assets")
# 3. Join-Path $ModPath "assets" used directly in parameters

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Join-Path Null Path Fixer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script identifies Join-Path operations that need validation." -ForegroundColor Yellow
Write-Host "Manual fixes may be required for complex cases." -ForegroundColor Yellow
Write-Host ""

# Get files that use Join-Path with ModPath or OutputDir
$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    $content -and (
        ($content -match 'Join-Path\s+\$ModPath') -or 
        ($content -match 'Join-Path\s+\$OutputDir')
    ) -and
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*" -and
    $_.Name -notlike "*BulkFixNullPaths*" -and
    $_.Name -notlike "*FixJoinPathOperations*"
}

Write-Host "Found $($psFiles.Count) scripts with Join-Path operations" -ForegroundColor Yellow
Write-Host ""

$filesNeedingFixes = @()

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $joinPathMatches = [regex]::Matches($content, 'Join-Path\s+(\$ModPath|\$OutputDir|\$[A-Za-z]+Path)\s+["'']([^"'']+)["'']')
    
    $needsFix = $false
    foreach ($match in $joinPathMatches) {
        $varName = $match.Groups[1].Value
        $pathPart = $match.Groups[2].Value
        
        # Check if there's validation before this Join-Path
        $beforeMatch = $content.Substring([Math]::Max(0, $match.Index - 200), [Math]::Min(400, $match.Index))
        if ($beforeMatch -notmatch "IsNullOrWhiteSpace.*$varName" -and $beforeMatch -notmatch "Validate.*$varName") {
            $needsFix = $true
            break
        }
    }
    
    if ($needsFix) {
        $filesNeedingFixes += $file.Name
        Write-Host "  [!] $($file.Name) - needs Join-Path validation" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Files needing Join-Path fixes: $($filesNeedingFixes.Count)" -ForegroundColor $(if ($filesNeedingFixes.Count -gt 0) { "Yellow" } else { "Green" })

if ($filesNeedingFixes.Count -gt 0) {
    Write-Host ""
    Write-Host "Recommended pattern for fixes:" -ForegroundColor Cyan
    Write-Host '  $outputDir = Join-Path $ModPath "assets"' -ForegroundColor Gray
    Write-Host '  if ([string]::IsNullOrWhiteSpace($outputDir)) {' -ForegroundColor Gray
    Write-Host '      Write-Host "  [FAIL] OutputDir is null" -ForegroundColor Red' -ForegroundColor Gray
    Write-Host '      continue  # or exit 1' -ForegroundColor Gray
    Write-Host '  }' -ForegroundColor Gray
}

Write-Host ""
