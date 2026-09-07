#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Finds Blender installation on the system
#>

Write-Host "Searching for Blender installation..." -ForegroundColor Cyan
Write-Host ""

# Search all drives and common locations
$drives = Get-PSDrive -PSProvider FileSystem | Select-Object -ExpandProperty Name
$searchPaths = @()

foreach ($drive in $drives) {
    $searchPaths += "$drive`:\Program Files\Blender Foundation"
    $searchPaths += "$drive`:\Program Files (x86)\Blender Foundation"
    $searchPaths += "$drive`:\Program Files\Blender*"
}

# Also check user locations
$searchPaths += "$env:LOCALAPPDATA\Programs\Blender Foundation"
$searchPaths += "$env:APPDATA\Blender*"

$foundBlenders = @()

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath -ErrorAction SilentlyContinue) {
        # Check if it's directly a blender.exe
        $blenderExe = Join-Path $basePath "blender.exe"
        if (Test-Path $blenderExe) {
            $foundBlenders += $blenderExe
            continue
        }
        
        # Check subdirectories
        $blenderDirs = Get-ChildItem -Path $basePath -Directory -ErrorAction SilentlyContinue | 
            Where-Object { $_.Name -like "Blender*" }
        
        foreach ($dir in $blenderDirs) {
            $blenderExe = Join-Path $dir.FullName "blender.exe"
            if (Test-Path $blenderExe) {
                $foundBlenders += $blenderExe
            }
        }
    }
}

if ($foundBlenders.Count -eq 0) {
    Write-Host "✗ Blender not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "To add Blender to PATH:" -ForegroundColor Yellow
    Write-Host "  1. Find your Blender installation folder" -ForegroundColor Gray
    Write-Host "  2. Add the folder containing blender.exe to System PATH" -ForegroundColor Gray
    Write-Host "  3. Or run: AddBlenderToPath.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host "Found Blender installation(s):" -ForegroundColor Green
foreach ($blender in $foundBlenders) {
    $dir = Split-Path $blender -Parent
    Write-Host "  - $blender" -ForegroundColor Cyan
    Write-Host "    Directory: $dir" -ForegroundColor Gray
}

# Use the most recent version
$latestBlender = $foundBlenders | Sort-Object { 
    $dir = Split-Path $_ -Parent
    $versionMatch = [regex]::Match($dir, '(\d+\.\d+)')
    if ($versionMatch.Success) {
        [version]$versionMatch.Groups[1].Value
    } else {
        [version]"0.0"
    }
} -Descending | Select-Object -First 1

$blenderDir = Split-Path $latestBlender -Parent

Write-Host ""
Write-Host "Using: $latestBlender" -ForegroundColor Green
Write-Host "Directory: $blenderDir" -ForegroundColor Cyan
Write-Host ""

# Check if in PATH
$currentPath = $env:Path
if ($currentPath -like "*$blenderDir*") {
    Write-Host "✓ Already in PATH" -ForegroundColor Green
} else {
    Write-Host "Not in PATH. To add permanently:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run this command as Administrator:" -ForegroundColor Cyan
    Write-Host '  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";' + $blenderDir + '", "Machine")' -ForegroundColor White
    Write-Host ""
    Write-Host "Or add this directory to PATH via Windows Settings:" -ForegroundColor Cyan
    Write-Host "  $blenderDir" -ForegroundColor White
}

# Return the path for use in other scripts
return $blenderDir

