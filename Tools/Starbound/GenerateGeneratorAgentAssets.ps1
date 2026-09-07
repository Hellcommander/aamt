#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the GeneratorAgent System.
    
.DESCRIPTION
    Generates UI icons and interface elements for:
    - Generator UI panels
    - Asset browser elements
    - Generator category icons
    - Preview panel elements
    - Export panel elements
    - Settings panel elements
    - Generator status indicators
    
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
    [bool]$UseCppBackend = $true
)

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
Write-Host "  GeneratorAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. GENERATOR UI PANEL ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Generator UI Panel Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$panelElements = @(
    @{ Id = "generator_panel_background"; Name = "Panel Background"; Desc = "Generator panel background texture, panel background, 128x128" },
    @{ Id = "generator_panel_border"; Name = "Panel Border"; Desc = "Generator panel border texture, panel border, 128x128" },
    @{ Id = "generator_tab_active"; Name = "Active Tab"; Desc = "Generator active tab icon, active tab, 64x32" },
    @{ Id = "generator_tab_inactive"; Name = "Inactive Tab"; Desc = "Generator inactive tab icon, inactive tab, 64x32" },
    @{ Id = "generator_separator"; Name = "Separator Line"; Desc = "Generator separator line texture, panel separator, 128x4" }
)

# Validate $ModPath before Join-Path
$panelOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($panelOutputDir)) {
    Write-Host "  [FAIL] panelOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping panel element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $panelOutputDir)) {
        New-Item -ItemType Directory -Path $panelOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($panelOutputDir)) {
        foreach ($element in $panelElements) {
        Write-Host "Generating panel element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($element.Id -like "*background*" -or $element.Id -like "*border*" -or $element.Id -like "*separator*") { "Texture" } else { "Icon" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $element.Id
                Prompt = "$($element.Desc). Generator UI element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $panelOutputDir
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
}

# ============================================================
# 2. ASSET BROWSER ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Asset Browser Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$browserElements = @(
    @{ Id = "browser_folder_icon"; Name = "Folder Icon"; Desc = "Asset browser folder icon, folder, 32x32" },
    @{ Id = "browser_file_icon"; Name = "File Icon"; Desc = "Asset browser file icon, file, 32x32" },
    @{ Id = "browser_asset_icon"; Name = "Asset Icon"; Desc = "Asset browser asset icon, asset item, 32x32" },
    @{ Id = "browser_refresh"; Name = "Refresh Button"; Desc = "Asset browser refresh button icon, refresh, 32x32" },
    @{ Id = "browser_search"; Name = "Search Icon"; Desc = "Asset browser search icon, search, 32x32" },
    @{ Id = "browser_filter"; Name = "Filter Icon"; Desc = "Asset browser filter icon, filter, 32x32" }
)

# Validate $ModPath before Join-Path
$browserOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($browserOutputDir)) {
    Write-Host "  [FAIL] browserOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping browser element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $browserOutputDir)) {
        New-Item -ItemType Directory -Path $browserOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($browserOutputDir)) {
        foreach ($element in $browserElements) {
        Write-Host "Generating browser element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $element.Id
                Prompt = "$($element.Desc). Asset browser element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $browserOutputDir
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
}

# ============================================================
# 3. GENERATOR CATEGORY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Generator Category Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$categoryIcons = @(
    @{ Id = "generator_category_mechs"; Name = "Mechs Category"; Desc = "Generator mechs category icon, mech generation, 32x32" },
    @{ Id = "generator_category_spells"; Name = "Spells Category"; Desc = "Generator spells category icon, spell generation, 32x32" },
    @{ Id = "generator_category_projectiles"; Name = "Projectiles Category"; Desc = "Generator projectiles category icon, projectile generation, 32x32" },
    @{ Id = "generator_category_particles"; Name = "Particles Category"; Desc = "Generator particles category icon, particle generation, 32x32" },
    @{ Id = "generator_category_textures"; Name = "Textures Category"; Desc = "Generator textures category icon, texture generation, 32x32" },
    @{ Id = "generator_category_meshes"; Name = "Meshes Category"; Desc = "Generator meshes category icon, mesh generation, 32x32" },
    @{ Id = "generator_category_animations"; Name = "Animations Category"; Desc = "Generator animations category icon, animation generation, 32x32" },
    @{ Id = "generator_category_ui"; Name = "UI Category"; Desc = "Generator UI category icon, UI generation, 32x32" },
    @{ Id = "generator_category_status"; Name = "Status Effects Category"; Desc = "Generator status effects category icon, status effect generation, 32x32" },
    @{ Id = "generator_category_icons"; Name = "Icons Category"; Desc = "Generator icons category icon, icon generation, 32x32" }
)

# Validate $ModPath before Join-Path
$categoryOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($categoryOutputDir)) {
    Write-Host "  [FAIL] categoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping category icon generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $categoryOutputDir)) {
        New-Item -ItemType Directory -Path $categoryOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($categoryOutputDir)) {
        foreach ($icon in $categoryIcons) {
        Write-Host "Generating category icon: $($icon.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $icon.Id
                Prompt = "$($icon.Desc). Generator category icon for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $categoryOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($icon.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($icon.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
}

# ============================================================
# 4. PREVIEW PANEL ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Preview Panel Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$previewElements = @(
    @{ Id = "preview_play"; Name = "Preview Play"; Desc = "Preview play button icon, play preview, 32x32" },
    @{ Id = "preview_pause"; Name = "Preview Pause"; Desc = "Preview pause button icon, pause preview, 32x32" },
    @{ Id = "preview_stop"; Name = "Preview Stop"; Desc = "Preview stop button icon, stop preview, 32x32" },
    @{ Id = "preview_reset"; Name = "Preview Reset"; Desc = "Preview reset button icon, reset preview, 32x32" },
    @{ Id = "preview_zoom_in"; Name = "Zoom In"; Desc = "Preview zoom in button icon, zoom in, 32x32" },
    @{ Id = "preview_zoom_out"; Name = "Zoom Out"; Desc = "Preview zoom out button icon, zoom out, 32x32" },
    @{ Id = "preview_rotate"; Name = "Preview Rotate"; Desc = "Preview rotate button icon, rotate preview, 32x32" }
)

# Validate $ModPath before Join-Path
$previewOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($previewOutputDir)) {
    Write-Host "  [FAIL] previewOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping preview element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $previewOutputDir)) {
        New-Item -ItemType Directory -Path $previewOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($previewOutputDir)) {
        foreach ($element in $previewElements) {
        Write-Host "Generating preview element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $element.Id
                Prompt = "$($element.Desc). Preview panel element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $previewOutputDir
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
}

# ============================================================
# 5. EXPORT PANEL ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Export Panel Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$exportElements = @(
    @{ Id = "export_button"; Name = "Export Button"; Desc = "Export button icon, export asset, 64x32" },
    @{ Id = "export_format_png"; Name = "PNG Format"; Desc = "PNG export format icon, PNG format, 32x32" },
    @{ Id = "export_format_json"; Name = "JSON Format"; Desc = "JSON export format icon, JSON format, 32x32" },
    @{ Id = "export_format_particle"; Name = "Particle Format"; Desc = "Particle export format icon, particle format, 32x32" },
    @{ Id = "export_success"; Name = "Export Success"; Desc = "Export success indicator icon, export successful, 32x32" },
    @{ Id = "export_failed"; Name = "Export Failed"; Desc = "Export failed indicator icon, export failed, 32x32" }
)

# Validate $ModPath before Join-Path
$exportOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($exportOutputDir)) {
    Write-Host "  [FAIL] exportOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping export element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $exportOutputDir)) {
        New-Item -ItemType Directory -Path $exportOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($exportOutputDir)) {
        foreach ($element in $exportElements) {
        Write-Host "Generating export element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $element.Id
                Prompt = "$($element.Desc). Export panel element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $exportOutputDir
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
}

# ============================================================
# 6. SETTINGS PANEL ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Settings Panel Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$settingsElements = @(
    @{ Id = "settings_icon"; Name = "Settings Icon"; Desc = "Settings icon, settings panel, 32x32" },
    @{ Id = "settings_save"; Name = "Save Settings"; Desc = "Save settings button icon, save, 32x32" },
    @{ Id = "settings_reset"; Name = "Reset Settings"; Desc = "Reset settings button icon, reset, 32x32" },
    @{ Id = "settings_advanced"; Name = "Advanced Settings"; Desc = "Advanced settings indicator icon, advanced, 32x32" }
)

# Validate $ModPath before Join-Path
$settingsOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($settingsOutputDir)) {
    Write-Host "  [FAIL] settingsOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping settings element generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $settingsOutputDir)) {
        New-Item -ItemType Directory -Path $settingsOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($settingsOutputDir)) {
    foreach ($element in $settingsElements) {
        Write-Host "Generating settings element: $($element.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $element.Id
                Prompt = "$($element.Desc). Settings panel element for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $settingsOutputDir
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
}

# ============================================================
# 7. GENERATOR STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Generator Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$statusIndicators = @(
    @{ Id = "generator_idle"; Name = "Generator Idle"; Desc = "Generator idle status indicator, idle, 32x32" },
    @{ Id = "generator_generating"; Name = "Generator Generating"; Desc = "Generator generating status indicator, generating, 32x32" },
    @{ Id = "generator_complete"; Name = "Generator Complete"; Desc = "Generator complete status indicator, generation complete, 32x32" },
    @{ Id = "generator_error"; Name = "Generator Error"; Desc = "Generator error status indicator, generation error, 32x32" },
    @{ Id = "generator_progress"; Name = "Generator Progress"; Desc = "Generator progress bar UI element, generation progress, 32x8" }
)

# Validate $ModPath before Join-Path
$statusOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping status indicator generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $statusOutputDir)) {
        New-Item -ItemType Directory -Path $statusOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($statusOutputDir)) {
    foreach ($indicator in $statusIndicators) {
        Write-Host "Generating status indicator: $($indicator.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($indicator.Id -like "*progress*") { "Icon" } else { "Icon" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $indicator.Id
                Prompt = "$($indicator.Desc). Generator status indicator for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $statusOutputDir
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
}

# ============================================================
# 8. GENERATOR ACTION BUTTONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Generator Action Buttons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$actionButtons = @(
    @{ Id = "action_generate"; Name = "Generate Button"; Desc = "Generate button icon, generate asset, 64x32" },
    @{ Id = "action_cancel"; Name = "Cancel Button"; Desc = "Cancel button icon, cancel generation, 64x32" },
    @{ Id = "action_save"; Name = "Save Button"; Desc = "Save button icon, save asset, 64x32" },
    @{ Id = "action_load"; Name = "Load Button"; Desc = "Load button icon, load asset, 64x32" },
    @{ Id = "action_new"; Name = "New Button"; Desc = "New button icon, new asset, 64x32" },
    @{ Id = "action_delete"; Name = "Delete Button"; Desc = "Delete button icon, delete asset, 64x32" }
)

# Validate $ModPath before Join-Path
$actionOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($actionOutputDir)) {
    Write-Host "  [FAIL] actionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping action button generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $actionOutputDir)) {
        New-Item -ItemType Directory -Path $actionOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($actionOutputDir)) {
        foreach ($button in $actionButtons) {
        Write-Host "Generating action button: $($button.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $button.Id
                Prompt = "$($button.Desc). Generator action button for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $actionOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($button.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($button.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
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
Write-Host "  Generator UI Panels: $(Join-Path $ModPath 'assets\generator\ui\panels')" -ForegroundColor Gray
Write-Host "  Asset Browser: $(Join-Path $ModPath 'assets\generator\ui\browser')" -ForegroundColor Gray
Write-Host "  Generator Categories: $(Join-Path $ModPath 'assets\generator\ui\categories')" -ForegroundColor Gray
Write-Host "  Preview Panel: $(Join-Path $ModPath 'assets\generator\ui\preview')" -ForegroundColor Gray
Write-Host "  Export Panel: $(Join-Path $ModPath 'assets\generator\ui\export')" -ForegroundColor Gray
Write-Host "  Settings Panel: $(Join-Path $ModPath 'assets\generator\ui\settings')" -ForegroundColor Gray
Write-Host "  Status Indicators: $(Join-Path $ModPath 'assets\generator\ui\status')" -ForegroundColor Gray
Write-Host "  Action Buttons: $(Join-Path $ModPath 'assets\generator\ui\actions')" -ForegroundColor Gray
Write-Host ""
