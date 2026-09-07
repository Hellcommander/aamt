#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate particle effects for Starbound/OpenStarbound.
    
.DESCRIPTION
    Creates Starbound-compatible .particle and .particlesource files with support for:
    - Ember particles (simple colored points)
    - Textured particles (using image files)
    - Animated particles (using animation files)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Setup logging directory and function (must be defined before use)
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "StarboundParticle_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
}
    - Particle sources (spawn groups of particles)
    
    Supports AI-assisted generation via Ollama for creative particle designs.

.PARAMETER ParticleName
    Name/kind of the particle (used in file name and particle definition)
    
.PARAMETER ParticleType
    Type of particle: Ember, Textured, Animated, Source
    
.PARAMETER Description
    Description for AI-assisted generation (optional)
    
.PARAMETER Color
    RGBA color array for ember/textured particles [R, G, B, A]
    
.PARAMETER Size
    Base size of the particle (default: 1.0)
    
.PARAMETER TimeToLive
    Particle lifetime in seconds (default: 1.0)
    
.PARAMETER InitialVelocity
    Initial velocity [X, Y] (default: [0, 0])
    
.PARAMETER FinalVelocity
    Final velocity [X, Y] (default: [0, 0])
    
.PARAMETER Layer
    Render layer: front, middle, back (default: middle)
    
.PARAMETER OutputDir
    Output directory for generated files

.PARAMETER Preset
    Use a preset: Fire, Ice, Poison, Electric, Blood, Sparkle, Smoke, Bubble

.EXAMPLE
    .\StarboundParticleGenerator.ps1 -ParticleName "myfire" -Preset Fire
    
.EXAMPLE
    .\StarboundParticleGenerator.ps1 -ParticleName "customspark" -ParticleType Ember -Color @(255, 200, 50, 255)
    
.EXAMPLE
    .\StarboundParticleGenerator.ps1 -ParticleName "magiceffect" -Description "Purple magical sparkles with swirl"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ParticleName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Ember", "Textured", "Animated", "Source")]
    [string]$ParticleType = "Ember",
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Defaults to OllamaModel if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseOllama,
    
    [Parameter(Mandatory=$false)]
    [int[]]$Color = @(255, 255, 255, 255),
    
    [Parameter(Mandatory=$false)]
    [float]$Size = 1.0,
    
    [Parameter(Mandatory=$false)]
    [float]$TimeToLive = 1.0,
    
    [Parameter(Mandatory=$false)]
    [float]$Fade = 0.9,
    
    [Parameter(Mandatory=$false)]
    [float[]]$InitialVelocity = @(0, 0),
    
    [Parameter(Mandatory=$false)]
    [float[]]$FinalVelocity = @(0, 0),
    
    [Parameter(Mandatory=$false)]
    [float[]]$Approach = @(20, 20),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("front", "middle", "back")]
    [string]$Layer = "middle",
    
    [Parameter(Mandatory=$false)]
    [string]$ImagePath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AnimationPath = "",
    
    [Parameter(Mandatory=$false)]
    [float]$Rotation = 0,
    
    [Parameter(Mandatory=$false)]
    [float]$AngularVelocity = 0,
    
    [Parameter(Mandatory=$false)]
    [int[]]$Light = @(),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("shrink", "fade", "none")]
    [string]$DestructionAction = "none",
    
    [Parameter(Mandatory=$false)]
    [float]$DestructionTime = 0,
    
    [Parameter(Mandatory=$false)]
    [switch]$CollidesLiquid,
    
    [Parameter(Mandatory=$false)]
    [switch]$UnderwaterOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$Looping,
    
    [Parameter(Mandatory=$false)]
    [hashtable]$Variance = @{},
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Fire", "Ice", "Poison", "Electric", "Blood", "Sparkle", "Smoke", "Bubble", "None")]
    [string]$Preset = "None",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "StarboundParticles",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$StarboundAssetsPath = "F:\Games\OpenStarbound\source\basegameunpackedAssets"
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Setup logging (must be done before Write-Log is called)
$logDir = Join-Path $PSScriptRoot "Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "StarboundParticle_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Define Write-Log function before it's used
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "Cyan" }
    }
    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
}

# Import shared Ollama integration module if available
$toolsRoot = Split-Path -Parent $PSScriptRoot
$sharedModulePath = Join-Path $toolsRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force -ErrorAction SilentlyContinue
    Write-Log "Using shared Ollama integration module" "INFO"
    
    # Initialize model selection if not already done
    if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
        if (-not (Test-OllamaConnection)) {
            Write-Log "Initializing Ollama connection..." "INFO"
            Initialize-OllamaModels
        }
    }
}

Write-Log "═══════════════════════════════════════════════════════════"
Write-Log "  Starbound Particle Generator"
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log ""
Write-Log "Particle Name: $ParticleName"
Write-Log "Particle Type: $ParticleType"
Write-Log "Preset: $Preset"
Write-Log "Output Directory: $OutputDir"
Write-Log ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Preset definitions
$presets = @{
    "Fire" = @{
        ParticleType = "Ember"
        Color = @(255, 120, 20, 255)
        Size = 1.2
        Fade = 0.85
        TimeToLive = 0.5
        InitialVelocity = @(0, 3)
        FinalVelocity = @(0, 8)
        Approach = @(10, 30)
        Layer = "middle"
        Light = @(200, 100, 20)
        Variance = @{
            initialVelocity = @(2, 2)
            size = 0.4
            color = @(255, 80, 0, 255)
        }
    }
    "Ice" = @{
        ParticleType = "Ember"
        Color = @(150, 220, 255, 255)
        Size = 0.8
        Fade = 0.9
        TimeToLive = 0.8
        InitialVelocity = @(0, -1)
        FinalVelocity = @(0, -3)
        Approach = @(15, 20)
        Layer = "front"
        Light = @(100, 150, 200)
        Variance = @{
            initialVelocity = @(1.5, 1)
            size = 0.3
        }
    }
    "Poison" = @{
        ParticleType = "Ember"
        Color = @(100, 220, 50, 255)
        Size = 1.0
        Fade = 0.85
        TimeToLive = 0.6
        InitialVelocity = @(0, 2)
        FinalVelocity = @(0, 4)
        Approach = @(20, 25)
        Layer = "middle"
        Variance = @{
            initialVelocity = @(2, 1.5)
            size = 0.3
            color = @(80, 180, 30, 255)
        }
    }
    "Electric" = @{
        ParticleType = "Ember"
        Color = @(180, 200, 255, 255)
        Size = 0.6
        Fade = 0.95
        TimeToLive = 0.2
        InitialVelocity = @(5, 5)
        FinalVelocity = @(10, 10)
        Approach = @(50, 50)
        Layer = "front"
        Light = @(150, 180, 255)
        Variance = @{
            initialVelocity = @(10, 10)
            size = 0.3
            color = @(255, 255, 255, 255)
        }
    }
    "Blood" = @{
        ParticleType = "Ember"
        Color = @(180, 0, 0, 255)
        Size = 1.2
        Fade = 0.9
        TimeToLive = 0.8
        InitialVelocity = @(8, 5)
        FinalVelocity = @(10, -15)
        Approach = @(20, 30)
        Layer = "front"
        Variance = @{
            initialVelocity = @(10, 3)
            timeToLive = 0.5
            size = 0.8
        }
    }
    "Sparkle" = @{
        ParticleType = "Ember"
        Color = @(255, 255, 200, 255)
        Size = 0.5
        Fade = 0.8
        TimeToLive = 0.4
        InitialVelocity = @(0, 2)
        FinalVelocity = @(0, 0)
        Approach = @(10, 10)
        Layer = "front"
        Light = @(255, 255, 150)
        Variance = @{
            initialVelocity = @(3, 3)
            size = 0.3
            color = @(255, 200, 100, 255)
        }
    }
    "Smoke" = @{
        ParticleType = "Animated"
        AnimationPath = "/animations/smoke/smoke.animation"  # Uses built-in Starbound animation
        Size = 0.5
        Fade = 0.9
        TimeToLive = 0.8
        InitialVelocity = @(0, -0.5)
        FinalVelocity = @(0, -0.5)
        Approach = @(0, 20)
        Layer = "back"
        DestructionAction = "shrink"
        DestructionTime = 1.0
        Variance = @{
            initialVelocity = @(0, 0.5)
            finalVelocity = @(0, -0.5)
        }
        # For custom animations, use StarboundAnimationGenerator.ps1
        # AnimationPath = "/animations/mysmoke/mysmoke.animation"
    }
    "Bubble" = @{
        ParticleType = "Textured"
        ImagePath = "/projectiles/npcs/bubble/bubbles.png:0"
        Size = 0.5
        Fade = 0.9
        TimeToLive = 3.0
        InitialVelocity = @(0, 1)
        FinalVelocity = @(0, 3)
        Layer = "front"
        UnderwaterOnly = $true
        Variance = @{
            size = 0.3
            initialVelocity = @(0.5, 0.5)
        }
    }
}

# AI-assisted generation with Ollama
if ($UseAI) {
    Write-Log "Using Ollama AI for particle generation..." "INFO"
    
    # Use shared module if available, otherwise fallback
    if (-not (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue)) {
        function Invoke-OllamaRequest {
            param([string]$Model, [string]$Prompt, [string]$BaseUrl)
            $body = @{ model = $Model; prompt = $Prompt; stream = $false } | ConvertTo-Json
            try {
                $response = Invoke-RestMethod -Uri "$BaseUrl/api/generate" -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop
                return $response.response.Trim()
            } catch {
                Write-Log "Error calling Ollama: $_" "ERROR"
                return $null
            }
        }
    }
    
    # Generate description if not provided
    if ([string]::IsNullOrWhiteSpace($Description)) {
        $aiPrompt = "Generate a creative description for a Starbound particle effect named '$ParticleName'. Include: colors, movement pattern, size, speed, and visual style. Return only a 2-3 sentence description."
        
        if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
            $Description = Invoke-OllamaRequest -Prompt $aiPrompt -TaskType "visual" -ResponseLength "short" -ModelName $OllamaModel
        } else {
            $Description = Invoke-OllamaRequest -Model $OllamaModel -Prompt $aiPrompt -BaseUrl $OllamaUrl
        }
        
        if ($Description) {
            Write-Log "AI-generated description: $Description" "SUCCESS"
        }
    }
    
    # Generate parameters from description
    if ($Description) {
        $paramPrompt = "Based on this particle description: '$Description'
        Extract parameters as JSON:
        {
          'Color': [R, G, B, A],
          'Size': number (0.5-2.0),
          'TimeToLive': number (0.1-2.0),
          'InitialVelocity': [X, Y],
          'FinalVelocity': [X, Y],
          'Fade': number (0.7-1.0)
        }
        Return ONLY the JSON, no other text."
        
        if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
            $paramResponse = Invoke-OllamaRequest -Prompt $paramPrompt -TaskType "analysis" -ResponseLength "short" -ModelName $OllamaModel
        } else {
            $paramResponse = Invoke-OllamaRequest -Model $OllamaModel -Prompt $paramPrompt -BaseUrl $OllamaUrl
        }
        if ($paramResponse) {
            $jsonMatch = $paramResponse | Select-String -Pattern '\{[\s\S]*\}' | Select-Object -First 1
            if ($jsonMatch) {
                try {
                    $aiParams = $jsonMatch.Matches[0].Value | ConvertFrom-Json
                    if ($aiParams.Color) { $Color = $aiParams.Color }
                    if ($aiParams.Size) { $Size = $aiParams.Size }
                    if ($aiParams.TimeToLive) { $TimeToLive = $aiParams.TimeToLive }
                    if ($aiParams.InitialVelocity) { $InitialVelocity = $aiParams.InitialVelocity }
                    if ($aiParams.FinalVelocity) { $FinalVelocity = $aiParams.FinalVelocity }
                    if ($aiParams.Fade) { $Fade = $aiParams.Fade }
                    Write-Log "AI-generated parameters applied" "SUCCESS"
                } catch {
                    Write-Log "Could not parse AI parameters, using defaults" "WARN"
                }
            }
        }
    }
}

# Apply preset if specified
if ($Preset -ne "None" -and $presets.ContainsKey($Preset)) {
    Write-Log "Applying preset: $Preset" "INFO"
    $presetData = $presets[$Preset]
    
    # Apply preset values (only if not explicitly provided)
    if ($PSBoundParameters.ContainsKey('ParticleType') -eq $false) { $ParticleType = $presetData.ParticleType }
    if ($PSBoundParameters.ContainsKey('Color') -eq $false -and $presetData.Color) { $Color = $presetData.Color }
    if ($PSBoundParameters.ContainsKey('Size') -eq $false) { $Size = $presetData.Size }
    if ($PSBoundParameters.ContainsKey('Fade') -eq $false) { $Fade = $presetData.Fade }
    if ($PSBoundParameters.ContainsKey('TimeToLive') -eq $false) { $TimeToLive = $presetData.TimeToLive }
    if ($PSBoundParameters.ContainsKey('InitialVelocity') -eq $false) { $InitialVelocity = $presetData.InitialVelocity }
    if ($PSBoundParameters.ContainsKey('FinalVelocity') -eq $false) { $FinalVelocity = $presetData.FinalVelocity }
    if ($PSBoundParameters.ContainsKey('Approach') -eq $false -and $presetData.Approach) { $Approach = $presetData.Approach }
    if ($PSBoundParameters.ContainsKey('Layer') -eq $false) { $Layer = $presetData.Layer }
    if ($PSBoundParameters.ContainsKey('Light') -eq $false -and $presetData.Light) { $Light = $presetData.Light }
    if ($PSBoundParameters.ContainsKey('AnimationPath') -eq $false -and $presetData.AnimationPath) { $AnimationPath = $presetData.AnimationPath }
    if ($PSBoundParameters.ContainsKey('ImagePath') -eq $false -and $presetData.ImagePath) { $ImagePath = $presetData.ImagePath }
    if ($PSBoundParameters.ContainsKey('DestructionAction') -eq $false -and $presetData.DestructionAction) { $DestructionAction = $presetData.DestructionAction }
    if ($PSBoundParameters.ContainsKey('DestructionTime') -eq $false -and $presetData.DestructionTime) { $DestructionTime = $presetData.DestructionTime }
    if ($PSBoundParameters.ContainsKey('UnderwaterOnly') -eq $false -and $presetData.UnderwaterOnly) { $UnderwaterOnly = $presetData.UnderwaterOnly }
    if ($PSBoundParameters.ContainsKey('Variance') -eq $false -and $presetData.Variance) { $Variance = $presetData.Variance }
}

# Build particle definition based on type
function Build-ParticleDefinition {
    param(
        [string]$Type,
        [hashtable]$Props
    )
    
    $def = [ordered]@{
        type = $Type.ToLower()
    }
    
    switch ($Type) {
        "Ember" {
            $def["size"] = $Props.Size
            $def["color"] = $Props.Color
            $def["fade"] = $Props.Fade
            $def["initialVelocity"] = $Props.InitialVelocity
            $def["finalVelocity"] = $Props.FinalVelocity
            $def["approach"] = $Props.Approach
            $def["timeToLive"] = $Props.TimeToLive
            $def["layer"] = $Props.Layer
        }
        "Textured" {
            $def["image"] = $Props.ImagePath
            $def["size"] = $Props.Size
            if ($Props.Color) { $def["color"] = $Props.Color }
            $def["fade"] = $Props.Fade
            $def["initialVelocity"] = $Props.InitialVelocity
            $def["finalVelocity"] = $Props.FinalVelocity
            if ($Props.Approach) { $def["approach"] = $Props.Approach }
            $def["timeToLive"] = $Props.TimeToLive
            $def["layer"] = $Props.Layer
            if ($Props.Rotation -ne 0) { $def["rotation"] = $Props.Rotation }
            if ($Props.AngularVelocity -ne 0) { $def["angularVelocity"] = $Props.AngularVelocity }
        }
        "Animated" {
            $def["animation"] = $Props.AnimationPath
            $def["position"] = @(0, 0)
            $def["size"] = $Props.Size
            $def["fade"] = $Props.Fade
            $def["initialVelocity"] = $Props.InitialVelocity
            $def["finalVelocity"] = $Props.FinalVelocity
            $def["approach"] = $Props.Approach
            $def["timeToLive"] = $Props.TimeToLive
            $def["layer"] = $Props.Layer
            if ($Props.Looping) { $def["looping"] = $true }
        }
    }
    
    # Common optional properties
    if ($Props.Light -and $Props.Light.Count -eq 3) {
        $def["light"] = $Props.Light
    }
    
    if ($Props.DestructionAction -ne "none") {
        $def["destructionAction"] = $Props.DestructionAction
        if ($Props.DestructionTime -gt 0) {
            $def["destructionTime"] = $Props.DestructionTime
        }
    }
    
    if ($Props.CollidesLiquid) {
        $def["collidesLiquid"] = $true
    }
    
    if ($Props.UnderwaterOnly) {
        $def["underwaterOnly"] = $true
    }
    
    # Add variance
    if ($Props.Variance -and $Props.Variance.Count -gt 0) {
        $def["variance"] = $Props.Variance
    }
    
    return $def
}

# Build the particle file
$props = @{
    Size = $Size
    Color = $Color
    Fade = $Fade
    InitialVelocity = $InitialVelocity
    FinalVelocity = $FinalVelocity
    Approach = $Approach
    TimeToLive = $TimeToLive
    Layer = $Layer
    Light = $Light
    ImagePath = $ImagePath
    AnimationPath = $AnimationPath
    Rotation = $Rotation
    AngularVelocity = $AngularVelocity
    DestructionAction = $DestructionAction
    DestructionTime = $DestructionTime
    CollidesLiquid = $CollidesLiquid
    UnderwaterOnly = $UnderwaterOnly
    Looping = $Looping
    Variance = $Variance
}

Write-Log "Building $ParticleType particle..." "INFO"

$particleDefinition = Build-ParticleDefinition -Type $ParticleType -Props $props

$particleFile = [ordered]@{
    kind = $ParticleName
    definition = $particleDefinition
}

# Convert to JSON with Starbound's formatting style
$jsonContent = $particleFile | ConvertTo-Json -Depth 10

# Starbound uses spaces around colons, let's format it nicely
$jsonContent = $jsonContent -replace '(?<="):\s*', ' : '

# Output file
# Validate $OutputDir before Join-Path
$outputPath = Join-Path $OutputDir "$ParticleName.particle"
if ([string]::IsNullOrWhiteSpace($outputPath)) {
    Write-Host "  [FAIL] outputPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}

# Create directory structure if ParticleName contains subdirectories (e.g., "coilSerpent/enter")
$outputDirPath = Split-Path -Parent $outputPath
if (-not [string]::IsNullOrWhiteSpace($outputDirPath) -and $outputDirPath -ne $OutputDir) {
    if (-not (Test-Path $outputDirPath)) {
        New-Item -ItemType Directory -Path $outputDirPath -Force | Out-Null
        Write-Log "Created directory: $outputDirPath" "INFO"
    }
}

$jsonContent | Out-File -FilePath $outputPath -Encoding UTF8 -NoNewline

Write-Log "Created: $outputPath" "SUCCESS"

# Create a particle source if requested or if it makes sense
if ($ParticleType -eq "Source") {
    Write-Log "Creating particle source..." "INFO"
    
    $sourceFile = [ordered]@{
        kind = "${ParticleName}_source"
        definition = [ordered]@{
            duration = 0.2
            loops = $true
            particles = @(
                @($ParticleName)
            )
        }
    }
    
    $sourceJson = $sourceFile | ConvertTo-Json -Depth 10
    $sourceJson = $sourceJson -replace '(?<="):\s*', ' : '
    
    # Validate $OutputDir before Join-Path
    $sourcePath = Join-Path $OutputDir "$ParticleName.particlesource"
 if ([string]::IsNullOrWhiteSpace($sourcePath)) {
        Write-Host "  [FAIL] sourcePath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($sourcePath)) {
        Write-Host "  [FAIL] sourcePath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
    $sourceJson | Out-File -FilePath $sourcePath -Encoding UTF8 -NoNewline
    
    Write-Log "Created: $sourcePath" "SUCCESS"
}

# Create variant particles (useful for effects)
if ($Preset -ne "None") {
    Write-Log "Creating variant particles..." "INFO"
    
    # Create a "2" variant with slightly different properties
    $variant2Props = $props.Clone()
    $variant2Props.Size = $Size * 0.8
    $variant2Props.TimeToLive = $TimeToLive * 0.8
    
    $variant2Def = Build-ParticleDefinition -Type $ParticleType -Props $variant2Props
    $variant2File = [ordered]@{
        kind = "${ParticleName}2"
        definition = $variant2Def
    }
    
    $variant2Json = $variant2File | ConvertTo-Json -Depth 10
    $variant2Json = $variant2Json -replace '(?<="):\s*', ' : '
    
    # Validate $OutputDir before Join-Path
    $variant2Path = Join-Path $OutputDir "${ParticleName}2.particle"
 if ([string]::IsNullOrWhiteSpace($variant2Path)) {
        Write-Host "  [FAIL] variant2Path is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($variant2Path)) {
        Write-Host "  [FAIL] variant2Path is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
    $variant2Json | Out-File -FilePath $variant2Path -Encoding UTF8 -NoNewline
    
    Write-Log "Created variant: $variant2Path" "SUCCESS"
    
    # Create a "dust" variant
    $dustProps = $props.Clone()
    $dustProps.Size = $Size * 0.5
    $dustProps.Fade = 0.95
    $dustProps.TimeToLive = $TimeToLive * 1.5
    
    $dustDef = Build-ParticleDefinition -Type $ParticleType -Props $dustProps
    $dustFile = [ordered]@{
        kind = "${ParticleName}dust"
        definition = $dustDef
    }
    
    $dustJson = $dustFile | ConvertTo-Json -Depth 10
    $dustJson = $dustJson -replace '(?<="):\s*', ' : '
    
    # Validate $OutputDir before Join-Path
    $dustPath = Join-Path $OutputDir "${ParticleName}dust.particle"
 if ([string]::IsNullOrWhiteSpace($dustPath)) {
        Write-Host "  [FAIL] dustPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($dustPath)) {
        Write-Host "  [FAIL] dustPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
    $dustJson | Out-File -FilePath $dustPath -Encoding UTF8 -NoNewline
    
    Write-Log "Created variant: $dustPath" "SUCCESS"
}

# Generate metadata
$metadata = @{
    ParticleName = $ParticleName
    ParticleType = $ParticleType
    Preset = $Preset
    GeneratedAt = (Get-Date).ToString("o")
    OutputDirectory = $OutputDir
    Files = @(Get-ChildItem -Path $OutputDir -Filter "*.particle" | Select-Object -ExpandProperty Name)
    StarboundFormat = "1.4+"
    Description = $Description
}

# Validate $OutputDir before Join-Path
$metadataPath = Join-Path $OutputDir "particle_metadata.json"
 if ([string]::IsNullOrWhiteSpace($metadataPath)) {
    Write-Host "  [FAIL] metadataPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($metadataPath)) {
    Write-Host "  [FAIL] metadataPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
    continue
}
$metadata | ConvertTo-Json -Depth 5 | Out-File -FilePath $metadataPath -Encoding UTF8

Write-Log ""
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log "  Generation Complete!" "SUCCESS"
Write-Log "═══════════════════════════════════════════════════════════"
Write-Log ""
Write-Log "Generated files:" "INFO"

Get-ChildItem -Path $OutputDir -Filter "*.particle*" | ForEach-Object {
    Write-Log "  - $($_.Name)" "SUCCESS"
}

Write-Log ""
Write-Log "To use in Starbound/OpenStarbound:" "INFO"
Write-Log "  1. Copy the .particle files to your mod's particles/ folder" "INFO"
Write-Log "  2. Reference them by kind name: `"$ParticleName`"" "INFO"
Write-Log ""
Write-Log "Example Lua usage:" "INFO"
Write-Log "  world.spawnProjectile(`"$ParticleName`", position, ...)" "INFO"
Write-Log ""

# Return the generated particle data for piping
return @{
    Success = $true
    ParticleName = $ParticleName
    ParticleType = $ParticleType
    OutputPath = $outputPath
    Files = (Get-ChildItem -Path $OutputDir -Filter "*.particle*" | Select-Object -ExpandProperty FullName)
}

