#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the CompositionAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Node type icons (Shape, Effect, Modifier, Control, Trigger, VFX, SFX, ChanceTrigger)
    - Tree visualization elements (connections, branches, nodes)
    - Composition UI elements (editor panels, buttons, controls)
    - Template icons
    - Metrics display elements
    - Simulation preview elements
    - Validation indicators
    - Cache indicators
    - Performance monitoring UI elements
    
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
Write-Host "  CompositionAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. NODE TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Node Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$nodeTypes = @(
    @{ Id = "node_shape"; Name = "Shape Node"; Desc = "Shape node icon, spell shape node, 32x32" },
    @{ Id = "node_effect"; Name = "Effect Node"; Desc = "Effect node icon, spell effect node, 32x32" },
    @{ Id = "node_modifier"; Name = "Modifier Node"; Desc = "Modifier node icon, spell modifier node, 32x32" },
    @{ Id = "node_control"; Name = "Control Node"; Desc = "Control node icon, spell control node, 32x32" },
    @{ Id = "node_trigger"; Name = "Trigger Node"; Desc = "Trigger node icon, spell trigger node, 32x32" },
    @{ Id = "node_vfx"; Name = "VFX Node"; Desc = "VFX node icon, visual effects node, 32x32" },
    @{ Id = "node_sfx"; Name = "SFX Node"; Desc = "SFX node icon, sound effects node, 32x32" },
    @{ Id = "node_chance_trigger"; Name = "Chance Trigger Node"; Desc = "Chance trigger node icon, probabilistic trigger node, 32x32" }
)

# Validate $ModPath before Join-Path
$nodeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($nodeOutputDir)) {
    Write-Host "  [FAIL] nodeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($nodeOutputDir)) {
    Write-Host "  [FAIL] nodeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $nodeOutputDir)) {
    New-Item -ItemType Directory -Path $nodeOutputDir -Force | Out-Null
}

foreach ($node in $nodeTypes) {
    Write-Host "Generating node icon: $($node.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $node.Id
            Prompt = "$($node.Desc). Composition node icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $nodeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($node.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($node.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. SHAPE TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Shape Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$shapeTypes = @(
    @{ Id = "shape_projectile"; Name = "Projectile Shape"; Desc = "Projectile shape icon, projectile spell shape, 32x32" },
    @{ Id = "shape_beam"; Name = "Beam Shape"; Desc = "Beam shape icon, beam spell shape, 32x32" },
    @{ Id = "shape_aoe"; Name = "AOE Shape"; Desc = "AOE shape icon, area of effect spell shape, 32x32" },
    @{ Id = "shape_root"; Name = "Root Shape"; Desc = "Root shape icon, root spell shape, 32x32" }
)

# Validate $ModPath before Join-Path
$shapeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($shapeOutputDir)) {
    Write-Host "  [FAIL] shapeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $shapeOutputDir)) {
    New-Item -ItemType Directory -Path $shapeOutputDir -Force | Out-Null
}

foreach ($shape in $shapeTypes) {
    Write-Host "Generating shape icon: $($shape.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $shape.Id
            Prompt = "$($shape.Desc). Spell shape icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $shapeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($shape.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($shape.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. EFFECT TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Effect Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$effectTypes = @(
    @{ Id = "effect_damage_fire"; Name = "Fire Damage Effect"; Desc = "Fire damage effect icon, fire damage spell effect, 32x32" },
    @{ Id = "effect_heal"; Name = "Heal Effect"; Desc = "Heal effect icon, healing spell effect, 32x32" },
    @{ Id = "effect_status_freeze"; Name = "Freeze Status Effect"; Desc = "Freeze status effect icon, freeze status spell effect, 32x32" },
    @{ Id = "effect_damage_ice"; Name = "Ice Damage Effect"; Desc = "Ice damage effect icon, ice damage spell effect, 32x32" },
    @{ Id = "effect_damage_lightning"; Name = "Lightning Damage Effect"; Desc = "Lightning damage effect icon, lightning damage spell effect, 32x32" }
)

# Validate $ModPath before Join-Path
$effectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($effectOutputDir)) {
    Write-Host "  [FAIL] effectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($effectOutputDir)) {
    Write-Host "  [FAIL] effectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $effectOutputDir)) {
    New-Item -ItemType Directory -Path $effectOutputDir -Force | Out-Null
}

foreach ($effect in $effectTypes) {
    Write-Host "Generating effect icon: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Spell effect icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $effectOutputDir
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
# 4. MODIFIER TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Modifier Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$modifierTypes = @(
    @{ Id = "modifier_bounce"; Name = "Bounce Modifier"; Desc = "Bounce modifier icon, bounce spell modifier, 32x32" },
    @{ Id = "modifier_chain"; Name = "Chain Modifier"; Desc = "Chain modifier icon, chain spell modifier, 32x32" },
    @{ Id = "modifier_repeat"; Name = "Repeat Modifier"; Desc = "Repeat modifier icon, repeat spell modifier, 32x32" }
)

# Validate $ModPath before Join-Path
$modifierOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($modifierOutputDir)) {
    Write-Host "  [FAIL] modifierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($modifierOutputDir)) {
    Write-Host "  [FAIL] modifierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $modifierOutputDir)) {
    New-Item -ItemType Directory -Path $modifierOutputDir -Force | Out-Null
}

foreach ($modifier in $modifierTypes) {
    Write-Host "Generating modifier icon: $($modifier.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $modifier.Id
            Prompt = "$($modifier.Desc). Spell modifier icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $modifierOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($modifier.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($modifier.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. TREE VISUALIZATION ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Tree Visualization Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$treeElements = @(
    @{ Id = "tree_connection"; Name = "Tree Connection"; Desc = "Tree connection line, node connection, 64x8" },
    @{ Id = "tree_branch"; Name = "Tree Branch"; Desc = "Tree branch line, node branch, 64x8" },
    @{ Id = "tree_node_background"; Name = "Node Background"; Desc = "Node background, node container, 64x64" },
    @{ Id = "tree_root"; Name = "Tree Root"; Desc = "Tree root indicator, root node, 32x32" },
    @{ Id = "tree_leaf"; Name = "Tree Leaf"; Desc = "Tree leaf indicator, leaf node, 32x32" },
    @{ Id = "tree_collapsed"; Name = "Collapsed Node"; Desc = "Collapsed node indicator, collapsed tree node, 32x32" },
    @{ Id = "tree_expanded"; Name = "Expanded Node"; Desc = "Expanded node indicator, expanded tree node, 32x32" }
)

# Validate $ModPath before Join-Path
$treeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($treeOutputDir)) {
    Write-Host "  [FAIL] treeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($treeOutputDir)) {
    Write-Host "  [FAIL] treeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $treeOutputDir)) {
    New-Item -ItemType Directory -Path $treeOutputDir -Force | Out-Null
}

foreach ($element in $treeElements) {
    Write-Host "Generating tree element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*connection*" -or $element.Id -like "*branch*" -or $element.Id -like "*background*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Tree visualization element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $treeOutputDir
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
# 6. COMPOSITION UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Composition UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{ Id = "ui_panel_composition"; Name = "Composition Panel"; Desc = "Composition editor panel background, composition UI panel, 256x256" },
    @{ Id = "ui_panel_tree_view"; Name = "Tree View Panel"; Desc = "Tree view panel background, tree view UI panel, 256x256" },
    @{ Id = "ui_panel_metrics"; Name = "Metrics Panel"; Desc = "Metrics panel background, metrics UI panel, 128x128" },
    @{ Id = "ui_panel_simulation"; Name = "Simulation Panel"; Desc = "Simulation panel background, simulation UI panel, 128x128" },
    @{ Id = "ui_button_create_node"; Name = "Create Node Button"; Desc = "Create node button icon, create node, 32x32" },
    @{ Id = "ui_button_delete_node"; Name = "Delete Node Button"; Desc = "Delete node button icon, delete node, 32x32" },
    @{ Id = "ui_button_connect"; Name = "Connect Button"; Desc = "Connect nodes button icon, connect nodes, 32x32" },
    @{ Id = "ui_button_disconnect"; Name = "Disconnect Button"; Desc = "Disconnect nodes button icon, disconnect nodes, 32x32" },
    @{ Id = "ui_button_validate"; Name = "Validate Button"; Desc = "Validate tree button icon, validate tree, 32x32" },
    @{ Id = "ui_button_optimize"; Name = "Optimize Button"; Desc = "Optimize tree button icon, optimize tree, 32x32" },
    @{ Id = "ui_button_simulate"; Name = "Simulate Button"; Desc = "Simulate button icon, simulate spell, 32x32" },
    @{ Id = "ui_button_save_template"; Name = "Save Template Button"; Desc = "Save template button icon, save template, 32x32" },
    @{ Id = "ui_button_load_template"; Name = "Load Template Button"; Desc = "Load template button icon, load template, 32x32" },
    @{ Id = "ui_button_export"; Name = "Export Button"; Desc = "Export button icon, export tree, 32x32" },
    @{ Id = "ui_button_import"; Name = "Import Button"; Desc = "Import button icon, import tree, 32x32" }
)

# Validate $ModPath before Join-Path
$uiOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $uiOutputDir)) {
    New-Item -ItemType Directory -Path $uiOutputDir -Force | Out-Null
}

foreach ($element in $uiElements) {
    Write-Host "Generating UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*panel*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Composition UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $uiOutputDir
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
# 7. TEMPLATE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Template Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$templateIcons = @(
    @{ Id = "template_basic"; Name = "Basic Template"; Desc = "Basic spell template icon, basic template, 32x32" },
    @{ Id = "template_advanced"; Name = "Advanced Template"; Desc = "Advanced spell template icon, advanced template, 32x32" },
    @{ Id = "template_custom"; Name = "Custom Template"; Desc = "Custom spell template icon, custom template, 32x32" },
    @{ Id = "template_save"; Name = "Save Template"; Desc = "Save template icon, save template, 32x32" },
    @{ Id = "template_load"; Name = "Load Template"; Desc = "Load template icon, load template, 32x32" }
)

# Validate $ModPath before Join-Path
$templateOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($templateOutputDir)) {
    Write-Host "  [FAIL] templateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($templateOutputDir)) {
    Write-Host "  [FAIL] templateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $templateOutputDir)) {
    New-Item -ItemType Directory -Path $templateOutputDir -Force | Out-Null
}

foreach ($icon in $templateIcons) {
    Write-Host "Generating template icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Spell template icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $templateOutputDir
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
# 8. METRICS DISPLAY ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Metrics Display Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$metricsElements = @(
    @{ Id = "metrics_mana_cost"; Name = "Mana Cost"; Desc = "Mana cost indicator icon, mana cost metric, 32x32" },
    @{ Id = "metrics_cooldown"; Name = "Cooldown"; Desc = "Cooldown indicator icon, cooldown metric, 32x32" },
    @{ Id = "metrics_damage"; Name = "Damage"; Desc = "Damage indicator icon, damage metric, 32x32" },
    @{ Id = "metrics_area"; Name = "Area"; Desc = "Area indicator icon, area metric, 32x32" },
    @{ Id = "metrics_cc_time"; Name = "Crowd Control Time"; Desc = "Crowd control time indicator icon, CC time metric, 32x32" },
    @{ Id = "metrics_heal"; Name = "Heal"; Desc = "Heal indicator icon, heal metric, 32x32" },
    @{ Id = "metrics_targets"; Name = "Targets Hit"; Desc = "Targets hit indicator icon, targets metric, 32x32" }
)

# Validate $ModPath before Join-Path
$metricsOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($metricsOutputDir)) {
    Write-Host "  [FAIL] metricsOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($metricsOutputDir)) {
    Write-Host "  [FAIL] metricsOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $metricsOutputDir)) {
    New-Item -ItemType Directory -Path $metricsOutputDir -Force | Out-Null
}

foreach ($element in $metricsElements) {
    Write-Host "Generating metrics element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $element.Id
            Prompt = "$($element.Desc). Metrics display element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $metricsOutputDir
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
# 9. SIMULATION PREVIEW ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Simulation Preview Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$simulationElements = @(
    @{ Id = "simulation_play"; Name = "Play Simulation"; Desc = "Play simulation button icon, play simulation, 32x32" },
    @{ Id = "simulation_pause"; Name = "Pause Simulation"; Desc = "Pause simulation button icon, pause simulation, 32x32" },
    @{ Id = "simulation_stop"; Name = "Stop Simulation"; Desc = "Stop simulation button icon, stop simulation, 32x32" },
    @{ Id = "simulation_reset"; Name = "Reset Simulation"; Desc = "Reset simulation button icon, reset simulation, 32x32" },
    @{ Id = "simulation_preview"; Name = "Simulation Preview"; Desc = "Simulation preview background, simulation preview, 128x128" }
)

# Validate $ModPath before Join-Path
$simulationOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($simulationOutputDir)) {
    Write-Host "  [FAIL] simulationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($simulationOutputDir)) {
    Write-Host "  [FAIL] simulationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $simulationOutputDir)) {
    New-Item -ItemType Directory -Path $simulationOutputDir -Force | Out-Null
}

foreach ($element in $simulationElements) {
    Write-Host "Generating simulation element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*preview*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Simulation preview element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $simulationOutputDir
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
# 10. VALIDATION INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Validation Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$validationIndicators = @(
    @{ Id = "validation_valid"; Name = "Valid"; Desc = "Valid indicator icon, validation passed, 32x32" },
    @{ Id = "validation_invalid"; Name = "Invalid"; Desc = "Invalid indicator icon, validation failed, 32x32" },
    @{ Id = "validation_warning"; Name = "Warning"; Desc = "Warning indicator icon, validation warning, 32x32" },
    @{ Id = "validation_error"; Name = "Error"; Desc = "Error indicator icon, validation error, 32x32" },
    @{ Id = "validation_circular"; Name = "Circular Reference"; Desc = "Circular reference indicator icon, circular reference detected, 32x32" }
)

# Validate $ModPath before Join-Path
$validationOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($validationOutputDir)) {
    Write-Host "  [FAIL] validationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($validationOutputDir)) {
    Write-Host "  [FAIL] validationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $validationOutputDir)) {
    New-Item -ItemType Directory -Path $validationOutputDir -Force | Out-Null
}

foreach ($indicator in $validationIndicators) {
    Write-Host "Generating validation indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Validation indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $validationOutputDir
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
# 11. CACHE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cache Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$cacheIndicators = @(
    @{ Id = "cache_metrics"; Name = "Metrics Cache"; Desc = "Metrics cache indicator icon, cached metrics, 32x32" },
    @{ Id = "cache_simulation"; Name = "Simulation Cache"; Desc = "Simulation cache indicator icon, cached simulation, 32x32" },
    @{ Id = "cache_hit"; Name = "Cache Hit"; Desc = "Cache hit indicator icon, cache hit, 32x32" },
    @{ Id = "cache_miss"; Name = "Cache Miss"; Desc = "Cache miss indicator icon, cache miss, 32x32" },
    @{ Id = "cache_clear"; Name = "Clear Cache"; Desc = "Clear cache button icon, clear cache, 32x32" }
)

# Validate $ModPath before Join-Path
$cacheOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($cacheOutputDir)) {
    Write-Host "  [FAIL] cacheOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cacheOutputDir)) {
    Write-Host "  [FAIL] cacheOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $cacheOutputDir)) {
    New-Item -ItemType Directory -Path $cacheOutputDir -Force | Out-Null
}

foreach ($indicator in $cacheIndicators) {
    Write-Host "Generating cache indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Cache indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $cacheOutputDir
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
# 12. PERFORMANCE MONITORING UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Performance Monitoring UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$performanceElements = @(
    @{ Id = "performance_memory"; Name = "Memory Usage"; Desc = "Memory usage indicator icon, memory usage, 32x32" },
    @{ Id = "performance_cpu"; Name = "CPU Usage"; Desc = "CPU usage indicator icon, CPU usage, 32x32" },
    @{ Id = "performance_processing_time"; Name = "Processing Time"; Desc = "Processing time indicator icon, processing time, 32x32" },
    @{ Id = "performance_cache_hit_rate"; Name = "Cache Hit Rate"; Desc = "Cache hit rate indicator icon, cache hit rate, 32x32" },
    @{ Id = "performance_stats"; Name = "Performance Stats"; Desc = "Performance stats panel background, performance stats, 128x128" }
)

# Validate $ModPath before Join-Path
$performanceOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($performanceOutputDir)) {
    Write-Host "  [FAIL] performanceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($performanceOutputDir)) {
    Write-Host "  [FAIL] performanceOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $performanceOutputDir)) {
    New-Item -ItemType Directory -Path $performanceOutputDir -Force | Out-Null
}

foreach ($element in $performanceElements) {
    Write-Host "Generating performance element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*stats*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Performance monitoring element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $performanceOutputDir
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
Write-Host "  Nodes: $(Join-Path $ModPath 'assets\composition\nodes')" -ForegroundColor Gray
Write-Host "  Shapes: $(Join-Path $ModPath 'assets\composition\shapes')" -ForegroundColor Gray
Write-Host "  Effects: $(Join-Path $ModPath 'assets\composition\effects')" -ForegroundColor Gray
Write-Host "  Modifiers: $(Join-Path $ModPath 'assets\composition\modifiers')" -ForegroundColor Gray
Write-Host "  Tree: $(Join-Path $ModPath 'assets\composition\tree')" -ForegroundColor Gray
Write-Host "  UI: $(Join-Path $ModPath 'assets\composition\ui')" -ForegroundColor Gray
Write-Host "  Templates: $(Join-Path $ModPath 'assets\composition\templates')" -ForegroundColor Gray
Write-Host "  Metrics: $(Join-Path $ModPath 'assets\composition\metrics')" -ForegroundColor Gray
Write-Host "  Simulation: $(Join-Path $ModPath 'assets\composition\simulation')" -ForegroundColor Gray
Write-Host "  Validation: $(Join-Path $ModPath 'assets\composition\validation')" -ForegroundColor Gray
Write-Host "  Cache: $(Join-Path $ModPath 'assets\composition\cache')" -ForegroundColor Gray
Write-Host "  Performance: $(Join-Path $ModPath 'assets\composition\performance')" -ForegroundColor Gray
Write-Host ""
