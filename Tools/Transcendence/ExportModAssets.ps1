<#
.SYNOPSIS
    Exports and processes TranscendenceArt assets for mod development.

.DESCRIPTION
    This tool helps modders create spritesheets, projectiles, and other game assets
    by using the official TranscendenceArt repository as reference. It can:
    - Download/clone the TranscendenceArt repository
    - Extract reference images and models
    - Generate spritesheets from images

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Export assets in game-compatible formats
    - Include proper credits and attribution

.PARAMETER ArtRepoPath
    Path to TranscendenceArt repository (will clone if not exists)

.PARAMETER OutputPath
    Output directory for exported assets

.PARAMETER AssetType
    Type of assets to process: Spritesheet, Projectile, Ship, Item, All

.PARAMETER SourceFolder
    Specific folder in Art repo to process (e.g., "Commonwealth Fleet", "Items")

.PARAMETER GenerateSpritesheet
    Generate spritesheet from images

.PARAMETER IncludeCredits
    Include credits file with exported assets

.PARAMETER ExportModels
    Also export 3D model files (OBJ, FBX, glTF, etc.)

.PARAMETER ExportAll
    Export all asset types (images, models, textures)

.PARAMETER TileWidth
    Width of each tile in spritesheet (default: 64)

.PARAMETER TileHeight
    Height of each tile in spritesheet (default: 64)

.PARAMETER Columns
    Number of columns in spritesheet grid (default: 8)

.PARAMETER SkipToolDownload
    Skip automatic download/installation of required tools (Git, ImageMagick)

.EXAMPLE
    .\ExportModAssets.ps1 -ArtRepoPath "D:\TranscendenceArt" -OutputPath "MyMod\Assets" -AssetType Ship

.EXAMPLE
    .\ExportModAssets.ps1 -GenerateSpritesheet -SourceFolder "Items" -OutputPath "MyMod\Resources"

.EXAMPLE
    .\ExportModAssets.ps1 -SourceFolder "Commonwealth Fleet" -ExportAll -OutputPath "MyMod\Assets"
#>

[CmdletBinding()]
param(
    [string]$ArtRepoPath = "",
    
    [string]$OutputPath = "",
    
    [ValidateSet("Spritesheet", "Projectile", "Ship", "Item", "All")]
    [string]$AssetType = "All",
    
    [string]$SourceFolder = "",
    
    [switch]$GenerateSpritesheet,
    
    [switch]$IncludeCredits,
    
    [switch]$CloneRepo,
    
    [int]$TileWidth = 64,
    
    [int]$TileHeight = 64,
    
    [int]$Columns = 8,
    
    [switch]$ExportModels,
    
    [switch]$ExportAll,
    
    [switch]$SkipToolDownload,
    
    [switch]$GenerateShipFacings,
    
    [int]$FacingCount = 120,
    
    [string]$BlenderPath = ""
)

$ErrorActionPreference = "Stop"

function Test-IsInteractiveConsole {
    # True only when a real user can answer a prompt (never when stdin is
    # redirected or the host is non-interactive). Used to auto-pick the safe
    # non-destructive default (skip tool install) on unattended runs.
    try {
        if (-not [Environment]::UserInteractive) { return $false }
        if ([Console]::IsInputRedirected) { return $false }
        return $true
    } catch { return $false }
}

# ============================================================
# CONFIGURATION
# ============================================================

$script:ArtRepoUrl = "https://github.com/kronosaur/TranscendenceArt.git"
$script:ArtRepoDefaultPath = Join-Path $PSScriptRoot "TranscendenceArt"
$script:SdkPath = Join-Path $PSScriptRoot "SDK"

# Required tools/SDKs
$script:RequiredTools = @{
    "Git" = @{
        Name = "Git for Windows"
        Url = ""  # Will be determined dynamically
        LatestUrl = "https://github.com/git-for-windows/git/releases/latest"
        Installer = "Git-Installer.exe"
        CheckCommand = "git"
        Required = $true
        Note = "Required for cloning the TranscendenceArt repository"
        DownloadPage = "https://git-scm.com/download/win"
    }
    "ImageMagick" = @{
        Name = "ImageMagick"
        Url = ""
        LatestUrl = "https://github.com/ImageMagick/ImageMagick/releases/latest"
        Installer = "ImageMagick-Installer.exe"
        CheckCommand = "magick"
        Required = $false
        Note = "Optional: Enables automatic spritesheet generation. Without it, manifest files are created for manual spritesheet creation."
        DownloadPage = "https://imagemagick.org/script/download.php#windows"
    }
    "Blender" = @{
        Name = "Blender"
        Url = ""
        LatestUrl = "https://www.blender.org/download/"
        Installer = "Blender-Installer.exe"
        CheckCommand = "blender"
        Required = $false
        Note = "Optional: Required for generating ship facings from 3D models. Enables rendering models from multiple angles."
        DownloadPage = "https://www.blender.org/download/"
        CommonPaths = @(
            "${env:ProgramFiles}\Blender Foundation\Blender *\blender.exe",
            "${env:ProgramFiles(x86)}\Blender Foundation\Blender *\blender.exe"
        )
    }
}

$script:CreditsText = @"
Transcendence Art Assets Reference
===================================

This mod uses assets created with reference to the official TranscendenceArt repository:
https://github.com/kronosaur/TranscendenceArt

Original 3D models and artwork:
Copyright (c) 2003-2019 by Kronosaur Productions, LLC.
https://transcendence.kronosaur.com

These assets are provided as reference material for mod development.
Please respect the original license and attribution requirements.

For help with modding, visit:
https://forums.kronosaur.com/
"@

# ============================================================
# TOOL/SDK MANAGEMENT
# ============================================================

function Test-ToolInstalled {
    param([string]$CommandName)
    
    $tool = Get-Command $CommandName -ErrorAction SilentlyContinue
    return ($null -ne $tool)
}

function Find-Blender {
    <#
    .SYNOPSIS
      Finds Blender installation by checking registry, environment variables, PATH, and common locations
    #>
    Write-Host "Detecting Blender installation..." -ForegroundColor Cyan
    
    # 1. Check if path was provided by user (highest priority)
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
        $providedPath = $BlenderPath.Trim()
        
        # If user provided a directory, look for blender.exe inside
        if (Test-Path $providedPath -PathType Container) {
            $blenderExe = Join-Path $providedPath "blender.exe"
            if (Test-Path $blenderExe) {
                Write-Host "  Found via provided path: $blenderExe" -ForegroundColor Green
                return $blenderExe
            }
        } elseif (Test-Path $providedPath -PathType Leaf) {
            Write-Host "  Found via provided path: $providedPath" -ForegroundColor Green
            return $providedPath
        }
    }
    
    # 2. Tools/TranscendenceTools.ini (user-editable)
    $toolPaths = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\ToolPaths.ps1"
    if (Test-Path $toolPaths) {
        . $toolPaths
        $fromIni = Get-AamtBlenderPath
        if ($fromIni -and (Test-Path $fromIni)) {
            Write-Host "  Found via TranscendenceTools.ini: $fromIni" -ForegroundColor Green
            return $fromIni
        }
    }

    # 3. Check environment variables
    $envVars = @("BLENDER_PATH", "BLENDER_DIR", "BLENDER_HOME", "BLENDER")
    foreach ($envVar in $envVars) {
        $envPath = [System.Environment]::GetEnvironmentVariable($envVar)
        if (-not [string]::IsNullOrWhiteSpace($envPath)) {
            if (Test-Path $envPath -PathType Container) {
                $blenderExe = Join-Path $envPath "blender.exe"
                if (Test-Path $blenderExe) {
                    Write-Host "  Found via environment variable $envVar : $blenderExe" -ForegroundColor Green
                    return $blenderExe
                }
            } elseif (Test-Path $envPath -PathType Leaf) {
                Write-Host "  Found via environment variable $envVar : $envPath" -ForegroundColor Green
                return $envPath
            }
        }
    }
    
    # 3. Check PATH (command lookup)
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        Write-Host "  Found via PATH: $($blender.Source)" -ForegroundColor Green
        return $blender.Source
    }
    
    # 4. Check Windows Registry (Uninstall keys)
    try {
        $registryKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        
        foreach ($regPath in $registryKeys) {
            $installed = Get-ItemProperty $regPath -ErrorAction SilentlyContinue | 
                Where-Object { $_.DisplayName -like "*Blender*" -and -not [string]::IsNullOrWhiteSpace($_.InstallLocation) }
            
            if ($installed) {
                foreach ($install in $installed) {
                    $installPath = $install.InstallLocation.Trim()
                    if (-not [string]::IsNullOrWhiteSpace($installPath) -and (Test-Path $installPath)) {
                        $blenderExe = Join-Path $installPath "blender.exe"
                        if (Test-Path $blenderExe) {
                            Write-Host "  Found via registry: $blenderExe" -ForegroundColor Green
                            Write-Host "    Version: $($install.DisplayVersion)" -ForegroundColor Gray
                            return $blenderExe
                        }
                    }
                }
            }
        }
    }
    catch {
        Write-Host "  Registry check failed: $_" -ForegroundColor Yellow
    }
    
    # 5. Check common installation paths (including custom D:\tools location)
    $commonPaths = @(
        "E:\tools\Blender Foundation",  # Primary (post OS-drive migrate)
        "D:\tools\Blender Foundation",
        "${env:ProgramFiles}\Blender Foundation",
        "${env:ProgramFiles(x86)}\Blender Foundation",
        "${env:LOCALAPPDATA}\Programs\Blender Foundation",
        "C:\Program Files\Blender Foundation",
        "C:\Program Files (x86)\Blender Foundation"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending  # Prefer newer versions
            
            foreach ($dir in $blenderDirs) {
                $blenderExe = Join-Path $dir.FullName "blender.exe"
                if (Test-Path $blenderExe) {
                    Write-Host "  Found via common path: $blenderExe" -ForegroundColor Green
                    return $blenderExe
                }
            }
        }
    }
    
    Write-Host "  Blender not found automatically" -ForegroundColor Yellow
    return $null
}

function Test-BlenderVulkanStartup {
    <#
    .SYNOPSIS
      Checks if Blender has the Vulkan startup file (required for UI to work on some systems)
    #>
    param([string]$BlenderExePath)
    
    if ([string]::IsNullOrWhiteSpace($BlenderExePath) -or -not (Test-Path $BlenderExePath)) {
        return $false
    }
    
    $blenderDir = Split-Path $BlenderExePath -Parent
    $vulkanStartup = Join-Path $blenderDir "blender_startup_vulkan.cmd"
    
    return (Test-Path $vulkanStartup)
}

function Get-BlenderVulkanStartupPath {
    <#
    .SYNOPSIS
      Gets the path to Blender's Vulkan startup script, or returns the regular blender.exe if not found
    #>
    param([string]$BlenderExePath)
    
    if ([string]::IsNullOrWhiteSpace($BlenderExePath) -or -not (Test-Path $BlenderExePath)) {
        return $null
    }
    
    $blenderDir = Split-Path $BlenderExePath -Parent
    $vulkanStartup = Join-Path $blenderDir "blender_startup_vulkan.cmd"
    
    if (Test-Path $vulkanStartup) {
        return $vulkanStartup
    }
    
    # Return regular blender.exe if Vulkan startup not found
    return $BlenderExePath
}

function New-BlenderVulkanStartup {
    <#
    .SYNOPSIS
      Creates the Vulkan startup file for Blender if it's missing
    #>
    param([string]$BlenderExePath)
    
    if ([string]::IsNullOrWhiteSpace($BlenderExePath) -or -not (Test-Path $BlenderExePath)) {
        Write-Host "  Cannot create Vulkan startup: Blender path invalid" -ForegroundColor Red
        return $false
    }
    
    $blenderDir = Split-Path $BlenderExePath -Parent
    $vulkanStartup = Join-Path $blenderDir "blender_startup_vulkan.cmd"
    
    if (Test-Path $vulkanStartup) {
        Write-Host "  Vulkan startup file already exists" -ForegroundColor Green
        return $true
    }
    
    try {
        $startupContent = @"
@echo off
echo Starting Blender with the Vulkan backend

"%~dp0\blender.exe" --gpu-backend vulkan
"@
        
        [System.IO.File]::WriteAllText($vulkanStartup, $startupContent, [System.Text.Encoding]::ASCII)
        
        if (Test-Path $vulkanStartup) {
            Write-Host "  ✓ Created Vulkan startup file: $vulkanStartup" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ✗ Failed to create Vulkan startup file" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Error creating Vulkan startup file: $_" -ForegroundColor Red
        return $false
    }
}

function Get-ToolDownloadPath {
    param([hashtable]$ToolInfo)
    
    if (-not (Test-Path $script:SdkPath)) {
        New-Item -ItemType Directory -Path $script:SdkPath -Force | Out-Null
    }
    
    return Join-Path $script:SdkPath $ToolInfo.Installer
}

function Get-LatestGitUrl {
    <#
    .SYNOPSIS
      Attempts to get the latest Git for Windows download URL
    #>
    try {
        # Try to get latest release page
        $latestPage = Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/latest" -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
        $redirectUrl = $latestPage.Headers.Location
        
        if ($redirectUrl) {
            # Extract version from redirect URL
            if ($redirectUrl -match '/tag/v?(\d+\.\d+\.\d+)') {
                $version = $matches[1]
                # Try 64-bit installer
                $downloadUrl = "https://github.com/git-for-windows/git/releases/download/v$version.windows.1/Git-$version-64-bit.exe"
                return $downloadUrl
            }
        }
    }
    catch {
        # Fallback to a known working version
        return "https://github.com/git-for-windows/git/releases/latest/download/Git-2.43.0-64-bit.exe"
    }
    
    return "https://github.com/git-for-windows/git/releases/latest/download/Git-2.43.0-64-bit.exe"
}

function Download-Tool {
    param(
        [string]$ToolName,
        [hashtable]$ToolInfo
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Downloading: $($ToolInfo.Name)" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Get download URL (try to get latest for Git)
    $downloadUrl = $ToolInfo.Url
    if ($ToolName -eq "Git" -and [string]::IsNullOrWhiteSpace($downloadUrl)) {
        Write-Host "  Getting latest Git version..." -ForegroundColor Gray
        $downloadUrl = Get-LatestGitUrl
        Write-Host "  Using: $downloadUrl" -ForegroundColor Gray
    }
    
    # Handle tools that require manual download
    if ([string]::IsNullOrWhiteSpace($downloadUrl) -or $downloadUrl -match 'download\.php|releases/latest$') {
        Write-Host "  Manual download required" -ForegroundColor Yellow
        if ($ToolInfo.DownloadPage) {
            Write-Host "  Download page: $($ToolInfo.DownloadPage)" -ForegroundColor Gray
        }
        if ($ToolInfo.LatestUrl) {
            Write-Host "  Latest releases: $($ToolInfo.LatestUrl)" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "  Please download the installer and run it manually." -ForegroundColor Yellow
        Write-Host "  After installation, restart this script." -ForegroundColor Yellow
        Write-Host ""
        return $null
    }
    
    $downloadPath = Get-ToolDownloadPath -ToolInfo $ToolInfo
    
    try {
        # Check if already downloaded
        if (Test-Path $downloadPath) {
            $fileSize = (Get-Item $downloadPath).Length / 1MB
            Write-Host "  Already downloaded: $downloadPath ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green
            Write-Host ""
            return $downloadPath
        }
        
        Write-Host "  Downloading from: $downloadUrl" -ForegroundColor Gray
        Write-Host "  Saving to: $downloadPath" -ForegroundColor Gray
        Write-Host "  This may take several minutes..." -ForegroundColor Yellow
        Write-Host ""
        
        $ProgressPreference = 'Continue'
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -UseBasicParsing -ErrorAction Stop
        }
        catch {
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -ErrorAction Stop
        }
        
        if (Test-Path $downloadPath) {
            $fileSize = (Get-Item $downloadPath).Length / 1MB
            Write-Host ""
            Write-Host "  ✓ Download complete: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
            Write-Host ""
            return $downloadPath
        } else {
            Write-Host ""
            Write-Host "  ✗ Download failed: File not found after download" -ForegroundColor Red
            Write-Host ""
            return $null
        }
    }
    catch {
        Write-Host ""
        Write-Host "  ✗ Error downloading: $_" -ForegroundColor Red
        if ($ToolInfo.DownloadPage) {
            Write-Host "  Please download manually from: $($ToolInfo.DownloadPage)" -ForegroundColor Yellow
        } elseif ($ToolInfo.LatestUrl) {
            Write-Host "  Please download manually from: $($ToolInfo.LatestUrl)" -ForegroundColor Yellow
        }
        Write-Host ""
        return $null
    }
}

function Install-Tool {
    param(
        [string]$InstallerPath,
        [string]$ToolName
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Installing: $ToolName" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Installer: $InstallerPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  The installation wizard will now open." -ForegroundColor Yellow
    Write-Host "  Please follow the installation prompts." -ForegroundColor Yellow
    Write-Host "  After installation completes, this script will continue automatically." -ForegroundColor Yellow
    Write-Host ""
    if (Test-IsInteractiveConsole) {
        Write-Host "  Press any key to start the installer..." -ForegroundColor Cyan
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } else {
        Write-Host "  [non-interactive] Starting installer automatically..." -ForegroundColor Gray
    }
    Write-Host ""
    
    try {
        Start-Process -FilePath $InstallerPath -Wait -NoNewWindow
        Write-Host ""
        Write-Host "  ✓ Installation wizard closed." -ForegroundColor Green
        Write-Host "  Verifying installation..." -ForegroundColor Gray
        Write-Host ""
        
        # Refresh PATH environment variable
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    catch {
        Write-Host ""
        Write-Host "  ✗ Error starting installer: $_" -ForegroundColor Red
        Write-Host ""
    }
}

function Ensure-RequiredTools {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Checking Required Tools" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $missingTools = @()
    $optionalMissing = @()
    
    foreach ($toolName in $script:RequiredTools.Keys) {
        $toolInfo = $script:RequiredTools[$toolName]
        Write-Host "Checking: $($toolInfo.Name)..." -ForegroundColor Cyan
        
        # Special handling for Blender - use Find-Blender function
        if ($toolName -eq "Blender") {
            $blenderPath = Find-Blender
            if ($blenderPath) {
                Write-Host "  ✓ Installed: $blenderPath" -ForegroundColor Green
                
                # Check for Vulkan startup file (required for UI on some systems)
                if (Test-BlenderVulkanStartup -BlenderExePath $blenderPath) {
                    $vulkanStartup = Get-BlenderVulkanStartupPath -BlenderExePath $blenderPath
                    Write-Host "  ✓ Vulkan startup file found: $vulkanStartup" -ForegroundColor Green
                } else {
                    Write-Host "  ⚠ Vulkan startup file (blender_startup_vulkan.cmd) not found" -ForegroundColor Yellow
                    Write-Host "    If Blender UI is blank, you may need this file." -ForegroundColor Yellow
                    Write-Host "    Location should be: $(Join-Path (Split-Path $blenderPath -Parent) 'blender_startup_vulkan.cmd')" -ForegroundColor Gray
                }
            } else {
                Write-Host "  ✗ Not found" -ForegroundColor Red
                if ($toolInfo.Required) {
                    $missingTools += @{
                        Name = $toolName
                        Info = $toolInfo
                    }
                } else {
                    $optionalMissing += @{
                        Name = $toolName
                        Info = $toolInfo
                    }
                    Write-Host "  (Optional - $($toolInfo.Note))" -ForegroundColor Gray
                }
            }
        } elseif (Test-ToolInstalled -CommandName $toolInfo.CheckCommand) {
            $toolPath = (Get-Command $toolInfo.CheckCommand).Source
            Write-Host "  ✓ Installed: $toolPath" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Not found" -ForegroundColor Red
            if ($toolInfo.Required) {
                $missingTools += @{
                    Name = $toolName
                    Info = $toolInfo
                }
            } else {
                $optionalMissing += @{
                    Name = $toolName
                    Info = $toolInfo
                }
                Write-Host "  (Optional - $($toolInfo.Note))" -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
    
    if ($missingTools.Count -eq 0 -and $optionalMissing.Count -eq 0) {
        Write-Host "All tools are available." -ForegroundColor Green
        Write-Host ""
        return $true
    }
    
    if ($missingTools.Count -gt 0) {
        Write-Host "Missing required tools:" -ForegroundColor Yellow
        foreach ($missing in $missingTools) {
            Write-Host "  - $($missing.Info.Name)" -ForegroundColor Yellow
        }
        Write-Host ""
        if ($SkipToolDownload -or -not (Test-IsInteractiveConsole)) {
            Write-Host "Non-interactive (or -SkipToolDownload): skipping tool download/install." -ForegroundColor Yellow
            Write-Host "  Install missing tools manually, or re-run interactively to be prompted." -ForegroundColor Gray
            $response = 'N'
        } else {
            Write-Host "Would you like to download and install the missing tools? (Y/N)" -ForegroundColor Cyan
            $response = Read-Host
        }
        
        if ($response -eq 'Y' -or $response -eq 'y') {
            Write-Host ""
            Write-Host "Proceeding with tool download and installation..." -ForegroundColor Green
            Write-Host ""
            
            # Create SDK directory
            if (-not (Test-Path $script:SdkPath)) {
                New-Item -ItemType Directory -Path $script:SdkPath -Force | Out-Null
            }
            
            foreach ($missing in $missingTools) {
                $toolInfo = $missing.Info
                $installerPath = Download-Tool -ToolName $missing.Name -ToolInfo $toolInfo
                
                if ($installerPath -and (Test-Path $installerPath)) {
                    Install-Tool -InstallerPath $installerPath -ToolName $toolInfo.Name
                    
                    # Verify installation
                    Start-Sleep -Seconds 2
                    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
                    
                    if (Test-ToolInstalled -CommandName $toolInfo.CheckCommand) {
                        Write-Host "  ✓ $($toolInfo.Name) installed successfully" -ForegroundColor Green
                        Write-Host ""
                    } else {
                        Write-Host "  ⚠ $($toolInfo.Name) installation verification failed" -ForegroundColor Yellow
                        Write-Host "    You may need to restart this script or your computer." -ForegroundColor Yellow
                        Write-Host "    Or add the tool to your PATH manually." -ForegroundColor Yellow
                        Write-Host ""
                    }
                }
            }
        } else {
            Write-Host ""
            Write-Host "Skipping tool installation. Some features may not work." -ForegroundColor Yellow
            Write-Host ""
            return $false
        }
    }
    
    if ($optionalMissing.Count -gt 0) {
        Write-Host "Optional tools available:" -ForegroundColor Gray
        foreach ($missing in $optionalMissing) {
            Write-Host "  - $($missing.Info.Name): $($missing.Info.Note)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    return ($missingTools.Count -eq 0)
}

# ============================================================
# REPOSITORY MANAGEMENT
# ============================================================

function Test-GitInstalled {
    return (Test-ToolInstalled -CommandName "git")
}

function Clone-ArtRepository {
    param([string]$TargetPath)
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Cloning TranscendenceArt Repository" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not (Test-GitInstalled)) {
        Write-Host "Error: Git is not installed or not in PATH" -ForegroundColor Red
        Write-Host "  Please install Git from: https://git-scm.com/" -ForegroundColor Yellow
        return $false
    }
    
    if (Test-Path $TargetPath) {
        Write-Host "Repository already exists at: $TargetPath" -ForegroundColor Green
        Write-Host "  Use -CloneRepo to force re-clone" -ForegroundColor Gray
        return $true
    }
    
    Write-Host "Cloning repository to: $TargetPath" -ForegroundColor Cyan
    Write-Host "  URL: $script:ArtRepoUrl" -ForegroundColor Gray
    Write-Host ""
    
    try {
        & git clone $script:ArtRepoUrl $TargetPath 2>&1 | ForEach-Object {
            Write-Host $_ -ForegroundColor Gray
        }
        
        if (Test-Path $TargetPath) {
            Write-Host ""
            Write-Host "✓ Repository cloned successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host ""
            Write-Host "✗ Clone failed: Repository not found" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host ""
        Write-Host "✗ Error cloning repository: $_" -ForegroundColor Red
        return $false
    }
}

# ============================================================
# ASSET DISCOVERY
# ============================================================

function Get-ArtFolders {
    param([string]$ArtRepoPath)
    
    if (-not (Test-Path $ArtRepoPath)) {
        return @()
    }
    
    $folders = Get-ChildItem -LiteralPath $ArtRepoPath -Directory -ErrorAction SilentlyContinue | 
        Where-Object { $_.Name -notmatch '^\.' } |
        Select-Object -ExpandProperty Name
    
    return $folders
}

function Get-AssetFiles {
    param(
        [string]$ArtRepoPath,
        [string]$FolderName,
        [string[]]$Extensions = @()
    )
    
    # Default extensions if none specified
    if ($Extensions.Count -eq 0) {
        $Extensions = Get-SupportedFormats
    }
    
    $folderPath = Join-Path $ArtRepoPath $FolderName
    if (-not (Test-Path $folderPath)) {
        return @()
    }
    
    $files = Get-ChildItem -LiteralPath $folderPath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $Extensions -contains $_.Extension.ToLower() }
    
    return $files
}

function Get-SupportedFormats {
    <#
    .SYNOPSIS
      Returns list of all supported file format extensions
    #>
    return @(
        # Image formats
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tga', '.tiff', '.tif', '.dds', 
        '.webp', '.ico', '.svg', '.psd', '.exr', '.hdr',
        # 3D Model formats
        '.scn', '.obj', '.fbx', '.dae', '.3ds', '.max', '.blend', '.ma', '.mb',
        '.x', '.x3d', '.ply', '.stl', '.gltf', '.glb', '.usd', '.usda', '.usdc',
        # Texture formats
        '.tex', '.dxt', '.ktx', '.astc',
        # Other
        '.mtl', '.mat', '.material'
    )
}

function Get-ImageFormats {
    return @('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tga', '.tiff', '.tif', '.dds', '.webp', '.ico', '.exr', '.hdr')
}

function Get-ModelFormats {
    return @('.scn', '.obj', '.fbx', '.dae', '.3ds', '.max', '.blend', '.ma', '.mb', '.x', '.x3d', '.ply', '.stl', '.gltf', '.glb', '.usd', '.usda', '.usdc')
}

function Get-TextureFormats {
    return @('.dds', '.tga', '.ktx', '.astc', '.tex', '.dxt')
}

# ============================================================
# IMAGE PROCESSING
# ============================================================

function Export-Images {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [string]$AssetType
    )
    
    Write-Host "Exporting images from: $SourcePath" -ForegroundColor Cyan
    
    $imageExtensions = Get-ImageFormats
    $images = Get-ChildItem -LiteralPath $SourcePath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $imageExtensions -contains $_.Extension.ToLower() }
    
    if ($images.Count -eq 0) {
        Write-Host "  No images found" -ForegroundColor Yellow
        return
    }
    
    Write-Host "  Found $($images.Count) image(s)" -ForegroundColor Gray
    
    $outputDir = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Join-Path $PSScriptRoot "ExportedAssets\$AssetType"
    } else {
        $OutputPath
    }
    
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    foreach ($image in $images) {
        $relativePath = $image.FullName.Replace($SourcePath, '').TrimStart('\', '/')
        $destPath = Join-Path $outputDir $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        Copy-Item -LiteralPath $image.FullName -Destination $destPath -Force
        Write-Host "  Copied: $relativePath" -ForegroundColor Gray
    }
    
    Write-Host "  Exported to: $outputDir" -ForegroundColor Green
}

function Export-Models {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [string]$AssetType
    )
    
    Write-Host "Exporting 3D models from: $SourcePath" -ForegroundColor Cyan
    
    $modelExtensions = Get-ModelFormats
    $models = Get-ChildItem -LiteralPath $SourcePath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $modelExtensions -contains $_.Extension.ToLower() }
    
    if ($models.Count -eq 0) {
        Write-Host "  No 3D models found" -ForegroundColor Yellow
        return
    }
    
    Write-Host "  Found $($models.Count) model file(s)" -ForegroundColor Gray
    
    $outputDir = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Join-Path $PSScriptRoot "ExportedAssets\$AssetType\Models"
    } else {
        Join-Path $OutputPath "Models"
    }
    
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    $modelInfo = @{}
    
    foreach ($model in $models) {
        $relativePath = $model.FullName.Replace($SourcePath, '').TrimStart('\', '/')
        $destPath = Join-Path $outputDir $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        Copy-Item -LiteralPath $model.FullName -Destination $destPath -Force
        
        # Track model info
        $ext = $model.Extension.ToLower()
        if (-not $modelInfo[$ext]) {
            $modelInfo[$ext] = 0
        }
        $modelInfo[$ext]++
        
        Write-Host "  Copied: $relativePath" -ForegroundColor Gray
        
        # Copy associated files (e.g., .mtl for .obj, textures)
        if ($ext -eq '.obj') {
            $mtlFile = $model.FullName -replace '\.obj$', '.mtl'
            if (Test-Path $mtlFile) {
                $mtlDest = $destPath -replace '\.obj$', '.mtl'
                Copy-Item -LiteralPath $mtlFile -Destination $mtlDest -Force
                Write-Host "    + MTL: $(Split-Path $mtlFile -Leaf)" -ForegroundColor DarkGray
            }
        }
    }
    
    Write-Host ""
    Write-Host "  Model format breakdown:" -ForegroundColor Gray
    foreach ($format in $modelInfo.Keys | Sort-Object) {
        Write-Host "    $format : $($modelInfo[$format]) file(s)" -ForegroundColor DarkGray
    }
    
    Write-Host ""
    Write-Host "  Exported to: $outputDir" -ForegroundColor Green
    
    # Create model reference guide
    $guidePath = Join-Path $outputDir "MODEL_FORMATS_GUIDE.txt"
    $guide = @"
3D Model Formats Reference Guide
=================================

This folder contains 3D model files from the TranscendenceArt repository.

Supported Formats:
"@
    
    $formatDescriptions = @{
        '.scn' = 'trueSpace scene file (original format, requires trueSpace software)'
        '.obj' = 'Wavefront OBJ (widely supported, text-based)'
        '.fbx' = 'Autodesk FBX (industry standard, binary/text)'
        '.dae' = 'COLLADA DAE (XML-based, open standard)'
        '.3ds' = '3D Studio (legacy format)'
        '.blend' = 'Blender project file'
        '.gltf' = 'glTF (modern web standard, JSON)'
        '.glb' = 'glTF Binary (compressed glTF)'
        '.ply' = 'Stanford PLY (point cloud/polygon)'
        '.stl' = 'STL (3D printing, simple)'
        '.x' = 'DirectX X file format'
        '.x3d' = 'X3D (XML-based 3D)'
        '.usd' = 'Universal Scene Description (Pixar)'
    }
    
    foreach ($format in $modelInfo.Keys | Sort-Object) {
        $desc = if ($formatDescriptions.ContainsKey($format)) { $formatDescriptions[$format] } else { "3D model format" }
        $guide += "`n  $format - $desc"
    }
    
    $guide += @"

Conversion Tools:
  - Blender (free): Supports most formats, can export to OBJ/FBX/glTF
  - MeshLab (free): Converts between formats
  - Assimp (library): For programmatic conversion

Note: trueSpace (.scn) files require the discontinued trueSpace software.
      Consider using Blender or other tools to work with converted formats.

For mod development:
  1. Use models as reference for creating 2D sprites
  2. Render models to create game-ready images
  3. Export to OBJ/glTF for use in modern tools
"@
    
    [System.IO.File]::WriteAllText($guidePath, $guide, [System.Text.UTF8Encoding]::new($false))
    Write-Host "  Created format guide: MODEL_FORMATS_GUIDE.txt" -ForegroundColor Green
}

function Export-AllAssets {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [string]$AssetType
    )
    
    Write-Host "Exporting all assets from: $SourcePath" -ForegroundColor Cyan
    Write-Host ""
    
    # Export images
    Export-Images -SourcePath $SourcePath -OutputPath $OutputPath -AssetType $AssetType
    
    Write-Host ""
    
    # Export models
    Export-Models -SourcePath $SourcePath -OutputPath $OutputPath -AssetType $AssetType
}

function Process-ModelsForFacings {
    <#
    .SYNOPSIS
      Processes 3D models to generate multiple facing sprites using Blender
    #>
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [int]$FacingCount = 120
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating Ship Facings from 3D Models" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Find Blender
    $blenderExe = Find-Blender
    if (-not $blenderExe) {
        Write-Host "Error: Blender not found. Cannot generate ship facings." -ForegroundColor Red
        Write-Host "  Install Blender from: https://www.blender.org/" -ForegroundColor Yellow
        return $false
    }
    
    # Use Vulkan startup if available
    $blenderPath = Get-BlenderVulkanStartupPath -BlenderExePath $blenderExe
    if ($blenderPath -ne $blenderExe) {
        Write-Host "Using Vulkan startup: $blenderPath" -ForegroundColor Green
    } else {
        Write-Host "Using Blender: $blenderExe" -ForegroundColor Green
        Write-Host "  Note: If UI is blank, create blender_startup_vulkan.cmd in Blender directory" -ForegroundColor Yellow
    }
    
    # Get all 3D model files
    $modelFormats = Get-ModelFormats
    $models = Get-ChildItem -LiteralPath $SourcePath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $modelFormats -contains $_.Extension.ToLower() }
    
    if ($models.Count -eq 0) {
        Write-Host "  No 3D models found in: $SourcePath" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "  Found $($models.Count) model file(s)" -ForegroundColor Gray
    Write-Host "  Target facings: $FacingCount" -ForegroundColor Gray
    Write-Host ""
    
    # Create output directory
    if (-not (Test-Path $OutputPath)) {
        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    }
    
    foreach ($model in $models) {
        Write-Host "Processing: $($model.Name)" -ForegroundColor Cyan
        
        # Generate facings using Blender
        $result = Generate-ShipSpritesFromModel -ModelPath $model.FullName -OutputPath $OutputPath -NumFacings $FacingCount -BlenderPath $blenderPath
        if ($result) {
            Write-Host "  ✓ Generated facings for $($model.Name)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed to generate facings for $($model.Name)" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    Write-Host "Ship facing generation complete: $OutputPath" -ForegroundColor Green
    return $true
}

function Generate-ShipSpritesFromModel {
    <#
    .SYNOPSIS
      Generates multiple facing sprites from a 3D model using Blender
    #>
    param(
        [string]$ModelPath,
        [string]$OutputPath,
        [int]$NumFacings = 120,
        [int]$RenderWidth = 64,
        [int]$RenderHeight = 64,
        [string]$BlenderPath = ""
    )
    
    if ([string]::IsNullOrWhiteSpace($BlenderPath)) {
        $BlenderPath = Find-Blender
        if ($BlenderPath) {
            $BlenderPath = Get-BlenderVulkanStartupPath -BlenderExePath $BlenderPath
        }
    }
    
    if (-not $BlenderPath -or -not (Test-Path $BlenderPath)) {
        Write-Host "  Error: Blender not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  Generating $NumFacings facings from: $(Split-Path $ModelPath -Leaf)" -ForegroundColor Gray
    
    # Create temporary directory for renders
    $tempRenderDir = Join-Path $env:TEMP "BlenderRenders_$(Get-Random)"
    if (-not (Test-Path $tempRenderDir)) {
        New-Item -ItemType Directory -Path $tempRenderDir -Force | Out-Null
    }
    
    try {
        # Create a Python script for Blender to render the model from multiple angles
        $pythonScript = Join-Path $tempRenderDir "render_facings.py"
        $pythonContent = @"
import bpy
import os
import math

# Clear existing mesh
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import model
model_path = r'$($ModelPath.Replace('\', '\\'))'
output_dir = r'$($tempRenderDir.Replace('\', '\\'))'

# Try to import based on file extension
ext = os.path.splitext(model_path)[1].lower()
try:
    if ext == '.obj':
        bpy.ops.wm.obj_import(filepath=model_path)
    elif ext in ['.fbx', '.dae', '.3ds']:
        bpy.ops.import_scene.`$(ext[1:])(filepath=model_path)
    elif ext == '.blend':
        bpy.ops.wm.open_mainfile(filepath=model_path)
    else:
        # Try generic import
        bpy.ops.import_scene.obj(filepath=model_path)
except:
    print(f"Warning: Could not import {model_path}, trying alternative method")
    try:
        bpy.ops.import_scene.obj(filepath=model_path)
    except:
        print(f"Error: Failed to import {model_path}")
        exit(1)

# Set up camera
bpy.ops.object.camera_add()
camera = bpy.context.active_object
camera.location = (0, -5, 0)
camera.rotation_euler = (math.radians(90), 0, 0)

# Set up lighting
bpy.ops.object.light_add(type='SUN')
light = bpy.context.active_object
light.location = (5, -5, 5)

# Set render settings
bpy.context.scene.render.resolution_x = $RenderWidth
bpy.context.scene.render.resolution_y = $RenderHeight
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.film_transparent = True

# Render from multiple angles
num_facings = $NumFacings
angle_step = 360.0 / num_facings

for i in range(num_facings):
    angle = math.radians(i * angle_step)
    # Rotate model around Z axis
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.rotation_euler[2] = angle
    
    # Render
    output_path = os.path.join(output_dir, f"facing_`{i:03d`}.png")
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)

print(f"Rendered {num_facings} facings to {output_dir}")
"@
        
        [System.IO.File]::WriteAllText($pythonScript, $pythonContent, [System.Text.UTF8Encoding]::new($false))
        
        # Run Blender with the Python script
        Write-Host "  Running Blender render script..." -ForegroundColor Gray
        
        # Use cmd.exe to run the batch file if it's a .cmd file, otherwise run directly
        if ($BlenderPath -match '\.cmd$') {
            $blenderArgs = "/c `"$BlenderPath`" --background --python `"$pythonScript`""
            $process = Start-Process -FilePath "cmd.exe" -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        } else {
            $blenderArgs = "--background --python `"$pythonScript`""
            $process = Start-Process -FilePath $BlenderPath -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        }
        
        if ($process.ExitCode -eq 0) {
            # Check if renders were created
            $renderedImages = Get-ChildItem -LiteralPath $tempRenderDir -Filter "facing_*.png" -ErrorAction SilentlyContinue
            
            if ($renderedImages.Count -gt 0) {
                Write-Host "  ✓ Rendered $($renderedImages.Count) facings" -ForegroundColor Green
                
                # Create spritesheet from rendered images
                $spritesheetName = "$(Split-Path $ModelPath -Leaf -Base)_spritesheet.png"
                $columns = [Math]::Ceiling([Math]::Sqrt($NumFacings))
                New-Spritesheet -SourcePath $tempRenderDir -OutputPath $OutputPath -OutputFileName $spritesheetName -TileWidth $RenderWidth -TileHeight $RenderHeight -Columns $columns
                
                return $true
            } else {
                Write-Host "  ✗ No rendered images found" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "  ✗ Blender render failed (exit code: $($process.ExitCode))" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Error during rendering: $_" -ForegroundColor Red
        return $false
    }
    finally {
        # Clean up temporary directory
        Remove-Item -LiteralPath $tempRenderDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function New-Spritesheet {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [int]$TileWidth = 64,
        [int]$TileHeight = 64,
        [int]$Columns = 8,
        [string]$OutputFileName = "spritesheet.png"
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating Spritesheet" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Get all images (support more formats)
    $imageFormats = Get-ImageFormats
    $images = Get-ChildItem -LiteralPath $SourcePath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $imageFormats -contains $_.Extension.ToLower() } |
        Sort-Object Name
    
    if ($images.Count -eq 0) {
        Write-Host "  No images found to create spritesheet" -ForegroundColor Yellow
        return
    }
    
    Write-Host "  Found $($images.Count) image(s)" -ForegroundColor Gray
    Write-Host "  Tile size: ${TileWidth}x${TileHeight}" -ForegroundColor Gray
    Write-Host "  Columns: $Columns" -ForegroundColor Gray
    Write-Host ""
    
    # Check if ImageMagick is available
    $magick = Get-Command "magick" -ErrorAction SilentlyContinue
    
    if ($magick) {
        Write-Host "Using ImageMagick to generate spritesheet..." -ForegroundColor Cyan
        
        $spritesheetPath = Join-Path $OutputPath $OutputFileName
        $tempDir = Join-Path $env:TEMP "TranscendenceSpritesheet_$(Get-Random)"
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        
        try {
            # Copy and resize images to temp directory
            $index = 0
            foreach ($img in $images) {
                $tempImg = Join-Path $tempDir "img_$index.png"
                & $magick $img.FullName -resize "${TileWidth}x${TileHeight}^" -gravity center -extent "${TileWidth}x${TileHeight}" $tempImg 2>&1 | Out-Null
                $index++
            }
            
            # Create montage (spritesheet)
            $rows = [Math]::Ceiling($images.Count / $Columns)
            & $magick montage "$tempDir\img_*.png" -tile ${Columns}x${rows} -geometry ${TileWidth}x${TileHeight}+0+0 -background transparent $spritesheetPath 2>&1 | Out-Null
            
            if (Test-Path $spritesheetPath) {
                Write-Host "  ✓ Spritesheet created: $spritesheetPath" -ForegroundColor Green
                
                # Create metadata file
                $metadataPath = Join-Path $OutputPath "spritesheet_metadata.txt"
                $metadata = @"
Spritesheet Metadata
====================

Source: $SourcePath
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Configuration:
  Tile Width: $TileWidth
  Tile Height: $TileHeight
  Columns: $Columns
  Rows: $rows
  Total Tiles: $($images.Count)

Image Mapping:
"@
                $tileIndex = 0
                foreach ($img in $images) {
                    $row = [Math]::Floor($tileIndex / $Columns)
                    $col = $tileIndex % $Columns
                    $metadata += "`n  Tile $tileIndex (Row $row, Col $col): $($img.Name)"
                    $tileIndex++
                }
                
                [System.IO.File]::WriteAllText($metadataPath, $metadata, [System.Text.UTF8Encoding]::new($false))
                Write-Host "  ✓ Metadata created: $metadataPath" -ForegroundColor Green
            }
        }
        finally {
            Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "ImageMagick not found. Creating manifest for manual spritesheet creation." -ForegroundColor Yellow
        Write-Host "  Install ImageMagick from: https://imagemagick.org/script/download.php" -ForegroundColor Gray
        Write-Host "  Or manually arrange images in your image editor" -ForegroundColor Gray
        Write-Host ""
        
        # Create a detailed manifest file
        $manifestPath = Join-Path $OutputPath "spritesheet_manifest.txt"
        $rows = [Math]::Ceiling($images.Count / $Columns)
        
        # Group images by format
        $imagesByFormat = $images | Group-Object { $_.Extension.ToLower() }
        
        $manifest = @"
Spritesheet Manifest
====================

Source: $SourcePath
Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Configuration:
  Tile Width: $TileWidth pixels
  Tile Height: $TileHeight pixels
  Columns: $Columns
  Rows: $rows (calculated)
  Total Images: $($images.Count)

Image Formats Found:
"@
        
        foreach ($formatGroup in $imagesByFormat) {
            $manifest += "`n  $($formatGroup.Name): $($formatGroup.Count) file(s)"
        }
        
        $manifest += @"

Instructions:
  1. Convert all images to PNG format (recommended for game compatibility)
  2. Resize all images to ${TileWidth}x${TileHeight} pixels
  3. Arrange in a grid: $Columns columns x $rows rows
  4. Save as PNG with transparency support
  5. Use the mapping below to reference tiles in your mod XML

Image Mapping (Tile Index = Row * $Columns + Column):
"@
        
        $tileIndex = 0
        foreach ($img in $images) {
            $row = [Math]::Floor($tileIndex / $Columns)
            $col = $tileIndex % $Columns
            $manifest += "`n  Tile $tileIndex (Row $row, Col $col):"
            $manifest += "`n    File: $($img.FullName)"
            $manifest += "`n    Name: $($img.Name)"
            $manifest += "`n    Format: $($img.Extension)"
            $fileSize = [math]::Round($img.Length / 1KB, 2)
            $manifest += "`n    Size: $fileSize KB"
            $tileIndex++
        }
        
        [System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))
        Write-Host "  Created manifest: $manifestPath" -ForegroundColor Green
        Write-Host "  Use this file to manually create your spritesheet" -ForegroundColor Gray
    }
}

# ============================================================
# CREDITS GENERATION
# ============================================================

function Write-CreditsFile {
    param(
        [string]$OutputPath,
        [string]$ModName = "Mod"
    )
    
    $creditsPath = Join-Path $OutputPath "CREDITS_TranscendenceArt.txt"
    
    $credits = $script:CreditsText
    $credits += "`n`nMod: $ModName`n"
    $credits += "Exported: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
    
    [System.IO.File]::WriteAllText($creditsPath, $credits, [System.Text.UTF8Encoding]::new($false))
    Write-Host "  Created credits file: $creditsPath" -ForegroundColor Green
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Transcendence Mod Asset Exporter" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check and install required tools
if (-not $SkipToolDownload) {
    $toolsOk = Ensure-RequiredTools
    if (-not $toolsOk) {
        Write-Host "Warning: Some required tools are missing. Some features may not work." -ForegroundColor Yellow
        Write-Host "  Use -SkipToolDownload to skip this check" -ForegroundColor Gray
        Write-Host ""
    }
} else {
    Write-Host "Skipping tool check (SkipToolDownload specified)" -ForegroundColor Gray
    Write-Host ""
}

# Determine Art Repository path
if ([string]::IsNullOrWhiteSpace($ArtRepoPath)) {
    $ArtRepoPath = $script:ArtRepoDefaultPath
}

$ArtRepoPath = [System.IO.Path]::GetFullPath($ArtRepoPath)

# Clone repository if needed
if ($CloneRepo -or -not (Test-Path $ArtRepoPath)) {
    $cloned = Clone-ArtRepository -TargetPath $ArtRepoPath
    if (-not $cloned) {
        Write-Host "Error: Could not access TranscendenceArt repository" -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path $ArtRepoPath)) {
    Write-Host "Error: TranscendenceArt repository not found at: $ArtRepoPath" -ForegroundColor Red
    Write-Host "  Use -CloneRepo to download it" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Art Repository: $ArtRepoPath" -ForegroundColor Green
Write-Host ""

# List available folders
Write-Host "Available asset folders:" -ForegroundColor Cyan
$folders = Get-ArtFolders -ArtRepoPath $ArtRepoPath
foreach ($folder in $folders | Sort-Object) {
    Write-Host "  - $folder" -ForegroundColor Gray
}
Write-Host ""

# Determine output path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $PSScriptRoot "ExportedAssets"
}

$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)

if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

Write-Host "Output directory: $OutputPath" -ForegroundColor Green
Write-Host ""

# Process assets
if (-not [string]::IsNullOrWhiteSpace($SourceFolder)) {
    # Process specific folder
    $sourcePath = Join-Path $ArtRepoPath $SourceFolder
    if (Test-Path $sourcePath) {
        if ($ExportAll) {
            Export-AllAssets -SourcePath $sourcePath -OutputPath $OutputPath -AssetType $SourceFolder
        } elseif ($ExportModels) {
            Export-Models -SourcePath $sourcePath -OutputPath $OutputPath -AssetType $SourceFolder
            Export-Images -SourcePath $sourcePath -OutputPath $OutputPath -AssetType $SourceFolder
        } else {
            Export-Images -SourcePath $sourcePath -OutputPath $OutputPath -AssetType $SourceFolder
        }
        
        if ($GenerateSpritesheet) {
            New-Spritesheet -SourcePath $sourcePath -OutputPath $OutputPath -TileWidth $TileWidth -TileHeight $TileHeight -Columns $Columns
        }
        
        if ($GenerateShipFacings) {
            Process-ModelsForFacings -SourcePath $sourcePath -OutputPath (Join-Path $OutputPath "ShipFacings") -FacingCount $FacingCount
        }
    } else {
        Write-Host "Error: Folder not found: $SourceFolder" -ForegroundColor Red
        exit 1
    }
} else {
    # Process based on asset type
    $foldersToProcess = @()
    
    switch ($AssetType) {
        "Ship" {
            $foldersToProcess = $folders | Where-Object { $_ -match "Fleet|Ships|Commonwealth|Corporate" }
        }
        "Item" {
            $foldersToProcess = $folders | Where-Object { $_ -eq "Items" }
        }
        "Projectile" {
            $foldersToProcess = $folders | Where-Object { $_ -match "Projectile|Weapon" }
        }
        "All" {
            $foldersToProcess = $folders
        }
    }
    
    foreach ($folder in $foldersToProcess) {
        Write-Host "Processing: $folder" -ForegroundColor Cyan
        $sourcePath = Join-Path $ArtRepoPath $folder
        $folderOutput = Join-Path $OutputPath $folder
        
        if ($ExportAll) {
            Export-AllAssets -SourcePath $sourcePath -OutputPath $folderOutput -AssetType $folder
        } elseif ($ExportModels) {
            Export-Models -SourcePath $sourcePath -OutputPath $folderOutput -AssetType $folder
            Export-Images -SourcePath $sourcePath -OutputPath $folderOutput -AssetType $folder
        } else {
            Export-Images -SourcePath $sourcePath -OutputPath $folderOutput -AssetType $folder
        }
        Write-Host ""
    }
}

# Generate credits file
if ($IncludeCredits) {
    Write-Host "Generating credits file..." -ForegroundColor Cyan
    Write-CreditsFile -OutputPath $OutputPath
    Write-Host ""
}

# Generate format summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Supported Formats" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image Formats:" -ForegroundColor Yellow
Write-Host "  $(($(Get-ImageFormats) -join ', '))" -ForegroundColor Gray
Write-Host ""
Write-Host "3D Model Formats:" -ForegroundColor Yellow
Write-Host "  $(($(Get-ModelFormats) -join ', '))" -ForegroundColor Gray
Write-Host ""
Write-Host "Texture Formats:" -ForegroundColor Yellow
Write-Host "  $(($(Get-TextureFormats) -join ', '))" -ForegroundColor Gray
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Export Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Exported assets: $OutputPath" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review exported images and models" -ForegroundColor White
Write-Host "  2. Convert models to game-compatible formats (OBJ, glTF)" -ForegroundColor White
Write-Host "  3. Render models to create 2D sprites for the game" -ForegroundColor White
Write-Host "  4. Process/convert images to game-compatible formats" -ForegroundColor White
Write-Host "  5. Create spritesheets if needed" -ForegroundColor White
Write-Host "  6. Add to your mod's Resources folder" -ForegroundColor White
Write-Host "  7. Reference assets in your mod XML" -ForegroundColor White
Write-Host ""
Write-Host "Conversion Tools:" -ForegroundColor Yellow
Write-Host "  - Blender (free): https://www.blender.org/" -ForegroundColor Gray
Write-Host "  - MeshLab (free): http://www.meshlab.net/" -ForegroundColor Gray
Write-Host "  - ImageMagick: https://imagemagick.org/ (for spritesheets)" -ForegroundColor Gray
Write-Host ""

