<#
.SYNOPSIS
    Fixes variable reference errors in Write-Host statements.
    
.DESCRIPTION
    Fixes patterns like "$ModPath: '$ModPath'" which cause parser errors.
    Changes them to use ${ModPath} to delimit the variable name.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0

Write-Host "Fixing variable reference errors in Write-Host statements..." -ForegroundColor Cyan

$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*" -and
    $_.Name -notlike "*BulkFixNullPaths*" -and
    $_.Name -notlike "*FixJoinPathOperations*" -and
    $_.Name -notlike "*AutoFixJoinPath*" -and
    $_.Name -notlike "*FixSyntaxErrors*" -and
    $_.Name -notlike "*FixMultipleIfKeywords*" -and
    $_.Name -notlike "*CleanupDuplicateValidations*" -and
    $_.Name -notlike "*FixVariableReferenceErrors*"
}

Write-Host "Processing $($psFiles.Count) files..." -ForegroundColor Yellow

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    # Process line by line to fix variable references
    $lines = $content -split "`r?`n"
    $newLines = @()
    $modified = $false
    
    foreach ($line in $lines) {
        $originalLine = $line
        
        # Fix pattern: ($ModPath: '$ModPath') -> (${ModPath}: '${ModPath}')
        # Match pattern: ($VAR: '$VAR') where VAR is a variable name
        if ($line -match 'Write-Host.*\(\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]\$([A-Za-z_][A-Za-z0-9_]*)[''"]') {
            $varName = $matches[1]
            $varName2 = $matches[2]
            
            if ($varName -eq $varName2) {
                # Use regex replace with proper escaping
                # Pattern: ($VAR: '$VAR') or ($VAR: "$VAR")
                $pattern1 = "\(\$" + [regex]::Escape($varName) + ":\s*'\$" + [regex]::Escape($varName) + "'\)"
                $pattern2 = "\(\$" + [regex]::Escape($varName) + ':\s*"\$' + [regex]::Escape($varName) + '"\)'
                $replacement = "(`${" + $varName + "}: '`${" + $varName + "}')"
                
                $line = $line -replace $pattern1, $replacement
                $line = $line -replace $pattern2, $replacement
                
                # Also handle without closing paren
                $pattern3 = "\(\$" + [regex]::Escape($varName) + ":\s*'\$" + [regex]::Escape($varName) + "'"
                $pattern4 = "\(\$" + [regex]::Escape($varName) + ':\s*"\$' + [regex]::Escape($varName) + '"'
                $replacement2 = "(`${" + $varName + "}: '`${" + $varName + "}'"
                
                $line = $line -replace $pattern3, $replacement2
                $line = $line -replace $pattern4, $replacement2
                
                if ($line -ne $originalLine) {
                    $modified = $true
                }
            }
        }
        
        $newLines += $line
    }
    
    if ($modified) {
        $content = $newLines -join "`n"
        Set-Content -Path $file.FullName -Value $content -NoNewline
        $filesFixed++
        Write-Host "  [FIXED] $($file.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Fixed $filesFixed files" -ForegroundColor Green
