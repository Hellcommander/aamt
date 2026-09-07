#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests asset generator quality by generating a complex sprite and using AI vision to analyze it

.DESCRIPTION
    Generates a sprite with a complex description, then uses Ollama vision model to analyze
    the generated image and compare it to the original description to verify quality.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$TestName = "test_complex_sprite",
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "A intricate magical crystal staff with glowing runes, ornate metalwork, multiple gemstones embedded in spiraling patterns, and ethereal energy wisps emanating from the top",
    
    [Parameter(Mandatory=$false)]
    [int]$Width = 64,
    
    [Parameter(Mandatory=$false)]
    [int]$Height = 64,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TestOutput",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$VisionModel = "llama3.2-vision:11b"  # Vision model for image analysis
)

$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Asset Generator Quality Test" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Import required modules
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGeneratorPath = Join-Path $PSScriptRoot "StarboundAssetGenerator.ps1"
$ollamaModulePath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\OllamaIntegration.psm1"

if (Test-Path $ollamaModulePath) {
    Import-Module $ollamaModulePath -Force
    Write-Host "[OK] Loaded Ollama integration module" -ForegroundColor Green
} else {
    Write-Host "[WARN] Ollama module not found, vision analysis will be limited" -ForegroundColor Yellow
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host ""
Write-Host "Test Configuration:" -ForegroundColor Yellow
Write-Host "  Test Name: $TestName" -ForegroundColor Gray
Write-Host "  Description: $Description" -ForegroundColor Gray
Write-Host "  Dimensions: ${Width}x${Height}" -ForegroundColor Gray
Write-Host "  Output: $OutputDir" -ForegroundColor Gray
Write-Host ""

# Step 1: Generate the sprite
Write-Host "Step 1: Generating sprite..." -ForegroundColor Cyan
Write-Host ""

$generatorParams = @{
    AssetType = "ItemSprite"
    AssetName = $TestName
    Description = $Description
    OutputDir = $OutputDir
    Parameters = @{
        Width = $Width
        Height = $Height
        FrameCount = 1
    }
}

# Call the asset generator script
Write-Host "  Calling asset generator..." -ForegroundColor Gray

# Build parameters hashtable as JSON string for passing
$paramsJson = $generatorParams.Parameters | ConvertTo-Json -Compress

$generatorResult = & pwsh -NoProfile -ExecutionPolicy Bypass -File $assetGeneratorPath `
    -AssetType "ItemSprite" `
    -AssetName $TestName `
    -Description $Description `
    -OutputDir $OutputDir

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "[ERROR] Sprite generation failed (exit code: $exitCode)" -ForegroundColor Red
    exit 1
}

# Find the generated sprite (may be in subdirectory)
$spritePath = Join-Path $OutputDir "$TestName.png"
if (-not (Test-Path $spritePath)) {
    # Check in items/sprites subdirectory (ItemSprite default location)
    $spritePath = Join-Path $OutputDir "items\sprites\$TestName.png"
}
if (-not (Test-Path $spritePath)) {
    # Search recursively
    $foundSprite = Get-ChildItem -Path $OutputDir -Filter "$TestName.png" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundSprite) {
        $spritePath = $foundSprite.FullName
    }
}
if (-not (Test-Path $spritePath)) {
    Write-Host "[ERROR] Generated sprite not found. Searched:" -ForegroundColor Red
    Write-Host "  - $OutputDir\$TestName.png" -ForegroundColor Gray
    Write-Host "  - $OutputDir\items\sprites\$TestName.png" -ForegroundColor Gray
    Write-Host "  - Recursively in $OutputDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Listing files in output directory:" -ForegroundColor Yellow
    Get-ChildItem -Path $OutputDir -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor Gray }
    exit 1
}

Write-Host ""
Write-Host "[OK] Sprite generated: $spritePath" -ForegroundColor Green

# Step 2: Analyze the generated image with AI vision
Write-Host ""
Write-Host "Step 2: Analyzing generated image with AI vision..." -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is available
try {
    $ollamaCheck = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Ollama is available" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Ollama not available, skipping vision analysis" -ForegroundColor Yellow
    Write-Host "  Install Ollama and a vision model to enable this feature" -ForegroundColor Gray
    Write-Host "  Example: ollama pull llama3.2-vision:11b" -ForegroundColor Gray
    exit 0
}

# Check if vision model is available, or find an alternative
$availableModels = $ollamaCheck.models | ForEach-Object { $_.name }
if ($VisionModel -notin $availableModels) {
    Write-Host "[WARN] Vision model '$VisionModel' not found" -ForegroundColor Yellow
    Write-Host "  Available models: $($availableModels -join ', ')" -ForegroundColor Gray
    
    # Try to find a vision-capable model
    $visionModels = @("llama3.2-vision", "llava", "bakllava", "moondream", "minicpm-v")
    $foundVisionModel = $null
    foreach ($vm in $visionModels) {
        $matching = $availableModels | Where-Object { $_ -like "$vm*" }
        if ($matching) {
            $foundVisionModel = $matching | Select-Object -First 1
            break
        }
    }
    
    if ($foundVisionModel) {
        Write-Host "  Using alternative vision model: $foundVisionModel" -ForegroundColor Green
        $VisionModel = $foundVisionModel
    } else {
        Write-Host "  No vision-capable models found." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Performing basic quality analysis instead..." -ForegroundColor Yellow
        Write-Host ""
        
        # Detailed image analysis without vision model
        Add-Type -AssemblyName System.Drawing
        $bitmap = New-Object System.Drawing.Bitmap($spritePath)
        
        # Count unique colors and analyze color distribution
        $colorSet = New-Object System.Collections.Generic.HashSet[string]
        $colorGroups = @{
            Red = 0
            Blue = 0
            Green = 0
            Purple = 0
            Yellow = 0
            White = 0
            Gray = 0
            Other = 0
        }
        $pixelCount = 0
        $edgePixels = 0
        $centerPixels = 0
        
        $centerX = $bitmap.Width / 2
        $centerY = $bitmap.Height / 2
        $centerRadius = [Math]::Min($bitmap.Width, $bitmap.Height) / 3
        
        for ($y = 0; $y -lt $bitmap.Height; $y++) {
            for ($x = 0; $x -lt $bitmap.Width; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.A -gt 0) {
                    $colorKey = "$($pixel.R),$($pixel.G),$($pixel.B)"
                    if (-not $colorSet.Contains($colorKey)) {
                        $colorSet.Add($colorKey) | Out-Null
                    }
                    $pixelCount++
                    
                    # Categorize colors - check complex colors first, then primary colors
                    $r = $pixel.R
                    $g = $pixel.G
                    $b = $pixel.B
                    $max = [Math]::Max($r, [Math]::Max($g, $b))
                    $min = [Math]::Min($r, [Math]::Min($g, $b))
                    
                    # Check purple first (high R and B, low G)
                    if ($r -gt 100 -and $b -gt 100 -and $g -lt [Math]::Min($r, $b) - 30) { 
                        $colorGroups.Purple++ 
                    }
                    # Check yellow (high R and G, low B)
                    elseif ($r -gt 150 -and $g -gt 100 -and $b -lt [Math]::Min($r, $g) - 40) { 
                        $colorGroups.Yellow++ 
                    }
                    # Check white/light (all channels high)
                    elseif ($max -gt 240 -and $min -gt 200) { 
                        $colorGroups.White++ 
                    }
                    # Check primary colors
                    elseif ($r -gt $g + 30 -and $r -gt $b + 30) { 
                        $colorGroups.Red++ 
                    }
                    elseif ($b -gt $r + 30 -and $b -gt $g + 30) { 
                        $colorGroups.Blue++ 
                    }
                    elseif ($g -gt $r + 30 -and $g -gt $b + 30) { 
                        $colorGroups.Green++ 
                    }
                    # Check gray (low saturation)
                    elseif ($max - $min -lt 30) { 
                        $colorGroups.Gray++ 
                    }
                    else { 
                        $colorGroups.Other++ 
                    }
                    
                    # Check if pixel is near center or edge
                    $distFromCenter = [Math]::Sqrt(($x - $centerX) * ($x - $centerX) + ($y - $centerY) * ($y - $centerY))
                    if ($distFromCenter -lt $centerRadius) {
                        $centerPixels++
                    } elseif ($x -lt 2 -or $x -gt $bitmap.Width - 3 -or $y -lt 2 -or $y -gt $bitmap.Height - 3) {
                        $edgePixels++
                    }
                }
            }
        }
        $bitmap.Dispose()
        
        # Build detailed description of what's in the image
        $imageDescription = "A $($bitmap.Width)x$($bitmap.Height) pixel image with $($colorSet.Count) unique colors. "
        $imageDescription += "Color distribution: "
        $colorDesc = @()
        if ($colorGroups.Red -gt 5) { $colorDesc += "$($colorGroups.Red) red pixels" }
        if ($colorGroups.Blue -gt 5) { $colorDesc += "$($colorGroups.Blue) blue pixels" }
        if ($colorGroups.Green -gt 5) { $colorDesc += "$($colorGroups.Green) green pixels" }
        if ($colorGroups.Purple -gt 5) { $colorDesc += "$($colorGroups.Purple) purple pixels" }
        if ($colorGroups.Yellow -gt 5) { $colorDesc += "$($colorGroups.Yellow) yellow pixels" }
        if ($colorGroups.White -gt 5) { $colorDesc += "$($colorGroups.White) white/light pixels" }
        if ($colorGroups.Gray -gt 5) { $colorDesc += "$($colorGroups.Gray) gray pixels" }
        $imageDescription += ($colorDesc -join ", ") + ". "
        $imageDescription += "Center region has $centerPixels pixels, edges have $edgePixels pixels. "
        if ($colorSet.Count -lt 10) {
            $imageDescription += "Very low color variety suggests a simple colored shape."
        } elseif ($colorSet.Count -lt 30) {
            $imageDescription += "Moderate color variety suggests some detail but likely simplified."
        } else {
            $imageDescription += "High color variety suggests detailed rendering with multiple elements."
        }
        
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Basic Quality Analysis" -ForegroundColor Cyan
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Original Description:" -ForegroundColor Yellow
        Write-Host "  $Description" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Image Statistics:" -ForegroundColor Yellow
        Write-Host "  Unique colors: $($colorSet.Count)" -ForegroundColor $(if ($colorSet.Count -ge 15) { "Green" } elseif ($colorSet.Count -ge 5) { "Yellow" } else { "Red" })
        Write-Host "  Non-transparent pixels: $pixelCount" -ForegroundColor Gray
        Write-Host "  Color distribution:" -ForegroundColor Gray
        if ($colorGroups.Red -gt 0) { Write-Host "    Red: $($colorGroups.Red)" -ForegroundColor Gray }
        if ($colorGroups.Blue -gt 0) { Write-Host "    Blue: $($colorGroups.Blue)" -ForegroundColor Gray }
        if ($colorGroups.Green -gt 0) { Write-Host "    Green: $($colorGroups.Green)" -ForegroundColor Gray }
        if ($colorGroups.Purple -gt 0) { Write-Host "    Purple: $($colorGroups.Purple)" -ForegroundColor Gray }
        if ($colorGroups.Yellow -gt 0) { Write-Host "    Yellow: $($colorGroups.Yellow)" -ForegroundColor Gray }
        if ($colorGroups.White -gt 0) { Write-Host "    White/Light: $($colorGroups.White)" -ForegroundColor Gray }
        if ($colorGroups.Gray -gt 0) { Write-Host "    Gray: $($colorGroups.Gray)" -ForegroundColor Gray }
        Write-Host ""
        
        if ($colorSet.Count -lt 10) {
            Write-Host "  [WARNING] Very few unique colors detected - likely a colored box/placeholder" -ForegroundColor Red
            Write-Host "  Expected: Complex sprite with multiple colors and details" -ForegroundColor Yellow
        } elseif ($colorSet.Count -lt 20) {
            Write-Host "  [CAUTION] Low color variety - may be too simple" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK] Good color variety detected" -ForegroundColor Green
        }
        
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Comparison: Requested vs. Generated" -ForegroundColor Cyan
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        
        # Direct comparison based on image analysis
        Write-Host "WHAT WAS REQUESTED:" -ForegroundColor Yellow
        Write-Host "  $Description" -ForegroundColor Gray
        Write-Host ""
        Write-Host "WHAT WAS ACTUALLY GENERATED (image analysis):" -ForegroundColor Yellow
        Write-Host "  $imageDescription" -ForegroundColor White
        Write-Host ""
        
        # Calculate accuracy score based on criteria
        $score = 0
        $scoreDetails = @()
        
        # Check for color variety (should have multiple colors for complex description)
        if ($colorSet.Count -ge 50) {
            $score += 2
            $scoreDetails += "Good color variety (+2)"
        } elseif ($colorSet.Count -ge 20) {
            $score += 1
            $scoreDetails += "Moderate color variety (+1)"
        } else {
            $scoreDetails += "Low color variety (0)"
        }
        
        # Check for multiple color groups (should have red, blue, green for gemstones)
        $colorGroupCount = ($colorGroups.Red, $colorGroups.Blue, $colorGroups.Green, $colorGroups.Purple, $colorGroups.Yellow | Where-Object { $_ -gt 5 }).Count
        if ($colorGroupCount -ge 3) {
            $score += 2
            $scoreDetails += "Multiple distinct color groups detected (+2)"
        } elseif ($colorGroupCount -ge 2) {
            $score += 1
            $scoreDetails += "Some color groups detected (+1)"
        } else {
            $scoreDetails += "Limited color groups (mostly $($colorGroups.GetEnumerator() | Where-Object { $_.Value -eq ($colorGroups.Values | Measure-Object -Maximum).Maximum } | Select-Object -First 1 -ExpandProperty Key)) (0)"
        }
        
        # Check if it's just a single color (colored box)
        $dominantColor = ($colorGroups.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1)
        $dominantPercent = [Math]::Round(($dominantColor.Value / $pixelCount) * 100, 1)
        if ($dominantPercent -gt 90) {
            $score = [Math]::Max(0, $score - 5)  # Heavy penalty for single-color dominance
            $scoreDetails += "CRITICAL: $dominantPercent% of image is single color - likely colored box (-5)"
        } elseif ($dominantPercent -gt 70) {
            $score = [Math]::Max(0, $score - 2)
            $scoreDetails += "Warning: $dominantPercent% of image is one color - very simplified (-2)"
        } else {
            $scoreDetails += "Color distribution is varied (+0)"
        }
        
        # Description mentions specific elements - check if colors suggest they might be present
        $descLower = $Description.ToLower()
        $expectedColors = 0
        $foundColors = 0
        
        if ($descLower -match "ruby|red|crimson") { $expectedColors++; if ($colorGroups.Red -gt 10) { $foundColors++ } }
        if ($descLower -match "sapphire|blue|azure") { $expectedColors++; if ($colorGroups.Blue -gt 10) { $foundColors++ } }
        if ($descLower -match "emerald|green|jade") { $expectedColors++; if ($colorGroups.Green -gt 10) { $foundColors++ } }
        if ($descLower -match "purple|violet") { $expectedColors++; if ($colorGroups.Purple -gt 10) { $foundColors++ } }
        if ($descLower -match "gold|golden|yellow|amber") { $expectedColors++; if ($colorGroups.Yellow -gt 10) { $foundColors++ } }
        if ($descLower -match "silver|gray|grey|metal") { $expectedColors++; if ($colorGroups.Gray -gt 10) { $foundColors++ } }
        if ($descLower -match "energy|wisp|ethereal|glow|light") { $expectedColors++; if ($colorGroups.Blue -gt 10 -or $colorGroups.White -gt 10 -or $colorGroups.Purple -gt 10) { $foundColors++ } }
        
        if ($expectedColors -gt 0) {
            $colorMatchPercent = [Math]::Round(($foundColors / $expectedColors) * 100, 0)
            if ($colorMatchPercent -ge 80) {
                $score += 3
                $scoreDetails += "Expected colors present: $foundColors/$expectedColors (+3)"
            } elseif ($colorMatchPercent -ge 50) {
                $score += 1
                $scoreDetails += "Some expected colors: $foundColors/$expectedColors (+1)"
            } else {
                $scoreDetails += "Missing expected colors: only $foundColors/$expectedColors (0)"
            }
        }
        
        # Cap score at 10
        $score = [Math]::Min(10, [Math]::Max(0, $score))
        
        Write-Host "SCORING BREAKDOWN:" -ForegroundColor Cyan
        foreach ($detail in $scoreDetails) {
            Write-Host "  $detail" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Estimated Quality Score: $score/10" -ForegroundColor $(if ($score -ge 7) { "Green" } elseif ($score -ge 4) { "Yellow" } else { "Red" })
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        
        if ($score -lt 4) {
            Write-Host "  [CONCLUSION] Generated sprite appears to be a colored box/placeholder" -ForegroundColor Red
            Write-Host "    The description requested complex details, but the image is too simple" -ForegroundColor Yellow
        } elseif ($score -lt 7) {
            Write-Host "  [CONCLUSION] Generated sprite is simplified but has some detail" -ForegroundColor Yellow
            Write-Host "    Some elements may be present but simplified due to resolution constraints" -ForegroundColor Gray
        } else {
            Write-Host "  [CONCLUSION] Generated sprite appears to have good detail" -ForegroundColor Green
            Write-Host "    Multiple colors and elements suggest proper sprite generation" -ForegroundColor Gray
        }
        
        Write-Host ""
        
        # Save results
        $resultsPath = Join-Path $OutputDir "${TestName}_analysis.json"
        $results = @{
            TestName = $TestName
            OriginalDescription = $Description
            Dimensions = @{
                Width = $Width
                Height = $Height
            }
            GeneratedImagePath = $spritePath
            ImageStatistics = @{
                UniqueColors = $colorSet.Count
                NonTransparentPixels = $pixelCount
                ColorDistribution = $colorGroups
                DominantColor = $dominantColor.Name
                DominantColorPercent = $dominantPercent
                CenterPixels = $centerPixels
                EdgePixels = $edgePixels
            }
            ImageDescription = $imageDescription
            Score = $score
            ScoreDetails = $scoreDetails
            ExpectedColors = $expectedColors
            FoundColors = $foundColors
            Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            Note = "Vision model not available - used statistical analysis with color distribution"
        }
        
        $results | ConvertTo-Json -Depth 10 | Set-Content -Path $resultsPath -Encoding UTF8
        Write-Host "[OK] Analysis saved to: $resultsPath" -ForegroundColor Green
        Write-Host ""
        
        # Use text model for additional analysis if timeout didn't occur
        Write-Host "  Performing additional AI text analysis..." -ForegroundColor Yellow
        $comparisonPrompt = @"
Compare what was REQUESTED vs. what was ACTUALLY GENERATED:

WHAT WAS REQUESTED:
"$Description"

WHAT WAS ACTUALLY GENERATED (based on image analysis):
$imageDescription

Analyze the accuracy:

1. What elements from the description should be visible in a 16x16 pixel sprite?
2. What level of detail is realistically possible at 16x16 resolution?
3. Rate the likely accuracy (1-10) where:
   - 10 = All major elements would be clearly visible with good detail
   - 7-9 = Most elements visible with reasonable detail
   - 4-6 = Some elements visible but simplified
   - 1-3 = Very simplified, mostly just basic shapes/colors
   - 0 = Just a colored box/placeholder

4. What specific elements from the description (staff, runes, metalwork, gemstones, energy wisps) would be:
   - Clearly visible at 16x16
   - Partially visible but simplified
   - Too small/detailed to be visible at this resolution
   - Missing entirely

Provide a detailed analysis and numerical score.
"@
        
        $comparisonRequest = @{
            model = if ($availableModels -contains "qwen2.5-coder:14b") { "qwen2.5-coder:14b" } 
                    elseif ($availableModels -contains "qwen2.5-coder:7b") { "qwen2.5-coder:7b" }
                    else { ($availableModels | Select-Object -First 1) }
            prompt = $comparisonPrompt
            stream = $false
        } | ConvertTo-Json -Depth 10
        
        try {
            $comparisonResponse = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" -Method Post -Body $comparisonRequest -ContentType "application/json" -TimeoutSec 60
            $comparison = $comparisonResponse.response
            
            Write-Host "Text-Based Analysis & Score:" -ForegroundColor Yellow
            Write-Host "  $comparison" -ForegroundColor White
            Write-Host ""
            
            # Extract score if possible
            if ($comparison -match '(\d+)(?:\s*/\s*10)?') {
                $score = [int]$matches[1]
                Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
                Write-Host "  Estimated Quality Score: $score/10" -ForegroundColor $(if ($score -ge 7) { "Green" } elseif ($score -ge 4) { "Yellow" } else { "Red" })
                Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
            }
            
            # Save results
            $resultsPath = Join-Path $OutputDir "${TestName}_analysis.json"
            $results = @{
                TestName = $TestName
                OriginalDescription = $Description
                Dimensions = @{
                    Width = $Width
                    Height = $Height
                }
                GeneratedImagePath = $spritePath
                ImageStatistics = @{
                    UniqueColors = $colorSet.Count
                    NonTransparentPixels = $pixelCount
                }
                TextBasedAnalysis = $comparison
                Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
                Note = "Vision model not available - used text-based analysis with image statistics"
            }
            
            $results | ConvertTo-Json -Depth 10 | Set-Content -Path $resultsPath -Encoding UTF8
            Write-Host ""
            Write-Host "[OK] Analysis saved to: $resultsPath" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Text analysis failed: $_" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "  To get detailed AI vision analysis, install a vision model:" -ForegroundColor Gray
        Write-Host "    ollama pull llama3.2-vision:11b" -ForegroundColor Gray
        Write-Host "    or: ollama pull llava:latest" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Sprite location: $spritePath" -ForegroundColor Cyan
        exit 0
    }
}

# Convert image to base64 for API
$imageBytes = [System.IO.File]::ReadAllBytes($spritePath)
$imageBase64 = [Convert]::ToBase64String($imageBytes)

# Create analysis prompt WITHOUT the original description (no cheating!)
# The AI should analyze what it actually sees, not what it expects to see
$analysisPrompt = @"
Analyze this sprite image and describe EXACTLY what you see. Be completely honest and specific:

1. What objects, shapes, or elements are actually visible in the image?
2. What colors and color patterns do you observe?
3. What level of detail and complexity is present?
4. Are there any visual features, patterns, decorations, or details visible?
5. Does this look like a proper detailed sprite, or just a simple colored shape/box/placeholder?

IMPORTANT: Describe ONLY what you can actually see in the image. Do not make assumptions or guess what it might be. If it's just a colored circle or rectangle, say so. If there are details, describe them specifically.

Provide a detailed, honest analysis of what the image actually contains.
"@

# Call Ollama vision API
Write-Host "  Calling vision model: $VisionModel" -ForegroundColor Gray
Write-Host "  This may take a moment..." -ForegroundColor Gray

try {
    $visionRequest = @{
        model = $VisionModel
        prompt = $analysisPrompt
        images = @($imageBase64)
        stream = $false
    } | ConvertTo-Json -Depth 10
    
    $visionResponse = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" -Method Post -Body $visionRequest -ContentType "application/json" -TimeoutSec 60
    
    $aiAnalysis = $visionResponse.response
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  AI Vision Analysis Results" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Original Description:" -ForegroundColor Yellow
    Write-Host "  $Description" -ForegroundColor Gray
    Write-Host ""
    Write-Host "AI Analysis of Generated Image (blind analysis - no description provided):" -ForegroundColor Yellow
    Write-Host "  $aiAnalysis" -ForegroundColor White
    Write-Host ""
    
    # Step 3: Compare and score (now reveal the original description)
    Write-Host "Step 3: Comparing what was requested vs. what was actually generated..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Now revealing the original description for comparison..." -ForegroundColor Gray
    Write-Host ""
    
    # Use AI to compare - NOW we reveal the original description
    $comparisonPrompt = @"
You analyzed an image and described what you saw. Now I'm revealing what was REQUESTED to be generated.

WHAT WAS REQUESTED:
$Description

WHAT YOU ACTUALLY SAW IN THE IMAGE:
$aiAnalysis

Compare these honestly. Rate the accuracy on a scale of 1-10 where:
- 10 = Perfect match, all requested elements present with high detail
- 7-9 = Good match, most elements present with reasonable detail  
- 4-6 = Partial match, some elements present but missing details
- 1-3 = Poor match, few elements present, mostly just colored shapes
- 0 = Complete failure, just a colored box/placeholder

Be honest - if the image is just a colored circle or rectangle, score it low even if the description was complex.

Provide:
1. A numerical score (0-10)
2. A brief explanation of why you gave this score
3. What specific elements from the original description are actually visible in the image
4. What specific elements from the original description are missing or poorly represented
"@
    
    $comparisonRequest = @{
        model = if ($availableModels -contains "qwen2.5-coder:14b") { "qwen2.5-coder:14b" } 
                elseif ($availableModels -contains "qwen2.5-coder:7b") { "qwen2.5-coder:7b" }
                else { ($availableModels | Select-Object -First 1) }
        prompt = $comparisonPrompt
        stream = $false
    } | ConvertTo-Json -Depth 10
    
    $comparisonResponse = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" -Method Post -Body $comparisonRequest -ContentType "application/json" -TimeoutSec 60
    
    $comparison = $comparisonResponse.response
    
    Write-Host "Comparison & Score:" -ForegroundColor Yellow
    Write-Host "  $comparison" -ForegroundColor White
    Write-Host ""
    
    # Extract score if possible
    if ($comparison -match '(\d+)(?:\s*/\s*10)?') {
        $score = [int]$matches[1]
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Quality Score: $score/10" -ForegroundColor $(if ($score -ge 7) { "Green" } elseif ($score -ge 4) { "Yellow" } else { "Red" })
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    }
    
    # Save results
    $resultsPath = Join-Path $OutputDir "${TestName}_analysis.json"
    $results = @{
        TestName = $TestName
        OriginalDescription = $Description
        Dimensions = @{
            Width = $Width
            Height = $Height
        }
        GeneratedImagePath = $spritePath
        AIAnalysis = $aiAnalysis
        Comparison = $comparison
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    
    $results | ConvertTo-Json -Depth 10 | Set-Content -Path $resultsPath -Encoding UTF8
    Write-Host ""
    Write-Host "[OK] Analysis saved to: $resultsPath" -ForegroundColor Green
    
} catch {
    Write-Host "[ERROR] Vision analysis failed: $_" -ForegroundColor Red
    Write-Host "  Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Green
