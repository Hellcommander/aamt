# Simple mod scanner
param([string]$ModPath)

. .\GetXmlIssues.ps1

$extensionsDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not ([System.IO.Path]::IsPathRooted($ModPath))) {
    # Handle relative paths like ..\ModName
    if ($ModPath.StartsWith('..\')) {
        $modName = $ModPath.Substring(3)
        $fullPath = Join-Path $extensionsDir $modName
    }
    else {
        $fullPath = Join-Path $extensionsDir $ModPath
    }
    $fullPath = [System.IO.Path]::GetFullPath($fullPath)
}
else {
    $fullPath = $ModPath
}

if (-not (Test-Path $fullPath)) {
    Write-Host "ERROR: Path does not exist: $fullPath" -ForegroundColor Red
    exit 1
}

$resolvedPath = $fullPath

Write-Host "Scanning: $resolvedPath" -ForegroundColor Yellow

$files = @()
$tdbFiles = @()
if (Test-Path $resolvedPath -PathType Leaf) {
    if ($resolvedPath.EndsWith('.xml')) { 
        $files = @($resolvedPath) 
    }
    elseif ($resolvedPath -match '\.(tdb|TDB)$') {
        $tdbFiles = @($resolvedPath)
    }
}
else {
    $files = @(Get-ChildItem -LiteralPath $resolvedPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
    # Get TDB files (case-insensitive, remove duplicates)
    $tdbFiles = @(Get-ChildItem -LiteralPath $resolvedPath -Include '*.tdb','*.TDB' -Recurse | 
        Select-Object -Unique -Property FullName | ForEach-Object { $_.FullName })
}

# For TDB files, check if corresponding XML source exists
$tdbWarnings = @()
foreach ($tdb in $tdbFiles) {
    $tdbName = [System.IO.Path]::GetFileNameWithoutExtension($tdb)
    $tdbDir = [System.IO.Path]::GetDirectoryName($tdb)
    
    # Check for XML source files in same directory or _Source subdirectory
    $xmlSource = @(
        (Join-Path $tdbDir "$tdbName.xml"),
        (Join-Path $tdbDir "_Source\$tdbName.xml"),
        (Join-Path $tdbDir "${tdbName}_Source\$tdbName.xml")
    ) | Where-Object { Test-Path $_ }
    
    if ($xmlSource.Count -gt 0) {
        # Found XML source, scan it instead
        Write-Host "TDB file detected: $(Split-Path -Leaf $tdb)" -ForegroundColor Cyan
        Write-Host "  Using XML source: $(Split-Path -Leaf $xmlSource[0])" -ForegroundColor Green
        $files += $xmlSource[0]
    }
    else {
        # No XML source found
        $tdbWarnings += "TDB file cannot be scanned (no XML source found): $(Split-Path -Leaf $tdb)"
    }
}

if ($files.Count -eq 0 -and $tdbWarnings.Count -eq 0) {
    Write-Host 'No XML files found' -ForegroundColor Red
    exit 1
}

if ($tdbWarnings.Count -gt 0) {
    Write-Host ''
    Write-Host 'TDB Files (cannot scan without XML source):' -ForegroundColor Yellow
    foreach ($warning in $tdbWarnings) {
        Write-Host "  $warning" -ForegroundColor Yellow
    }
    Write-Host ''
}

if ($files.Count -gt 0) {
    Write-Host "Found $($files.Count) XML file(s)" -ForegroundColor Green
    Write-Host ''
}

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

# Show summary
$byType = $allIssues | Group-Object Code
Write-Host ''
Write-Host 'Issues by Type:' -ForegroundColor Cyan
foreach ($group in $byType) {
    Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor White
}

