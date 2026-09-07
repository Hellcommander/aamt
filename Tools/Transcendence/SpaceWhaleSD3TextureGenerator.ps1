<#
.SYNOPSIS
    Space Whale SD3 Texture Generator
    Uses Stable Diffusion 3 to generate high-quality creative textures for Blender models and projectiles.
    
.DESCRIPTION
    Generates textures using SD3 Medium with Ollama prompt enhancement for:
    - Blender model textures (diffuse, normal, specular maps)
    - Projectile textures
    - Design drafts and concept art
    
.PARAMETER ShipRegistry
    Path to ship registry JSON file
    
.PARAMETER VisualRegistry
    Path to visual language registry JSON file
    
.PARAMETER OutputDir
    Output directory for generated textures
    
.PARAMETER TextureType
    Type of textures to generate: "blender", "projectile", "design_draft", or "all"
    
.PARAMETER Variations
    Number of variations per texture (default: 3)
    
.PARAMETER ShipId
    Optional: Filter by specific ship ID
    
.PARAMETER QualityThreshold
    Minimum quality score (out of 20) required to accept generated image (default: 17.0)
    Images below this threshold will be retried up to MaxRetries times
    
.PARAMETER MaxRetries
    Maximum number of retry attempts for images that don't meet quality threshold (default: 3)
    
.PARAMETER QualityAssessmentDepth
    Quality assessment depth: "fast" (sanity checks only), "mechanical" (Qwen3-VL-8B), "full" (both models)
    Models are loaded on-demand and unloaded after use to save VRAM
    
.EXAMPLE
    .\SpaceWhaleSD3TextureGenerator.ps1 -ShipRegistry "space_whale_ship_example.json" -VisualRegistry "space_whale_visual_language_registry.json" -OutputDir "Output/Textures" -TextureType "all"
    
.EXAMPLE
    .\SpaceWhaleSD3TextureGenerator.ps1 -ShipRegistry "space_whale_ship_example.json" -VisualRegistry "space_whale_visual_language_registry.json" -OutputDir "Output/Textures" -TextureType "all" -QualityThreshold 15.0 -MaxRetries 5
    
.EXAMPLE
    .\SpaceWhaleSD3TextureGenerator.ps1 -ShipRegistry "space_whale_ship_example.json" -VisualRegistry "space_whale_visual_language_registry.json" -OutputDir "Output/Textures" -TextureType "all" -QualityAssessmentDepth "full"
    Uses both Qwen3-VL-8B (mechanical QA) and LLaVA:13b (aesthetic) for complete quality assessment
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ShipRegistry,
    
    [Parameter(Mandatory=$true)]
    [string]$VisualRegistry,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    
    [string]$TextureType = "all",
    
    [int]$Variations = 3,
    
    [string]$ShipId = $null,
    
    [string]$ReferenceTextureDir = "",
    
    [double]$ImageStrength = 0.7,
    
    [switch]$IncludeFullShipArtwork,
    
    [double]$QualityThreshold = 17.0,
    
    [int]$MaxRetries = 3,
    
    [ValidateSet("fast", "mechanical", "full")]
    [string]$QualityAssessmentDepth = "fast"
)

# Import required modules
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sharedDir = Join-Path (Split-Path -Parent $scriptDir) "Shared"

# Prefer Shared/ai_resources.py (starts aamt-1338 on :1338). Fall back to the PS module.
$aiResources = Join-Path $sharedDir "ai_resources.py"
$txPipe = Join-Path $scriptDir "tx_ai_pipeline.py"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py -and (Test-Path -LiteralPath $txPipe)) {
    Write-Host "Checking Shared AI pipeline..." -ForegroundColor Cyan
    & $py $txPipe probe
    & $py $txPipe ensure image
    & $py $txPipe ensure mesh
} elseif ($py -and (Test-Path -LiteralPath $aiResources)) {
    Write-Host "Ensuring Shared image stage (SD3.5 :1338)..." -ForegroundColor Cyan
    & $py $aiResources --ensure image
}

# Import Stable Diffusion integration
$sdModule = Join-Path $sharedDir "StableDiffusionIntegration.psm1"
if (-not (Test-Path $sdModule)) {
    Write-Error "StableDiffusionIntegration.psm1 not found at: $sdModule"
    exit 1
}
# Suppress warning about unapproved verb "Generate" - this is expected and harmless
Import-Module $sdModule -Force -DisableNameChecking

# Import Ollama integration for prompt enhancement
$ollamaModule = Join-Path $sharedDir "OllamaIntegration.psm1"
if (Test-Path $ollamaModule) {
    Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue -DisableNameChecking
}

# Early SD3 server detection and startup (before loading registries)
Write-Host "Checking SD3 server status..." -ForegroundColor Cyan
$toolsRoot = Split-Path -Parent $scriptDir
if (Test-StableDiffusionConnection) {
    Write-Host "  [OK] SD3 server is already running" -ForegroundColor Green
} else {
    Write-Host "  SD3 server not detected, attempting to start..." -ForegroundColor Yellow
    if (Start-StableDiffusionServerIfNeeded -ToolsRoot $toolsRoot) {
        Write-Host "  [OK] SD3 server started successfully" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] SD3 server could not be started automatically" -ForegroundColor Yellow
        Write-Host "  You may need to start it manually before generation can proceed" -ForegroundColor Gray
    }
}

# Load registries
Write-Host "Loading registries..." -ForegroundColor Cyan
$shipData = Get-Content $ShipRegistry -Raw | ConvertFrom-Json
$visualData = Get-Content $VisualRegistry -Raw | ConvertFrom-Json

# Filter by ship ID if specified
if ($ShipId) {
    # Handle different registry structures
    if ($shipData.ships) {
        $shipData.ships = $shipData.ships | Where-Object { $_.id -eq $ShipId }
        Write-Host "  Filtered to ship ID: $ShipId ($($shipData.ships.Count) ship(s))" -ForegroundColor Green
    } elseif ($shipData.PSObject.Properties.Name -contains $ShipId) {
        # Registry might be keyed by ship ID
        $shipData = @{ ships = @($shipData.$ShipId) }
        Write-Host "  Filtered to ship ID: $ShipId" -ForegroundColor Green
    }
}

# Parse texture type (supports comma-separated values like "blender,projectile")
$textureTypes = $TextureType -split ',' | ForEach-Object { $_.Trim() }
if ($TextureType -eq "all") {
    $textureTypes = @("blender", "projectile", "design_draft")
    if ($IncludeFullShipArtwork) {
        $textureTypes += "full_ship_artwork"
    }
} elseif ($IncludeFullShipArtwork -and $textureTypes -notcontains "full_ship_artwork") {
    $textureTypes += "full_ship_artwork"
}

# Create output directories
$outputPath = New-Item -ItemType Directory -Path $OutputDir -Force
$blenderDir = Join-Path $outputPath "Blender"
$projectileDir = Join-Path $outputPath "Projectiles"
$designDir = Join-Path $outputPath "DesignDrafts"
$artworkDir = Join-Path $outputPath "FullShipArtwork"
$bestDir = Join-Path $outputPath "Best"

# Create output directories based on parsed types
if ($textureTypes -contains "blender" -or $textureTypes -contains "all") {
    New-Item -ItemType Directory -Path $blenderDir -Force | Out-Null
}
if ($textureTypes -contains "projectile" -or $textureTypes -contains "all") {
    New-Item -ItemType Directory -Path $projectileDir -Force | Out-Null
}
if ($textureTypes -contains "design_draft" -or $textureTypes -contains "all") {
    New-Item -ItemType Directory -Path $designDir -Force | Out-Null
}
if ($textureTypes -contains "full_ship_artwork" -or $textureTypes -contains "all") {
    New-Item -ItemType Directory -Path $artworkDir -Force | Out-Null
}
# Always create Best directory for saving best images
New-Item -ItemType Directory -Path $bestDir -Force | Out-Null

# Extract visual language colors (handle different structures)
$baseColor = "#1a2a3a"
$veinColor = "#66ccff"
$emissiveColor = "#88ffff"

# Try different registry structures
if ($visualData.colorPalettes -and $visualData.colorPalettes.primary) {
    $palette = $visualData.colorPalettes.primary
    $baseColor = $palette.baseColor
    $veinColor = $palette.veinColor
    $emissiveColor = $palette.emissiveColor
} elseif ($visualData.palette) {
    $baseColor = $visualData.palette.baseColor
    $veinColor = $visualData.palette.veinColor
    $emissiveColor = $visualData.palette.emissiveColor
} elseif ($visualData.baseColor) {
    $baseColor = $visualData.baseColor
    $veinColor = $visualData.veinColor
    $emissiveColor = $visualData.emissiveColor
}

Write-Host "  Using colors: Base=$baseColor, Vein=$veinColor, Emissive=$emissiveColor" -ForegroundColor Gray

# Quality threshold for retry logic (configurable via parameters)
# NOTE: Quality scoring only detects broken/corrupt images, not aesthetic quality
# Set threshold low to avoid unnecessary retries - real quality assessment requires AI models
$script:QualityThreshold = $QualityThreshold  # Minimum score out of 20 (default: 17.0, but sanity check returns 18.0 for valid images)
$script:MaxRetries = $MaxRetries  # Maximum retry attempts

# Vision model quality assessment configuration
$script:QualityAssessmentDepth = $QualityAssessmentDepth  # "fast" (sanity only), "mechanical" (Qwen3-VL), "full" (all models)
$script:VisionModels = @{
    "mechanical" = "qwen3-vl:8b"  # Technical defect detection
    "aesthetic" = "llava:13b"      # Professional quality judgment
}

# Logging setup for quality retry tracking
$script:QualityLogPath = Join-Path $OutputDir "quality_retry_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:QualityLogEnabled = $true

Write-Host "`nQuality Settings:" -ForegroundColor Cyan
Write-Host "  Threshold: $QualityThreshold/20" -ForegroundColor Gray
Write-Host "  Max Retries: $MaxRetries" -ForegroundColor Gray
Write-Host "  Assessment Depth: $QualityAssessmentDepth" -ForegroundColor Gray
if ($QualityAssessmentDepth -eq "fast") {
    Write-Host "    (Fast mode: Basic sanity checks only)" -ForegroundColor DarkGray
} elseif ($QualityAssessmentDepth -eq "mechanical") {
    Write-Host "    (Mechanical QA: Using Qwen3-VL-8B for technical defect detection)" -ForegroundColor DarkGray
} else {
    Write-Host "    (Full mode: Qwen3-VL-8B + LLaVA:13b for complete quality assessment)" -ForegroundColor DarkGray
}
Write-Host "  Quality Log: $script:QualityLogPath" -ForegroundColor Gray
Write-Host ""

function Write-QualityLog {
    <#
    .SYNOPSIS
    Writes quality retry information to log file.
    #>
    param(
        [string]$Message,
        [string]$Category = "",
        [int]$Attempt = 0,
        [double]$Score = 0.0,
        [string]$ImagePath = ""
    )
    
    if (-not $script:QualityLogEnabled) { return }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp]"
    
    if ($Category) { $logEntry += " [$Category]" }
    if ($Attempt -gt 0) { $logEntry += " [Attempt $Attempt]" }
    if ($Score -gt 0) { $logEntry += " [Score: $([math]::Round($Score, 2))/20]" }
    if ($ImagePath) { $logEntry += " [File: $(Split-Path -Leaf $ImagePath)]" }
    
    $logEntry += " $Message"
    
    try {
        Add-Content -Path $script:QualityLogPath -Value $logEntry -ErrorAction SilentlyContinue
    } catch {
        # Silently fail if logging can't write
    }
}

function Invoke-GenerateWithQualityRetry {
    <#
    .SYNOPSIS
    Wrapper function that generates an image and retries if quality score is below threshold.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [scriptblock]$GenerationScript,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath,
        
        [string]$Category = "",
        
        [int]$MaxRetries = $script:MaxRetries,
        
        [double]$QualityThreshold = $script:QualityThreshold
    )
    
    $attempt = 0
    $bestScore = 0.0
    $bestPath = $null
    $allScores = @()
    
    Write-QualityLog -Message "Starting quality retry generation" -Category $Category -ImagePath $OutputPath
    
    while ($attempt -lt $MaxRetries) {
        $attempt++
        
        try {
            # Generate image using the provided script block
            $result = & $GenerationScript
            
            if (-not $result -or -not (Test-Path $OutputPath)) {
                Write-QualityLog -Message "Generation failed" -Category $Category -Attempt $attempt -ImagePath $OutputPath
                if ($attempt -lt $MaxRetries) {
                    Write-Host "    [RETRY $attempt/$MaxRetries] Generation failed, retrying..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 2  # Brief delay before retry
                    continue
                } else {
                    Write-Host "    [ERROR] Generation failed after $MaxRetries attempts" -ForegroundColor Red
                    Write-QualityLog -Message "Generation failed after all retries" -Category $Category -Attempt $attempt
                    return $null
                }
            }
            
            # Assess quality (use configured depth)
            $score = Get-BestImageScore -ImagePath $OutputPath -Depth $script:QualityAssessmentDepth
            $allScores += $score
            Write-QualityLog -Message "Quality assessment completed" -Category $Category -Attempt $attempt -Score $score -ImagePath $OutputPath
            
            if ($score -ge $QualityThreshold) {
                Write-Host "    [OK] Quality score: $([math]::Round($score, 1))/20 (meets threshold $QualityThreshold)" -ForegroundColor Green
                Write-QualityLog -Message "Quality threshold met" -Category $Category -Attempt $attempt -Score $score -ImagePath $OutputPath
                
                # Save as best if it's the highest score so far
                if ($score -gt $bestScore) {
                    $bestScore = $score
                    $bestPath = $OutputPath
                    if ($Category) {
                        Save-BestImage -Category $Category -ImagePath $OutputPath -Score $score | Out-Null
                    }
                }
                
                Write-QualityLog -Message "Generation successful" -Category $Category -Attempt $attempt -Score $score -ImagePath $OutputPath
                return $OutputPath
            } else {
                Write-Host "    [RETRY $attempt/$MaxRetries] Quality score: $([math]::Round($score, 1))/20 (below threshold $QualityThreshold)" -ForegroundColor Yellow
                Write-QualityLog -Message "Quality below threshold, retrying" -Category $Category -Attempt $attempt -Score $score -ImagePath $OutputPath
                
                # Track best score even if below threshold
                if ($score -gt $bestScore) {
                    $bestScore = $score
                    $bestPath = $OutputPath
                }
                
                # Delete low-quality image before retry
                if (Test-Path $OutputPath) {
                    Remove-Item -Path $OutputPath -Force -ErrorAction SilentlyContinue
                }
                
                if ($attempt -lt $MaxRetries) {
                    Start-Sleep -Seconds 3  # Delay before retry (exponential backoff)
                }
            }
        } catch {
            Write-Host "    [ERROR] Attempt $attempt failed: $_" -ForegroundColor Red
            Write-QualityLog -Message "Exception during generation: $_" -Category $Category -Attempt $attempt -ImagePath $OutputPath
            if ($attempt -lt $MaxRetries) {
                Start-Sleep -Seconds 2
            }
        }
    }
    
    # If we exhausted retries, use the best we found (even if below threshold)
    if ($bestPath -and (Test-Path $bestPath)) {
        $avgScore = if ($allScores.Count -gt 0) { ($allScores | Measure-Object -Average).Average } else { $bestScore }
        Write-Host "    [WARN] Using best result after $MaxRetries attempts: $([math]::Round($bestScore, 1))/20 (avg: $([math]::Round($avgScore, 1))/20)" -ForegroundColor Yellow
        Write-Host "    [INFO] Quality threshold ($QualityThreshold/20) not met. Consider:" -ForegroundColor Cyan
        Write-Host "      - Increasing generation steps for better detail" -ForegroundColor Gray
        Write-Host "      - Adjusting guidance scale for better prompt adherence" -ForegroundColor Gray
        Write-Host "      - Using different seeds or seed variation" -ForegroundColor Gray
        Write-Host "      - Lowering quality threshold if acceptable (current: $QualityThreshold/20)" -ForegroundColor Gray
        Write-QualityLog -Message "Using best result after all retries" -Category $Category -Attempt $attempt -Score $bestScore -ImagePath $bestPath
        
        if ($Category) {
            Save-BestImage -Category $Category -ImagePath $bestPath -Score $bestScore | Out-Null
        }
        return $bestPath
    }
    
    Write-Host "    [ERROR] Failed to generate acceptable quality after $MaxRetries attempts" -ForegroundColor Red
    Write-Host "    [INFO] Troubleshooting suggestions:" -ForegroundColor Cyan
    Write-Host "      - Check SD3 server is running and responding" -ForegroundColor Gray
    Write-Host "      - Verify output directory is writable" -ForegroundColor Gray
    Write-Host "      - Review quality log: $script:QualityLogPath" -ForegroundColor Gray
    Write-Host "      - Try increasing MaxRetries (current: $MaxRetries)" -ForegroundColor Gray
    Write-QualityLog -Message "Failed to generate after all retries" -Category $Category -Attempt $attempt
    return $null
}

function Generate-BlenderTexture {
    <#
    .SYNOPSIS
    Generate texture for Blender model (diffuse map).
    #>
    param(
        [object]$Ship,
        [int]$Variation = 0
    )
    
    $shipId = if ($Ship.id) { $Ship.id } else { $Ship.PSObject.Properties.Name[0] }
    $shipName = if ($Ship.name) { $Ship.name } else { $shipId }
    $shipDesc = if ($Ship.description) { $Ship.description } else { if ($Ship.visual.description) { $Ship.visual.description } else { "Space whale capital ship" } }
    
    # Extract detailed ship information for enhanced prompts
    $shipDetails = @{
        length = if ($Ship.visual.silhouette.currentSize.length) { $Ship.visual.silhouette.currentSize.length } else { 8.0 }
        width = if ($Ship.visual.silhouette.currentSize.width) { $Ship.visual.silhouette.currentSize.width } else { 3.5 }
        height = if ($Ship.visual.silhouette.currentSize.height) { $Ship.visual.silhouette.currentSize.height } else { 2.0 }
        profile = if ($Ship.visual.silhouette.profile) { $Ship.visual.silhouette.profile } else { "streamlined" }
        skinType = if ($Ship.visual.materials.skinType) { $Ship.visual.materials.skinType } else { "bioluminescent" }
        gillCount = if ($Ship.visual.animations.gillVentCount) { $Ship.visual.animations.gillVentCount } else { 6 }
    }
    
    # Look for reference texture (prioritize design drafts, then BEST images, then procedural textures)
    $referenceImage = $null
    if ($ReferenceTextureDir -and (Test-Path $ReferenceTextureDir)) {
        # First, try to find design drafts (best visual reference for textures)
        $bestDesignDir = Join-Path $ReferenceTextureDir "Best\design_draft"
        if (Test-Path $bestDesignDir) {
            $bestDesignRefs = Get-ChildItem -Path $bestDesignDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($bestDesignRefs) {
                $referenceImage = $bestDesignRefs.FullName
                Write-Host "    Using BEST design draft as reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Green
            }
        }
        
        if (-not $referenceImage) {
            $designDraftDir = Join-Path $ReferenceTextureDir "DesignDrafts"
            if (Test-Path $designDraftDir) {
                $designDraftRefs = Get-ChildItem -Path $designDraftDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($designDraftRefs) {
                    $referenceImage = $designDraftRefs.FullName
                    Write-Host "    Using design draft as reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Cyan
                }
            }
        }
        
        # Second, try BEST Blender textures
        if (-not $referenceImage) {
            $bestBlenderDir = Join-Path $ReferenceTextureDir "Best\blender"
            if (Test-Path $bestBlenderDir) {
                $bestRefs = Get-ChildItem -Path $bestBlenderDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($bestRefs) {
                    $referenceImage = $bestRefs.FullName
                }
            }
        }
        
        # Third, try procedural textures
        if (-not $referenceImage) {
            $possibleRefs = @(
                (Join-Path $ReferenceTextureDir "${shipId}_diffuse.png"),
                (Join-Path $ReferenceTextureDir "${shipId}_texture.png"),
                (Join-Path $ReferenceTextureDir "${shipId}.png"),
                (Get-ChildItem -Path $ReferenceTextureDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1)
            )
            
            foreach ($ref in $possibleRefs) {
                if ($ref -and (Test-Path $ref)) {
                    $referenceImage = $ref
                    break
                }
            }
        }
    }
    
    # Build detailed prompt for Blender texture based on ship description and details
    $prompt = @"
Space whale capital ship texture, high-quality game asset, 4K resolution, detailed organic-mechanical hybrid design.

SHIP DESCRIPTION: $shipName - $shipDesc

SHIP SPECIFICATIONS:
- Dimensions: $($shipDetails.length) length × $($shipDetails.width) width × $($shipDetails.height) height
- Profile: $($shipDetails.profile)
- Skin Type: $($shipDetails.skinType)
- Gill Vents: $($shipDetails.gillCount) pairs

MATERIALS (based on ship description):
- Living $($shipDetails.skinType) skin: smooth, translucent organic membrane
- Dark navy base color ($baseColor) with bright cyan vein network ($veinColor)
- Crystalline armor plates: semi-transparent, faceted appearance
- Subsurface scattering creating soft internal glow
- Intense white-cyan emissive core ($emissiveColor)

TEXTURE DETAILS (matching ship design):
- Subtle organic wrinkles and folds matching $($shipDetails.profile) profile
- Very faint scale-like texture pattern
- Glowing energy runes and crystalline tech nodes
- Visible energy conduits connecting $($shipDetails.gillCount) gill vent pairs
- Procedural noise for organic variation
- High detail, smooth surfaces, intense glows

STYLE: Nova Drift aesthetic - high-energy glows, smooth additive effects, organic-meets-technological
LIGHTING: Glows from within, central Bio-Core pulses, energy flows through veins
SCALE: Massive capital ship presence, ancient and evolved

Technical: Seamless tileable texture, 1024x1024 or 2048x2048, high detail, game-ready, no text or watermarks

IMPORTANT: Create texture that matches the ship description "$shipDesc" and follows the design specifications above. Use the reference design draft as a visual guide for color, style, and detail consistency.
"@
    
    $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic, cartoon, stylized, unrealistic"
    
    $outputFile = Join-Path $blenderDir "${shipId}_diffuse_v${Variation:00d}.png"
    
    Write-Host "  Generating Blender texture for $shipName (variation $Variation)..." -ForegroundColor Cyan
    if ($referenceImage) {
        Write-Host "    Using reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Gray
    }
    
    # Use retry wrapper with quality checking
    $result = Invoke-GenerateWithQualityRetry -OutputPath $outputFile -Category "blender" -GenerationScript {
        $params = @{
            Prompt = $prompt
            OutputPath = $outputFile
            NegativePrompt = $negativePrompt
            Width = 1024
            Height = 1024
            Steps = 28
            GuidanceScale = 7.0
            EnhanceWithOllama = $true
            AutoStartServer = $true
        }
        
        if ($referenceImage) {
            $params.ReferenceImagePath = $referenceImage
            $params.ImageStrength = $ImageStrength
        }
        
        Generate-AssetImageWithSD3 @params
    }
    
    return $result
}

function Generate-ProjectileTexture {
    <#
    .SYNOPSIS
    Generate texture for projectile (energy bolt, plasma ball, etc.).
    #>
    param(
        [string]$ProjectileType = "energy_bolt",
        [int]$Variation = 0
    )
    
    $projectilePrompts = @{
        "energy_bolt" = @"
Space whale energy projectile, high-quality game asset, 512x512, detailed energy weapon.

VISUAL: Bright cyan-white energy core ($emissiveColor) with dark navy outer shell ($baseColor)
STYLE: Nova Drift - high-energy glows, smooth additive effects, particle-driven motion
DETAILS: Concentric energy rings, plasma trails, intense core glow, energy distortion
COMPOSITION: Centered energy bolt, radial energy waves, glowing particles
TECHNICAL: Seamless, tileable, game-ready, no text or watermarks
"@
        "plasma_ball" = @"
Space whale plasma projectile, high-quality game asset, 512x512, detailed plasma weapon.

VISUAL: Magenta-pink plasma core with cyan rim ($veinColor), dark navy base ($baseColor)
STYLE: Nova Drift - plasma oscillations, magnetosonic waves, harmonic aurora effects
DETAILS: Swirling plasma patterns, energy vortices, intense core, plasma trails
COMPOSITION: Spherical plasma ball, energy rings, particle effects
TECHNICAL: Seamless, tileable, game-ready, no text or watermarks
"@
        "bio_missile" = @"
Space whale bio-organic missile, high-quality game asset, 512x512, detailed organic weapon.

VISUAL: Organic shell with crystalline tech overlay, bioluminescent core ($emissiveColor)
STYLE: Nova Drift - organic-mechanical hybrid, living weapon aesthetic
DETAILS: Segmented organic body, crystalline fins, glowing energy core, bio-tech patterns
COMPOSITION: Missile shape, fins, energy trail, organic details
TECHNICAL: Seamless, tileable, game-ready, no text or watermarks
"@
    }
    
    $prompt = $projectilePrompts[$ProjectileType]
    if (-not $prompt) {
        $prompt = $projectilePrompts["energy_bolt"]
    }
    
    $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic, cartoon"
    
    $outputFile = Join-Path $projectileDir "${ProjectileType}_v${Variation:00d}.png"
    
    Write-Host "  Generating projectile texture: $ProjectileType (variation $Variation)..." -ForegroundColor Cyan
    
    # Use retry wrapper with quality checking
    $result = Invoke-GenerateWithQualityRetry -OutputPath $outputFile -Category "projectile" -GenerationScript {
        Generate-AssetImageWithSD3 `
            -Prompt $prompt `
            -OutputPath $outputFile `
            -NegativePrompt $negativePrompt `
            -Width 512 `
            -Height 512 `
            -Steps 28 `
            -GuidanceScale 7.0 `
            -EnhanceWithOllama:$true `
            -AutoStartServer:$true
    }
    
    return $result
}

function Generate-FullShipArtwork {
    <#
    .SYNOPSIS
    Generate complete full ship artwork showing the entire ship design.
    #>
    param(
        [object]$Ship,
        [int]$Variation = 0,
        [string]$View = "side"
    )
    
    $shipId = if ($Ship.id) { $Ship.id } else { $Ship.PSObject.Properties.Name[0] }
    $shipName = if ($Ship.name) { $Ship.name } else { $shipId }
    $shipDesc = if ($Ship.description) { $Ship.description } else { if ($Ship.visual.description) { $Ship.visual.description } else { "Space whale capital ship" } }
    
    # Extract detailed ship information for enhanced prompts
    $length = if ($Ship.visual.silhouette.currentSize.length) { $Ship.visual.silhouette.currentSize.length } else { 8.0 }
    $width = if ($Ship.visual.silhouette.currentSize.width) { $Ship.visual.silhouette.currentSize.width } else { 3.5 }
    $height = if ($Ship.visual.silhouette.currentSize.height) { $Ship.visual.silhouette.currentSize.height } else { 2.0 }
    $profile = if ($Ship.visual.silhouette.profile) { $Ship.visual.silhouette.profile } else { "streamlined" }
    $skinType = if ($Ship.visual.materials.skinType) { $Ship.visual.materials.skinType } else { "bioluminescent" }
    $gillCount = if ($Ship.visual.animations.gillVentCount) { $Ship.visual.animations.gillVentCount } else { 6 }
    $breathingSpeed = if ($Ship.visual.animations.breathingSpeed) { $Ship.visual.animations.breathingSpeed } else { 0.8 }
    $dorsalCrestGlow = if ($Ship.visual.animations.dorsalCrestGlow) { $Ship.visual.animations.dorsalCrestGlow } else { $true }
    
    # Look for reference images (prioritize design drafts as primary reference)
    $referenceImage = $null
    if ($ReferenceTextureDir -and (Test-Path $ReferenceTextureDir)) {
        # First, try to find BEST design drafts (best visual reference for full ship artwork)
        $bestDesignDir = Join-Path $ReferenceTextureDir "Best\design_draft"
        if (Test-Path $bestDesignDir) {
            $bestDesignRefs = Get-ChildItem -Path $bestDesignDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($bestDesignRefs) {
                $referenceImage = $bestDesignRefs.FullName
                Write-Host "    Using BEST design draft as reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Green
            }
        }
        
        # Second, try existing design drafts (primary reference for full ship artwork)
        if (-not $referenceImage) {
            $designDraftDir = Join-Path $ReferenceTextureDir "DesignDrafts"
            if (Test-Path $designDraftDir) {
                $designDraftRefs = Get-ChildItem -Path $designDraftDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($designDraftRefs) {
                    $referenceImage = $designDraftRefs.FullName
                    Write-Host "    Using design draft as reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Cyan
                }
            }
        }
        
        # Third, try BEST full ship artwork (for consistency across views)
        if (-not $referenceImage) {
            $bestArtworkDir = Join-Path $ReferenceTextureDir "Best\full_ship_artwork"
            if (Test-Path $bestArtworkDir) {
                $bestArtworkRefs = Get-ChildItem -Path $bestArtworkDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($bestArtworkRefs) {
                    $referenceImage = $bestArtworkRefs.FullName
                }
            }
        }
        
        # Fourth, try existing full artwork
        if (-not $referenceImage) {
            $artworkDir = Join-Path $ReferenceTextureDir "FullShipArtwork"
            if (Test-Path $artworkDir) {
                $artworkRefs = Get-ChildItem -Path $artworkDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($artworkRefs) {
                    $referenceImage = $artworkRefs.FullName
                }
            }
        }
        
        # If no reference found, try other textures
        if (-not $referenceImage) {
            $possibleRefs = @(
                (Join-Path $ReferenceTextureDir "${shipId}_design_draft.png"),
                (Join-Path $ReferenceTextureDir "${shipId}_concept.png"),
                (Get-ChildItem -Path $ReferenceTextureDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1)
            )
            
            foreach ($ref in $possibleRefs) {
                if ($ref -and (Test-Path $ref)) {
                    $referenceImage = $ref
                    break
                }
            }
        }
    }
    
    # Build view-specific composition descriptions
    $viewDescriptions = @{
        "side" = "Side profile view, full length visible, dramatic side lighting, space background with stars"
        "front" = "Front view, head-on perspective, symmetrical composition, glowing Bio-Core visible through translucent skin"
        "three_quarter" = "Three-quarter view, dynamic angle showing both side and front, cinematic perspective"
        "top" = "Top-down view, dorsal crest prominent, full length visible, bioluminescent patterns visible"
        "dramatic" = "Dramatic cinematic angle, low perspective looking up, ship dominates frame, epic scale"
    }
    
    $composition = $viewDescriptions[$View]
    if (-not $composition) {
        $composition = $viewDescriptions["side"]
    }
    
    # Build detailed prompt for full ship artwork based on ship description and design drafts
    $prompt = @"
Complete space whale capital ship artwork, high-quality full ship render, detailed illustration, 2048x2048.

SHIP DESCRIPTION: $shipName - $shipDesc

COMPLETE SHIP DESIGN (based on description and design drafts):
- Full ship visible in frame, complete from head to tail
- Dimensions: ${length} length × ${width} width × ${height} height
- Profile: $profile whale shape with organic-mechanical hybrid design
- Bulbous head with wide mouth opening, visible internal structures
- Elongated cylindrical mid-section with ventral belly bulge
- Tapering tail with horizontal fin, prominent dorsal crest
- All major features visible: $gillCount pairs of gill vents, Bio-Core, energy conduits
- Skin type: $skinType with bioluminescent properties
- Breathing rhythm: $breathingSpeed speed, dorsal crest glow: $dorsalCrestGlow

MATERIALS & COLORS (from ship description):
- Living $($shipDetails.skinType) skin: smooth, translucent organic membrane
- Dark navy base ($baseColor) with bright cyan vein network ($veinColor)
- Crystalline armor plates: semi-transparent, faceted appearance
- Intense white-cyan emissive core ($emissiveColor) pulsing rhythmically at $($shipDetails.breathingSpeed) speed
- Magenta-pink energy accents throughout

LIGHTING & EFFECTS (from ship description):
- Glows from within: central Bio-Core pulses with visible energy waves
- Energy flows through vein network in cascading waves
- $($shipDetails.gillCount) pairs of gill vents pulse with bioluminescent light
- Dorsal crest glows with intricate bioluminescent patterns: $($shipDetails.dorsalCrestGlow)
- All light uses additive blending for intense, vibrant glows
- Dynamic lighting creates depth and dimension

STYLE: Nova Drift aesthetic - high-energy glows, smooth additive effects, organic-meets-technological
MOOD: Ancient, evolved, massive capital ship, dominates the frame, inspires awe and respect
COMPOSITION: $composition

TECHNICAL: Ultra-high detail, complete ship visible, smooth surfaces, intense glows, cinematic quality, professional game artwork, no text or watermarks

IMPORTANT: Create artwork that accurately represents the ship description "$shipDesc" and follows all design specifications above. Use the reference design draft as a visual guide to ensure consistency with the established design.
"@
    
    $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic, cartoon, stylized, unrealistic proportions, partial ship, cropped, incomplete"
    
    $viewSuffix = if ($View -ne "side") { "_${View}" } else { "" }
    $outputFile = Join-Path $artworkDir "${shipId}_full_ship${viewSuffix}_v${Variation:00d}.png"
    
    Write-Host "  Generating full ship artwork for $shipName ($View view, variation $Variation)..." -ForegroundColor Cyan
    if ($referenceImage) {
        Write-Host "    Using reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Gray
    }
    
    # Use retry wrapper with quality checking
    $result = Invoke-GenerateWithQualityRetry -OutputPath $outputFile -Category "full_ship_artwork" -GenerationScript {
        $params = @{
            Prompt = $prompt
            OutputPath = $outputFile
            NegativePrompt = $negativePrompt
            Width = 2048
            Height = 2048
            Steps = 28
            GuidanceScale = 7.0
            EnhanceWithOllama = $true
            AutoStartServer = $true
        }
        
        if ($referenceImage) {
            $params.ReferenceImagePath = $referenceImage
            # Use higher strength for design drafts (they provide complete visual reference)
            $strength = if ($referenceImage -like "*design_draft*" -or $referenceImage -like "*DesignDrafts*") { 
                [Math]::Min($ImageStrength + 0.15, 0.9) 
            } elseif ($referenceImage -like "*FullShipArtwork*") {
                [Math]::Min($ImageStrength + 0.1, 0.85)
            } else { 
                $ImageStrength 
            }
            $params.ImageStrength = $strength
            Write-Host "    Reference strength: $strength (design draft provides complete visual guide)" -ForegroundColor Gray
        }
        
        Generate-AssetImageWithSD3 @params
    }
    
    return $result
}

function Generate-DesignDraft {
    <#
    .SYNOPSIS
    Generate design draft/concept art for space whale ship.
    #>
    param(
        [object]$Ship,
        [int]$Variation = 0
    )
    
    $shipId = if ($Ship.id) { $Ship.id } else { $Ship.PSObject.Properties.Name[0] }
    $shipName = if ($Ship.name) { $Ship.name } else { $shipId }
    $shipDesc = if ($Ship.description) { $Ship.description } else { if ($Ship.visual.description) { $Ship.visual.description } else { "Space whale capital ship" } }
    
    # Extract detailed ship information for enhanced prompts
    $shipDetails = @{
        length = if ($Ship.visual.silhouette.currentSize.length) { $Ship.visual.silhouette.currentSize.length } else { 8.0 }
        width = if ($Ship.visual.silhouette.currentSize.width) { $Ship.visual.silhouette.currentSize.width } else { 3.5 }
        height = if ($Ship.visual.silhouette.currentSize.height) { $Ship.visual.silhouette.currentSize.height } else { 2.0 }
        profile = if ($Ship.visual.silhouette.profile) { $Ship.visual.silhouette.profile } else { "streamlined" }
        skinType = if ($Ship.visual.materials.skinType) { $Ship.visual.materials.skinType } else { "bioluminescent" }
        gillCount = if ($Ship.visual.animations.gillVentCount) { $Ship.visual.animations.gillVentCount } else { 6 }
        breathingSpeed = if ($Ship.visual.animations.breathingSpeed) { $Ship.visual.animations.breathingSpeed } else { 0.8 }
        dorsalCrestGlow = if ($Ship.visual.animations.dorsalCrestGlow) { $Ship.visual.animations.dorsalCrestGlow } else { $true }
    }
    
    # Look for reference image (prioritize BEST design drafts, then existing design drafts)
    $referenceImage = $null
    if ($ReferenceTextureDir -and (Test-Path $ReferenceTextureDir)) {
        # First, try to find BEST images (highest quality references)
        $bestBlenderDir = Join-Path $ReferenceTextureDir "Best\blender"
        if (Test-Path $bestBlenderDir) {
            $bestRefs = Get-ChildItem -Path $bestBlenderDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($bestRefs) {
                $referenceImage = $bestRefs.FullName
                Write-Host "    Using BEST reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Green
            }
        }
        
        # Second, try best design drafts (highest quality)
        if (-not $referenceImage) {
            $bestDesignDir = Join-Path $ReferenceTextureDir "Best\design_draft"
            if (Test-Path $bestDesignDir) {
                $bestDesignRefs = Get-ChildItem -Path $bestDesignDir -Filter "*${shipId}*best*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($bestDesignRefs) {
                    $referenceImage = $bestDesignRefs.FullName
                    Write-Host "    Using BEST reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Green
                }
            }
        }
        
        # Third, try existing design drafts
        if (-not $referenceImage) {
            $designDraftDir = Join-Path $ReferenceTextureDir "DesignDrafts"
            if (Test-Path $designDraftDir) {
                $designDraftRefs = Get-ChildItem -Path $designDraftDir -Filter "*${shipId}*design_draft*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($designDraftRefs) {
                    $referenceImage = $designDraftRefs.FullName
                }
            }
        }
        
        # If no best/design draft found, try other references
        if (-not $referenceImage) {
            $possibleRefs = @(
                (Join-Path $ReferenceTextureDir "${shipId}_design_draft.png"),
                (Join-Path $ReferenceTextureDir "${shipId}_concept.png"),
                (Join-Path $ReferenceTextureDir "${shipId}_diffuse.png"),
                (Get-ChildItem -Path $ReferenceTextureDir -Filter "*${shipId}*.png" -ErrorAction SilentlyContinue | Select-Object -First 1)
            )
            
            foreach ($ref in $possibleRefs) {
                if ($ref -and (Test-Path $ref)) {
                    $referenceImage = $ref
                    break
                }
            }
        }
    }
    
    # Build detailed prompt for design draft based on ship description and specifications
    $prompt = @"
Space whale capital ship concept art, high-quality game design draft, detailed illustration, 1024x1024.

SHIP DESCRIPTION: $shipName - $shipDesc

SHIP DESIGN (based on description and specifications):
- $($shipDetails.profile) whale shape: $($shipDetails.length) length × $($shipDetails.width) width × $($shipDetails.height) height
- Bulbous head with wide mouth opening
- Elongated cylindrical mid-section with ventral belly bulge
- Tapering tail with horizontal fin
- Prominent dorsal crest running along the top
- $($shipDetails.gillCount) pairs of gill vents for energy exchange

MATERIALS & COLORS (from ship description):
- Living $($shipDetails.skinType) skin: smooth, translucent organic membrane
- Dark navy base ($baseColor) with bright cyan veins ($veinColor)
- Crystalline armor plates: semi-transparent, faceted
- Intense white-cyan emissive core ($emissiveColor)
- Magenta-pink energy accents

LIGHTING & EFFECTS (from ship description):
- Glows from within: central Bio-Core pulses rhythmically at $($shipDetails.breathingSpeed) speed
- Energy flows through vein network in waves
- $($shipDetails.gillCount) pairs of gill vents pulse with light
- Dorsal crest glows with bioluminescent patterns: $($shipDetails.dorsalCrestGlow)
- All light uses additive blending for intensity

STYLE: Nova Drift aesthetic - high-energy glows, smooth additive effects, procedural distortion
MOOD: Ancient, evolved, dominates the screen, inspires awe and respect
COMPOSITION: Side view, dramatic lighting, space background, cinematic framing

Technical: High detail, smooth surfaces, intense glows, game concept art quality, no text or watermarks

IMPORTANT: Create design draft that accurately represents the ship description "$shipDesc" and follows all design specifications above. This will serve as a reference for future texture and artwork generation.
"@
    
    $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic, cartoon, stylized, unrealistic proportions"
    
    $outputFile = Join-Path $designDir "${shipId}_design_draft_v${Variation:00d}.png"
    
    Write-Host "  Generating design draft for $shipName (variation $Variation)..." -ForegroundColor Cyan
    if ($referenceImage) {
        Write-Host "    Using reference: $(Split-Path -Leaf $referenceImage)" -ForegroundColor Gray
    }
    
    # Use retry wrapper with quality checking
    $result = Invoke-GenerateWithQualityRetry -OutputPath $outputFile -Category "design_draft" -GenerationScript {
        $params = @{
            Prompt = $prompt
            OutputPath = $outputFile
            NegativePrompt = $negativePrompt
            Width = 1024
            Height = 1024
            Steps = 28
            GuidanceScale = 7.0
            EnhanceWithOllama = $true
            AutoStartServer = $true
        }
        
        if ($referenceImage) {
            $params.ReferenceImagePath = $referenceImage
            $params.ImageStrength = $ImageStrength
        }
        
        Generate-AssetImageWithSD3 @params
    }
    
    return $result
}

# Main generation loop
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Space Whale SD3 Texture Generator" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Texture Type: $TextureType" -ForegroundColor Yellow
Write-Host "Variations per texture: $Variations" -ForegroundColor Yellow
if ($textureTypes -notcontains "design_draft") {
    Write-Host "Mode: FAST (design drafts disabled)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: FULL (includes design drafts)" -ForegroundColor Yellow
}
Write-Host "Output: $OutputDir" -ForegroundColor Yellow
if ($ReferenceTextureDir -and (Test-Path $ReferenceTextureDir)) {
    Write-Host "Reference textures: $ReferenceTextureDir" -ForegroundColor Yellow
    Write-Host "Image strength: $ImageStrength" -ForegroundColor Yellow
} else {
    Write-Host "Reference textures: None (text-to-image mode)" -ForegroundColor Gray
}
Write-Host "============================================================`n" -ForegroundColor Cyan

$totalGenerated = 0
$totalFailed = 0

# Track best images for each category
$bestImages = @{
    "blender" = @{}
    "projectile" = @{}
    "design_draft" = @{}
    "full_ship_artwork" = @{}
}

function Save-BestImage {
    <#
    .SYNOPSIS
    Saves the best image to the Best directory and updates tracking.
    #>
    param(
        [string]$Category,
        [string]$ImagePath,
        [string]$ShipId = "",
        [string]$View = "",
        [double]$Score = 0.0
    )
    
    if (-not (Test-Path $ImagePath)) {
        return
    }
    
    # Create category subdirectory in Best
    $categoryBestDir = Join-Path $bestDir $Category
    New-Item -ItemType Directory -Path $categoryBestDir -Force | Out-Null
    
    # Generate best image filename
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($ImagePath)
    $extension = [System.IO.Path]::GetExtension($ImagePath)
    
    if ($ShipId) {
        $bestFileName = "${ShipId}_best${extension}"
    } elseif ($View) {
        $bestFileName = "${baseName}_best${extension}"
    } else {
        $bestFileName = "${baseName}_best${extension}"
    }
    
    $bestPath = Join-Path $categoryBestDir $bestFileName
    
    try {
        # Copy image to Best directory
        Copy-Item -Path $ImagePath -Destination $bestPath -Force
        Write-Host "    [BEST] Saved to: $bestPath" -ForegroundColor Green
        
        # Track best image
        $key = if ($ShipId) { $ShipId } else { $baseName }
        if (-not $bestImages[$Category].ContainsKey($key) -or $bestImages[$Category][$key].Score -lt $Score) {
            $bestImages[$Category][$key] = @{
                Path = $bestPath
                Score = $Score
                OriginalPath = $ImagePath
            }
        }
        
        return $bestPath
    } catch {
        Write-Host "    [WARN] Failed to save best image: $_" -ForegroundColor Yellow
        return $null
    }
}

# Unload-OllamaModel is now provided by OllamaIntegration.psm1
# If not available, use local fallback
if (-not (Get-Command Unload-OllamaModel -ErrorAction SilentlyContinue)) {
    function Unload-OllamaModel {
        <#
        .SYNOPSIS
        Unloads an Ollama model from VRAM to free memory (local fallback).
        #>
        param(
            [string]$ModelName
        )
        
        try {
            # Use Ollama API to unload model (keep_alive: 0)
            $ollamaUrl = "http://localhost:11434/api/generate"
            $body = @{
                model = $ModelName
                prompt = ""
                keep_alive = 0
                stream = $false
            } | ConvertTo-Json -Compress
            
            $null = Invoke-RestMethod -Uri $ollamaUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
            Write-QualityLog -Message "Unloaded model: $ModelName" -ImagePath ""
        } catch {
            # Try CLI method as fallback
            try {
                $null = & ollama stop $ModelName 2>&1
            } catch {
                # Ignore errors - model may already be unloaded
            }
        }
    }
}

function Invoke-VisionQualityAssessment {
    <#
    .SYNOPSIS
    Calls vision-language models via Ollama to assess image quality.
    Loads model, assesses, then unloads to free VRAM.
    #>
    param(
        [string]$ImagePath,
        [string]$ModelName,
        [string]$AssessmentType  # "mechanical" or "aesthetic"
    )
    
    if (-not (Test-Path $ImagePath)) {
        return $null
    }
    
    try {
        # Convert image to base64
        $imageBytes = [System.IO.File]::ReadAllBytes($ImagePath)
        $imageBase64 = [Convert]::ToBase64String($imageBytes)
        
        # Create prompt based on assessment type
        if ($AssessmentType -eq "mechanical") {
            $prompt = "Analyze this image for technical quality issues. Check for: aliasing, compression artifacts, texture inconsistencies, sprite defects, shading errors, jagged edges, or pixel-level problems. Rate the technical quality from 0-20 where 20 is perfect. Respond with ONLY a number from 0-20."
        } else {
            $prompt = "Analyze this image for professional quality. Evaluate: composition, lighting, aesthetic coherence, professional polish, and overall visual appeal. Rate the aesthetic quality from 0-20 where 20 is excellent. Respond with ONLY a number from 0-20."
        }
        
        # Call Ollama API with image (model will auto-load on first use)
        $ollamaUrl = "http://localhost:11434/api/chat"
        $body = @{
            model = $ModelName
            messages = @(
                @{
                    role = "user"
                    content = $prompt
                    images = @($imageBase64)
                }
            )
            stream = $false
            keep_alive = "1m"  # Keep loaded briefly in case we need it again soon
        } | ConvertTo-Json -Depth 10 -Compress
        
        $response = Invoke-RestMethod -Uri $ollamaUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
        
        if ($response.message -and $response.message.content) {
            $scoreText = $response.message.content.Trim()
            # Extract numeric score
            if ($scoreText -match '(\d+(?:\.\d+)?)') {
                $score = [double]$matches[1]
                # Clamp to 0-20 range
                $score = [Math]::Max(0.0, [Math]::Min(20.0, $score))
                
                # Unload model after assessment to free VRAM
                Unload-OllamaModel -ModelName $ModelName
                
                return $score
            }
        }
        
        # Unload even if assessment failed
        Unload-OllamaModel -ModelName $ModelName
        return $null
    } catch {
        Write-QualityLog -Message "Vision assessment error ($AssessmentType): $_" -ImagePath $ImagePath
        # Try to unload on error
        Unload-OllamaModel -ModelName $ModelName
        return $null
    }
}

function Get-BestImageScore {
    <#
    .SYNOPSIS
    Multi-tier quality assessment: Sanity check → Mechanical QA → Aesthetic scoring → Professional judgment
    #>
    param(
        [string]$ImagePath,
        [string]$Depth = $script:QualityAssessmentDepth  # "fast", "mechanical", "full"
    )
    
    if (-not (Test-Path $ImagePath)) {
        Write-QualityLog -Message "Image not found" -ImagePath $ImagePath
        return 0.0
    }
    
    try {
        Add-Type -AssemblyName System.Drawing
        
        # Load and validate image
        $fileInfo = Get-Item $ImagePath
        $image = [System.Drawing.Image]::FromFile($ImagePath)
        $width = $image.Width
        $height = $image.Height
        $image.Dispose()
        
        # Phase 1: Sanity check (always runs)
        if ($fileInfo.Length -lt 10KB) {
            Write-QualityLog -Message "Image too small (likely corrupt): $($fileInfo.Length) bytes" -ImagePath $ImagePath
            return 5.0
        }
        
        if ($width -lt 128 -or $height -lt 128) {
            Write-QualityLog -Message "Resolution too low: ${width}x${height}" -ImagePath $ImagePath
            return 5.0
        }
        
        # Fast path: Return high score for valid images (no AI assessment)
        if ($Depth -eq "fast") {
            if ($width -ge 512 -and $height -ge 512) {
                Write-QualityLog -Message "Image passes sanity checks (fast mode): ${width}x${height}, $([math]::Round($fileInfo.Length/1MB, 2))MB" -ImagePath $ImagePath
                return 18.0
            } else {
                Write-QualityLog -Message "Unusual dimensions but acceptable: ${width}x${height}" -ImagePath $ImagePath
                return 15.0
            }
        }
        
        # Phase 2: Mechanical QA (Qwen3-VL-8B) - loads, uses, then unloads
        $mechanicalScore = $null
        if ($Depth -in @("mechanical", "full")) {
            Write-Host "    [QA] Running mechanical QA (Qwen3-VL-8B)..." -ForegroundColor Cyan
            Write-QualityLog -Message "Running mechanical QA with Qwen3-VL-8B..." -ImagePath $ImagePath
            $mechanicalScore = Invoke-VisionQualityAssessment -ImagePath $ImagePath -ModelName $script:VisionModels["mechanical"] -AssessmentType "mechanical"
            if ($null -ne $mechanicalScore) {
                Write-Host "    [QA] Mechanical score: $([math]::Round($mechanicalScore, 1))/20" -ForegroundColor Green
                Write-QualityLog -Message "Mechanical QA score: $([math]::Round($mechanicalScore, 1))/20" -ImagePath $ImagePath
            } else {
                Write-Host "    [QA] Mechanical assessment failed, using fallback" -ForegroundColor Yellow
            }
        }
        
        # Phase 3: Aesthetic scoring (LLaVA:13b) - only in full mode, loads, uses, then unloads
        $aestheticScore = $null
        if ($Depth -eq "full") {
            Write-Host "    [QA] Running aesthetic assessment (LLaVA:13b)..." -ForegroundColor Cyan
            Write-QualityLog -Message "Running aesthetic assessment with LLaVA:13b..." -ImagePath $ImagePath
            $aestheticScore = Invoke-VisionQualityAssessment -ImagePath $ImagePath -ModelName $script:VisionModels["aesthetic"] -AssessmentType "aesthetic"
            if ($null -ne $aestheticScore) {
                Write-Host "    [QA] Aesthetic score: $([math]::Round($aestheticScore, 1))/20" -ForegroundColor Green
                Write-QualityLog -Message "Aesthetic score: $([math]::Round($aestheticScore, 1))/20" -ImagePath $ImagePath
            } else {
                Write-Host "    [QA] Aesthetic assessment failed, using mechanical score only" -ForegroundColor Yellow
            }
        }
        
        # Calculate final score
        $finalScore = 18.0  # Default to passing score
        
        if ($null -ne $mechanicalScore) {
            # Use mechanical score if available
            $finalScore = $mechanicalScore
        }
        
        if ($null -ne $aestheticScore) {
            # In full mode, combine mechanical and aesthetic scores
            if ($null -ne $mechanicalScore) {
                # Weighted combination: 60% mechanical (technical correctness), 40% aesthetic (professional polish)
                $finalScore = ($mechanicalScore * 0.6 + $aestheticScore * 0.4)
                Write-Host "    [QA] Combined score: $([math]::Round($finalScore, 1))/20 (mechanical: $([math]::Round($mechanicalScore, 1)), aesthetic: $([math]::Round($aestheticScore, 1)))" -ForegroundColor Cyan
            } else {
                $finalScore = $aestheticScore
            }
        }
        
        Write-QualityLog -Message "Final quality score: $([math]::Round($finalScore, 1))/20 (depth: $Depth)" -ImagePath $ImagePath
        return $finalScore
        
    } catch {
        Write-QualityLog -Message "Error in quality assessment: $_" -ImagePath $ImagePath
        # Fallback to basic sanity check
        try {
            if ($width -ge 512 -and $height -ge 512) {
                return 18.0
            } else {
                return 15.0
            }
        } catch {
            return 5.0
        }
    }
}

# Count stages for progress display
$stageCount = 0
if ($textureTypes -contains "blender" -or $textureTypes -contains "all") { $stageCount++ }
if ($textureTypes -contains "projectile" -or $textureTypes -contains "all") { $stageCount++ }
if ($textureTypes -contains "design_draft" -or $textureTypes -contains "all") { $stageCount++ }
if ($textureTypes -contains "full_ship_artwork" -or $textureTypes -contains "all") { $stageCount++ }

$currentStage = 0

# Final server check before generation starts
Write-Host "Verifying SD3 server is ready..." -ForegroundColor Cyan
if (-not (Test-StableDiffusionConnection)) {
    Write-Host "  [ERROR] SD3 server is not available!" -ForegroundColor Red
    Write-Host "  Please ensure the SD3 server is running before generating textures." -ForegroundColor Yellow
    Write-Host "  You can start it manually or it should have started automatically." -ForegroundColor Gray
    exit 1
}
Write-Host "  [OK] SD3 server is ready" -ForegroundColor Green
Write-Host ""

# Generate Blender textures
if ($textureTypes -contains "blender" -or $textureTypes -contains "all") {
    $currentStage++
    Write-Host "[$currentStage/$stageCount] Generating Blender Model Textures..." -ForegroundColor Cyan
    Write-Host "  Target: Diffuse maps for Blender models" -ForegroundColor Gray
    Write-Host "  Resolution: 1024x1024" -ForegroundColor Gray
    Write-Host ""
    
    if ($shipData.ships) {
        foreach ($ship in $shipData.ships) {
            for ($v = 0; $v -lt $Variations; $v++) {
                $result = Generate-BlenderTexture -Ship $ship -Variation $v
                if ($result) {
                    $totalGenerated++
                } else {
                    $totalFailed++
                }
            }
        }
    }
    Write-Host ""
}

# Generate projectile textures
if ($textureTypes -contains "projectile" -or $textureTypes -contains "all") {
    $currentStage++
    Write-Host "[$currentStage/$stageCount] Generating Projectile Textures..." -ForegroundColor Cyan
    Write-Host "  Target: Energy bolts, plasma balls, bio-missiles" -ForegroundColor Gray
    Write-Host "  Resolution: 512x512" -ForegroundColor Gray
    Write-Host ""
    
    $projectileTypes = @("energy_bolt", "plasma_ball", "bio_missile")
    foreach ($projType in $projectileTypes) {
        for ($v = 0; $v -lt $Variations; $v++) {
            $result = Generate-ProjectileTexture -ProjectileType $projType -Variation $v
            if ($result) {
                $totalGenerated++
            } else {
                $totalFailed++
            }
        }
    }
    Write-Host ""
}

# Generate design drafts
if ($textureTypes -contains "design_draft" -or $textureTypes -contains "all") {
    $currentStage++
    Write-Host "[$currentStage/$stageCount] Generating Design Drafts..." -ForegroundColor Cyan
    Write-Host "  Target: Concept art and design references" -ForegroundColor Gray
    Write-Host "  Resolution: 1024x1024" -ForegroundColor Gray
    Write-Host ""
    
    if ($shipData.ships) {
        foreach ($ship in $shipData.ships) {
            for ($v = 0; $v -lt $Variations; $v++) {
                $result = Generate-DesignDraft -Ship $ship -Variation $v
                if ($result) {
                    $totalGenerated++
                } else {
                    $totalFailed++
                }
            }
        }
    }
    Write-Host ""
}

# Generate full ship artwork
if ($textureTypes -contains "full_ship_artwork" -or $textureTypes -contains "all") {
    $currentStage++
    Write-Host "[$currentStage/$stageCount] Generating Full Ship Artwork..." -ForegroundColor Cyan
    Write-Host "  Target: Complete ship renders showing full design" -ForegroundColor Gray
    Write-Host "  Resolution: 2048x2048" -ForegroundColor Gray
    Write-Host "  Views: Side, Front, Three-quarter, Top, Dramatic" -ForegroundColor Gray
    Write-Host ""
    
    if ($shipData.ships) {
        $views = @("side", "front", "three_quarter", "dramatic")
        foreach ($ship in $shipData.ships) {
            # Generate multiple views per ship
            foreach ($view in $views) {
                for ($v = 0; $v -lt $Variations; $v++) {
                    $result = Generate-FullShipArtwork -Ship $ship -Variation $v -View $view
                    if ($result) {
                        $totalGenerated++
                    } else {
                        $totalFailed++
                    }
                }
            }
        }
    }
    Write-Host ""
}

# Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Generation Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Total generated: $totalGenerated" -ForegroundColor Green
if ($totalFailed -gt 0) {
    Write-Host "Total failed: $totalFailed" -ForegroundColor Yellow
}
Write-Host "Output directory: $OutputDir" -ForegroundColor Gray
Write-Host ""

# Save best images summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Best Images Saved for Reference" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$bestCount = 0
foreach ($category in $bestImages.Keys) {
    if ($bestImages[$category].Count -gt 0) {
        $categoryBestDir = Join-Path $bestDir $category
        Write-Host "  $category`: $($bestImages[$category].Count) best image(s)" -ForegroundColor Yellow
        Write-Host "    Location: $categoryBestDir" -ForegroundColor Gray
        $bestCount += $bestImages[$category].Count
    }
}

if ($bestCount -gt 0) {
    Write-Host "  Total best images: $bestCount" -ForegroundColor Green
    Write-Host "  Best images directory: $bestDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  These best images will be used as reference for future generation." -ForegroundColor Cyan
} else {
    Write-Host "  No best images saved (all generation failed)" -ForegroundColor Yellow
}

Write-Host ""
