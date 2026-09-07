# Quick scan script to test and get results
param([string]$ModPath)

if (-not $ModPath) {
    Write-Host "Usage: .\QuickScan.ps1 -ModPath 'path\to\mod'"
    exit 1
}

# Load the main script functions
. .\TranscendenceModTools.ps1 -NoGui

# Resolve path
$extensionsDir = Join-Path $PSScriptRoot '..'
if (-not ([System.IO.Path]::IsPathRooted($ModPath))) {
    $fullPath = Join-Path $extensionsDir $ModPath
}
else {
    $fullPath = $ModPath
}

try {
    $resolvedPath = (Resolve-Path $fullPath -ErrorAction Stop).Path
}
catch {
    Write-Host "ERROR: Cannot resolve path: $ModPath" -ForegroundColor Red
    exit 1
}

Write-Host "Scanning: $resolvedPath" -ForegroundColor Yellow

# Get files
$files = @()
if (Test-Path $resolvedPath -PathType Leaf) {
    if ($resolvedPath.EndsWith('.xml')) { 
        $files = @($resolvedPath) 
    }
}
else {
    $files = @(Get-ChildItem -LiteralPath $resolvedPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
}

if ($files.Count -eq 0) {
    Write-Host 'No XML files found' -ForegroundColor Red
    exit 1
}

Write-Host "Found $($files.Count) XML file(s)" -ForegroundColor Green

# Scan files
$allIssues = @()
foreach ($f in $files) {
    $fileName = Split-Path -Leaf $f
    Write-Host "Scanning: $fileName" -NoNewline
    
    try {
        $fileIssues = Get-XmlIssues -FilePath $f
        if ($fileIssues.Count -gt 0) {
            Write-Host " - Found $($fileIssues.Count) issue(s)" -ForegroundColor Yellow
            $allIssues += $fileIssues
        }
        else {
            Write-Host " - OK" -ForegroundColor Green
        }
    }
    catch {
        Write-Host " - ERROR: $_" -ForegroundColor Red
    }
}

Write-Host ''
Write-Host "Total Issues: $($allIssues.Count)" -ForegroundColor Cyan

# Save results
$logFile = Join-Path $PSScriptRoot "scan_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$logContent = "Scan Results`n============`nPath: $resolvedPath`nFiles: $($files.Count)`nIssues: $($allIssues.Count)`n`n"

foreach ($issue in $allIssues) {
    $fileName = Split-Path -Leaf $issue.File
    $logContent += "[$($issue.Severity)] $fileName (Line $($issue.Line)): $($issue.Code) - $($issue.Message)`n"
}

[System.IO.File]::WriteAllText($logFile, $logContent, [System.Text.Encoding]::UTF8)
Write-Host "Results saved to: $logFile" -ForegroundColor Green

