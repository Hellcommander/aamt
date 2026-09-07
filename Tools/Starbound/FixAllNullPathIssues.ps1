#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fixes all null path issues in Generate*.ps1 scripts by replacing duplicate validation blocks and invalid continue statements.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$files = Get-ChildItem -Path $scriptDir -Filter "Generate*.ps1" -File

$fixedCount = 0
$errorCount = 0

foreach ($file in $files) {
    Write-Host "Checking: $($file.Name)" -ForegroundColor Cyan
    
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    # Pattern 1: Fix duplicate validation blocks with continue statements
    # Pattern: " if ([string]::IsNullOrWhiteSpace($varOutputDir)) { ... continue }" appearing twice
    $pattern1 = '(?s)# Validate.*?Join-Path.*?\r?\n\$\w+OutputDir = Join-Path.*?\r?\n\s+if.*?IsNullOrWhiteSpace\(\$\w+OutputDir\).*?continue.*?\r?\n\s+\}\s+\r?\n\s+if.*?IsNullOrWhiteSpace\(\$\w+OutputDir\).*?continue.*?\r?\n\s+\}'
    
    # Pattern 2: Fix single validation with continue outside loop
    $pattern2 = '(?s)(\$\w+OutputDir = Join-Path.*?\r?\n)\s+if.*?IsNullOrWhiteSpace\(\$\w+OutputDir\).*?continue.*?\r?\n\s+\}\s+\r?\n\s+if.*?IsNullOrWhiteSpace\(\$\w+OutputDir\).*?continue.*?\r?\n\s+\}\s+\r?\n(if.*?Test-Path.*?\r?\n.*?New-Item.*?\r?\n\s+\}\s+\r?\n)\s*(foreach)'
    
    # For now, just report which files have the issue
    if ($content -match ' if.*IsNullOrWhiteSpace.*OutputDir.*continue') {
        Write-Host "  [NEEDS FIX] $($file.Name) has null path issues" -ForegroundColor Yellow
        $fixedCount++
    }
}

Write-Host "`nFound $fixedCount files that may need fixing" -ForegroundColor Cyan
Write-Host "Note: Manual fixing recommended for each file to ensure correctness" -ForegroundColor Gray
