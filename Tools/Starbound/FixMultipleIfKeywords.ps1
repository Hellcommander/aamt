<#
.SYNOPSIS
    Fixes multiple "if" keywords introduced by the auto-fix scripts.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0

Write-Host "Fixing multiple 'if' keywords..." -ForegroundColor Cyan

# Find all files with multiple "if" keywords
$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    $content -and $content -match 'if\s+if\s+if'
}

Write-Host "Found $($psFiles.Count) files with multiple 'if' keywords" -ForegroundColor Yellow

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    # Fix: "if if if" or "if if if if" -> "if" (any number of repeated "if")
    $content = $content -replace '(if\s+)+if\s*\(', 'if ('
    
    # Fix: " if if if" (with leading space) -> " if"
    $content = $content -replace '(\s+)(if\s+)+if\s*\(', '$1if ('
    
    # Fix malformed lines like "# Validate $ModPath before Join-Path`n$outputBase"
    $content = $content -replace '# Validate \$ModPath before Join-Path`n\$', '# Validate $ModPath before Join-Path`n$'
    
    # Fix duplicate validation blocks - remove duplicates
    $lines = $content -split "`r?`n"
    $newLines = @()
    $lastValidation = ""
    
    foreach ($line in $lines) {
        # Skip duplicate validation comments
        if ($line -match '# Validate.*before Join-Path') {
            if ($line -eq $lastValidation) {
                continue  # Skip duplicate
            }
            $lastValidation = $line
        } else {
            $lastValidation = ""
        }
        
        # Fix malformed assignments like " = $tempOutputDir" (missing variable name)
        if ($line -match '^\s+=\s+\$tempOutputDir') {
            $line = $line -replace '^\s+=\s+', '            OutputDir = '
        }
        
        # Fix lines that have validation before assignment on same line
        if ($line -match '# Validate.*`n\$([A-Za-z]+)\s*=') {
            $varName = $matches[1]
            $indent = $line -replace '^(\s*).*$', '$1'
            $newLines += "$indent# Validate `$ModPath before Join-Path"
            $line = $line -replace '.*`n', ''
            $line = $line -replace '^\s+', "$indent"
        }
        
        $newLines += $line
    }
    
    $content = $newLines -join "`n"
    
    if ($content -ne $originalContent) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        $filesFixed++
        Write-Host "  [FIXED] $($file.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Fixed $filesFixed files" -ForegroundColor Green
