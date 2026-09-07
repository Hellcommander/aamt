#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Installs ImageMagick to E:\tools for spellstone asset generation.
    
.DESCRIPTION
    Downloads and installs ImageMagick portable version to E:\tools\ImageMagick
    and adds it to the PATH for the current session.
    
.PARAMETER InstallPath
    Installation directory (default: E:\tools)
    
.PARAMETER Version
    ImageMagick version to install (default: auto-detect latest)
    
.PARAMETER UseChocolatey
    Use Chocolatey package manager if available
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "E:\tools",
    
    [Parameter(Mandatory=$false)]
    [string]$Version = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseChocolatey,

    [Parameter(Mandatory=$false)]
    [switch]$Interactive,

    [Parameter(Mandatory=$false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ImageMagick Installation Script" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if ImageMagick is already installed at E:\tools\ImageMagick
$expectedPath = Join-Path $InstallPath "ImageMagick\magick.exe"
if (Test-Path $expectedPath) {
    Write-Host "✓ ImageMagick is already installed at: $expectedPath" -ForegroundColor Green
    Write-Host "  Version: " -NoNewline
    & $expectedPath -version 2>&1 | Select-Object -First 1
    Write-Host ""
    Write-Host "ImageMagick is ready to use!" -ForegroundColor Green
    exit 0
}

# Check if ImageMagick is installed elsewhere
$magickCommand = Get-Command "magick" -ErrorAction SilentlyContinue
if ($magickCommand) {
    Write-Host "✓ ImageMagick is already installed at: $($magickCommand.Source)" -ForegroundColor Green
    Write-Host "  Version: " -NoNewline
    & magick -version | Select-Object -First 1
    Write-Host ""
    Write-Host "Note: This script installs to E:\tools\ImageMagick" -ForegroundColor Yellow

    # Non-interactive by default: an existing ImageMagick is a safe, usable
    # result, so we keep it and exit 0 unless the caller explicitly opts in.
    # -Force  => reinstall to E:\tools anyway.
    # -Interactive (on a real console) => prompt as before.
    $isConsole = $Host.UI.RawUI -ne $null -and -not [System.Console]::IsInputRedirected
    if ($Force) {
        Write-Host "-Force specified: installing to E:\tools\ImageMagick anyway..." -ForegroundColor Yellow
    }
    elseif ($Interactive -and $isConsole) {
        $continue = Read-Host "Do you want to install to E:\tools anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "Installation cancelled; using existing ImageMagick." -ForegroundColor Yellow
            exit 0
        }
    }
    else {
        Write-Host "Using existing ImageMagick (non-interactive default)." -ForegroundColor Green
        Write-Host "  Pass -Force to reinstall to E:\tools, or -Interactive to be prompted." -ForegroundColor Gray
        exit 0
    }
}

# Create installation directory
$imageMagickPath = Join-Path $InstallPath "ImageMagick"
if (-not (Test-Path $InstallPath)) {
    Write-Host "Creating installation directory: $InstallPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

if (-not (Test-Path $imageMagickPath)) {
    Write-Host "Creating ImageMagick directory: $imageMagickPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $imageMagickPath -Force | Out-Null
}

Write-Host ""
Write-Host "Installation Path: $imageMagickPath" -ForegroundColor Green
Write-Host ""

# Check for package managers first
$wingetCommand = Get-Command "winget" -ErrorAction SilentlyContinue
if ($wingetCommand) {
    Write-Host "Using winget to install ImageMagick..." -ForegroundColor Yellow
    Write-Host ""
    try {
        & winget install --id ImageMagick.ImageMagick --location $imageMagickPath --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ ImageMagick installed via winget" -ForegroundColor Green
            exit 0
        }
    } catch {
        Write-Host "winget installation failed, trying other methods..." -ForegroundColor Yellow
    }
}

# Check for Chocolatey
if ($UseChocolatey) {
    $chocoCommand = Get-Command "choco" -ErrorAction SilentlyContinue
    if ($chocoCommand) {
        Write-Host "Using Chocolatey to install ImageMagick..." -ForegroundColor Yellow
        Write-Host ""
        try {
            & choco install imagemagick.tool --version $Version --params "/InstallDir:`"$imageMagickPath`"" -y
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ ImageMagick installed via Chocolatey" -ForegroundColor Green
                exit 0
            }
        } catch {
            Write-Host "Chocolatey installation failed, trying direct download..." -ForegroundColor Yellow
        }
    }
}

# Determine architecture
$arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
Write-Host "Detected Architecture: $arch" -ForegroundColor Gray
Write-Host ""

# Try to get latest version from GitHub API if not specified
if ([string]::IsNullOrEmpty($Version)) {
    Write-Host "Detecting latest ImageMagick version..." -ForegroundColor Yellow
    try {
        $ProgressPreference = 'SilentlyContinue'
        $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/ImageMagick/ImageMagick/releases/latest" -UseBasicParsing
        $ProgressPreference = 'Continue'
        $Version = $releases.tag_name -replace '^v', ''
        Write-Host "✓ Latest version: $Version" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Could not detect latest version, using 7.1.1-15" -ForegroundColor Yellow
        $Version = "7.1.1-15"
    }
    Write-Host ""
}

# ImageMagick download URLs (try multiple sources and version formats)
$versionFormats = @(
    $Version,
    ($Version -replace '-', '.'),
    ($Version -replace '\.', '-')
)

$downloadUrls = @()
foreach ($vFormat in $versionFormats) {
    $downloadUrls += @(
        "https://github.com/ImageMagick/ImageMagick/releases/download/${vFormat}/ImageMagick-${vFormat}-portable-Q16-HDRI-${arch}.zip",
        "https://imagemagick.org/archive/binaries/ImageMagick-${vFormat}-portable-Q16-HDRI-${arch}.zip"
    )
}

# Also try direct binary download page
$downloadUrls += "https://imagemagick.org/script/download.php#windows"

$zipFile = Join-Path $env:TEMP "ImageMagick-${Version}-${arch}.zip"

Write-Host "Downloading ImageMagick ${Version}..." -ForegroundColor Yellow
Write-Host ""

$downloadSuccess = $false
foreach ($downloadUrl in $downloadUrls) {
    if ($downloadUrl -like "*download.php*") {
        Write-Host "⚠ Manual download required. Please visit:" -ForegroundColor Yellow
        Write-Host "  $downloadUrl" -ForegroundColor Gray
        Write-Host "  Download the portable Q16-HDRI version for $arch" -ForegroundColor Gray
        Write-Host "  Extract to: $imageMagickPath" -ForegroundColor Gray
        Write-Host ""
        break
    }
    
    Write-Host "Trying: $downloadUrl" -ForegroundColor Gray
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing -ErrorAction Stop -TimeoutSec 30
        $ProgressPreference = 'Continue'
        
        # Verify file was downloaded and has content
        if ((Test-Path $zipFile) -and (Get-Item $zipFile).Length -gt 1MB) {
            $downloadSuccess = $true
            Write-Host "✓ Download successful" -ForegroundColor Green
            break
        } else {
            Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Host "  ✗ Failed" -ForegroundColor Yellow
        continue
    }
}

if (-not $downloadSuccess) {
    Write-Host ""
    Write-Host "⚠ Automatic download failed. Please download manually:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://imagemagick.org/script/download.php#windows" -ForegroundColor Gray
    Write-Host "  2. Download: ImageMagick-*-portable-Q16-HDRI-${arch}.zip" -ForegroundColor Gray
    Write-Host "  3. Extract to: $imageMagickPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or use Chocolatey (if installed):" -ForegroundColor Yellow
    Write-Host "  choco install imagemagick.tool -y" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

try {
    
    if (-not (Test-Path $zipFile)) {
        throw "Download failed - file not found"
    }
    
    $fileSize = (Get-Item $zipFile).Length / 1MB
    Write-Host "✓ Downloaded successfully ($([Math]::Round($fileSize, 2)) MB)" -ForegroundColor Green
    Write-Host ""
    
    # Extract ImageMagick
    Write-Host "Extracting ImageMagick..." -ForegroundColor Yellow
    
    # Use .NET compression for extraction
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    
    # Clear existing installation if present
    if (Test-Path $imageMagickPath) {
        Get-ChildItem -Path $imageMagickPath -Recurse | Remove-Item -Force -Recurse
    }
    
    # Extract to temporary location first
    $tempExtract = Join-Path $env:TEMP "ImageMagick-Extract"
    if (Test-Path $tempExtract) {
        Remove-Item -Path $tempExtract -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempExtract -Force | Out-Null
    
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $tempExtract)
    
    # Find the ImageMagick folder inside the extracted files
    $extractedFolders = Get-ChildItem -Path $tempExtract -Directory | Where-Object { $_.Name -like "ImageMagick*" }
    
    if ($extractedFolders.Count -eq 0) {
        # If no ImageMagick folder, the files might be directly in tempExtract
        Write-Host "Moving extracted files..." -ForegroundColor Gray
        Move-Item -Path "$tempExtract\*" -Destination $imageMagickPath -Force
    } else {
        # Move the ImageMagick folder contents
        $sourceFolder = $extractedFolders[0].FullName
        Write-Host "Moving from: $sourceFolder" -ForegroundColor Gray
        Move-Item -Path "$sourceFolder\*" -Destination $imageMagickPath -Force
    }
    
    # Clean up temp extraction folder
    Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "✓ Extraction complete" -ForegroundColor Green
    Write-Host ""
    
    # Verify installation
    $magickExe = Join-Path $imageMagickPath "magick.exe"
    if (Test-Path $magickExe) {
        Write-Host "✓ ImageMagick installed successfully!" -ForegroundColor Green
        Write-Host ""
        
        # Test the installation
        Write-Host "Testing installation..." -ForegroundColor Yellow
        $versionOutput = & $magickExe -version 2>&1 | Select-Object -First 1
        Write-Host "  $versionOutput" -ForegroundColor Gray
        Write-Host ""
        
        # Add to PATH for current session
        $magickDir = $imageMagickPath
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "Process")
        if ($currentPath -notlike "*$magickDir*") {
            $newPath = "$currentPath;$magickDir"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "Process")
            Write-Host "✓ Added to PATH for current session" -ForegroundColor Green
        }
        
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Installation Complete" -ForegroundColor Cyan
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "ImageMagick Location: $imageMagickPath" -ForegroundColor Green
        Write-Host ""
        Write-Host "To add to PATH permanently, run as Administrator:" -ForegroundColor Yellow
        Write-Host "  [Environment]::SetEnvironmentVariable('Path', " -ForegroundColor Gray -NoNewline
        Write-Host "'`$env:Path;E:\tools\ImageMagick', 'Machine')" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Or manually add to System Environment Variables:" -ForegroundColor Yellow
        Write-Host "  E:\tools\ImageMagick" -ForegroundColor Gray
        Write-Host ""
        
    } else {
        throw "magick.exe not found after extraction"
    }
    
    # Clean up zip file
    Remove-Item -Path $zipFile -Force -ErrorAction SilentlyContinue
    
} catch {
    Write-Host ""
    Write-Host "✗ Installation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: Download manually from:" -ForegroundColor Yellow
    Write-Host "  https://imagemagick.org/script/download.php" -ForegroundColor Gray
    Write-Host "  Extract to: $imageMagickPath" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
