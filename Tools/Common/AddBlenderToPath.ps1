#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Finds Blender installation and adds it to PATH
    
.DESCRIPTION
    Searches common locations for Blender and provides instructions
    to add it to PATH permanently, or adds it for the current session.
#>

Write-Host "Searching for Blender installation..." -ForegroundColor Cyan
Write-Host ""

# Search locations
$searchPaths = @(
    "E:\tools\Blender Foundation",
    "D:\tools\Blender Foundation",
    "${env:ProgramFiles}\Blender Foundation",
    "${env:ProgramFiles(x86)}\Blender Foundation",
    "$env:LOCALAPPDATA\Programs\Blender Foundation",
    "C:\Program Files\Blender Foundation",
    "C:\Program Files (x86)\Blender Foundation",
    "D:\Program Files\Blender Foundation",
    "D:\Program Files (x86)\Blender Foundation"
)

$foundBlender = $null

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath) {
        $blenderDirs = Get-ChildItem -Path $basePath -Directory -Filter "Blender *" -ErrorAction SilentlyContinue
        foreach ($dir in $blenderDirs) {
            $blenderExe = Join-Path $dir.FullName "blender.exe"
            if (Test-Path $blenderExe) {
                $foundBlender = $blenderExe
                Write-Host "✓ Found Blender: $blenderExe" -ForegroundColor Green
                break
            }
        }
        if ($foundBlender) { break }
    }
}

if (-not $foundBlender) {
    Write-Host "✗ Blender not found in common locations" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please provide the path to blender.exe manually:" -ForegroundColor Yellow
    Write-Host "  Example: C:\Program Files\Blender Foundation\Blender 4.0\blender.exe" -ForegroundColor Gray
    # Non-interactive safe: skip the manual-path prompt when no console is attached.
    $__interactive = ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and $env:AAMT_NONINTERACTIVE -ne '1')
    if ($__interactive) {
        $manualPath = Read-Host "Enter Blender path (or press Enter to skip)"
    } else {
        Write-Host "Non-interactive: no Blender path provided; skipping." -ForegroundColor Gray
        $manualPath = ""
    }
    
    if ($manualPath -and (Test-Path $manualPath)) {
        $foundBlender = $manualPath
        Write-Host "✓ Using provided path: $foundBlender" -ForegroundColor Green
    } else {
        Write-Host "✗ Blender path not found or invalid" -ForegroundColor Red
        exit 1
    }
}

# Get the directory containing blender.exe
$blenderDir = Split-Path $foundBlender -Parent

Write-Host ""
Write-Host "Blender directory: $blenderDir" -ForegroundColor Cyan
Write-Host ""

# Check if already in PATH
$currentPath = $env:Path
if ($currentPath -like "*$blenderDir*") {
    Write-Host "✓ Blender directory is already in PATH" -ForegroundColor Green
} else {
    Write-Host "Blender directory is NOT in PATH" -ForegroundColor Yellow
    Write-Host ""
    
    # Add to current session
    $env:Path += ";$blenderDir"
    Write-Host "✓ Added to PATH for current session" -ForegroundColor Green
    Write-Host ""
    
    # Instructions for permanent addition
    Write-Host "To add Blender to PATH permanently:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Method 1: PowerShell (Run as Administrator)" -ForegroundColor Cyan
    Write-Host '  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";' + $blenderDir + '", "Machine")' -ForegroundColor Gray
    Write-Host ""
    Write-Host "Method 2: Windows Settings" -ForegroundColor Cyan
    Write-Host "  1. Press Win+X, select 'System'" -ForegroundColor Gray
    Write-Host "  2. Click 'Advanced system settings'" -ForegroundColor Gray
    Write-Host "  3. Click 'Environment Variables'" -ForegroundColor Gray
    Write-Host "  4. Under 'System variables', select 'Path' and click 'Edit'" -ForegroundColor Gray
    Write-Host "  5. Click 'New' and add: $blenderDir" -ForegroundColor Gray
    Write-Host "  6. Click OK on all dialogs" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Method 3: Command Prompt (Run as Administrator)" -ForegroundColor Cyan
    Write-Host "  setx PATH `"%PATH%;$blenderDir`" /M" -ForegroundColor Gray
    Write-Host ""
    
    # Ask if user wants to add permanently (requires admin)
    # Non-interactive safe: default to NOT modifying the system PATH unattended.
    $__interactive = ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and $env:AAMT_NONINTERACTIVE -ne '1')
    if ($__interactive) {
        $addPermanent = Read-Host "Add to PATH permanently now? (requires Administrator) [Y/N]"
    } else {
        Write-Host "Non-interactive: not modifying system PATH (added for current session only)." -ForegroundColor Gray
        $addPermanent = 'N'
    }
    if ($addPermanent -eq 'Y' -or $addPermanent -eq 'y') {
        try {
            # Try to add to system PATH
            $currentMachinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
            if ($currentMachinePath -notlike "*$blenderDir*") {
                [Environment]::SetEnvironmentVariable("Path", $currentMachinePath + ";$blenderDir", "Machine")
                Write-Host "✓ Added to system PATH permanently" -ForegroundColor Green
                Write-Host "  Note: You may need to restart your terminal for changes to take effect" -ForegroundColor Yellow
            } else {
                Write-Host "✓ Already in system PATH" -ForegroundColor Green
            }
        } catch {
            Write-Host "✗ Failed to add to system PATH (requires Administrator privileges)" -ForegroundColor Red
            Write-Host "  Error: $_" -ForegroundColor Gray
            Write-Host "  Please use Method 2 (Windows Settings) or run PowerShell as Administrator" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Testing Blender..." -ForegroundColor Cyan
$testBlender = Get-Command blender -ErrorAction SilentlyContinue
if ($testBlender) {
    Write-Host "✓ Blender is now accessible via 'blender' command" -ForegroundColor Green
    Write-Host "  Location: $($testBlender.Source)" -ForegroundColor Gray
} else {
    Write-Host "⚠ Blender command not yet available in this session" -ForegroundColor Yellow
    Write-Host "  Restart your terminal or run: `$env:Path += `";$blenderDir`"" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green

