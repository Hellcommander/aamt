<#
.SYNOPSIS
    Bulk fix null path errors in all generator scripts.
    
.DESCRIPTION
    Automatically adds path validation to all .ps1 files that use $ModPath or $OutputDir.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0
$filesSkipped = 0
$errors = @()

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Bulk Null Path Fixer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Get all .ps1 files that use ModPath or OutputDir
$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    $content -and (
        ($content -match '\$ModPath') -or 
        ($content -match '\$OutputDir')
    ) -and
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*" -and
    $_.Name -notlike "*BulkFixNullPaths*"
}

Write-Host "Found $($psFiles.Count) scripts that use ModPath or OutputDir" -ForegroundColor Yellow
Write-Host ""

foreach ($file in $psFiles) {
    try {
        $content = Get-Content $file.FullName -Raw
        $originalContent = $content
        $modified = $false
        
        # Pattern 1: Add ModPath validation at script start (if uses $ModPath)
        if ($content -match '\$ModPath' -and $content -match 'param\s*\(') {
            # Check if validation already exists
            if ($content -notmatch 'IsNullOrWhiteSpace.*ModPath|Validate ModPath.*cannot be empty') {
                # Find position after param block and ErrorActionPreference
                $paramPattern = 'param\s*\([^)]+\)'
                $paramMatch = [regex]::Match($content, $paramPattern)
                
                if ($paramMatch.Success) {
                    $afterParams = $content.Substring($paramMatch.Index + $paramMatch.Length)
                    
                    # Look for ErrorActionPreference or similar setup code
                    $setupPattern = '\$ErrorActionPreference\s*=\s*["'']Stop["'']'
                    $setupMatch = [regex]::Match($afterParams, $setupPattern)
                    
                    $insertPos = $paramMatch.Index + $paramMatch.Length
                    if ($setupMatch.Success) {
                        $insertPos += $setupMatch.Index + $setupMatch.Length
                    }
                    
                    # Check if there's already a validation comment nearby
                    $checkArea = $content.Substring([Math]::Max(0, $insertPos - 200), [Math]::Min(400, $content.Length - [Math]::Max(0, $insertPos - 200)))
                    if ($checkArea -notmatch 'IsNullOrWhiteSpace.*ModPath') {
                        $validationCode = @"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace(`$ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

"@
                        $content = $content.Insert($insertPos, $validationCode)
                        $modified = $true
                    }
                }
            }
        }
        
        if ($modified) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
            $filesFixed++
            Write-Host "  [FIXED] $($file.Name)" -ForegroundColor Green
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
Write-Host "Fixed: $filesFixed files" -ForegroundColor Green
Write-Host "Skipped: $filesSkipped files (already have validation or don't need it)" -ForegroundColor Gray

if ($errors.Count -gt 0) {
    Write-Host "Errors: $($errors.Count)" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  $error" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Note: This adds ModPath validation at script start." -ForegroundColor Yellow
Write-Host "      Individual Join-Path operations may need additional validation." -ForegroundColor Yellow
Write-Host ""
