<#
.SYNOPSIS
    Automatically fixes null path errors in all generator scripts.
    
.DESCRIPTION
    Scans all .ps1 files in the Starbound directory and adds path validation
    to prevent "Cannot bind argument to parameter 'Path' because it is null" errors.
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesFixed = 0
$filesSkipped = 0
$errors = @()

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Null Path Error Fixer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Get all .ps1 files
$psFiles = Get-ChildItem -Path $scriptDir -Filter "*.ps1" -File | Where-Object {
    $_.Name -notlike "*PathValidation*" -and
    $_.Name -notlike "*AddPathValidation*" -and
    $_.Name -notlike "*FixAllNullPaths*"
}

Write-Host "Found $($psFiles.Count) PowerShell scripts to check" -ForegroundColor Yellow
Write-Host ""

foreach ($file in $psFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    $modified = $false
    
    try {
        # Pattern 1: Add ModPath validation if script uses $ModPath
        if ($content -match '\$ModPath' -and $content -match 'param\s*\(') {
            # Check if validation already exists
            if ($content -notmatch 'IsNullOrWhiteSpace.*ModPath|Validate ModPath') {
                # Find the end of param block
                $paramMatch = [regex]::Match($content, 'param\s*\([^)]+\)')
                if ($paramMatch.Success) {
                    $insertPos = $paramMatch.Index + $paramMatch.Length
                    $afterParams = $content.Substring($insertPos)
                    
                    # Find where to insert (after ErrorActionPreference or similar setup)
                    $setupMatch = [regex]::Match($afterParams, '\$ErrorActionPreference\s*=\s*["\']Stop["\']')
                    if ($setupMatch.Success) {
                        $insertPos += $setupMatch.Index + $setupMatch.Length
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
        
        # Pattern 2: Fix Join-Path with $ModPath in OutputDir assignments
        # This is complex and would need careful parsing, so we'll do it manually for critical files
        
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
Write-Host "Note: This script only adds ModPath validation at script start." -ForegroundColor Yellow
Write-Host "      Individual Join-Path operations may still need manual fixes." -ForegroundColor Yellow
Write-Host ""
