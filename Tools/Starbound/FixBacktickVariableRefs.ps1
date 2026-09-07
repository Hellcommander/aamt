<#
.SYNOPSIS
    Fixes variable reference errors with backtick-escaped dollar signs.
    
.DESCRIPTION
    Fixes patterns like "`$ModPath: '`$ModPath'" which cause parser errors.
    Changes them to use `${ModPath} to delimit the variable name.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0

Write-Host "Fixing backtick-escaped variable reference errors..." -ForegroundColor Cyan

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
    $_.Name -notlike "*FixBacktickVariableRefs*"
}

Write-Host "Processing $($psFiles.Count) files..." -ForegroundColor Yellow

# Common variable names
$commonVars = @('ModPath', 'OutputDir', 'BackendPath', 'outputBase', 'outputDir', 'targetDir', 
                'spritePath', 'iconPath', 'particlePath', 'soundPath', 'animPath', 'helperPath',
                'metadataPath', 'sourcePath', 'variant2Path', 'dustPath', 'starOutputDir',
                'planetOutputDir', 'starmapOutputDir', 'blackHoleOutputDir', 'wormholeOutputDir',
                'quantumOutputDir', 'gravityWellOutputDir', 'gammaRayOutputDir', 'eventHorizonOutputDir',
                'dustCloudOutputDir', 'accretionDiskOutputDir', 'fileTypeOutputDir', 'generatorAgentPath',
                'directoryOutputDir', 'archiveOutputDir')

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    $modified = $false
    
    # Fix each common variable pattern with backticks
    foreach ($varName in $commonVars) {
        # Pattern: `$VAR: '`$VAR'
        $oldPattern1 = "`$" + $varName + ": '`$" + $varName + "'"
        $newPattern1 = "`${" + $varName + "}: '`${" + $varName + "}'"
        if ($content.Contains($oldPattern1)) {
            $content = $content.Replace($oldPattern1, $newPattern1)
            $modified = $true
        }
        
        # Pattern: (`$VAR: '`$VAR')
        $oldPattern2 = "(`$" + $varName + ": '`$" + $varName + "')"
        $newPattern2 = "(`${" + $varName + "}: '`${" + $varName + "}')"
        if ($content.Contains($oldPattern2)) {
            $content = $content.Replace($oldPattern2, $newPattern2)
            $modified = $true
        }
        
        # Pattern with double quotes: (`$VAR: "`$VAR")
        $oldPattern3 = "(`$" + $varName + ': "`$' + $varName + '")'
        $newPattern3 = "(`${" + $varName + '}: "`${' + $varName + '}")'
        if ($content.Contains($oldPattern3)) {
            $content = $content.Replace($oldPattern3, $newPattern3)
            $modified = $true
        }
    }
    
    # Also do a general regex replacement for any variable pattern we might have missed
    $lines = $content -split "`r?`n"
    $newLines = @()
    
    foreach ($line in $lines) {
        $originalLine = $line
        
        # Match pattern: `$VAR: '`$VAR' where VAR is any variable name
        # Use a simpler approach - just look for the pattern and replace
        if ($line -match '`\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]`\$\1[''"]') {
            $varName = $matches[1]
            # Only fix if not already fixed
            if ($line -notmatch '\$\{' + $varName + '\}') {
                $oldStr = "`$" + $varName + ": '`$" + $varName + "'"
                $newStr = "`${" + $varName + "}: '`${" + $varName + "}'"
                $line = $line.Replace($oldStr, $newStr)
                $modified = $true
            }
        }
        
        # Match with parens: (`$VAR: '`$VAR')
        if ($line -match '\(`\$([A-Za-z_][A-Za-z0-9_]*):\s*[''"]`\$\1[''"]\)') {
            $varName = $matches[1]
            if ($line -notmatch '\$\{' + $varName + '\}') {
                $oldStr = "(`$" + $varName + ": '`$" + $varName + "')"
                $newStr = "(`${" + $varName + "}: '`${" + $varName + "}')"
                $line = $line.Replace($oldStr, $newStr)
                $modified = $true
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
