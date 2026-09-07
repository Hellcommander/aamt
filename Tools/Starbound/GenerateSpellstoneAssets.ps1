#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generates spellstone asset variants for procedural item use.
    
.DESCRIPTION
    Generates spellstone assets organized by spellform, delivery type, and spellshape modifiers.
    Supports procedural item generation by creating a structured asset library that accounts for:
    - Spellform types (fireBolt, iceShard, lightningBolt, etc.)
    - Delivery types (projectile, beam, area, self, etc.)
    - Spellshape modifiers (amplify, pierce, split, homing, etc.)
    - Strength levels (weak, moderate, strong, extreme)
    
.PARAMETER AssetType
    Type of assets to generate: spellform, spellshape, delivery, or "all"
    
.PARAMETER SpellformId
    Specific spellform ID (e.g., fireBolt, iceShard) or "all"
    
.PARAMETER DeliveryType
    Delivery type: projectile, beam, area, self, channel, or "all"
    
.PARAMETER SpellshapeId
    Specific spellshape ID (e.g., amplify, pierce) or "all"
    
.PARAMETER StrengthLevel
    Strength level: weak, moderate, strong, extreme, or "all"
    
.PARAMETER Variants
    Number of variants to generate per combination (default: 3)
    
.PARAMETER OutputDir
    Base output directory for generated assets (default: mod assets directory)
    
.EXAMPLE
    .\GenerateSpellstoneAssets.ps1 -AssetType spellform -SpellformId fireBolt -DeliveryType projectile -Variants 3
    Generates 3 variants of fireBolt projectile spellform
    
.EXAMPLE
    .\GenerateSpellstoneAssets.ps1 -AssetType spellshape -SpellshapeId amplify -StrengthLevel all -Variants 2
    Generates 2 variants of amplify spellshape for all strength levels
    
.EXAMPLE
    .\GenerateSpellstoneAssets.ps1 -AssetType all
    Generates complete spellstone asset set (all spellforms, spellshapes, delivery types)
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("spellform", "spellshape", "delivery", "all")]
    [string]$AssetType = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$SpellformId = "all",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("projectile", "beam", "area", "self", "channel", "all")]
    [string]$DeliveryType = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$SpellshapeId = "all",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("weak", "moderate", "strong", "extreme", "all")]
    [string]$StrengthLevel = "all",
    
    [Parameter(Mandatory=$false)]
    [int]$Variants = 0,  # 0 means use default from settings
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ""  # Empty means use default from settings
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import shared settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Use default output directory from settings if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = $script:SpellstoneOutputDir
}

# Use default variants from settings if not specified
if ($Variants -eq 0) {
    $Variants = $script:DefaultVariants
}

# Import asset generator
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"
if (-not (Test-Path $assetGenerator)) {
    Write-Host "Error: StarboundOllamaAssetGenerator.ps1 not found" -ForegroundColor Red
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Spellstone Asset Generator for Procedural Items" -ForegroundColor Cyan
Write-Host "  (Spellform + Delivery Type + Spellshape System)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Define spellforms by delivery type
$spellforms = @{
    projectile = @("fireBolt", "iceShard", "lightningBolt", "arcaneMissile", "voidOrb", "natureSeed")
    beam = @("fireBeam", "iceBeam", "lightningBeam", "arcaneRay", "voidBeam", "cosmicRay")
    area = @("fireNova", "iceBlast", "lightningStorm", "arcaneExplosion", "voidRift", "natureBloom")
    self = @("fireShield", "iceArmor", "lightningAura", "arcaneWard", "voidCloak", "natureRegen")
    channel = @("fireChannel", "iceChannel", "lightningChannel", "arcaneChannel", "voidChannel", "natureChannel")
}

# Define spellshapes
$allSpellshapes = @("amplify", "pierce", "split", "homing", "explode", "chain", "freeze", "efficiency", "overcharge", "ricochet")

# Define strength levels
$allStrengthLevels = @("weak", "moderate", "strong", "extreme")

# Define delivery types
$allDeliveryTypes = @("projectile", "beam", "area", "self", "channel")

# Spellform descriptions
$spellformDescriptions = @{
    fireBolt = "A fiery projectile spell that deals fire damage and applies burning"
    iceShard = "A sharp ice projectile that deals cold damage and may freeze enemies"
    lightningBolt = "A fast electric projectile that can chain between enemies"
    fireBeam = "A continuous beam of fire energy that deals sustained damage"
    iceBeam = "A freezing beam that slows and damages enemies"
    lightningBeam = "A crackling lightning beam with high damage"
    fireNova = "An explosive area-effect fire spell that damages all nearby enemies"
    iceBlast = "An area-effect ice spell that freezes enemies in a radius"
    lightningStorm = "An area-effect lightning spell that strikes multiple targets"
    fireShield = "A protective fire shield that damages attackers"
    iceArmor = "A defensive ice armor that slows attackers"
    lightningAura = "An electric aura that damages nearby enemies"
}

# Delivery type descriptions
$deliveryDescriptions = @{
    projectile = "A fast-moving projectile that travels in a straight line"
    beam = "A continuous beam that deals damage over time"
    area = "An area-effect spell that damages enemies in a radius"
    self = "A self-targeted spell that affects the caster"
    channel = "A channeled spell that requires continuous casting"
}

# Spellshape descriptions
$spellshapeDescriptions = @{
    amplify = "Increases spell power at the cost of higher mana consumption"
    pierce = "Allows the projectile to pass through multiple enemies"
    split = "Splits into multiple projectiles on impact or after distance"
    homing = "Seeks out nearby enemies automatically"
    explode = "Creates an area explosion on impact"
    chain = "Jumps between nearby enemies after hitting"
    freeze = "Enhanced freezing effects that can immobilize enemies"
    efficiency = "Reduces mana cost and cooldown at the expense of damage"
    overcharge = "Massively increases damage but also mana cost"
    ricochet = "Bounces between surfaces and enemies"
}

# Strength level modifiers
$strengthModifiers = @{
    weak = "subtle, minimal"
    moderate = "noticeable, balanced"
    strong = "powerful, significant"
    extreme = "overwhelming, maximum"
}

# Statistics
$generatedCount = 0
$failedCount = 0
$skippedCount = 0

# Generate spellform assets
if ($AssetType -eq "all" -or $AssetType -eq "spellform") {
    Write-Host "Generating Spellform Assets..." -ForegroundColor Yellow
    Write-Host ""
    
    $deliveryTypes = if ($DeliveryType -eq "all") { $allDeliveryTypes } else { @($DeliveryType) }
    
    foreach ($delivery in $deliveryTypes) {
        $spellformList = if ($SpellformId -eq "all") { $spellforms[$delivery] } else { @($SpellformId) }
        
        foreach ($spellform in $spellformList) {
            for ($variant = 1; $variant -le $Variants; $variant++) {
                $assetName = "${spellform}_${delivery}_$(($variant).ToString('00'))"
                
                # Build description
                $baseDesc = if ($spellformDescriptions.ContainsKey($spellform)) {
                    $spellformDescriptions[$spellform]
                } else {
                    "A $spellform spell with $delivery delivery type"
                }
                $deliveryDesc = $deliveryDescriptions[$delivery]
                $description = "$baseDesc. $deliveryDesc"
                
                # Determine output directory
                # Validate $OutputDir before Join-Path
                $elementOutputDir = Join-Path $OutputDir "spellforms\$delivery\$spellform"
 if ([string]::IsNullOrWhiteSpace($elementOutputDir)) {
                    Write-Host "  [FAIL] elementOutputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($elementOutputDir)) {
                    Write-Host "  [FAIL] elementOutputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
                    continue
                }
                
                # Check if asset already exists
                $spritePath = Join-Path $elementOutputDir "$assetName.png"
                if (Test-Path $spritePath) {
                    Write-Host "[SKIP] $assetName (already exists)" -ForegroundColor Yellow
                    $skippedCount++
                    continue
                }
                
                Write-Host "[GEN] $assetName" -ForegroundColor Cyan
                Write-Host "      Spellform: $spellform, Delivery: $delivery, Variant: $variant" -ForegroundColor Gray
                Write-Host "      Description: $description" -ForegroundColor Gray
                
                try {
                    & $assetGenerator `
                        -AssetType "ItemSprite" `
                        -AssetName $assetName `
                        -Description $description `
                        -OutputDir $elementOutputDir `
                        -GenerateMultiple 1
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "      ✓ Generated successfully" -ForegroundColor Green
                        $generatedCount++
                    } else {
                        Write-Host "      ✗ Generation failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
                        $failedCount++
                    }
                } catch {
                    Write-Host "      ✗ Error: $_" -ForegroundColor Red
                    $failedCount++
                }
                
                Write-Host ""
            }
        }
    }
}

# Generate spellshape assets
if ($AssetType -eq "all" -or $AssetType -eq "spellshape") {
    Write-Host "Generating Spellshape Assets..." -ForegroundColor Yellow
    Write-Host ""
    
    $spellshapeList = if ($SpellshapeId -eq "all") { $allSpellshapes } else { @($SpellshapeId) }
    $strengthLevels = if ($StrengthLevel -eq "all") { $allStrengthLevels } else { @($StrengthLevel) }
    
    foreach ($spellshape in $spellshapeList) {
        foreach ($strength in $strengthLevels) {
            for ($variant = 1; $variant -le $Variants; $variant++) {
                $assetName = "${spellshape}_${strength}_$(($variant).ToString('00'))"
                
                # Build description
                $baseDesc = if ($spellshapeDescriptions.ContainsKey($spellshape)) {
                    $spellshapeDescriptions[$spellshape]
                } else {
                    "A $spellshape spellshape modifier"
                }
                $strengthMod = $strengthModifiers[$strength]
                $description = "$strengthMod $baseDesc"
                
                # Determine output directory
                # Validate $OutputDir before Join-Path
                $elementOutputDir = Join-Path $OutputDir "spellshapes\$spellshape\$strength"
 if ([string]::IsNullOrWhiteSpace($elementOutputDir)) {
                    Write-Host "  [FAIL] elementOutputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($elementOutputDir)) {
                    Write-Host "  [FAIL] elementOutputDir is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
                    continue
                }
                
                # Check if asset already exists
                $spritePath = Join-Path $elementOutputDir "$assetName.png"
                if (Test-Path $spritePath) {
                    Write-Host "[SKIP] $assetName (already exists)" -ForegroundColor Yellow
                    $skippedCount++
                    continue
                }
                
                Write-Host "[GEN] $assetName" -ForegroundColor Cyan
                Write-Host "      Spellshape: $spellshape, Strength: $strength, Variant: $variant" -ForegroundColor Gray
                Write-Host "      Description: $description" -ForegroundColor Gray
                
                try {
                    & $assetGenerator `
                        -AssetType "ItemSprite" `
                        -AssetName $assetName `
                        -Description $description `
                        -OutputDir $elementOutputDir `
                        -GenerateMultiple 1
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "      ✓ Generated successfully" -ForegroundColor Green
                        $generatedCount++
                    } else {
                        Write-Host "      ✗ Generation failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
                        $failedCount++
                    }
                } catch {
                    Write-Host "      ✗ Error: $_" -ForegroundColor Red
                    $failedCount++
                }
                
                Write-Host ""
            }
        }
    }
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Statistics:" -ForegroundColor Yellow
Write-Host "  Generated: $generatedCount" -ForegroundColor Green
Write-Host "  Skipped (existing): $skippedCount" -ForegroundColor Yellow
Write-Host "  Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""

if ($failedCount -eq 0) {
    Write-Host "✓ All assets generated successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠ Some assets failed to generate. Check errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Assets are organized in:" -ForegroundColor Cyan
Write-Host "  $OutputDir" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review generated assets for quality" -ForegroundColor Gray
Write-Host "  2. Register assets in SpellstoneAssetRegistry" -ForegroundColor Gray
Write-Host "  3. Use SpellstoneAssetSelector for procedural item generation" -ForegroundColor Gray
Write-Host ""
