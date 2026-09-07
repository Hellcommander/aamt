# GenerateMechCockpitAssets.ps1
# Generates cockpit assets with alpha channel transparency for all mech forms

param(
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting,
    [string]$FormID = ""  # Empty = all forms
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
$mechsDir = "$modPath\Data\Config\Mechs"

# Setup error logging
$logDir = "$scriptPath\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = "$logDir\GenerateMechCockpitAssets_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-LogError {
    param([string]$Message, [string]$Exception = "")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] ERROR: $Message"
    if ($Exception) {
        $logMessage += "`nException: $Exception"
    }
    Write-Host $logMessage -ForegroundColor Red
    Add-Content -Path $logFile -Value $logMessage
}

function Write-LogInfo {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $logFile -Value $logMessage
}

# Log script start
Write-LogInfo "=== Script Started ==="
Write-LogInfo "Log file: $logFile"
Write-Host "Errors will be logged to: $logFile" -ForegroundColor Cyan

# Trap errors and log them
trap {
    Write-LogError -Message $_.Exception.Message -Exception $_.Exception.ToString()
    Write-Host "`nError logged to: $logFile" -ForegroundColor Yellow
    Write-Host "You can copy the error from the log file." -ForegroundColor Yellow
    continue
}

# Load cockpit system config
$cockpitConfig = Get-Content "$mechsDir\CockpitSystem.json" | ConvertFrom-Json

# Get form files
$formFiles = if ($FormID) {
    @(Get-Item "$mechsDir\${FormID}Form.json" -ErrorAction SilentlyContinue)
} else {
    Get-ChildItem "$mechsDir\*Form.json" | Where-Object { $_.Name -ne "CockpitSystem.json" }
}

Write-Host "=== Generating Cockpit Assets with Alpha Channels ===" -ForegroundColor Cyan
Write-Host "Forms to process: $($formFiles.Count)" -ForegroundColor Yellow

foreach ($formFile in $formFiles) {
    $formJson = Get-Content $formFile.FullName | ConvertFrom-Json
    $formId = $formJson.id
    
    if (-not $formJson.cockpit) {
        Write-Host "`nSkipping $formId - no cockpit config" -ForegroundColor Yellow
        continue
    }
    
    $cockpit = $formJson.cockpit
    Write-Host "`n[Form] Processing $formId cockpit..." -ForegroundColor Green
    
    # 1. Generate Cockpit Frame Sprite
    Write-Host "  [1/3] Generating cockpit frame..." -ForegroundColor White
    $framePath = "$modPath\sprites\cockpits\${formId}_frame.png"
    
    if (-not ($SkipExisting -and (Test-Path $framePath))) {
        $params = @{
            AssetType = "Sprite"
            AssetName = "cockpit_${formId}_frame"
            Width = $cockpit.size[0]
            Height = $cockpit.size[1]
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $formId
                Type = "cockpit_frame"
                Shape = $cockpit.shape
                FrameStyle = $cockpit.frameStyle
                FrameThickness = $cockpit.frameThickness
                FrameColor = $cockpit.frameColor
                AlphaChannel = $false  # Frame is opaque
            }
        }
        
        try {
            & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
            Write-LogInfo "Generated cockpit frame for $formId"
        } catch {
            Write-LogError -Message "Failed to generate cockpit frame for $formId" -Exception $_.Exception.ToString()
            throw
        }
    }
    
    # 2. Generate Cockpit Glass (with alpha transparency)
    Write-Host "  [2/3] Generating cockpit glass (alpha channel)..." -ForegroundColor White
    $glassPath = "$modPath\sprites\cockpits\${formId}_glass.png"
    
    if (-not ($SkipExisting -and (Test-Path $glassPath))) {
        $params = @{
            AssetType = "Sprite"
            AssetName = "cockpit_${formId}_glass"
            Width = $cockpit.size[0]
            Height = $cockpit.size[1]
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $formId
                Type = "cockpit_glass"
                Shape = $cockpit.shape
                GlassTint = $cockpit.glassTint
                TransparencyLevel = $cockpit.transparencyLevel
                AlphaChannel = $true
                PlayerVisible = $true
                RGBA = $true
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 3. Generate Cockpit Interior (player visible area)
    Write-Host "  [3/3] Generating cockpit interior (player visibility)..." -ForegroundColor White
    $interiorPath = "$modPath\sprites\cockpits\${formId}_interior.png"
    
    if (-not ($SkipExisting -and (Test-Path $interiorPath))) {
        $params = @{
            AssetType = "Sprite"
            AssetName = "cockpit_${formId}_interior"
            Width = $cockpit.size[0]
            Height = $cockpit.size[1]
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $formId
                Type = "cockpit_interior"
                Shape = $cockpit.shape
                PlayerScale = $cockpit.playerScale
                PlayerOffset = $cockpit.playerOffset
                AlphaChannel = $true
                TransparencyLevel = 1.0  # Fully transparent for player visibility
                RGBA = $true
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
}

Write-Host "`n=== Cockpit Asset Generation Complete ===" -ForegroundColor Cyan
Write-Host "All cockpits generated with alpha channel transparency for player visibility" -ForegroundColor Green
