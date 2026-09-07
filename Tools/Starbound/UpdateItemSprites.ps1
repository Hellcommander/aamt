#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Update item JSON files to reference newly generated sprites.
    
.DESCRIPTION
    Updates spellstone_items.json and other item files to use the generated sprites
    instead of placeholder assets.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
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

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Updating Item Sprite References" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if sprites directory exists
# Validate $ModPath before Join-Path
$spritesDir = Join-Path $ModPath "assets\items\sprites"
 if ([string]::IsNullOrWhiteSpace($spritesDir)) {
    Write-Host "  [FAIL] spritesDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($spritesDir)) {
    Write-Host "  [FAIL] spritesDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $spritesDir)) {
    Write-Host "Error: Sprites directory not found: $spritesDir" -ForegroundColor Red
    Write-Host "Run GenerateModSprites.ps1 first to generate sprites." -ForegroundColor Yellow
    exit 1
}

# Get all generated sprites
$generatedSprites = Get-ChildItem -Path $spritesDir -Filter "*.png" | ForEach-Object {
    $_.BaseName
}

Write-Host "Found $($generatedSprites.Count) generated sprites" -ForegroundColor Green
Write-Host ""

# Update spell ingredients JSON files
$ingredientFiles = @(
    "spellIngredients\basic_elements.json",
    "spellIngredients\crystals.json",
    "spellIngredients\catalysts.json",
    "spellIngredients\rare_components.json",
    "spellIngredients\exotic_materials.json"
)

$ingredientUpdated = 0
foreach ($ingredientFile in $ingredientFiles) {
    $filePath = Join-Path $ModPath $ingredientFile
    if (Test-Path $filePath) {
        $content = Get-Content $filePath -Raw
        $data = $content | ConvertFrom-Json
        
        if ($data.ingredients) {
            foreach ($ingredient in $data.ingredients) {
                if ($generatedSprites -contains $ingredient.id) {
                    $ingredient.icon = "/items/sprites/$($ingredient.id).png"
                    $ingredientUpdated++
                }
            }
            
            $jsonContent = $data | ConvertTo-Json -Depth 20
            $jsonContent | Set-Content -Path $filePath -Encoding UTF8
        }
    }
}

if ($ingredientUpdated -gt 0) {
    Write-Host "Updated $ingredientUpdated ingredient icon references" -ForegroundColor Green
    Write-Host ""
}

# Update spellstone_items.json
# Validate $ModPath before Join-Path
$spellstoneFile = Join-Path $ModPath "items\spellstones\spellstone_items.json"
 if ([string]::IsNullOrWhiteSpace($spellstoneFile)) {
    Write-Host "  [FAIL] spellstoneFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($spellstoneFile)) {
    Write-Host "  [FAIL] spellstoneFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $spellstoneFile) {
    Write-Host "Updating spellstone_items.json..." -ForegroundColor Cyan
    
    $content = Get-Content $spellstoneFile -Raw
    $data = $content | ConvertFrom-Json
    
    $updated = 0
    
    # Update base cores
    if ($data.spellstone_items.base_cores) {
        $data.spellstone_items.base_cores.PSObject.Properties | ForEach-Object {
            $id = $_.Name
            if ($generatedSprites -contains $id) {
                $_.Value.asset.primary = "/items/sprites/$id.png"
                $_.Value.asset.source = "magi_tech_custom"
                $_.Value.asset.license = "MIT"
                $_.Value.asset.attribution = "Generated sprite for MagiTech mod"
                $_.Value.asset.usage = "Custom"
                $updated++
                Write-Host "  Updated: $id" -ForegroundColor Green
            }
        }
    }
    
    # Update elemental variants
    if ($data.spellstone_items.elemental_variants) {
        $data.spellstone_items.elemental_variants.PSObject.Properties | ForEach-Object {
            $id = $_.Name
            if ($generatedSprites -contains $id) {
                $_.Value.asset.primary = "/items/sprites/$id.png"
                $_.Value.asset.source = "magi_tech_custom"
                $_.Value.asset.license = "MIT"
                $_.Value.asset.attribution = "Generated sprite for MagiTech mod"
                $_.Value.asset.usage = "Custom"
                $updated++
                Write-Host "  Updated: $id" -ForegroundColor Green
            }
        }
    }
    
    # Save updated file
    $jsonContent = $data | ConvertTo-Json -Depth 20
    $jsonContent | Set-Content -Path $spellstoneFile -Encoding UTF8
    
    Write-Host "Updated $updated spellstone references" -ForegroundColor Green
    Write-Host ""
}

# Update alchemical grenade launcher
# Validate $ModPath before Join-Path
$grenadeLauncherFile = Join-Path $ModPath "items\weapons\alchemicalgrenadelauncher\alchemical_grenade_launcher.json"
 if ([string]::IsNullOrWhiteSpace($grenadeLauncherFile)) {
    Write-Host "  [FAIL] grenadeLauncherFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($grenadeLauncherFile)) {
    Write-Host "  [FAIL] grenadeLauncherFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $grenadeLauncherFile) {
    Write-Host "Updating alchemical_grenade_launcher.json..." -ForegroundColor Cyan
    
    $content = Get-Content $grenadeLauncherFile -Raw
    $data = $content | ConvertFrom-Json
    
    if ($generatedSprites -contains "alchemical_grenade_launcher") {
        if ($data.alchemical_grenade_launcher.weapon_data.asset) {
            $data.alchemical_grenade_launcher.weapon_data.asset.primary = "/items/sprites/alchemical_grenade_launcher.png"
            $data.alchemical_grenade_launcher.weapon_data.asset.source = "magi_tech_custom"
            $data.alchemical_grenade_launcher.weapon_data.asset.license = "MIT"
            $data.alchemical_grenade_launcher.weapon_data.asset.attribution = "Generated sprite for MagiTech mod"
            $data.alchemical_grenade_launcher.weapon_data.asset.usage = "Custom"
            
            $jsonContent = $data | ConvertTo-Json -Depth 20
            $jsonContent | Set-Content -Path $grenadeLauncherFile -Encoding UTF8
            
            Write-Host "  Updated: alchemical_grenade_launcher" -ForegroundColor Green
        }
    }
    Write-Host ""
}

# Update reagent items
# Validate $ModPath before Join-Path
$reagentDir = Join-Path $ModPath "items\consumable\reagents"
 if ([string]::IsNullOrWhiteSpace($reagentDir)) {
    Write-Host "  [FAIL] reagentDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($reagentDir)) {
    Write-Host "  [FAIL] reagentDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $reagentDir) {
    Write-Host "Updating reagent items..." -ForegroundColor Cyan
    
    $reagentFiles = Get-ChildItem -Path $reagentDir -Filter "*.item"
    $reagentUpdated = 0
    
    foreach ($file in $reagentFiles) {
        try {
            $content = Get-Content $file.FullName -Raw
            $data = $content | ConvertFrom-Json
            $itemId = $data.itemName
            
            if ($generatedSprites -contains $itemId) {
                if (-not $data.inventoryIcon) {
                    $data | Add-Member -NotePropertyName "inventoryIcon" -NotePropertyValue "$itemId.png" -Force
                } else {
                    $data.inventoryIcon = "$itemId.png"
                }
                
                $jsonContent = $data | ConvertTo-Json -Depth 20
                $jsonContent | Set-Content -Path $file.FullName -Encoding UTF8
                $reagentUpdated++
                Write-Host "  Updated: $itemId" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Error updating $($file.Name): $_" -ForegroundColor Red
        }
    }
    
    if ($reagentUpdated -gt 0) {
        Write-Host "Updated $reagentUpdated reagent item references" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Update Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "All item JSON files have been updated to reference generated sprites." -ForegroundColor Green
Write-Host ""
