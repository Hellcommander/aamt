<#
.SYNOPSIS
    Automatically fixes Join-Path operations by adding validation before them.
    
.DESCRIPTION
    Scans PowerShell scripts and adds validation before Join-Path operations
    that use $ModPath or $OutputDir to prevent null path errors.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0
$filesSkipped = 0
$operationsFixed = 0
$errors = @()

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Auto Join-Path Fixer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Get all .ps1 files that use Join-Path with ModPath or OutputDir
$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    $content -and (
        ($content -match 'Join-Path\s+\$ModPath') -or 
        ($content -match 'Join-Path\s+\$OutputDir')
    ) -and
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*" -and
    $_.Name -notlike "*BulkFixNullPaths*" -and
    $_.Name -notlike "*FixJoinPathOperations*" -and
    $_.Name -notlike "*AutoFixJoinPath*"
}

Write-Host "Found $($psFiles.Count) scripts with Join-Path operations" -ForegroundColor Yellow
Write-Host ""

foreach ($file in $psFiles) {
    try {
        $lines = Get-Content $file.FullName
        $newLines = @()
        $fileModified = $false
        $opsFixed = 0
        $skipNext = $false
        
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            $trimmed = $line.TrimStart()
            
            # Skip if this line was already processed
            if ($skipNext) {
                $skipNext = $false
                continue
            }
            
            # Pattern 1: $var = Join-Path $ModPath "path"
            if ($trimmed -match '^\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*Join-Path\s+(\$ModPath|\$OutputDir|\$[A-Za-z]+Path)\s+["'']([^"'']+)["'']') {
                $varName = $matches[1]
                $baseVar = $matches[2]
                $pathPart = $matches[3]
                
                # Check if validation already exists (look at previous 5 lines)
                $hasValidation = $false
                for ($j = [Math]::Max(0, $i - 5); $j -lt $i; $j++) {
                    if ($lines[$j] -match "IsNullOrWhiteSpace.*$baseVar" -or 
                        $lines[$j] -match "IsNullOrWhiteSpace.*$varName") {
                        $hasValidation = $true
                        break
                    }
                }
                
                if (-not $hasValidation) {
                    # Add validation before the assignment
                    $indent = $line -replace '^(\s*).*$', '$1'
                    $newLines += "$indent# Validate $baseVar before Join-Path"
                    $newLines += "$indent`$$varName = Join-Path $baseVar `"$pathPart`""
                    $newLines += "$indentif ([string]::IsNullOrWhiteSpace(`$$varName)) {"
                    $newLines += "$indent    Write-Host `"  [FAIL] ${varName} is null (${baseVar}: '${baseVar}')`" -ForegroundColor Red"
                    $newLines += "$indent    continue"
                    $newLines += "$indent}"
                    $fileModified = $true
                    $opsFixed++
                    $operationsFixed++
                    continue
                }
            }
            
            # Pattern 2: OutputDir = (Join-Path $ModPath "path")
            if ($trimmed -match 'OutputDir\s*=\s*\(Join-Path\s+(\$ModPath|\$OutputDir|\$[A-Za-z]+Path)\s+["'']([^"'']+)["'']\)') {
                $baseVar = $matches[1]
                $pathPart = $matches[2]
                
                # Check if validation already exists
                $hasValidation = $false
                for ($j = [Math]::Max(0, $i - 5); $j -lt $i; $j++) {
                    if ($lines[$j] -match "IsNullOrWhiteSpace.*$baseVar" -or 
                        $lines[$j] -match "IsNullOrWhiteSpace.*OutputDir") {
                        $hasValidation = $true
                        break
                    }
                }
                
                if (-not $hasValidation) {
                    # Add validation before the assignment
                    $indent = $line -replace '^(\s*).*$', '$1'
                    $newLines += "$indent# Validate $baseVar before Join-Path"
                    $newLines += "$indent`$tempOutputDir = Join-Path $baseVar `"$pathPart`""
                    $newLines += "$indentif ([string]::IsNullOrWhiteSpace(`$tempOutputDir)) {"
                    $newLines += "$indent    Write-Host `"  [FAIL] OutputDir is null (${baseVar}: '${baseVar}')`" -ForegroundColor Red"
                    $newLines += "$indent    continue"
                    $newLines += "$indent}"
                    $newLines += "$indentOutputDir = `$tempOutputDir"
                    $fileModified = $true
                    $opsFixed++
                    $operationsFixed++
                    continue
                }
            }
            
            # Pattern 3: Direct usage in hashtable: OutputDir = Join-Path $ModPath "path"
            if ($trimmed -match '^\s*OutputDir\s*=\s*Join-Path\s+(\$ModPath|\$OutputDir|\$[A-Za-z]+Path)\s+["'']([^"'']+)["'']') {
                $baseVar = $matches[1]
                $pathPart = $matches[2]
                
                # Check if validation already exists
                $hasValidation = $false
                for ($j = [Math]::Max(0, $i - 5); $j -lt $i; $j++) {
                    if ($lines[$j] -match "IsNullOrWhiteSpace.*$baseVar" -or 
                        $lines[$j] -match "IsNullOrWhiteSpace.*OutputDir") {
                        $hasValidation = $true
                        break
                    }
                }
                
                if (-not $hasValidation) {
                    # Add validation before the assignment
                    $indent = $line -replace '^(\s*).*$', '$1'
                    $newLines += "$indent# Validate $baseVar before Join-Path"
                    $newLines += "$indent`$tempOutputDir = Join-Path $baseVar `"$pathPart`""
                    $newLines += "$indentif ([string]::IsNullOrWhiteSpace(`$tempOutputDir)) {"
                    $newLines += "$indent    Write-Host `"  [FAIL] OutputDir is null (${baseVar}: '${baseVar}')`" -ForegroundColor Red"
                    $newLines += "$indent    continue"
                    $newLines += "$indent}"
                    $newLines += "$indentOutputDir = `$tempOutputDir"
                    $fileModified = $true
                    $opsFixed++
                    $operationsFixed++
                    continue
                }
            }
            
            # Keep the original line
            $newLines += $line
        }
        
        if ($fileModified) {
            Set-Content -Path $file.FullName -Value $newLines
            $filesFixed++
            Write-Host "  [FIXED] $($file.Name) - $opsFixed operations" -ForegroundColor Green
        } else {
            $filesSkipped++
        }
    } catch {
        $errors += "Error processing $($file.Name): $_"
        Write-Host "  [ERROR] $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Files fixed: $filesFixed" -ForegroundColor Green
Write-Host "Files skipped: $filesSkipped (already have validation)" -ForegroundColor Gray
Write-Host "Total operations fixed: $operationsFixed" -ForegroundColor Green

if ($errors.Count -gt 0) {
    Write-Host "Errors: $($errors.Count)" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  $error" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Note: This script adds validation before Join-Path operations." -ForegroundColor Yellow
Write-Host "      Review the changes to ensure they match your coding style." -ForegroundColor Yellow
Write-Host ""
