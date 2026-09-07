<#
.SYNOPSIS
    Fixes variable reference errors in Write-Host statements - final comprehensive fix.
    
.DESCRIPTION
    Fixes patterns like "($ModPath: '$ModPath')" which cause parser errors.
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
    $_.Name -notlike "*FixVariableReferenceErrors*" -and
    $_.Name -notlike "*FixVariableRefsFinal*"
}

Write-Host "Processing $($psFiles.Count) files..." -ForegroundColor Yellow

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    $modified = $false
    
    # Process line by line
    $lines = $content -split "`r?`n"
    $newLines = @()
    
    foreach ($line in $lines) {
        $originalLine = $line
        
        # Match pattern: ($VAR: '$VAR') where VAR is any variable name
        # Use backreference \1 to match the same variable name
        if ($line -match '\(\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]\$\1[''"]\)') {
            $varName = $matches[1]
            # Simple string replacement - replace ($VAR: '$VAR') with (${VAR}: '${VAR}')
            $oldStr = "(`$" + $varName + ": '`$" + $varName + "')"
            $newStr = "(`${" + $varName + "}: '`${" + $varName + "}')"
            $line = $line.Replace($oldStr, $newStr)
            $modified = $true
        }
        
        # Also match without closing paren: ($VAR: '$VAR'
        if ($line -match '\(\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]\$\1[''"]') {
            $varName = $matches[1]
            # Only fix if not already fixed
            if ($line -notmatch "`${$varName}") {
                $oldStr = "(`$" + $varName + ": '`$" + $varName + "'"
                $newStr = "(`${" + $varName + "}: '`${" + $varName + "}'"
                $line = $line.Replace($oldStr, $newStr)
                $modified = $true
            }
        }
        
        # Also handle double quotes: ($VAR: "$VAR")
        if ($line -match '\(\$([A-Za-z_][A-Za-z0-9_]*):\s*"\$\1"\)') {
            $varName = $matches[1]
            $oldStr = "(`$" + $varName + ': "`$' + $varName + '")'
            $newStr = "(`${" + $varName + '}: "`${' + $varName + '}")'
            $line = $line.Replace($oldStr, $newStr)
            $modified = $true
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
