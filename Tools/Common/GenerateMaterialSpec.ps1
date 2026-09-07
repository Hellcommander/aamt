#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quality-aware AI prompt template for generating procedural material specifications from registry entries.
    
.DESCRIPTION
    Uses Ollama to generate structured JSON material specifications based on registry entries.
    The output is deterministic, registry-driven, quality-tiered, style-aware, and shape-aware.
    
.PARAMETER RegistryPath

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    Path to the asset registry JSON file.
    
.PARAMETER AssetId
    Asset ID from the registry to generate material spec for.
    
.PARAMETER Model
    Ollama model to use (default: auto-detected).
    
.PARAMETER OutputPath
    Output path for the generated material specification JSON.
    
.PARAMETER VisualJson
    Direct visual block JSON (alternative to registry).
    
.PARAMETER GenerationJson
    Direct generation block JSON (alternative to registry).
    
.EXAMPLE
    .\GenerateMaterialSpec.ps1 -RegistryPath "asset_registry.json" -AssetId "nature_verdant_pulse"
    
.EXAMPLE
    .\GenerateMaterialSpec.ps1 -VisualJson '{"icon":{"shape":"spiral","palette":["#4caf50"]}}' -GenerationJson '{"quality":"high"}'
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualJson = "",
    
    [Parameter(Mandatory=$false)]
    [string]$GenerationJson = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ExportJson = ""
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import Ollama functions from AssetMakerAI
$assetMakerPath = Join-Path $PSScriptRoot "..\Transcendence\AssetMakerAI.ps1"
if (Test-Path $assetMakerPath) {
    # Dot-source to get functions (but don't execute main script)
    $scriptContent = Get-Content $assetMakerPath -Raw
    # Extract just the function definitions (simple approach: execute in a scope)
    try {
        . $assetMakerPath -ErrorAction SilentlyContinue
    }
    catch {
        # If dot-sourcing fails, define functions inline
        Write-Host "Warning: Could not import from AssetMakerAI.ps1, using inline functions" -ForegroundColor Yellow
    }
}

# Fallback: Define Ollama functions if not imported
if (-not (Get-Command "Invoke-OllamaChat" -ErrorAction SilentlyContinue)) {
    function Test-OllamaRunning {
        try {
            $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
            return $true
        }
        catch {
            return $false
        }
    }
    
    function Get-RecommendedModel {
        try {
            $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 5
            $models = $response.models | ForEach-Object { $_.name }
            if ($models.Count -gt 0) {
                $preferred = @("llama3.2", "llama3.1", "llama3", "mistral", "phi3")
                foreach ($pref in $preferred) {
                    $match = $models | Where-Object { $_ -like "$pref*" }
                    if ($match) {
                        return $match[0]
                    }
                }
                return $models[0]
            }
        }
        catch { }
        return $script:DefaultModel
    }
    
    function Invoke-OllamaChat {
        param(
            [string]$Prompt,
            [string]$ModelName,
            [hashtable]$SystemPrompt = @{}
        )
        
        if (-not (Test-OllamaRunning)) {
            Write-Host "Error: Ollama service is not running" -ForegroundColor Red
            return $null
        }
        
        $systemMessage = if ($SystemPrompt.Count -gt 0) {
            $SystemPrompt.Values | Select-Object -First 1
        } else {
            "You are a helpful assistant."
        }
        
        $requestBody = @{
            model = $ModelName
            messages = @(
                @{
                    role = "system"
                    content = $systemMessage
                },
                @{
                    role = "user"
                    content = $Prompt
                }
            )
            stream = $false
        } | ConvertTo-Json -Depth 10
        
        try {
            $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
            
            if ($response.message -and $response.message.content) {
                return $response.message.content.Trim()
            }
            
            return $null
        }
        catch {
            Write-Host "Error calling Ollama: $_" -ForegroundColor Red
            return $null
        }
    }
}

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

$script:OllamaUrl = "http://localhost:11434"
$script:OllamaApiUrl = "$script:OllamaUrl/api"
$script:DefaultModel = "llama3.2"

# ------------------------------------------------------------
# Quality-Aware Prompt Template
# ------------------------------------------------------------

function Get-QualityAwarePrompt {
    <#
    .SYNOPSIS
      Generates the quality-aware AI prompt template
    #>
    param(
        [string]$VisualBlock,
        [string]$GenerationBlock,
        [string]$ExportBlock
    )
    
    $prompt = @"
You are an expert procedural texture and icon designer for game assets.

Your task is to generate a procedural material specification for Blender based on the following registry entry:

[VISUAL_BLOCK]
$VisualBlock

[GENERATION_BLOCK]
$GenerationBlock

[EXPORT_BLOCK]
$ExportBlock

Your output MUST be valid JSON with no commentary.

============================================================
REQUIREMENTS
============================================================

1. Interpret the visual.icon block:
   - shape: describe the silhouette and internal pattern
   - palette: convert hex colors into descriptive color usage
   - style: painterly, pixel, flat, or procedural
   - contrast: low, medium, high
   - lighting: rim light, soft light, directional, etc.
   - size: icon resolution (16–64)

2. Interpret the visual.fx block (if present):
   - frames: number of animation frames
   - motion: how the FX evolves over time
   - glow: whether emission should be used
   - size: FX resolution

3. Interpret the visual.projectile block (if present):
   - shape: projectile silhouette
   - frames: animation frames
   - size: resolution

4. Interpret the generation.quality field:
   - "draft": minimal detail, fast bake, simple noise
   - "standard": moderate detail, 1–2 noise layers
   - "high": multiple layers, detail noise, rim lighting
   - "ultra": micro‑detail, curvature hints, multi‑pass complexity

5. Produce a JSON object with the following structure:

{
  "material": {
    "style": "...",
    "shape": "...",
    "palette": [
      { "hex": "#xxxxxx", "usage": "..." }
    ],
    "contrast": "...",
    "lighting": "...",
    "quality": "...",
    "proceduralLayers": [
      {
        "type": "noise | voronoi | gradient | mix | emission",
        "scale": number,
        "detail": number,
        "factor": number,
        "purpose": "base | detail | highlight | glow"
      }
    ]
  },

  "animation": {
    "frames": number,
    "motion": "...",
    "glow": boolean
  },

  "textures": {
    "baseColor": true/false,
    "normal": true/false,
    "roughness": true/false,
    "emission": true/false
  }
}

============================================================
QUALITY RULES
============================================================

If quality = "draft":
- Use 1–2 procedural layers
- Low detail values
- No rim lighting
- No micro‑detail

If quality = "standard":
- Use 2–3 layers
- Moderate detail
- Simple color ramp

If quality = "high":
- Use 3–5 layers
- Add detail noise
- Add rim lighting if lighting suggests it
- Add subtle emission for magical effects

If quality = "ultra":
- Use 5–8 layers
- Add micro‑detail noise
- Add curvature‑like variation (simulated via layered noise)
- Add strong rim lighting if appropriate
- Add emission shaping for magical effects

============================================================
OUTPUT RULES
============================================================

- Output ONLY JSON.
- No explanations.
- No prose.
- No comments.
- No code blocks.
- No Blender code.
- The JSON must be ready for Blender to interpret.
"@

    return $prompt
}

# ------------------------------------------------------------
# Main Function
# ------------------------------------------------------------

function Generate-MaterialSpec {
    <#
    .SYNOPSIS
      Generates a material specification from a registry entry using AI
    #>
    param(
        [string]$RegistryPath,
        [string]$AssetId,
        [string]$VisualJson,
        [string]$GenerationJson,
        [string]$ExportJson,
        [string]$ModelName
    )
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Quality-Aware Material Specification Generator" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Load from registry if provided
    if (-not [string]::IsNullOrWhiteSpace($RegistryPath) -and -not [string]::IsNullOrWhiteSpace($AssetId)) {
        if (-not (Test-Path $RegistryPath)) {
            Write-Host "Error: Registry file not found: $RegistryPath" -ForegroundColor Red
            return $null
        }
        
        Write-Host "Loading registry entry..." -ForegroundColor Cyan
        try {
            $registry = Get-Content $RegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $entry = $registry.entries | Where-Object { $_.id -eq $AssetId } | Select-Object -First 1
            
            if (-not $entry) {
                Write-Host "Error: Asset ID '$AssetId' not found in registry" -ForegroundColor Red
                return $null
            }
            
            Write-Host "  Found: $($entry.name) ($AssetId)" -ForegroundColor Green
            
            $VisualJson = ($entry.visual | ConvertTo-Json -Compress -Depth 10)
            $GenerationJson = ($entry.generation | ConvertTo-Json -Compress -Depth 10)
            $ExportJson = ($entry.export | ConvertTo-Json -Compress -Depth 10)
        }
        catch {
            Write-Host "Error loading registry: $_" -ForegroundColor Red
            return $null
        }
    }
    
    # Validate we have at least visual block
    if ([string]::IsNullOrWhiteSpace($VisualJson)) {
        Write-Host "Error: Visual block is required" -ForegroundColor Red
        return $null
    }
    
    # Parse JSON blocks to ensure they're valid
    try {
        $visualObj = $VisualJson | ConvertFrom-Json
        Write-Host "  Visual block: Valid" -ForegroundColor Gray
    }
    catch {
        Write-Host "Error: Invalid VisualJson: $_" -ForegroundColor Red
        return $null
    }
    
    if (-not [string]::IsNullOrWhiteSpace($GenerationJson)) {
        try {
            $genObj = $GenerationJson | ConvertFrom-Json
            Write-Host "  Generation block: Valid" -ForegroundColor Gray
        }
        catch {
            Write-Host "Warning: Invalid GenerationJson, using defaults" -ForegroundColor Yellow
            $GenerationJson = '{"quality":"standard"}'
        }
    } else {
        $GenerationJson = '{"quality":"standard"}'
    }
    
    if ([string]::IsNullOrWhiteSpace($ExportJson)) {
        $ExportJson = '{"elin":true,"terraria":true,"starbound":true}'
    }
    
    Write-Host ""
    
    # Check Ollama
    if (-not (Test-OllamaRunning)) {
        Write-Host "Error: Ollama service is not running" -ForegroundColor Red
        Write-Host "  Start Ollama service or run: ollama serve" -ForegroundColor Yellow
        return $null
    }
    
    # Get model
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = Get-RecommendedModel
        if ([string]::IsNullOrWhiteSpace($ModelName)) {
            $ModelName = $script:DefaultModel
        }
    }
    
    Write-Host "Using model: $ModelName" -ForegroundColor Cyan
    Write-Host ""
    
    # Generate prompt
    $prompt = Get-QualityAwarePrompt -VisualBlock $VisualJson -GenerationBlock $GenerationJson -ExportBlock $ExportJson
    
    Write-Host "Generating material specification..." -ForegroundColor Cyan
    
    # Call Ollama
    $systemPrompt = "You are an expert procedural texture designer. Output ONLY valid JSON with no commentary, explanations, or code blocks."
    
    $response = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if (-not $response) {
        Write-Host "Error: Failed to get response from Ollama" -ForegroundColor Red
        return $null
    }
    
    # Extract JSON from response
    $jsonMatch = $response -match '\{[\s\S]*\}'
    if ($jsonMatch) {
        try {
            $spec = $matches[0] | ConvertFrom-Json
            
            Write-Host "  ✓ Material specification generated" -ForegroundColor Green
            Write-Host ""
            Write-Host "Material Spec Summary:" -ForegroundColor Cyan
            Write-Host "  Style: $($spec.material.style)" -ForegroundColor Gray
            Write-Host "  Shape: $($spec.material.shape)" -ForegroundColor Gray
            Write-Host "  Quality: $($spec.material.quality)" -ForegroundColor Gray
            Write-Host "  Layers: $($spec.material.proceduralLayers.Count)" -ForegroundColor Gray
            Write-Host "  Textures: $($spec.textures | ConvertTo-Json -Compress)" -ForegroundColor Gray
            Write-Host ""
            
            return $spec
        }
        catch {
            Write-Host "Error parsing JSON response: $_" -ForegroundColor Red
            Write-Host "Raw response:" -ForegroundColor Yellow
            Write-Host $response -ForegroundColor Gray
            return $null
        }
    } else {
        Write-Host "Error: No JSON found in response" -ForegroundColor Red
        Write-Host "Raw response:" -ForegroundColor Yellow
        Write-Host $response -ForegroundColor Gray
        return $null
    }
}

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------

$spec = Generate-MaterialSpec `
    -RegistryPath $RegistryPath `
    -AssetId $AssetId `
    -VisualJson $VisualJson `
    -GenerationJson $GenerationJson `
    -ExportJson $ExportJson `
    -ModelName $Model

if ($spec) {
    # Save to file if output path provided
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $outputDir = Split-Path -Parent $OutputPath
        if ($outputDir -and -not (Test-Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        $spec | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8
        Write-Host "Saved material specification to: $OutputPath" -ForegroundColor Green
    } else {
        # Output to console
        Write-Host ""
        Write-Host "Material Specification:" -ForegroundColor Cyan
        Write-Host ($spec | ConvertTo-Json -Depth 10) -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  Generation Complete!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Generation failed." -ForegroundColor Red
    exit 1
}

