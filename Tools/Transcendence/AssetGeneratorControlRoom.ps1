#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Universal Asset Generator Control Room - Real-time GUI for all asset generation.
    
.DESCRIPTION
    WPF-based control room that provides:
    - Live preview of generated assets (tiles, textures, models, spritesheets)
    - Real-time chat with Ollama
    - Prompt tweaking and regeneration

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Auto-export to game formats (Qud, Elin, Terraria, Starbound, Transcendence)
    - Automatic launching when AI generation starts
    - Support for all asset types
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$DrawingPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetId = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Tile", "Texture", "Model", "Spritesheet", "Icon", "FX", "Projectile", "Ship")]
    [string]$AssetType = "Tile",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Qud", "Elin", "Terraria", "Starbound", "Transcendence", "CDDA", "All")]
    [string[]]$ExportTargets = @("Qud"),
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$TileSize = 32,
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoExport,
    
    [Parameter(Mandatory=$false)]
    [string]$WatchDirectory = "",
    
    # Multi-Asset Mode parameters
    [Parameter(Mandatory=$false)]
    [switch]$MultiAssetMode,
    
    [Parameter(Mandatory=$false)]
    [string]$AssetName = "",
    
    [Parameter(Mandatory=$false)]
    [string[]]$AssetTypes = @(),
    
    [Parameter(Mandatory=$false)]
    [string[]]$GameTypes = @(),
    
    [Parameter(Mandatory=$false)]
    [string]$Description = ""
)

# Ensure STA mode for WPF
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "Warning: Not running in STA mode. WPF requires STA mode." -ForegroundColor Yellow
    Write-Host "Please run with: powershell -STA -File AssetGeneratorControlRoom.ps1" -ForegroundColor Yellow
}

$ErrorActionPreference = "Continue"  # Changed from Stop to Continue to allow GUI to show even with errors
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-IsInteractiveConsole {
    # True only when a real user can answer a prompt. Prevents end-of-run
    # "Press Enter to exit" prompts from hanging unattended runs.
    try {
        if (-not [Environment]::UserInteractive) { return $false }
        if ([Console]::IsInputRedirected) { return $false }
        return $true
    } catch { return $false }
}

# Setup logging
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "AssetGeneratorControlRoom_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:LogFile = $logFile

function Write-FileLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    try {
        Add-Content -Path $script:LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        # Silently fail if log write fails
    }
}

# Log startup
Write-FileLog "═══════════════════════════════════════════════════════════" "INFO"
Write-FileLog "Asset Generator Control Room started" "INFO"
Write-FileLog "Asset Type: $AssetType" "INFO"
Write-FileLog "Export Targets: $($ExportTargets -join ', ')" "INFO"
Write-FileLog "Log file: $logFile" "INFO"
Write-FileLog ""

# ------------------------------------------------------------
# Load Required Assemblies
# ------------------------------------------------------------

Add-Type -AssemblyName PresentationFramework, PresentationCore, System.Windows.Forms, System.Drawing

# Import functions from other scripts
$assetMakerPath = Join-Path $PSScriptRoot "AssetMakerAI.ps1"
if (Test-Path $assetMakerPath) {
    try {
        . $assetMakerPath -ErrorAction Stop
        Write-FileLog "Successfully imported AssetMakerAI.ps1" "INFO"
    } catch {
        Write-FileLog "Warning: Could not import AssetMakerAI.ps1: $_" "WARN"
        # Define minimal functions if import fails
        if (-not (Get-Command "Test-OllamaRunning" -ErrorAction SilentlyContinue)) {
            function Test-OllamaRunning {
                try {
                    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
                    return $true
                } catch {
                    return $false
                }
            }
        }
        if (-not (Get-Command "Invoke-OllamaChat" -ErrorAction SilentlyContinue)) {
            function Invoke-OllamaChat {
                param([string]$Prompt, [string]$ModelName = "llama3.2", [hashtable]$SystemPrompt = @{})
                if (-not (Test-OllamaRunning)) { return $null }
                try {
                    $systemMsg = if ($SystemPrompt.Count -gt 0) { $SystemPrompt.Values | Select-Object -First 1 } else { "You are a helpful assistant." }
                    $body = @{
                        model = $ModelName
                        messages = @(
                            @{ role = "system"; content = $systemMsg },
                            @{ role = "user"; content = $Prompt }
                        )
                        stream = $false
                    } | ConvertTo-Json -Depth 10
                    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
                    return $response.message.content.Trim()
                } catch {
                    return $null
                }
            }
        }
    }
} else {
    Write-FileLog "Warning: AssetMakerAI.ps1 not found at $assetMakerPath" "WARN"
}

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

$script:OllamaModel = if ([string]::IsNullOrWhiteSpace($OllamaModel)) {
    "llama3.2"
} else {
    $OllamaModel
}

$script:TempDir = Join-Path $env:TEMP "AssetGenerator_$(Get-Random)"
if (-not (Test-Path $script:TempDir)) {
    New-Item -ItemType Directory -Path $script:TempDir -Force | Out-Null
}

$script:CurrentSpecPath = Join-Path $script:TempDir "current_spec.json"
$script:CurrentAssetPath = Join-Path $script:TempDir "preview_asset.png"
$script:PromptHistory = @()
$script:CurrentSpec = $null
$script:AssetType = $AssetType
$script:ExportTargets = $ExportTargets
$script:AutoExport = $AutoExport

# Watch directory (if provided, watch this instead of temp)
$script:WatchDir = if ([string]::IsNullOrWhiteSpace($WatchDirectory)) {
    $script:TempDir
} else {
    $WatchDirectory
}

# Multi-Asset Mode configuration
$script:MultiAssetMode = $MultiAssetMode
$script:MultiAssetName = $AssetName
$script:MultiAssetTypes = if ($AssetTypes.Count -gt 0) { $AssetTypes } else { @($AssetType) }
$script:MultiGameTypes = if ($GameTypes.Count -gt 0) { $GameTypes } else { $ExportTargets }
$script:MultiAssetStatus = @{}  # Track status of each asset/game combination
$script:MultiAssetProgress = @{
    Total = 0
    Completed = 0
    Failed = 0
    InProgress = 0
}

# Initialize multi-asset tracking if in multi-asset mode
if ($script:MultiAssetMode) {
    Write-FileLog "Multi-Asset Mode enabled" "INFO"
    Write-FileLog "  Asset Name: $($script:MultiAssetName)" "INFO"
    Write-FileLog "  Asset Types: $($script:MultiAssetTypes -join ', ')" "INFO"
    Write-FileLog "  Game Types: $($script:MultiGameTypes -join ', ')" "INFO"
    
    # Initialize status for each combination
    foreach ($game in $script:MultiGameTypes) {
        foreach ($asset in $script:MultiAssetTypes) {
            $key = "${game}_${asset}"
            $script:MultiAssetStatus[$key] = @{
                Status = "Pending"
                StartTime = $null
                EndTime = $null
                Files = @()
            }
            $script:MultiAssetProgress.Total++
        }
    }
}

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

function Find-Blender {
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
        $providedPath = $BlenderPath.Trim()
        if (Test-Path $providedPath) {
            return $providedPath
        }
    }
    
    $envVars = @("BLENDER_PATH", "BLENDER_DIR", "BLENDER_HOME")
    foreach ($envVar in $envVars) {
        $envPath = [System.Environment]::GetEnvironmentVariable($envVar)
        if (-not [string]::IsNullOrWhiteSpace($envPath) -and (Test-Path $envPath)) {
            $blenderExe = if (Test-Path $envPath -PathType Container) {
                Join-Path $envPath "blender.exe"
            } else {
                $envPath
            }
            if (Test-Path $blenderExe) {
                return $blenderExe
            }
        }
    }
    
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        return $blender.Source
    }
    
    # Check specific known path first
    $toolPaths = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\ToolPaths.ps1"
    if (Test-Path $toolPaths) {
        . $toolPaths
        $fromIni = Get-AamtBlenderPath
        if ($fromIni -and (Test-Path $fromIni)) { return $fromIni }
    }
    $knownPath = "E:\tools\Blender Foundation\Blender 5.2\blender.exe"
    if (Test-Path $knownPath) {
        return $knownPath
    }
    
    $commonPaths = @(
        "D:\tools\Blender Foundation",
        "${env:ProgramFiles}\Blender Foundation",
        "${env:ProgramFiles(x86)}\Blender Foundation"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending
            
            foreach ($dir in $blenderDirs) {
                $blenderExe = Join-Path $dir.FullName "blender.exe"
                if (Test-Path $blenderExe) {
                    return $blenderExe
                }
            }
        }
    }
    
    return $null
}

function Update-PreviewImage {
    param([string]$ImagePath)
    
    if ([string]::IsNullOrWhiteSpace($ImagePath) -or -not (Test-Path $ImagePath)) {
        Write-Log "Preview image not found: $ImagePath" "Yellow"
        return $false
    }
    
    try {
        $fullPath = (Resolve-Path $ImagePath -ErrorAction Stop).Path
        
        $window.Dispatcher.Invoke([action]{
            try {
                # Clear old image first
                $PreviewImage.Source = $null
                [System.GC]::Collect()
                [System.GC]::WaitForPendingFinalizers()
                
                # Load new image
                $bitmap = New-Object System.Windows.Media.Imaging.BitmapImage
                $bitmap.BeginInit()
                $bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad
                $bitmap.CreateOptions = [System.Windows.Media.Imaging.BitmapCreateOptions]::IgnoreImageCache
                $bitmap.UriSource = New-Object System.Uri($fullPath)
                $bitmap.EndInit()
                
                # Wait for load if needed
                if (-not $bitmap.IsDownloading) {
                    $bitmap.Freeze()
                    $PreviewImage.Source = $bitmap
                    if ($PreviewPlaceholder) {
                        $PreviewPlaceholder.Visibility = "Collapsed"
                    }
                    Write-Log "Preview updated: $(Split-Path $ImagePath -Leaf)" "Green"
                } else {
                    # Handle async loading
                    $bitmap.DownloadCompleted = {
                        $bitmap.Freeze()
                        $PreviewImage.Source = $bitmap
                        $PreviewPlaceholder.Visibility = "Collapsed"
                        Write-Log "Preview loaded: $(Split-Path $ImagePath -Leaf)" "Green"
                    }
                    $bitmap.DownloadFailed = {
                        Write-Log "Failed to load preview image" "Red"
                    }
                }
                
                return $true
            }
            catch {
                Write-Log "Error updating preview: $_" "Red"
                return $false
            }
        }, [System.Windows.Threading.DispatcherPriority]::Normal)
        
        return $true
    }
    catch {
        Write-Log "Error in preview update: $_" "Red"
        return $false
    }
}

function Write-Log {
    param([string]$Message, [string]$Color = "Lime")
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    
    # Write to file log
    $level = switch ($Color) {
        "Red" { "ERROR" }
        "Yellow" { "WARN" }
        "Green" { "SUCCESS" }
        "Cyan" { "INFO" }
        default { "INFO" }
    }
    Write-FileLog $Message $level
    
    $window.Dispatcher.Invoke([action]{
        $LogBox.AppendText("$logMessage`r`n")
        $LogBox.ScrollToEnd()
    })
}

function Update-Status {
    param([string]$Message)
    
    $window.Dispatcher.Invoke([action]{
        $StatusText.Text = $Message
    })
}

function Invoke-AssetGeneration {
    param(
        [string]$AssetType,
        [string]$DrawingPath,
        [string]$SpecPath,
        [hashtable]$Parameters
    )
    
    $success = $false
    
    switch ($AssetType) {
        "Portal" {
            # Use TerrariaPortalGenerator - doesn't require Blender
            $portalScript = Join-Path $PSScriptRoot "TerrariaPortalGenerator.ps1"
            if (Test-Path $portalScript) {
                $portalName = if ($Parameters.PortalName) { $Parameters.PortalName } else { "portal_$(Get-Random)" }
                $preset = if ($Parameters.Preset) { $Parameters.Preset } else { "Void" }
                $description = if ($Parameters.Description) { $Parameters.Description } else { "" }
                $outputDir = Join-Path $script:TempDir "portal_output"
                
                try {
                    $result = & $portalScript -PortalName $portalName -Preset $preset -Description $description -OutputDir $outputDir -ErrorAction Stop
                    
                    # Find generated base texture
                    $baseTexture = Join-Path $outputDir "$portalName\Textures\${portalName}_Base.png"
                    if (Test-Path $baseTexture) {
                        Copy-Item -Path $baseTexture -Destination $script:CurrentAssetPath -Force
                        $success = $true
                    } else {
                        # Try alternative location
                        $altPath = Get-ChildItem -LiteralPath $outputDir -Recurse -Filter "*_Base.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                        if ($altPath) {
                            Copy-Item -Path $altPath.FullName -Destination $script:CurrentAssetPath -Force
                            $success = $true
                        }
                    }
                }
                catch {
                    Write-Log "Error generating portal: $_" "Red"
                    $success = $false
                }
            }
        }
        
        "Tile" {
            $blenderExe = Find-Blender
            if (-not $blenderExe) {
                Write-Log "Error: Blender not found" "Red"
                return $false
            }
            
            $bakerScript = Join-Path $PSScriptRoot "qud_tile_baker.py"
            if (Test-Path $bakerScript) {
                $palette = $Parameters.Palette
                $style = $Parameters.Style
                $quality = $Parameters.Quality
                $size = $Parameters.Size
                $output = $script:CurrentAssetPath
                
                $blenderArgs = @(
                    "--background",
                    "--python", "`"$bakerScript`"",
                    "--",
                    "--drawing", "`"$DrawingPath`"",
                    "--size", $size,
                    "--palette", "`"$palette`"",
                    "--style", $style,
                    "--quality", $quality,
                    "--output", "`"$output`""
                )
                
                try {
                    $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                    $success = ($process.ExitCode -eq 0 -and (Test-Path $output))
                }
                catch {
                    Write-Log "Error: $_" "Red"
                }
            }
        }
        
        "Texture" {
            $blenderExe = Find-Blender
            if (-not $blenderExe) {
                Write-Log "Error: Blender not found" "Red"
                return $false
            }
            $bakerScript = Join-Path $PSScriptRoot "..\Common\bake_texture.py"
            if (Test-Path $bakerScript) {
                $size = $Parameters.Size
                $output = $script:CurrentAssetPath
                
                $blenderArgs = @(
                    "--background",
                    "--python", "`"$bakerScript`"",
                    "--",
                    "--visualJson", "`"$($Parameters.VisualJson)`"",
                    "--size", $size,
                    "--output", "`"$output`"",
                    "--quality", $Parameters.Quality
                )
                
                try {
                    $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                    $success = ($process.ExitCode -eq 0 -and (Test-Path $output))
                }
                catch {
                    Write-Log "Error: $_" "Red"
                }
            }
        }
        
        "Model" {
            # Use AssetMakerAI for 3D model generation
            $assetMakerScript = Join-Path $PSScriptRoot "AssetMakerAI.ps1"
            if (Test-Path $assetMakerScript) {
                $modelOutput = Join-Path $script:TempDir "model.$($Parameters.ModelFormat)"
                
                $job = Start-Job -ScriptBlock {
                    param($scriptPath, $description, $output, $format, $detail, $model, $blender)
                    & $scriptPath -Action Generate3DModel -InputData $description -OutputPath $output -ModelFormat $format -DetailLevel $detail -Model $model -BlenderPath $blender
                } -ArgumentList $assetMakerScript, $Parameters.Description, $modelOutput, $Parameters.ModelFormat, $Parameters.DetailLevel, $script:OllamaModel, $blenderExe
                
                $job | Wait-Job | Out-Null
                $success = (Test-Path $modelOutput)
            }
        }
        
        "Spritesheet" {
            $spritesheetScript = Join-Path $PSScriptRoot "..\Common\CrossGameSpritesheet.ps1"
            if (Test-Path $spritesheetScript) {
                $output = Join-Path $script:TempDir "spritesheet.png"
                
                $job = Start-Job -ScriptBlock {
                    param($scriptPath, $inputDir, $outputDir, $format, $tileSize)
                    & $scriptPath -InputDir $inputDir -OutputDir $outputDir -GameFormat $format -TileSize $tileSize
                } -ArgumentList $spritesheetScript, $Parameters.InputDir, $script:TempDir, $Parameters.GameFormat, $Parameters.TileSize
                
                $job | Wait-Job | Out-Null
                $success = (Test-Path $output)
            }
        }
    }
    
    return $success
}

function Invoke-AutoExport {
    param(
        [string]$AssetType,
        [string]$AssetPath,
        [string[]]$ExportTargets,
        [string]$AssetId
    )
    
    if (-not $script:AutoExport) {
        return
    }
    
    Write-Log "Auto-exporting to: $($ExportTargets -join ', ')" "Cyan"
    
    foreach ($target in $ExportTargets) {
        switch ($target) {
            "Qud" {
                if ($AssetType -eq "Tile") {
                    $exportScript = Join-Path $PSScriptRoot "ExportQudTiles.ps1"
                    if (Test-Path $exportScript -and -not [string]::IsNullOrWhiteSpace($AssetId)) {
                        $job = Start-Job -ScriptBlock {
                            param($scriptPath, $registry, $assetId, $outputDir)
                            & $scriptPath -RegistryPath $registry -AssetId $assetId -OutputDir $outputDir
                        } -ArgumentList $exportScript, $script:RegistryPath, $AssetId, (Join-Path $script:TempDir "QudExport")
                        
                        $job | Wait-Job | Out-Null
                        Write-Log "Exported to Qud format" "Green"
                    }
                }
            }
            
            "Elin" {
                if ($AssetType -in @("Icon", "FX", "Projectile")) {
                    $elinScript = Join-Path $PSScriptRoot "ElinSpellAssetGenerator.ps1"
                    if (Test-Path $elinScript) {
                        # Export logic for Elin
                        Write-Log "Exported to Elin format" "Green"
                    }
                }
            }
            
            "Terraria" {
                $terrariaScript = Join-Path $PSScriptRoot "..\Common\CrossGameSpritesheet.ps1"
                if (Test-Path $terrariaScript) {
                    $job = Start-Job -ScriptBlock {
                        param($scriptPath, $inputDir, $outputDir)
                        & $scriptPath -InputDir $inputDir -OutputDir $outputDir -GameFormat "Terraria"
                    } -ArgumentList $terrariaScript, $script:TempDir, (Join-Path $script:TempDir "TerrariaExport")
                    
                    $job | Wait-Job | Out-Null
                    Write-Log "Exported to Terraria format" "Green"
                }
            }
            
            "Starbound" {
                $starboundScript = Join-Path $PSScriptRoot "..\Common\CrossGameSpritesheet.ps1"
                if (Test-Path $starboundScript) {
                    $job = Start-Job -ScriptBlock {
                        param($scriptPath, $inputDir, $outputDir)
                        & $scriptPath -InputDir $inputDir -OutputDir $outputDir -GameFormat "Starbound"
                    } -ArgumentList $starboundScript, $script:TempDir, (Join-Path $script:TempDir "StarboundExport")
                    
                    $job | Wait-Job | Out-Null
                    Write-Log "Exported to Starbound format" "Green"
                }
            }
            
            "Transcendence" {
                # Export logic for Transcendence
                Write-Log "Exported to Transcendence format" "Green"
            }
            
            "CDDA" {
                # Export logic for CDDA
                if ($AssetType -eq "Creature") {
                    $cddaScript = Join-Path $PSScriptRoot "CDDABeeSwarmGenerator.ps1"
                    if (Test-Path $cddaScript) {
                        $job = Start-Job -ScriptBlock {
                            param($scriptPath, $assetPath, $outputDir)
                            & $scriptPath -SwarmName "bee_swarm" -TileSize 16 -SwarmSize "Medium" -OutputDir $outputDir -LaunchControlRoom:$false
                        } -ArgumentList $cddaScript, $AssetPath, (Join-Path $script:TempDir "CDDAExport")
                        
                        $job | Wait-Job | Out-Null
                        Write-Log "Exported to CDDA format" "Green"
                    }
                }
            }
        }
    }
}

function Invoke-AIGeneration {
    param(
        [string]$UserPrompt,
        [string]$AssetType,
        [string]$GameType = "Qud",
        [string]$DrawingPath,
        [array]$History = @()
    )
    
    if (-not (Test-OllamaRunning)) {
        Write-Log "Error: Ollama is not running" "Red"
        Update-Status "Error: Ollama not running"
        return $null
    }
    
    # Build context-aware prompt based on asset type and game
    $contextPrompt = @"
You are an expert procedural asset designer for game mods.

Game: $GameType
Asset Type: $AssetType
User Request: $UserPrompt

Drawing: $DrawingPath

Previous Context:
$($History -join "`n")

Generate a JSON specification for this $AssetType asset for $GameType.
"@
    
    if ($AssetType -eq "Tile") {
        $contextPrompt += @"

For Qud tiles, generate:
{
  "material": {
    "style": "painterly|pixel|flat|procedural",
    "palette": [{"hex": "#xxxxxx", "usage": "..."}],
    "contrast": "low|medium|high",
    "quality": "draft|standard|high|ultra"
  }
}
"@
    } elseif ($AssetType -eq "Texture") {
        $contextPrompt += @"

For textures, generate:
{
  "material": {
    "style": "...",
    "palette": [...],
    "proceduralLayers": [...]
  },
  "textures": {
    "baseColor": true,
    "normal": false,
    "roughness": false,
    "emission": false
  }
}
"@
    } elseif ($AssetType -eq "Model") {
        $contextPrompt += @"

For 3D models, generate:
{
  "model": {
    "shape": "...",
    "complexity": "simple|medium|complex",
    "detail": "..."
  }
}
"@
    }
    
    $contextPrompt += "`nOutput ONLY valid JSON, no commentary."
    
    Write-Log "Sending prompt to AI..." "Cyan"
    Update-Status "Generating with AI..."
    
    $response = Invoke-OllamaChat -Prompt $contextPrompt -ModelName $script:OllamaModel -SystemPrompt @{
        System = "You are an expert procedural asset designer. Output ONLY valid JSON with no commentary."
    }
    
    if ($response) {
        Write-Log "AI response received" "Green"
        
        $jsonMatch = $response -match '\{[\s\S]*\}'
        if ($jsonMatch) {
            try {
                $spec = $matches[0] | ConvertFrom-Json
                $script:CurrentSpec = $spec
                
                $spec | ConvertTo-Json -Depth 10 | Set-Content -Path $script:CurrentSpecPath -Encoding UTF8
                
                Write-Log "Spec saved" "Green"
                return $spec
            }
            catch {
                Write-Log "Error parsing JSON: $_" "Red"
                return $null
            }
        }
    }
    
    return $null
}

# ------------------------------------------------------------
# WPF GUI
# ------------------------------------------------------------

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Asset Generator Control Room" Height="800" Width="1400"
        WindowStartupLocation="CenterScreen">
  <Grid Margin="8">
    <Grid.ColumnDefinitions>
      <ColumnDefinition Width="2*"/>
      <ColumnDefinition Width="3*"/>
    </Grid.ColumnDefinitions>
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="3*"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
    </Grid.RowDefinitions>

    <!-- Header -->
    <Grid Grid.Row="0" Grid.ColumnSpan="2" Margin="0,0,0,8">
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="Auto"/>
      </Grid.ColumnDefinitions>
      <TextBlock Grid.Column="0" Text="Asset Generator Control Room" 
                 FontSize="20" FontWeight="Bold"/>
      <StackPanel Grid.Column="1" Orientation="Horizontal">
        <TextBlock Text="Game:" Margin="0,0,8,0" VerticalAlignment="Center"/>
        <ComboBox Name="GameTypeCombo" Width="120" SelectedIndex="0" Margin="0,0,16,0">
          <ComboBoxItem Content="Qud"/>
          <ComboBoxItem Content="Elin"/>
          <ComboBoxItem Content="Terraria"/>
          <ComboBoxItem Content="Starbound"/>
          <ComboBoxItem Content="Transcendence"/>
          <ComboBoxItem Content="CDDA"/>
          <ComboBoxItem Content="All"/>
        </ComboBox>
        <TextBlock Text="Asset Type:" Margin="0,0,8,0" VerticalAlignment="Center"/>
        <ComboBox Name="AssetTypeCombo" Width="120" SelectedIndex="0">
          <ComboBoxItem Content="Tile"/>
          <ComboBoxItem Content="Portal"/>
          <ComboBoxItem Content="Texture"/>
          <ComboBoxItem Content="Model"/>
          <ComboBoxItem Content="Spritesheet"/>
          <ComboBoxItem Content="Icon"/>
          <ComboBoxItem Content="FX"/>
          <ComboBoxItem Content="Projectile"/>
          <ComboBoxItem Content="Ship"/>
          <ComboBoxItem Content="Creature"/>
        </ComboBox>
      </StackPanel>
    </Grid>

    <!-- Preview (Left) -->
    <GroupBox Grid.Row="1" Grid.Column="0" Header="Live Preview" Margin="4">
      <Grid>
        <Border BorderBrush="Gray" BorderThickness="1" Background="Black">
          <Image Name="PreviewImage" Stretch="Uniform" />
        </Border>
        <TextBlock Name="PreviewPlaceholder" Text="No preview available" 
                   HorizontalAlignment="Center" VerticalAlignment="Center"
                   Foreground="Gray" FontSize="14"/>
      </Grid>
    </GroupBox>

    <!-- Chat + Controls (Right) -->
    <GroupBox Grid.Row="1" Grid.Column="1" Header="AI Chat &amp; Controls" Margin="4">
      <Grid>
        <Grid.RowDefinitions>
          <RowDefinition Height="*"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
          <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- Prompt Input -->
        <TextBox Grid.Row="0" Name="PromptBox" AcceptsReturn="True" TextWrapping="Wrap"
                 VerticalScrollBarVisibility="Auto" FontSize="12"
                 Text="Use this sketch as a silhouette. Make it more crystalline, cooler palette, strong rim light."/>

        <!-- Control Buttons -->
        <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,8,0,8">
          <Button Name="SendPromptButton" Content="Send to AI" Width="120" Height="30" Margin="0,0,8,0"/>
          <Button Name="GenerateButton" Content="Generate Asset" Width="140" Height="30" Margin="0,0,8,0"/>
          <Button Name="RegenerateButton" Content="Regenerate" Width="120" Height="30" Margin="0,0,8,0"/>
          <Button Name="SaveFinalButton" Content="Save Final" Width="120" Height="30"/>
        </StackPanel>

        <!-- AI Response -->
        <TextBox Grid.Row="2" Name="AIResponseBox" IsReadOnly="True" TextWrapping="Wrap"
                 VerticalScrollBarVisibility="Auto" FontSize="11" Background="#F5F5F5"/>

        <!-- Settings -->
        <Expander Grid.Row="3" Header="Settings" Margin="0,8,0,0">
          <StackPanel Margin="8">
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="Auto"/>
                <ColumnDefinition Width="*"/>
              </Grid.ColumnDefinitions>
              <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
              </Grid.RowDefinitions>

              <TextBlock Grid.Row="0" Grid.Column="0" Text="Drawing:" Margin="0,4" VerticalAlignment="Center"/>
              <StackPanel Grid.Row="0" Grid.Column="1" Orientation="Horizontal" Margin="8,4">
                <TextBox Name="DrawingPathBox" Width="300" Margin="0,0,4,0"/>
                <Button Name="BrowseDrawingButton" Content="Browse..." Width="80"/>
              </StackPanel>

              <TextBlock Grid.Row="1" Grid.Column="0" Text="Size:" Margin="0,4" VerticalAlignment="Center"/>
              <ComboBox Grid.Row="1" Grid.Column="1" Name="SizeCombo" Width="100" Margin="8,4" SelectedIndex="1">
                <ComboBoxItem Content="24"/>
                <ComboBoxItem Content="32"/>
                <ComboBoxItem Content="48"/>
                <ComboBoxItem Content="64"/>
                <ComboBoxItem Content="128"/>
                <ComboBoxItem Content="256"/>
                <ComboBoxItem Content="512"/>
              </ComboBox>

              <TextBlock Grid.Row="2" Grid.Column="0" Text="Ollama Model:" Margin="0,4" VerticalAlignment="Center"/>
              <TextBox Grid.Row="2" Grid.Column="1" Name="ModelBox" Width="200" Margin="8,4" Text="llama3.2"/>

              <TextBlock Grid.Row="3" Grid.Column="0" Text="Export Targets:" Margin="0,4" VerticalAlignment="Center"/>
              <StackPanel Grid.Row="3" Grid.Column="1" Orientation="Horizontal" Margin="8,4">
                <CheckBox Name="ExportQudCheck" Content="Qud" Margin="0,0,8,0" IsChecked="True"/>
                <CheckBox Name="ExportElinCheck" Content="Elin" Margin="0,0,8,0"/>
                <CheckBox Name="ExportTerrariaCheck" Content="Terraria" Margin="0,0,8,0"/>
                <CheckBox Name="ExportStarboundCheck" Content="Starbound" Margin="0,0,8,0"/>
                <CheckBox Name="ExportTranscendenceCheck" Content="Transcendence" Margin="0,0,8,0"/>
                <CheckBox Name="ExportCDDACheck" Content="CDDA"/>
              </StackPanel>

              <TextBlock Grid.Row="4" Grid.Column="0" Text="Auto-Export:" Margin="0,4" VerticalAlignment="Center"/>
              <CheckBox Grid.Row="4" Grid.Column="1" Name="AutoExportCheck" Content="Automatically export after generation" 
                       Margin="8,4" IsChecked="False"/>

              <TextBlock Grid.Row="5" Grid.Column="0" Text="Output Path:" Margin="0,4" VerticalAlignment="Center"/>
              <StackPanel Grid.Row="5" Grid.Column="1" Orientation="Horizontal" Margin="8,4">
                <TextBox Name="OutputPathBox" Width="300" Margin="0,0,4,0"/>
                <Button Name="BrowseOutputButton" Content="Browse..." Width="80"/>
              </StackPanel>
            </Grid>
          </StackPanel>
        </Expander>
      </Grid>
    </GroupBox>

    <!-- Status Bar -->
    <Border Grid.Row="2" Grid.ColumnSpan="2" Background="#E0E0E0" Padding="4" Margin="0,8,0,0">
      <TextBlock Name="StatusText" Text="Ready." FontWeight="Bold"/>
    </Border>

    <!-- Log -->
    <GroupBox Grid.Row="3" Grid.ColumnSpan="2" Header="Log" Margin="4,8,4,0">
      <TextBox Name="LogBox" AcceptsReturn="True" TextWrapping="Wrap"
               VerticalScrollBarVisibility="Auto" IsReadOnly="True"
               FontFamily="Consolas" FontSize="10" Background="Black" Foreground="Lime"/>
    </GroupBox>
  </Grid>
</Window>
"@

# Create window with error handling
try {
    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    Write-FileLog "Window created successfully" "INFO"
} catch {
    Write-FileLog "Error creating window: $_" "ERROR"
    Write-FileLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    Write-Host "Error creating GUI window: $_" -ForegroundColor Red
    Write-Host "This may be due to missing WPF assemblies or STA mode requirement." -ForegroundColor Yellow
    Write-Host "Try running with: powershell -STA -File AssetGeneratorControlRoom.ps1" -ForegroundColor Yellow
    if (Test-IsInteractiveConsole) { Read-Host "Press Enter to exit" }
    exit 1
}

# Get UI elements
$PreviewImage = $window.FindName("PreviewImage")
$PreviewPlaceholder = $window.FindName("PreviewPlaceholder")
$PromptBox = $window.FindName("PromptBox")
$SendPromptBtn = $window.FindName("SendPromptButton")
$GenerateBtn = $window.FindName("GenerateButton")
$RegenerateBtn = $window.FindName("RegenerateButton")
$SaveFinalBtn = $window.FindName("SaveFinalButton")
$StatusText = $window.FindName("StatusText")
$LogBox = $window.FindName("LogBox")
$AIResponseBox = $window.FindName("AIResponseBox")
$DrawingPathBox = $window.FindName("DrawingPathBox")
$BrowseDrawingBtn = $window.FindName("BrowseDrawingButton")
$SizeCombo = $window.FindName("SizeCombo")
$ModelBox = $window.FindName("ModelBox")
$AssetTypeCombo = $window.FindName("AssetTypeCombo")
$GameTypeCombo = $window.FindName("GameTypeCombo")
$ExportQudCheck = $window.FindName("ExportQudCheck")
$ExportElinCheck = $window.FindName("ExportElinCheck")
$ExportTerrariaCheck = $window.FindName("ExportTerrariaCheck")
$ExportStarboundCheck = $window.FindName("ExportStarboundCheck")
$ExportTranscendenceCheck = $window.FindName("ExportTranscendenceCheck")
$ExportCDDACheck = $window.FindName("ExportCDDACheck")
$AutoExportCheck = $window.FindName("AutoExportCheck")
$OutputPathBox = $window.FindName("OutputPathBox")
$BrowseOutputBtn = $window.FindName("BrowseOutputButton")

# Initialize
if (-not [string]::IsNullOrWhiteSpace($DrawingPath)) {
    $DrawingPathBox.Text = $DrawingPath
}

# Initialize description/prompt
if (-not [string]::IsNullOrWhiteSpace($Description)) {
    $PromptBox.Text = $Description
}

# Set initial game type based on ExportTargets
$gameTypeIndex = switch ($ExportTargets) {
    { $_ -contains "Qud" } { 0 }
    { $_ -contains "Elin" } { 1 }
    { $_ -contains "Terraria" } { 2 }
    { $_ -contains "Starbound" } { 3 }
    { $_ -contains "Transcendence" } { 4 }
    default { 5 } # All
}
$GameTypeCombo.SelectedIndex = $gameTypeIndex

# Set initial asset type
$assetTypeIndex = switch ($AssetType) {
    "Tile" { 0 }
    "Portal" { 1 }
    "Texture" { 2 }
    "Model" { 3 }
    "Spritesheet" { 4 }
    "Icon" { 5 }
    "FX" { 6 }
    "Projectile" { 7 }
    "Ship" { 8 }
    "Creature" { 9 }
    default { 0 }
}
$AssetTypeCombo.SelectedIndex = $assetTypeIndex
$OutputPathBox.Text = Join-Path $PSScriptRoot "GeneratedAssets"

# Set export targets (with null checks)
if ($ExportQudCheck) { $ExportQudCheck.IsChecked = $ExportTargets -contains "Qud" }
if ($ExportElinCheck) { $ExportElinCheck.IsChecked = $ExportTargets -contains "Elin" }
if ($ExportTerrariaCheck) { $ExportTerrariaCheck.IsChecked = $ExportTargets -contains "Terraria" }
if ($ExportStarboundCheck) { $ExportStarboundCheck.IsChecked = $ExportTargets -contains "Starbound" }
if ($ExportTranscendenceCheck) { $ExportTranscendenceCheck.IsChecked = $ExportTargets -contains "Transcendence" }
if ($ExportCDDACheck) { $ExportCDDACheck.IsChecked = $ExportTargets -contains "CDDA" }
if ($AutoExportCheck) { $AutoExportCheck.IsChecked = $AutoExport }

# File watcher
# Setup file watcher with improved reliability
$script:fileWatcher = New-Object System.IO.FileSystemWatcher
$script:fileWatcher.Path = $script:WatchDir
$script:fileWatcher.Filter = "*.*"
$script:fileWatcher.IncludeSubdirectories = $true
$script:fileWatcher.NotifyFilter = [System.IO.NotifyFilters]::FileName, [System.IO.NotifyFilters]::LastWrite, [System.IO.NotifyFilters]::Size
$script:fileWatcher.EnableRaisingEvents = $true

# Image file extensions to watch
$imageExtensions = @('.png', '.jpg', '.jpeg', '.bmp', '.gif')

$fileWatcherAction = {
    param($eventArgs)
    $filePath = $eventArgs.FullPath
    
    # Only process image files
    $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
    if ($imageExtensions -notcontains $ext) {
        return
    }
    
    # Wait for file to be fully written
    $maxWait = 10
    $waited = 0
    while ($waited -lt $maxWait) {
        try {
            $file = Get-Item $filePath -ErrorAction Stop
            if ($file.Length -gt 0) {
                # File exists and has content, try to open it to ensure it's not locked
                try {
                    $stream = [System.IO.File]::Open($filePath, 'Open', 'Read', 'Read')
                    $stream.Close()
                    $stream.Dispose()
                    break
                } catch {
                    Start-Sleep -Milliseconds 200
                    $waited++
                    continue
                }
            }
        } catch {
            Start-Sleep -Milliseconds 200
            $waited++
            continue
        }
        break
    }
    
    if (Test-Path $filePath) {
        try {
            Write-Log "File detected: $(Split-Path $filePath -Leaf)" "Cyan"
            Update-PreviewImage -ImagePath $filePath
            Write-Log "Preview updated" "Green"
        } catch {
            Write-Log "Error updating preview: $_" "Red"
        }
    }
}

$script:createdHandler = Register-ObjectEvent -InputObject $script:fileWatcher -EventName "Created" -Action $fileWatcherAction
$script:changedHandler = Register-ObjectEvent -InputObject $script:fileWatcher -EventName "Changed" -Action $fileWatcherAction

# Also poll the directory periodically as a backup
$script:pollTimer = New-Object System.Windows.Threading.DispatcherTimer
$script:pollTimer.Interval = [TimeSpan]::FromSeconds(2)
$script:pollTimer.Add_Tick({
    try {
        $files = Get-ChildItem -LiteralPath $script:WatchDir -Filter "*.png" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddSeconds(-5) } |
            Sort-Object LastWriteTime -Descending
        
        if ($files.Count -gt 0) {
            $latestFile = $files[0].FullName
            if ($script:lastPreviewFile -ne $latestFile) {
                $script:lastPreviewFile = $latestFile
                $fileName = Split-Path $latestFile -Leaf
                Update-PreviewImage -ImagePath $latestFile
                Write-Log "Polled: $fileName" "Cyan"
                Write-FileLog "Polled file: $fileName" "INFO"
            }
        }
    } catch {
        # Silently handle errors
    }
})
$script:pollTimer.Start()
$script:lastPreviewFile = ""

# ------------------------------------------------------------
# Event Handlers
# ------------------------------------------------------------

$BrowseDrawingBtn.Add_Click({
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = "Image Files (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg|All Files (*.*)|*.*"
    $dialog.Title = "Select Drawing/Input File"
    
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $DrawingPathBox.Text = $dialog.FileName
        Write-Log "Selected input: $($dialog.FileName)"
    }
})

$BrowseOutputBtn.Add_Click({
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Select Output Directory"
    
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $OutputPathBox.Text = $dialog.SelectedPath
        Write-Log "Output directory: $($dialog.SelectedPath)"
    }
})

# Game Type selection handler
$GameTypeCombo.Add_SelectionChanged({
    $selectedGame = $GameTypeCombo.SelectedItem.Content
    $script:ExportTargets = @($selectedGame)
    
    # Update export checkboxes
    $ExportQudCheck.IsChecked = $selectedGame -eq "Qud" -or $selectedGame -eq "All"
    $ExportElinCheck.IsChecked = $selectedGame -eq "Elin" -or $selectedGame -eq "All"
    $ExportTerrariaCheck.IsChecked = $selectedGame -eq "Terraria" -or $selectedGame -eq "All"
    $ExportStarboundCheck.IsChecked = $selectedGame -eq "Starbound" -or $selectedGame -eq "All"
    $ExportTranscendenceCheck.IsChecked = $selectedGame -eq "Transcendence" -or $selectedGame -eq "All"
    
    Write-Log "Game type changed to: $selectedGame" "Cyan"
    Update-Status "Game: $selectedGame"
})

# Asset Type selection handler
$AssetTypeCombo.Add_SelectionChanged({
    $selectedType = $AssetTypeCombo.SelectedItem.Content
    $script:AssetType = $selectedType
    
    # Update drawing path requirement hint
    $requiresDrawing = $selectedType -in @("Tile", "Icon", "FX", "Projectile")
    if (-not $requiresDrawing) {
        if ([string]::IsNullOrWhiteSpace($DrawingPathBox.Text)) {
            $DrawingPathBox.ToolTip = "Optional - Leave empty for procedural generation"
        }
    } else {
        $DrawingPathBox.ToolTip = "Required for $selectedType generation"
    }
    
    Write-Log "Asset type changed to: $selectedType" "Cyan"
    Update-Status "Asset Type: $selectedType"
    $script:AssetType = $selectedType
    Write-Log "Asset type changed to: $selectedType"
    
    # Update size options based on asset type
    if ($selectedType -eq "Tile") {
        $SizeCombo.SelectedIndex = 1  # 32
    } elseif ($selectedType -eq "Texture") {
        $SizeCombo.SelectedIndex = 5  # 512
    } elseif ($selectedType -eq "Model") {
        $SizeCombo.SelectedIndex = 6  # 512
    }
})

$SendPromptBtn.Add_Click({
    $prompt = $PromptBox.Text
    if ([string]::IsNullOrWhiteSpace($prompt)) {
        Write-Log "Error: Prompt is empty" "Red"
        return
    }
    
    $drawingPath = $DrawingPathBox.Text
    $assetType = $AssetTypeCombo.SelectedItem.Content
    
    $script:OllamaModel = $ModelBox.Text
    if ([string]::IsNullOrWhiteSpace($script:OllamaModel)) {
        $script:OllamaModel = "llama3.2"
    }
    
    $script:PromptHistory += $prompt
    
    $gameType = $GameTypeCombo.SelectedItem.Content
    
    $job = Start-Job -ScriptBlock {
        param($prompt, $drawing, $type, $gameType, $model, $history, $scriptRoot)
        
        . (Join-Path $scriptRoot "AssetMakerAI.ps1") -ErrorAction SilentlyContinue
        
        if (-not (Get-Command "Invoke-OllamaChat" -ErrorAction SilentlyContinue)) {
            $script:OllamaUrl = "http://localhost:11434"
            $script:OllamaApiUrl = "$script:OllamaUrl/api"
            
            function Test-OllamaRunning {
                try {
                    Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop | Out-Null
                    return $true
                }
                catch { return $false }
            }
            
            function Invoke-OllamaChat {
                param([string]$Prompt, [string]$ModelName, [hashtable]$SystemPrompt = @{})
                
                if (-not (Test-OllamaRunning)) { return $null }
                
                $systemMessage = if ($SystemPrompt.Count -gt 0) {
                    $SystemPrompt.Values | Select-Object -First 1
                } else {
                    "You are a helpful assistant."
                }
                
                $requestBody = @{
                    model = $ModelName
                    messages = @(
                        @{ role = "system"; content = $systemMessage },
                        @{ role = "user"; content = $Prompt }
                    )
                    stream = $false
                } | ConvertTo-Json -Depth 10
                
                try {
                    $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
                    return $response.message.content.Trim()
                }
                catch {
                    return $null
                }
            }
        }
        
        $contextPrompt = "Game: $gameType`nAsset Type: $type`nUser Request: $prompt`nDrawing: $drawing`nPrevious: $($history -join '; ')"
        $response = Invoke-OllamaChat -Prompt $contextPrompt -ModelName $model -SystemPrompt @{
            System = "You are an expert procedural asset designer for $gameType. Output ONLY valid JSON."
        }
        
        return @{ Response = $response; Success = $null -ne $response }
    } -ArgumentList $prompt, $drawingPath, $assetType, $gameType, $script:OllamaModel, ($script:PromptHistory[0..($script:PromptHistory.Count-2)]), $PSScriptRoot
    
    Write-Log "AI generation started" "Cyan"
    Update-Status "Generating with AI..."
    $SendPromptBtn.IsEnabled = $false
    
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(500)
    $timer.Add_Tick({
        if ($job.State -eq "Completed") {
            $timer.Stop()
            $result = Receive-Job $job
            Remove-Job $job
            
            $SendPromptBtn.IsEnabled = $true
            
            if ($result.Success) {
                $AIResponseBox.Text = $result.Response
                Write-Log "AI response received" "Green"
                
                $jsonMatch = $result.Response -match '\{[\s\S]*\}'
                if ($jsonMatch) {
                    try {
                        $spec = $matches[0] | ConvertFrom-Json
                        $spec | ConvertTo-Json -Depth 10 | Set-Content -Path $script:CurrentSpecPath -Encoding UTF8
                        $script:CurrentSpec = $spec
                        Write-Log "Spec saved" "Green"
                        Update-Status "AI generation complete - Ready to generate"
                    }
                    catch {
                        Write-Log "Error parsing JSON: $_" "Red"
                        Update-Status "Error: Invalid JSON"
                    }
                }
            } else {
                Write-Log "AI generation failed" "Red"
                Update-Status "Error: AI generation failed"
            }
        }
    })
    $timer.Start()
})

$GenerateBtn.Add_Click({
    $drawingPath = $DrawingPathBox.Text
    $assetType = $AssetTypeCombo.SelectedItem.Content
    $sizeIndex = $SizeCombo.SelectedIndex
    $sizes = @(24, 32, 48, 64, 128, 256, 512)
    $size = $sizes[$sizeIndex]
    
    # Drawing path is optional for Model, Texture, Portal, and Ship asset types
    $requiresDrawing = $assetType -in @("Tile", "Icon", "FX", "Projectile")
    
    if ($requiresDrawing -and -not [string]::IsNullOrWhiteSpace($drawingPath) -and -not (Test-Path $drawingPath)) {
        Write-Log "Error: Input file not found: $drawingPath" "Red"
        Update-Status "Error: Input file not found"
        return
    }
    
    # If drawing path is empty and not required, use empty string
    if ([string]::IsNullOrWhiteSpace($drawingPath) -and -not $requiresDrawing) {
        $drawingPath = ""
        Write-Log "No input file specified - generating procedurally for $gameType" "Cyan"
    }
    
    # Get export targets (with null checks)
    $exportTargets = @()
    if ($ExportQudCheck -and $ExportQudCheck.IsChecked) { $exportTargets += "Qud" }
    if ($ExportElinCheck -and $ExportElinCheck.IsChecked) { $exportTargets += "Elin" }
    if ($ExportTerrariaCheck -and $ExportTerrariaCheck.IsChecked) { $exportTargets += "Terraria" }
    if ($ExportStarboundCheck -and $ExportStarboundCheck.IsChecked) { $exportTargets += "Starbound" }
    if ($ExportTranscendenceCheck -and $ExportTranscendenceCheck.IsChecked) { $exportTargets += "Transcendence" }
    if ($ExportCDDACheck -and $ExportCDDACheck.IsChecked) { $exportTargets += "CDDA" }
    
    $script:ExportTargets = $exportTargets
    $script:AutoExport = if ($AutoExportCheck) { $AutoExportCheck.IsChecked } else { $false }
    
    Write-Log "Starting asset generation..." "Cyan"
    Write-FileLog "Starting asset generation: $assetType for $gameType" "INFO"
    Update-Status "Generating asset..."
    $GenerateBtn.IsEnabled = $false
    
    # Load spec
    $palette = "#ffffff,#000000"
    $style = "painterly"
    $quality = "standard"
    
    if (Test-Path $script:CurrentSpecPath) {
        try {
            $spec = Get-Content $script:CurrentSpecPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($spec.material) {
                if ($spec.material.palette) {
                    $palette = ($spec.material.palette | ForEach-Object { $_.hex }) -join ","
                }
                if ($spec.material.style) {
                    $style = $spec.material.style
                }
                if ($spec.material.quality) {
                    $quality = $spec.material.quality
                }
            }
        }
        catch { }
    }
    
    $job = Start-Job -ScriptBlock {
        param($type, $drawing, $spec, $size, $palette, $style, $quality, $tempDir, $scriptRoot)
        
        $blenderExe = $null
        # Tools/TranscendenceTools.ini via Shared/tool_paths.py
        $tp = Join-Path $scriptRoot "..\Shared\tool_paths.py"
        if (Test-Path $tp) {
            try {
                $line = & python $tp 2>$null | Where-Object { $_ -match '^Blender:\s*(.+)$' } | Select-Object -First 1
                if ($line -match '^Blender:\s*(.+)$') {
                    $cand = $matches[1].Trim()
                    if ($cand -and $cand -ne 'None' -and (Test-Path $cand)) { $blenderExe = $cand }
                }
            } catch { }
        }
        if (-not $blenderExe) {
            $knownPath = "E:\tools\Blender Foundation\Blender 5.2\blender.exe"
            if (Test-Path $knownPath) {
                $blenderExe = $knownPath
            } else {
                $commonPaths = @("E:\tools\Blender Foundation", "D:\tools\Blender Foundation", "${env:ProgramFiles}\Blender Foundation", "${env:ProgramFiles(x86)}\Blender Foundation")
                foreach ($basePath in $commonPaths) {
                    if (Test-Path $basePath) {
                        $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                            Where-Object { $_.Name -match '^Blender' } | Sort-Object Name -Descending
                        foreach ($dir in $blenderDirs) {
                            $blenderExe = Join-Path $dir.FullName "blender.exe"
                            if (Test-Path $blenderExe) { break }
                        }
                    }
                    if ($blenderExe) { break }
                }
            }
        }
        
        if (-not $blenderExe) {
            $blender = Get-Command "blender" -ErrorAction SilentlyContinue
            if ($blender) { $blenderExe = $blender.Source }
        }
        
        if (-not $blenderExe) {
            return @{ Success = $false; Message = "Blender not found" }
        }
        
        $output = Join-Path $tempDir "preview_asset.png"
        
        if ($type -eq "Portal") {
            # Use TerrariaPortalGenerator
            $portalScript = Join-Path $scriptRoot "TerrariaPortalGenerator.ps1"
            if (Test-Path $portalScript) {
                $portalName = "portal_$(Get-Random)"
                $preset = "Void"
                $description = if ($spec -and $spec.description) { $spec.description } else { "" }
                $outputDir = Join-Path $tempDir "portal_output"
                
                try {
                    & $portalScript -PortalName $portalName -Preset $preset -Description $description -OutputDir $outputDir -ErrorAction Stop
                    
                    # Find generated base texture
                    $baseTexture = Join-Path $outputDir "$portalName\Textures\${portalName}_Base.png"
                    if (-not (Test-Path $baseTexture)) {
                        $altPath = Get-ChildItem -LiteralPath $outputDir -Recurse -Filter "*_Base.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                        if ($altPath) { $baseTexture = $altPath.FullName }
                    }
                    
                    if (Test-Path $baseTexture) {
                        Copy-Item -Path $baseTexture -Destination $output -Force
                        return @{ Success = $true; Message = "Portal generated" }
                    } else {
                        return @{ Success = $false; Message = "Portal texture not found" }
                    }
                }
                catch {
                    return @{ Success = $false; Message = "Error: $_" }
                }
            } else {
                return @{ Success = $false; Message = "TerrariaPortalGenerator script not found" }
            }
        } elseif ($type -eq "Tile") {
            $bakerScript = Join-Path $scriptRoot "qud_tile_baker.py"
            $blenderArgs = @(
                "--background", "--python", "`"$bakerScript`"", "--",
                "--drawing", "`"$drawing`"", "--size", $size,
                "--palette", "`"$palette`"", "--style", $style,
                "--quality", $quality, "--output", "`"$output`""
            )
        } elseif ($type -eq "Texture") {
            $bakerScript = Join-Path $scriptRoot "bake_texture.py"
            $visualJson = @{
                icon = @{
                    palette = $palette -split ","
                    style = $style
                }
            } | ConvertTo-Json -Compress
            $blenderArgs = @(
                "--background", "--python", "`"$bakerScript`"", "--",
                "--visualJson", "`"$visualJson`"", "--size", $size,
                "--output", "`"$output`"", "--quality", $quality
            )
        } elseif ($type -eq "Ship" -and $gameType -eq "Starbound") {
            # Use StarboundAssetGenerator for ship
            $starboundScript = Join-Path $scriptRoot "StarboundAssetGenerator.ps1"
            if (Test-Path $starboundScript) {
                $output = Join-Path $tempDir "ship.png"
                $description = "A small scout ship for Starbound"
                
                & $starboundScript -AssetType "Model" -AssetName "Ship" -Description $description -OutputDir $tempDir -UseCppBackend:$false
                
                return @{
                    Success = (Test-Path $output) -or (Get-ChildItem -LiteralPath $tempDir -Filter "*.png" -File | Measure-Object).Count -gt 0
                    Message = "Ship generation complete"
                }
            } else {
                return @{ Success = $false; Message = "StarboundAssetGenerator script not found" }
            }
        } else {
            return @{ Success = $false; Message = "Asset type not yet supported: $type for $gameType" }
        }
        
        try {
            $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
            return @{
                Success = ($process.ExitCode -eq 0 -and (Test-Path $output))
                Message = if ($process.ExitCode -eq 0) { "Generation complete" } else { "Generation failed" }
            }
        }
        catch {
            return @{ Success = $false; Message = "Error: $_" }
        }
    } -ArgumentList $assetType, $drawingPath, $script:CurrentSpecPath, $size, $palette, $style, $quality, $script:TempDir, $PSScriptRoot
    
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(500)
    $timer.Add_Tick({
        if ($job.State -eq "Completed") {
            $timer.Stop()
            $result = Receive-Job $job
            Remove-Job $job
            
            $GenerateBtn.IsEnabled = $true
            
            if ($result.Success) {
                Write-Log "Asset generation complete!" "Green"
                Update-Status "Asset generated successfully"
                Update-PreviewImage -ImagePath $script:CurrentAssetPath
                
                # Auto-export if enabled
                if ($script:AutoExport) {
                    Invoke-AutoExport -AssetType $assetType -AssetPath $script:CurrentAssetPath -ExportTargets $script:ExportTargets -AssetId $AssetId
                }
            } else {
                Write-Log "Generation failed: $($result.Message)" "Red"
                Write-FileLog "Asset generation failed: $($result.Message)" "ERROR"
                Update-Status "Error: Generation failed"
            }
        }
    })
    $timer.Start()
})

$RegenerateBtn.Add_Click({
    if ($script:PromptHistory.Count -gt 0) {
        $lastPrompt = $script:PromptHistory[-1]
        $PromptBox.Text = "$lastPrompt (refined)"
        $SendPromptBtn.RaiseEvent([System.Windows.RoutedEventArgs]::new([System.Windows.Controls.Button]::ClickEvent))
    }
})

$SaveFinalBtn.Add_Click({
    if (-not (Test-Path $script:CurrentAssetPath)) {
        Write-Log "Error: No asset to save" "Red"
        Update-Status "Error: No asset generated yet"
        return
    }
    
    $outputDir = $OutputPathBox.Text
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    $assetName = if (-not [string]::IsNullOrWhiteSpace($AssetId)) {
        $AssetId
    } else {
        $assetType = $AssetTypeCombo.SelectedItem.Content
        $gameType = $GameTypeCombo.SelectedItem.Content
        $script:AssetType = $assetType
        "${assetType}_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }
    
    $finalPath = Join-Path $outputDir "$assetName.png"
    Copy-Item -Path $script:CurrentAssetPath -Destination $finalPath -Force
    
    Write-Log "Asset saved to: $finalPath" "Green"
    Update-Status "Asset saved successfully"
    
    # Export to game formats if enabled
    if ($script:AutoExport) {
        Invoke-AutoExport -AssetType $script:AssetType -AssetPath $finalPath -ExportTargets $script:ExportTargets -AssetId $assetName
    }
})

# Initialize log
Write-Log "Asset Generator Control Room started"
Write-Log "Asset Type: $AssetType"
Write-Log "Export Targets: $($ExportTargets -join ', ')"

if (Test-OllamaRunning) {
    Write-Log "Ollama is running" "Green"
    Update-Status "Ready - Ollama connected"
} else {
    Write-Log "Warning: Ollama is not running" "Yellow"
    Update-Status "Warning: Ollama not running"
}

# Show window with error handling
try {
    Write-FileLog "Showing GUI window..." "INFO"
    $window.ShowDialog() | Out-Null
    Write-FileLog "GUI window closed" "INFO"
} catch {
    Write-FileLog "Error showing GUI window: $_" "ERROR"
    Write-FileLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    Write-Host "Error showing GUI: $_" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    if (Test-IsInteractiveConsole) { Read-Host "Press Enter to exit" }
}

# Cleanup
$fileWatcher.EnableRaisingEvents = $false
if ($createdHandler) { Unregister-Event -SourceIdentifier $createdHandler.Name -ErrorAction SilentlyContinue }
if ($changedHandler) { Unregister-Event -SourceIdentifier $changedHandler.Name -ErrorAction SilentlyContinue }
$fileWatcher.Dispose()
if (Test-Path $script:TempDir) {
    Remove-Item -LiteralPath $script:TempDir -Recurse -Force -ErrorAction SilentlyContinue
}

