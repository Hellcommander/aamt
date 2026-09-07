<#
.SYNOPSIS
    Removes duplicate validation blocks and fixes indentation issues.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0

Write-Host "Cleaning up duplicate validations and indentation..." -ForegroundColor Cyan

$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*" -and
    $_.Name -notlike "*BulkFixNullPaths*" -and
    $_.Name -notlike "*FixJoinPathOperations*" -and
    $_.Name -notlike "*AutoFixJoinPath*" -and
    $_.Name -notlike "*FixSyntaxErrors*" -and
    $_.Name -notlike "*FixMultipleIfKeywords*" -and
    $_.Name -notlike "*CleanupDuplicateValidations*"
}

Write-Host "Processing $($psFiles.Count) files..." -ForegroundColor Yellow

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    # Fix lines that start with space before "if ("
    $content = $content -replace '^(\s+) if\s*\(', '$1if ('
    
    # Remove duplicate validation blocks (same validation twice in a row)
    $lines = $content -split "`r?`n"
    $newLines = @()
    $skipNext = $false
    
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        
        # Check if this is a duplicate validation block
        if ($i -gt 0 -and $line -match '^\s+if\s+\(\[string\]::IsNullOrWhiteSpace') {
            $prevLine = $lines[$i - 1]
            if ($prevLine -match '^\s+if\s+\(\[string\]::IsNullOrWhiteSpace') {
                # Check if they're checking the same variable
                $thisVar = if ($line -match '\$([A-Za-z_][A-Za-z0-9_]*)') { $matches[1] } else { "" }
                $prevVar = if ($prevLine -match '\$([A-Za-z_][A-Za-z0-9_]*)') { $matches[1] } else { "" }
                
                if ($thisVar -eq $prevVar -and $thisVar -ne "") {
                    # Skip this duplicate
                    # Also skip the next few lines (the Write-Host and continue/exit)
                    $skipCount = 0
                    for ($j = $i + 1; $j -lt $lines.Count -and $skipCount -lt 3; $j++) {
                        if ($lines[$j] -match '^\s+(Write-Host|continue|exit)') {
                            $skipCount++
                        } else {
                            break
                        }
                    }
                    $i += $skipCount
                    continue
                }
            }
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
