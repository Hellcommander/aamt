<#
.SYNOPSIS
    Shared Image Quality Assessment Module
    Provides multi-tier quality assessment using vision-language models
    
.DESCRIPTION
    This module provides quality assessment for generated images using:
    - Phase 1: Sanity checks (file size, resolution)
    - Phase 2: Mechanical QA (Qwen3-VL-8B) - technical defect detection
    - Phase 3: Aesthetic scoring (LLaVA:13b) - professional quality judgment
    
    Models are automatically loaded on-demand and unloaded after use to save VRAM.
#>

# Vision model configuration
$script:VisionModels = @{
    "mechanical" = "qwen3-vl:8b"  # Technical defect detection
    "aesthetic" = "llava:13b"      # Professional quality judgment
}
$script:LastQualityAssessment = $null

function Write-QualityLog {
    <#
    .SYNOPSIS
    Writes quality assessment log entries (optional, can be overridden by scripts)
    #>
    param(
        [string]$Message,
        [string]$Category = "",
        [int]$Attempt = 0,
        [double]$Score = 0.0,
        [string]$ImagePath = ""
    )
    # Default implementation - scripts can override this
    # This allows the module to work without requiring logging setup
}

function Unload-OllamaModel {
    <#
    .SYNOPSIS
    Unloads an Ollama model from VRAM to free memory.
    Uses shared OllamaIntegration module if available, otherwise local implementation.
    #>
    param(
        [string]$ModelName
    )
    
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        return
    }
    
    # Try to use shared module's function first
    if (Get-Command Unload-OllamaModel -ErrorAction SilentlyContinue -Module OllamaIntegration) {
        Unload-OllamaModel -ModelName $ModelName
        return
    }
    
    # Fallback to local implementation
    try {
        $ollamaUrl = "http://localhost:11434/api/generate"
        $body = @{
            model = $ModelName
            prompt = ""
            keep_alive = 0
            stream = $false
        } | ConvertTo-Json -Compress
        
        $null = Invoke-RestMethod -Uri $ollamaUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
    } catch {
        # Try CLI method as fallback
        try {
            $null = & ollama stop $ModelName 2>&1
        } catch {
            # Ignore errors - model may already be unloaded
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
        
        # Call Ollama API with image — request GPU layers (do not silently run VLMs on CPU-only).
        $numGpu = 99
        try {
            if (Get-Command Get-GPUInfo -ErrorAction SilentlyContinue) {
                $gi = Get-GPUInfo
                if ($gi -and $gi.Available -and $gi.VRAMGB -gt 0 -and (Get-Command Get-OptimalGPULayers -ErrorAction SilentlyContinue)) {
                    $numGpu = Get-OptimalGPULayers -ModelName $ModelName -AvailableVRAMGB $gi.VRAMGB -PreferGPU
                }
            } elseif (Get-Command Get-FreeVramMB -ErrorAction SilentlyContinue) {
                $freeMb = Get-FreeVramMB
                if ($null -ne $freeMb -and $freeMb -lt 2048) {
                    Write-Host "    [QA] Low free VRAM (${freeMb}MB) — vision model may spill; unload other GPU apps if scores fail." -ForegroundColor Yellow
                }
            }
        } catch { }

        $ollamaUrl = "http://localhost:11434/api/chat"
        $bodyObj = @{
            model = $ModelName
            messages = @(
                @{
                    role = "user"
                    content = $prompt
                    images = @($imageBase64)
                }
            )
            stream = $false
            keep_alive = "1m"
            options = @{
                num_gpu = $numGpu
            }
        }
        Write-Host "    [QA] Ollama vision on GPU (num_gpu=$numGpu, model=$ModelName)" -ForegroundColor DarkCyan
        $body = $bodyObj | ConvertTo-Json -Depth 10 -Compress
        
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
    Multi-tier quality assessment: Sanity check → Mechanical QA → Aesthetic scoring
    
    .PARAMETER ImagePath
    Path to the image file to assess
    
    .PARAMETER Depth
    Assessment depth: "fast" (sanity only), "mechanical" (Qwen3-VL-8B), "full" (both models)
    
    .PARAMETER VisionModels
    Optional hashtable with model names. Defaults to qwen3-vl:8b (mechanical) and llava:13b (aesthetic)
    
    .PARAMETER LogFunction
    Optional function to call for logging. Should accept Message, Category, Attempt, Score, ImagePath parameters.
    
    .EXAMPLE
    $score = Get-BestImageScore -ImagePath "image.png" -Depth "full"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ImagePath,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("fast", "mechanical", "full")]
        [string]$Depth = "fast",
        
        [Parameter(Mandatory=$false)]
        [hashtable]$VisionModels = $script:VisionModels,
        
        [Parameter(Mandatory=$false)]
        [scriptblock]$LogFunction = ${function:Write-QualityLog}
    )
    
    if (-not (Test-Path $ImagePath)) {
        if ($LogFunction) {
            & $LogFunction -Message "Image not found" -ImagePath $ImagePath
        }
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
            if ($LogFunction) {
                & $LogFunction -Message "Image too small (likely corrupt): $($fileInfo.Length) bytes" -ImagePath $ImagePath
            }
            return 5.0
        }
        
        if ($width -lt 128 -or $height -lt 128) {
            if ($LogFunction) {
                & $LogFunction -Message "Resolution too low: ${width}x${height}" -ImagePath $ImagePath
            }
            return 5.0
        }
        
        # Fast path: Return high score for valid images (no AI assessment)
        if ($Depth -eq "fast") {
            if ($width -ge 512 -and $height -ge 512) {
                if ($LogFunction) {
                    & $LogFunction -Message "Image passes sanity checks (fast mode): ${width}x${height}, $([math]::Round($fileInfo.Length/1MB, 2))MB" -ImagePath $ImagePath
                }
                return 18.0
            } else {
                if ($LogFunction) {
                    & $LogFunction -Message "Unusual dimensions but acceptable: ${width}x${height}" -ImagePath $ImagePath
                }
                return 15.0
            }
        }
        
        # Phase 2: Mechanical QA (Qwen3-VL-8B) - loads, uses, then unloads
        $mechanicalScore = $null
        if ($Depth -in @("mechanical", "full")) {
            Write-Host "    [QA] Running mechanical QA (Qwen3-VL-8B)..." -ForegroundColor Cyan
            if ($LogFunction) {
                & $LogFunction -Message "Running mechanical QA with Qwen3-VL-8B..." -ImagePath $ImagePath
            }
            $mechanicalScore = Invoke-VisionQualityAssessment -ImagePath $ImagePath -ModelName $VisionModels["mechanical"] -AssessmentType "mechanical"
            if ($null -ne $mechanicalScore) {
                Write-Host "    [QA] Mechanical score: $([math]::Round($mechanicalScore, 1))/20" -ForegroundColor Green
                if ($LogFunction) {
                    & $LogFunction -Message "Mechanical QA score: $([math]::Round($mechanicalScore, 1))/20" -ImagePath $ImagePath
                }
            } else {
                Write-Host "    [QA] Mechanical assessment failed, using fallback" -ForegroundColor Yellow
            }
        }
        
        # Phase 3: Aesthetic scoring (LLaVA:13b) - only in full mode, loads, uses, then unloads
        $aestheticScore = $null
        if ($Depth -eq "full") {
            Write-Host "    [QA] Running aesthetic assessment (LLaVA:13b)..." -ForegroundColor Cyan
            if ($LogFunction) {
                & $LogFunction -Message "Running aesthetic assessment with LLaVA:13b..." -ImagePath $ImagePath
            }
            $aestheticScore = Invoke-VisionQualityAssessment -ImagePath $ImagePath -ModelName $VisionModels["aesthetic"] -AssessmentType "aesthetic"
            if ($null -ne $aestheticScore) {
                Write-Host "    [QA] Aesthetic score: $([math]::Round($aestheticScore, 1))/20" -ForegroundColor Green
                if ($LogFunction) {
                    & $LogFunction -Message "Aesthetic score: $([math]::Round($aestheticScore, 1))/20" -ImagePath $ImagePath
                }
            } else {
                Write-Host "    [QA] Aesthetic assessment failed, using mechanical score only" -ForegroundColor Yellow
            }
        }
        
        # Calculate final score.
        # IMPORTANT: never auto-approve when required vision models fail to load/score.
        # Old behavior defaulted to 18.0 (pass) if both VLMs failed — that hid bad assets.
        $script:LastQualityAssessment = @{
            Depth            = $Depth
            MechanicalScore  = $mechanicalScore
            AestheticScore   = $aestheticScore
            ModelsFailed     = $false
            Incomplete       = $false
            ImagePath        = $ImagePath
        }

        $finalScore = $null

        if ($null -ne $mechanicalScore -and $null -ne $aestheticScore) {
            # Weighted combination: 60% mechanical, 40% aesthetic
            $finalScore = ($mechanicalScore * 0.6 + $aestheticScore * 0.4)
            Write-Host "    [QA] Combined score: $([math]::Round($finalScore, 1))/20 (mechanical: $([math]::Round($mechanicalScore, 1)), aesthetic: $([math]::Round($aestheticScore, 1)))" -ForegroundColor Cyan
        } elseif ($null -ne $mechanicalScore) {
            $finalScore = $mechanicalScore
            if ($Depth -eq "full") {
                Write-Host "    [QA] Aesthetic model failed — using mechanical only (not an auto-approve)" -ForegroundColor Yellow
                $script:LastQualityAssessment.Incomplete = $true
            }
        } elseif ($null -ne $aestheticScore) {
            $finalScore = $aestheticScore
            Write-Host "    [QA] Mechanical model failed — using aesthetic only (not an auto-approve)" -ForegroundColor Yellow
            $script:LastQualityAssessment.Incomplete = $true
        } else {
            # Required VLM path produced no scores
            $script:LastQualityAssessment.ModelsFailed = $true
            $script:LastQualityAssessment.Incomplete = $true
            Write-Host "    [QA] FAIL: vision model(s) did not return scores — refusing auto-approve" -ForegroundColor Red
            if ($LogFunction) {
                & $LogFunction -Message "QA incomplete: required vision models failed to load/score" -ImagePath $ImagePath
            }
            return 0.0
        }

        if ($LogFunction) {
            & $LogFunction -Message "Final quality score: $([math]::Round($finalScore, 1))/20 (depth: $Depth)" -ImagePath $ImagePath
        }
        return $finalScore
        
    } catch {
        if ($LogFunction) {
            & $LogFunction -Message "Error in quality assessment: $_" -ImagePath $ImagePath
        }
        $script:LastQualityAssessment = @{
            Depth           = $Depth
            ModelsFailed    = $true
            Incomplete      = $true
            ImagePath       = $ImagePath
            Error           = "$_"
        }
        # Do NOT auto-approve on errors when AI QA was requested
        if ($Depth -in @("mechanical", "full")) {
            Write-Host "    [QA] FAIL: assessment error — refusing auto-approve ($_)" -ForegroundColor Red
            return 0.0
        }
        # fast-mode-only fallback: sanity dimensions if we still have them
        try {
            if ($width -ge 512 -and $height -ge 512) { return 18.0 }
            return 15.0
        } catch {
            return 5.0
        }
    }
}

function Get-LastQualityAssessmentMeta {
    <#
    .SYNOPSIS
    Returns metadata from the last Get-BestImageScore call (models failed / incomplete).
    #>
    if ($null -eq $script:LastQualityAssessment) {
        return $null
    }
    return [pscustomobject]$script:LastQualityAssessment
}

# Export functions
function Invoke-VisionQualityFeedback {
    <#
    .SYNOPSIS
    Ask a vision model what is wrong and how to fix it (for regenerate loops).
    #>
    param(
        [Parameter(Mandatory=$true)][string]$ImagePath,
        [Parameter(Mandatory=$true)][string]$ModelName,
        [Parameter(Mandatory=$true)][ValidateSet("mechanical", "aesthetic")][string]$AssessmentType,
        [string]$AssetContext = "game sprite / icon"
    )

    if (-not (Test-Path $ImagePath)) { return $null }

    try {
        $imageBytes = [System.IO.File]::ReadAllBytes($ImagePath)
        $imageBase64 = [Convert]::ToBase64String($imageBytes)

        if ($AssessmentType -eq "mechanical") {
            $prompt = @"
You are a technical art QA reviewer for $AssetContext.
List concrete defects (aliasing, artifacts, muddy edges, bad transparency, noise, broken silhouette, wrong scale).
Then give short fix instructions a Stable Diffusion regenerate pass should follow.
Format:
SCORE: <0-20>
ISSUES: <bullet-like short list>
FIX: <one concise regeneration brief>
"@
        } else {
            $prompt = @"
You are an aesthetic art director for $AssetContext.
Judge composition, readability, color harmony, polish, and game-art fit.
Then give short fix instructions for a regenerate pass.
Format:
SCORE: <0-20>
ISSUES: <bullet-like short list>
FIX: <one concise regeneration brief>
"@
        }

        $ollamaUrl = "http://localhost:11434/api/chat"
        $numGpu = 99
        try {
            if (Get-Command Get-GPUInfo -ErrorAction SilentlyContinue) {
                $gi = Get-GPUInfo
                if ($gi -and $gi.Available -and $gi.VRAMGB -gt 0 -and (Get-Command Get-OptimalGPULayers -ErrorAction SilentlyContinue)) {
                    $numGpu = Get-OptimalGPULayers -ModelName $ModelName -AvailableVRAMGB $gi.VRAMGB -PreferGPU
                }
            }
        } catch { }
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
            keep_alive = "1m"
            options = @{ num_gpu = $numGpu }
        } | ConvertTo-Json -Depth 10 -Compress

        $response = Invoke-RestMethod -Uri $ollamaUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 180
        Unload-OllamaModel -ModelName $ModelName

        if (-not ($response.message -and $response.message.content)) { return $null }
        $text = $response.message.content.Trim()
        $score = $null
        if ($text -match 'SCORE:\s*(\d+(?:\.\d+)?)') {
            $score = [Math]::Max(0.0, [Math]::Min(20.0, [double]$matches[1]))
        } elseif ($text -match '(\d+(?:\.\d+)?)') {
            $score = [Math]::Max(0.0, [Math]::Min(20.0, [double]$matches[1]))
        }
        $issues = $null
        if ($text -match 'ISSUES:\s*(.+?)(?:FIX:|$)') { $issues = $matches[1].Trim() }
        $fix = $null
        if ($text -match 'FIX:\s*(.+)$') { $fix = $matches[1].Trim() }

        return [pscustomobject]@{
            AssessmentType = $AssessmentType
            ModelName      = $ModelName
            Score          = $score
            Issues         = $issues
            Fix            = $fix
            Raw            = $text
        }
    } catch {
        Write-QualityLog -Message "Vision feedback error ($AssessmentType): $_" -ImagePath $ImagePath
        Unload-OllamaModel -ModelName $ModelName
        return $null
    }
}

function Get-ImageQualityReport {
    <#
    .SYNOPSIS
    Multi-module QA report: sanity + mechanical + aesthetic scores and fix guidance.
    Use this when a regenerate loop needs to know what to fix.
    #>
    param(
        [Parameter(Mandatory=$true)][string]$ImagePath,
        [ValidateSet("fast", "mechanical", "full")][string]$Depth = "full",
        [hashtable]$VisionModels = $script:VisionModels,
        [double]$PassThreshold = 15.0,
        [string]$AssetContext = "game sprite / icon"
    )

    $report = [ordered]@{
        ImagePath     = $ImagePath
        Depth         = $Depth
        PassThreshold = $PassThreshold
        Passed        = $false
        CombinedScore = 0.0
        SanityScore   = $null
        Mechanical    = $null
        Aesthetic     = $null
        FixBrief      = ""
        Issues        = @()
        ModelsFailed  = $false
        Incomplete    = $false
    }

    if (-not (Test-Path $ImagePath)) {
        $report.FixBrief = "Image missing; regenerate from draft."
        $report.Issues = @("file missing")
        return [pscustomobject]$report
    }

    # Numeric multi-tier score (existing path)
    $combined = Get-BestImageScore -ImagePath $ImagePath -Depth $Depth -VisionModels $VisionModels
    $report.CombinedScore = [double]$combined
    $meta = Get-LastQualityAssessmentMeta
    $report.ModelsFailed = [bool]($meta -and $meta.ModelsFailed)
    $report.Incomplete   = [bool]($meta -and $meta.Incomplete)

    if ($Depth -eq "fast") {
        $report.SanityScore = $combined
        $report.Passed = ($combined -ge $PassThreshold)
        if (-not $report.Passed) {
            $report.Issues += "failed sanity checks"
            $report.FixBrief = "Increase resolution/detail; ensure opaque readable silhouette on transparent background."
        }
        return [pscustomobject]$report
    }

    # If both (or required) vision models failed to load/score, never pass
    if ($report.ModelsFailed) {
        $report.Passed = $false
        $report.Issues += "vision QA models failed to load or return scores"
        $report.FixBrief = "QA models unavailable (mechanical/aesthetic). Ensure Ollama is running and models are pulled (qwen3-vl:8b, llava:13b), then regenerate and re-score. Do not treat this asset as approved."
        return [pscustomobject]$report
    }

    $mechModel = $VisionModels["mechanical"]
    $aesModel = $VisionModels["aesthetic"]

    if ($Depth -in @("mechanical", "full") -and $mechModel) {
        $report.Mechanical = Invoke-VisionQualityFeedback -ImagePath $ImagePath -ModelName $mechModel -AssessmentType mechanical -AssetContext $AssetContext
        if ($report.Mechanical -and $report.Mechanical.Issues) { $report.Issues += "mechanical: $($report.Mechanical.Issues)" }
        if ($report.Mechanical -and $report.Mechanical.Fix) { $report.FixBrief += "MECHANICAL FIX: $($report.Mechanical.Fix)`n" }
    }

    if ($Depth -eq "full" -and $aesModel) {
        $report.Aesthetic = Invoke-VisionQualityFeedback -ImagePath $ImagePath -ModelName $aesModel -AssessmentType aesthetic -AssetContext $AssetContext
        if ($report.Aesthetic -and $report.Aesthetic.Issues) { $report.Issues += "aesthetic: $($report.Aesthetic.Issues)" }
        if ($report.Aesthetic -and $report.Aesthetic.Fix) { $report.FixBrief += "AESTHETIC FIX: $($report.Aesthetic.Fix)`n" }
    }

    # Incomplete single-model results can still pass on score, but flag it
    $report.Passed = ($report.CombinedScore -ge $PassThreshold) -and (-not $report.ModelsFailed)
    if (-not $report.Passed -and [string]::IsNullOrWhiteSpace($report.FixBrief)) {
        $report.FixBrief = "Improve clarity, silhouette, and game-art readability; reduce artifacts; keep transparent background."
    }
    return [pscustomobject]$report
}

Export-ModuleMember -Function Get-BestImageScore, Invoke-VisionQualityAssessment, Invoke-VisionQualityFeedback, Get-ImageQualityReport, Get-LastQualityAssessmentMeta, Unload-OllamaModel, Write-QualityLog
