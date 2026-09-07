<#
.SYNOPSIS
    Enhanced Ollama-Powered Asset Generator for Elin Mod
    AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Generates high-quality assets and spritesheets using Ollama AI for intelligent
    prompt generation and specifications. Uses the Shared Ollama integration module
    for optimal performance.
    
    Features:

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - AI-powered asset specifications using Ollama
    - High-quality procedural image generation
    - Spritesheet generation for batch assets
    - Integration with existing asset generators
    - Support for all asset types (icons, sprites, textures, spell assets)

.PARAMETER ModPath
    Path to the mod directory

.PARAMETER AssetTypes
    Comma-separated list of asset types (icons, sprites, textures, spell_assets, all)

.PARAMETER Systems
    Comma-separated list of magic systems (or "all")

.PARAMETER OutputDir
    Output directory for generated assets

.PARAMETER UseOllama
    Use Ollama for AI-powered specifications (default: true)

.PARAMETER GenerateSpritesheets
    Generate spritesheets for batch assets

.PARAMETER Quality
    Asset quality level (low, medium, high, ultra)

.EXAMPLE
    .\OllamaAssetGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -AssetTypes "textures,icons" -UseOllama

.EXAMPLE
    .\OllamaAssetGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -AssetTypes "all" -GenerateSpritesheets -Quality "high"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [string]$AssetTypes = "all",
    
    [string]$Systems = "all",
    
    [string]$OutputDir = "",
    
    [switch]$UseOllama,
    
    [switch]$GenerateSpritesheets,
    
    [ValidateSet("low", "medium", "high", "ultra")]
    [string]$Quality = "high"
)

$ErrorActionPreference = "Stop"

# Set PSScriptRoot if not set (when script is dot-sourced)
if (-not $PSScriptRoot) {
    if ($MyInvocation.MyCommand.Path) {
        $PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    } elseif ($PSCommandPath) {
        $PSScriptRoot = Split-Path -Parent $PSCommandPath
    } else {
        $PSScriptRoot = $PWD.Path
    }
}

# Import unified tool detection and integration
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedPath = Join-Path $toolsRoot "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $PSScriptRoot "ElinAssetRender.psm1") -Force -ErrorAction SilentlyContinue

# Initialize tools for Elin asset generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin" `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")
Write-Host ""

# Check Python dependency with Pillow
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$pythonAvailable = Test-PythonDependency -CheckPillow
if (-not $pythonAvailable) {
    Write-Host ""
    Write-Host "WARNING: Python or Pillow is missing. Asset generation may fail." -ForegroundColor Yellow
    Write-Host "  Some features will be disabled or use fallback methods." -ForegroundColor Yellow
    Write-Host ""
}

# Use Ollama if available
if ($UseOllama) {
    $ollamaAvailable = Use-OllamaIfAvailable
    if (-not $ollamaAvailable) {
        Write-Host "⚠ Warning: Ollama not available, but -UseOllama was specified" -ForegroundColor Yellow
        Write-Host "  Continuing without Ollama AI features..." -ForegroundColor Gray
        $script:UseOllama = $false
    } else {
        Write-Host "✓ Ollama integration enabled" -ForegroundColor Green
    }
}

# Configuration
$script:ModPath = $ModPath
$script:OutputDir = if ($OutputDir) { $OutputDir } else { Join-Path $ModPath "GeneratedAssets" }
$script:Quality = $Quality
$script:UseOllama = if ($UseOllama) { $true } else { $false }
$script:GenerateSpritesheets = if ($GenerateSpritesheets) { $true } else { $false }
$script:AssetTypes = $AssetTypes
$script:Systems = $Systems

# Quality settings
$script:QualitySettings = @{
    "low" = @{ Size = 128; Detail = "basic"; Colors = 2 }
    "medium" = @{ Size = 256; Detail = "standard"; Colors = 4 }
    "high" = @{ Size = 512; Detail = "enhanced"; Colors = 6 }
    "ultra" = @{ Size = 1024; Detail = "ultra"; Colors = 8 }
}

# Asset type configurations
$script:AssetConfigs = @{
    "icons" = @{
        DefaultSize = 32
        Folder = "Icons"
        Description = "UI icons for menus and interfaces"
    }
    "sprites" = @{
        DefaultSize = 64
        Folder = "Sprites"
        Description = "Character and object sprites"
    }
    "textures" = @{
        DefaultSize = 512
        Folder = "Textures"
        Description = "Material textures for 3D objects - tileable, Unity-compatible, power-of-2"
    }
    "spell_assets" = @{
        DefaultSize = 32
        Folder = "SpellAssets"
        Description = "Spell icons, effects, and projectiles"
    }
}

# All systems
$script:AllSystems = @(
    "DragonMagic", "DreamMagic", "ElementMagic", "WispMagic", "DruidicMagic",
    "Crossmagic", "RiverMagic", "Pollution", "ArcaneSaturation", "BardicMagic",
    "SpiritMagic", "Geomancy", "Necromancy", "BloodMagic", "Golemancy",
    "SpectreMagic", "Technomancy", "TerrainMagic", "WeatherMagic", "RuneMagic",
    "EtherwindMagic", "Geoscience", "DynamicSpells", "SlotMagic",
    "PactMagic", "RitualMagic", "SlotMachine", "AIAssistant", "PCCMutation",
    "QuestPlus", "SpriteAlter", "CombatPlus", "EditorWindows", "UI", "UIButtons",
    "SpellEffects", "ComputeShaders"
)

# Progress tracking
$script:Progress = @{
    TotalAssets = 0
    GeneratedAssets = 0
    FailedAssets = 0
    StartTime = Get-Date
}

# Note: Model selection uses Shared OllamaIntegration.psm1 tier system
# The shared module automatically:
# - Routes visual tasks to "visual" tier (llama3.1:8b by default)
# - Detects dark tone content via Test-DarkTone and routes to "dark_tone" tier
# - Escalates to "escalation" tier if models refuse
# No custom model selection needed - use Invoke-OllamaRequest with TaskType="visual"

# ============================================================
# OLLAMA INTEGRATION
# ============================================================

function Test-OllamaForAssets {
    <#
    .SYNOPSIS
    Tests Ollama connection and prepares for asset generation.
    #>
    if (-not $script:UseOllama) {
        Write-Host "  Ollama disabled, using default specifications" -ForegroundColor Gray
        return $false
    }
    
    Write-Host "`n🔍 Testing Ollama connection..." -ForegroundColor Cyan
    
    if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
        $result = Test-OllamaConnection
        if ($result) {
            Write-Host "✓ Ollama ready for asset generation" -ForegroundColor Green
            return $true
        }
    } else {
        # Fallback: test connection manually
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
            if ($response.models -and $response.models.Count -gt 0) {
                Write-Host "✓ Ollama ready (found $($response.models.Count) models)" -ForegroundColor Green
                return $true
            }
        } catch {
            Write-Host "⚠ Ollama not available: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "  Continuing with default specifications..." -ForegroundColor Gray
            # Don't return here, fall through to return false
        }
    }
    
    return $false
}

function Get-AIAssetSpecification {
    <#
    .SYNOPSIS
    Uses Ollama to generate detailed asset specifications.
    #>
    param(
        [string]$SystemName,
        [string]$AssetType,
        [string]$Description = ""
    )
    
    if (-not $script:UseOllama) {
        return Get-DefaultAssetSpec -SystemName $SystemName -AssetType $AssetType
    }
    
    $quality = $script:QualitySettings[$script:Quality]
    $assetConfig = $script:AssetConfigs[$AssetType]
    
    $prompt = @"
Generate a detailed JSON specification for a $AssetType asset for the $SystemName magic system.

Asset Requirements:
- Type: $AssetType ($($assetConfig.Description))
- Target Size: $($quality.Size)px
- Quality Level: $($quality.Detail)
- System Theme: $SystemName

$Description

Generate a JSON specification with:
- colors: Array of $($quality.Colors) hex colors appropriate for $SystemName
- pattern: Pattern type (gradient, noise, organic, geometric, etc.)
- style: Visual style (painterly, pixel-art, realistic, stylized)
- effects: Array of visual effects (glow, shadow, rim-light, etc.)
- theme: Theme elements specific to $SystemName
- size: Recommended size in pixels
- details: Array of detail elements to include
- tileable: true (for textures, ensure they can tile seamlessly)

Return ONLY valid JSON, no markdown, no code blocks, just the JSON object.
"@
    
    $systemPrompt = "You are a professional game asset designer. Generate precise JSON specifications for game assets. Always return valid JSON only."
    
    # Use Shared OllamaIntegration - automatically handles dark tone detection and tier routing
    # For visual tasks, it auto-detects dark tone and routes to dark_tone tier
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $response = Invoke-OllamaRequest -Prompt $prompt -TaskType "visual" -SystemPrompt $systemPrompt -ResponseLength "standard" -UseChatAPI -AutoEscalate
    } else {
        # Fallback implementation (should not be needed if Shared module is loaded)
        try {
            $body = @{
                model = "llama3.1:8b"  # Default fallback
                messages = @(
                    @{ role = "system"; content = $systemPrompt }
                    @{ role = "user"; content = $prompt }
                )
                stream = $false
            } | ConvertTo-Json -Depth 10
            
            $response = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
            $response = $response.message.content
        } catch {
            Write-Host "  ⚠ Ollama request failed, using defaults" -ForegroundColor Yellow
            return Get-DefaultAssetSpec -SystemName $SystemName -AssetType $AssetType
        }
    }
    
    if ($response) {
        try {
            # Extract JSON from response
            if ($response -match '\{.*\}') {
                $jsonMatch = $Matches[0]
                $spec = $jsonMatch | ConvertFrom-Json
                Write-Host "  ✓ Generated AI specification" -ForegroundColor Green
                return $spec
            }
        } catch {
            Write-Host "  ⚠ Failed to parse AI response, using defaults" -ForegroundColor Yellow
        }
    }
    
    return Get-DefaultAssetSpec -SystemName $SystemName -AssetType $AssetType
}

function Get-DefaultAssetSpec {
    <#
    .SYNOPSIS
    Returns default asset specification when AI is not available.
    #>
    param(
        [string]$SystemName,
        [string]$AssetType
    )
    
    $quality = $script:QualitySettings[$script:Quality]
    
    # System-specific color palettes
    $systemColors = @{
        "DragonMagic" = @("#ff4444", "#ff8844", "#ffaa44", "#ffcc44")
        "BloodMagic" = @("#8b0000", "#cc0000", "#ff0000", "#ff4444")
        "Necromancy" = @("#2d2d2d", "#4a4a4a", "#6b6b6b", "#8b8b8b")
        "DruidicMagic" = @("#2d5016", "#4a7c2a", "#6ba83a", "#8bc34a")
        "ElementMagic" = @("#1e88e5", "#42a5f5", "#64b5f6", "#90caf9")
        "Geomancy" = @("#5d4037", "#795548", "#8d6e63", "#a1887f")
    }
    
    $colors = if ($systemColors.ContainsKey($SystemName)) {
        $systemColors[$SystemName]
    } else {
        @("#4a90e2", "#6ba8e5", "#8bc5e8", "#a8d5eb")
    }
    
    return @{
        colors = $colors[0..([math]::Min($quality.Colors - 1, $colors.Count - 1))]
        pattern = "gradient"
        style = "stylized"
        effects = @("glow")
        theme = $SystemName
        size = $quality.Size
        details = @()
    }
}

# ============================================================
# DEPENDENCY CHECKING
# ============================================================

function Test-PythonDependency {
    <#
    .SYNOPSIS
    Tests if Python is available and checks for required packages.
    #>
    param(
        [switch]$CheckPillow
    )
    
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { 
        $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue 
    }
    
    if (-not $pythonCmd) {
        Write-Host "  [ERROR] Python is not installed or not in PATH" -ForegroundColor Red
        Write-Host "    Install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "    Make sure to add Python to your PATH during installation" -ForegroundColor Yellow
        return $false
    }
    
    $pythonVersion = & $pythonCmd.Source --version 2>&1
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
    
    if ($CheckPillow) {
        # Check for Pillow
        $pillowCheck = & $pythonCmd.Source -c "import PIL; print('OK')" 2>&1
        if ($LASTEXITCODE -ne 0 -or $pillowCheck -notmatch "OK") {
            Write-Host "  [ERROR] Pillow (PIL) is not installed" -ForegroundColor Red
            Write-Host "    Install it with: pip install Pillow" -ForegroundColor Yellow
            Write-Host "    Or: $($pythonCmd.Source) -m pip install Pillow" -ForegroundColor Yellow
            return $false
        } else {
            Write-Host "  [OK] Pillow (PIL) is installed" -ForegroundColor Green
        }
    }
    
    return $true
}

function Write-ErrorWithContext {
    <#
    .SYNOPSIS
    Writes an error message with additional context and suggestions.
    #>
    param(
        [string]$Message,
        [string]$Context = "",
        [string[]]$Suggestions = @()
    )
    
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
    if ($Context) {
        Write-Host "    Context: $Context" -ForegroundColor Gray
    }
    if ($Suggestions.Count -gt 0) {
        Write-Host "    Suggestions:" -ForegroundColor Yellow
        foreach ($suggestion in $Suggestions) {
            Write-Host "      - $suggestion" -ForegroundColor Yellow
        }
    }
}

# ============================================================
# PATH UTILITIES
# ============================================================

function Normalize-PathForCommand {
    <#
    .SYNOPSIS
    Normalizes a path for use in command-line arguments, ensuring it works with spaces.
    PowerShell's array argument passing automatically handles quoting, but we ensure paths are resolved.
    #>
    param(
        [string]$Path
    )
    
    if ([string]::IsNullOrEmpty($Path)) {
        return $Path
    }
    
    # Resolve to absolute path if relative and path exists
    if (Test-Path $Path) {
        try {
            $resolved = Resolve-Path -Path $Path -ErrorAction Stop
            return $resolved.Path
        } catch {
            # If resolution fails, return original path
            return $Path
        }
    }
    
    # If path doesn't exist yet (e.g., output path), normalize it but keep original format
    # PowerShell will handle quoting automatically when passed in array
    return $Path
}

function Join-PathArray {
    <#
    .SYNOPSIS
    Joins an array of paths with a delimiter, handling paths with spaces and special characters.
    Uses a safe delimiter approach for paths that may contain commas.
    #>
    param(
        [array]$Paths,
        [string]$Delimiter = ","
    )
    
    $normalizedPaths = @()
    foreach ($path in $Paths) {
        # Normalize each path
        $normalized = Normalize-PathForCommand -Path $path
        # For paths with spaces or commas, we need special handling
        # Since we're joining with comma, we'll use a different approach if paths contain commas
        if ($normalized -match ',') {
            # If path contains comma, we need to escape or use different delimiter
            # For now, quote the entire path
            $normalizedPaths += "`"$normalized`""
        } else {
            $normalizedPaths += $normalized
        }
    }
    
    return $normalizedPaths -join $Delimiter
}

# ============================================================
# ASSET GENERATION
# ============================================================

function Generate-Asset {
    <#
    .SYNOPSIS
    Generates a single asset using AI specifications.
    #>
    param(
        [string]$SystemName,
        [string]$AssetType,
        [string]$AssetName,
        [object]$Specification
    )
    
    $assetConfig = $script:AssetConfigs[$AssetType]
    
    # Canonical CRCC / Unity layout: Assets/Resources/{System}/{Folder}
    $resourcesRoot = Join-Path $script:ModPath "Assets\Resources"
    if (-not (Test-Path $resourcesRoot)) {
        # Fall back to GeneratedAssets only when Resources does not exist yet
        $outputPath = Join-Path $script:OutputDir $assetConfig.Folder
        $outputPath = Join-Path $outputPath $SystemName
    } else {
        $outputPath = Join-Path $resourcesRoot $SystemName
        $outputPath = Join-Path $outputPath $assetConfig.Folder
    }
    
    if (-not (Test-Path $outputPath)) {
        New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    }
    
    $outputFile = Join-Path $outputPath "$AssetName.png"
    
    # Use Python script for actual image generation
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $pythonScript = Join-Path $scriptDir "generate_asset_image.py"
    
    if (-not (Test-Path $pythonScript)) {
        Write-ErrorWithContext `
            -Message "Python asset generator script not found" `
            -Context "Expected at: $pythonScript" `
            -Suggestions @(
                "Verify the script file exists",
                "Check that you're running from the correct directory",
                "Ensure generate_asset_image.py is in the same directory as OllamaAssetGenerator.ps1"
            )
        # Create placeholder using PowerShell
        Create-PlaceholderAsset -OutputPath $outputFile -Specification $Specification -AssetType $AssetType
        return $false
    }
    
    # Create temporary spec file
    $tempSpec = Join-Path $env:TEMP "asset_spec_$(Get-Random).json"
    $json = $Specification | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($tempSpec, $json, (New-Object System.Text.UTF8Encoding $false))
    
    $success = $false
    try {
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { 
            $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue 
        }
        
        if ($pythonCmd) {
            # Normalize paths to handle spaces correctly
            $normalizedScript = Normalize-PathForCommand -Path $pythonScript
            $normalizedSpec = Normalize-PathForCommand -Path $tempSpec
            $normalizedOutput = Normalize-PathForCommand -Path $outputFile
            
            $args = @(
                $normalizedScript
                "--spec", $normalizedSpec
                "--output", $normalizedOutput
                "--type", $AssetType
                "--size", $Specification.size
            )
            
            $result = & $pythonCmd.Source $args 2>&1
            $exitCode = $LASTEXITCODE
            
            if ($exitCode -eq 0 -and (Test-Path $outputFile)) {
                Write-Host "  [OK] Generated: $AssetName" -ForegroundColor Green
                $success = $true
                if ($AssetType -eq "textures" -and (Get-Command Invoke-ElinPbrSkin -ErrorAction SilentlyContinue)) {
                    $skinDir = Join-Path $outputPath "Skins"
                    $skinName = ($SystemName -replace '[^A-Za-z0-9_]', '_')
                    Write-Host "  [PBR] Skin maps -> $skinDir" -ForegroundColor Cyan
                    [void](Invoke-ElinPbrSkin -OutputDir $skinDir -Name $skinName -Spec $Specification -Quality $(if ($script:Quality -eq "ultra") { "ultra" } elseif ($script:Quality -eq "high") { "high" } else { "standard" }))
                }
            } else {
                Write-ErrorWithContext `
                    -Message "Asset generation failed for $AssetName" `
                    -Context "Exit code: $exitCode, Type: $AssetType, System: $SystemName" `
                    -Suggestions @(
                        "Check Python error output above",
                        "Verify Python and Pillow are installed correctly",
                        "Check that output directory is writable",
                        "Review the specification file for errors"
                    )
                if ($result) {
                    Write-Host "    Python output: $result" -ForegroundColor Gray
                }
                $success = $false
            }
        } else {
            Write-ErrorWithContext `
                -Message "Python is not installed or not in PATH" `
                -Context "Asset: $AssetName, Type: $AssetType" `
                -Suggestions @(
                    "Install Python from https://www.python.org/downloads/",
                    "Add Python to your system PATH",
                    "Or use python3 if installed"
                )
            Create-PlaceholderAsset -OutputPath $outputFile -Specification $Specification -AssetType $AssetType
            $success = $false
        }
    }
    catch {
        Write-ErrorWithContext `
            -Message "Exception during asset generation" `
            -Context "Asset: $AssetName, Type: $AssetType, System: $SystemName" `
            -Suggestions @(
                "Check that all paths are valid",
                "Verify file permissions",
                "Ensure sufficient disk space",
                "Review the full error message above"
            )
        Write-Host "    Exception: $_" -ForegroundColor Red
        Write-Host "    Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
        $success = $false
    }
    finally {
        if (Test-Path $tempSpec) {
            Remove-Item $tempSpec -Force -ErrorAction SilentlyContinue
        }
    }
    
    return $success
}

function Create-PlaceholderAsset {
    <#
    .SYNOPSIS
    Creates a real procedural PNG when Python is unavailable (never a no-op).
    #>
    param(
        [string]$OutputPath,
        [object]$Specification,
        [string]$AssetType
    )
    
    try {
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        $size = 96
        if ($Specification -and $Specification.size) { $size = [int]$Specification.size }
        elseif ($Specification -and $Specification.Size) { $size = [int]$Specification.Size }
        Add-Type -AssemblyName System.Drawing
        $bmp = New-Object System.Drawing.Bitmap($size, $size)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $g.Clear([System.Drawing.Color]::Transparent)
        $color = switch ($AssetType) {
            "Spell" { [System.Drawing.Color]::FromArgb(255, 100, 180, 255) }
            "Item" { [System.Drawing.Color]::FromArgb(255, 80, 220, 120) }
            "Ability" { [System.Drawing.Color]::FromArgb(255, 220, 120, 255) }
            default { [System.Drawing.Color]::FromArgb(255, 120, 160, 220) }
        }
        $brush = New-Object System.Drawing.SolidBrush($color)
        $g.FillEllipse($brush, 4, 4, $size - 8, $size - 8)
        $hi = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(180, 255, 255, 255))
        $g.FillEllipse($hi, [int]($size * 0.25), [int]($size * 0.25), [int]($size * 0.2), [int]($size * 0.2))
        $brush.Dispose(); $hi.Dispose(); $g.Dispose()
        $bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        Write-Host "  [Procedural] Wrote fallback PNG: $OutputPath" -ForegroundColor Gray
    } catch {
        Write-Host "  [ERROR] Failed to write procedural PNG: $_" -ForegroundColor Red
        throw
    }
}

function Generate-Spritesheet {
    <#
    .SYNOPSIS
    Generates a spritesheet from multiple assets (Transcendence-style).
    #>
    param(
        [string]$SystemName,
        [string]$AssetType,
        [array]$Assets,
        [int]$Columns = 0,
        [int]$Rows = 0,
        [int]$FrameWidth = 0,
        [int]$FrameHeight = 0,
        [int]$Spacing = 2
    )
    
    if ($Assets.Count -eq 0) {
        return
    }
    
    Write-Host "`n📦 Generating spritesheet for $SystemName $AssetType..." -ForegroundColor Cyan
    Write-Host "  Assets: $($Assets.Count)" -ForegroundColor Gray
    
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $pythonScript = Join-Path $scriptDir "generate_spritesheet.py"
    
    if (-not (Test-Path $pythonScript)) {
        Write-Host "  ⚠ Spritesheet generator not found" -ForegroundColor Yellow
        return
    }
    
    $assetConfig = $script:AssetConfigs[$AssetType]
    $outputPath = Join-Path $script:OutputDir $assetConfig.Folder
    $outputPath = Join-Path $outputPath $SystemName
    
    # Determine frame size from asset config or quality settings
    if ($FrameWidth -eq 0) {
        $FrameWidth = if ($assetConfig.DefaultSize) { $assetConfig.DefaultSize } else { 32 }
    }
    if ($FrameHeight -eq 0) {
        $FrameHeight = $FrameWidth  # Square by default
    }
    
    # Determine grid layout
    $numAssets = $Assets.Count
    if ($Columns -eq 0 -and $Rows -eq 0) {
        # Auto-calculate: try to make it roughly square
        $Columns = [math]::Ceiling([math]::Sqrt($numAssets))
        $Rows = [math]::Ceiling($numAssets / $Columns)
    } elseif ($Columns -eq 0) {
        $Columns = [math]::Ceiling($numAssets / $Rows)
    } elseif ($Rows -eq 0) {
        $Rows = [math]::Ceiling($numAssets / $Columns)
    }
    
    $spritesheetPath = Join-Path $outputPath "${SystemName}_${AssetType}_spritesheet.png"
    
    # Build asset paths list (use actual file paths from Assets array)
    $assetPaths = @()
    foreach ($asset in $Assets) {
        if ($asset.Path -and (Test-Path $asset.Path)) {
            $assetPaths += $asset.Path
        } elseif ($asset -is [string] -and (Test-Path $asset)) {
            $assetPaths += $asset
        }
    }
    
    if ($assetPaths.Count -eq 0) {
        Write-Host "  ⚠ No valid asset paths found" -ForegroundColor Yellow
        return
    }
    
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
    
    if ($pythonCmd) {
        # Normalize paths to handle spaces correctly
        $normalizedScript = Normalize-PathForCommand -Path $pythonScript
        $normalizedOutput = Normalize-PathForCommand -Path $spritesheetPath
        $normalizedAssets = Join-PathArray -Paths $assetPaths -Delimiter ","
        
        $args = @(
            $normalizedScript
            "--assets", $normalizedAssets
            "--output", $normalizedOutput
            "--type", $AssetType
            "--spacing", $Spacing
        )
        
        # Add optional parameters
        if ($Columns -gt 0) {
            $args += "--columns", $Columns
        }
        if ($Rows -gt 0) {
            $args += "--rows", $Rows
        }
        if ($FrameWidth -gt 0) {
            $args += "--frame-width", $FrameWidth
        }
        if ($FrameHeight -gt 0) {
            $args += "--frame-height", $FrameHeight
        }
        
        Write-Host "  Grid: ${Columns}x${Rows}, Frame: ${FrameWidth}x${FrameHeight}" -ForegroundColor Gray
        
        $result = & $pythonCmd.Source $args 2>&1
        
        if ($LASTEXITCODE -eq 0 -and (Test-Path $spritesheetPath)) {
            Write-Host "  ✓ Generated spritesheet: $(Split-Path $spritesheetPath -Leaf)" -ForegroundColor Green
            
            # Check for metadata
            $metadataPath = $spritesheetPath -replace '\.png$', '.json'
            if (Test-Path $metadataPath) {
                Write-Host "  ✓ Metadata: $(Split-Path $metadataPath -Leaf)" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ✗ Spritesheet generation failed" -ForegroundColor Red
            if ($result) {
                Write-Host "  Error: $result" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  ⚠ Python not found" -ForegroundColor Yellow
    }
}

# ============================================================
# PREVIEW GENERATION
# ============================================================

function Generate-Previews {
    <#
    .SYNOPSIS
    Generates preview thumbnails and asset catalog.
    #>
    param(
        [string]$AssetsDir,
        [string]$OutputDir = ""
    )
    
    if ([string]::IsNullOrEmpty($OutputDir)) {
        $OutputDir = Join-Path $AssetsDir "previews"
    }
    
    Write-Host "`nGenerating previews and catalog..." -ForegroundColor Cyan
    
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $pythonScript = Join-Path $scriptDir "generate_previews.py"
    
    if (-not (Test-Path $pythonScript)) {
        Write-Host "  [WARN] Preview generator not found: $pythonScript" -ForegroundColor Yellow
        return $false
    }
    
    if (-not (Test-Path $AssetsDir)) {
        Write-Host "  [WARN] Assets directory does not exist: $AssetsDir" -ForegroundColor Yellow
        return $false
    }
    
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { 
        $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue 
    }
    
    if (-not $pythonCmd) {
        Write-Host "  [WARN] Python not found, skipping preview generation" -ForegroundColor Yellow
        return $false
    }
    
    try {
        # Normalize paths to handle spaces correctly
        $normalizedScript = Normalize-PathForCommand -Path $pythonScript
        $normalizedAssetsDir = Normalize-PathForCommand -Path $AssetsDir
        $normalizedOutputDir = Normalize-PathForCommand -Path $OutputDir
        
        $args = @(
            $normalizedScript
            "--assets-dir", $normalizedAssetsDir
            "--output-dir", $normalizedOutputDir
            "--thumbnail-size", "128", "128"
            "--preview-size", "512", "512"
        )
        
        $result = & $pythonCmd.Source $args 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Preview generation complete" -ForegroundColor Green
            Write-Host "  Catalog: $(Join-Path $OutputDir 'catalog.html')" -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "  [WARN] Preview generation had issues: $result" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "  [WARN] Error during preview generation: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================
# MAIN PROCESSING
# ============================================================

function Process-Assets {
    <#
    .SYNOPSIS
    Main processing function.
    #>
    
    Write-Host "`n🎨 Ollama-Powered Asset Generator" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Gray
    Write-Host "Mod Path: $($script:ModPath)" -ForegroundColor White
    Write-Host "Output: $($script:OutputDir)" -ForegroundColor White
    Write-Host "Quality: $($script:Quality)" -ForegroundColor White
    Write-Host "=" * 60 -ForegroundColor Gray
    
    # Test Ollama connection
    $ollamaAvailable = Test-OllamaForAssets
    
    # Parse asset types (use script-level variable if available, otherwise use param)
    $assetTypesParam = if ($script:AssetTypes) { $script:AssetTypes } else { $AssetTypes }
    $typesToProcess = if ($assetTypesParam -eq "all") {
        $script:AssetConfigs.Keys
    } else {
        $assetTypesParam -split "," | ForEach-Object { $_.Trim() }
    }
    
    # Parse systems (use script-level variable if available, otherwise use param)
    $systemsParam = if ($script:Systems) { $script:Systems } else { $Systems }
    $systemsToProcess = if ($systemsParam -eq "all") {
        $script:AllSystems
    } else {
        $systemsParam -split "," | ForEach-Object { $_.Trim() }
    }
    
    # Create output directory
    if (-not (Test-Path $script:OutputDir)) {
        New-Item -ItemType Directory -Path $script:OutputDir -Force | Out-Null
    }
    
    # Process each asset type
    foreach ($assetType in $typesToProcess) {
        if (-not $script:AssetConfigs.ContainsKey($assetType)) {
            Write-Host "`n⚠ Unknown asset type: $assetType" -ForegroundColor Yellow
            continue
        }
        
        Write-Host "`n📁 Processing $assetType assets..." -ForegroundColor Cyan
        
        $assetsGenerated = @()
        
        foreach ($system in $systemsToProcess) {
            Write-Host "  🎯 $system..." -ForegroundColor White
            
            # Generate AI specification
            $spec = Get-AIAssetSpecification -SystemName $system -AssetType $assetType
            
            # Generate asset
            $assetName = "$($system.ToLower())_$($assetType)"
            $result = Generate-Asset -SystemName $system -AssetType $assetType -AssetName $assetName -Specification $spec
            
            if ($result) {
                $assetsGenerated += @{
                    System = $system
                    Type = $assetType
                    Name = $assetName
                    Path = Join-Path $script:OutputDir "$($script:AssetConfigs[$assetType].Folder)\$system\$assetName.png"
                }
                $script:Progress.GeneratedAssets++
            } else {
                $script:Progress.FailedAssets++
            }
            
            $script:Progress.TotalAssets++
        }
        
        # Generate spritesheet if requested
        if ($script:GenerateSpritesheets -and $assetsGenerated.Count -gt 0) {
            $systemGroups = $assetsGenerated | Group-Object -Property System
            foreach ($group in $systemGroups) {
                # Determine optimal grid layout based on asset count
                $assetCount = $group.Group.Count
                $defaultSize = $script:AssetConfigs[$assetType].DefaultSize
                
                # Calculate optimal columns (prefer wider sheets for icons/sprites)
                $optimalColumns = if ($assetType -in @("icons", "sprites", "spell_assets")) {
                    [math]::Min(10, [math]::Ceiling([math]::Sqrt($assetCount * 1.5)))
                } else {
                    [math]::Ceiling([math]::Sqrt($assetCount))
                }
                
                Generate-Spritesheet `
                    -SystemName $group.Name `
                    -AssetType $assetType `
                    -Assets $group.Group `
                    -Columns $optimalColumns `
                    -FrameWidth $defaultSize `
                    -FrameHeight $defaultSize `
                    -Spacing 2
            }
        }
    }
    
    # Generate previews and catalog
    if ($script:Progress.GeneratedAssets -gt 0) {
        Generate-Previews -AssetsDir $script:OutputDir
    }
    
    # Summary
    $elapsed = (Get-Date) - $script:Progress.StartTime
    Write-Host "`n" + ("=" * 60) -ForegroundColor Gray
    Write-Host "✅ Generation Complete!" -ForegroundColor Green
    Write-Host "  Total Assets: $($script:Progress.TotalAssets)" -ForegroundColor White
    Write-Host "  Generated: $($script:Progress.GeneratedAssets)" -ForegroundColor Green
    Write-Host "  Failed: $($script:Progress.FailedAssets)" -ForegroundColor $(if ($script:Progress.FailedAssets -gt 0) { "Red" } else { "Gray" })
    Write-Host "  Time: $([math]::Round($elapsed.TotalSeconds, 2))s" -ForegroundColor White
    Write-Host "  Output: $($script:OutputDir)" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Gray
}

# Run main processing
Process-Assets
