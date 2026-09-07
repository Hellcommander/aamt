#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the InventoryAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Inventory UI panels and buttons
    - Slot icons (empty, occupied, locked, etc.)
    - Container sprites (bags, chests, etc.)
    - Quick access bar elements
    - Equipment preset icons
    - Sorting/filtering UI elements
    - Weight/volume indicators
    - Transfer indicators
    - Stack indicators
    - Tooltip elements
    - Search UI elements
    
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
Write-Host "  InventoryAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. INVENTORY UI PANELS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Inventory UI Panels" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiPanels = @(
    @{ Id = "panel_inventory"; Name = "Inventory Panel"; Desc = "Inventory panel background, inventory UI panel, 256x256" },
    @{ Id = "panel_container"; Name = "Container Panel"; Desc = "Container panel background, container UI panel, 256x256" },
    @{ Id = "panel_quick_access"; Name = "Quick Access Panel"; Desc = "Quick access panel background, quick access UI panel, 128x64" },
    @{ Id = "panel_equipment"; Name = "Equipment Panel"; Desc = "Equipment panel background, equipment UI panel, 128x256" },
    @{ Id = "panel_tooltip"; Name = "Tooltip Panel"; Desc = "Tooltip panel background, tooltip UI panel, 128x128" }
)

# Validate $ModPath before Join-Path
$panelOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($panelOutputDir)) {
    Write-Host "  [FAIL] panelOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($panelOutputDir)) {
    Write-Host "  [FAIL] panelOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $panelOutputDir)) {
    New-Item -ItemType Directory -Path $panelOutputDir -Force | Out-Null
}

foreach ($panel in $uiPanels) {
    Write-Host "Generating UI panel: $($panel.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $panel.Id
            Prompt = "$($panel.Desc). Inventory UI panel for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $panelOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($panel.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($panel.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. INVENTORY UI BUTTONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Inventory UI Buttons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiButtons = @(
    @{ Id = "button_sort"; Name = "Sort Button"; Desc = "Sort button icon, sort items, 32x32" },
    @{ Id = "button_filter"; Name = "Filter Button"; Desc = "Filter button icon, filter items, 32x32" },
    @{ Id = "button_stack"; Name = "Stack Button"; Desc = "Stack button icon, stack items, 32x32" },
    @{ Id = "button_transfer"; Name = "Transfer Button"; Desc = "Transfer button icon, transfer items, 32x32" },
    @{ Id = "button_search"; Name = "Search Button"; Desc = "Search button icon, search items, 32x32" },
    @{ Id = "button_close"; Name = "Close Button"; Desc = "Close button icon, close inventory, 32x32" },
    @{ Id = "button_save_preset"; Name = "Save Preset Button"; Desc = "Save preset button icon, save equipment preset, 32x32" },
    @{ Id = "button_load_preset"; Name = "Load Preset Button"; Desc = "Load preset button icon, load equipment preset, 32x32" }
)

# Validate $ModPath before Join-Path
$buttonOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($buttonOutputDir)) {
    Write-Host "  [FAIL] buttonOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($buttonOutputDir)) {
    Write-Host "  [FAIL] buttonOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $buttonOutputDir)) {
    New-Item -ItemType Directory -Path $buttonOutputDir -Force | Out-Null
}

foreach ($button in $uiButtons) {
    Write-Host "Generating UI button: $($button.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $button.Id
            Prompt = "$($button.Desc). Inventory UI button for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $buttonOutputDir
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

# ============================================================
# 3. SLOT ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Slot Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$slotIcons = @(
    @{ Id = "slot_empty"; Name = "Empty Slot"; Desc = "Empty inventory slot icon, empty slot, 32x32" },
    @{ Id = "slot_occupied"; Name = "Occupied Slot"; Desc = "Occupied inventory slot icon, occupied slot, 32x32" },
    @{ Id = "slot_locked"; Name = "Locked Slot"; Desc = "Locked inventory slot icon, locked slot, 32x32" },
    @{ Id = "slot_highlighted"; Name = "Highlighted Slot"; Desc = "Highlighted inventory slot icon, highlighted slot, 32x32" },
    @{ Id = "slot_selected"; Name = "Selected Slot"; Desc = "Selected inventory slot icon, selected slot, 32x32" },
    @{ Id = "slot_stackable"; Name = "Stackable Slot"; Desc = "Stackable inventory slot icon, stackable slot, 32x32" }
)

# Validate $ModPath before Join-Path
$slotOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($slotOutputDir)) {
    Write-Host "  [FAIL] slotOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($slotOutputDir)) {
    Write-Host "  [FAIL] slotOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $slotOutputDir)) {
    New-Item -ItemType Directory -Path $slotOutputDir -Force | Out-Null
}

foreach ($icon in $slotIcons) {
    Write-Host "Generating slot icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Inventory slot icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $slotOutputDir
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
# 4. CONTAINER SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Container Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$containers = @(
    @{ Id = "container_bag"; Name = "Bag Container"; Desc = "Bag container sprite, inventory bag, 32x32" },
    @{ Id = "container_chest"; Name = "Chest Container"; Desc = "Chest container sprite, storage chest, 32x32" },
    @{ Id = "container_backpack"; Name = "Backpack Container"; Desc = "Backpack container sprite, backpack, 32x32" },
    @{ Id = "container_pouch"; Name = "Pouch Container"; Desc = "Pouch container sprite, item pouch, 32x32" },
    @{ Id = "container_shared"; Name = "Shared Container"; Desc = "Shared container sprite, shared storage, 32x32" },
    @{ Id = "container_equipment"; Name = "Equipment Container"; Desc = "Equipment container sprite, equipment storage, 32x32" }
)

# Validate $ModPath before Join-Path
$containerOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($containerOutputDir)) {
    Write-Host "  [FAIL] containerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($containerOutputDir)) {
    Write-Host "  [FAIL] containerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $containerOutputDir)) {
    New-Item -ItemType Directory -Path $containerOutputDir -Force | Out-Null
}

foreach ($container in $containers) {
    Write-Host "Generating container: $($container.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $container.Id
            Prompt = "$($container.Desc). Container sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $containerOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($container.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($container.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. QUICK ACCESS BAR ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Quick Access Bar Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$quickAccessElements = @(
    @{ Id = "quick_access_slot"; Name = "Quick Access Slot"; Desc = "Quick access slot icon, quick access slot, 32x32" },
    @{ Id = "quick_access_active"; Name = "Active Quick Access"; Desc = "Active quick access indicator, active slot, 32x32" },
    @{ Id = "quick_access_bar"; Name = "Quick Access Bar"; Desc = "Quick access bar background, quick access bar, 128x32" }
)

# Validate $ModPath before Join-Path
$quickAccessOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($quickAccessOutputDir)) {
    Write-Host "  [FAIL] quickAccessOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($quickAccessOutputDir)) {
    Write-Host "  [FAIL] quickAccessOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $quickAccessOutputDir)) {
    New-Item -ItemType Directory -Path $quickAccessOutputDir -Force | Out-Null
}

foreach ($element in $quickAccessElements) {
    Write-Host "Generating quick access element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*bar*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Quick access bar element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $quickAccessOutputDir
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
# 6. EQUIPMENT PRESET ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Equipment Preset Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$presetIcons = @(
    @{ Id = "preset_combat"; Name = "Combat Preset"; Desc = "Combat equipment preset icon, combat preset, 32x32" },
    @{ Id = "preset_exploration"; Name = "Exploration Preset"; Desc = "Exploration equipment preset icon, exploration preset, 32x32" },
    @{ Id = "preset_crafting"; Name = "Crafting Preset"; Desc = "Crafting equipment preset icon, crafting preset, 32x32" },
    @{ Id = "preset_custom"; Name = "Custom Preset"; Desc = "Custom equipment preset icon, custom preset, 32x32" },
    @{ Id = "preset_save"; Name = "Save Preset"; Desc = "Save preset icon, save equipment preset, 32x32" },
    @{ Id = "preset_load"; Name = "Load Preset"; Desc = "Load preset icon, load equipment preset, 32x32" }
)

# Validate $ModPath before Join-Path
$presetOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($presetOutputDir)) {
    Write-Host "  [FAIL] presetOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($presetOutputDir)) {
    Write-Host "  [FAIL] presetOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $presetOutputDir)) {
    New-Item -ItemType Directory -Path $presetOutputDir -Force | Out-Null
}

foreach ($icon in $presetIcons) {
    Write-Host "Generating preset icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Equipment preset icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $presetOutputDir
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
# 7. SORTING/FILTERING UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Sorting/Filtering UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$sortFilterElements = @(
    @{ Id = "sort_name"; Name = "Sort by Name"; Desc = "Sort by name icon, name sorting, 32x32" },
    @{ Id = "sort_value"; Name = "Sort by Value"; Desc = "Sort by value icon, value sorting, 32x32" },
    @{ Id = "sort_weight"; Name = "Sort by Weight"; Desc = "Sort by weight icon, weight sorting, 32x32" },
    @{ Id = "sort_category"; Name = "Sort by Category"; Desc = "Sort by category icon, category sorting, 32x32" },
    @{ Id = "sort_rarity"; Name = "Sort by Rarity"; Desc = "Sort by rarity icon, rarity sorting, 32x32" },
    @{ Id = "filter_category"; Name = "Category Filter"; Desc = "Category filter icon, category filter, 32x32" },
    @{ Id = "filter_rarity"; Name = "Rarity Filter"; Desc = "Rarity filter icon, rarity filter, 32x32" },
    @{ Id = "filter_tag"; Name = "Tag Filter"; Desc = "Tag filter icon, tag filter, 32x32" },
    @{ Id = "filter_clear"; Name = "Clear Filter"; Desc = "Clear filter icon, clear filters, 32x32" }
)

# Validate $ModPath before Join-Path
$sortFilterOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($sortFilterOutputDir)) {
    Write-Host "  [FAIL] sortFilterOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($sortFilterOutputDir)) {
    Write-Host "  [FAIL] sortFilterOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $sortFilterOutputDir)) {
    New-Item -ItemType Directory -Path $sortFilterOutputDir -Force | Out-Null
}

foreach ($element in $sortFilterElements) {
    Write-Host "Generating sort/filter element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $element.Id
            Prompt = "$($element.Desc). Sorting/filtering UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $sortFilterOutputDir
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
# 8. WEIGHT/VOLUME INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weight/Volume Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weightVolumeIndicators = @(
    @{ Id = "indicator_weight"; Name = "Weight Indicator"; Desc = "Weight indicator icon, weight display, 32x32" },
    @{ Id = "indicator_volume"; Name = "Volume Indicator"; Desc = "Volume indicator icon, volume display, 32x32" },
    @{ Id = "indicator_weight_low"; Name = "Low Weight"; Desc = "Low weight indicator, weight low, 32x32" },
    @{ Id = "indicator_weight_medium"; Name = "Medium Weight"; Desc = "Medium weight indicator, weight medium, 32x32" },
    @{ Id = "indicator_weight_high"; Name = "High Weight"; Desc = "High weight indicator, weight high, 32x32" },
    @{ Id = "indicator_weight_full"; Name = "Weight Full"; Desc = "Weight full indicator, weight limit reached, 32x32" },
    @{ Id = "indicator_volume_full"; Name = "Volume Full"; Desc = "Volume full indicator, volume limit reached, 32x32" }
)

# Validate $ModPath before Join-Path
$weightVolumeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($weightVolumeOutputDir)) {
    Write-Host "  [FAIL] weightVolumeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($weightVolumeOutputDir)) {
    Write-Host "  [FAIL] weightVolumeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $weightVolumeOutputDir)) {
    New-Item -ItemType Directory -Path $weightVolumeOutputDir -Force | Out-Null
}

foreach ($indicator in $weightVolumeIndicators) {
    Write-Host "Generating weight/volume indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Weight/volume indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $weightVolumeOutputDir
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
# 9. TRANSFER INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Transfer Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$transferIndicators = @(
    @{ Id = "transfer_arrow"; Name = "Transfer Arrow"; Desc = "Transfer arrow icon, transfer direction, 32x32" },
    @{ Id = "transfer_success"; Name = "Transfer Success"; Desc = "Transfer success indicator, transfer successful, 32x32" },
    @{ Id = "transfer_failed"; Name = "Transfer Failed"; Desc = "Transfer failed indicator, transfer failed, 32x32" },
    @{ Id = "transfer_in_progress"; Name = "Transfer In Progress"; Desc = "Transfer in progress indicator, transferring, 32x32" },
    @{ Id = "transfer_all"; Name = "Transfer All"; Desc = "Transfer all indicator, transfer all items, 32x32" }
)

# Validate $ModPath before Join-Path
$transferOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($transferOutputDir)) {
    Write-Host "  [FAIL] transferOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($transferOutputDir)) {
    Write-Host "  [FAIL] transferOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $transferOutputDir)) {
    New-Item -ItemType Directory -Path $transferOutputDir -Force | Out-Null
}

foreach ($indicator in $transferIndicators) {
    Write-Host "Generating transfer indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Transfer indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $transferOutputDir
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
# 10. STACK INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Stack Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stackIndicators = @(
    @{ Id = "stack_indicator"; Name = "Stack Indicator"; Desc = "Stack indicator icon, item stack, 16x16" },
    @{ Id = "stack_full"; Name = "Stack Full"; Desc = "Stack full indicator, stack at max, 16x16" },
    @{ Id = "stack_partial"; Name = "Stack Partial"; Desc = "Stack partial indicator, partial stack, 16x16" },
    @{ Id = "stack_auto"; Name = "Auto Stack"; Desc = "Auto stack indicator, auto stacking, 32x32" }
)

# Validate $ModPath before Join-Path
$stackOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stackOutputDir)) {
    Write-Host "  [FAIL] stackOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stackOutputDir)) {
    Write-Host "  [FAIL] stackOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stackOutputDir)) {
    New-Item -ItemType Directory -Path $stackOutputDir -Force | Out-Null
}

foreach ($indicator in $stackIndicators) {
    Write-Host "Generating stack indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Stack indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stackOutputDir
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
# 11. TOOLTIP ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Tooltip Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tooltipElements = @(
    @{ Id = "tooltip_background"; Name = "Tooltip Background"; Desc = "Tooltip background texture, tooltip panel, 128x128" },
    @{ Id = "tooltip_border"; Name = "Tooltip Border"; Desc = "Tooltip border texture, tooltip border, 128x128" },
    @{ Id = "tooltip_arrow"; Name = "Tooltip Arrow"; Desc = "Tooltip arrow icon, tooltip pointer, 16x16" },
    @{ Id = "tooltip_icon_stats"; Name = "Stats Icon"; Desc = "Item stats icon, item statistics, 16x16" },
    @{ Id = "tooltip_icon_description"; Name = "Description Icon"; Desc = "Item description icon, item description, 16x16" },
    @{ Id = "tooltip_icon_requirements"; Name = "Requirements Icon"; Desc = "Item requirements icon, item requirements, 16x16" },
    @{ Id = "tooltip_icon_effects"; Name = "Effects Icon"; Desc = "Item effects icon, item effects, 16x16" }
)

# Validate $ModPath before Join-Path
$tooltipOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tooltipOutputDir)) {
    Write-Host "  [FAIL] tooltipOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($tooltipOutputDir)) {
    Write-Host "  [FAIL] tooltipOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $tooltipOutputDir)) {
    New-Item -ItemType Directory -Path $tooltipOutputDir -Force | Out-Null
}

foreach ($element in $tooltipElements) {
    Write-Host "Generating tooltip element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*background*" -or $element.Id -like "*border*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Tooltip element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $tooltipOutputDir
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
# 12. SEARCH UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Search UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$searchElements = @(
    @{ Id = "search_box"; Name = "Search Box"; Desc = "Search box background, search input, 128x32" },
    @{ Id = "search_icon"; Name = "Search Icon"; Desc = "Search icon, search, 32x32" },
    @{ Id = "search_clear"; Name = "Clear Search"; Desc = "Clear search icon, clear search, 16x16" },
    @{ Id = "search_results"; Name = "Search Results"; Desc = "Search results indicator, search results, 32x32" }
)

# Validate $ModPath before Join-Path
$searchOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($searchOutputDir)) {
    Write-Host "  [FAIL] searchOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($searchOutputDir)) {
    Write-Host "  [FAIL] searchOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $searchOutputDir)) {
    New-Item -ItemType Directory -Path $searchOutputDir -Force | Out-Null
}

foreach ($element in $searchElements) {
    Write-Host "Generating search element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*box*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Search UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $searchOutputDir
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
Write-Host "  UI Panels: $(Join-Path $ModPath 'assets\inventory\ui\panels')" -ForegroundColor Gray
Write-Host "  UI Buttons: $(Join-Path $ModPath 'assets\inventory\ui\buttons')" -ForegroundColor Gray
Write-Host "  Slots: $(Join-Path $ModPath 'assets\inventory\slots')" -ForegroundColor Gray
Write-Host "  Containers: $(Join-Path $ModPath 'assets\inventory\containers')" -ForegroundColor Gray
Write-Host "  Quick Access: $(Join-Path $ModPath 'assets\inventory\quick_access')" -ForegroundColor Gray
Write-Host "  Presets: $(Join-Path $ModPath 'assets\inventory\presets')" -ForegroundColor Gray
Write-Host "  Sort/Filter: $(Join-Path $ModPath 'assets\inventory\sort_filter')" -ForegroundColor Gray
Write-Host "  Weight/Volume: $(Join-Path $ModPath 'assets\inventory\weight_volume')" -ForegroundColor Gray
Write-Host "  Transfer: $(Join-Path $ModPath 'assets\inventory\transfer')" -ForegroundColor Gray
Write-Host "  Stack: $(Join-Path $ModPath 'assets\inventory\stack')" -ForegroundColor Gray
Write-Host "  Tooltips: $(Join-Path $ModPath 'assets\inventory\tooltips')" -ForegroundColor Gray
Write-Host "  Search: $(Join-Path $ModPath 'assets\inventory\search')" -ForegroundColor Gray
Write-Host ""
