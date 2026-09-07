<#
.SYNOPSIS
    Comprehensive fix for ALL variable reference errors in Write-Host statements.
    
.DESCRIPTION
    Fixes patterns like "$VAR: '$VAR'" or "`$VAR: '`$VAR'" which cause parser errors.
    Changes them to use ${VAR} to delimit the variable name.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0
$totalFixes = 0

Write-Host "Fixing ALL variable reference errors in Write-Host statements..." -ForegroundColor Cyan

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
    $_.Name -notlike "*FixVariableReferenceErrors*" -and
    $_.Name -notlike "*FixVariableRefsFinal*" -and
    $_.Name -notlike "*FixAllVariableRefs*" -and
    $_.Name -notlike "*FixBacktickVariableRefs*" -and
    $_.Name -notlike "*FixAllVariableRefErrors*"
}

Write-Host "Processing $($psFiles.Count) files..." -ForegroundColor Yellow

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    $fileFixes = 0
    
    # Process line by line
    $lines = $content -split "`r?`n"
    $newLines = @()
    
    foreach ($line in $lines) {
        $originalLine = $line
        
        # Pattern 1: ($VAR: '$VAR') - with regular dollar signs
        if ($line -match '\(\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]\$\1[''"]\)') {
            $varName = $matches[1]
            if ($line -notmatch '\$\{' + $varName + '\}') {
                $oldStr = "(`$" + $varName + ": '`$" + $varName + "')"
                $newStr = "(`${" + $varName + "}: '`${" + $varName + "}')"
                $line = $line.Replace($oldStr, $newStr)
                $fileFixes++
            }
        }
        
        # Pattern 2: `$VAR: '`$VAR' - with backtick-escaped dollar signs
        if ($line -match '`\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]`\$\1[''"]') {
            $varName = $matches[1]
            if ($line -notmatch '`\$\{' + $varName + '\}') {
                $oldStr = "`$" + $varName + ": '`$" + $varName + "'"
                $newStr = "`${" + $varName + "}: '`${" + $varName + "}'"
                $line = $line.Replace($oldStr, $newStr)
                $fileFixes++
            }
        }
        
        # Pattern 3: (`$VAR: '`$VAR') - with backticks and parens
        if ($line -match '\(`\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]`\$\1[''"]\)') {
            $varName = $matches[1]
            if ($line -notmatch '`\$\{' + $varName + '\}') {
                $oldStr = "(`$" + $varName + ": '`$" + $varName + "')"
                $newStr = "(`${" + $varName + "}: '`${" + $varName + "}')"
                $line = $line.Replace($oldStr, $newStr)
                $fileFixes++
            }
        }
        
        # Pattern 4: $VAR: '$VAR' (without parens) - regular dollar signs
        if ($line -match '\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]\$\1[''"]' -and $line -match 'Write-Host') {
            $varName = $matches[1]
            if ($line -notmatch '\$\{' + $varName + '\}') {
                $oldStr = "`$" + $varName + ": '`$" + $varName + "'"
                $newStr = "`${" + $varName + "}: '`${" + $varName + "}'"
                $line = $line.Replace($oldStr, $newStr)
                $fileFixes++
            }
        }
        
        $newLines += $line
    }
    
    if ($fileFixes -gt 0) {
        $content = $newLines -join "`n"
        Set-Content -Path $file.FullName -Value $content -NoNewline
        $filesFixed++
        $totalFixes += $fileFixes
        Write-Host "  [FIXED] $($file.Name) - $fileFixes fixes" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Fixed $filesFixed files with $totalFixes total fixes" -ForegroundColor Green
