#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Enchantment System.
    
.DESCRIPTION
    Generates visual assets for:
    - Enchantment tier icons (Basic, Common, Uncommon, Rare, Epic, Legendary, Mythic, Divine)
    - Enchantment rarity icons (Common, Uncommon, Rare, Epic, Legendary, Mythic)
    - Enchantment category icons (Damage, Utility, Defensive, Environmental, Synergy, Risk, Stability, Corruption)
    - Enchantment trigger icons (combat, movement, environmental, social)
    - Enchantment effect visuals
    - Rune/glow effects
    - Enchantment UI elements
    - Mana indicators
    - Cooldown indicators
    - Synergy/conflict indicators
    
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
Write-Host "  Enchantment System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. ENCHANTMENT TIER ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Tier Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tiers = @(
    @{ Id = "tier_basic"; Name = "Basic Tier"; Desc = "Basic enchantment tier icon, tier 1, 32x32" },
    @{ Id = "tier_common"; Name = "Common Tier"; Desc = "Common enchantment tier icon, tier 2, 32x32" },
    @{ Id = "tier_uncommon"; Name = "Uncommon Tier"; Desc = "Uncommon enchantment tier icon, tier 3, 32x32" },
    @{ Id = "tier_rare"; Name = "Rare Tier"; Desc = "Rare enchantment tier icon, tier 4, 32x32" },
    @{ Id = "tier_epic"; Name = "Epic Tier"; Desc = "Epic enchantment tier icon, tier 5, 32x32" },
    @{ Id = "tier_legendary"; Name = "Legendary Tier"; Desc = "Legendary enchantment tier icon, tier 6, 32x32" },
    @{ Id = "tier_mythic"; Name = "Mythic Tier"; Desc = "Mythic enchantment tier icon, tier 7, 32x32" },
    @{ Id = "tier_divine"; Name = "Divine Tier"; Desc = "Divine enchantment tier icon, tier 8, 32x32" }
)

# Validate $ModPath before Join-Path
$tierOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tierOutputDir)) {
    Write-Host "  [FAIL] tierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($tierOutputDir)) {
    Write-Host "  [FAIL] tierOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $tierOutputDir)) {
    New-Item -ItemType Directory -Path $tierOutputDir -Force | Out-Null
}

foreach ($tier in $tiers) {
    Write-Host "Generating tier icon: $($tier.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $tier.Id
            Prompt = "$($tier.Desc). Enchantment tier icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $tierOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tier.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tier.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. ENCHANTMENT RARITY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Rarity Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$rarities = @(
    @{ Id = "rarity_common"; Name = "Common Rarity"; Desc = "Common enchantment rarity icon, common rarity, 32x32" },
    @{ Id = "rarity_uncommon"; Name = "Uncommon Rarity"; Desc = "Uncommon enchantment rarity icon, uncommon rarity, 32x32" },
    @{ Id = "rarity_rare"; Name = "Rare Rarity"; Desc = "Rare enchantment rarity icon, rare rarity, 32x32" },
    @{ Id = "rarity_epic"; Name = "Epic Rarity"; Desc = "Epic enchantment rarity icon, epic rarity, 32x32" },
    @{ Id = "rarity_legendary"; Name = "Legendary Rarity"; Desc = "Legendary enchantment rarity icon, legendary rarity, 32x32" },
    @{ Id = "rarity_mythic"; Name = "Mythic Rarity"; Desc = "Mythic enchantment rarity icon, mythic rarity, 32x32" }
)

# Validate $ModPath before Join-Path
$rarityOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($rarityOutputDir)) {
    Write-Host "  [FAIL] rarityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($rarityOutputDir)) {
    Write-Host "  [FAIL] rarityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $rarityOutputDir)) {
    New-Item -ItemType Directory -Path $rarityOutputDir -Force | Out-Null
}

foreach ($rarity in $rarities) {
    Write-Host "Generating rarity icon: $($rarity.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $rarity.Id
            Prompt = "$($rarity.Desc). Enchantment rarity icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $rarityOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($rarity.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($rarity.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. ENCHANTMENT CATEGORY ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Category Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$categories = @(
    @{ Id = "category_damage"; Name = "Damage Category"; Desc = "Damage enchantment category icon, damage category, 32x32" },
    @{ Id = "category_utility"; Name = "Utility Category"; Desc = "Utility enchantment category icon, utility category, 32x32" },
    @{ Id = "category_defensive"; Name = "Defensive Category"; Desc = "Defensive enchantment category icon, defensive category, 32x32" },
    @{ Id = "category_environmental"; Name = "Environmental Category"; Desc = "Environmental enchantment category icon, environmental category, 32x32" },
    @{ Id = "category_synergy"; Name = "Synergy Category"; Desc = "Synergy enchantment category icon, synergy category, 32x32" },
    @{ Id = "category_risk"; Name = "Risk Category"; Desc = "Risk enchantment category icon, risk category, 32x32" },
    @{ Id = "category_stability"; Name = "Stability Category"; Desc = "Stability enchantment category icon, stability category, 32x32" },
    @{ Id = "category_corruption"; Name = "Corruption Category"; Desc = "Corruption enchantment category icon, corruption category, 32x32" }
)

# Validate $ModPath before Join-Path
$categoryOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($categoryOutputDir)) {
    Write-Host "  [FAIL] categoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($categoryOutputDir)) {
    Write-Host "  [FAIL] categoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $categoryOutputDir)) {
    New-Item -ItemType Directory -Path $categoryOutputDir -Force | Out-Null
}

foreach ($category in $categories) {
    Write-Host "Generating category icon: $($category.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $category.Id
            Prompt = "$($category.Desc). Enchantment category icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $categoryOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($category.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($category.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. ENCHANTMENT TRIGGER ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Trigger Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$triggers = @(
    @{ Id = "trigger_on_hit"; Name = "On Hit Trigger"; Desc = "On hit trigger icon, hit target trigger, 32x32" },
    @{ Id = "trigger_on_damage"; Name = "On Damage Trigger"; Desc = "On damage trigger icon, receive damage trigger, 32x32" },
    @{ Id = "trigger_critical"; Name = "Critical Strike Trigger"; Desc = "Critical strike trigger icon, critical strike trigger, 32x32" },
    @{ Id = "trigger_block"; Name = "Block Trigger"; Desc = "Block trigger icon, block trigger, 32x32" },
    @{ Id = "trigger_dodge"; Name = "Dodge Trigger"; Desc = "Dodge trigger icon, dodge trigger, 32x32" },
    @{ Id = "trigger_kill"; Name = "Kill Trigger"; Desc = "Kill trigger icon, kill trigger, 32x32" },
    @{ Id = "trigger_move"; Name = "Move Trigger"; Desc = "Move trigger icon, movement trigger, 32x32" },
    @{ Id = "trigger_jump"; Name = "Jump Trigger"; Desc = "Jump trigger icon, jump trigger, 32x32" },
    @{ Id = "trigger_biome"; Name = "Biome Trigger"; Desc = "Biome trigger icon, enter biome trigger, 32x32" },
    @{ Id = "trigger_weather"; Name = "Weather Trigger"; Desc = "Weather trigger icon, weather change trigger, 32x32" },
    @{ Id = "trigger_time"; Name = "Time Trigger"; Desc = "Time trigger icon, time of day trigger, 32x32" },
    @{ Id = "trigger_custom"; Name = "Custom Trigger"; Desc = "Custom trigger icon, custom event trigger, 32x32" }
)

# Validate $ModPath before Join-Path
$triggerOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($triggerOutputDir)) {
    Write-Host "  [FAIL] triggerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($triggerOutputDir)) {
    Write-Host "  [FAIL] triggerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $triggerOutputDir)) {
    New-Item -ItemType Directory -Path $triggerOutputDir -Force | Out-Null
}

foreach ($trigger in $triggers) {
    Write-Host "Generating trigger icon: $($trigger.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $trigger.Id
            Prompt = "$($trigger.Desc). Enchantment trigger icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $triggerOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($trigger.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($trigger.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. ENCHANTMENT EFFECT VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Effect Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$effects = @(
    @{ Id = "effect_apply"; Name = "Apply Effect"; Desc = "Enchantment apply particle effect, enchantment applied visual, 64x64" },
    @{ Id = "effect_remove"; Name = "Remove Effect"; Desc = "Enchantment remove particle effect, enchantment removed visual, 64x64" },
    @{ Id = "effect_active"; Name = "Active Effect"; Desc = "Active enchantment particle effect, active enchantment visual, 64x64" },
    @{ Id = "effect_trigger"; Name = "Trigger Effect"; Desc = "Enchantment trigger particle effect, trigger activated visual, 64x64" },
    @{ Id = "effect_synergy"; Name = "Synergy Effect"; Desc = "Synergy particle effect, synergy activated visual, 64x64" },
    @{ Id = "effect_conflict"; Name = "Conflict Effect"; Desc = "Conflict particle effect, conflict activated visual, 64x64" }
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

foreach ($effect in $effects) {
    Write-Host "Generating effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Enchantment effect for Starbound."
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
# 6. RUNE/GLOW EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Rune/Glow Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$runes = @(
    @{ Id = "rune_basic"; Name = "Basic Rune"; Desc = "Basic enchantment rune texture, basic rune, 64x64" },
    @{ Id = "rune_common"; Name = "Common Rune"; Desc = "Common enchantment rune texture, common rune, 64x64" },
    @{ Id = "rune_rare"; Name = "Rare Rune"; Desc = "Rare enchantment rune texture, rare rune, 64x64" },
    @{ Id = "rune_epic"; Name = "Epic Rune"; Desc = "Epic enchantment rune texture, epic rune, 64x64" },
    @{ Id = "rune_legendary"; Name = "Legendary Rune"; Desc = "Legendary enchantment rune texture, legendary rune, 64x64" },
    @{ Id = "glow_active"; Name = "Active Glow"; Desc = "Active enchantment glow particle effect, active glow visual, 64x64" },
    @{ Id = "glow_charging"; Name = "Charging Glow"; Desc = "Charging enchantment glow particle effect, charging glow visual, 64x64" },
    @{ Id = "glow_ready"; Name = "Ready Glow"; Desc = "Ready enchantment glow particle effect, ready glow visual, 64x64" }
)

# Validate $ModPath before Join-Path
$runeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($runeOutputDir)) {
    Write-Host "  [FAIL] runeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($runeOutputDir)) {
    Write-Host "  [FAIL] runeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $runeOutputDir)) {
    New-Item -ItemType Directory -Path $runeOutputDir -Force | Out-Null
}

foreach ($rune in $runes) {
    Write-Host "Generating rune/glow: $($rune.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($rune.Id -like "*glow*") { "Particle" } else { "Texture" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $rune.Id
            Prompt = "$($rune.Desc). Enchantment rune/glow for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $runeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($rune.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($rune.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. ENCHANTMENT UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiElements = @(
    @{ Id = "ui_panel_enchantment"; Name = "Enchantment Panel"; Desc = "Enchantment panel background, enchantment UI panel, 256x256" },
    @{ Id = "ui_panel_slots"; Name = "Enchantment Slots Panel"; Desc = "Enchantment slots panel background, slot management panel, 128x128" },
    @{ Id = "ui_slot_enchantment"; Name = "Enchantment Slot"; Desc = "Enchantment slot background, enchantment slot, 32x32" },
    @{ Id = "ui_slot_empty"; Name = "Empty Slot"; Desc = "Empty enchantment slot background, empty slot, 32x32" },
    @{ Id = "ui_slot_locked"; Name = "Locked Slot"; Desc = "Locked enchantment slot background, locked slot, 32x32" },
    @{ Id = "ui_button_apply"; Name = "Apply Button"; Desc = "Apply enchantment button icon, apply enchantment, 32x32" },
    @{ Id = "ui_button_remove"; Name = "Remove Button"; Desc = "Remove enchantment button icon, remove enchantment, 32x32" },
    @{ Id = "ui_button_upgrade"; Name = "Upgrade Button"; Desc = "Upgrade enchantment button icon, upgrade enchantment, 32x32" },
    @{ Id = "ui_tooltip_enchantment"; Name = "Enchantment Tooltip"; Desc = "Enchantment tooltip background, enchantment information tooltip, 128x128" }
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
        $assetType = if ($element.Id -like "*panel*" -or $element.Id -like "*tooltip*" -or $element.Id -like "*slot*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Enchantment UI element for Starbound."
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
# 8. MANA INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mana Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$manaIndicators = @(
    @{ Id = "mana_full"; Name = "Mana Full"; Desc = "Mana full indicator icon, full mana, 32x32" },
    @{ Id = "mana_high"; Name = "Mana High"; Desc = "Mana high indicator icon, high mana, 32x32" },
    @{ Id = "mana_medium"; Name = "Mana Medium"; Desc = "Mana medium indicator icon, medium mana, 32x32" },
    @{ Id = "mana_low"; Name = "Mana Low"; Desc = "Mana low indicator icon, low mana, 32x32" },
    @{ Id = "mana_empty"; Name = "Mana Empty"; Desc = "Mana empty indicator icon, no mana, 32x32" },
    @{ Id = "mana_charging"; Name = "Mana Charging"; Desc = "Mana charging indicator icon, charging mana, 32x32" },
    @{ Id = "mana_bar"; Name = "Mana Bar"; Desc = "Mana bar background texture, mana meter, 128x16" }
)

# Validate $ModPath before Join-Path
$manaOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($manaOutputDir)) {
    Write-Host "  [FAIL] manaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($manaOutputDir)) {
    Write-Host "  [FAIL] manaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $manaOutputDir)) {
    New-Item -ItemType Directory -Path $manaOutputDir -Force | Out-Null
}

foreach ($indicator in $manaIndicators) {
    Write-Host "Generating mana indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*bar*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Mana indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $manaOutputDir
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
# 9. COOLDOWN INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cooldown Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$cooldownIndicators = @(
    @{ Id = "cooldown_ready"; Name = "Cooldown Ready"; Desc = "Cooldown ready indicator icon, ready to use, 32x32" },
    @{ Id = "cooldown_active"; Name = "Cooldown Active"; Desc = "Cooldown active indicator icon, on cooldown, 32x32" },
    @{ Id = "cooldown_almost_ready"; Name = "Almost Ready"; Desc = "Almost ready indicator icon, almost ready, 32x32" },
    @{ Id = "cooldown_bar"; Name = "Cooldown Bar"; Desc = "Cooldown bar background texture, cooldown meter, 128x16" }
)

# Validate $ModPath before Join-Path
$cooldownOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($cooldownOutputDir)) {
    Write-Host "  [FAIL] cooldownOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cooldownOutputDir)) {
    Write-Host "  [FAIL] cooldownOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $cooldownOutputDir)) {
    New-Item -ItemType Directory -Path $cooldownOutputDir -Force | Out-Null
}

foreach ($indicator in $cooldownIndicators) {
    Write-Host "Generating cooldown indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*bar*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Cooldown indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $cooldownOutputDir
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
# 10. SYNERGY/CONFLICT INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Synergy/Conflict Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$synergyIndicators = @(
    @{ Id = "synergy_active"; Name = "Synergy Active"; Desc = "Synergy active indicator icon, synergy active, 32x32" },
    @{ Id = "synergy_bonus"; Name = "Synergy Bonus"; Desc = "Synergy bonus indicator icon, synergy bonus, 32x32" },
    @{ Id = "conflict_active"; Name = "Conflict Active"; Desc = "Conflict active indicator icon, conflict active, 32x32" },
    @{ Id = "conflict_penalty"; Name = "Conflict Penalty"; Desc = "Conflict penalty indicator icon, conflict penalty, 32x32" },
    @{ Id = "compatible"; Name = "Compatible"; Desc = "Compatible indicator icon, enchantments compatible, 32x32" },
    @{ Id = "incompatible"; Name = "Incompatible"; Desc = "Incompatible indicator icon, enchantments incompatible, 32x32" }
)

# Validate $ModPath before Join-Path
$synergyOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($synergyOutputDir)) {
    Write-Host "  [FAIL] synergyOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($synergyOutputDir)) {
    Write-Host "  [FAIL] synergyOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $synergyOutputDir)) {
    New-Item -ItemType Directory -Path $synergyOutputDir -Force | Out-Null
}

foreach ($indicator in $synergyIndicators) {
    Write-Host "Generating synergy/conflict indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Synergy/conflict indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $synergyOutputDir
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
Write-Host "  Tiers: $(Join-Path $ModPath 'assets\enchantment\tiers')" -ForegroundColor Gray
Write-Host "  Rarities: $(Join-Path $ModPath 'assets\enchantment\rarities')" -ForegroundColor Gray
Write-Host "  Categories: $(Join-Path $ModPath 'assets\enchantment\categories')" -ForegroundColor Gray
Write-Host "  Triggers: $(Join-Path $ModPath 'assets\enchantment\triggers')" -ForegroundColor Gray
Write-Host "  Effects: $(Join-Path $ModPath 'assets\enchantment\effects')" -ForegroundColor Gray
Write-Host "  Runes: $(Join-Path $ModPath 'assets\enchantment\runes')" -ForegroundColor Gray
Write-Host "  UI: $(Join-Path $ModPath 'assets\enchantment\ui')" -ForegroundColor Gray
Write-Host "  Mana: $(Join-Path $ModPath 'assets\enchantment\mana')" -ForegroundColor Gray
Write-Host "  Cooldown: $(Join-Path $ModPath 'assets\enchantment\cooldown')" -ForegroundColor Gray
Write-Host "  Synergy: $(Join-Path $ModPath 'assets\enchantment\synergy')" -ForegroundColor Gray
Write-Host ""
