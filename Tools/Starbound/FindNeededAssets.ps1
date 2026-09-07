#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Find all assets needed by the mod that are missing or need generation.
    
.DESCRIPTION
    Scans the mod directory for asset references and identifies:
    - Missing sprites/images
    - Items needing sprites
    - Animations needing spritesheets
    - Buff icons
    - Projectile sprites
    - Object sprites
    - Interface icons
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "needed_assets_report.json"
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
Write-Host "  Asset Requirements Scanner" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$neededAssets = @{
    Items = @()
    SpellIngredients = @()
    Reagents = @()
    Weapons = @()
    Projectiles = @()
    Objects = @()
    Animations = @()
    Buffs = @()
    Interface = @()
    Particles = @()
}

# Function to check if asset exists
function Test-AssetExists {
    param([string]$AssetPath, [string]$ModPath)
    
    # Convert Starbound path to filesystem path
    $fsPath = $AssetPath -replace '^/', ''
    $fullPath = Join-Path $ModPath $fsPath
    
    return Test-Path $fullPath
}

# Function to extract asset path from JSON
function Get-AssetPaths {
    param([object]$Data, [string]$Type)
    
    $paths = @()
    
    if ($Data.asset -and $Data.asset.primary) {
        $paths += @{
            Path = $Data.asset.primary
            Type = $Type
            Source = "asset.primary"
        }
    }
    
    if ($Data.inventoryIcon) {
        $iconPath = if ($Data.inventoryIcon -notmatch '^/') {
            "/items/sprites/$($Data.inventoryIcon)"
        } else {
            $Data.inventoryIcon
        }
        $paths += @{
            Path = $iconPath
            Type = $Type
            Source = "inventoryIcon"
        }
    }
    
    if ($Data.icon) {
        $iconPath = if ($Data.icon -notmatch '^/') {
            "/items/sprites/$($Data.icon)"
        } else {
            $Data.icon
        }
        $paths += @{
            Path = $iconPath
            Type = $Type
            Source = "icon"
        }
    }
    
    if ($Data.animationParts) {
        $Data.animationParts.PSObject.Properties | ForEach-Object {
            $partPath = $_.Value
            if ($partPath -match '\.png$') {
                $paths += @{
                    Path = $partPath
                    Type = "AnimationPart"
                    Source = "animationParts.$($_.Name)"
                }
            }
        }
    }
    
    return $paths
}

# ============================================================
# 1. SCAN ITEM FILES
# ============================================================
Write-Host "Scanning item files..." -ForegroundColor Yellow

$itemFiles = Get-ChildItem -Path (Join-Path $ModPath "items") -Filter "*.item" -Recurse

foreach ($file in $itemFiles) {
    try {
        $data = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $itemId = $data.itemName
        
        $assetPaths = Get-AssetPaths -Data $data -Type "Item"
        
        foreach ($asset in $assetPaths) {
            if (-not (Test-AssetExists -AssetPath $asset.Path -ModPath $ModPath)) {
                $neededAssets.Items += @{
                    ItemId = $itemId
                    File = $file.FullName.Replace($ModPath, "")
                    AssetPath = $asset.Path
                    Source = $asset.Source
                    Status = "Missing"
                }
            }
        }
    } catch {
        Write-Host "  Error parsing $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host "  Found $($neededAssets.Items.Count) missing item assets" -ForegroundColor $(if ($neededAssets.Items.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# 2. SCAN SPELLSTONES
# ============================================================
Write-Host "Scanning spellstones..." -ForegroundColor Yellow

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
    $data = Get-Content $spellstoneFile -Raw | ConvertFrom-Json
    
    # Base cores
    if ($data.spellstone_items.base_cores) {
        $data.spellstone_items.base_cores.PSObject.Properties | ForEach-Object {
            $item = $_.Value
            if ($item.asset -and $item.asset.primary) {
                if (-not (Test-AssetExists -AssetPath $item.asset.primary -ModPath $ModPath)) {
                    $neededAssets.SpellIngredients += @{
                        Id = $_.Name
                        Name = $item.itemName
                        AssetPath = $item.asset.primary
                        Status = "Missing"
                    }
                }
            }
        }
    }
    
    # Elemental variants
    if ($data.spellstone_items.elemental_variants) {
        $data.spellstone_items.elemental_variants.PSObject.Properties | ForEach-Object {
            $item = $_.Value
            if ($item.asset -and $item.asset.primary) {
                if (-not (Test-AssetExists -AssetPath $item.asset.primary -ModPath $ModPath)) {
                    $neededAssets.SpellIngredients += @{
                        Id = $_.Name
                        Name = $item.itemName
                        AssetPath = $item.asset.primary
                        Status = "Missing"
                    }
                }
            }
        }
    }
}

Write-Host "  Found $($neededAssets.SpellIngredients.Count) missing spellstone assets" -ForegroundColor $(if ($neededAssets.SpellIngredients.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# 3. SCAN SPELL INGREDIENTS
# ============================================================
Write-Host "Scanning spell ingredients..." -ForegroundColor Yellow

$ingredientFiles = @(
    "spellIngredients\basic_elements.json",
    "spellIngredients\crystals.json",
    "spellIngredients\catalysts.json",
    "spellIngredients\rare_components.json",
    "spellIngredients\exotic_materials.json"
)

foreach ($ingredientFile in $ingredientFiles) {
    $filePath = Join-Path $ModPath $ingredientFile
    if (Test-Path $filePath) {
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
        
        if ($data.ingredients) {
            foreach ($ingredient in $data.ingredients) {
                if ($ingredient.icon) {
                    $iconPath = if ($ingredient.icon -notmatch '^/') {
                        "/items/materials/$($ingredient.icon)"
                    } else {
                        $ingredient.icon
                    }
                    
                    if (-not (Test-AssetExists -AssetPath $iconPath -ModPath $ModPath)) {
                        $neededAssets.SpellIngredients += @{
                            Id = $ingredient.id
                            Name = $ingredient.name
                            AssetPath = $iconPath
                            Status = "Missing"
                        }
                    }
                }
            }
        }
    }
}

Write-Host "  Found $($neededAssets.SpellIngredients.Count) missing ingredient assets" -ForegroundColor $(if ($neededAssets.SpellIngredients.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# 4. SCAN BUFFS
# ============================================================
Write-Host "Scanning buff definitions..." -ForegroundColor Yellow

# Validate $ModPath before Join-Path
$buffsFile = Join-Path $ModPath "Data\buffs\buff_definitions.json"
 if ([string]::IsNullOrWhiteSpace($buffsFile)) {
    Write-Host "  [FAIL] buffsFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($buffsFile)) {
    Write-Host "  [FAIL] buffsFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $buffsFile) {
    $data = Get-Content $buffsFile -Raw | ConvertFrom-Json
    
    if ($data.buffs) {
        $data.buffs | ForEach-Object {
            if ($_.icon) {
                $iconPath = if ($_.icon -notmatch '^/') {
                    "/buffs/icons/$($_.icon)"
                } else {
                    $_.icon
                }
                
                if (-not (Test-AssetExists -AssetPath $iconPath -ModPath $ModPath)) {
                    $neededAssets.Buffs += @{
                        Id = $_.id
                        Name = $_.name
                        AssetPath = $iconPath
                        Status = "Missing"
                    }
                }
            }
        }
    }
}

Write-Host "  Found $($neededAssets.Buffs.Count) missing buff icons" -ForegroundColor $(if ($neededAssets.Buffs.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# 5. SCAN ANIMATIONS
# ============================================================
Write-Host "Scanning animations..." -ForegroundColor Yellow

$animationFiles = Get-ChildItem -Path (Join-Path $ModPath "animations") -Filter "*.animation" -Recurse

foreach ($file in $animationFiles) {
    try {
        $content = Get-Content $file.FullName -Raw
        $data = $content | ConvertFrom-Json
        
        # Check for image references in animatedParts
        if ($data.animatedParts -and $data.animatedParts.parts) {
            $data.animatedParts.parts.PSObject.Properties | ForEach-Object {
                $part = $_.Value
                if ($part.properties -and $part.properties.image) {
                    $imagePath = $part.properties.image
                    if (-not (Test-AssetExists -AssetPath $imagePath -ModPath $ModPath)) {
                        $neededAssets.Animations += @{
                            AnimationFile = $file.FullName.Replace($ModPath, "")
                            Part = $_.Name
                            AssetPath = $imagePath
                            Status = "Missing"
                        }
                    }
                }
            }
        }
        
        # Check for frames reference
        if ($data.frames) {
            $framesPath = if ($data.frames -notmatch '^/') {
                Join-Path (Split-Path $file.DirectoryName) $data.frames
            } else {
                Join-Path $ModPath ($data.frames -replace '^/', '')
            }
            
            if (-not (Test-Path $framesPath)) {
                $neededAssets.Animations += @{
                    AnimationFile = $file.FullName.Replace($ModPath, "")
                    AssetPath = $data.frames
                    Status = "Missing"
                }
            }
        }
    } catch {
        Write-Host "  Error parsing $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host "  Found $($neededAssets.Animations.Count) missing animation assets" -ForegroundColor $(if ($neededAssets.Animations.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# 6. SCAN PROJECTILES
# ============================================================
Write-Host "Scanning projectiles..." -ForegroundColor Yellow

$projectileFiles = Get-ChildItem -Path (Join-Path $ModPath "projectiles") -Filter "*.projectile" -Recurse

foreach ($file in $projectileFiles) {
    try {
        $data = Get-Content $file.FullName -Raw | ConvertFrom-Json
        
        # Check for image references
        if ($data.image) {
            if (-not (Test-AssetExists -AssetPath $data.image -ModPath $ModPath)) {
                $neededAssets.Projectiles += @{
                    File = $file.FullName.Replace($ModPath, "")
                    AssetPath = $data.image
                    Status = "Missing"
                }
            }
        }
    } catch {
        Write-Host "  Error parsing $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host "  Found $($neededAssets.Projectiles.Count) missing projectile assets" -ForegroundColor $(if ($neededAssets.Projectiles.Count -eq 0) { "Green" } else { "Yellow" })

# ============================================================
# SUMMARY
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Asset Requirements Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$total = $neededAssets.Items.Count + 
         $neededAssets.SpellIngredients.Count + 
         $neededAssets.Reagents.Count + 
         $neededAssets.Weapons.Count + 
         $neededAssets.Projectiles.Count + 
         $neededAssets.Objects.Count + 
         $neededAssets.Animations.Count + 
         $neededAssets.Buffs.Count + 
         $neededAssets.Interface.Count + 
         $neededAssets.Particles.Count

Write-Host "Total Missing Assets: $total" -ForegroundColor $(if ($total -eq 0) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "Breakdown:" -ForegroundColor Cyan
Write-Host "  Items: $($neededAssets.Items.Count)" -ForegroundColor Gray
Write-Host "  Spell Ingredients: $($neededAssets.SpellIngredients.Count)" -ForegroundColor Gray
Write-Host "  Reagents: $($neededAssets.Reagents.Count)" -ForegroundColor Gray
Write-Host "  Weapons: $($neededAssets.Weapons.Count)" -ForegroundColor Gray
Write-Host "  Projectiles: $($neededAssets.Projectiles.Count)" -ForegroundColor Gray
Write-Host "  Objects: $($neededAssets.Objects.Count)" -ForegroundColor Gray
Write-Host "  Animations: $($neededAssets.Animations.Count)" -ForegroundColor Gray
Write-Host "  Buffs: $($neededAssets.Buffs.Count)" -ForegroundColor Gray
Write-Host "  Interface: $($neededAssets.Interface.Count)" -ForegroundColor Gray
Write-Host "  Particles: $($neededAssets.Particles.Count)" -ForegroundColor Gray
Write-Host ""

# Save report
$reportPath = Join-Path $PSScriptRoot $OutputFile
$neededAssets | ConvertTo-Json -Depth 10 | Set-Content -Path $reportPath -Encoding UTF8

Write-Host "Report saved to: $reportPath" -ForegroundColor Green
Write-Host ""

# Generate generation script
if ($total -gt 0) {
    Write-Host "Generating asset generation script..." -ForegroundColor Cyan
    
    $genScript = @"
# Auto-generated asset generation script
# Generated from asset requirements scan

`$itemsToGenerate = @(
"@
    
    # Add items
    foreach ($item in $neededAssets.Items) {
        $itemId = ($item.AssetPath -split '/')[-1] -replace '\.png$', ''
        $genScript += "`n    @{ Id = '$itemId'; Type = 'ItemSprite'; Prompt = 'Item sprite for $($item.ItemId)' },"
    }
    
    # Add spell ingredients
    foreach ($ingredient in $neededAssets.SpellIngredients) {
        $genScript += "`n    @{ Id = '$($ingredient.Id)'; Type = 'ItemSprite'; Prompt = '$($ingredient.Name) - $($ingredient.AssetPath)' },"
    }
    
    # Add buffs
    foreach ($buff in $neededAssets.Buffs) {
        $itemId = ($buff.AssetPath -split '/')[-1] -replace '\.png$', ''
        $genScript += "`n    @{ Id = '$itemId'; Type = 'Icon'; Prompt = 'Buff icon for $($buff.Name)' },"
    }
    
    $genScript += @"

)

# Generate all assets
foreach (`$item in `$itemsToGenerate) {
    .\StarboundOllamaAssetGenerator.ps1 `
        -AssetType `$item.Type `
        -AssetName `$item.Id `
        -Prompt `$item.Prompt `
        -OllamaModel "codellama:7b-instruct"
}
"@
    
    $genScriptPath = Join-Path $PSScriptRoot "GenerateMissingAssets.ps1"
    $genScript | Set-Content -Path $genScriptPath -Encoding UTF8
    
    Write-Host "Generation script created: $genScriptPath" -ForegroundColor Green
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Scan Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
