#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Space Whale Complete Asset Generator - Uses Control Room GUI for progress tracking
    
.DESCRIPTION
    Generates all required assets for Space Whale ship:
    - Visual Language (color palettes, materials, textures)
    - FX Assets (Nova Drift style effects)
    - Audio Assets (EM/Plasma/Acoustic/Mechanical channels)
    - Ship Spritesheet (120 facings)
    - Skinning/Rigging assets
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir,
    
    [Parameter(Mandatory=$false)]
    [string]$ShipId,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipVisualLanguage,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipFX,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipAudio,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSpritesheet,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseControlRoom
)

# Set error handling - continue on errors but log them
$ErrorActionPreference = "Continue"
$WarningPreference = "Continue"

# Suppress common non-critical errors
$PSDefaultParameterValues['*:ErrorAction'] = 'SilentlyContinue'

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Trap all errors to prevent script from exiting
trap {
    Write-Host "  [WARNING] Error caught: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  Continuing execution..." -ForegroundColor Gray
    continue
}

# Load settings from JSON file
$settingsFile = Join-Path $PSScriptRoot "SpaceWhaleAssetGenerator_Settings.json"
$script:Settings = $null

function Load-Settings {
    <#
    .SYNOPSIS
        Loads settings from JSON file, with fallback to defaults
    #>
    try {
        if (Test-Path $settingsFile) {
            try {
                $script:Settings = Get-Content $settingsFile -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue
                if ($script:Settings) {
                    Write-Host "Loaded settings from: $settingsFile" -ForegroundColor Gray
                    return $true
                }
            } catch {
                # Silently use defaults
            }
        }
    } catch {
        # Silently use defaults
    }
    return $false
}

# Load settings (will create defaults if file doesn't exist)
Load-Settings | Out-Null

# Get default value from settings or use parameter default
function Get-Setting {
    param(
        [string]$Key,
        [object]$DefaultValue
    )
    if ($script:Settings -and $script:Settings.defaults -and $script:Settings.defaults.$Key) {
        return $script:Settings.defaults.$Key
    }
    return $DefaultValue
}

# Import model router functions for dual-model support
function Get-CodeModel {
    <#
    .SYNOPSIS
        Gets the code model (CodeLlama-34B) from settings or dual-model router for code/XML tasks
    #>
    # Check settings first
    if ($script:Settings -and $script:Settings.models -and 
        -not [string]::IsNullOrWhiteSpace($script:Settings.models.codeModel)) {
        return $script:Settings.models.codeModel
    }
    
    # Use router if enabled
    $useRouter = if ($script:Settings -and $script:Settings.models) {
        $script:Settings.models.useDualModelRouter
    } else {
        $true  # Default to using router
    }
    
    if ($useRouter) {
        $routerScript = Join-Path (Join-Path $PSScriptRoot "..") "Common\ollama_model_router.py"
        if (Test-Path $routerScript) {
            try {
                $result = python $routerScript -c "from ollama_model_router import get_code_model; print(get_code_model())" 2>&1 | Out-String
                if ($result -and $result.Trim()) {
                    $trimmed = $result.Trim()
                    if ($trimmed -and -not $trimmed.StartsWith("Error") -and -not $trimmed.StartsWith("Traceback")) {
                        return $trimmed
                    }
                }
            } catch {
                # Fallback if router fails - silently continue
            }
        }
    }
    
    return "codellama:34b"  # Fallback
}

function Get-VisualModel {
    <#
    .SYNOPSIS
        Gets the visual model (WizardLM) from settings or dual-model router for visual tasks
    #>
    # Check settings first
    if ($script:Settings -and $script:Settings.models -and 
        -not [string]::IsNullOrWhiteSpace($script:Settings.models.visualModel)) {
        return $script:Settings.models.visualModel
    }
    
    # Use router if enabled
    $useRouter = if ($script:Settings -and $script:Settings.models) {
        $script:Settings.models.useDualModelRouter
    } else {
        $true  # Default to using router
    }
    
    if ($useRouter) {
        $routerScript = Join-Path (Join-Path $PSScriptRoot "..") "Common\ollama_model_router.py"
        if (Test-Path $routerScript) {
            try {
                $result = python $routerScript -c "from ollama_model_router import get_visual_model; print(get_visual_model())" 2>&1 | Out-String
                if ($result -and $result.Trim()) {
                    $trimmed = $result.Trim()
                    if ($trimmed -and -not $trimmed.StartsWith("Error") -and -not $trimmed.StartsWith("Traceback")) {
                        return $trimmed
                    }
                }
            } catch {
                # Fallback if router fails - silently continue
            }
        }
    }
    
    return "wizardlm-uncensored:latest"  # Fallback
}

function Get-XMLModel {
    <#
    .SYNOPSIS
        Gets the XML model from settings or dual-model router for XML generation tasks
    #>
    # Check settings first
    if ($script:Settings -and $script:Settings.models -and 
        -not [string]::IsNullOrWhiteSpace($script:Settings.models.xmlModel)) {
        return $script:Settings.models.xmlModel
    }
    
    # XML tasks use code model by default
    return Get-CodeModel
}

function Get-AudioModel {
    <#
    .SYNOPSIS
        Gets the audio model from settings or dual-model router for audio generation tasks
    #>
    # Check settings first
    if ($script:Settings -and $script:Settings.models -and 
        -not [string]::IsNullOrWhiteSpace($script:Settings.models.audioModel)) {
        return $script:Settings.models.audioModel
    }
    
    # Audio tasks use visual model by default
    return Get-VisualModel
}

# Apply settings defaults if parameters not provided
if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
    $RegistryPath = Get-Setting "registryPath" "space_whale_ship_example.json"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Get-Setting "outputDir" "Output/SpaceWhaleAssets"
}
if ([string]::IsNullOrWhiteSpace($ShipId)) {
    $ShipId = Get-Setting "shipId" ""
}
if ([string]::IsNullOrWhiteSpace($OllamaModel)) {
    $OllamaModel = Get-Setting "ollamaModel" ""
    # Auto-detect model if still empty (use visual model as default for general tasks)
    if ([string]::IsNullOrWhiteSpace($OllamaModel)) {
        $OllamaModel = Get-VisualModel
        Write-Host "Using auto-detected visual model: $OllamaModel" -ForegroundColor Cyan
    }
}
# Apply switch defaults from settings
if (-not $PSBoundParameters.ContainsKey('UseControlRoom')) {
    $UseControlRoom = Get-Setting "useControlRoom" $false
}
if (-not $PSBoundParameters.ContainsKey('SkipVisualLanguage')) {
    $SkipVisualLanguage = Get-Setting "skipVisualLanguage" $false
}
if (-not $PSBoundParameters.ContainsKey('SkipFX')) {
    $SkipFX = Get-Setting "skipFX" $false
}
if (-not $PSBoundParameters.ContainsKey('SkipAudio')) {
    $SkipAudio = Get-Setting "skipAudio" $false
}
if (-not $PSBoundParameters.ContainsKey('SkipSpritesheet')) {
    $SkipSpritesheet = Get-Setting "skipSpritesheet" $false
}

Write-Host "Space Whale Complete Asset Generator" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Registry: $RegistryPath" -ForegroundColor Gray
Write-Host "  Output: $OutputDir" -ForegroundColor Gray
Write-Host "  Ship ID: $(if ([string]::IsNullOrWhiteSpace($ShipId)) { 'All ships' } else { $ShipId })" -ForegroundColor Gray
Write-Host "  Model: $OllamaModel" -ForegroundColor Gray
Write-Host "  Control Room: $UseControlRoom" -ForegroundColor Gray
Write-Host ""
Write-Host "Tasks to run:" -ForegroundColor Yellow
Write-Host "  Visual Language: $(if ($SkipVisualLanguage) { 'SKIPPED' } else { 'ENABLED' })" -ForegroundColor $(if ($SkipVisualLanguage) { 'Gray' } else { 'Green' })
Write-Host "  FX Assets: $(if ($SkipFX) { 'SKIPPED' } else { 'ENABLED' })" -ForegroundColor $(if ($SkipFX) { 'Gray' } else { 'Green' })
Write-Host "  Audio Assets: $(if ($SkipAudio) { 'SKIPPED' } else { 'ENABLED' })" -ForegroundColor $(if ($SkipAudio) { 'Gray' } else { 'Green' })
Write-Host "  Spritesheet: $(if ($SkipSpritesheet) { 'SKIPPED' } else { 'ENABLED' })" -ForegroundColor $(if ($SkipSpritesheet) { 'Gray' } else { 'Green' })
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Check for Control Room Monitor (WPF-based with job cards)
$controlRoomPath = Join-Path $PSScriptRoot "AssetGeneratorControlRoom_Monitor.ps1"
$useGUI = $UseControlRoom -or (Test-Path $controlRoomPath)

if ($useGUI) {
    Write-Host "Launching Control Room Monitor GUI for progress tracking..." -ForegroundColor Green
    Write-Host ""
    
    # Get advanced settings for Control Room Monitor
    $watchDir = if ($script:Settings -and $script:Settings.advanced -and 
                     -not [string]::IsNullOrWhiteSpace($script:Settings.advanced.controlRoomWatchDirectory)) {
        $script:Settings.advanced.controlRoomWatchDirectory
    } else {
        $OutputDir
    }
    
    $maxCores = if ($script:Settings -and $script:Settings.advanced) { 
        $script:Settings.advanced.controlRoomMaxCores 
    } else { 
        32 
    }
    
    # Launch Control Room Monitor (WPF-based with job cards and live previews)
    $controlRoomArgs = @(
        "-STA",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$controlRoomPath`"",
        "-WatchDirectory", $watchDir,
        "-MaxCores", $maxCores
    )
    
    Start-Process powershell -ArgumentList $controlRoomArgs -WindowStyle Normal
    
    Write-Host "Control Room Monitor launched!" -ForegroundColor Green
    Write-Host "  - Watch progress in the GUI window" -ForegroundColor Gray
    Write-Host "  - Preview assets as they're generated" -ForegroundColor Gray
    Write-Host "  - View job cards for each asset type" -ForegroundColor Gray
    Write-Host ""
    Start-Sleep -Seconds 2
}

# Check if we should use comprehensive generator (uses Ollama)
$comprehensiveScript = Join-Path $PSScriptRoot "space_whale_comprehensive_asset_generator.py"
$useComprehensive = Test-Path $comprehensiveScript

if ($useComprehensive) {
    Write-Host "Using Comprehensive Asset Generator (with Ollama AI)" -ForegroundColor Green
    Write-Host "  This will generate 150 variations using AI models" -ForegroundColor Gray
    Write-Host "  Ollama will be used (you'll see multithreaded activity)" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if Ollama is running
    Write-Host "Checking Ollama connection..." -ForegroundColor Yellow
    try {
        $ollamaCheck = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($ollamaCheck -and $ollamaCheck.StatusCode -eq 200) {
            Write-Host "  [OK] Ollama is running and accessible" -ForegroundColor Green
            try {
                $models = ($ollamaCheck.Content | ConvertFrom-Json).models
                Write-Host "  Available models: $($models.Count)" -ForegroundColor Gray
                foreach ($model in $models | Select-Object -First 3) {
                    Write-Host "    - $($model.name)" -ForegroundColor Gray
                }
                if ($models.Count -gt 3) {
                    Write-Host "    ... and $($models.Count - 3) more" -ForegroundColor Gray
                }
            } catch {
                Write-Host "  [WARNING]  Warning: Could not parse Ollama response" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  [WARNING]  Warning: Ollama not accessible at http://localhost:11434" -ForegroundColor Yellow
            Write-Host "  Generation will use fallback methods" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  [WARNING]  Warning: Ollama not accessible at http://localhost:11434" -ForegroundColor Yellow
        Write-Host "  Generation will use fallback methods" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Build arguments for comprehensive generator
    $compArgs = @()
    
    # Pass output directory
    $compArgs += "--output-dir", $OutputDir
    
    # Pass model if specified
    if (-not [string]::IsNullOrWhiteSpace($OllamaModel)) {
        $compArgs += "--ollama-model", $OllamaModel
        Write-Host "Using specified model: $OllamaModel" -ForegroundColor Cyan
    } else {
        Write-Host "Using auto-detected models (via dual-model router)" -ForegroundColor Cyan
        Write-Host "  - Code tasks: CodeLlama-34B (if available)" -ForegroundColor Gray
        Write-Host "  - Visual tasks: WizardLM (if available)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Run comprehensive generator
    Write-Host "Starting comprehensive generation..." -ForegroundColor Yellow
    Write-Host "  Script: $comprehensiveScript" -ForegroundColor Gray
    if ($compArgs.Count -gt 0) {
        Write-Host "  Args: $($compArgs -join ' ')" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "NOTE: Ollama will show multithreaded activity when generating variations" -ForegroundColor Cyan
    Write-Host "      You can monitor CPU/network usage to confirm Ollama is working" -ForegroundColor Gray
    Write-Host ""
    
    try {
        $output = & python $comprehensiveScript @compArgs 2>&1
        $exitCode = $LASTEXITCODE
        
        # Filter out common Python warnings/errors that aren't critical
        if ($output) {
            $filteredOutput = $output | Where-Object { 
                $_ -notmatch "^\s*$" -and 
                $_ -notmatch "^WARNING:" -and
                $_ -notmatch "^UserWarning:" -and
                $_ -notmatch "^DeprecationWarning:" -and
                $_ -notmatch "^Traceback" -and
                $_ -notmatch "^\s*File " -and
                $_ -notmatch "^\s*line \d+"
            }
            if ($filteredOutput) {
                Write-Host $filteredOutput
            }
        }
        
        if ($exitCode -eq 0 -or $exitCode -eq $null) {
            Write-Host ""
            Write-Host "====================================" -ForegroundColor Cyan
            Write-Host "Comprehensive Generation Complete!" -ForegroundColor Green
            Write-Host "====================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Generated assets with AI assistance:" -ForegroundColor Yellow
            Write-Host "  - 150 Visual Language variations (via Ollama)" -ForegroundColor Gray
            Write-Host "  - 150 FX Asset variations" -ForegroundColor Gray
            Write-Host "  - Quality reports and assessments" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan
            
            # Check what was generated
            $outputPath = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
            if ($outputPath) {
                $files = Get-ChildItem -Path $outputPath -Recurse -File -ErrorAction SilentlyContinue
                if ($files) {
                    Write-Host ""
                    Write-Host "Generated files: $($files.Count) total" -ForegroundColor Green
                }
            }
        } else {
            Write-Host ""
            Write-Host "====================================" -ForegroundColor Cyan
            Write-Host "Generation Failed (Exit Code: $exitCode)" -ForegroundColor Red
            Write-Host "====================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Check the error messages above for details." -ForegroundColor Yellow
            Write-Host "Continuing with fallback generators..." -ForegroundColor Gray
            Write-Host ""
        }
    } catch {
        Write-Host ""
        Write-Host "[WARNING]  Warning: Comprehensive generator failed: $_" -ForegroundColor Yellow
        Write-Host "Continuing with fallback generators..." -ForegroundColor Gray
        Write-Host ""
        # Don't exit - continue with fallback
    }
    
    # Only exit if comprehensive generator succeeded
    if ($exitCode -eq 0) {
        exit 0
    }
    # Otherwise continue with fallback generators below
}

# Fallback to individual generators (if comprehensive generator not available)
Write-Host "Comprehensive generator not found, using individual generators..." -ForegroundColor Yellow
Write-Host "  Note: Individual generators may not use Ollama AI" -ForegroundColor Gray
Write-Host ""

# Track progress
$totalSteps = 0
$completedSteps = 0

if (-not $SkipVisualLanguage) { $totalSteps++ }
if (-not $SkipFX) { $totalSteps++ }
if (-not $SkipAudio) { $totalSteps++ }
if (-not $SkipSpritesheet) { $totalSteps++ }

function Write-Progress-Step {
    param(
        [string]$Step,
        [string]$Status = "Starting..."
    )
    
    $script:completedSteps++
    $percent = if ($totalSteps -gt 0) { ($completedSteps / $totalSteps) * 100 } else { 0 }
    
    Write-Host "[$completedSteps/$totalSteps] $Step" -ForegroundColor Yellow
    Write-Host "  Status: $Status" -ForegroundColor Gray
    
    if ($useGUI) {
        # Log to Control Room watch directory
        $logFile = Join-Path $OutputDir "generation_log.txt"
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $logFile -Value "[$timestamp] [$Step] $Status" -Encoding UTF8
    }
}

# 1. Visual Language Assets
if (-not $SkipVisualLanguage) {
    Write-Progress-Step "Visual Language" "Generating color palettes and materials..."
    
    $visualScript = Join-Path $PSScriptRoot "SpaceWhaleVisualLanguageGenerator.ps1"
    if (Test-Path $visualScript) {
        Write-Host "  Running: $visualScript" -ForegroundColor Gray
        try {
            $output = & $visualScript -RegistryPath "space_whale_visual_language_registry.json" -OutputDir (Join-Path $OutputDir "VisualLanguage") 2>&1
            if ($output) { 
                # Filter error output
                $filtered = $output | Where-Object { $_ -notmatch "^\s*$" -and $_ -notmatch "^Error" }
                if ($filtered) { Write-Host $filtered }
            }
            $exitCode = $LASTEXITCODE
            if ($exitCode -eq 0 -or $exitCode -eq $null) {
                Write-Progress-Step "Visual Language" "[DONE] Complete"
            } else {
                Write-Host "  [WARNING]  Warning: Visual Language generation returned exit code: $LASTEXITCODE" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [WARNING]  Error: Visual Language generation failed: $_" -ForegroundColor Red
            Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [WARNING]  Visual Language generator not found: $visualScript" -ForegroundColor Yellow
        Write-Host "  Skipping Visual Language generation..." -ForegroundColor Gray
    }
    Write-Host ""
}

# 2. FX Assets
if (-not $SkipFX) {
    Write-Progress-Step "FX Assets" "Generating Nova Drift style effects..."
    
    $fxScript = Join-Path $PSScriptRoot "space_whale_fx_variation_generator.py"
    if (Test-Path $fxScript) {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python) {
            Write-Host "  Running: python $fxScript" -ForegroundColor Gray
            try {
                $output = & python $fxScript "space_whale_fx_registry.json" 10 5 2>&1
                if ($output) { Write-Host $output }
                if ($LASTEXITCODE -eq 0) {
                    Write-Progress-Step "FX Assets" "[DONE] Complete"
                } else {
                    Write-Host "  [WARNING]  Warning: FX generation returned exit code: $LASTEXITCODE" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "  [WARNING]  Error: FX generation failed: $_" -ForegroundColor Red
                Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Gray
            }
        } else {
            Write-Host "  [WARNING]  Python not found in PATH" -ForegroundColor Yellow
            Write-Host "  Skipping FX generation..." -ForegroundColor Gray
        }
    } else {
        Write-Host "  [WARNING]  FX generator not found: $fxScript" -ForegroundColor Yellow
        Write-Host "  Skipping FX generation..." -ForegroundColor Gray
    }
    Write-Host ""
}

# 3. Audio Assets
if (-not $SkipAudio) {
    Write-Progress-Step "Audio Assets" "Generating EM/Plasma/Acoustic/Mechanical channels..."
    
    $audioScript = Join-Path $PSScriptRoot "SpaceWhaleAudioGenerator.ps1"
    if (Test-Path $audioScript) {
        Write-Host "  Running: $audioScript" -ForegroundColor Gray
        try {
            $output = & $audioScript -RegistryPath "space_whale_audio_registry.json" -OutputDir (Join-Path $OutputDir "Audio") 2>&1
            if ($output) { Write-Host $output }
            if ($LASTEXITCODE -eq 0) {
                Write-Progress-Step "Audio Assets" "[DONE] Complete"
            } else {
                Write-Host "  [WARNING]  Warning: Audio generation returned exit code: $LASTEXITCODE" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [WARNING]  Error: Audio generation failed: $_" -ForegroundColor Red
            Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [WARNING]  Audio generator not found: $audioScript" -ForegroundColor Yellow
        Write-Host "  Skipping Audio generation..." -ForegroundColor Gray
    }
    Write-Host ""
}

# 4. Ship Spritesheet (120 Facings)
if (-not $SkipSpritesheet) {
    Write-Progress-Step "Ship Spritesheet" "Generating 120 facings spritesheet..."
    
    $spritesheetScript = Join-Path $PSScriptRoot "SpaceWhale120FacingsGenerator.ps1"
    if (Test-Path $spritesheetScript) {
        Write-Host "  Running: $spritesheetScript" -ForegroundColor Gray
        try {
            $spritesheetArgs = @(
                "-RegistryPath", $RegistryPath,
                "-OutputDir", (Join-Path $OutputDir "Spritesheets")
            )
            
            if (-not [string]::IsNullOrWhiteSpace($ShipId)) {
                $spritesheetArgs += "-ShipId", $ShipId
            }
            
            $output = & $spritesheetScript @spritesheetArgs 2>&1
            if ($output) { Write-Host $output }
            if ($LASTEXITCODE -eq 0) {
                Write-Progress-Step "Ship Spritesheet" "[DONE] Complete"
            } else {
                Write-Host "  [WARNING]  Warning: Spritesheet generation returned exit code: $LASTEXITCODE" -ForegroundColor Yellow
                Write-Host "  Note: This requires Blender to be installed and configured" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  [WARNING]  Error: Spritesheet generation failed: $_" -ForegroundColor Red
            Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Gray
            Write-Host "  Note: This requires Blender to be installed and configured" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [WARNING]  Spritesheet generator not found: $spritesheetScript" -ForegroundColor Yellow
        Write-Host "  Skipping Spritesheet generation..." -ForegroundColor Gray
    }
    Write-Host ""
}

# Summary
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Generation Summary" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Completed: $completedSteps / $totalSteps tasks" -ForegroundColor $(if ($completedSteps -eq $totalSteps) { 'Green' } else { 'Yellow' })
Write-Host ""
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan

# Check what was actually generated
Write-Host ""
Write-Host "Generated files:" -ForegroundColor Yellow
$outputPath = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
if ($outputPath) {
    $files = Get-ChildItem -Path $outputPath -Recurse -File -ErrorAction SilentlyContinue
    if ($files) {
        Write-Host "  Total files: $($files.Count)" -ForegroundColor Gray
        $fileTypes = $files | Group-Object Extension | Sort-Object Count -Descending | Select-Object -First 5
        foreach ($type in $fileTypes) {
            Write-Host "    $($type.Name): $($type.Count) files" -ForegroundColor Gray
        }
    } else {
        Write-Host "  No files found in output directory" -ForegroundColor Yellow
        Write-Host "  This may indicate that generation did not produce any output" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Output directory not found or not accessible" -ForegroundColor Yellow
}

Write-Host ""

if ($useGUI) {
    Write-Host "Control Room Monitor is still running." -ForegroundColor Cyan
    Write-Host "  - Check the GUI window for previews" -ForegroundColor Gray
    Write-Host "  - Assets are being generated in the background" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review generated assets in: $OutputDir" -ForegroundColor Gray
Write-Host "  2. Check the Control Room Monitor for live progress" -ForegroundColor Gray
Write-Host "  3. Test assets in-game" -ForegroundColor Gray
Write-Host "  4. Adjust settings and regenerate if needed" -ForegroundColor Gray
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

