#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate real unique assets to replace placeholder assets in the codebase.
    
.DESCRIPTION
    Generates actual assets for all placeholder references found in the codebase:
    - Interface assets (enchantment table UI)
    - Crossbow generator assets
    - Flame projectile assets
    - Other placeholder assets
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Placeholder Asset Replacement Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. ENCHANTMENT TABLE INTERFACE ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Table Interface Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$interfaceAssets = @(
    @{ Id = "magi_tech_item_placeholder"; Name = "Item Placeholder"; Desc = "Item placeholder icon, empty item slot, 150x150" },
    @{ Id = "magi_tech_enchantment_table_background"; Name = "Enchantment Table Background"; Desc = "Enchantment table background texture, UI background panel, 1000x700" },
    @{ Id = "magi_tech_enchant_button"; Name = "Enchant Button"; Desc = "Enchant button icon, apply enchantment button, 260x40" },
    @{ Id = "magi_tech_enchant_button_hover"; Name = "Enchant Button Hover"; Desc = "Enchant button hover state, hover effect, 260x40" },
    @{ Id = "magi_tech_enchant_button_pressed"; Name = "Enchant Button Pressed"; Desc = "Enchant button pressed state, pressed effect, 260x40" },
    @{ Id = "magi_tech_remove_button"; Name = "Remove Button"; Desc = "Remove enchantment button icon, remove button, 260x40" },
    @{ Id = "magi_tech_remove_button_hover"; Name = "Remove Button Hover"; Desc = "Remove button hover state, hover effect, 260x40" },
    @{ Id = "magi_tech_remove_button_pressed"; Name = "Remove Button Pressed"; Desc = "Remove button pressed state, pressed effect, 260x40" },
    @{ Id = "magi_tech_filter_button"; Name = "Filter Button"; Desc = "Filter button icon, filter button, 180x25" },
    @{ Id = "magi_tech_filter_button_hover"; Name = "Filter Button Hover"; Desc = "Filter button hover state, hover effect, 180x25" },
    @{ Id = "magi_tech_close_button"; Name = "Close Button"; Desc = "Close button icon, close interface button, 40x40" },
    @{ Id = "magi_tech_close_button_hover"; Name = "Close Button Hover"; Desc = "Close button hover state, hover effect, 40x40" },
    @{ Id = "magi_tech_enchantment_icon"; Name = "Enchantment Icon"; Desc = "Enchantment table icon, interface icon, 32x32" }
)

# Validate $ModPath before Join-Path
$interfaceOutputDir = Join-Path $ModPath "interface"
 if ([string]::IsNullOrWhiteSpace($interfaceOutputDir)) {
    Write-Host "  [FAIL] interfaceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($interfaceOutputDir)) {
    Write-Host "  [FAIL] interfaceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $interfaceOutputDir)) {
    New-Item -ItemType Directory -Path $interfaceOutputDir -Force | Out-Null
}

foreach ($asset in $interfaceAssets) {
    Write-Host "Generating interface asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($asset.Id -like "*background*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). Interface asset for Starbound enchantment table."
            OllamaModel = $OllamaModel
            OutputDir = $interfaceOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. CROSSBOW GENERATOR ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Crossbow Generator Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$crossbowAssets = @(
    @{ Id = "crossbow_basic_sprite"; Name = "Basic Crossbow Sprite"; Desc = "Basic crossbow sprite, crossbow weapon sprite, 64x64" },
    @{ Id = "crossbow_basic_icon"; Name = "Basic Crossbow Icon"; Desc = "Basic crossbow icon, crossbow item icon, 32x32" },
    @{ Id = "crossbow_advanced_sprite"; Name = "Advanced Crossbow Sprite"; Desc = "Advanced crossbow sprite, enhanced crossbow sprite, 64x64" },
    @{ Id = "crossbow_advanced_icon"; Name = "Advanced Crossbow Icon"; Desc = "Advanced crossbow icon, enhanced crossbow icon, 32x32" },
    @{ Id = "bolt_basic_sprite"; Name = "Basic Bolt Sprite"; Desc = "Basic bolt sprite, crossbow bolt projectile, 32x32" },
    @{ Id = "bolt_basic_icon"; Name = "Basic Bolt Icon"; Desc = "Basic bolt icon, bolt item icon, 32x32" },
    @{ Id = "arrow_basic_sprite"; Name = "Basic Arrow Sprite"; Desc = "Basic arrow sprite, arrow projectile, 32x32" },
    @{ Id = "arrow_basic_icon"; Name = "Basic Arrow Icon"; Desc = "Basic arrow icon, arrow item icon, 32x32" }
)

# Validate $ModPath before Join-Path
$crossbowOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($crossbowOutputDir)) {
    Write-Host "  [FAIL] crossbowOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($crossbowOutputDir)) {
    Write-Host "  [FAIL] crossbowOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $crossbowOutputDir)) {
    New-Item -ItemType Directory -Path $crossbowOutputDir -Force | Out-Null
}

foreach ($asset in $crossbowAssets) {
    Write-Host "Generating crossbow asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($asset.Id -like "*sprite*") { "Sprite" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). Crossbow generator asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $crossbowOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. FLAME PROJECTILE ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Flame Projectile Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$flameAssets = @(
    @{ Id = "flame_noise_texture"; Name = "Flame Noise Texture"; Desc = "Flame noise texture, procedural noise texture, 128x128" },
    @{ Id = "flame_gradient_texture"; Name = "Flame Gradient Texture"; Desc = "Flame gradient texture, radial gradient texture, 128x128" },
    @{ Id = "flame_merged_texture"; Name = "Flame Merged Texture"; Desc = "Flame merged texture, combined noise and gradient, 128x128" },
    @{ Id = "flame_ember_particle"; Name = "Flame Ember Particle"; Desc = "Flame ember particle effect, ember particles, 64x64" },
    @{ Id = "flame_trail_particle"; Name = "Flame Trail Particle"; Desc = "Flame trail particle effect, trail particles, 128x32" },
    @{ Id = "flame_smoke_particle"; Name = "Flame Smoke Particle"; Desc = "Flame smoke particle effect, smoke particles, 64x64" }
)

# Validate $ModPath before Join-Path
$flameOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($flameOutputDir)) {
    Write-Host "  [FAIL] flameOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($flameOutputDir)) {
    Write-Host "  [FAIL] flameOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $flameOutputDir)) {
    New-Item -ItemType Directory -Path $flameOutputDir -Force | Out-Null
}

foreach ($asset in $flameAssets) {
    Write-Host "Generating flame asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($asset.Id -like "*particle*") { "Particle" } else { "Texture" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). Flame projectile asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $flameOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. AI ART GENERATOR PLACEHOLDER ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating AI Art Generator Placeholder Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$aiArtAssets = @(
    @{ Id = "ai_art_placeholder"; Name = "AI Art Placeholder"; Desc = "AI art placeholder image, generated art placeholder, 256x256" },
    @{ Id = "ai_art_default"; Name = "AI Art Default"; Desc = "AI art default image, default generated art, 256x256" }
)

# Validate $ModPath before Join-Path
$aiArtOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($aiArtOutputDir)) {
    Write-Host "  [FAIL] aiArtOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($aiArtOutputDir)) {
    Write-Host "  [FAIL] aiArtOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $aiArtOutputDir)) {
    New-Item -ItemType Directory -Path $aiArtOutputDir -Force | Out-Null
}

foreach ($asset in $aiArtAssets) {
    Write-Host "Generating AI art asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). AI art generator asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $aiArtOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. VISUAL QA SYSTEM PLACEHOLDER ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Visual QA System Placeholder Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$qaAssets = @(
    @{ Id = "qa_placeholder_image"; Name = "QA Placeholder Image"; Desc = "Visual QA placeholder image, QA test image, 128x128" },
    @{ Id = "qa_reference_image"; Name = "QA Reference Image"; Desc = "Visual QA reference image, QA reference, 128x128" }
)

# Validate $ModPath before Join-Path
$qaOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($qaOutputDir)) {
    Write-Host "  [FAIL] qaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($qaOutputDir)) {
    Write-Host "  [FAIL] qaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $qaOutputDir)) {
    New-Item -ItemType Directory -Path $qaOutputDir -Force | Out-Null
}

foreach ($asset in $qaAssets) {
    Write-Host "Generating QA asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). Visual QA system asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $qaOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. GPU INTERFACE PLACEHOLDER ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating GPU Interface Placeholder Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$gpuAssets = @(
    @{ Id = "gpu_texture_placeholder"; Name = "GPU Texture Placeholder"; Desc = "GPU texture placeholder, default GPU texture, 64x64" },
    @{ Id = "gpu_audio_texture_placeholder"; Name = "GPU Audio Texture Placeholder"; Desc = "GPU audio texture placeholder, audio texture, 64x64" }
)

# Validate $ModPath before Join-Path
$gpuOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($gpuOutputDir)) {
    Write-Host "  [FAIL] gpuOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($gpuOutputDir)) {
    Write-Host "  [FAIL] gpuOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $gpuOutputDir)) {
    New-Item -ItemType Directory -Path $gpuOutputDir -Force | Out-Null
}

foreach ($asset in $gpuAssets) {
    Write-Host "Generating GPU asset: $($asset.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $asset.Id
            Prompt = "$($asset.Desc). GPU interface asset for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $gpuOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($asset.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($asset.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  Interface: $(Join-Path $ModPath 'interface')" -ForegroundColor Gray
Write-Host "  Crossbow: $(Join-Path $ModPath 'assets\weapons\crossbow')" -ForegroundColor Gray
Write-Host "  Flame: $(Join-Path $ModPath 'assets\projectiles\flame')" -ForegroundColor Gray
Write-Host "  AI Art: $(Join-Path $ModPath 'assets\ai_art')" -ForegroundColor Gray
Write-Host "  QA: $(Join-Path $ModPath 'assets\qa')" -ForegroundColor Gray
Write-Host "  GPU: $(Join-Path $ModPath 'assets\gpu')" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Update code references to use new asset paths" -ForegroundColor Gray
Write-Host "  2. Remove placeholder comments from code" -ForegroundColor Gray
Write-Host "  3. Test assets in-game" -ForegroundColor Gray
Write-Host ""
