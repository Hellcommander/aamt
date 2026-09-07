# OllamaImageGenerator.ps1
# AI-Assisted Modding Tools (AAMT)
# Enhanced image generator using Ollama + Stable Diffusion 3 for high-quality asset generation
# Workflow: Ollama enhances description → SD3 generates high-quality image

param(
    [Parameter(Mandatory=$true)]
    [string]$Description,
    
    [Parameter(Mandatory=$false)]
    [int]$Width = 1024,
    
    [Parameter(Mandatory=$false)]
    [int]$Height = 1024,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$StableDiffusionUrl = "http://localhost:1337",
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "",  # Auto-selected by OllamaIntegration.psm1
    
    [Parameter(Mandatory=$false)]
    [switch]$UseStableDiffusion = $true,  # Use SD3 for actual image generation
    
    [Parameter(Mandatory=$false)]
    [switch]$EnhanceOnly = $false,  # Only enhance description, don't generate image

$ErrorActionPreference = "Stop"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for image generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "StableDiffusion")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for image generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Starbound - Image Generator" `
        -RequiredTools @("ImageMagick") `
        -OptionalTools @("Ollama", "StableDiffusion")
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    Write-Host "[OK] Ollama integration enabled" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Ollama not available - description enhancement disabled" -ForegroundColor Yellow
}

# Use Stable Diffusion if available
if ($UseStableDiffusion -and $tools.Tools["StableDiffusion"].Available) {
    Use-StableDiffusionIfAvailable | Out-Null
    Write-Host "[OK] Stable Diffusion integration enabled" -ForegroundColor Green
} elseif ($UseStableDiffusion) {
    Write-Host "[WARNING] Stable Diffusion not available - falling back to description enhancement only" -ForegroundColor Yellow
    $UseStableDiffusion = $false
}

# Load shared asset generation settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
    # Use Ollama settings from shared config if available
    if ($script:OllamaUrl) {
        $OllamaUrl = $script:OllamaUrl
    }
}

# Check if Ollama is available (using unified detection)
function Test-OllamaConnection {
    param([string]$Url = "http://localhost:11434")
    # Use unified detection first
    if (Test-OllamaAvailable) {
        return $true
    }
    # Fallback to manual check
    try {
        $response = Invoke-RestMethod -Uri "$Url/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Enhance description using Ollama for better procedural generation
function Enhance-DescriptionWithOllama {
    param(
        [string]$Description,
        [string]$OllamaUrl,
        [string]$Model
    )
    
    # Try to use shared OllamaIntegration module if available
    $toolsRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $sharedModulePath = Join-Path $toolsRoot "Shared\OllamaIntegration.psm1"
    if (Test-Path $sharedModulePath) {
        Import-Module $sharedModulePath -Force -ErrorAction SilentlyContinue
        if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
            if (Test-OllamaConnection) {
                try {
                    $enhancementPrompt = @"
You are a game asset designer for Starbound. Enhance this asset description to provide detailed visual guidance for procedural generation:

Original description: $Description

Provide an enhanced description that includes:
- Specific color palette suggestions (RGB values)
- Visual style details (pixel art, shading, outlines)
- Material/texture characteristics
- Size and proportion details
- Any thematic elements that should be emphasized

Return ONLY the enhanced description, no other text.
"@
                    # Use visual task type for creative description enhancement
                    # Empty ModelName lets the shared module auto-select the best available model
                    $modelToUse = if ($Model -and $Model.Trim() -ne "") { $Model } else { "" }
                    $enhanced = Invoke-OllamaRequest -Prompt $enhancementPrompt -TaskType "visual" -ResponseLength "standard" -ModelName $modelToUse
                    if ($enhanced -and $enhanced.Length -gt $Description.Length) {
                        Write-Host "✓ Description enhanced with Ollama" -ForegroundColor Green
                        return $enhanced
                    }
                } catch {
                    Write-Host "⚠ Ollama enhancement failed: $_" -ForegroundColor Yellow
                }
            }
        }
    }
    
    # Fallback to basic implementation if shared module not available
    if (-not (Test-OllamaConnection -Url $OllamaUrl)) {
        Write-Host "⚠ Ollama not available, using original description" -ForegroundColor Yellow
        return $Description
    }
    
    try {
        $enhancementPrompt = @"
You are a game asset designer for Starbound. Enhance this asset description to provide detailed visual guidance for procedural generation:

Original description: $Description

Provide an enhanced description that includes:
- Specific color palette suggestions (RGB values)
- Visual style details (pixel art, shading, outlines)
- Material/texture characteristics
- Size and proportion details
- Any thematic elements that should be emphasized

Return ONLY the enhanced description, no other text.
"@
        
        # Auto-select model if not specified
        $modelToUse = $Model
        if ([string]::IsNullOrWhiteSpace($modelToUse)) {
            try {
                $models = (Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -TimeoutSec 2).models
                $modelNames = $models | ForEach-Object { $_.name }
                # Try preferred models in order
                $preferred = @("llama3.1:8b", "wizardlm-uncensored", "qwen2.5-coder:7b")
                foreach ($pref in $preferred) {
                    if ($modelNames -contains $pref) {
                        $modelToUse = $pref
                        break
                    }
                }
                if ([string]::IsNullOrWhiteSpace($modelToUse) -and $modelNames.Count -gt 0) {
                    $modelToUse = $modelNames[0]
                }
            } catch {
                Write-Host "⚠ Could not auto-select model, using first available" -ForegroundColor Yellow
            }
        }
        
        if ([string]::IsNullOrWhiteSpace($modelToUse)) {
            return $Description
        }
        
        $body = @{
            model = $modelToUse
            prompt = $enhancementPrompt
            stream = $false
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $enhanced = $response.response.Trim()
        
        # Unload model after use to free VRAM
        try {
            $unloadBody = @{
                model = $modelToUse
                prompt = ""
                keep_alive = 0
                stream = $false
            } | ConvertTo-Json -Compress
            $null = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
                -Method Post `
                -ContentType "application/json" `
                -Body $unloadBody `
                -TimeoutSec 5 `
                -ErrorAction SilentlyContinue
        } catch {
            # Try CLI method as fallback
            try {
                $null = & ollama stop $modelToUse 2>&1
            } catch {
                # Ignore errors - model may already be unloaded
            }
        }
        
        if ($enhanced -and $enhanced.Length -gt $Description.Length) {
            Write-Host "✓ Description enhanced with Ollama" -ForegroundColor Green
            return $enhanced
        } else {
            return $Description
        }
    } catch {
        Write-Host "⚠ Ollama enhancement failed: $_" -ForegroundColor Yellow
        # Try to unload model even on error
        if ($modelToUse) {
            try {
                $unloadBody = @{
                    model = $modelToUse
                    prompt = ""
                    keep_alive = 0
                    stream = $false
                } | ConvertTo-Json -Compress
                $null = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
                    -Method Post `
                    -ContentType "application/json" `
                    -Body $unloadBody `
                    -TimeoutSec 5 `
                    -ErrorAction SilentlyContinue
            } catch {
                try {
                    $null = & ollama stop $modelToUse 2>&1
                } catch {
                    # Ignore
                }
            }
        }
        return $Description
    }
}

# Extract parameters from enhanced description
function Extract-ParametersFromDescription {
    param([string]$Description)
    
    $params = @{}
    $descLower = $Description.ToLower()
    
    # Extract color hints
    if ($descLower -match "rgb\((\d+),\s*(\d+),\s*(\d+)\)") {
        $params['ColorPalette'] = @(
            [int]$matches[1], [int]$matches[2], [int]$matches[3]
        )
    } elseif ($descLower -match "purple|violet") {
        $params['ColorPalette'] = @(@(200, 100, 255), @(150, 50, 200), @(100, 25, 150))
    } elseif ($descLower -match "blue|azure") {
        $params['ColorPalette'] = @(@(100, 150, 255), @(50, 100, 200), @(25, 50, 150))
    } elseif ($descLower -match "red|fire|crimson") {
        $params['ColorPalette'] = @(@(255, 100, 100), @(200, 50, 50), @(150, 25, 25))
    } elseif ($descLower -match "green|emerald") {
        $params['ColorPalette'] = @(@(100, 255, 100), @(50, 200, 50), @(25, 150, 25))
    }
    
    # Extract style hints
    if ($descLower -match "magic|arcane|spell|mystical") {
        $params['Style'] = "magical"
        $params['HasGradient'] = $true
        $params['HasSparkles'] = $true
    } elseif ($descLower -match "metal|mech|mechanical") {
        $params['Style'] = "metallic"
        $params['HasPattern'] = $true
    } elseif ($descLower -match "crystal|gem|shiny") {
        $params['Style'] = "crystalline"
        $params['HasGradient'] = $true
    }
    
    return $params
}

# Import Stable Diffusion integration if using SD3
if ($UseStableDiffusion -and -not $EnhanceOnly) {
    $toolsRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $sdModulePath = Join-Path $toolsRoot "Shared\StableDiffusionIntegration.psm1"
    if (Test-Path $sdModulePath) {
        # Suppress warning about unapproved verb "Generate" - this is expected and harmless
        Import-Module $sdModulePath -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
        Write-Host "✓ Loaded Stable Diffusion 3 integration" -ForegroundColor Green
    }
}

# Main execution
if ($Description) {
    Write-Host "=== AI Asset Generation ===" -ForegroundColor Cyan
    Write-Host "Original description: $Description" -ForegroundColor Gray
    
    # Enhance description with Ollama
    Write-Host "Enhancing description with Ollama..." -ForegroundColor Cyan
    $enhancedDescription = Enhance-DescriptionWithOllama -Description $Description -OllamaUrl $OllamaUrl -Model $Model
    $extractedParams = Extract-ParametersFromDescription -Description $enhancedDescription
    
    if ($EnhanceOnly) {
        # Return enhanced description and parameters as JSON
        $result = @{
            OriginalDescription = $Description
            EnhancedDescription = $enhancedDescription
            ExtractedParameters = $extractedParams
            Width = $Width
            Height = $Height
        }
        
        if ($OutputPath) {
            $result | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8
            Write-Host "✓ Enhanced description saved to: $OutputPath" -ForegroundColor Green
        }
        
        Write-Output ($result | ConvertTo-Json -Depth 10)
    } elseif ($UseStableDiffusion -and $tools.Tools["StableDiffusion"].Available -and (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue)) {
        # Generate actual image with SD3
        Write-Host "Generating high-quality image with Stable Diffusion 3 Medium..." -ForegroundColor Cyan
        
        if (-not $OutputPath) {
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $OutputPath = "generated_asset_${timestamp}.png"
        }
        
        try {
            $imagePath = Generate-AssetImageWithSD3 `
                -Prompt $enhancedDescription `
                -OutputPath $OutputPath `
                -Width $Width `
                -Height $Height `
                -EnhanceWithOllama:$false `  # Already enhanced above
                -AutoStartServer:$true
            
            Write-Host "✓ Image generated: $imagePath" -ForegroundColor Green
            
            # Save metadata
            $metadataPath = $OutputPath -replace '\.png$', '_metadata.json'
            $metadata = @{
                OriginalDescription = $Description
                EnhancedDescription = $enhancedDescription
                ExtractedParameters = $extractedParams
                Dimensions = @{ Width = $Width; Height = $Height }
                GeneratedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
                Model = "Stable Diffusion 3 Medium"
                EnhancedWithOllama = $true
            }
            $metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8
            
            Write-Output $imagePath
        } catch {
            Write-Host "✗ SD3 generation failed: $_" -ForegroundColor Red
            Write-Host "  Falling back to description enhancement only" -ForegroundColor Yellow
            $EnhanceOnly = $true
            # Fall through to enhance-only path
        }
    } else {
        # Fallback: return enhanced description
        Write-Host "⚠ SD3 not available, returning enhanced description only" -ForegroundColor Yellow
        $result = @{
            OriginalDescription = $Description
            EnhancedDescription = $enhancedDescription
            ExtractedParameters = $extractedParams
            Width = $Width
            Height = $Height
        }
        Write-Output ($result | ConvertTo-Json -Depth 10)
    }
} else {
    Write-Host "Error: Description is required" -ForegroundColor Red
    exit 1
}

