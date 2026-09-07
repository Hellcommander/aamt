# AI-Assisted Modding Tools (AAMT) - Caves of Qud Toolset
# PowerShell script to generate high-quality Space-Time Vortex assets using Ollama
# Usage: .\GenerateVortexAssets.ps1 -ModPath "Mod Path" [-QualityAssessmentDepth "full"] [-GenerateDesignDraft]
#
# Quality Assessment Depth:
#   - "fast": Sanity checks only (file exists, not empty, valid PNG)
#   - "mechanical": Uses Qwen3-VL-8B for mechanical quality checks
#   - "full": Uses both Qwen3-VL-8B and LLaVA:13b for complete quality assessment
#
# Design Drafts:
#   - Generate design draft/concept art first using SD3 (improves final asset quality)
#   - Enabled by default if SD3 is available
#   - Use -GenerateDesignDraft:$false to disable

param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("fast", "mechanical", "full")]
    [string]$QualityAssessmentDepth = "full",  # fast | mechanical | full — maps to Python --quality
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateDesignDraft,  # Generate design draft/concept art first using SD3 (requires SD3 server)

    [Parameter(Mandatory=$false)]
    [switch]$Interactive  # Wait for keypress at end; default off for unattended runs
)

function Test-InteractiveConsole {
    if ($env:CI -eq "true" -or $env:CI -eq "1") { return $false }
    if ($env:TF_BUILD -eq "True") { return $false }
    try {
        return [Environment]::UserInteractive -and $Host.Name -ne "Default Host"
    } catch {
        return $false
    }
}

function Wait-OptionalKeyPress {
    if ($Interactive -and (Test-InteractiveConsole)) {
        Write-Host "Press any key to exit..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration (optional)
# Path calculation: Tools\Qud -> Tools\Shared (one level up from script directory)
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
$toolsetIntegrationAvailable = $false
$tools = $null

try {
    $toolDetectionPath = Join-Path $sharedPath "ToolDetection.psm1"
    $toolsetIntegrationPath = Join-Path $sharedPath "ToolsetIntegration.psm1"
    
    # Import modules if they exist (matching Starbound script approach)
    if (Test-Path $toolDetectionPath) {
        Import-Module $toolDetectionPath -ErrorAction SilentlyContinue -Force
    }
    if (Test-Path $toolsetIntegrationPath) {
        Import-Module $toolsetIntegrationPath -ErrorAction SilentlyContinue -Force
    }
    
    # Check if function is available after import
    if (Get-Command Initialize-ToolsetTools -ErrorAction SilentlyContinue) {
        $toolsetIntegrationAvailable = $true
        $tools = Initialize-ToolsetTools `
            -RequiredTools @("Ollama", "Python") `
            -OptionalTools @("ImageMagick")
    } else {
        $toolsetIntegrationAvailable = $false
    }
} catch {
    $toolsetIntegrationAvailable = $false
    # Silently fall back to manual detection - this is expected if modules aren't available
}

# Import Stable Diffusion integration if available (for design drafts)
$sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"
$script:SD3Available = $false
if (Test-Path $sdModule) {
    try {
        Import-Module $sdModule -DisableNameChecking -ErrorAction Stop
        $script:SD3Available = $true
    } catch {
        $script:SD3Available = $false
    }
}

# Import quality assessment module if available
$qualityModule = Join-Path $sharedPath "ImageQualityAssessment.psm1"
$script:QualityAssessmentAvailable = $false
if (Test-Path $qualityModule) {
    try {
        Import-Module $qualityModule -DisableNameChecking -ErrorAction Stop
        if (Get-Command Get-BestImageScore -ErrorAction SilentlyContinue) {
            $script:QualityAssessmentAvailable = $true
            Write-Host "[OK] Quality assessment module loaded" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Quality assessment module loaded but Get-BestImageScore not found" -ForegroundColor Yellow
        }
    } catch {
        $script:QualityAssessmentAvailable = $false
        Write-Host "[WARN] Failed to import quality assessment module: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "[INFO] Quality assessment module not found at: $qualityModule" -ForegroundColor Gray
}

# Change to script directory
Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Space-Time Vortex Asset Generator (Ollama REQUIRED)" -ForegroundColor Cyan
Write-Host "AI-Assisted Modding Tools (AAMT)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Mod Path: $ModPath"
Write-Host ""

# Verify required tools (using toolset integration if available, otherwise manual check)
$ollamaAvailable = $false
$pythonAvailable = $false

if ($toolsetIntegrationAvailable -and $tools) {
    # Use toolset integration
    if (-not $tools.AllRequiredAvailable) {
        Write-Host "ERROR: Missing required tools for Vortex asset generation" -ForegroundColor Red
        if (Get-Command Show-ToolsetStatus -ErrorAction SilentlyContinue) {
            Show-ToolsetStatus -ToolsetName "Caves of Qud - Vortex Generator" `
                -RequiredTools @("Ollama", "Python") `
                -OptionalTools @("ImageMagick")
        }
        exit 1
    }
    
    $ollamaAvailable = $tools.Tools["Ollama"].Available
    $pythonAvailable = $tools.Tools["Python"].Available
    
    if ($ollamaAvailable) {
        Write-Host "[OK] Ollama is available" -ForegroundColor Green
        Write-Host "     Path: $($tools.Tools['Ollama'].Path)" -ForegroundColor Gray
        if ($tools.Tools["Ollama"].Version) {
            Write-Host "     Version: $($tools.Tools['Ollama'].Version)" -ForegroundColor Gray
        }
        Write-Host ""
    }
} else {
    # Manual tool detection
    Write-Host "Checking required tools..." -ForegroundColor Gray
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0 -or $pythonVersion -match "Python") {
            $pythonAvailable = $true
            Write-Host "[OK] Python is available" -ForegroundColor Green
            Write-Host "     Version: $pythonVersion" -ForegroundColor Gray
        }
    } catch {
        $pythonAvailable = $false
    }
    
    # Check Ollama
    try {
        $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        $ollamaAvailable = $true
        Write-Host "[OK] Ollama is available" -ForegroundColor Green
        Write-Host "     URL: http://localhost:11434" -ForegroundColor Gray
    } catch {
        $ollamaAvailable = $false
    }
    
    Write-Host ""
}

# Verify Ollama is available (required)
if (-not $ollamaAvailable) {
    Write-Host "[ERROR] Ollama is not available!" -ForegroundColor Red
    Write-Host "        Please start Ollama: ollama serve" -ForegroundColor Yellow
    Write-Host "        Verify it's running: curl http://localhost:11434/api/tags" -ForegroundColor Yellow
    Write-Host ""
    Wait-OptionalKeyPress
    exit 1
}

# Verify Python is available (required)
if (-not $pythonAvailable) {
    Write-Host "[ERROR] Python is not available!" -ForegroundColor Red
    Write-Host "        Please install Python 3.x and ensure it's in PATH" -ForegroundColor Yellow
    Write-Host ""
    Wait-OptionalKeyPress
    exit 1
}

# Use Ollama integration if available
if (Get-Command Use-OllamaIfAvailable -ErrorAction SilentlyContinue) {
    Use-OllamaIfAvailable | Out-Null
}

# Generate design drafts if enabled and SD3 is available (enabled by default if SD3 available)
$shouldGenerateDraft = if ($PSBoundParameters.ContainsKey("GenerateDesignDraft")) { $GenerateDesignDraft } else { $true }
if ($shouldGenerateDraft -and $script:SD3Available) {
    Write-Host ""
    Write-Host "Step 0: Generating design drafts/concept art with SD3..." -ForegroundColor Yellow
    Write-Host "  (Design drafts improve final asset quality by providing visual reference)" -ForegroundColor Gray
    # Prefer CUDA/VRAM — older vortex runs often spilled to CPU and pegged host cores.
    if (Get-Command Set-StableDiffusionGpuPreferredEnv -ErrorAction SilentlyContinue) {
        Set-StableDiffusionGpuPreferredEnv -Offload gpu -Force
    } else {
        $env:SD_OFFLOAD = "gpu"
        $env:SD_HEADROOM_GB = "0"
        $env:SD_SKIP_T5 = "1"
    }
    
    # Check if SD3 server is available (like Starbound generator does)
    if (Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue) {
        $connectionTest = Test-StableDiffusionConnection
        if ($connectionTest) {
            Write-Host "  [OK] SD3 server connection verified" -ForegroundColor Green
            if (Get-Command Assert-StableDiffusionUsesGpu -ErrorAction SilentlyContinue) {
                Assert-StableDiffusionUsesGpu | Out-Null
            }
            
            # Verify module variables are set correctly (debug check)
            if (Get-Command Find-LocalStableDiffusionServer -ErrorAction SilentlyContinue) {
                $serverInfo = Find-LocalStableDiffusionServer
                if ($serverInfo -is [hashtable] -and $serverInfo.ContainsKey("BaseUrl")) {
                    Write-Host "  [OK] SD3 server URL: $($serverInfo.BaseUrl)" -ForegroundColor Gray
                }
            }
            
            # Create design drafts directory
            $designDraftsDir = Join-Path $ModPath "DesignDrafts"
            if (-not (Test-Path $designDraftsDir)) {
                New-Item -ItemType Directory -Path $designDraftsDir -Force | Out-Null
            }
            
            # Generate design drafts for main assets
            $draftAssets = @(
                @{Name="Space-Time Vortex Icon"; Type="icon"; Prompt="Caves of Qud mutation icon, space-time vortex, spiral singularity, blue-purple mental mutation aesthetic, pixel art style, 1024x1024 concept art"},
                @{Name="Black Hole"; Type="black_hole"; Prompt="Caves of Qud space-time vortex black hole, dark center, spiral accretion disk, space-time distortion, ominous dark blue-black colors, pixel art style, 1024x1024 concept art"},
                @{Name="White Hole"; Type="white_hole"; Prompt="Caves of Qud space-time rupture white hole, explosive energy burst, radiating rays, bright white-yellow-orange colors, pixel art style, 1024x1024 concept art"}
            )
            
            foreach ($asset in $draftAssets) {
                $designDraftFile = Join-Path $designDraftsDir "$($asset.Type)_design_draft.png"
                Write-Host "  Generating design draft: $($asset.Name)..." -ForegroundColor Gray
                
                try {
                    if (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue) {
                        # Ensure server detection is fresh before each call
                        # This should set $script:StableDiffusionApiUrl correctly
                        $null = Test-StableDiffusionConnection -ErrorAction SilentlyContinue
                        
                        # Verify URL is set correctly (debug)
                        if (Get-Command Find-LocalStableDiffusionServer -ErrorAction SilentlyContinue) {
                            $serverCheck = Find-LocalStableDiffusionServer -ErrorAction SilentlyContinue
                            if ($serverCheck -is [hashtable] -and $serverCheck.ContainsKey("BaseUrl")) {
                                $expectedUrl = "$($serverCheck.BaseUrl)$($serverCheck.ApiEndpoint)"
                                Write-Host "    [DEBUG] Expected API URL: $expectedUrl" -ForegroundColor DarkGray
                            }
                        }
                        
                        $sd3Params = @{
                            Prompt = $asset.Prompt
                            OutputPath = $designDraftFile
                            NegativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark"
                            Width = 1024
                            Height = 1024
                            Steps = 28
                            GuidanceScale = 7.0
                            EnhanceWithOllama = $true
                            AutoStartServer = $true
                        }
                        
                        Write-Host "    Calling Generate-AssetImageWithSD3..." -ForegroundColor Gray
                        $draftResult = Generate-AssetImageWithSD3 @sd3Params
                        
                        if ($draftResult -and (Test-Path $designDraftFile)) {
                            Write-Host "    [OK] Design draft created: $(Split-Path -Leaf $designDraftFile)" -ForegroundColor Green
                            
                            # Assess quality if enabled
                            if ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -ne "fast") {
                                if (Get-Command Get-BestImageScore -ErrorAction SilentlyContinue) {
                                    try {
                                        $draftScore = Get-BestImageScore -ImagePath $designDraftFile -Depth $QualityAssessmentDepth
                                        Write-Host "    Design draft quality: $([math]::Round($draftScore, 1))/20" -ForegroundColor $(if ($draftScore -ge 15.0) { "Green" } else { "Yellow" })
                                    } catch {
                                        Write-Host "    [WARN] Could not assess draft quality: $_" -ForegroundColor Yellow
                                    }
                                }
                            }
                        } else {
                            Write-Host "    [WARN] Design draft generation failed, continuing without reference" -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "    [WARN] SD3 generation function not available" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "    [WARN] Design draft generation error: $_" -ForegroundColor Yellow
                    Write-Host "           Continuing without design draft..." -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "  [INFO] SD3 server not available, skipping design draft" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [INFO] SD3 integration not available, skipping design draft" -ForegroundColor Gray
    }
    Write-Host ""
} elseif ($shouldGenerateDraft -and -not $script:SD3Available) {
    Write-Host ""
    Write-Host "[INFO] Design draft generation skipped: SD3 integration not available" -ForegroundColor Gray
    Write-Host ""
}

# Run the Python script
Write-Host "Starting asset generation..." -ForegroundColor Cyan
Write-Host ""

try {
    $qualityArg = if ($QualityAssessmentDepth -eq "fast") { "fast" } else { "full" }
    python generate_vortex_professional.py "$ModPath" --quality $qualityArg
    $pythonExitCode = $LASTEXITCODE
    
    # Run quality assessment even if there were partial errors (non-zero exit code)
    # The Python script may complete with errors but still generate some assets
    $shouldAssessQuality = $true
    
    if ($pythonExitCode -eq 0) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "Asset generation complete!" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host "Asset generation completed with errors (exit code: $pythonExitCode)" -ForegroundColor Yellow
        Write-Host "  Some assets may still have been generated" -ForegroundColor Gray
        Write-Host "============================================================" -ForegroundColor Yellow
    }

    # Bridge Textures/ -> Assets/Resources + .meta (Editor not required)
    $bridge = Join-Path $PSScriptRoot "export_textures_to_unity.py"
    if (Test-Path $bridge) {
        Write-Host ""
        Write-Host "Unity texture export (.meta)..." -ForegroundColor Cyan
        python $bridge --mod $ModPath
    }

    $sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
    Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -Force -ErrorAction SilentlyContinue
    if ((Get-Command Invoke-AamtUnityAssetBundles -ErrorAction SilentlyContinue) -and
        (Test-Path (Join-Path $ModPath "Assets"))) {
        $qudGame = if ($env:QUD_GAME_ROOT) { $env:QUD_GAME_ROOT } else { "E:\SteamLibrary\steamapps\common\Caves of Qud" }
        Write-Host "Attempting AssetBundle build with matching Unity Editor..." -ForegroundColor Cyan
        [void](Invoke-AamtUnityAssetBundles -ProjectPath $ModPath -GameRoot $qudGame -EnsureProject)
    }
    
    # Quality assessment if enabled (run even if there were errors)
    if ($shouldAssessQuality) {
        Write-Host ""
        Write-Host "Quality Assessment Status:" -ForegroundColor Cyan
        Write-Host "  Module Available: $script:QualityAssessmentAvailable" -ForegroundColor $(if ($script:QualityAssessmentAvailable) { "Green" } else { "Yellow" })
        Write-Host "  Assessment Depth: $QualityAssessmentDepth" -ForegroundColor Gray
        Write-Host ""
        
        if ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -ne "fast") {
            Write-Host "Assessing quality of generated assets..." -ForegroundColor Cyan
            Write-Host "  Assessment Depth: $QualityAssessmentDepth" -ForegroundColor Gray
            Write-Host "  Quality Assessment Module: Available" -ForegroundColor Green
            
            # Find all generated PNG images (search in last 10 minutes to catch recently generated files)
            $texturesPath = Join-Path $ModPath "Textures"
            $visualsPath = Join-Path $ModPath "Visuals"
            $searchStartTime = (Get-Date).AddMinutes(-10)
            
            Write-Host "  Searching for generated images..." -ForegroundColor Gray
            Write-Host "    Textures path: $texturesPath" -ForegroundColor Gray
            Write-Host "    Visuals path: $visualsPath" -ForegroundColor Gray
            Write-Host "    Search window: Last 10 minutes (since $($searchStartTime.ToString('HH:mm:ss')))" -ForegroundColor Gray
            
            $generatedImages = @()
            if (Test-Path $texturesPath) {
                $textureImages = Get-ChildItem -Path $texturesPath -Filter "*.png" -Recurse -ErrorAction SilentlyContinue
                $generatedImages += $textureImages
                Write-Host "    Found $($textureImages.Count) PNG file(s) in Textures/" -ForegroundColor Gray
            } else {
                Write-Host "    [WARN] Textures path does not exist: $texturesPath" -ForegroundColor Yellow
            }
            if (Test-Path $visualsPath) {
                $visualImages = Get-ChildItem -Path $visualsPath -Filter "*.png" -Recurse -ErrorAction SilentlyContinue
                $generatedImages += $visualImages
                Write-Host "    Found $($visualImages.Count) PNG file(s) in Visuals/" -ForegroundColor Gray
            } else {
                Write-Host "    [WARN] Visuals path does not exist: $visualsPath" -ForegroundColor Yellow
            }
            
            # Filter to recently modified files (within search window) or all if none found
            $recentImages = $generatedImages | Where-Object { $_.LastWriteTime -gt $searchStartTime }
            if ($recentImages.Count -gt 0) {
                $generatedImages = $recentImages
                Write-Host "    Filtered to $($generatedImages.Count) recently modified file(s)" -ForegroundColor Gray
            } else {
                Write-Host "    [INFO] No files modified in last 10 minutes, assessing all found images" -ForegroundColor Gray
            }
            
            # Remove duplicates (same file might be in both directories)
            $generatedImages = $generatedImages | Sort-Object FullName -Unique
            
            if ($generatedImages.Count -gt 0) {
                Write-Host "  Found $($generatedImages.Count) generated image(s) to assess" -ForegroundColor Green
                $lowQualityImages = @()
                $assessedCount = 0
                $retryCount = 0
                $maxRetries = 1  # Allow one retry for low-quality assets
                
                foreach ($image in $generatedImages) {
                    if (Get-Command Get-BestImageScore -ErrorAction SilentlyContinue) {
                        Write-Host "    Assessing: $($image.Name)..." -ForegroundColor Gray
                        try {
                            $score = Get-BestImageScore -ImagePath $image.FullName -Depth $QualityAssessmentDepth
                            $assessedCount++
                            
                            if ($score -lt 15.0) {
                                Write-Host "      [WARN] Low quality detected: $($image.Name) (score: $([math]::Round($score, 1))/20)" -ForegroundColor Yellow
                                $lowQualityImages += $image
                                
                                # Auto-retry for low-quality assets
                                if ($retryCount -lt $maxRetries) {
                                    Write-Host "      [INFO] Attempting to regenerate low-quality asset..." -ForegroundColor Cyan
                                    $retryCount++
                                    
                                    # Determine asset type from filename for targeted regeneration
                                    $assetType = "unknown"
                                    if ($image.Name -match "icon") { $assetType = "icon" }
                                    elseif ($image.Name -match "BlackHole") { $assetType = "black_hole" }
                                    elseif ($image.Name -match "WhiteHole") { $assetType = "white_hole" }
                                    elseif ($image.Name -match "Particle") { $assetType = "particle" }
                                    elseif ($image.Name -match "Distortion") { $assetType = "distortion" }
                                    elseif ($image.Name -match "Ability") { $assetType = "ability" }
                                    elseif ($image.Name -match "Warning") { $assetType = "warning" }
                                    
                                    # Note: Full regeneration would require re-running the Python script
                                    # For now, we just report the low quality
                                    Write-Host "      [INFO] Regeneration would require full asset generation run" -ForegroundColor Gray
                                    Write-Host "      [INFO] Consider re-running with different AI prompts or parameters" -ForegroundColor Gray
                                }
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
                
                Write-Host ""
                Write-Host "Quality assessment complete: $assessedCount/$($generatedImages.Count) images assessed" -ForegroundColor Cyan
                
                if ($lowQualityImages.Count -gt 0) {
                    Write-Host "  [WARN] $($lowQualityImages.Count) image(s) failed quality assessment (score < 15.0)" -ForegroundColor Yellow
                    Write-Host "    Consider regenerating these assets:" -ForegroundColor Gray
                    foreach ($img in $lowQualityImages) {
                        Write-Host "      - $($img.Name)" -ForegroundColor Gray
                    }
                    Write-Host ""
                    Write-Host "    To regenerate, re-run this script with the same parameters." -ForegroundColor Gray
                } else {
                    Write-Host "  [OK] All assessed images passed quality check" -ForegroundColor Green
                }
            } else {
                Write-Host "  [WARN] No generated images found for quality assessment" -ForegroundColor Yellow
            }
        } elseif ($script:QualityAssessmentAvailable -and $QualityAssessmentDepth -eq "fast") {
            Write-Host ""
            Write-Host "Quality assessment skipped: Depth is 'fast' (sanity checks only, no AI models)" -ForegroundColor Gray
            Write-Host "  To enable quality assessment, use: -QualityAssessmentDepth 'mechanical' or 'full'" -ForegroundColor Gray
        } elseif (-not $script:QualityAssessmentAvailable) {
            Write-Host ""
            Write-Host "Quality assessment skipped: ImageQualityAssessment module not available" -ForegroundColor Yellow
            Write-Host "  Module path checked: $qualityModule" -ForegroundColor Gray
            if (-not (Test-Path $qualityModule)) {
                Write-Host "  [INFO] Module file not found at expected location" -ForegroundColor Gray
            }
        } else {
            Write-Host ""
            Write-Host "Quality assessment skipped: Unknown reason" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "Quality assessment skipped: Unknown reason" -ForegroundColor Yellow
    }
    
    # Set exit code based on Python result
    if ($pythonExitCode -ne 0) {
        Write-Host ""
        Write-Host "============================================================" -ForegroundColor Yellow
        Write-Host "WARNING: Generation completed with errors (exit code: $pythonExitCode)" -ForegroundColor Yellow
        Write-Host "  Check the error messages above for details" -ForegroundColor Gray
        Write-Host "============================================================" -ForegroundColor Yellow
        exit $pythonExitCode
    }
    
} catch {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "ERROR: Asset generation failed!" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure Ollama is running: ollama serve" -ForegroundColor Gray
    Write-Host "  2. Check that required models are installed" -ForegroundColor Gray
    Write-Host "  3. Verify the mod path is correct" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Wait-OptionalKeyPress
