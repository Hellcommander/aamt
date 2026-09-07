#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the PortalAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Portal sprites (different portal types)
    - Portal particle effects (sparks, embers)
    - Portal editor UI elements
    - Portal extension visuals
    - Portal preview visuals
    - Portal state indicators
    
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
Write-Host "  PortalAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PORTAL SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalTypes = @(
    @{ Id = "portal_standard"; Name = "Standard Portal"; Desc = "Standard portal sprite, basic portal ring, 64x64" },
    @{ Id = "portal_dimensional"; Name = "Dimensional Portal"; Desc = "Dimensional portal sprite, dimensional rift portal, 64x64" },
    @{ Id = "portal_temporal"; Name = "Temporal Portal"; Desc = "Temporal portal sprite, time portal, 64x64" },
    @{ Id = "portal_quantum"; Name = "Quantum Portal"; Desc = "Quantum portal sprite, quantum portal, 64x64" },
    @{ Id = "portal_void"; Name = "Void Portal"; Desc = "Void portal sprite, void portal, 64x64" },
    @{ Id = "portal_recursive"; Name = "Recursive Portal"; Desc = "Recursive portal sprite, recursive portal, 64x64" },
    @{ Id = "portal_network"; Name = "Network Portal"; Desc = "Network portal sprite, network portal, 64x64" }
)

# Validate $ModPath before Join-Path
$portalOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($portalOutputDir)) {
    Write-Host "  [FAIL] portalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($portalOutputDir)) {
    Write-Host "  [FAIL] portalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $portalOutputDir)) {
    New-Item -ItemType Directory -Path $portalOutputDir -Force | Out-Null
}

foreach ($portal in $portalTypes) {
    Write-Host "Generating portal: $($portal.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "PortalSprite"
            AssetName = $portal.Id
            Prompt = "$($portal.Desc). Portal sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($portal.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($portal.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. PORTAL PARTICLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Particle Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$particleEffects = @(
    @{ Id = "portal_spark_trail"; Name = "Spark Trail"; Desc = "Portal spark trail particle effect, spark trail, 32x32" },
    @{ Id = "portal_embers"; Name = "Embers"; Desc = "Portal embers particle effect, embers, 32x32" },
    @{ Id = "portal_swirl"; Name = "Swirl"; Desc = "Portal swirl particle effect, swirling energy, 64x64" },
    @{ Id = "portal_pulse"; Name = "Pulse"; Desc = "Portal pulse particle effect, pulsing energy, 64x64" },
    @{ Id = "portal_distortion"; Name = "Distortion"; Desc = "Portal distortion particle effect, space distortion, 64x64" },
    @{ Id = "portal_rift"; Name = "Rift"; Desc = "Portal rift particle effect, dimensional rift, 64x64" }
)

# Validate $ModPath before Join-Path
$particleOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($particleOutputDir)) {
    Write-Host "  [FAIL] particleOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($particleOutputDir)) {
    Write-Host "  [FAIL] particleOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $particleOutputDir)) {
    New-Item -ItemType Directory -Path $particleOutputDir -Force | Out-Null
}

foreach ($effect in $particleEffects) {
    Write-Host "Generating particle effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Portal particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $particleOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. PORTAL EDITOR UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Editor UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$editorElements = @(
    @{ Id = "editor_ring_designer"; Name = "Ring Designer"; Desc = "Ring designer UI icon, portal ring editor, 32x32" },
    @{ Id = "editor_shader"; Name = "Shader Editor"; Desc = "Shader editor UI icon, shader editor, 32x32" },
    @{ Id = "editor_particle_profiler"; Name = "Particle Profiler"; Desc = "Particle profiler UI icon, particle profiler, 32x32" },
    @{ Id = "editor_link_manager"; Name = "Link Manager"; Desc = "Link manager UI icon, portal link manager, 32x32" },
    @{ Id = "editor_collider_debug"; Name = "Collider Debug"; Desc = "Collider debug UI icon, collider debug, 32x32" },
    @{ Id = "editor_preview"; Name = "Preview"; Desc = "Preview UI icon, portal preview, 32x32" },
    @{ Id = "editor_save"; Name = "Save"; Desc = "Save UI icon, save portal, 32x32" },
    @{ Id = "editor_load"; Name = "Load"; Desc = "Load UI icon, load portal, 32x32" }
)

# Validate $ModPath before Join-Path
$editorOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($editorOutputDir)) {
    Write-Host "  [FAIL] editorOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($editorOutputDir)) {
    Write-Host "  [FAIL] editorOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $editorOutputDir)) {
    New-Item -ItemType Directory -Path $editorOutputDir -Force | Out-Null
}

foreach ($element in $editorElements) {
    Write-Host "Generating editor element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $element.Id
            Prompt = "$($element.Desc). Portal editor UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $editorOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($element.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($element.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. PORTAL EXTENSION VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Extension Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$extensionVisuals = @(
    @{ Id = "extension_recursive"; Name = "Recursive Extension"; Desc = "Recursive portal extension icon, recursive portals, 32x32" },
    @{ Id = "extension_env_blend"; Name = "Environmental Blend"; Desc = "Environmental blend extension icon, environment blending, 32x32" },
    @{ Id = "extension_rift"; Name = "Dimensional Rift"; Desc = "Dimensional rift extension icon, dimensional rifts, 32x32" },
    @{ Id = "extension_ai_nav"; Name = "AI Navigation"; Desc = "AI navigation extension icon, portal AI navigation, 32x32" },
    @{ Id = "extension_network"; Name = "Network Sync"; Desc = "Network sync extension icon, network synchronization, 32x32" },
    @{ Id = "extension_cubemap"; Name = "Cubemap Probe"; Desc = "Cubemap probe icon, environment probe, 32x32" },
    @{ Id = "extension_render_target"; Name = "Render Target"; Desc = "Render target icon, render target, 32x32" }
)

# Validate $ModPath before Join-Path
$extensionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($extensionOutputDir)) {
    Write-Host "  [FAIL] extensionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($extensionOutputDir)) {
    Write-Host "  [FAIL] extensionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $extensionOutputDir)) {
    New-Item -ItemType Directory -Path $extensionOutputDir -Force | Out-Null
}

foreach ($visual in $extensionVisuals) {
    Write-Host "Generating extension visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Portal extension visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $extensionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($visual.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($visual.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. PORTAL STATE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal State Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stateIndicators = @(
    @{ Id = "state_open"; Name = "Open State"; Desc = "Portal open state indicator, portal open, 32x32" },
    @{ Id = "state_closed"; Name = "Closed State"; Desc = "Portal closed state indicator, portal closed, 32x32" },
    @{ Id = "state_opening"; Name = "Opening State"; Desc = "Portal opening state indicator, portal opening, 32x32" },
    @{ Id = "state_closing"; Name = "Closing State"; Desc = "Portal closing state indicator, portal closing, 32x32" },
    @{ Id = "state_traversing"; Name = "Traversing State"; Desc = "Portal traversing state indicator, portal traversing, 32x32" },
    @{ Id = "state_cooldown"; Name = "Cooldown State"; Desc = "Portal cooldown state indicator, portal cooldown, 32x32" },
    @{ Id = "state_linked"; Name = "Linked State"; Desc = "Portal linked state indicator, portal linked, 32x32" },
    @{ Id = "state_unlinked"; Name = "Unlinked State"; Desc = "Portal unlinked state indicator, portal unlinked, 32x32" }
)

# Validate $ModPath before Join-Path
$stateOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stateOutputDir)) {
    New-Item -ItemType Directory -Path $stateOutputDir -Force | Out-Null
}

foreach ($indicator in $stateIndicators) {
    Write-Host "Generating state indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Portal state indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stateOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. PORTAL PREVIEW VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Preview Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$previewVisuals = @(
    @{ Id = "preview_portal"; Name = "Portal Preview"; Desc = "Portal preview sprite, portal preview, 64x64" },
    @{ Id = "preview_rim_collider"; Name = "Rim Collider"; Desc = "Rim collider preview indicator, rim collider, 32x32" },
    @{ Id = "preview_trigger_volume"; Name = "Trigger Volume"; Desc = "Trigger volume preview indicator, trigger volume, 32x32" },
    @{ Id = "preview_destination"; Name = "Destination"; Desc = "Destination preview indicator, portal destination, 32x32" }
)

# Validate $ModPath before Join-Path
$previewOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($previewOutputDir)) {
    Write-Host "  [FAIL] previewOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($previewOutputDir)) {
    Write-Host "  [FAIL] previewOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $previewOutputDir)) {
    New-Item -ItemType Directory -Path $previewOutputDir -Force | Out-Null
}

foreach ($visual in $previewVisuals) {
    Write-Host "Generating preview visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($visual.Id -like "*portal*") { "PortalSprite" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Portal preview visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $previewOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($visual.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($visual.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. PORTAL NETWORK VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Network Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$networkVisuals = @(
    @{ Id = "network_node"; Name = "Network Node"; Desc = "Portal network node icon, network node, 32x32" },
    @{ Id = "network_edge"; Name = "Network Edge"; Desc = "Portal network edge icon, network connection, 32x32" },
    @{ Id = "network_path"; Name = "Network Path"; Desc = "Portal network path icon, network path, 32x32" },
    @{ Id = "network_sync"; Name = "Network Sync"; Desc = "Network sync indicator, network synchronization, 32x32" }
)

# Validate $ModPath before Join-Path
$networkOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($networkOutputDir)) {
    Write-Host "  [FAIL] networkOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($networkOutputDir)) {
    Write-Host "  [FAIL] networkOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $networkOutputDir)) {
    New-Item -ItemType Directory -Path $networkOutputDir -Force | Out-Null
}

foreach ($visual in $networkVisuals) {
    Write-Host "Generating network visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Portal network visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $networkOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($visual.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($visual.Name) : $_" -ForegroundColor Red
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
Write-Host "  Portal Sprites: $(Join-Path $ModPath 'assets\portals\sprites')" -ForegroundColor Gray
Write-Host "  Portal Particles: $(Join-Path $ModPath 'assets\portals\particles')" -ForegroundColor Gray
Write-Host "  Portal Editor: $(Join-Path $ModPath 'assets\portals\editor')" -ForegroundColor Gray
Write-Host "  Portal Extensions: $(Join-Path $ModPath 'assets\portals\extensions')" -ForegroundColor Gray
Write-Host "  Portal States: $(Join-Path $ModPath 'assets\portals\states')" -ForegroundColor Gray
Write-Host "  Portal Preview: $(Join-Path $ModPath 'assets\portals\preview')" -ForegroundColor Gray
Write-Host "  Portal Network: $(Join-Path $ModPath 'assets\portals\network')" -ForegroundColor Gray
Write-Host ""
