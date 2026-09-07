#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test script to verify spritesheet preview loading
#>

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$testDir = Join-Path $PSScriptRoot "Output\TestSamples\Spritesheets"

Write-Host "Creating test spritesheet for preview test..." -ForegroundColor Cyan

# Create directory
New-Item -ItemType Directory -Path $testDir -Force | Out-Null

# Create a simple test image (200x200 cyan square)
Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap(200, 200)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::FromArgb(26, 42, 58)) # Dark blue background
$brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(102, 204, 255)) # Cyan
$graphics.FillEllipse($brush, 50, 50, 100, 100)
$graphics.Dispose()

# Save as test spritesheet
$testFile = Join-Path $testDir "test_spritesheet_120facings.png"
$bitmap.Save($testFile, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()

Write-Host "✓ Created test spritesheet: $testFile" -ForegroundColor Green
Write-Host "  File size: $((Get-Item $testFile).Length) bytes" -ForegroundColor Gray
Write-Host ""
Write-Host "Now launch the monitor to test:" -ForegroundColor Yellow
Write-Host "  powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1 -WatchDirectory `"Output\TestSamples`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "The monitor should detect and display this spritesheet preview." -ForegroundColor Gray

