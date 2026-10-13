param(
    [string]$ModPath = "E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_astral_magic",

    [ValidateSet("references", "procedural", "ollama", "sd", "all")]
    [string]$Mode = "all",

    [ValidateSet("fast", "mechanical", "full")]
    [string]$Quality = "full",

    [switch]$UseSD,

    [switch]$GenerateDesignDraft
)

$ErrorActionPreference = "Stop"
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot   = Split-Path -Parent $scriptDir
$sharedPath  = Join-Path $toolsRoot "Shared"

# Load shared asset generation settings
$settingsPath = Join-Path $toolsRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Optional shared tool detection
$toolDetectionPath     = Join-Path $sharedPath "ToolDetection.psm1"
$toolsetIntegrationPath = Join-Path $sharedPath "ToolsetIntegration.psm1"
if (Test-Path $toolDetectionPath)     { Import-Module $toolDetectionPath -Force -ErrorAction SilentlyContinue }
if (Test-Path $toolsetIntegrationPath){ Import-Module $toolsetIntegrationPath -Force -ErrorAction SilentlyContinue }
if (Get-Command Initialize-ToolsetTools -ErrorAction SilentlyContinue) {
    $null = Initialize-ToolsetTools -RequiredTools @("Python") -OptionalTools @("Ollama", "ImageMagick")
}

# Stable Diffusion integration
$sdModule = Join-Path $sharedPath "StableDiffusionIntegration.psm1"
$script:SDAvailable  = $false
$script:SDImportError = $null
if (Test-Path $sdModule) {
    try {
        Import-Module $sdModule -DisableNameChecking -ErrorAction Stop
        $script:SDAvailable = $true
    } catch {
        $script:SDAvailable  = $false
        $script:SDImportError = $_.Exception.Message
    }
} else {
    $script:SDImportError = "Module not found: $sdModule"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) { Write-Error "Python not found in PATH" }

$generator = Join-Path $scriptDir "generate_astral_magic_assets.py"
if (-not (Test-Path $generator)) {
    Write-Error "Missing generator script: $generator"
}

$shouldGenerateDraft = $false
if ($PSBoundParameters.ContainsKey("GenerateDesignDraft")) {
    $shouldGenerateDraft = [bool]$GenerateDesignDraft
} elseif ($Mode -eq "sd" -or $UseSD -or $Mode -eq "all") {
    $shouldGenerateDraft = $true
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Soulash 2 Astral Magic Asset Generator" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Mod:     $ModPath"
Write-Host "  Mode:    $Mode"
Write-Host "  Quality: $Quality"
Write-Host "  Use SD:  $($UseSD -or $Mode -eq 'sd')"
Write-Host ""

$sdDraftIcon  = $null
$sdDraftThumb = $null
$designDraftsDir = Join-Path $ModPath "DesignDrafts"

# Step 0: SD design drafts (optional)
if ($shouldGenerateDraft -and $script:SDAvailable) {
    Write-Host "Step 0: Generating SD design drafts..." -ForegroundColor Yellow

    # Module function: checks IPv4 + IPv6, starts the server if needed and waits for /ping.
    $sdAutoStarted = Start-SDServerIfNeeded -Verbose

    if (Get-Command Test-StableDiffusionConnection -ErrorAction SilentlyContinue) {
        $sdConnected = Test-StableDiffusionConnection -Verbose
        if (-not $sdConnected) {
            Write-Host "  [ERROR] SD server not reachable; start manually if needed" -ForegroundColor Red
        }

        if ($sdConnected) {
            Write-Host "  [OK] Stable Diffusion server connected" -ForegroundColor Green

            if (-not (Test-Path $designDraftsDir)) {
                New-Item -ItemType Directory -Path $designDraftsDir -Force | Out-Null
            }

            $negativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, letters, logo, oversaturated, muddy colors"
            $draftAssets = @(
                @{
                    Name   = "Astral Magic Mod Icon"
                    File   = "icon_design_draft.png"
                    Prompt = "Soulash 2 mod icon, astral magic, summoning astral wisps and frost sparks, dark fantasy violet and cyan palette, crisp readable silhouette, hand-painted pixel art style, square composition, 1024x1024 concept art"
                    Width  = 1024
                    Height = 1024
                },
                @{
                    Name   = "Astral Magic Workshop Thumbnail"
                    File   = "thumbnail_design_draft.png"
                    Prompt = "Soulash 2 mod workshop thumbnail, astral magic banner, swirling astral wisps and shatterfrost sparks, dark cosmic atmosphere, cinematic 4:3 composition, no text, 1024x768 concept art"
                    Width  = 1024
                    Height = 768
                }
            )

            foreach ($asset in $draftAssets) {
                $draftPath = Join-Path $designDraftsDir $asset.File
                Write-Host "  Generating: $($asset.Name)..." -ForegroundColor Gray
                try {
                    if (Get-Command Generate-AssetImageWithSD3 -ErrorAction SilentlyContinue) {
                        $null = Test-StableDiffusionConnection -ErrorAction SilentlyContinue
                        Generate-AssetImageWithSD3 `
                            -Prompt $asset.Prompt `
                            -OutputPath $draftPath `
                            -NegativePrompt $negativePrompt `
                            -Width $asset.Width `
                            -Height $asset.Height `
                            -Steps 28 `
                            -GuidanceScale 7.0 `
                            -EnhanceWithOllama:$true `
                            -AutoStartServer:$false | Out-Null

                        if (Test-Path $draftPath) {
                            Write-Host "    [OK] $($asset.File)" -ForegroundColor Green
                        } else {
                            Write-Host "    [WARN] Draft not created: $($asset.File)" -ForegroundColor Yellow
                        }
                    }
                } catch {
                    Write-Host "    [WARN] SD draft failed: $_" -ForegroundColor Yellow
                }
            }

            $iconDraftPath  = Join-Path $designDraftsDir "icon_design_draft.png"
            $thumbDraftPath = Join-Path $designDraftsDir "thumbnail_design_draft.png"
            if (Test-Path $iconDraftPath)  { $sdDraftIcon  = $iconDraftPath }
            if (Test-Path $thumbDraftPath) { $sdDraftThumb = $thumbDraftPath }
        } else {
            Write-Host "  [WARN] SD server not available (Python will use procedural fallback)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
} elseif ($shouldGenerateDraft -and -not $script:SDAvailable) {
    Write-Host "[WARN] StableDiffusionIntegration.psm1 not loaded; skipping SD features." -ForegroundColor Yellow
    if ($script:SDImportError) {
        Write-Host "       Reason: $($script:SDImportError)" -ForegroundColor Gray
    }
    Write-Host "       Python will use procedural fallback." -ForegroundColor Gray
    Write-Host ""
}

# Build Python args
$pythonArgs = @(
    $generator,
    "--mod-path", $ModPath,
    "--mode", $Mode,
    "--quality", $Quality,
    "--grids", "abilities,amplifiers,passives,skills,stackers,entities"
)

if ($UseSD -or $Mode -eq "sd") {
    $pythonArgs += "--use-sd"
}
if ($sdDraftIcon) {
    $pythonArgs += @("--sd-draft-icon", $sdDraftIcon)
}
if ($sdDraftThumb) {
    $pythonArgs += @("--sd-draft-thumbnail", $sdDraftThumb)
}
if (Test-Path $designDraftsDir) {
    $pythonArgs += @("--sd-drafts-dir", $designDraftsDir)
}

Write-Host "Starting astral asset generation..." -ForegroundColor Cyan
& $python.Source @pythonArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Astral asset generation failed (exit $LASTEXITCODE)"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Astral Magic asset generation complete." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
