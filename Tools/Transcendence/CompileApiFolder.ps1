<#
.SYNOPSIS
    Compiles a Transcendence API folder with automatic SDK download and setup.

.DESCRIPTION
    This script compiles a Transcendence API folder (e.g., TranscendenceDev-integration-API59).
    It automatically detects required SDKs, downloads them if missing, and compiles the project.
    
    Supports drag-and-drop: Drop an API folder onto this script or its .bat wrapper.

.PARAMETER ApiFolderPath
    Path to the API folder to compile (e.g., TranscendenceDev-integration-API59)

.PARAMETER SdkPath
    Path to SDK resources folder (default: $PSScriptRoot\SDK)

.PARAMETER VisualStudioPath
    Path to Visual Studio installation (auto-detected if not specified)

.PARAMETER BuildConfiguration
    Build configuration: Debug, Release, or Both (default: Release)

.PARAMETER SkipSdkDownload
    Skip SDK download and use existing SDKs only

.EXAMPLE
    .\CompileApiFolder.ps1 -ApiFolderPath "D:\path\to\TranscendenceDev-integration-API59"

.EXAMPLE
    .\CompileApiFolder.ps1 "D:\path\to\TranscendenceDev-integration-API59"

.EXAMPLE
    .\CompileApiFolder.ps1 "D:\path\to\API59" -UseVS2026
    # Use VS 2026 when project officially moves to C++20
#>

[CmdletBinding()]
param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string]$ApiFolderPath,
    
    [string]$SdkPath = "",
    
    [string]$VisualStudioPath = "",
    
    [ValidateSet("Debug", "Release", "Both")]
    [string]$BuildConfiguration = "Release",
    
    [switch]$SkipSdkDownload,
    
    [switch]$NonInteractive,
    
    [switch]$RetargetSolution,
    
    [switch]$UseVisualStudioIDE,  # Build using Visual Studio IDE (devenv.exe) instead of MSBuild
    
    [switch]$UseVS2026  # Use Visual Studio 2026 (for C++20 support) instead of default VS 2022
)

# ============================================================
# CONFIGURATION
# ============================================================

$ErrorActionPreference = "Stop"

function Test-IsInteractiveConsole {
    try {
        if (-not [Environment]::UserInteractive) { return $false }
        if ([Console]::IsInputRedirected) { return $false }
        return $true
    } catch { return $false }
}

# Auto-enable non-interactive behaviour when there is no console to prompt on,
# so the build never hangs on a Read-Host during unattended/CI runs.
if (-not $NonInteractive -and -not (Test-IsInteractiveConsole)) {
    Write-Host "No interactive console detected; running in non-interactive mode (SDK prompts skipped)." -ForegroundColor Yellow
    $NonInteractive = $true
}

# Configuration file path
$configFile = Join-Path $PSScriptRoot "CompileApiFolder.config.json"

# Load configuration if it exists
$script:Config = @{
    SdkPath = Join-Path $PSScriptRoot "SDK"
    VisualStudioPath = ""
    KnownSdkLocations = @{}
}

if (Test-Path $configFile) {
    try {
        $loadedConfig = Get-Content $configFile -Raw | ConvertFrom-Json
        if ($loadedConfig.SdkPath) { $script:Config.SdkPath = $loadedConfig.SdkPath }
        if ($loadedConfig.VisualStudioPath) { $script:Config.VisualStudioPath = $loadedConfig.VisualStudioPath }
        if ($loadedConfig.KnownSdkLocations) {
            $script:Config.KnownSdkLocations = @{}
            $loadedConfig.KnownSdkLocations.PSObject.Properties | ForEach-Object {
                $script:Config.KnownSdkLocations[$_.Name] = $_.Value
            }
        }
        Write-Host "Loaded configuration from: $configFile" -ForegroundColor Gray
    }
    catch {
        Write-Host "Warning: Could not load configuration file: $_" -ForegroundColor Yellow
    }
}

# Default SDK path (use config or default)
if ([string]::IsNullOrWhiteSpace($SdkPath)) {
    $SdkPath = $script:Config.SdkPath
}

# Use config Visual Studio path if not provided
if ([string]::IsNullOrWhiteSpace($VisualStudioPath) -and -not [string]::IsNullOrWhiteSpace($script:Config.VisualStudioPath)) {
    $VisualStudioPath = $script:Config.VisualStudioPath
}

# SDK download URLs and requirements
$script:SdkRequirements = @{
    "DirectXSDK" = @{
        Name = "DirectX SDK (June 2010)"
        Url = ""  # No longer available - Microsoft removed download (end-of-life)
        Installer = "DXSDK_Jun10.exe"
        RequiredPath = "C:\Program Files (x86)\Microsoft DirectX SDK (June 2010)"
        CheckPath = "C:\Program Files (x86)\Microsoft DirectX SDK (June 2010)\Include"
        Optional = $true  # Made optional - Windows SDK includes DirectX headers
        DetectionMethod = "MultiplePaths"  # Uses enhanced detection
        Note = "END-OF-LIFE: No longer available for download. Use Windows SDK (included with Visual Studio) instead - it includes DirectX headers."
    }
    "WindowsSDK" = @{
        Name = "Windows SDK"
        Url = ""
        RequiredPath = ""
        CheckPath = ""
        Optional = $true
        Note = "Usually included with Visual Studio"
        DetectionMethod = "VisualStudioAndRegistry"  # Uses enhanced detection
    }
}

# ============================================================
# DRAG-AND-DROP SUPPORT
# ============================================================

if ([string]::IsNullOrWhiteSpace($ApiFolderPath) -and $args.Count -gt 0) {
    $ApiFolderPath = $args[0].Trim('"', "'")
    Write-Host ""
    Write-Host "  DRAG-AND-DROP DETECTED" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dropped path: $ApiFolderPath" -ForegroundColor Gray
    Write-Host ""
}

# ============================================================
# VALIDATION
# ============================================================

if ([string]::IsNullOrWhiteSpace($ApiFolderPath)) {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Compile API Folder" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\CompileApiFolder.ps1 -ApiFolderPath <path>" -ForegroundColor White
    Write-Host "  Or drag-and-drop an API folder onto this script" -ForegroundColor White
    Write-Host ""
    Write-Host "Example:" -ForegroundColor Yellow
    Write-Host "  .\CompileApiFolder.ps1 -ApiFolderPath `"D:\path\to\TranscendenceDev-integration-API59`"" -ForegroundColor White
    Write-Host ""
    exit 1
}

$ApiFolderPath = [System.IO.Path]::GetFullPath($ApiFolderPath)

if (-not (Test-Path $ApiFolderPath -PathType Container)) {
    Write-Host "Error: API folder not found: $ApiFolderPath" -ForegroundColor Red
    exit 1
}

# Detect API version from folder name
$folderName = Split-Path $ApiFolderPath -Leaf
$apiVersion = 0
if ($folderName -match 'API(\d+)') {
    $apiVersion = [int]$matches[1]
    Write-Host "Detected API version: $apiVersion" -ForegroundColor Green
} else {
    Write-Host "Warning: Could not detect API version from folder name" -ForegroundColor Yellow
}

# ============================================================
# SDK MANAGEMENT
# ============================================================

function Test-SdkInstalled {
    param([hashtable]$SdkInfo)
    
    # Check known locations from config first
    $sdkName = $SdkInfo.Name
    if ($script:Config.KnownSdkLocations.ContainsKey($sdkName)) {
        $knownPath = $script:Config.KnownSdkLocations[$sdkName]
        if (Test-Path $knownPath) {
            Write-Host "  ✓ Found in configured location: $knownPath" -ForegroundColor Green
            return $true
        }
    }
    
    # DirectX SDK detection - check multiple locations
    if ($sdkName -eq "DirectXSDK" -or $SdkInfo.Name -like "*DirectX*") {
        $directXPaths = @(
            "C:\Program Files (x86)\Microsoft DirectX SDK (June 2010)\Include",
            "C:\Program Files\Microsoft DirectX SDK (June 2010)\Include",
            "D:\Program Files (x86)\Microsoft DirectX SDK (June 2010)\Include",
            "D:\Program Files\Microsoft DirectX SDK (June 2010)\Include",
            "C:\Program Files (x86)\Microsoft DirectX SDK\Include",
            "C:\Program Files\Microsoft DirectX SDK\Include"
        )
        
        # Also check for d3dx9.h or d3d9.h in Include folder
        foreach ($path in $directXPaths) {
            if (Test-Path $path) {
                $headerFile = Join-Path $path "d3dx9.h"
                if (Test-Path $headerFile) {
                    Write-Host "  ✓ Found DirectX SDK at: $path" -ForegroundColor Green
                    return $true
                }
            }
        }
        
        # Check registry for DirectX SDK path
        try {
            $regPath = "HKLM:\SOFTWARE\Microsoft\DirectX"
            if (Test-Path $regPath) {
                $dxPath = (Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue).InstallPath
                if ($dxPath -and (Test-Path (Join-Path $dxPath "Include"))) {
                    Write-Host "  ✓ Found DirectX SDK via registry: $dxPath" -ForegroundColor Green
                    return $true
                }
            }
        } catch {
            # Registry check failed, continue
        }
        
        # Check environment variable
        $dxEnv = $env:DXSDK_DIR
        if ($dxEnv -and (Test-Path (Join-Path $dxEnv "Include"))) {
            Write-Host "  ✓ Found DirectX SDK via DXSDK_DIR: $dxEnv" -ForegroundColor Green
            return $true
        }
        
        # Check for DirectX headers in Windows SDK (modern alternative)
        # Windows SDK includes DirectX headers since Windows 8 SDK
        $windowsKitsPaths = @(
            "${env:ProgramFiles(x86)}\Windows Kits\10\Include",
            "${env:ProgramFiles}\Windows Kits\10\Include",
            "D:\Program Files (x86)\Windows Kits\10\Include",
            "D:\Program Files\Windows Kits\10\Include"
        )
        
        foreach ($kitsPath in $windowsKitsPaths) {
            if (Test-Path $kitsPath) {
                # Check for DirectX headers in Windows SDK
                $sdkVersions = Get-ChildItem -Path $kitsPath -Directory -ErrorAction SilentlyContinue | 
                    Where-Object { $_.Name -match "^\d+\.\d+" } | 
                    Sort-Object { [Version]$_.Name } -Descending
                
                foreach ($sdkVersion in $sdkVersions) {
                    $dxHeaderPath = Join-Path $sdkVersion.FullName "um\d3d9.h"
                    if (Test-Path $dxHeaderPath) {
                        Write-Host "  ✓ Found DirectX headers in Windows SDK $($sdkVersion.Name) at: $($sdkVersion.FullName)" -ForegroundColor Green
                        Write-Host "    (Modern alternative to DirectX SDK June 2010)" -ForegroundColor Gray
                        return $true
                    }
                }
            }
        }
        
        return $false
    }
    
    # Windows SDK detection - check Visual Studio installations
    if ($sdkName -eq "WindowsSDK" -or $SdkInfo.Name -like "*Windows SDK*") {
        # Check Visual Studio installations
        $vsPaths = @(
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio",
            "${env:ProgramFiles}\Microsoft Visual Studio",
            "D:\Program Files (x86)\Microsoft Visual Studio",
            "D:\Program Files\Microsoft Visual Studio"
        )
        
        foreach ($vsBase in $vsPaths) {
            if (Test-Path $vsBase) {
                # Check for Windows SDK in Visual Studio installations
                $vsVersions = Get-ChildItem -Path $vsBase -Directory -ErrorAction SilentlyContinue | 
                    Where-Object { $_.Name -match "^\d{4}" }
                
                foreach ($vsVersion in $vsVersions) {
                    $sdkPath = Join-Path $vsVersion.FullName "Windows Kits\10\Include"
                    if (Test-Path $sdkPath) {
                        $sdkVersions = Get-ChildItem -Path $sdkPath -Directory -ErrorAction SilentlyContinue | 
                            Where-Object { $_.Name -match "^\d+\.\d+" } | 
                            Sort-Object { [Version]$_.Name } -Descending
                        if ($sdkVersions) {
                            $latestSdk = $sdkVersions[0]
                            Write-Host "  ✓ Found Windows SDK $($latestSdk.Name) at: $($latestSdk.FullName)" -ForegroundColor Green
                            return $true
                        }
                    }
                }
            }
        }
        
        # Check Program Files for Windows Kits
        $windowsKitsPaths = @(
            "${env:ProgramFiles(x86)}\Windows Kits\10\Include",
            "${env:ProgramFiles}\Windows Kits\10\Include",
            "D:\Program Files (x86)\Windows Kits\10\Include",
            "D:\Program Files\Windows Kits\10\Include"
        )
        
        foreach ($kitsPath in $windowsKitsPaths) {
            if (Test-Path $kitsPath) {
                $sdkVersions = Get-ChildItem -Path $kitsPath -Directory -ErrorAction SilentlyContinue | 
                    Where-Object { $_.Name -match "^\d+\.\d+" } | 
                    Sort-Object { [Version]$_.Name } -Descending
                if ($sdkVersions) {
                    $latestSdk = $sdkVersions[0]
                    Write-Host "  ✓ Found Windows SDK $($latestSdk.Name) at: $($latestSdk.FullName)" -ForegroundColor Green
                    return $true
                }
            }
        }
        
        # Check registry for Windows SDK
        try {
            $regPath = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Kits\Installed Roots"
            if (Test-Path $regPath) {
                $kitsRoot = (Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue).KitsRoot10
                if ($kitsRoot -and (Test-Path (Join-Path $kitsRoot "Include"))) {
                    Write-Host "  ✓ Found Windows SDK via registry: $kitsRoot" -ForegroundColor Green
                    return $true
                }
            }
        } catch {
            # Registry check failed, continue
        }
        
        return $false
    }
    
    # Check default location for other SDKs
    if ([string]::IsNullOrWhiteSpace($SdkInfo.CheckPath)) {
        return $false
    }
    
    if (Test-Path $SdkInfo.CheckPath) {
        Write-Host "  ✓ Found at: $($SdkInfo.CheckPath)" -ForegroundColor Green
        return $true
    }
    
    return $false
}

function Get-SdkDownloadPath {
    param([hashtable]$SdkInfo)
    
    if (-not (Test-Path $SdkPath)) {
        New-Item -ItemType Directory -Path $SdkPath -Force | Out-Null
    }
    
    return Join-Path $SdkPath $SdkInfo.Installer
}

function Download-Sdk {
    param(
        [string]$SdkName,
        [hashtable]$SdkInfo
    )
    
    Write-Host "Downloading $($SdkInfo.Name)..." -ForegroundColor Cyan
    Write-Host "  URL: $($SdkInfo.Url)" -ForegroundColor Gray
    
    $downloadPath = Get-SdkDownloadPath -SdkInfo $SdkInfo
    
    try {
        # Check if already downloaded
        if (Test-Path $downloadPath) {
            Write-Host "  Already downloaded: $downloadPath" -ForegroundColor Green
            return $downloadPath
        }
        
        # Download using Invoke-WebRequest
        Write-Host "  Downloading to: $downloadPath" -ForegroundColor Gray
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $SdkInfo.Url -OutFile $downloadPath -UseBasicParsing
        
        Write-Host "  Download complete" -ForegroundColor Green
        return $downloadPath
    }
    catch {
        Write-Host "  Error downloading SDK: $_" -ForegroundColor Red
        return $null
    }
}

function Install-Sdk {
    param(
        [string]$InstallerPath,
        [string]$SdkName
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Installing: $SdkName" -ForegroundColor Cyan
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
    }
    catch {
        Write-Host ""
        Write-Host "  ✗ Error starting installer: $_" -ForegroundColor Red
        Write-Host ""
    }
}

function Ensure-Sdks {
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Checking SDK Requirements" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $missingSdks = @()
    
    foreach ($sdkName in $script:SdkRequirements.Keys) {
        $sdkInfo = $script:SdkRequirements[$sdkName]
        Write-Host "Checking: $($sdkInfo.Name)..." -ForegroundColor Cyan
        
        $isInstalled = Test-SdkInstalled -SdkInfo $sdkInfo
        
        if (-not $isInstalled) {
            Write-Host "  ✗ Not found" -ForegroundColor Red
            if (-not $sdkInfo.Optional) {
                $missingSdks += @{
                    Name = $sdkName
                    Info = $sdkInfo
                }
            } else {
                Write-Host "  (Optional - $($sdkInfo.Note))" -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
    
    if ($missingSdks.Count -eq 0) {
        Write-Host "All required SDKs are installed." -ForegroundColor Green
        Write-Host ""
        return $true
    }
    
    if ($SkipSdkDownload) {
        Write-Host "Skipping SDK download (SkipSdkDownload specified)" -ForegroundColor Yellow
        Write-Host "Missing SDKs:" -ForegroundColor Yellow
        foreach ($missing in $missingSdks) {
            Write-Host "  - $($missing.Info.Name)" -ForegroundColor Yellow
        }
        Write-Host ""
        return $false
    }
    
    # Auto-download with user confirmation (or skip if non-interactive)
    Write-Host ""
    Write-Host "Missing required SDKs detected:" -ForegroundColor Yellow
    foreach ($missing in $missingSdks) {
        Write-Host "  - $($missing.Info.Name)" -ForegroundColor Yellow
        if ($missing.Info.Url) {
            Write-Host "    Download URL: $($missing.Info.Url)" -ForegroundColor Gray
        } elseif ($missing.Info.Name -like "*DirectX*") {
            Write-Host "    ⚠️  DirectX SDK is END-OF-LIFE and no longer available for download" -ForegroundColor Red
            Write-Host "    ✓ Use Windows SDK instead (included with Visual Studio)" -ForegroundColor Green
            Write-Host "    ✓ Windows SDK includes DirectX headers - no separate install needed" -ForegroundColor Green
        }
        if ($missing.Info.Note) {
            Write-Host "    Note: $($missing.Info.Note)" -ForegroundColor Gray
        }
    }
    Write-Host ""
    
    if ($NonInteractive) {
        Write-Host "Non-interactive mode: Skipping SDK download." -ForegroundColor Yellow
        Write-Host "  Use -SkipSdkDownload to suppress this message, or install SDKs manually." -ForegroundColor Gray
        Write-Host ""
        return $false
    }
    
    Write-Host "Would you like to download and install the missing SDKs? (Y/N)" -ForegroundColor Cyan
    Write-Host "  (You can skip this with -SkipSdkDownload if SDKs are already installed)" -ForegroundColor Gray
    Write-Host "  (Use -NonInteractive to skip prompts)" -ForegroundColor Gray
    $response = Read-Host
    
    if ($response -ne 'Y' -and $response -ne 'y') {
        Write-Host ""
        Write-Host "Skipping SDK download. Build may fail without required SDKs." -ForegroundColor Yellow
        Write-Host ""
        return $false
    }
    
    Write-Host ""
    Write-Host "Proceeding with SDK download and installation..." -ForegroundColor Green
    Write-Host ""
    
    # Create SDK directory
    if (-not (Test-Path $SdkPath)) {
        New-Item -ItemType Directory -Path $SdkPath -Force | Out-Null
        Write-Host "Created SDK directory: $SdkPath" -ForegroundColor Green
    }
    
    foreach ($missing in $missingSdks) {
        $sdkInfo = $missing.Info
        
        if ([string]::IsNullOrWhiteSpace($sdkInfo.Url)) {
            Write-Host "  No download URL available for $($sdkInfo.Name)" -ForegroundColor Yellow
            Write-Host "  Please install manually from: $($sdkInfo.RequiredPath)" -ForegroundColor Yellow
            continue
        }
        
        $installerPath = Download-Sdk -SdkName $missing.Name -SdkInfo $sdkInfo
        
        if ($installerPath -and (Test-Path $installerPath)) {
            Install-Sdk -InstallerPath $installerPath -SdkName $sdkInfo.Name
            
            # Verify installation
            if (Test-SdkInstalled -SdkInfo $sdkInfo) {
                Write-Host "  ✓ $($sdkInfo.Name) installed successfully" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $($sdkInfo.Name) installation may have failed" -ForegroundColor Red
                Write-Host "    Please verify installation at: $($sdkInfo.RequiredPath)" -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host ""
    return $true
}

# ============================================================
# VISUAL STUDIO DETECTION
# ============================================================

function Find-VisualStudio {
    Write-Host "Detecting Visual Studio..." -ForegroundColor Cyan
    
    # Check if path was provided by user (highest priority)
    if (-not [string]::IsNullOrWhiteSpace($VisualStudioPath)) {
        $providedPath = $VisualStudioPath.Trim()
        
        # If user provided devenv.exe path, extract the VS root
        if ($providedPath -match '(.+)\\Common7\\IDE\\devenv\.exe$') {
            $providedPath = $matches[1]
        }
        
        if (Test-Path $providedPath) {
            Write-Host "  Using user-specified path: $providedPath" -ForegroundColor Green
            return $providedPath
        } else {
            Write-Host "  Warning: Provided path not found: $providedPath" -ForegroundColor Yellow
        }
    }
    
    # Check environment variables (set by Visual Studio Developer Command Prompt)
    if ($env:VSINSTALLDIR) {
        $vsPath = $env:VSINSTALLDIR.TrimEnd('\', '/')
        if (Test-Path $vsPath) {
            Write-Host "  Found via VSINSTALLDIR: $vsPath" -ForegroundColor Green
            return $vsPath
        }
    }
    
    if ($env:VCINSTALLDIR) {
        # VCINSTALLDIR is usually under VSINSTALLDIR, extract parent
        $vsPath = Split-Path (Split-Path $env:VCINSTALLDIR -Parent) -Parent
        if (Test-Path $vsPath) {
            Write-Host "  Found via VCINSTALLDIR: $vsPath" -ForegroundColor Green
            return $vsPath
        }
    }
    
    # Try vswhere first (Visual Studio Installer tool)
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        try {
            # Check if VS 2026 toggle is enabled (for C++20 support)
            if ($script:UseVS2026) {
                # First, try to find VS 2026 specifically (version 19.x) - for C++20 support
                $vs2026Json = & $vswhere -products * -version "[19.0,20.0)" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath,installationVersion -format json 2>$null
                if ($vs2026Json) {
                    try {
                        $vs2026Installations = $vs2026Json | ConvertFrom-Json
                        if ($vs2026Installations -and ($vs2026Installations | Measure-Object).Count -gt 0) {
                            $installations = if ($vs2026Installations -is [System.Array]) { $vs2026Installations } else { @($vs2026Installations) }
                            if ($installations.Count -gt 0) {
                                $sorted = $installations | Sort-Object { 
                                    try { [Version]$_.installationVersion } catch { [Version]"0.0.0.0" }
                                } -Descending
                                
                                $vsPath = $sorted[0].installationPath
                                if ($vsPath) {
                                    $vsPath = $vsPath.ToString().Trim()
                                    if ($vsPath -and (Test-Path $vsPath)) {
                                        Write-Host "  Found Visual Studio 2026 (for C++20 support): $vsPath" -ForegroundColor Green
                                        Write-Host "    Version: $($sorted[0].installationVersion)" -ForegroundColor Gray
                                        return $vsPath
                                    }
                                }
                            }
                        }
                    } catch {
                        # Continue to fallback
                    }
                }
            }
            
            # Default: Try to find VS 2022 specifically (version 17.x) - default until project officially moves to C++20
            $vs2022Json = & $vswhere -products * -version "[17.0,18.0)" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath,installationVersion -format json 2>$null
            if ($vs2022Json) {
                try {
                    $vs2022Installations = $vs2022Json | ConvertFrom-Json
                    if ($vs2022Installations -and ($vs2022Installations | Measure-Object).Count -gt 0) {
                        $installations = if ($vs2022Installations -is [System.Array]) { $vs2022Installations } else { @($vs2022Installations) }
                        if ($installations.Count -gt 0) {
                            # Sort by version (highest first) and take the first VS 2022
                            $sorted = $installations | Sort-Object { 
                                try { [Version]$_.installationVersion } catch { [Version]"0.0.0.0" }
                            } -Descending
                            
                            $vsPath = $sorted[0].installationPath
                            if ($vsPath) {
                                $vsPath = $vsPath.ToString().Trim()
                                if ($vsPath -and (Test-Path $vsPath)) {
                                    Write-Host "  Found Visual Studio 2022 (default for pre-C++20 support): $vsPath" -ForegroundColor Green
                                    Write-Host "    Version: $($sorted[0].installationVersion)" -ForegroundColor Gray
                                    Write-Host "    Note: Using VS 2022 by default until project officially moves to C++20" -ForegroundColor Gray
                                    return $vsPath
                                }
                            }
                        }
                    }
                } catch {
                    # Continue to fallback
                }
            }
            
            # Fallback: Get all installations, sorted by version (highest first)
            # Prioritize VS 2022 (version 17.x) and later
            $vsInstallationsJson = & $vswhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath,installationVersion -format json 2>$null
            
            if ($vsInstallationsJson) {
                try {
                    $vsInstallations = $vsInstallationsJson | ConvertFrom-Json
                    
                    if ($vsInstallations -and ($vsInstallations | Measure-Object).Count -gt 0) {
                        # Handle single object or array
                        $installations = if ($vsInstallations -is [System.Array]) { $vsInstallations } else { @($vsInstallations) }
                        
                        # Sort by version (highest first), prioritizing VS 2022+ (17.x+)
                        $sorted = $installations | Sort-Object { 
                            try { 
                                $ver = [Version]$_.installationVersion
                                # Prioritize VS 2022+ (version 17.x) - add 1000 to make them sort first
                                if ($ver.Major -ge 17) { 
                                    [Version]::new($ver.Major + 1000, $ver.Minor, $ver.Build, $ver.Revision)
                                } else {
                                    $ver
                                }
                            } catch { [Version]"0.0.0.0" }
                        } -Descending
                        
                        $vsPath = $sorted[0].installationPath
                        if ($vsPath) {
                            $vsPath = $vsPath.ToString().Trim()
                            if ($vsPath -and (Test-Path $vsPath)) {
                                Write-Host "  Found via vswhere (highest version): $vsPath" -ForegroundColor Green
                                Write-Host "    Version: $($sorted[0].installationVersion)" -ForegroundColor Gray
                                return $vsPath
                            }
                        }
                    }
                }
                catch {
                    Write-Host "  Could not parse vswhere JSON output: $_" -ForegroundColor Yellow
                }
            }
            
            # Fallback: use -latest flag (only capture stdout, not stderr)
            try {
                $vsPathOutput = & $vswhere -latest -property installationPath 2>$null
                if ($vsPathOutput) {
                    # Handle array output (take first result) and convert to string
                    $vsPath = if ($vsPathOutput -is [System.Array]) { 
                        $vsPathOutput[0].ToString().Trim()
                    } else { 
                        $vsPathOutput.ToString().Trim()
                    }
                    
                    # Remove any error messages and validate path
                    if ($vsPath -and -not $vsPath.StartsWith("Error") -and $vsPath.Length -gt 0 -and (Test-Path $vsPath)) {
                        Write-Host "  Found via vswhere (latest): $vsPath" -ForegroundColor Green
                        return $vsPath
                    }
                }
            }
            catch {
                Write-Host "  vswhere -latest failed: $_" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "  vswhere execution failed: $_" -ForegroundColor Yellow
        }
    }
    
    # Fallback: Try common installation paths
    if ($script:UseVS2026) {
        # Prioritize VS 2026 for C++20 support
        $vsPaths = @(
            "${env:ProgramFiles}\Microsoft Visual Studio\2026\Enterprise",
            "${env:ProgramFiles}\Microsoft Visual Studio\2026\Professional",
            "${env:ProgramFiles}\Microsoft Visual Studio\2026\Community",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2026\Enterprise",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2026\Professional",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2026\Community",
            "D:\tools\Microsoft Visual Studio\18\Community",  # User's known location
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise",
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional",
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community"
        )
    } else {
        # Default: Prioritize VS 2022 for pre-C++20 support
        $vsPaths = @(
            "D:\tools\Microsoft Visual Studio\18\Community",  # User's known location
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise",
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional",
            "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Enterprise",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Professional",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Community",
            "${env:ProgramFiles}\Microsoft Visual Studio\2019\Enterprise",
            "${env:ProgramFiles}\Microsoft Visual Studio\2019\Professional",
            "${env:ProgramFiles}\Microsoft Visual Studio\2019\Community",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Enterprise",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Professional",
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Community"
        )
    }
    
    foreach ($path in $vsPaths) {
        if (Test-Path $path) {
            Write-Host "  Found: $path" -ForegroundColor Green
            return $path
        }
    }
    
    Write-Host "  Visual Studio not found automatically" -ForegroundColor Yellow
    return $null
}

function Get-MSBuildPath {
    param([string]$VisualStudioPath)
    
    # First, check if MSBuild is in PATH (easiest)
    $msbuildInPath = Get-Command "MSBuild.exe" -ErrorAction SilentlyContinue
    if ($msbuildInPath) {
        $msbuildPath = $msbuildInPath.Source
        Write-Host "  Found MSBuild in PATH: $msbuildPath" -ForegroundColor Green
        return $msbuildPath
    }
    
    # Check MSBuild environment variable
    if ($env:MSBUILD_PATH) {
        if (Test-Path $env:MSBUILD_PATH) {
            Write-Host "  Found MSBuild via MSBUILD_PATH: $env:MSBUILD_PATH" -ForegroundColor Green
            return $env:MSBUILD_PATH
        }
    }
    
    # Convert parameter to string explicitly (handle any type)
    $vsPathString = ""
    if ($null -eq $VisualStudioPath) {
        return $null
    }
    elseif ($VisualStudioPath -is [System.Array]) {
        $vsPathString = $VisualStudioPath[0].ToString().Trim()
    }
    elseif ($VisualStudioPath -is [PSCustomObject]) {
        $vsPathString = $VisualStudioPath.ToString().Trim()
    }
    else {
        $vsPathString = [string]$VisualStudioPath
        $vsPathString = $vsPathString.Trim()
    }
    
    if ([string]::IsNullOrWhiteSpace($vsPathString)) {
        return $null
    }
    
    # Ensure it's a valid path string
    $vsPathString = $vsPathString -replace "`0", "" -replace "`r", "" -replace "`n", ""
    
    Write-Host "  Looking for MSBuild in: $vsPathString" -ForegroundColor Gray
    
    # Try different MSBuild locations
    $msbuildPaths = @(
        "$vsPathString\MSBuild\Current\Bin\MSBuild.exe",
        "$vsPathString\MSBuild\15.0\Bin\MSBuild.exe",
        "$vsPathString\MSBuild\14.0\Bin\MSBuild.exe"
    )
    
    foreach ($path in $msbuildPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

function Get-BestAvailableToolset {
    param([string]$VisualStudioPath, [string]$MsBuildPath)
    
    if ([string]::IsNullOrWhiteSpace($VisualStudioPath) -or [string]::IsNullOrWhiteSpace($MsBuildPath)) {
        return $null
    }
    
    Write-Host "  Detecting available platform toolsets..." -ForegroundColor Gray
    
    # Try to query MSBuild for available toolsets by actually testing them
    # Create a minimal test project file to query available toolsets
    $tempDir = [System.IO.Path]::GetTempPath()
    $testProjFile = Join-Path $tempDir "ToolsetDetection_$([Guid]::NewGuid().ToString('N').Substring(0,8)).vcxproj"
    
    try {
        # Create a minimal vcxproj file
        $testProjContent = @"
<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Release|Win32">
      <Configuration>Release</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <ProjectGuid>{00000000-0000-0000-0000-000000000000}</ProjectGuid>
  </PropertyGroup>
  <Import Project="`$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'`$(Configuration)|`$(Platform)'=='Release|Win32'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <PlatformToolset>v143</PlatformToolset>
  </PropertyGroup>
  <Import Project="`$(VCTargetsPath)\Microsoft.Cpp.props" />
  <Import Project="`$(VCTargetsPath)\Microsoft.Cpp.targets" />
</Project>
"@
        [System.IO.File]::WriteAllText($testProjFile, $testProjContent)
        
        # Try toolsets in order (newest stable first)
        # Test what's actually available, not what we think should be there
        $toolsetsToTry = @("v143", "v142", "v141", "v140", "v120")
        
        foreach ($toolset in $toolsetsToTry) {
            # Test if this toolset is available by trying to evaluate MSBuild properties
            $testArgs = @(
                $testProjFile,
                "/p:PlatformToolset=$toolset",
                "/p:Configuration=Release",
                "/p:Platform=Win32",
                "/t:ResolveProjectReferences",  # Lightweight target that just validates
                "/nologo",
                "/verbosity:quiet"
            )
            
            try {
                $null = & $MsBuildPath $testArgs 2>&1 | Out-Null
                $testResult = $LASTEXITCODE
                
                # If it succeeds or gives a non-toolset error, the toolset is available
                # MSB8020 specifically means toolset not found
                if ($testResult -eq 0) {
                    Write-Host "  ✓ Found available toolset: $toolset" -ForegroundColor Green
                    return $toolset
                }
            } catch {
                # Continue to next toolset
            }
        }
        
        Write-Host "  ⚠️  Could not detect available toolset, will use project defaults" -ForegroundColor Yellow
        return $null
    }
    catch {
        Write-Host "  ⚠️  Toolset detection failed: $_" -ForegroundColor Yellow
        Write-Host "  Will use project defaults" -ForegroundColor Gray
        return $null
    }
    finally {
        # Clean up test file
        if (Test-Path $testProjFile) {
            Remove-Item $testProjFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# ============================================================
# COMPILATION
# ============================================================

function Get-DevenvPath {
    param([string]$VisualStudioPath)
    
    if ([string]::IsNullOrWhiteSpace($VisualStudioPath)) {
        return $null
    }
    
    $devenvPaths = @(
        "$VisualStudioPath\Common7\IDE\devenv.exe",
        "$VisualStudioPath\IDE\devenv.exe"
    )
    
    foreach ($path in $devenvPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

function Compile-ApiFolder {
    param(
        [string]$ApiFolder,
        [string]$MsBuildPath,
        [string]$Configuration,
        [string]$BestToolset = $null,
        [string]$VisualStudioPath = $null,
        [bool]$UseIDE = $false
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Compiling API Folder" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "API Folder: $ApiFolder" -ForegroundColor White
    Write-Host "Configuration: $Configuration" -ForegroundColor White
    Write-Host ""
    
    # Find solution file
    $solutionFiles = @(Get-ChildItem -LiteralPath $ApiFolder -Filter "*.sln" -Recurse -ErrorAction SilentlyContinue)
    
    if ($solutionFiles.Count -eq 0) {
        Write-Host "Error: No .sln solution file found in API folder" -ForegroundColor Red
        return $false
    }

    # Prefer the game client solution — NOT Alchemy\CCShell.sln or zlib samples.
    $preferred = @(
        $solutionFiles | Where-Object { $_.FullName -match '\\Transcendence\\Transcendence\.sln$' }
    )
    if ($preferred.Count -eq 0) {
        $preferred = @($solutionFiles | Where-Object { $_.Name -eq 'Transcendence.sln' })
    }
    if ($preferred.Count -eq 0) {
        $preferred = @($solutionFiles | Where-Object { $_.Name -notmatch 'CCShell|zlib|DotZLib|TransExec' })
    }
    if ($preferred.Count -eq 0) {
        $preferred = @($solutionFiles[0])
    }

    $solutionFile = $preferred[0].FullName
    Write-Host "Solution file: $solutionFile" -ForegroundColor Gray
    if ($solutionFiles.Count -gt 1) {
        Write-Host "  (preferred Transcendence.sln over $($solutionFiles.Count) total .sln files)" -ForegroundColor DarkGray
    }
    Write-Host ""
    
    # Build using Visual Studio IDE if requested
    if ($UseIDE -and $VisualStudioPath) {
        $devenvPath = Get-DevenvPath -VisualStudioPath $VisualStudioPath
        if ($devenvPath -and (Test-Path $devenvPath)) {
            Write-Host "Building with Visual Studio 2022 IDE..." -ForegroundColor Cyan
            Write-Host "  Visual Studio: $devenvPath" -ForegroundColor Gray
            Write-Host "  Solution: $solutionFile" -ForegroundColor Gray
            Write-Host "  Configuration: $Configuration" -ForegroundColor Gray
            Write-Host ""
            
            # Build using devenv.exe command line
            # /Build: Builds the solution/project
            # /Rebuild: Cleans and builds
            # /Out: Redirects output to file
            $buildConfig = "$Configuration|Win32"
            $logFile = Join-Path $env:TEMP "VSBuild_$([Guid]::NewGuid().ToString('N').Substring(0,8)).log"
            
            try {
                Write-Host "  Starting build (output will be logged to: $logFile)..." -ForegroundColor Gray
                $buildArgs = @(
                    $solutionFile,
                    "/Build", $buildConfig,
                    "/Out", $logFile
                )
                
                $process = Start-Process -FilePath $devenvPath -ArgumentList $buildArgs -Wait -NoNewWindow -PassThru
                
                # Read and display log
                if (Test-Path $logFile) {
                    $logContent = Get-Content $logFile -Raw -ErrorAction SilentlyContinue
                    if ($logContent) {
                        # Display relevant parts of the log
                        $logLines = $logContent -split "`n"
                        foreach ($line in $logLines) {
                            if ($line -match "error|Error|ERROR|failed|Failed|FAILED") {
                                Write-Host $line -ForegroundColor Red
                            } elseif ($line -match "warning|Warning|WARNING") {
                                Write-Host $line -ForegroundColor Yellow
                            } elseif ($line -match "succeeded|Succeeded|SUCCEEDED|Build succeeded|========== Build:") {
                                Write-Host $line -ForegroundColor Green
                            }
                        }
                    }
                    Remove-Item $logFile -Force -ErrorAction SilentlyContinue
                }
                
                if ($process.ExitCode -eq 0) {
                    Write-Host ""
                    Write-Host "✓ Build successful!" -ForegroundColor Green
                    return $true
                } else {
                    Write-Host ""
                    Write-Host "✗ Build failed with exit code: $($process.ExitCode)" -ForegroundColor Red
                    Write-Host "  Full log available at: $logFile" -ForegroundColor Yellow
                    return $false
                }
            } catch {
                Write-Host ""
                Write-Host "✗ Build error: $_" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "Warning: Visual Studio IDE (devenv.exe) not found, falling back to MSBuild" -ForegroundColor Yellow
            Write-Host ""
        }
    }
    
    # Build using MSBuild
    if ($MsBuildPath -and (Test-Path $MsBuildPath)) {
        Write-Host "Building with MSBuild..." -ForegroundColor Cyan
        Write-Host "  MSBuild: $MsBuildPath" -ForegroundColor Gray
        Write-Host "  Solution: $solutionFile" -ForegroundColor Gray
        Write-Host "  Configuration: $Configuration" -ForegroundColor Gray
        Write-Host ""
        
        $buildArgs = @(
            $solutionFile,
            "/p:Configuration=$Configuration",
            "/p:Platform=Win32",
            "/m",  # Multi-processor build
            "/v:minimal"
        )
        
        # Override platform toolset to use the best available
        if ($BestToolset) {
            $buildArgs += "/p:PlatformToolset=$BestToolset"
            Write-Host "  Overriding platform toolset to: $BestToolset (best available)" -ForegroundColor Cyan
        }
        
        # Override C++ standard to C++20 if code requires it
        # Modern toolsets support C++20, and the code may require it
        if ($BestToolset -match "v14[0-9]") {
            # VS 2022+ toolsets support C++20
            # Use ClCompile_AdditionalOptions to pass /std:c++20 directly to compiler
            # Note: MSBuild property syntax - no quotes needed, MSBuild handles it
            $buildArgs += "/p:ClCompile_AdditionalOptions=/std:c++20 %(AdditionalOptions)"
            Write-Host "  Overriding C++ standard to: C++20 (required by code)" -ForegroundColor Cyan
        }
        
        try {
            # Capture both stdout and stderr
            $output = & $MsBuildPath $buildArgs 2>&1
            $buildResult = $LASTEXITCODE
            
            # Display output (MSBuild output is already formatted)
            if ($output) {
                $output | ForEach-Object {
                    # Color code MSBuild output
                    $line = $_.ToString()
                    if ($line -match "error|Error|ERROR|failed|Failed|FAILED") {
                        Write-Host $line -ForegroundColor Red
                    } elseif ($line -match "warning|Warning|WARNING") {
                        Write-Host $line -ForegroundColor Yellow
                    } elseif ($line -match "succeeded|Succeeded|SUCCEEDED|Build succeeded") {
                        Write-Host $line -ForegroundColor Green
                    } else {
                        Write-Host $line
                    }
                }
            }
            
            if ($buildResult -eq 0) {
                Write-Host ""
                Write-Host "✓ Build successful!" -ForegroundColor Green
                return $true
            } else {
                Write-Host ""
                Write-Host "✗ Build failed with exit code: $buildResult" -ForegroundColor Red
                Write-Host "  Check the error messages above for details." -ForegroundColor Yellow
                
                # Check for specific common errors and provide solutions
                $errorOutput = $output -join "`n"
                
                # Check for C++ standard errors
                if ($errorOutput -match "requires at least '/std:c\+\+20'|requires at least '/std:c\+\+17'|LanguageStandard") {
                    Write-Host ""
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host "  C++ Standard Version Error Detected" -ForegroundColor Yellow
                    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "The code requires a newer C++ standard than the project is configured for." -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "Retrying with C++20 standard..." -ForegroundColor Cyan
                    Write-Host ""
                    
                    # Retry with C++20 using compiler flag directly
                    $buildArgsCpp20 = @(
                        $solutionFile,
                        "/p:Configuration=$Configuration",
                        "/p:Platform=Win32",
                        "/p:ClCompile_AdditionalOptions=/std:c++20 %(AdditionalOptions)"
                    )
                    if ($BestToolset) {
                        $buildArgsCpp20 += "/p:PlatformToolset=$BestToolset"
                    }
                    $buildArgsCpp20 += "/m", "/v:minimal"
                    
                    try {
                        $outputCpp20 = & $MsBuildPath $buildArgsCpp20 2>&1
                        $buildResultCpp20 = $LASTEXITCODE
                        
                        if ($outputCpp20) {
                            $outputCpp20 | ForEach-Object {
                                $line = $_.ToString()
                                if ($line -match "error|Error|ERROR|failed|Failed|FAILED") {
                                    Write-Host $line -ForegroundColor Red
                                } elseif ($line -match "warning|Warning|WARNING") {
                                    Write-Host $line -ForegroundColor Yellow
                                } elseif ($line -match "succeeded|Succeeded|SUCCEEDED|Build succeeded") {
                                    Write-Host $line -ForegroundColor Green
                                } else {
                                    Write-Host $line
                                }
                            }
                        }
                        
                        if ($buildResultCpp20 -eq 0) {
                            Write-Host ""
                            Write-Host "✓ Build successful with C++20 standard!" -ForegroundColor Green
                            return $true
                        } else {
                            Write-Host ""
                            Write-Host "✗ Build still failed with C++20" -ForegroundColor Red
                        }
                    } catch {
                        Write-Host "  Retry error: $_" -ForegroundColor Red
                    }
                }
                
                # Check if toolset override failed - try falling back to stable toolset
                if ($errorOutput -match "MSB8020.*Platform Toolset.*cannot be found") {
                    # Try falling back to v143 (most common stable toolset)
                    if ($BestToolset -ne "v143") {
                        Write-Host ""
                        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                        Write-Host "  Toolset Not Available - Falling Back to Stable v143" -ForegroundColor Yellow
                        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                        Write-Host ""
                        Write-Host "Requested toolset ($BestToolset) is not installed." -ForegroundColor Yellow
                        Write-Host "Retrying with v143 (stable Visual Studio 2022 toolset)..." -ForegroundColor Cyan
                        Write-Host ""
                        
                        # Retry with v143
                        $buildArgsFallback = @(
                            $solutionFile,
                            "/p:Configuration=$Configuration",
                            "/p:Platform=Win32",
                            "/p:PlatformToolset=v143",
                            "/m",
                            "/v:minimal"
                        )
                        
                        try {
                            $outputFallback = & $MsBuildPath $buildArgsFallback 2>&1
                            $buildResultFallback = $LASTEXITCODE
                            
                            if ($outputFallback) {
                                $outputFallback | ForEach-Object {
                                    $line = $_.ToString()
                                    if ($line -match "error|Error|ERROR|failed|Failed|FAILED") {
                                        Write-Host $line -ForegroundColor Red
                                    } elseif ($line -match "warning|Warning|WARNING") {
                                        Write-Host $line -ForegroundColor Yellow
                                    } elseif ($line -match "succeeded|Succeeded|SUCCEEDED|Build succeeded") {
                                        Write-Host $line -ForegroundColor Green
                                    } else {
                                        Write-Host $line
                                    }
                                }
                            }
                            
                            if ($buildResultFallback -eq 0) {
                                Write-Host ""
                                Write-Host "✓ Build successful with stable v143 toolset!" -ForegroundColor Green
                                return $true
                            } else {
                                Write-Host ""
                                Write-Host "✗ Build still failed with v143" -ForegroundColor Red
                            }
                        } catch {
                            Write-Host "  Retry error: $_" -ForegroundColor Red
                        }
                    }
                }
                
                if ($errorOutput -match "MSB8020.*Platform Toolset.*cannot be found") {
                    Write-Host ""
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host "  Platform Toolset Error Detected" -ForegroundColor Yellow
                    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "The project is configured for an old Visual Studio toolset." -ForegroundColor Yellow
                    Write-Host ""
                    
                    # Detect available toolsets from Visual Studio installation
                    $availableToolsets = @()
                    if ($vsPathString) {
                        $vsToolsets = @(
                            "v143",  # VS 2022
                            "v142",  # VS 2019
                            "v141",  # VS 2017
                            "v140"   # VS 2015
                        )
                        
                        # Map toolset versions to Visual Studio versions
                        $toolsetMap = @{
                            "v143" = "Visual Studio 2022"
                            "v142" = "Visual Studio 2019"
                            "v141" = "Visual Studio 2017"
                            "v140" = "Visual Studio 2015"
                        }
                        
                        foreach ($toolset in $vsToolsets) {
                            $toolsetPath = Join-Path $vsPathString "VC\Tools\MSVC"
                            if (Test-Path $toolsetPath) {
                                $msvcVersions = Get-ChildItem -Path $toolsetPath -Directory -ErrorAction SilentlyContinue | 
                                    Sort-Object { [Version]$_.Name } -Descending
                                if ($msvcVersions) {
                                    $vsName = if ($toolsetMap.ContainsKey($toolset)) { 
                                        $toolsetMap[$toolset] 
                                    } else { 
                                        "Visual Studio (toolset $toolset)" 
                                    }
                                    $availableToolsets += "$vsName (toolset $toolset)"
                                    break
                                }
                            }
                        }
                        
                        # If no toolset found, default to VS 2022/2025 recommendation
                        if ($availableToolsets.Count -eq 0) {
                            $availableToolsets += "Visual Studio 2022/2025 (toolset v143 or newer)"
                        }
                    }
                    
                    Write-Host "Solution Options:" -ForegroundColor Cyan
                    Write-Host "  1. Retarget the solution to use the latest toolset:" -ForegroundColor White
                    Write-Host "     a. Open the solution in Visual Studio" -ForegroundColor Gray
                    Write-Host "     b. Right-click the solution → 'Retarget solution'" -ForegroundColor Gray
                    if ($availableToolsets.Count -gt 0) {
                        Write-Host "     c. Select the latest available: $($availableToolsets[0])" -ForegroundColor Green
                    } else {
                        Write-Host "     c. Select the latest available toolset (v143 or newer)" -ForegroundColor Gray
                    }
                    Write-Host "     d. Save and rebuild" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "  2. Or install the old toolset (not recommended):" -ForegroundColor White
                    Write-Host "     - Install Visual Studio 2013 with Windows XP support" -ForegroundColor Gray
                    Write-Host "     - This is outdated and not recommended" -ForegroundColor Gray
                    Write-Host ""
                    Write-Host "  Recommended: Use Visual Studio 2025/2026 toolset (latest available)" -ForegroundColor Green
                    Write-Host ""
                } elseif ($errorOutput -match "MSB8020") {
                    Write-Host ""
                    Write-Host "Platform Toolset Error: Project requires a different Visual Studio version." -ForegroundColor Yellow
                    Write-Host "  Try retargeting the solution in Visual Studio." -ForegroundColor Gray
                    Write-Host ""
                }
                
                Write-Host "  Common issues:" -ForegroundColor Yellow
                Write-Host "    - Missing SDKs (DirectX SDK or Windows SDK)" -ForegroundColor Gray
                Write-Host "    - Missing dependencies or libraries" -ForegroundColor Gray
                Write-Host "    - Project configuration errors" -ForegroundColor Gray
                Write-Host "    - Outdated platform toolset (retarget solution)" -ForegroundColor Gray
                return $false
            }
        }
        catch {
            Write-Host ""
            Write-Host "✗ Build error: $_" -ForegroundColor Red
            Write-Host "  Exception details: $($_.Exception.Message)" -ForegroundColor Yellow
            if ($_.Exception.InnerException) {
                Write-Host "  Inner exception: $($_.Exception.InnerException.Message)" -ForegroundColor Yellow
            }
            return $false
        }
    } else {
        Write-Host "Error: MSBuild not found" -ForegroundColor Red
        Write-Host "  Please install Visual Studio or provide MSBuild path" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Transcendence API Folder Compiler" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Store UseVS2026 in script scope for function access
$script:UseVS2026 = $UseVS2026

if ($UseVS2026) {
    Write-Host "Mode: Visual Studio 2026 (for C++20 support)" -ForegroundColor Green
} else {
    Write-Host "Default: Visual Studio 2022 (for pre-C++20 support)" -ForegroundColor Gray
    Write-Host "  Use -UseVS2026 to enable VS 2026 when project moves to C++20" -ForegroundColor Gray
}
Write-Host ""

# Check SDKs
$sdksOk = Ensure-Sdks
if (-not $sdksOk) {
    Write-Host ""
    Write-Host "⚠️  Warning: Some SDKs may be missing. Build may fail." -ForegroundColor Yellow
    Write-Host "   If build fails, you may need to:" -ForegroundColor Yellow
    Write-Host "   1. Install Windows SDK (included with Visual Studio)" -ForegroundColor Gray
    Write-Host "   2. Or install legacy DirectX SDK (if required by project)" -ForegroundColor Gray
    Write-Host "   3. Use -SkipSdkDownload to suppress this warning" -ForegroundColor Gray
    Write-Host ""
}

# Find Visual Studio (defaults to VS 2022 for pre-C++20 support)
$vsPathRaw = Find-VisualStudio
if (-not $vsPathRaw) {
    Write-Host "Error: Visual Studio not found" -ForegroundColor Red
    Write-Host "  Please install Visual Studio 2022 (default for pre-C++20 support)" -ForegroundColor Yellow
    Write-Host "  Or provide path with -VisualStudioPath parameter" -ForegroundColor Yellow
    exit 1
}

# Convert to string (handle arrays, objects, etc.)
$vsPathString = ""
if ($vsPathRaw -is [System.Array]) {
    $vsPathString = $vsPathRaw[0].ToString().Trim()
} elseif ($vsPathRaw -is [PSCustomObject]) {
    $vsPathString = $vsPathRaw.ToString().Trim()
} elseif ($vsPathRaw) {
    $vsPathString = $vsPathRaw.ToString().Trim()
}

# Remove any null characters or invalid paths
$vsPathString = $vsPathString -replace "`0", "" -replace "`r", "" -replace "`n", ""

if ([string]::IsNullOrWhiteSpace($vsPathString)) {
    Write-Host "Error: Invalid Visual Studio path" -ForegroundColor Red
    exit 1
}

Write-Host "  Using Visual Studio path: $vsPathString" -ForegroundColor Gray
Write-Host ""

# Find MSBuild
$msbuildPath = Get-MSBuildPath -VisualStudioPath $vsPathString
if (-not $msbuildPath) {
    Write-Host "Error: MSBuild not found in Visual Studio installation" -ForegroundColor Red
    exit 1
}

# Detect best available toolset by actually testing what's installed
Write-Host "Detecting best available toolset..." -ForegroundColor Cyan
$bestToolset = Get-BestAvailableToolset -VisualStudioPath $vsPathString -MsBuildPath $msbuildPath
if ($bestToolset) {
    Write-Host "  ✓ Will use toolset: $bestToolset (automatically overrides project settings)" -ForegroundColor Green
    Write-Host "  This uses the best stable toolset actually installed on your system" -ForegroundColor Gray
} else {
    Write-Host "  ⚠️  Could not detect toolset, will use project defaults" -ForegroundColor Yellow
}

Write-Host ""

# Compile
$configurations = if ($BuildConfiguration -eq "Both") { @("Debug", "Release") } else { @($BuildConfiguration) }
$allSuccess = $true

foreach ($config in $configurations) {
    $success = Compile-ApiFolder -ApiFolder $ApiFolderPath -MsBuildPath $msbuildPath -Configuration $config -BestToolset $bestToolset -VisualStudioPath $vsPathString -UseIDE $UseVisualStudioIDE
    if (-not $success) {
        $allSuccess = $false
    }
    Write-Host ""
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Build Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Save configuration if Visual Studio was auto-detected
if ([string]::IsNullOrWhiteSpace($script:Config.VisualStudioPath) -and $vsPath) {
    $vsPathToSave = if ($vsPath) { $vsPath.ToString().Trim() } else { "" }
    if ($vsPathToSave) {
        $script:Config.VisualStudioPath = $vsPathToSave
    }
    try {
        $json = $script:Config | ConvertTo-Json -Depth 10 -Compress:$false
        [System.IO.File]::WriteAllText($configFile, $json, [System.Text.UTF8Encoding]::new($false))
        Write-Host "Configuration saved to: $configFile" -ForegroundColor Gray
    }
    catch {
        Write-Host "Warning: Could not save configuration: $_" -ForegroundColor Yellow
    }
}

if ($allSuccess) {
    Write-Host "✓ All builds completed successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some builds failed. Check output above for details." -ForegroundColor Red
    exit 1
}

