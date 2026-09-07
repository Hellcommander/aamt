#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Adds Blender to system PATH permanently
    
.DESCRIPTION
    Adds D:\tools\Blender Foundation\Blender 5.0 to system PATH
    Requires Administrator privileges
#>

$blenderDir = "D:\tools\Blender Foundation\Blender 5.0"

Write-Host "Adding Blender to system PATH..." -ForegroundColor Cyan
Write-Host "Directory: $blenderDir" -ForegroundColor Gray
Write-Host ""

# Check if already in PATH
$currentMachinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentMachinePath -like "*$blenderDir*") {
    Write-Host "✓ Blender is already in system PATH" -ForegroundColor Green
    exit 0
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠ This script requires Administrator privileges" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To add Blender to PATH manually:" -ForegroundColor Cyan
    Write-Host "  1. Press Win+X, select 'Windows PowerShell (Admin)' or 'Terminal (Admin)'" -ForegroundColor Gray
    Write-Host "  2. Run this command:" -ForegroundColor Gray
    Write-Host "     [Environment]::SetEnvironmentVariable(`"Path`", `$env:Path + `";$blenderDir`", `"Machine`")" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use Windows Settings:" -ForegroundColor Cyan
    Write-Host "  1. Press Win+X → System → Advanced system settings" -ForegroundColor Gray
    Write-Host "  2. Environment Variables → System variables → Path → Edit" -ForegroundColor Gray
    Write-Host "  3. New → Add: $blenderDir" -ForegroundColor Gray
    Write-Host "  4. OK on all dialogs" -ForegroundColor Gray
    exit 1
}

try {
    # Add to system PATH
    $newPath = $currentMachinePath + ";$blenderDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    
    Write-Host "✓ Successfully added Blender to system PATH" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: You may need to restart your terminal for changes to take effect" -ForegroundColor Yellow
    Write-Host "      Or run: `$env:Path += `";$blenderDir`"" -ForegroundColor Gray
    
} catch {
    Write-Host "✗ Failed to add to system PATH" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Gray
    exit 1
}

