#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for Plugin Systems.
    
.DESCRIPTION
    Generates UI icons, interface elements, and effects for:
    - Plugin management UI
    - Interface manager elements
    - Crafting UI icons
    - Captain's chair icons
    - Hyperdrive effects
    - Plugin status indicators
    
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
Write-Host "  Plugin System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PLUGIN MANAGEMENT UI
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Plugin Management UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$pluginUI = @(
    @{ Id = "plugin_enabled"; Name = "Plugin Enabled"; Desc = "Plugin enabled indicator icon, active plugin, 32x32" },
    @{ Id = "plugin_disabled"; Name = "Plugin Disabled"; Desc = "Plugin disabled indicator icon, inactive plugin, 32x32" },
    @{ Id = "plugin_loading"; Name = "Plugin Loading"; Desc = "Plugin loading indicator icon, plugin loading, 32x32" },
    @{ Id = "plugin_error"; Name = "Plugin Error"; Desc = "Plugin error indicator icon, plugin error, 32x32" },
    @{ Id = "plugin_reload"; Name = "Plugin Reload"; Desc = "Plugin reload button icon, reload plugin, 32x32" },
    @{ Id = "plugin_settings"; Name = "Plugin Settings"; Desc = "Plugin settings button icon, configure plugin, 32x32" }
)

# Validate $ModPath before Join-Path
$pluginUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($pluginUIOutputDir)) {
    Write-Host "  [FAIL] pluginUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($pluginUIOutputDir)) {
    Write-Host "  [FAIL] pluginUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $pluginUIOutputDir)) {
    New-Item -ItemType Directory -Path $pluginUIOutputDir -Force | Out-Null
}

foreach ($ui in $pluginUI) {
    Write-Host "Generating plugin UI element: $($ui.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $ui.Id
            Prompt = "$($ui.Desc). Plugin UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $pluginUIOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($ui.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($ui.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. INTERFACE MANAGER UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Interface Manager UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$interfaceUI = @(
    @{ Id = "interface_feature_enabled"; Name = "Feature Enabled"; Desc = "Interface feature enabled indicator, active feature, 32x32" },
    @{ Id = "interface_feature_disabled"; Name = "Feature Disabled"; Desc = "Interface feature disabled indicator, inactive feature, 32x32" },
    @{ Id = "interface_hot_reload"; Name = "Hot Reload"; Desc = "Interface hot reload indicator, hot reload active, 32x32" },
    @{ Id = "interface_metrics"; Name = "Interface Metrics"; Desc = "Interface metrics icon, performance metrics, 32x32" }
)

# Validate $ModPath before Join-Path
$interfaceUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($interfaceUIOutputDir)) {
    Write-Host "  [FAIL] interfaceUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($interfaceUIOutputDir)) {
    Write-Host "  [FAIL] interfaceUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $interfaceUIOutputDir)) {
    New-Item -ItemType Directory -Path $interfaceUIOutputDir -Force | Out-Null
}

foreach ($ui in $interfaceUI) {
    Write-Host "Generating interface UI element: $($ui.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $ui.Id
            Prompt = "$($ui.Desc). Interface UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $interfaceUIOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($ui.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($ui.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. CRAFTING UI ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Crafting UI Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$craftingUI = @(
    @{ Id = "crafting_station"; Name = "Crafting Station"; Desc = "Crafting station icon, crafting interface, 64x64" },
    @{ Id = "crafting_recipe"; Name = "Crafting Recipe"; Desc = "Crafting recipe icon, recipe display, 32x32" },
    @{ Id = "crafting_ingredient"; Name = "Crafting Ingredient"; Desc = "Crafting ingredient slot icon, ingredient slot, 32x32" },
    @{ Id = "crafting_result"; Name = "Crafting Result"; Desc = "Crafting result slot icon, result slot, 32x32" },
    @{ Id = "crafting_craft"; Name = "Craft Button"; Desc = "Craft button icon, craft action, 64x32" },
    @{ Id = "crafting_cancel"; Name = "Cancel Button"; Desc = "Cancel button icon, cancel action, 64x32" }
)

# Validate $ModPath before Join-Path
$craftingUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($craftingUIOutputDir)) {
    Write-Host "  [FAIL] craftingUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($craftingUIOutputDir)) {
    Write-Host "  [FAIL] craftingUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $craftingUIOutputDir)) {
    New-Item -ItemType Directory -Path $craftingUIOutputDir -Force | Out-Null
}

foreach ($ui in $craftingUI) {
    Write-Host "Generating crafting UI element: $($ui.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $ui.Id
            Prompt = "$($ui.Desc). Crafting UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $craftingUIOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($ui.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($ui.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. CAPTAIN'S CHAIR ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Captain's Chair Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$chairIcons = @(
    @{ Id = "captain_chair_icon"; Name = "Captain's Chair"; Desc = "Captain's chair icon, chair interface, 64x64" },
    @{ Id = "captain_chair_active"; Name = "Chair Active"; Desc = "Captain's chair active indicator, chair in use, 32x32" },
    @{ Id = "captain_chair_inactive"; Name = "Chair Inactive"; Desc = "Captain's chair inactive indicator, chair available, 32x32" },
    @{ Id = "captain_chair_pilot"; Name = "Pilot Seat"; Desc = "Pilot seat icon, pilot interface, 64x64" },
    @{ Id = "captain_chair_command"; Name = "Command Chair"; Desc = "Command chair icon, command interface, 64x64" }
)

# Validate $ModPath before Join-Path
$chairOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($chairOutputDir)) {
    Write-Host "  [FAIL] chairOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($chairOutputDir)) {
    Write-Host "  [FAIL] chairOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $chairOutputDir)) {
    New-Item -ItemType Directory -Path $chairOutputDir -Force | Out-Null
}

foreach ($icon in $chairIcons) {
    Write-Host "Generating chair icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Captain's chair icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $chairOutputDir
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

# ============================================================
# 5. HYPERDRIVE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Hyperdrive Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$hyperdriveEffects = @(
    @{ Id = "hyperdrive_jump_effect"; Name = "Hyperdrive Jump"; Desc = "Hyperdrive jump particle effect, jump initiation" },
    @{ Id = "hyperdrive_travel"; Name = "Hyperdrive Travel"; Desc = "Hyperdrive travel particle effect, in transit" },
    @{ Id = "hyperdrive_arrival"; Name = "Hyperdrive Arrival"; Desc = "Hyperdrive arrival particle effect, jump completion" },
    @{ Id = "hyperdrive_warmup"; Name = "Hyperdrive Warmup"; Desc = "Hyperdrive warmup particle effect, system warming up" },
    @{ Id = "hyperdrive_cooldown"; Name = "Hyperdrive Cooldown"; Desc = "Hyperdrive cooldown particle effect, system cooling down" },
    @{ Id = "hyperdrive_icon"; Name = "Hyperdrive Icon"; Desc = "Hyperdrive icon, hyperdrive interface, 64x64" }
)

# Validate $ModPath before Join-Path
$hyperdriveOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($hyperdriveOutputDir)) {
    Write-Host "  [FAIL] hyperdriveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($hyperdriveOutputDir)) {
    Write-Host "  [FAIL] hyperdriveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $hyperdriveOutputDir)) {
    New-Item -ItemType Directory -Path $hyperdriveOutputDir -Force | Out-Null
}

foreach ($effect in $hyperdriveEffects) {
    Write-Host "Generating hyperdrive effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($effect.Id -like "*icon*") { "Icon" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Hyperdrive effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $hyperdriveOutputDir
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
Write-Host "  Plugin UI: $(Join-Path $ModPath 'assets\plugins\ui')" -ForegroundColor Gray
Write-Host "  Interface UI: $(Join-Path $ModPath 'assets\plugins\interface')" -ForegroundColor Gray
Write-Host "  Crafting UI: $(Join-Path $ModPath 'assets\plugins\crafting')" -ForegroundColor Gray
Write-Host "  Captain's Chair: $(Join-Path $ModPath 'assets\plugins\captain_chair')" -ForegroundColor Gray
Write-Host "  Hyperdrive: $(Join-Path $ModPath 'assets\plugins\hyperdrive')" -ForegroundColor Gray
Write-Host ""
