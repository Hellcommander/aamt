#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate Starbound assets using Ollama AI for creative descriptions and parameters.
    AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Uses Ollama to generate creative asset descriptions and parameters, then feeds them
    into the existing Starbound asset generators. Supports all asset types with AI assistance.
    Part of the AI-Assisted Modding Tools (AAMT) suite.
    
.PARAMETER AssetType
    Type of asset: Particle, Texture, Animation, Icon, Spell, Projectile
    
.PARAMETER AssetName
    Name of the asset
    
.PARAMETER Prompt
    Optional prompt for Ollama. If not provided, generates a creative description.
    
.PARAMETER OllamaModel
    Ollama model to use (default: codellama:7b). Used as fallback if specific models not specified.
    
.PARAMETER PlanningModel
    Model for planning/description generation tasks (default: qwen2.5-coder:14b for structured planning, llama3.1:8b for creative)
    
.PARAMETER VisualModel
    Model for visual/creative asset generation tasks (default: llama3.1:8b - excellent for creative concepting and descriptions)
    
.PARAMETER AnalysisModel
    Model for analysis tasks like parameter extraction (default: uses VisualModel or OllamaModel)
    
.PARAMETER OllamaUrl
    Ollama API URL (default: http://localhost:11434)
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER GenerateMultiple
    Generate multiple variations
    
.EXAMPLE
    .\StarboundOllamaAssetGenerator.ps1 -AssetType Particle -AssetName "magicportal" -Prompt "purple swirling magical energy"
    
.EXAMPLE
    .\StarboundOllamaAssetGenerator.ps1 -AssetType Texture -AssetName "runicstone" -GenerateMultiple
    
.EXAMPLE
    .\StarboundOllamaAssetGenerator.ps1 -AssetType Sprite -AssetName "magicorb" -QualityAssessmentDepth "full"
    Uses both Qwen3-VL-8B (mechanical QA) and LLaVA:13b (aesthetic) for complete quality assessment
    
.EXAMPLE
    .\StarboundOllamaAssetGenerator.ps1 -AssetType Sprite -AssetName "magicorb" -GenerateDesignDraft
    Generates a design draft/concept art first, then uses it as reference for the final sprite (improves quality)
    
.EXAMPLE
    .\StarboundOllamaAssetGenerator.ps1 -AssetType Sprite -AssetName "magicorb" -GenerateDesignDraft:$false
    Skips design draft generation (faster, but lower quality without visual reference)
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Particle", "Texture", "Animation", "Icon", "Spell", "Projectile", "Sprite", "ItemSprite", "MechSprite", "AnimationSprite", "Sound", "MechSet", "MechSetVariant", "Tile", "Portal", "PortalSprite", "Ship", "Cursor", "Behavior", "DungeonFloorTile", "DungeonDecorTile", "DungeonWallTile", "PlantSprite")]
    [string]$AssetType,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [string]$Prompt = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers qwen2.5-coder:7b)
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers qwen2.5-coder:14b)
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers llama3.1:8b)
    
    [Parameter(Mandatory=$false)]
    [string]$AnalysisModel = "",  # Auto-selected by OllamaIntegration.psm1 (prefers deepseek-r1:7b or qwen2.5-coder:14b)
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseCppBackend,
    
    [Parameter(Mandatory=$false)]
    [int]$GenerateMultiple = 1,
    
    [Parameter(Mandatory=$false)]
    [object]$Parameters = @{},  # Accept both Hashtable and PSCustomObject
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("fast", "mechanical", "full")]
    [string]$QualityAssessmentDepth = "fast",  # Quality assessment depth: "fast" (sanity only), "mechanical" (Qwen3-VL-8B), "full" (both models)
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateDesignDraft,  # Generate design draft/concept art first (improves final asset quality) - enabled by default
    
    [Parameter(Mandatory=$false)]
    [double]$DesignDraftImageStrength = 0.0  # Image strength for design draft (0.0 = text-to-image, higher = use reference)
)

$ErrorActionPreference = "Stop"

# Validate MyInvocation.MyCommand.Path is not null before using it
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
    Write-Host "Error: Cannot determine script path (MyInvocation.MyCommand.Path is null)" -ForegroundColor Red
    exit 1
}

$PSScriptRoot = Split-Path -Parent $scriptPath

# Validate PSScriptRoot is not null or empty
if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    Write-Host "Error: Cannot determine script root directory" -ForegroundColor Red
    Write-Host "  MyInvocation.MyCommand.Path: '$scriptPath'" -ForegroundColor Gray
    exit 1
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
try {
    Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction Stop
    Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction Stop
    
    # Import quality assessment module if available
    $qualityModule = Join-Path $sharedPath "ImageQualityAssessment.psm1"
    if (Test-Path $qualityModule) {
        Import-Module $qualityModule -Force -ErrorAction SilentlyContinue -DisableNameChecking
        $script:QualityAssessmentAvailable = $true
    } else {
        $script:QualityAssessmentAvailable = $false
    }
    
    # Import Stable Diffusion integration if available (for design drafts)
    $sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"
    if (Test-Path $sdModule) {
        try {
            Import-Module $sdModule -Force -ErrorAction Stop -DisableNameChecking
            $script:SD3Available = $true
            
            # Verify key functions are available
            $requiredFunctions = @("Test-StableDiffusionConnection", "Generate-AssetImageWithSD3", "Start-StableDiffusionServerIfNeeded")
            $missingFunctions = @()
            foreach ($func in $requiredFunctions) {
                if (-not (Get-Command $func -ErrorAction SilentlyContinue)) {
                    $missingFunctions += $func
                }
            }
            
            if ($missingFunctions.Count -gt 0) {
                Write-Host "  [WARN] SD3 module loaded but missing functions: $($missingFunctions -join ', ')" -ForegroundColor Yellow
                $script:SD3Available = $false
            }
        } catch {
            Write-Host "  [WARN] Failed to import SD3 module: $_" -ForegroundColor Yellow
            $script:SD3Available = $false
        }
    } else {
        Write-Host "  [INFO] SD3 module not found at: $sdModule" -ForegroundColor Gray
        $script:SD3Available = $false
    }
} catch {
    Write-Host "ERROR: Failed to import required modules: $_" -ForegroundColor Red
    Write-Host "  Expected module path: $sharedPath" -ForegroundColor Gray
    Write-Host "  Please ensure ToolDetection.psm1 and ToolsetIntegration.psm1 exist" -ForegroundColor Yellow
    exit 1
}

# Initialize tools for Starbound asset generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Starbound asset generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Starbound" `
        -RequiredTools @("ImageMagick") `
        -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    Write-Host "[OK] Ollama integration enabled" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Ollama not available - AI features will be limited" -ForegroundColor Yellow
}

# Load shared asset generation settings (moved here after validation)
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Validate OutputDir is not empty (critical check before any processing)
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    Write-Host "Error: OutputDir cannot be empty" -ForegroundColor Red
    Write-Host "  AssetType: $AssetType" -ForegroundColor Gray
    Write-Host "  AssetName: $AssetName" -ForegroundColor Gray
    Write-Host "  Please provide a valid OutputDir parameter" -ForegroundColor Yellow
    exit 1
}

# Ensure OutputDir exists (create if it doesn't - this is normal for new asset generation)
if (-not (Test-Path $OutputDir)) {
    Write-Host "Creating output directory: $OutputDir" -ForegroundColor Gray
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Validate AssetName is not empty (critical check before any processing)
if ([string]::IsNullOrWhiteSpace($AssetName)) {
    Write-Host "Error: AssetName cannot be empty" -ForegroundColor Red
    Write-Host "  AssetType: $AssetType" -ForegroundColor Gray
    Write-Host "  Please provide a valid AssetName parameter" -ForegroundColor Yellow
    exit 1
}

# Load shared asset generation settings (but don't override parameters if they're explicitly provided)
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
    # Only use settings if parameters are empty (allow explicit overrides)
    # Also filter out invalid models like llama3.2
    if ([string]::IsNullOrWhiteSpace($PlanningModel) -and $script:PlanningModel) {
        if ($script:PlanningModel -ne "llama3.2" -and $script:PlanningModel -notlike "llama3.2*") {
            $PlanningModel = $script:PlanningModel
        }
    }
    if ([string]::IsNullOrWhiteSpace($VisualModel) -and $script:VisualModel) {
        if ($script:VisualModel -ne "llama3.2" -and $script:VisualModel -notlike "llama3.2*") {
            $VisualModel = $script:VisualModel
        }
    }
    if ([string]::IsNullOrWhiteSpace($OllamaModel) -and $script:OllamaModel) {
        if ($script:OllamaModel -ne "llama3.2" -and $script:OllamaModel -notlike "llama3.2*") {
            $OllamaModel = $script:OllamaModel
        }
    }
}

# Clear any invalid model references (like llama3.2 which doesn't exist)
# Do this silently to avoid warning spam - the auto-selection will handle it
if ($PlanningModel -eq "llama3.2" -or $PlanningModel -like "llama3.2*") {
    $PlanningModel = ""
}
if ($VisualModel -eq "llama3.2" -or $VisualModel -like "llama3.2*") {
    $VisualModel = ""
}
if ($OllamaModel -eq "llama3.2" -or $OllamaModel -like "llama3.2*") {
    $OllamaModel = ""
}

# Import shared Ollama integration module with auto model selection
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedModulePath = Join-Path $toolsRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force -DisableNameChecking
    Write-Host "Using shared Ollama integration module with auto model selection" -ForegroundColor Green
    
    # Initialize model selection if not already done
    if (-not (Test-OllamaConnection)) {
        Write-Host "Initializing Ollama connection and model selection..." -ForegroundColor Cyan
        Initialize-OllamaModels
    }
} else {
    Write-Host "Warning: Shared Ollama module not found, using basic implementation" -ForegroundColor Yellow
    Write-Host "  Expected at: $sharedModulePath" -ForegroundColor Gray
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Starbound Ollama Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
if ($script:QualityAssessmentAvailable) {
    Write-Host "Quality Assessment: Enabled" -ForegroundColor Green
    Write-Host "  Assessment Depth: $QualityAssessmentDepth" -ForegroundColor Gray
    if ($QualityAssessmentDepth -eq "fast") {
        Write-Host "    Mode: Fast (sanity checks only, no AI models)" -ForegroundColor Gray
    } elseif ($QualityAssessmentDepth -eq "mechanical") {
        Write-Host "    Mode: Mechanical QA (Qwen3-VL-8B for technical defects)" -ForegroundColor Gray
    } else {
        Write-Host "    Mode: Full (Qwen3-VL-8B + LLaVA:13b for complete assessment)" -ForegroundColor Gray
    }
} else {
    Write-Host "Quality Assessment: Disabled (module not available)" -ForegroundColor Yellow
}

$shouldGenerateDraft = if ($PSBoundParameters.ContainsKey("GenerateDesignDraft")) { $GenerateDesignDraft } else { $true }
if ($shouldGenerateDraft) {
    if ($script:SD3Available) {
        Write-Host "Design Draft Generation: Enabled" -ForegroundColor Green
        Write-Host "  Creates concept art first, then uses it as reference for final asset" -ForegroundColor Gray
        Write-Host "  Improves quality by establishing visual style before generation" -ForegroundColor Gray
        
        # Check if SD3 server is accessible
        if (Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue) {
            try {
                $serverStatus = Test-StableDiffusionConnection -ErrorAction Stop
                if ($serverStatus) {
                    Write-Host "  SD3 Server: Connected" -ForegroundColor Green
                } else {
                    Write-Host "  SD3 Server: Not connected (will attempt auto-start)" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "  SD3 Server: Connection check failed - $_" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  SD3 Server: Cannot check status (function not available)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Design Draft Generation: Disabled (SD3 not available)" -ForegroundColor Yellow
        Write-Host "  Reason: StableDiffusionIntegration.psm1 not loaded or missing functions" -ForegroundColor Gray
    }
} else {
    Write-Host "Design Draft Generation: Disabled (explicitly disabled)" -ForegroundColor Gray
}
Write-Host ""

# Function to generate asset description using Ollama
function Get-AssetDescription {
    param(
        [string]$AssetType,
        [string]$AssetName,
        [string]$UserPrompt,
        [string]$VisualModel = "",
        [string]$PlanningModel = "",
        [string]$OllamaModel = ""
    )
    
    $systemPrompt = switch ($AssetType) {
        "Particle" {
            "You are a game asset designer for Starbound. Generate a creative description for a particle effect named '$AssetName'. 
            Include: visual style (colors, movement pattern), particle behavior (size, speed, lifetime), and thematic elements.
            Return only a concise 2-3 sentence description suitable for generating game assets."
        }
        "Texture" {
            "You are a game asset designer for Starbound. Generate a creative description for a texture named '$AssetName'.
            Include: material type (stone, metal, organic, etc.), color palette, surface details (rough, smooth, patterned), and thematic style.
            Return only a concise 2-3 sentence description suitable for generating game textures."
        }
        "Animation" {
            "You are a game asset designer for Starbound. Generate a creative description for an animation named '$AssetName'.
            Include: animation type (spell cast, idle, attack, etc.), frame count suggestion, movement style, and visual effects.
            Return only a concise 2-3 sentence description suitable for generating game animations."
        }
        "Icon" {
            "You are a game asset designer for Starbound. Generate a creative description for an icon named '$AssetName'.
            Include: icon style (simple, detailed), shape suggestions, color scheme, and what it represents.
            Return only a concise 2-3 sentence description suitable for generating game icons."
        }
        "Spell" {
            "You are a game asset designer for Starbound. Generate a creative description for a spell named '$AssetName'.
            Include: spell type (projectile, area, buff, etc.), visual effects, damage type, and thematic elements.
            Return only a concise 2-3 sentence description suitable for generating game spells."
        }
        "Projectile" {
            "You are a game asset designer for Starbound. Generate a creative description for a projectile named '$AssetName'.
            Include: projectile appearance, trail effects, speed characteristics, and damage type.
            Return only a concise 2-3 sentence description suitable for generating game projectiles."
        }
        "Sprite" {
            "You are a game asset designer for Starbound. Generate a creative description for a sprite named '$AssetName'.
            Include: visual appearance, color scheme, style (pixel art, hand-drawn, etc.), size, and what it represents.
            Return only a concise 2-3 sentence description suitable for generating game sprites."
        }
        "ItemSprite" {
            "You are a game asset designer for Starbound. Generate a creative description for an item sprite named '$AssetName'.
            Include: item type (weapon, tool, consumable, etc.), visual style, color palette, and distinguishing features.
            IMPORTANT: Describe this as a detailed 64x64 pixel sprite with fine details, patterns, and clear visual elements. The sprite will be generated at 64x64 resolution for maximum detail, then automatically scaled down to 16x16 (Starbound's required item icon size). Focus on describing rich detail, clear shapes, and high contrast that will look good when scaled down.
            Return only a concise 2-3 sentence description suitable for generating high-detail item sprites."
        }
        "MechSprite" {
            "You are a game asset designer for Starbound. Generate a creative description for a mech sprite named '$AssetName'.
            Include: mech appearance, color scheme, style, and visual characteristics (robotic, organic, etc.).
            IMPORTANT: Describe this as a detailed 64x64 pixel sprite. The sprite will be generated at 64x64 resolution for maximum detail, then automatically scaled down to 48x48 (Starbound's maximum mech part icon size). Focus on clear details and distinctive features that will remain visible when scaled.
            Note: Mechs may use 3D meshes, but sprites are needed for UI icons and previews.
            Return only a concise 2-3 sentence description suitable for generating high-detail mech sprites."
        }
        "Sprite" {
            "You are a game asset designer for Starbound. Generate a creative description for a sprite named '$AssetName'.
            Include: object type (furniture, decoration, tool, etc.), visual style, color palette, and distinguishing features.
            IMPORTANT: Describe this as a detailed 64x64 pixel sprite. The sprite will be generated at 64x64 resolution for maximum detail, then automatically scaled down to 48x48 (Starbound's maximum object/furniture icon size). Focus on clear details and distinctive features that will remain visible when scaled.
            Return only a concise 2-3 sentence description suitable for generating high-detail sprites."
        }
        "Projectile" {
            "You are a game asset designer for Starbound. Generate a creative description for a projectile sprite named '$AssetName'.
            Include: projectile type (arrow, bolt, energy, magic, etc.), visual style, color palette, trail effects, and motion characteristics.
            IMPORTANT: Describe this as a detailed 64x64 pixel sprite. The sprite will be generated at 64x64 resolution for maximum detail, then automatically scaled down to 48x48 (Starbound's projectile sprite limit). Focus on clear details and motion blur effects that will look good when scaled.
            Return only a concise 2-3 sentence description suitable for generating high-detail projectile sprites."
        }
        "Particle" {
            "You are a game asset designer for Starbound. Generate a creative description for a particle effect named '$AssetName'.
            Include: particle type (spark, smoke, magic, etc.), visual style, color palette, size, and behavior characteristics.
            IMPORTANT: Describe this as a 32x32 pixel particle sprite. Particles are typically small effects, so focus on clear, simple shapes with good contrast. The sprite will be generated at 32x32 resolution.
            Return only a concise 2-3 sentence description suitable for generating particle sprites."
        }
        "AnimationSprite" {
            "You are a game asset designer for Starbound. Generate a creative description for an animation spritesheet named '$AssetName'.
            Include: animation type (spell cast, device activation, status effect, etc.), frame sequence description, color palette, 
            movement pattern, and visual style. This will be a horizontal spritesheet with multiple frames.
            Return only a concise 2-3 sentence description suitable for generating animation spritesheets."
        }
        "Sound" {
            "You are a game sound designer for Starbound. Generate a creative description for a sound effect named '$AssetName'.
            Include: sound characteristics (pitch, timbre, duration), audio style (sharp, smooth, mechanical, organic), 
            sound type (impact, charge, ambient, magic, etc.), and thematic elements.
            Return only a concise 2-3 sentence description suitable for procedural sound generation."
        }
    }
    
    $fullPrompt = if ($UserPrompt) {
        "$systemPrompt`n`nUser request: $UserPrompt"
    } else {
        "$systemPrompt`n`nGenerate a creative and unique description."
    }
    
    # Determine which model to use based on asset type
    # Visual/graphical assets use visual task type - excellent for creative concepting
    # Analysis/planning tasks use analysis/code task type - deterministic JSON/atlas layouts
    $isVisualAsset = $AssetType -in @("Particle", "Texture", "Animation", "Icon", "Sprite", "ItemSprite", "MechSprite", "AnimationSprite", "MechSet", "MechSetVariant")
    
    if ($isVisualAsset) {
        $taskType = "visual"
        # Use shared module auto-selection if VisualModel is empty, otherwise use specified model
        $modelToUse = if ($VisualModel -and $VisualModel.Trim() -ne "") { $VisualModel } else { "" }
        Write-Host "  Using creative model (auto-selected) for graphical asset description" -ForegroundColor Gray
    } else {
        $taskType = "analysis"
        # Use shared module auto-selection if PlanningModel is empty, otherwise use specified model
        $modelToUse = if ($PlanningModel -and $PlanningModel.Trim() -ne "") { $PlanningModel } else { "" }
        Write-Host "  Using structured planning model (auto-selected) for non-visual asset description" -ForegroundColor Gray
    }
    
    # Use shared module if available (with auto model selection), otherwise fallback
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        # Use appropriate task type based on asset type
        # Empty ModelName lets the shared module auto-select the best available model
        try {
            $result = Invoke-OllamaRequest -Prompt $fullPrompt -TaskType $taskType -ResponseLength "standard" -ModelName $modelToUse
            if ($result) { return $result }
        } catch {
            Write-Host "$taskType model '$modelToUse' not available, using auto-selection" -ForegroundColor Yellow
            # Retry with empty model name to trigger auto-selection
            $result = Invoke-OllamaRequest -Prompt $fullPrompt -TaskType $taskType -ResponseLength "standard" -ModelName ""
            if ($result) { return $result }
        }
    }
    
    # Fallback to basic implementation (or retry with OllamaModel)
    $body = @{
        model = $modelToUse
        prompt = $fullPrompt
        stream = $false
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -ErrorAction Stop
        return $response.response.Trim()
    } catch {
        # If PlanningModel failed, try with OllamaModel as fallback
        if ($modelToUse -ne $OllamaModel) {
            Write-Host "PlanningModel '$modelToUse' failed, trying OllamaModel '$OllamaModel'..." -ForegroundColor Yellow
            $body = @{
                model = $OllamaModel
                prompt = $fullPrompt
                stream = $false
            } | ConvertTo-Json
            try {
                $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
                    -Method Post `
                    -ContentType "application/json" `
                    -Body $body `
                    -ErrorAction Stop
                return $response.response.Trim()
            } catch {
                Write-Host "Error calling Ollama with fallback model: $_" -ForegroundColor Red
                return $null
            }
        } else {
            Write-Host "Error calling Ollama: $_" -ForegroundColor Red
            return $null
        }
    }
}

# Function to extract visual parameters from description (enhanced for meaningful usage)
function Get-AssetParameters {
    param(
        [string]$AssetType,
        [string]$Description,
        [string]$VisualModel = "",
        [string]$PlanningModel = "",
        [string]$AnalysisModel = "",
        [string]$OllamaModel = ""
    )
    
    $paramPrompt = switch ($AssetType) {
        "Particle" {
            "Based on this particle effect description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'ParticleCount': number (4-100),
              'FrameCount': number (4-16),
              'ParticleSize': number (4-16),
              'Color': [R, G, B, A] array,
              'TimeToLive': number (0.1-2.0),
              'InitialVelocity': [X, Y] array,
              'EffectType': string (Portal, Explosion, Trail, etc.)
            }
            Return ONLY the JSON, no other text."
        }
        "Texture" {
            "Based on this texture description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'Size': number (128, 256, 512, or 1024),
              'NoiseScale': number (1.0-10.0),
              'Seed': number (0-1000),
              'ColorPalette': [color1, color2, color3] array of RGB arrays
            }
            Return ONLY the JSON, no other text."
        }
        "Animation" {
            "Based on this animation description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'FrameCount': number (4-32),
              'FrameDuration': number (0.05-0.2),
              'Mode': string (Loop, Once, PingPong),
              'Size': [width, height] array
            }
            Return ONLY the JSON, no other text."
        }
        "Icon" {
            "Based on this icon description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'Size': number (32, 64, 128),
              'Style': string (Default, Rounded, Sharp),
              'Shape': string (Circle, Square, Hexagon, Custom)
            }
            Return ONLY the JSON, no other text."
        }
        "Sprite" {
            "Based on this sprite description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'Width': number (16, 32, 64, 128),
              'Height': number (16, 32, 64, 128),
              'FrameCount': number (1-16),
              'ColorPalette': [color1, color2, color3] array of RGB arrays,
              'Style': string (PixelArt, HandDrawn, Procedural)
            }
            Return ONLY the JSON, no other text."
        }
        "ItemSprite" {
            "Based on this item sprite description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'Width': number (16, 32, 64),
              'Height': number (16, 32, 64),
              'FrameCount': number (1-8),
              'ColorPalette': [color1, color2, color3] array of RGB arrays,
              'ItemType': string (Weapon, Tool, Consumable, Material, etc.)
            }
            Return ONLY the JSON, no other text."
        }
        "MechSprite" {
            "Based on this mech sprite description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'Width': number (32, 64, 128),
              'Height': number (32, 64, 128),
              'FrameCount': number (1-4),
              'ColorPalette': [color1, color2, color3] array of RGB arrays,
              'MechType': string (Bipedal, Quadruped, Hover, Tank, etc.)
            }
            Return ONLY the JSON, no other text."
        }
        "AnimationSprite" {
            "Based on this animation spritesheet description: '$Description'
            Extract and return ONLY a JSON object with these exact keys:
            {
              'FrameWidth': number (16, 32, 48, 64),
              'FrameHeight': number (16, 32, 48, 64),
              'FrameCount': number (4-16),
              'AnimationCycle': number (0.1-2.0),
              'ColorPalette': [color1, color2, color3] array of RGB arrays,
              'AnimationType': string (SpellCast, DeviceActivation, StatusEffect, etc.)
            }
            Return ONLY the JSON, no other text."
        }
        default {
            "Based on this asset description: '$Description'
            Extract relevant parameters as a JSON object.
            Return ONLY the JSON, no other text."
        }
    }
    
    # Use visual task type for parameter extraction from visual assets
    # Visual assets need creative parameter generation
    $isVisualAsset = $AssetType -in @("Particle", "Texture", "Animation", "Icon", "Sprite", "ItemSprite", "MechSprite", "AnimationSprite", "MechSet", "MechSetVariant")
    
    if ($isVisualAsset) {
        $taskType = "visual"
        # Use shared module auto-selection if VisualModel is empty, otherwise use specified model
        $modelToUse = if ($VisualModel -and $VisualModel.Trim() -ne "") { $VisualModel } else { "" }
        Write-Host "  Using creative model (auto-selected) for parameter extraction" -ForegroundColor Gray
    } else {
        $taskType = "analysis"
        # Use shared module auto-selection if models are empty, otherwise use specified model
        $modelToUse = if ($AnalysisModel -and $AnalysisModel.Trim() -ne "") { $AnalysisModel } elseif ($PlanningModel -and $PlanningModel.Trim() -ne "") { $PlanningModel } elseif ($OllamaModel -and $OllamaModel.Trim() -ne "") { $OllamaModel } else { "" }
        Write-Host "  Using structured/hybrid model (auto-selected) for parameter extraction" -ForegroundColor Gray
    }
    
    # Use shared module if available (with auto model selection), otherwise fallback
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        # Use appropriate task type based on asset type
        # Empty ModelName lets the shared module auto-select the best available model
        $response = Invoke-OllamaRequest -Prompt $paramPrompt -TaskType $taskType -ResponseLength "short" -ModelName $modelToUse
    } else {
        # Fallback to basic implementation
        $body = @{
            model = $modelToUse
            prompt = $paramPrompt
            stream = $false
        } | ConvertTo-Json
        
        try {
            $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
                -Method Post `
                -ContentType "application/json" `
                -Body $body `
                -ErrorAction Stop
            $response = $response.response.Trim()
        } catch {
            Write-Host "Error calling Ollama: $_" -ForegroundColor Red
            $response = $null
        }
    }
    
    if ($response) {
        # Try to extract JSON from response
        $jsonMatch = $response | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
        if ($jsonMatch) {
            try {
                $params = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                return $params
            } catch {
                Write-Host "Warning: Could not parse parameters from Ollama response" -ForegroundColor Yellow
            }
        }
    }
    
    # Return default parameters if parsing fails
    return Get-DefaultParameters -AssetType $AssetType
}

# Function to get default parameters
function Get-DefaultParameters {
    param([string]$AssetType)
    
    switch ($AssetType) {
        "Particle" {
            return @{
                ParticleCount = 50
                FrameCount = 8
                ParticleSize = 8
                Color = @(255, 200, 100, 255)
                TimeToLive = 1.0
                InitialVelocity = @(0, 5)
                EffectType = "Portal"
            }
        }
        "Texture" {
            return @{
                Size = 256
                NoiseScale = 4.0
                Seed = 0
            }
        }
        "Animation" {
            return @{
                FrameCount = 8
                FrameDuration = 0.1
                Mode = "Loop"
                Size = @(64, 64)
            }
        }
        "Icon" {
            return @{
                Size = 64
                Style = "Default"
                Shape = "Circle"
            }
        }
        "Sprite" {
            return @{
                Width = 64
                Height = 64
                FrameCount = 1
                ColorPalette = @(@(255, 200, 100), @(200, 150, 80), @(150, 100, 60))
                Style = "PixelArt"
            }
        }
        "ItemSprite" {
            return @{
                Width = 32
                Height = 32
                FrameCount = 1
                ColorPalette = @(@(255, 200, 100), @(200, 150, 80), @(150, 100, 60))
                ItemType = "Weapon"
            }
        }
        "MechSprite" {
            return @{
                Width = 64
                Height = 64
                FrameCount = 1
                ColorPalette = @(@(100, 150, 255), @(80, 120, 200), @(60, 90, 150))
                MechType = "Bipedal"
            }
        }
        "AnimationSprite" {
            return @{
                FrameWidth = 32
                FrameHeight = 32
                FrameCount = 8
                AnimationCycle = 0.5
                ColorPalette = @(@(255, 200, 100), @(200, 150, 80), @(150, 100, 60))
                AnimationType = "SpellCast"
            }
        }
        "Sound" {
            return @{
                SoundType = "Impact"
                Duration = 0.5
                Frequency = 440
                Volume = 0.7
                Format = "ogg"
            }
        }
        default {
            return @{}
        }
    }
}

# Check if Ollama is available (use shared module if available)
Write-Host "Checking Ollama connection..." -ForegroundColor Cyan
if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
    # Use shared module's connection test
    if (-not (Test-OllamaConnection)) {
        Write-Host "[ERROR] Ollama connection failed" -ForegroundColor Red
        exit 1
    }
        Write-Host "[OK] Ollama connected" -ForegroundColor Green
    
    # Check if specific models are available (only if explicitly provided, not empty)
    $models = (Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get).models
    
    # Only check PlanningModel if it's explicitly provided (not empty/whitespace)
    if ($PlanningModel -and $PlanningModel.Trim() -ne "") {
        $planningExists = $models | Where-Object { $_.name -like "$PlanningModel*" }
        if ($planningExists) {
            Write-Host "Planning model: $PlanningModel" -ForegroundColor Green
        } else {
            Write-Host "Planning model '$PlanningModel' not found, using auto-selection" -ForegroundColor Yellow
            # Clear the invalid model so auto-selection can work
            $PlanningModel = ""
        }
    } else {
        Write-Host "Planning model: auto-selected by OllamaIntegration.psm1" -ForegroundColor Gray
    }
    
    # Only check VisualModel if it's explicitly provided (not empty/whitespace)
    if ($VisualModel -and $VisualModel.Trim() -ne "") {
        $visualExists = $models | Where-Object { $_.name -like "$VisualModel*" }
        if ($visualExists) {
            Write-Host "Visual model: $VisualModel" -ForegroundColor Green
        } else {
            Write-Host "Visual model '$VisualModel' not found, using auto-selection" -ForegroundColor Yellow
            # Clear the invalid model so auto-selection can work
            $VisualModel = ""
        }
    } else {
        Write-Host "Visual model: auto-selected by OllamaIntegration.psm1" -ForegroundColor Gray
    }
    
    if ($OllamaModel -and -not $PlanningModel -and -not $VisualModel) {
        $modelExists = $models | Where-Object { $_.name -like "$OllamaModel*" }
        if (-not $modelExists) {
            Write-Host "Model '$OllamaModel' not found. Available models:" -ForegroundColor Yellow
            $models | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor Gray }
            Write-Host "Using auto-selected model instead" -ForegroundColor Yellow
        } else {
            Write-Host "Using model: $OllamaModel" -ForegroundColor Green
        }
    }
} else {
    # Fallback to basic connection test
    try {
        $testResponse = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -ErrorAction Stop
        Write-Host "[OK] Ollama connected" -ForegroundColor Green
        
        # Check if model is available
        $models = (Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get).models
        $modelExists = $models | Where-Object { $_.name -like "$OllamaModel*" }
        if (-not $modelExists) {
            Write-Host "Model '$OllamaModel' not found. Available models:" -ForegroundColor Yellow
            $models | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor Gray }
            Write-Host "Installing model: ollama pull $OllamaModel" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host "Using model: $OllamaModel" -ForegroundColor Green
    } catch {
        Write-Host "✗ Cannot connect to Ollama at $OllamaUrl" -ForegroundColor Red
        Write-Host "  Make sure Ollama is running: ollama serve" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ""

# Validate AssetName is not empty
if ([string]::IsNullOrWhiteSpace($AssetName)) {
    Write-Host "Error: AssetName cannot be empty" -ForegroundColor Red
    exit 1
}

# Helper function for Ollama requests (if shared module not available)
function Invoke-OllamaRequest {
    param(
        [string]$Prompt,
        [string]$TaskType = "planning",
        [string]$ModelName = "",
        [string]$OllamaUrl = "http://localhost:11434",
        [string]$ResponseLength = "standard"
    )
    
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue -Module OllamaIntegration) {
        # Use shared module version
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType $TaskType -ModelName $ModelName -OllamaUrl $OllamaUrl -ResponseLength $ResponseLength
    }
    
    # Fallback implementation
    $modelToUse = if ($ModelName) { $ModelName } else { $OllamaModel }
    if (-not $modelToUse) { $modelToUse = "qwen2.5-coder:7b" }
    
    $body = @{
        model = $modelToUse
        prompt = $Prompt
        stream = $false
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -ErrorAction Stop
        return $response.response.Trim()
    } catch {
        Write-Host "Error calling Ollama: $_" -ForegroundColor Yellow
        return $null
    }
}

# Function to generate complete mechset variant with all assets
function Generate-MechSetVariant {
    param(
        [string]$VariantName,
        [string]$BaseMechSetName = "",
        [hashtable]$Parameters = @{},
        [string]$OllamaUrl,
        [string]$VisualModel,
        [string]$PlanningModel,
        [string]$OllamaModel
    )
    
    $modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
    $variantConfigPath = "$modPath\Data\Config\Mechs\MechVariantSystem.json"
    
    # Load variant system config
    if (Test-Path $variantConfigPath) {
        $variantConfig = Get-Content $variantConfigPath | ConvertFrom-Json
    } else {
        Write-Host "Warning: MechVariantSystem.json not found, using defaults" -ForegroundColor Yellow
        $variantConfig = @{
            variantTemplates = @{
                baseTemplate = @{
                    name = "Base MagiTech"
                    colorScheme = @{ primary = @(150, 150, 180); secondary = @(100, 100, 140); accent = @(200, 200, 255); glow = @(150, 200, 255) }
                    artStyle = @{ shading = "flat"; outline = $true; pixelArt = $true; paletteLimit = 16 }
                    designLanguage = @{ techLevel = "advanced"; aesthetic = "magitech"; material = "enchanted_metal" }
                }
            }
        }
    }
    
    # Find or create variant template
    $variantTemplate = $null
    if ($variantConfig.variantTemplates.variantExamples) {
        $variantTemplate = $variantConfig.variantTemplates.variantExamples | Where-Object { $_.id -eq $VariantName } | Select-Object -First 1
    }
    
    if (-not $variantTemplate) {
        Write-Host "Creating new variant template: $VariantName" -ForegroundColor Yellow
        
        # Use Ollama to generate variant theme and design
        $variantPrompt = "Create a unique mech variant theme called '$VariantName'. Describe the color scheme (primary, secondary, accent, glow as RGB values), art style (shading, outline, pixel art), and design language (tech level, aesthetic, material, details). Return as JSON with colorScheme, artStyle, and designLanguage objects."
        
        try {
            $modelToUse = if ($PlanningModel) { $PlanningModel } elseif ($OllamaModel) { $OllamaModel } else { "qwen2.5-coder:7b" }
            $variantDescription = Invoke-OllamaRequest -Prompt $variantPrompt -TaskType "planning" -ModelName $modelToUse -OllamaUrl $OllamaUrl
            if ($variantDescription) {
                # Try to parse JSON from response
                $jsonMatch = $variantDescription | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
                if ($jsonMatch) {
                    $variantTemplate = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                    $variantTemplate.id = $VariantName
                    $variantTemplate.name = $VariantName -replace '([A-Z])', ' $1' -replace '^.', { $_.ToString().ToUpper() }
                }
            }
        } catch {
            Write-Host "Failed to generate variant template with Ollama, using defaults" -ForegroundColor Yellow
        }
        
        if (-not $variantTemplate) {
            $variantTemplate = $variantConfig.variantTemplates.baseTemplate
            $variantTemplate.id = $VariantName
            $variantTemplate.name = $VariantName -replace '([A-Z])', ' $1' -replace '^.', { $_.ToString().ToUpper() }
        }
    }
    
    # Find base mechset to create variant of
    $baseMechSetPath = "$modPath\Data\Config\Mechs"
    $mechSetFiles = Get-ChildItem -Path $baseMechSetPath -Filter "*MechSet.json" -ErrorAction SilentlyContinue
    
    if ([string]::IsNullOrWhiteSpace($BaseMechSetName) -and $mechSetFiles.Count -gt 0) {
        # Use first available mechset if none specified
        $BaseMechSetName = $mechSetFiles[0].BaseName
    }
    
    if ([string]::IsNullOrWhiteSpace($BaseMechSetName)) {
        Write-Host "Error: No base mechset found or specified" -ForegroundColor Red
        return $false
    }
    
    $baseMechSetPath = "$baseMechSetPath\$BaseMechSetName.json"
    if (-not (Test-Path $baseMechSetPath)) {
        Write-Host "Error: Base mechset not found: $baseMechSetPath" -ForegroundColor Red
        return $false
    }
    
    $baseMechSet = Get-Content $baseMechSetPath | ConvertFrom-Json
    
    # IMPORTANT: Check that reference forms exist first
    # Reference forms = templates/inspiration (not directly used by players)
    # Mechforms = actual forms used in mechsets (players build mechsets, which contain mechforms)
    # Mechforms are based on reference forms but altered to match the mechset's structural consistency
    Write-Host "`nChecking for reference forms (templates)..." -ForegroundColor Cyan
    $referenceFormsPath = "$modPath\Data\Config\Mechs"
    $missingReferenceForms = @()
    
    foreach ($form in $baseMechSet.forms) {
        # Extract form ID from configFile path (e.g., "/Data/Config/Mechs/AetherWardenForm.json" -> "AetherWarden")
        $formConfigFile = $form.configFile
        if ($formConfigFile -match "/([^/]+)Form\.json$") {
            $formId = $matches[1]
            $referenceFormPath = "$referenceFormsPath\${formId}Form.json"
            
            if (-not (Test-Path $referenceFormPath)) {
                $missingReferenceForms += $formId
                Write-Host "  [MISSING] Reference form not found: ${formId}Form.json" -ForegroundColor Yellow
            } else {
                Write-Host "  [OK] Reference form found: ${formId}Form.json" -ForegroundColor Green
            }
        }
    }
    
    if ($missingReferenceForms.Count -gt 0) {
        Write-Host "`nERROR: Reference forms must be generated first before creating mechforms!" -ForegroundColor Red
        Write-Host "Missing reference forms: $($missingReferenceForms -join ', ')" -ForegroundColor Red
        Write-Host "`nWorkflow:" -ForegroundColor Yellow
        Write-Host "  1. Generate reference forms first (templates/inspiration - not directly used by players)" -ForegroundColor Yellow
        Write-Host "  2. Generate mechforms based on reference forms (these are the actual forms used in mechsets)" -ForegroundColor Yellow
        Write-Host "  3. Players build mechsets, which contain mechforms (not reference forms)" -ForegroundColor Yellow
        Write-Host "  4. Mechforms are altered from reference forms to match the mechset's structural consistency" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "`nAll reference forms found. Proceeding to generate mechforms..." -ForegroundColor Green
    Write-Host "  Mechforms are the actual forms used in mechsets (players build mechsets, not reference forms)" -ForegroundColor Gray
    
    Write-Host "=== Generating MechSet Variant: $($variantTemplate.name) ===" -ForegroundColor Cyan
    Write-Host "Base MechSet: $BaseMechSetName" -ForegroundColor Yellow
    Write-Host "Variant ID: $VariantName" -ForegroundColor Yellow
    Write-Host "Forms in mechset: $($baseMechSet.forms.Count)" -ForegroundColor Yellow
    
    # Create variant mechset JSON with per-form atlas support
    $variantMechSet = @{
        systemName = "$($baseMechSet.systemName) - $($variantTemplate.name) Variant"
        version = $baseMechSet.version
        description = "$($baseMechSet.description) - $($variantTemplate.description)"
        maxForms = $baseMechSet.maxForms
        mechType = $baseMechSet.mechType
        playerVisibility = $baseMechSet.playerVisibility
        baseChassis = $baseMechSet.baseChassis
        forms = @()
        progression = $baseMechSet.progression
        transformation = $baseMechSet.transformation
        animationConfig = @{
            frameSize = $baseMechSet.animationConfig.frameSize
            atlasSize = @(4096, 4096)  # 4096x4096 per atlas - standard spritesheet size
            maxAtlases = $baseMechSet.forms.Count  # One atlas per form for high quality
            cellsPerAtlas = $baseMechSet.animationConfig.cellsPerAtlas
            framesPerForm = $baseMechSet.animationConfig.framesPerForm
            perFormAtlas = $true  # Each form gets its own dedicated atlas
            atlasNaming = "form_{formId}_{variantId}"  # Atlas naming pattern
            gpuOptimized = $true  # Optimized for average high-end GPU capabilities
        }
        performance = $baseMechSet.performance
        variant = @{
            variantId = $VariantName
            variantName = $variantTemplate.name
            colorScheme = $variantTemplate.colorScheme
            artStyle = $variantTemplate.artStyle
            designLanguage = $variantTemplate.designLanguage
            structuralCohesion = $true  # All forms share same chassis structure
        }
    }
    
    # Build structural cohesion prompt for all forms - they must look like transformations of the same mech
    $colorScheme = $variantTemplate.colorScheme
    $artStyle = $variantTemplate.artStyle
    $designLanguage = $variantTemplate.designLanguage
    
    # Generate base chassis description that will be shared across all forms
    $chassisDescription = "Base chassis with $($designLanguage.material) construction, $($designLanguage.aesthetic) aesthetic, featuring $($designLanguage.details). The mech has distinctive structural elements: armor plating patterns, joint mechanisms, core components, and signature design features that remain consistent across all transformations."
    
    $cohesionPrompt = @"
VARIANT THEME: $($variantTemplate.name)
STRUCTURAL COHESION: All forms are transformations of the SAME mech chassis - they share:
  - Same base chassis structure and frame
  - Same armor plating patterns and segments (just repositioned/reconfigured)
  - Same joint mechanisms and connection points
  - Same core components (cockpit, power core, etc.) - just relocated
  - Same signature design elements and distinctive features
  - Same material construction and surface details
  
COLOR SCHEME: Primary RGB($($colorScheme.primary[0]),$($colorScheme.primary[1]),$($colorScheme.primary[2])), Accent RGB($($colorScheme.accent[0]),$($colorScheme.accent[1]),$($colorScheme.accent[2]))
ART STYLE: $($artStyle.shading) shading, $($artStyle.pixelArt) pixel art, $($artStyle.paletteLimit) color palette
DESIGN LANGUAGE: $($designLanguage.aesthetic), $($designLanguage.material), $($designLanguage.details)

BASE CHASSIS: $chassisDescription

CRITICAL: Each form must look like the SAME mech that has physically transformed/reconfigured its parts.
  - Armor plates move and reposition, but remain recognizable as the same plates
  - Joints and mechanisms are the same, just in different positions
  - Core components (cockpit, power core) are the same, just relocated
  - Design elements (rune patterns, tech details, etc.) are consistent across forms
  - The mech should look like it could physically transform between these forms
  - NOT just different mechs with the same colors - they must share structural DNA
"@
    
    Write-Host "`nGenerating uniform variant assets for all forms in mechset..." -ForegroundColor Cyan
    Write-Host "Visual Cohesion: All forms will share the same visual style" -ForegroundColor Yellow
    
    # Create variant directories
    $variantDir = "$modPath\sprites\forms\variants\$VariantName"
    $variantIconDir = "$modPath\interface\icons\forms\variants\$VariantName"
    $variantParticleDir = "$modPath\particles\variants\$VariantName"
    
    @($variantDir, $variantIconDir, $variantParticleDir) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }
    
    # Generate mechforms - these are the actual forms used in mechsets
    # Players build mechsets, which contain mechforms (not reference forms)
    # Mechforms are based on reference forms but altered to match the mechset's structural consistency
    foreach ($form in $baseMechSet.forms) {
        Write-Host "`n  [Form $($form.slotIndex)] Generating MECHFORM for $($form.id)..." -ForegroundColor Green
        Write-Host "    Reference form: ${form.id}Form.json (template/inspiration)" -ForegroundColor Gray
        Write-Host "    Mechform: Actual form used in mechset (players build mechsets, which contain mechforms)" -ForegroundColor Gray
        Write-Host "    This mechform will be altered from reference form to match the mechset's structural consistency" -ForegroundColor Gray
        
        # Load reference form to use as base template
        $formConfigFile = $form.configFile
        $referenceFormPath = ""
        if ($formConfigFile -match "/([^/]+)Form\.json$") {
            $formId = $matches[1]
            $referenceFormPath = "$modPath\Data\Config\Mechs\${formId}Form.json"
        }
        
        $referenceFormData = $null
        if (Test-Path $referenceFormPath) {
            $referenceFormData = Get-Content $referenceFormPath | ConvertFrom-Json
            Write-Host "    Reference form loaded: $formId" -ForegroundColor Gray
        }
        
        # 1. Generate Form Icon (48x48) showing this form as a transformation of the base chassis
        $iconPath = "$variantIconDir\$($form.id).png"
        if (-not (Test-Path $iconPath)) {
            Write-Host "    Generating icon..." -ForegroundColor White
            $iconParams = @{
                AssetType = "Icon"
                AssetName = "${BaseMechSetName}_${VariantName}_${form.id}_icon"
                OllamaModel = $OllamaModel
                PlanningModel = $PlanningModel
                VisualModel = $VisualModel
                Prompt = "$cohesionPrompt`n`nMECHFORM: $($form.displayName) - $($form.description). This is a MECHFORM (actual form used in mechset, not a reference form). Players build mechsets, which contain mechforms. This mechform is based on reference form ${form.id}Form.json (template/inspiration) but ALTERED to match this mechset's structural consistency. The icon must show the same structural elements (armor plates, joints, core components) as other mechforms in this mechset, reconfigured for this form's role. It should be immediately recognizable as the same mech, just transformed."
                OutputDir = $variantIconDir
            }
            & "$PSScriptRoot\StarboundOllamaAssetGenerator.ps1" @iconParams | Out-Null
        }
        
        # 2. Generate Animation Spritesheet Atlas (136 frames) - One dedicated atlas per form for high quality
        $animPath = "$variantDir\$($form.id)_atlas.png"
        if (-not (Test-Path $animPath)) {
            Write-Host "    Generating animation atlas (dedicated atlas for this form)..." -ForegroundColor White
            
            # Load cockpit spec for this form
            $formConfigPath = "$modPath\Data\Config\Mechs\$($form.id)Form.json"
            $cockpitInfo = ""
            if (Test-Path $formConfigPath) {
                $formConfig = Get-Content $formConfigPath | ConvertFrom-Json
                if ($formConfig.cockpit) {
                    $cockpitInfo = "`nCockpit: Must include visible cockpit with alpha channel for player visibility."
                }
            }
            
            # Get atlas dimensions - use 4096x4096 as standard spritesheet size
            $atlasSize = if ($baseMechSet.animationConfig.atlasSize) { 
                # Use configured size if it's at least 4096x4096, otherwise use 4096x4096
                if ($baseMechSet.animationConfig.atlasSize[0] -ge 4096 -and $baseMechSet.animationConfig.atlasSize[1] -ge 4096) {
                    $baseMechSet.animationConfig.atlasSize
                } else {
                    @(4096, 4096)
                }
            } else {
                @(4096, 4096)  # Default to 4096x4096 - standard spritesheet size
            }
            $frameSize = $baseMechSet.animationConfig.frameSize
            $framesPerForm = $baseMechSet.animationConfig.framesPerForm
            
            Write-Host "      Atlas size: ${atlasSize[0]}x${atlasSize[1]} (standard spritesheet size)" -ForegroundColor Gray
            
            $animParams = @{
                AssetType = "Animation"
                AssetName = "${BaseMechSetName}_${VariantName}_${form.id}_atlas"
                OllamaModel = $OllamaModel
                PlanningModel = $PlanningModel
                VisualModel = $VisualModel
                Prompt = "$cohesionPrompt`n`nMECHFORM: $($form.displayName) - $($form.description). This is a MECHFORM (actual form used in mechset, not a reference form). Players build mechsets, which contain mechforms. Generate animation atlas (${atlasSize[0]}x${atlasSize[1]} pixels - standard spritesheet size) with $framesPerForm frames ($frameSize[0]x$frameSize[1] per frame) showing this MECHFORM as a transformation of the base chassis. This mechform is based on reference form ${form.id}Form.json (template/inspiration) but ALTERED to match this mechset's structural consistency. This mechform gets its OWN dedicated ${atlasSize[0]}x${atlasSize[1]} atlas for maximum quality. All frames must show the SAME structural elements (armor plates, joints, core components) as other mechforms in this mechset, reconfigured for this form. The mech must look like it physically transformed from the base chassis - same parts, different configuration. Maintain structural consistency across all frames.$cockpitInfo"
                OutputDir = $variantDir
                Parameters = @{
                    AtlasWidth = $atlasSize[0]
                    AtlasHeight = $atlasSize[1]
                    FrameWidth = $frameSize[0]
                    FrameHeight = $frameSize[1]
                    FrameCount = $framesPerForm
                    PerFormAtlas = $true
                    GPUTarget = "high-end"
                }
            }
            & "$PSScriptRoot\StarboundOllamaAssetGenerator.ps1" @animParams | Out-Null
        }
        
        # 2.5. Generate hitbox from animation atlas
        if (Test-Path $animPath) {
            Write-Host "    Generating hitbox from animation atlas..." -ForegroundColor White
            
            # Calculate frames per row from atlas dimensions
            $framesPerRow = [math]::Floor($atlasSize[0] / $frameSize[0])
            $framesPerColumn = [math]::Floor($atlasSize[1] / $frameSize[1])
            
            # Get form config path
            $formConfigPath = ""
            if ($formConfigFile -match "/([^/]+)Form\.json$") {
                $formId = $matches[1]
                $formConfigPath = "$modPath\Data\Config\Mechs\${formId}Form.json"
            }
            
            # Generate hitbox using hybrid C++/Lua approach
            $hitboxScript = "$PSScriptRoot\GenerateMechHitboxes.ps1"
            if (Test-Path $hitboxScript) {
                try {
                    $hitboxParams = @{
                        ModPath = $modPath
                        SpritesheetPath = $animPath
                        FrameWidth = $frameSize[0]
                        FrameHeight = $frameSize[1]
                        FramesPerRow = $framesPerRow
                        FormConfigPath = $formConfigPath
                        UseMaxHitbox = $true
                        AlphaThreshold = 128
                    }
                    & $hitboxScript @hitboxParams | Out-Null
                    Write-Host "      [OK] Hitbox generated and form config updated" -ForegroundColor Green
                } catch {
                    Write-Host "      [WARNING] Hitbox generation failed: $_" -ForegroundColor Yellow
                    Write-Host "      Form will use default collision box" -ForegroundColor Yellow
                }
            } else {
                Write-Host "      [WARNING] Hitbox generator script not found: $hitboxScript" -ForegroundColor Yellow
            }
        }
        
        # 3. Generate VFX Particles (enter/exit) with variant style
        $vfxEnterPath = "$variantParticleDir\$($form.id)Enter.particle"
        $vfxExitPath = "$variantParticleDir\$($form.id)Exit.particle"
        
        if (-not (Test-Path $vfxEnterPath)) {
            Write-Host "    Generating transformation VFX..." -ForegroundColor White
            $vfxParams = @{
                AssetType = "Particle"
                AssetName = "${BaseMechSetName}_${VariantName}_${form.id}_enter"
                OllamaModel = $OllamaModel
                PlanningModel = $PlanningModel
                VisualModel = $VisualModel
                Prompt = "$cohesionPrompt`n`nMECHFORM: $($form.displayName). This is a MECHFORM (actual form used in mechset, not a reference form). Players build mechsets, which contain mechforms. Generate transformation enter particle effect showing the mech's structural components (armor plates, joints, core) physically reconfiguring into this MECHFORM. This mechform is based on reference form ${form.id}Form.json (template/inspiration) but altered for mechset consistency. The particles should show the same chassis elements moving and repositioning, not just color effects. Match the variant's color scheme and aesthetic."
                OutputDir = $variantParticleDir
            }
            & "$PSScriptRoot\StarboundOllamaAssetGenerator.ps1" @vfxParams | Out-Null
        }
        
        if (-not (Test-Path $vfxExitPath)) {
            $vfxParams = @{
                AssetType = "Particle"
                AssetName = "${BaseMechSetName}_${VariantName}_${form.id}_exit"
                OllamaModel = $OllamaModel
                PlanningModel = $PlanningModel
                VisualModel = $VisualModel
                Prompt = "$cohesionPrompt`n`nMECHFORM: $($form.displayName). This is a MECHFORM (actual form used in mechset, not a reference form). Players build mechsets, which contain mechforms. Generate transformation exit particle effect showing the mech's structural components (armor plates, joints, core) physically reconfiguring away from this MECHFORM. This mechform is based on reference form ${form.id}Form.json (template/inspiration) but altered for mechset consistency. The particles should show the same chassis elements moving and repositioning, not just color effects. Match the variant's color scheme and aesthetic."
                OutputDir = $variantParticleDir
            }
            & "$PSScriptRoot\StarboundOllamaAssetGenerator.ps1" @vfxParams | Out-Null
        }
    }
    
    # Update form configs to point to variant assets (one atlas per form)
    foreach ($form in $baseMechSet.forms) {
        $variantForm = @{
            slotIndex = $form.slotIndex
            id = $form.id
            displayName = "$($form.displayName) ($($variantTemplate.name))"
            role = $form.role
            description = "$($form.description) - $($variantTemplate.name) variant with uniform visual style"
            configFile = $form.configFile
            variantAssets = @{
                icon = "/interface/icons/forms/variants/$VariantName/$($form.id).png"
                animationAtlas = "/sprites/forms/variants/$VariantName/$($form.id)_atlas.png"  # Dedicated atlas for this form
                atlasConfig = @{
                    atlasName = "${form.id}_${VariantName}"
                    frameSize = $baseMechSet.animationConfig.frameSize
                    framesPerForm = $baseMechSet.animationConfig.framesPerForm
                    atlasSize = @(4096, 4096)  # 4096x4096 per atlas - standard spritesheet size
                    dedicatedAtlas = $true  # This form has its own atlas
                    gpuOptimized = $true  # Optimized for average high-end GPU
                }
                vfxEnter = "/particles/variants/$VariantName/$($form.id)Enter.particle"
                vfxExit = "/particles/variants/$VariantName/$($form.id)Exit.particle"
            }
        }
        $variantMechSet.forms += $variantForm
    }
    
    # Save variant mechset JSON
    $variantMechSetPath = "$baseMechSetPath\..\$BaseMechSetName`_$VariantName.json"
    $variantMechSet | ConvertTo-Json -Depth 10 | Set-Content -Path $variantMechSetPath
    Write-Host "`n[OK] Created variant mechset config: $variantMechSetPath" -ForegroundColor Green
    Write-Host "    Generated MECHFORMS (actual forms used in mechsets, not reference forms)" -ForegroundColor Green
    Write-Host "    Players build mechsets, which contain these mechforms" -ForegroundColor Green
    Write-Host "    All $($baseMechSet.forms.Count) mechforms are transformations of the same base chassis" -ForegroundColor Green
    Write-Host "    Structural elements (armor, joints, core) are consistent across all mechforms" -ForegroundColor Green
    Write-Host "    Mechforms share the same $($variantTemplate.name) design DNA" -ForegroundColor Green
    Write-Host "    Each mechform has its own dedicated 4096x4096 animation atlas for maximum quality" -ForegroundColor Green
    Write-Host "    Atlas size: 4096x4096 (standard spritesheet size)" -ForegroundColor Green
    Write-Host "    Total atlases: $($baseMechSet.forms.Count) (one per mechform, 4096x4096 each)" -ForegroundColor Green
    
    return $true
}

# Handle MechSet and MechSetVariant asset types specially
if ($AssetType -eq "MechSetVariant") {
    Write-Host "=== Generating MechSet Variant ===" -ForegroundColor Cyan
    Write-Host "Variant Name: $AssetName" -ForegroundColor Yellow
    
    # Extract base mechset name from parameters if provided
    $baseMechSet = ""
    if ($PSBoundParameters.ContainsKey("Parameters") -and $Parameters.BaseMechSet) {
        $baseMechSet = $Parameters.BaseMechSet
    }
    
    $success = Generate-MechSetVariant `
        -VariantName $AssetName `
        -BaseMechSetName $baseMechSet `
        -Parameters $Parameters `
        -OllamaUrl $OllamaUrl `
        -VisualModel $VisualModel `
        -PlanningModel $PlanningModel `
        -OllamaModel $OllamaModel
    
    if ($success) {
        Write-Host "`n[OK] MechSet Variant generation complete: $AssetName" -ForegroundColor Green
    } else {
        Write-Host "`n[ERROR] MechSet Variant generation failed: $AssetName" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# Generate assets
for ($i = 1; $i -le $GenerateMultiple; $i++) {
    $currentAssetName = if ($GenerateMultiple -gt 1) { "${AssetName}_v$i" } else { $AssetName }
    
    # Validate current asset name is not empty
    if ([string]::IsNullOrWhiteSpace($currentAssetName)) {
        Write-Host "Error: Generated asset name is empty (iteration $i)" -ForegroundColor Red
        continue
    }
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating: $currentAssetName ($i/$GenerateMultiple)" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Step 1: Generate description
    Write-Host "Step 1: Generating asset description with Ollama..." -ForegroundColor Yellow
    $description = Get-AssetDescription -AssetType $AssetType -AssetName $currentAssetName -UserPrompt $Prompt -VisualModel $VisualModel -PlanningModel $PlanningModel -OllamaModel $OllamaModel
    
    if (-not $description) {
        Write-Host "Failed to generate description. Using fallback." -ForegroundColor Red
        $description = "A $AssetType asset named $currentAssetName for the Magi-Tech mod"
    }
    
    Write-Host "Description: $description" -ForegroundColor Green
    Write-Host ""
    
    # Step 2: Extract parameters
    Write-Host "Step 2: Extracting parameters with Ollama..." -ForegroundColor Yellow
    $parameters = Get-AssetParameters -AssetType $AssetType -Description $description -VisualModel $VisualModel -PlanningModel $PlanningModel -AnalysisModel $AnalysisModel -OllamaModel $OllamaModel
    
    Write-Host "Parameters:" -ForegroundColor Green
    $parameters.PSObject.Properties | ForEach-Object {
        Write-Host "  $($_.Name): $($_.Value)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Step 2.5: Generate design draft/concept art (if SD3 available and enabled)
    # Default to enabled if not explicitly disabled
    $shouldGenerateDraft = if ($PSBoundParameters.ContainsKey("GenerateDesignDraft")) { $GenerateDesignDraft } else { $true }
    $designDraftPath = $null
    if ($shouldGenerateDraft -and $script:SD3Available) {
        Write-Host "Step 2.5: Generating design draft/concept art with SD3..." -ForegroundColor Yellow
        
        # Check if SD3 server is available
        $testConnectionCmd = Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue
        if ($testConnectionCmd) {
            Write-Host "  Checking SD3 server connection..." -ForegroundColor Gray
            try {
                $connectionTest = Test-StableDiffusionConnection -ErrorAction Stop
                if ($connectionTest) {
                # Create design drafts directory
                $designDraftsDir = Join-Path $OutputDir "DesignDrafts"
                if (-not (Test-Path $designDraftsDir)) {
                    New-Item -ItemType Directory -Path $designDraftsDir -Force | Out-Null
                }
                
                # Build enhanced prompt for design draft
                $designDraftPrompt = @"
Starbound game asset concept art, high-quality design draft, detailed illustration, 1024x1024.

ASSET TYPE: $AssetType
ASSET NAME: $currentAssetName
DESCRIPTION: $description

Create a detailed concept art design draft that establishes:
- Visual style and color palette
- Composition and layout
- Material characteristics and textures
- Lighting and mood
- Overall aesthetic direction

This design draft will serve as a visual reference for generating the final game asset sprite/texture.
Style: Starbound pixel art aesthetic, game-ready concept art, high detail, clear visual elements.
"@
                
                $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic, cartoon, stylized, unrealistic proportions"
                
                $designDraftFile = Join-Path $designDraftsDir "${currentAssetName}_design_draft.png"
                
                try {
                    if (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue) {
                        $sd3Params = @{
                            Prompt = $designDraftPrompt
                            OutputPath = $designDraftFile
                            NegativePrompt = $negativePrompt
                            Width = 1024
                            Height = 1024
                            Steps = 28
                            GuidanceScale = 7.0
                            EnhanceWithOllama = $true
                            AutoStartServer = $true
                        }
                        
                        # Use reference if provided and image strength > 0
                        if ($DesignDraftImageStrength -gt 0) {
                            # Look for existing design drafts as reference
                            $existingDrafts = Get-ChildItem -Path $designDraftsDir -Filter "*${AssetName}*design_draft*.png" -ErrorAction SilentlyContinue | 
                                Sort-Object LastWriteTime -Descending | Select-Object -First 1
                            if ($existingDrafts) {
                                $sd3Params.ReferenceImagePath = $existingDrafts.FullName
                                $sd3Params.ImageStrength = $DesignDraftImageStrength
                                Write-Host "  Using existing design draft as reference: $(Split-Path -Leaf $existingDrafts.FullName)" -ForegroundColor Gray
                            }
                        }
                        
                        Write-Host "  Calling Generate-AssetImageWithSD3..." -ForegroundColor Gray
                        Write-Host "    Prompt length: $($designDraftPrompt.Length) characters" -ForegroundColor Gray
                        Write-Host "    Output path: $designDraftFile" -ForegroundColor Gray
                        
                        $draftResult = Generate-AssetImageWithSD3 @sd3Params
                        
                        if ($draftResult) {
                            Write-Host "  [OK] Generate-AssetImageWithSD3 returned: $draftResult" -ForegroundColor Green
                            
                            # Check if file was created (might be different path if multiple images)
                            if (Test-Path $designDraftFile) {
                                $designDraftPath = $designDraftFile
                                Write-Host "  [OK] Design draft created: $(Split-Path -Leaf $designDraftFile)" -ForegroundColor Green
                            } elseif ($draftResult -is [string] -and (Test-Path $draftResult)) {
                                $designDraftPath = $draftResult
                                Write-Host "  [OK] Design draft created at alternative path: $(Split-Path -Leaf $draftResult)" -ForegroundColor Green
                            } elseif ($draftResult -is [array] -and $draftResult.Count -gt 0) {
                                $designDraftPath = $draftResult[0]
                                Write-Host "  [OK] Design draft created (multiple variants): $(Split-Path -Leaf $designDraftPath)" -ForegroundColor Green
                            } else {
                                Write-Host "  [WARN] Design draft generation returned result but file not found" -ForegroundColor Yellow
                                Write-Host "         Result type: $($draftResult.GetType().Name)" -ForegroundColor Gray
                                Write-Host "         Result value: $draftResult" -ForegroundColor Gray
                            }
                            
                            # Assess quality if enabled and file exists
                            if ($designDraftPath -and (Test-Path $designDraftPath) -and $script:QualityAssessmentAvailable -and $QualityAssessmentDepth -ne "fast") {
                                if (Get-Command Get-BestImageScore -ErrorAction SilentlyContinue) {
                                    try {
                                        $draftScore = Get-BestImageScore -ImagePath $designDraftPath -Depth $QualityAssessmentDepth
                                        Write-Host "  Design draft quality: $([math]::Round($draftScore, 1))/20" -ForegroundColor $(if ($draftScore -ge 15.0) { "Green" } else { "Yellow" })
                                    } catch {
                                        Write-Host "  [WARN] Quality assessment failed: $_" -ForegroundColor Yellow
                                    }
                                }
                            }
                        } else {
                            Write-Host "  [WARN] Design draft generation returned null/empty, continuing without reference" -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "  [WARN] Generate-AssetImageWithSD3 function not available" -ForegroundColor Yellow
                        Write-Host "         Check if StableDiffusionIntegration.psm1 is properly imported" -ForegroundColor Gray
                    }
                } catch {
                    Write-Host "  [ERROR] Design draft generation failed: $_" -ForegroundColor Red
                    Write-Host "         Exception type: $($_.Exception.GetType().Name)" -ForegroundColor Gray
                    Write-Host "         Exception message: $($_.Exception.Message)" -ForegroundColor Gray
                    if ($_.Exception.InnerException) {
                        Write-Host "         Inner exception: $($_.Exception.InnerException.Message)" -ForegroundColor Gray
                    }
                    Write-Host "         Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
                    Write-Host "         Continuing without design draft..." -ForegroundColor Yellow
                }
                } else {
                    Write-Host "  [INFO] SD3 server connection test failed" -ForegroundColor Yellow
                    Write-Host "         Attempting to start server automatically..." -ForegroundColor Gray
                    try {
                        if (Get-Command Start-StableDiffusionServerIfNeeded -ErrorAction SilentlyContinue) {
                            $serverStarted = Start-StableDiffusionServerIfNeeded -ErrorAction Stop
                            if ($serverStarted) {
                                Write-Host "  [OK] SD3 server started successfully" -ForegroundColor Green
                                # Retry connection test
                                Start-Sleep -Seconds 5
                                if (Test-StableDiffusionConnection) {
                                    Write-Host "  [OK] SD3 server is now responding" -ForegroundColor Green
                                    # Continue with draft generation (will be handled in next iteration or retry)
                                } else {
                                    Write-Host "  [WARN] SD3 server started but not responding yet, skipping design draft" -ForegroundColor Yellow
                                }
                            } else {
                                Write-Host "  [WARN] Could not start SD3 server, skipping design draft" -ForegroundColor Yellow
                            }
                        } else {
                            Write-Host "  [WARN] Start-StableDiffusionServerIfNeeded function not available" -ForegroundColor Yellow
                        }
                    } catch {
                        Write-Host "  [WARN] Failed to start SD3 server: $_" -ForegroundColor Yellow
                        Write-Host "         Skipping design draft generation" -ForegroundColor Gray
                    }
                }
            } catch {
                Write-Host "  [ERROR] Connection test failed: $_" -ForegroundColor Red
                Write-Host "         Skipping design draft generation" -ForegroundColor Gray
            }
        } else {
            Write-Host "  [INFO] Test-StableDiffusionConnection function not available" -ForegroundColor Yellow
            Write-Host "         SD3 integration module may not be fully loaded" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    # Step 3: Generate asset using existing generator
    Write-Host "Step 3: Generating asset..." -ForegroundColor Yellow
    
    # Validate PSScriptRoot before using it
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        Write-Host "Error: PSScriptRoot is null or empty, cannot locate StarboundAssetGenerator.ps1" -ForegroundColor Red
        exit 1
    }
    
    $assetGenerator = Join-Path $PSScriptRoot "StarboundAssetGenerator.ps1"
    
    # Validate assetGenerator path is not null or empty
    if ([string]::IsNullOrWhiteSpace($assetGenerator)) {
        Write-Host "Error: Failed to construct path to StarboundAssetGenerator.ps1" -ForegroundColor Red
        Write-Host "  PSScriptRoot: '$PSScriptRoot'" -ForegroundColor Gray
        exit 1
    }
    
    if (-not (Test-Path $assetGenerator)) {
        Write-Host "Error: StarboundAssetGenerator.ps1 not found at: $assetGenerator" -ForegroundColor Red
        exit 1
    }
    
    # Convert PSCustomObject to Hashtable
    $paramHashtable = @{}
    if ($parameters) {
        $parameters.PSObject.Properties | ForEach-Object {
            $paramHashtable[$_.Name] = $_.Value
        }
    }
    
    # Merge user-provided Parameters with extracted parameters (user-provided take precedence)
    # Handle both Hashtable and PSCustomObject types
    if ($Parameters -ne $null) {
        $userParams = @{}
        
        # Check if Parameters is a Hashtable
        if ($Parameters -is [hashtable]) {
            $userParams = $Parameters
        }
        # Check if Parameters is a PSCustomObject
        elseif ($Parameters -is [PSCustomObject]) {
            # Convert PSCustomObject to Hashtable
            $Parameters.PSObject.Properties | ForEach-Object {
                $userParams[$_.Name] = $_.Value
            }
        }
        # Check if Parameters has a Count property (might be a collection)
        elseif ($Parameters.PSObject.Properties -ne $null) {
            # Try to convert PSCustomObject-like object to Hashtable
            try {
                $Parameters.PSObject.Properties | ForEach-Object {
                    $userParams[$_.Name] = $_.Value
                }
            } catch {
                Write-Host "Warning: Could not convert Parameters to Hashtable, skipping user parameters: $_" -ForegroundColor Yellow
                $userParams = @{}
            }
        }
        
        # Merge user parameters into paramHashtable (only if we successfully converted)
        if ($userParams.Count -gt 0) {
            foreach ($key in $userParams.Keys) {
                $paramHashtable[$key] = $userParams[$key]
            }
        }
    }
    
    # Enhance description with design draft reference if available
    $enhancedDescription = $description
    if ($designDraftPath -and (Test-Path $designDraftPath)) {
        $enhancedDescription = "$description`n`nNOTE: A design draft/concept art has been generated at: $designDraftPath. Use this design draft as a visual reference to ensure the final asset matches the established style, colors, and composition."
        Write-Host "  Using design draft as visual reference for asset generation" -ForegroundColor Cyan
        Write-Host "    Design draft: $(Split-Path -Leaf $designDraftPath)" -ForegroundColor Gray
    }
    
    $generatorParams = @{
        AssetType = $AssetType
        AssetName = $currentAssetName
        Description = $enhancedDescription  # Enhanced description with design draft reference
        OutputDir = $OutputDir
        Parameters = $paramHashtable
        # Force description-based generation when Ollama description is available
        # The asset generator will prioritize the description over simple shape generation
        UseCppBackend = $false  # Use description-enhanced generation instead of C++ backend simple shapes
    }
    
    # Add design draft reference to parameters so asset generator can use it as reference
    if ($designDraftPath -and (Test-Path $designDraftPath)) {
        if (-not $generatorParams.Parameters) {
            $generatorParams.Parameters = @{}
        }
        $generatorParams.Parameters["DesignDraftPath"] = $designDraftPath
        $generatorParams.Parameters["ReferenceImage"] = $designDraftPath
        $generatorParams.Parameters["ReferenceImagePath"] = $designDraftPath
    }
    
    # Warn if C++ backend was requested but we're using description-based generation instead
    if ($UseCppBackend) {
        Write-Host "Note: Ollama description provided - using description-based generation for high-quality assets" -ForegroundColor Yellow
        Write-Host "      This ensures the Ollama-generated description is used instead of simple procedural shapes" -ForegroundColor Yellow
    }
    
    # Validate generatorParams.OutputDir before calling asset generator
    if ([string]::IsNullOrWhiteSpace($generatorParams.OutputDir)) {
        Write-Host "Error: OutputDir in generatorParams is null or empty" -ForegroundColor Red
        Write-Host "  Original OutputDir: '$OutputDir'" -ForegroundColor Gray
        exit 1
    }
    
    # Validate assetGenerator path before calling
    if ([string]::IsNullOrWhiteSpace($assetGenerator)) {
        Write-Host "Error: assetGenerator path is null or empty" -ForegroundColor Red
        Write-Host "  PSScriptRoot: '$PSScriptRoot'" -ForegroundColor Gray
        exit 1
    }
    
    try {
        & $assetGenerator @generatorParams
    } catch {
        Write-Host "Error: Failed to call asset generator: $_" -ForegroundColor Red
        Write-Host "  AssetGenerator: '$assetGenerator'" -ForegroundColor Gray
        Write-Host "  OutputDir: '$($generatorParams.OutputDir)'" -ForegroundColor Gray
        Write-Host "  AssetName: '$($generatorParams.AssetName)'" -ForegroundColor Gray
        Write-Host "  Error Details: $($_.Exception.Message)" -ForegroundColor Gray
        Write-Host "  Line: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Gray
        throw
    }
    
    # Post-process any generated images with ImageMagick
    # Validate PSScriptRoot before using it
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        Write-Host "  [WARNING] PSScriptRoot is null, skipping post-processor path construction" -ForegroundColor Yellow
    } else {
        $postProcessorPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\ImageMagickPostProcessor.psm1"
        if ([string]::IsNullOrWhiteSpace($postProcessorPath)) {
            Write-Host "  [WARNING] Failed to construct post-processor path, skipping post-processing" -ForegroundColor Yellow
        } elseif (Test-Path $postProcessorPath) {
            Import-Module $postProcessorPath -Force -DisableNameChecking -ErrorAction SilentlyContinue
            
            # Find generated images in output directory
            # Validate OutputDir again before using it (defensive check)
            if ([string]::IsNullOrWhiteSpace($OutputDir)) {
                Write-Host "  [WARNING] OutputDir is null or empty, skipping post-processing" -ForegroundColor Yellow
            } else {
                # Ensure OutputDir exists before searching (it might not exist if no assets generated yet)
                if (-not (Test-Path $OutputDir)) {
                    Write-Host "  [INFO] Output directory does not exist yet, skipping post-processing" -ForegroundColor Gray
                    if ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -ne "fast") {
                        Write-Host "  [WARN] Quality assessment skipped: Output directory does not exist" -ForegroundColor Yellow
                    }
                } else {
                    # Search for recently created images (within last 10 minutes to catch assets that just finished)
                    $searchStartTime = (Get-Date).AddMinutes(-10)
                    Write-Host "  Searching for generated images in: $OutputDir" -ForegroundColor Gray
                    Write-Host "    Looking for images matching '$currentAssetName' or created after $($searchStartTime.ToString('HH:mm:ss'))" -ForegroundColor Gray
                    
                    try {
                        $allImages = Get-ChildItem -Path $OutputDir -Filter "*.png" -Recurse -ErrorAction Stop
                        Write-Host "    Found $($allImages.Count) total PNG file(s) in output directory" -ForegroundColor Gray
                        
                        $generatedImages = $allImages | Where-Object { 
                            $_.Name -like "*$currentAssetName*" -or 
                            $_.LastWriteTime -gt $searchStartTime 
                        }
                        
                        Write-Host "  Found $($generatedImages.Count) image(s) matching criteria" -ForegroundColor Gray
                        
                        # If no images match criteria but we have recent images, show them for debugging
                        if ($generatedImages.Count -eq 0 -and $allImages.Count -gt 0) {
                            $recentImages = $allImages | Where-Object { $_.LastWriteTime -gt $searchStartTime }
                            if ($recentImages.Count -gt 0) {
                                Write-Host "    [INFO] Found $($recentImages.Count) recent image(s) that don't match name filter:" -ForegroundColor Yellow
                                foreach ($img in $recentImages | Select-Object -First 5) {
                                    Write-Host "      - $($img.Name) (created: $($img.LastWriteTime.ToString('HH:mm:ss')))" -ForegroundColor Gray
                                }
                                # Use recent images if no name match found
                                $generatedImages = $recentImages
                                Write-Host "    Using recent images for quality assessment" -ForegroundColor Cyan
                            }
                        }
                    } catch {
                        Write-Host "  [ERROR] Failed to search for images: $_" -ForegroundColor Red
                        $generatedImages = @()
                    }
                    
                    if ($generatedImages.Count -gt 0) {
                        Write-Host "  Post-processing $($generatedImages.Count) image(s) with ImageMagick in background..." -ForegroundColor Gray
                        
                        # Initialize background jobs list if not exists
                        if (-not $script:backgroundPostProcessingJobs) {
                            $script:backgroundPostProcessingJobs = @()
                        }
                        
                        # Quality assessment if enabled
                        if ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -ne "fast") {
                            Write-Host "  Assessing quality of $($generatedImages.Count) generated image(s)..." -ForegroundColor Cyan
                            Write-Host "    Quality Assessment Depth: $QualityAssessmentDepth" -ForegroundColor Gray
                            $lowQualityImages = @()
                            $assessedCount = 0
                            
                            foreach ($image in $generatedImages) {
                                if (Get-Command Get-BestImageScore -ErrorAction SilentlyContinue) {
                                    Write-Host "    Assessing: $($image.Name)..." -ForegroundColor Gray
                                    try {
                                        $score = Get-BestImageScore -ImagePath $image.FullName -Depth $QualityAssessmentDepth
                                        $assessedCount++
                                        if ($score -lt 15.0) {
                                            Write-Host "      [WARN] Low quality detected: $($image.Name) (score: $([math]::Round($score, 1))/20)" -ForegroundColor Yellow
                                            $lowQualityImages += $image
                                        } else {
                                            Write-Host "      [OK] Quality check passed: $($image.Name) (score: $([math]::Round($score, 1))/20)" -ForegroundColor Green
                                        }
                                    } catch {
                                        Write-Host "      [ERROR] Failed to assess quality for $($image.Name): $_" -ForegroundColor Red
                                    }
                                } else {
                                    Write-Host "    [WARN] Get-BestImageScore command not available, skipping quality assessment" -ForegroundColor Yellow
                                }
                            }
                            
                            Write-Host "  Quality assessment complete: $assessedCount/$($generatedImages.Count) images assessed" -ForegroundColor Cyan
                            if ($lowQualityImages.Count -gt 0) {
                                Write-Host "  [WARN] $($lowQualityImages.Count) image(s) failed quality assessment (score < 15.0)" -ForegroundColor Yellow
                                Write-Host "    Consider regenerating these assets:" -ForegroundColor Gray
                                foreach ($img in $lowQualityImages) {
                                    Write-Host "      - $($img.Name)" -ForegroundColor Gray
                                }
                            } else {
                                Write-Host "  [OK] All assessed images passed quality check" -ForegroundColor Green
                            }
                        } elseif ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -eq "fast") {
                            Write-Host "  Quality assessment skipped: Depth is 'fast' (sanity checks only, no AI models)" -ForegroundColor Gray
                        } elseif (-not $script:QualityAssessmentAvailable) {
                            Write-Host "  Quality assessment skipped: ImageQualityAssessment module not available" -ForegroundColor Yellow
                        }
                        
                        foreach ($image in $generatedImages) {
                            # Start background job for ImageMagick processing
                            $job = Start-Job -ScriptBlock {
                                param($ImagePath, $PostProcessorPath, $GameType, $Quality)
                                
                                try {
                                    # Import the post-processor module in the job context
                                    if (Test-Path $PostProcessorPath) {
                                        Import-Module $PostProcessorPath -Force -DisableNameChecking -ErrorAction SilentlyContinue
                                        
                                        # Process the image
                                        Process-AIGeneratedImage `
                                            -InputPath $ImagePath `
                                            -GameType $GameType `
                                            -Quality $Quality `
                                            -ErrorAction SilentlyContinue | Out-Null
                                    }
                                } catch {
                                    # Silently handle errors in background job
                                    # Errors are already logged by Process-AIGeneratedImage
                                }
                            } -ArgumentList $image.FullName, $postProcessorPath, "Starbound", "high"
                            
                            # Store job reference
                            $script:backgroundPostProcessingJobs += $job
                        }
                        
                        Write-Host "  Started $($generatedImages.Count) background job(s) for ImageMagick processing" -ForegroundColor Gray
                    }
                }
            }
        }
    }
    
    Write-Host ""
    Write-Host "[OK] Asset generation complete: $currentAssetName" -ForegroundColor Green
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  All Assets Generated" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output directory: $OutputDir" -ForegroundColor Green
Write-Host ""

# Wait for background ImageMagick post-processing jobs to complete
if ($script:backgroundPostProcessingJobs -and $script:backgroundPostProcessingJobs.Count -gt 0) {
    Write-Host "Waiting for background ImageMagick post-processing to complete..." -ForegroundColor Gray
    $runningJobs = $script:backgroundPostProcessingJobs | Where-Object { $_.State -eq "Running" }
    
    if ($runningJobs.Count -gt 0) {
        Write-Host "  $($runningJobs.Count) job(s) still processing..." -ForegroundColor Gray
        $runningJobs | Wait-Job -Timeout 300 | Out-Null  # Wait up to 5 minutes
        
        # Check for any remaining running jobs
        $stillRunning = $script:backgroundPostProcessingJobs | Where-Object { $_.State -eq "Running" }
        if ($stillRunning.Count -gt 0) {
            Write-Host "  [INFO] $($stillRunning.Count) job(s) still running in background - they will complete asynchronously" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK] All ImageMagick post-processing jobs completed" -ForegroundColor Green
        }
    } else {
        # All jobs already completed
        Write-Host "  [OK] All ImageMagick post-processing jobs completed" -ForegroundColor Green
    }
    
    # Clean up all completed/failed jobs
    $completedJobs = $script:backgroundPostProcessingJobs | Where-Object { $_.State -in @("Completed", "Failed") }
    if ($completedJobs.Count -gt 0) {
        $completedJobs | Remove-Job -Force | Out-Null
    }
    
    # Update the jobs list to only include running jobs
    $script:backgroundPostProcessingJobs = $script:backgroundPostProcessingJobs | Where-Object { $_.State -eq "Running" }
    
    Write-Host ""
}
