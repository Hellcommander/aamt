<#
.SYNOPSIS
    Generate Broodmother Mutation asset drafts (SD3.5) and exports (PNG).

.DESCRIPTION
    Wrapper around `generate_broodmother_assets_ollama.py` that:
    - Verifies Python + Ollama availability (Ollama required for prompt packs)
    - Optionally relies on SD3.5 (auto-detected) to generate high-res drafts
    - Exports game-ready PNGs into the mod directory

    This mirrors the workflow used by `GenerateVortexAssets.ps1`.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,

    [switch]$SkipSD35 = $false,
    [switch]$SkipExport,

    [string]$DraftDir = "DesignDrafts",

    [switch]$NoPostprocess,
    
    [switch]$LoadExisting,

    # Regenerate DesignDrafts\prompt_pack.json via Ollama even if already 34/34 complete
    [switch]$ForcePromptPack,
    
    [switch]$GenerateAudio,
    
    [switch]$UnloadModels,
    
    [switch]$Parallel,
    
    [int]$MaxWorkers = 0,
    
    [switch]$NoCache,
    
    [string]$CacheDir = "",
    
    [switch]$ArtDirector,
    
    [switch]$MultiAgent,

    # draft=fast SD only; police=heuristic+critic+retry (default); full=sequential multi-model (slow)
    [ValidateSet("draft", "police", "full", "")]
    [string]$QualityMode = "",
    
    [int]$MaxRefinementIterations = 3,
    
    [int]$QualityThreshold = 75,
    
    [switch]$EnableVisionModels = $true,
    
    [switch]$EnablePreferenceScorer = $true,

    [int]$OllamaTimeout = 600,

    # Uncensored model for biomutation prompt packs / art director (no content filters)
    [string]$OllamaModel = "wizardlm-uncensored:latest",

    # Prefer the CUDA/miniconda interpreter used by SD3.5 (has Pillow). Double-click PATH often hits Python 3.14 without deps.
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Broodmother Asset Generator (Ollama + SD3.5 Drafts)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Mod Path: $ModPath" -ForegroundColor Gray
Write-Host ""

# Shared modules live at Tools\Shared (one level up from Tools\Qud)
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"

function Resolve-BroodmotherPython {
    param([string]$Preferred)
    $candidates = @()
    if ($Preferred) { $candidates += $Preferred }
    if ($env:AAMT_PYTHON) { $candidates += $env:AAMT_PYTHON }
    $candidates += @(
        "E:\tools\miniconda3\python.exe",
        "$env:USERPROFILE\miniconda3\python.exe",
        "$env:LOCALAPPDATA\miniconda3\python.exe",
        "C:\ProgramData\miniconda3\python.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return (Resolve-Path -LiteralPath $c).Path }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$pythonExe = Resolve-BroodmotherPython -Preferred $PythonExe
if (-not $pythonExe) {
    Write-Host "[ERROR] Python not found. Install miniconda at E:\tools\miniconda3 or set -PythonExe." -ForegroundColor Red
    throw "Python not found"
}

# Check Python + Pillow on the chosen interpreter
try {
    $pyVersion = & $pythonExe --version 2>&1
    if (-not ("$pyVersion" -match "Python")) {
        throw "Python not detected at $pythonExe"
    }
    Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green
    Write-Host "     $pythonExe" -ForegroundColor DarkGray
    & $pythonExe -c "import PIL" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Pillow (PIL) missing in this Python. Install with:" -ForegroundColor Red
        Write-Host "  `"$pythonExe`" -m pip install Pillow" -ForegroundColor Yellow
        throw "Pillow not installed for $pythonExe"
    }
    Write-Host "[OK] Pillow available" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    throw
}

# Import shared Ollama integration module (silence PowerShell Verbose spam from Import-Module)
$ollamaModulePath = Join-Path $sharedPath "OllamaIntegration.psm1"
$wantPyVerbose = $PSCmdlet.MyInvocation.BoundParameters["Verbose"] -or $VerbosePreference -eq "Continue"
$prevVerbosePreference = $VerbosePreference
$VerbosePreference = "SilentlyContinue"
if (Test-Path $ollamaModulePath) {
    try {
        Import-Module $ollamaModulePath -Force -DisableNameChecking -ErrorAction Stop
        Write-Host "[OK] Ollama integration module loaded" -ForegroundColor Green
    } catch {
        $VerbosePreference = $prevVerbosePreference
        Write-Host "[ERROR] Failed to import Ollama integration module: $_" -ForegroundColor Red
        throw
    }
} else {
    $VerbosePreference = $prevVerbosePreference
    Write-Host "[ERROR] Ollama integration module not found: $ollamaModulePath" -ForegroundColor Red
    throw "Required module missing"
}

# Check Ollama connection and auto-select models using shared module
Write-Host ""
Write-Host "Checking Ollama connection..." -ForegroundColor Cyan
if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
    if (-not (Test-OllamaConnection)) {
        $VerbosePreference = $prevVerbosePreference
        Write-Host "[ERROR] Ollama connection failed" -ForegroundColor Red
        Write-Host "  Make sure Ollama is running: ollama serve" -ForegroundColor Yellow
        Write-Host "  Install models: ollama pull llama3.1:8b" -ForegroundColor Yellow
        if (-not $LoadExisting) {
            exit 1
        } else {
            Write-Host "[WARN] Continuing with --load-existing (Ollama calls will be skipped)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[OK] Ollama connection verified" -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] Test-OllamaConnection function not available" -ForegroundColor Red
    Write-Host "  OllamaIntegration.psm1 may not be properly loaded" -ForegroundColor Yellow
    if (-not $LoadExisting) {
        $VerbosePreference = $prevVerbosePreference
        exit 1
    }
}
$VerbosePreference = $prevVerbosePreference

# Optional: SD3.5 module presence (the Python script will also check)
$sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"
if (Test-Path $sdModule) {
    Write-Host "[OK] SD3.5 integration module found" -ForegroundColor Green
} else {
    Write-Host "[WARN] SD3.5 integration module not found; SD drafts will fail unless -SkipSD35 is used" -ForegroundColor Yellow
}

$scriptPath = Join-Path $PSScriptRoot "generate_broodmother_assets_ollama.py"
if (-not (Test-Path $scriptPath)) {
    throw "Generator script not found: $scriptPath"
}

# Build argument list - PowerShell will handle quoting automatically
$argsList = @($scriptPath, $ModPath, "--draft-dir", $DraftDir)
if ($SkipSD35) { $argsList += "--skip-sd35" }
if ($SkipExport) { $argsList += "--skip-export" }
if ($NoPostprocess) { $argsList += "--no-postprocess" }
if ($LoadExisting) { $argsList += "--load-existing" }
if ($ForcePromptPack) { $argsList += "--force-prompt-pack" }
if ($GenerateAudio) { $argsList += "--generate-audio" }
if ($wantPyVerbose) { $argsList += "--verbose" }
if ($UnloadModels) { $argsList += "--unload-models" }
if ($Parallel) { $argsList += "--parallel" }
if ($MaxWorkers -gt 0) { $argsList += "--max-workers"; $argsList += $MaxWorkers }
if ($NoCache) { $argsList += "--no-cache" }
if ($CacheDir) { $argsList += "--cache-dir"; $argsList += $CacheDir }
if ($QualityMode) { $argsList += "--quality-mode"; $argsList += $QualityMode }
if ($ArtDirector) { $argsList += "--art-director" }
if ($MultiAgent) { $argsList += "--multi-agent" }
if ($MaxRefinementIterations -ne 3) { $argsList += "--max-refinement-iterations"; $argsList += $MaxRefinementIterations }
if ($QualityThreshold -ne 75) { $argsList += "--quality-threshold"; $argsList += $QualityThreshold }
if (-not $EnableVisionModels) { $argsList += "--no-enable-vision-models" }
if (-not $EnablePreferenceScorer) { $argsList += "--no-enable-preference-scorer" }
if ($OllamaTimeout -gt 0) { $argsList += "--ollama-timeout"; $argsList += $OllamaTimeout }
if ($OllamaModel) { $argsList += "--model"; $argsList += $OllamaModel }

Write-Host ""
Write-Host "Running generator..." -ForegroundColor Cyan
Write-Host "  Ollama model: $OllamaModel (uncensored)" -ForegroundColor Gray
Write-Host "  Python: $pythonExe" -ForegroundColor Gray
Write-Host "  $pythonExe $($argsList -join ' ')" -ForegroundColor DarkGray
Write-Host ""

# Run Python script with error handling
# Use & operator to properly handle arguments with spaces
try {
    # Execute using & operator which properly handles argument quoting
    & $pythonExe $argsList
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] Python script exited with code: $exitCode" -ForegroundColor Red
        Write-Host "Check the output above for details." -ForegroundColor Yellow
    } else {
        # Python already bridges Textures->Assets; attempt AssetBundles with exact Qud Editor.
        $sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
        Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -Force -ErrorAction SilentlyContinue
        if ((Get-Command Invoke-AamtUnityAssetBundles -ErrorAction SilentlyContinue) -and
            (Test-Path (Join-Path $ModPath "Assets"))) {
            Write-Host ""
            Write-Host "Attempting AssetBundle build with matching Unity Editor..." -ForegroundColor Cyan
            $qudGame = if ($env:QUD_GAME_ROOT) { $env:QUD_GAME_ROOT } else { "E:\SteamLibrary\steamapps\common\Caves of Qud" }
            [void](Invoke-AamtUnityAssetBundles -ProjectPath $ModPath -GameRoot $qudGame -EnsureProject)
        }
    }
    
    exit $exitCode
} catch {
    Write-Host ""
    Write-Host "[ERROR] Failed to run Python script: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Yellow
    exit 1
} finally {
    # Cleanup: Unload models if requested
    if ($UnloadModels) {
        Write-Host ""
        Write-Host "Unloading Ollama models to free VRAM..." -ForegroundColor Cyan
        try {
            if (Get-Command Unload-OllamaModel -ErrorAction SilentlyContinue) {
                # Use shared module's unload function if available
                $ollamaUrl = "http://localhost:11434"
                $psResponse = Invoke-RestMethod -Uri "$ollamaUrl/api/ps" -TimeoutSec 5 -ErrorAction SilentlyContinue
                if ($psResponse -and $psResponse.models) {
                    foreach ($model in $psResponse.models) {
                        if ($model.name) {
                            try {
                                Unload-OllamaModel -ModelName $model.name -ErrorAction SilentlyContinue
                                Write-Host "  Unloaded: $($model.name)" -ForegroundColor Gray
                            } catch {
                                # Try alternative method
                                try {
                                    $null = & ollama stop $model.name 2>&1
                                } catch { }
                            }
                        }
                    }
                    Write-Host "[OK] VRAM freed" -ForegroundColor Green
                } else {
                    Write-Host "[INFO] No models to unload" -ForegroundColor Gray
                }
            } else {
                # Fallback to manual unload
                $ollamaUrl = "http://localhost:11434"
                $psResponse = Invoke-RestMethod -Uri "$ollamaUrl/api/ps" -TimeoutSec 5 -ErrorAction SilentlyContinue
                if ($psResponse -and $psResponse.models) {
                    foreach ($model in $psResponse.models) {
                        if ($model.name) {
                            try {
                                $unloadBody = @{
                                    model = $model.name
                                    prompt = ""
                                    keep_alive = 0
                                    stream = $false
                                } | ConvertTo-Json -Compress
                                $null = Invoke-RestMethod -Uri "$ollamaUrl/api/generate" -Method Post -Body $unloadBody -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
                                Write-Host "  Unloaded: $($model.name)" -ForegroundColor Gray
                            } catch {
                                # Try alternative method
                                try {
                                    $null = & ollama stop $model.name 2>&1
                                } catch { }
                            }
                        }
                    }
                    Write-Host "[OK] VRAM freed" -ForegroundColor Green
                } else {
                    Write-Host "[INFO] No models to unload" -ForegroundColor Gray
                }
            }
        } catch {
            Write-Host "[WARN] Could not unload models: $_" -ForegroundColor Yellow
        }
    }
}
