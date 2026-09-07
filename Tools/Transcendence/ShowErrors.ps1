# Script to show detailed error information

param(
    [string]$ModPath = "..\ZZZ_CrossModCompatibility"
)

Write-Host "Transcendence Mod Tools - Error Details" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Load scanner functions (avoid dot-sourcing the full GUI tool)
$issuesModule = Join-Path $PSScriptRoot "GetXmlIssues.ps1"
if (-not (Test-Path $issuesModule)) {
    Write-Host "ERROR: GetXmlIssues.ps1 not found at: $issuesModule" -ForegroundColor Red
    exit 1
}
. $issuesModule

# Resolve mod path
$modPath = Resolve-Path $ModPath -ErrorAction SilentlyContinue
if (-not $modPath) {
    Write-Host "ERROR: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

Write-Host "Mod Path: $modPath" -ForegroundColor Yellow
Write-Host ""

# Get all XML files
$files = Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName }
Write-Host "Found $($files.Count) XML files" -ForegroundColor Green
Write-Host ""

# Scan for issues
Write-Host "Scanning for issues..." -ForegroundColor Cyan
$allIssues = @()
foreach ($file in $files) {
    try {
        $issues = Get-XmlIssues -FilePath $file
        if ($issues.Count -gt 0) {
            $allIssues += $issues
        }
    }
    catch {
        Write-Host "  Warning: Failed to scan $file" -ForegroundColor Yellow
        Write-Host "    Error: $_" -ForegroundColor Red
    }
}

Write-Host "Total issues found: $($allIssues.Count)" -ForegroundColor Yellow
Write-Host ""

# Show XML_WELLFORMED_ERROR details
$wellformed = $allIssues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' }
if ($wellformed.Count -gt 0) {
    Write-Host "XML Well-Formedness Errors ($($wellformed.Count)):" -ForegroundColor Red
    Write-Host ""
    
    $wellformed | ForEach-Object {
        $fileName = Split-Path -Leaf $_.File
        Write-Host "  File: $fileName" -ForegroundColor Yellow
        Write-Host "    Line: $($_.Line)" -ForegroundColor Gray
        Write-Host "    Message: $($_.Message)" -ForegroundColor White
        Write-Host ""
    }
}
else {
    Write-Host "No XML well-formedness errors found." -ForegroundColor Green
}

# Show all error types
Write-Host "All Error Types:" -ForegroundColor Cyan
$byType = $allIssues | Group-Object Code
foreach ($group in $byType) {
    Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor Gray
}

