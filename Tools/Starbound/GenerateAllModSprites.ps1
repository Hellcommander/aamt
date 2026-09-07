#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate sprites for ALL mod content: spell ingredients, items, projectiles, objects, and monsters.
    
.DESCRIPTION
    Automatically generates sprites for:
    - All spellstone cores and elemental variants
    - All spell ingredients (basic elements, crystals, catalysts, rare components, exotic materials)
    - All reagent items
    - All unique weapons and items
    - All projectiles
    - All objects
    - All monsters/minions
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for sprite generation
    
.PARAMETER SkipExisting
    Skip sprites that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "",  # Auto-selected by OllamaIntegration.psm1
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",  # Auto-selected by OllamaIntegration.psm1
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "",  # Auto-selected by OllamaIntegration.psm1
    
    [Parameter(Mandatory=$false)]
    [switch]$UseCppBackend,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("fast", "mechanical", "full")]
    [string]$QualityAssessmentDepth = "fast"  # Quality assessment depth: "fast" (sanity only), "mechanical" (Qwen3-VL-8B), "full" (both models)
)

$ErrorActionPreference = "Continue"  # Changed from "Stop" to continue on errors and report them

# Validate ModPath is not null or empty FIRST
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "[ERROR] ModPath cannot be null or empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Yellow
    exit 1
}

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

# Verify asset generator exists
if (-not (Test-Path $assetGenerator)) {
    Write-Host "[ERROR] Asset generator script not found: $assetGenerator" -ForegroundColor Red
    Write-Host "Please ensure StarboundOllamaAssetGenerator.ps1 exists in the script directory." -ForegroundColor Yellow
    exit 1
}

# Ensure output directories exist
# Validate $ModPath before Join-Path (already validated above, but double-check)
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "[ERROR] ModPath is null or empty after validation" -ForegroundColor Red
    exit 1
}
$outputBase = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($outputBase)) {
    Write-Host "  [FAIL] outputBase is null (`${ModPath}: '`${ModPath}')" -ForegroundColor Red
    exit 1
}
$directories = @(
    (Join-Path $outputBase "items\sprites"),
    (Join-Path $outputBase "projectiles"),
    (Join-Path $outputBase "objects"),
    (Join-Path $outputBase "monsters")
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        Write-Host "Creating directory: $dir" -ForegroundColor Gray
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Complete Mod Sprite Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$allItems = @()
$generated = 0
$failed = 0
$skipped = 0
$script:failedAssets = @()  # Track failed asset names and reasons

# Helper function to safely join paths with ModPath validation
function Join-ModPath {
    param(
        [string]$ChildPath,
        [string]$Context = "operation"
    )
    
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        Write-Host "  [FAIL] ModPath is null or empty in $Context" -ForegroundColor Red
        return $null
    }
    
    if ([string]::IsNullOrWhiteSpace($ChildPath)) {
        Write-Host "  [FAIL] ChildPath is null or empty in $Context" -ForegroundColor Red
        return $null
    }
    
    $result = Join-Path $ModPath $ChildPath
    if ([string]::IsNullOrWhiteSpace($result)) {
        Write-Host "  [FAIL] Join-Path result is null in $Context (ModPath: '$ModPath', ChildPath: '$ChildPath')" -ForegroundColor Red
        return $null
    }
    
    return $result
}

# Check if sprite already exists
function Test-SpriteExists {
    param([string]$ItemId, [string]$OutputDir)
    # Validate $OutputDir before Join-Path
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        Write-Host "  [FAIL] OutputDir is null in Test-SpriteExists" -ForegroundColor Red
        return $false
    }
    $spritePath = Join-Path $OutputDir "items\sprites\$ItemId.png"
    if ([string]::IsNullOrWhiteSpace($spritePath)) {
        Write-Host "  [FAIL] spritePath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        return $false
    }
    return (Test-Path $spritePath)
}

# Helper function to safely get JSON property value
function Get-JsonProperty {
    param(
        [object]$Object,
        [string]$PropertyName,
        [string]$DefaultValue = ""
    )
    
    if (-not $Object) { return $DefaultValue }
    if ($Object.PSObject.Properties.Name -contains $PropertyName) {
        $value = $Object.$PropertyName
        if ($null -eq $value) { return $DefaultValue }
        return $value
    }
    return $DefaultValue
}

# Function to generate sprite
function Generate-Sprite {
    param(
        [string]$ItemId,
        [string]$Name,
        [string]$Description,
        [string]$Category,
        [string]$Rarity,
        [string]$Element = "",
        [string]$OutputDir
    )
    
    # Validate ItemId is not empty - do this FIRST before any other processing
    if ([string]::IsNullOrWhiteSpace($ItemId)) {
        $script:failed++
        $displayName = if ([string]::IsNullOrWhiteSpace($Name)) { "(unnamed)" } else { $Name }
        $script:failedAssets += [PSCustomObject]@{ AssetName = $displayName; Reason = "Empty ItemId"; Category = "Validation" }
        Write-Host "  [FAIL] Skipping item with empty ID: $displayName" -ForegroundColor Red
        return $false
    }
    
    # Validate OutputDir is not null or empty - do this BEFORE using it
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        $script:failed++
        $displayName = if ([string]::IsNullOrWhiteSpace($Name)) { $ItemId } else { $Name }
        $script:failedAssets += [PSCustomObject]@{ AssetName = $displayName; Reason = "OutputDir is null or empty"; Category = "Validation" }
        Write-Host "  [FAIL] $displayName : OutputDir is null or empty" -ForegroundColor Red
        return $false
    }
    
    # Validate Name is not empty (use ItemId as fallback)
    if ([string]::IsNullOrWhiteSpace($Name)) {
        $Name = $ItemId
    }
    
    if ($SkipExisting -and (Test-SpriteExists -ItemId $ItemId -OutputDir $OutputDir)) {
        $script:skipped++
        Write-Host "  [SKIP] Sprite already exists: $ItemId" -ForegroundColor Gray
        return $true
    }
    
    # Create enhanced prompt
    $prompt = $Description
    if ($Element) {
        $prompt = "$Element elemental $prompt"
    }
    
    # Add rarity-based visual cues
    switch ($Rarity) {
        "common" { $prompt = "$prompt, simple appearance, basic magical glow" }
        "uncommon" { $prompt = "$prompt, refined appearance, enhanced glow" }
        "rare" { $prompt = "$prompt, faceted crystal with animated runes, powerful energy" }
        "epic" { $prompt = "$prompt, pulsating crystal with swirling energy, epic appearance" }
        "legendary" { $prompt = "$prompt, radiant crystal with rotating inner shards, legendary power" }
    }
    
    # Add category-specific cues
    switch ($Category) {
        "crystal" { $prompt = "$prompt, crystalline structure, gem-like appearance" }
        "organic" { $prompt = "$prompt, organic material, living essence" }
        "elemental" { $prompt = "$prompt, pure elemental energy, glowing core" }
        "catalyst" { $prompt = "$prompt, manufactured catalyst, synthetic compound" }
        "exotic" { $prompt = "$prompt, exotic otherworldly material, unique appearance" }
    }
    
    try {
        # Validate ItemId is not empty before calling asset generator
        if ([string]::IsNullOrWhiteSpace($ItemId)) {
            $script:failed++
            Write-Host "  [FAIL] Skipping item with empty ID: $Name" -ForegroundColor Red
            return $false
        }
        
        # Double-check OutputDir is still valid before building params
        if ([string]::IsNullOrWhiteSpace($OutputDir)) {
            $script:failed++
            Write-Host "  [FAIL] $Name : OutputDir became null or empty before calling asset generator" -ForegroundColor Red
            return $false
        }
        
        # Validate assetGenerator path is not null
        if ([string]::IsNullOrWhiteSpace($assetGenerator)) {
            $script:failed++
            Write-Host "  [FAIL] $Name : assetGenerator path is null or empty" -ForegroundColor Red
            return $false
        }
        
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $ItemId
            Prompt = $prompt
            OllamaModel = $OllamaModel
            VisualModel = $VisualModel
            OutputDir = $OutputDir
            QualityAssessmentDepth = $QualityAssessmentDepth
        }
        # Only add PlanningModel if it's specified (otherwise defaults to OllamaModel)
        if ($PlanningModel -and $PlanningModel.Trim() -ne "") {
            $params['PlanningModel'] = $PlanningModel
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        # Validate AssetName is not empty before calling
        if ([string]::IsNullOrWhiteSpace($params.AssetName)) {
            $script:failed++
            Write-Host "  [FAIL] AssetName is empty for item: $Name (ItemId: '$ItemId')" -ForegroundColor Red
            return $false
        }
        
        # Validate OutputDir in params is not null
        if ([string]::IsNullOrWhiteSpace($params.OutputDir)) {
            $script:failed++
            Write-Host "  [FAIL] $Name : OutputDir in params is null or empty (original OutputDir: '$OutputDir')" -ForegroundColor Red
            return $false
        }
        
        # Call asset generator with error handling
        try {
            $output = & $assetGenerator @params 2>&1
            if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
                # Show the output so user can see what went wrong
                Write-Host "  [ERROR OUTPUT] $($output -join "`n")" -ForegroundColor Yellow
                $script:failed++
                $errorMsg = "Asset generator exited with code $LASTEXITCODE"
                # Track file path for potential cleanup
                $outputPath = if ($params.OutputDir -and $params.AssetName) {
                    Join-Path $params.OutputDir "$($params.AssetName).png"
                } else { $null }
                $script:failedAssets += [PSCustomObject]@{ 
                    AssetName = $Name; 
                    Reason = $errorMsg; 
                    Category = "Generator Error"
                    FilePath = $outputPath
                }
                Write-Host "  [FAIL] $Name : $errorMsg" -ForegroundColor Red
                return $false
            }
        } catch {
            $script:failed++
            $errorMsg = "Error calling asset generator: $_"
            # Track file path for potential cleanup
            $outputPath = if ($params.OutputDir -and $params.AssetName) {
                Join-Path $params.OutputDir "$($params.AssetName).png"
            } else { $null }
            $script:failedAssets += [PSCustomObject]@{ 
                AssetName = $Name; 
                Reason = $errorMsg; 
                Category = "Exception"
                FilePath = $outputPath
            }
            Write-Host "  [FAIL] $Name : $errorMsg" -ForegroundColor Red
            Write-Host "    OutputDir: '$($params.OutputDir)'" -ForegroundColor Gray
            Write-Host "    AssetName: '$($params.AssetName)'" -ForegroundColor Gray
            Write-Host "    AssetGenerator: '$assetGenerator'" -ForegroundColor Gray
            return $false
        }
        
        $script:generated++
        Write-Host "  [OK] Generated: $Name" -ForegroundColor Green
        return $true
    } catch {
        $script:failed++
        $errorDetails = $_.Exception.Message
        $errorMsg = "$errorDetails (Line: $($_.InvocationInfo.ScriptLineNumber))"
        $script:failedAssets += [PSCustomObject]@{ AssetName = $Name; Reason = $errorMsg; Category = "Exception" }
        $errorLine = $_.InvocationInfo.ScriptLineNumber
        $errorCmd = $_.InvocationInfo.Line
        Write-Host "  [FAIL] $Name : $_" -ForegroundColor Red
        Write-Host "    Error Details: $errorDetails" -ForegroundColor Gray
        Write-Host "    Line: $errorLine" -ForegroundColor Gray
        Write-Host "    Command: $errorCmd" -ForegroundColor Gray
        Write-Host "    OutputDir: '$OutputDir'" -ForegroundColor Gray
        return $false
    }
}

# ============================================================
# 1. SPELLSTONES (Procedural Assets - Default Generation)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spellstone Sprites (Procedural)" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Spellstones are procedural assets - generate default set
$spellstoneDefaults = @(
    # Base cores by rarity
    @{
        ItemId = "spellstone_core_common"
        Name = "Arcane Core (Common)"
        Description = "A simple translucent crystal core, pulsing with basic arcane energy."
        Category = "spellstone"
        Rarity = "common"
        Element = ""
    },
    @{
        ItemId = "spellstone_core_uncommon"
        Name = "Refined Core (Uncommon)"
        Description = "A refined crystal with enhanced magical properties."
        Category = "spellstone"
        Rarity = "uncommon"
        Element = ""
    },
    @{
        ItemId = "spellstone_core_rare"
        Name = "Refined Core (Rare)"
        Description = "A sharply faceted crystal with subtle internal glow and enhanced magical properties."
        Category = "spellstone"
        Rarity = "rare"
        Element = ""
    },
    @{
        ItemId = "spellstone_core_epic"
        Name = "Arcane Core (Epic)"
        Description = "A pulsating crystal covered in animated runes, swirling with powerful arcane energy."
        Category = "spellstone"
        Rarity = "epic"
        Element = ""
    },
    @{
        ItemId = "spellstone_core_legendary"
        Name = "Legendary Core"
        Description = "A radiant crystal with rotating inner shards, emanating legendary power."
        Category = "spellstone"
        Rarity = "legendary"
        Element = ""
    },
    # Elemental variants
    @{
        ItemId = "spellstone_fire"
        Name = "Fire Spellstone"
        Description = "A blazing crystal infused with fire elemental energy."
        Category = "spellstone"
        Rarity = "rare"
        Element = "fire"
    },
    @{
        ItemId = "spellstone_ice"
        Name = "Ice Spellstone"
        Description = "A crystalline shard radiating cold elemental energy."
        Category = "spellstone"
        Rarity = "rare"
        Element = "ice"
    },
    @{
        ItemId = "spellstone_poison"
        Name = "Poison Spellstone"
        Description = "A toxic crystal pulsing with poison elemental energy."
        Category = "spellstone"
        Rarity = "rare"
        Element = "poison"
    },
    @{
        ItemId = "spellstone_electric"
        Name = "Electric Spellstone"
        Description = "A crackling crystal charged with electric elemental energy."
        Category = "spellstone"
        Rarity = "rare"
        Element = "electric"
    },
    @{
        ItemId = "spellstone_cosmic"
        Name = "Cosmic Spellstone"
        Description = "A stellar crystal containing cosmic elemental energy."
        Category = "spellstone"
        Rarity = "epic"
        Element = "cosmic"
    }
)

Write-Host "Generating default procedural spellstone assets..." -ForegroundColor Cyan

foreach ($spellstone in $spellstoneDefaults) {
    # Validate ItemId is not empty before generating
    if ([string]::IsNullOrWhiteSpace($spellstone.ItemId)) {
        Write-Host "  [SKIP] Skipping spellstone with empty ItemId: $($spellstone.Name)" -ForegroundColor Yellow
        continue
    }
    
    # Validate ModPath before using it
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        $script:failed++
        Write-Host "  [FAIL] $($spellstone.Name) : ModPath is null or empty" -ForegroundColor Red
        continue
    }
    
    $spellstoneOutputDir = Join-Path $ModPath "assets"
    if ([string]::IsNullOrWhiteSpace($spellstoneOutputDir)) {
        $script:failed++
        Write-Host "  [FAIL] $($spellstone.Name) : OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
        continue
    }
    
    Generate-Sprite `
        -ItemId $spellstone.ItemId `
        -Name $spellstone.Name `
        -Description $spellstone.Description `
        -Category $spellstone.Category `
        -Rarity $spellstone.Rarity `
        -Element $spellstone.Element `
        -OutputDir $spellstoneOutputDir
}

Write-Host "  [OK] Generated $($spellstoneDefaults.Count) default spellstone sprites" -ForegroundColor Green

# ============================================================
# 2. SPELL INGREDIENTS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Ingredient Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$ingredientFiles = @(
    "spellIngredients\basic_elements.json",
    "spellIngredients\crystals.json",
    "spellIngredients\catalysts.json",
    "spellIngredients\rare_components.json",
    "spellIngredients\exotic_materials.json"
)

foreach ($ingredientFile in $ingredientFiles) {
    # Validate ModPath before using it
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        Write-Host "  [FAIL] ModPath is null or empty, skipping: $ingredientFile" -ForegroundColor Red
        continue
    }
    
    $filePath = Join-Path $ModPath $ingredientFile
    if ([string]::IsNullOrWhiteSpace($filePath)) {
        Write-Host "  [FAIL] filePath is null for: $ingredientFile (ModPath: '$ModPath')" -ForegroundColor Red
        continue
    }
    
    if (Test-Path $filePath) {
        try {
            Write-Host "Processing: $ingredientFile" -ForegroundColor Cyan
            $data = Get-Content $filePath -Raw | ConvertFrom-Json
            
            if ($data.ingredients) {
                foreach ($ingredient in $data.ingredients) {
                    # Validate required fields
                    $itemId = if ($ingredient.id) { $ingredient.id } else { "" }
                    if ([string]::IsNullOrWhiteSpace($itemId)) {
                        Write-Host "  [SKIP] Empty ingredient ID in $ingredientFile" -ForegroundColor Yellow
                        continue
                    }
                    
                    $name = if ($ingredient.name) { $ingredient.name } else { $itemId }
                    $description = if ($ingredient.description) { $ingredient.description } else { "A spell ingredient" }
                    $category = if ($ingredient.category) { $ingredient.category } else { "ingredient" }
                    $rarity = if ($ingredient.rarity) { $ingredient.rarity } else { "common" }
                    $element = if ($ingredient.properties -and $ingredient.properties.element) { $ingredient.properties.element } else { "" }
                    
                    # Validate ModPath before using it
                    if ([string]::IsNullOrWhiteSpace($ModPath)) {
                        Write-Host "  [FAIL] ModPath is null or empty, skipping: $itemId" -ForegroundColor Red
                        continue
                    }
                    
                    $ingredientOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($ingredientOutputDir)) {
                        Write-Host "  [FAIL] OutputDir is null for: $itemId (ModPath: '$ModPath')" -ForegroundColor Red
                        continue
                    }
                    
                    Generate-Sprite `
                        -ItemId $itemId `
                        -Name $name `
                        -Description $description `
                        -Category $category `
                        -Rarity $rarity `
                        -Element $element `
                        -OutputDir $ingredientOutputDir
                }
            }
        } catch {
            Write-Host "  [ERROR] Failed to process $ingredientFile : $_" -ForegroundColor Red
        }
    }
}

# ============================================================
# 3. REAGENT ITEMS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Reagent Item Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "  [FAIL] ModPath is null or empty, skipping reagent icon generation" -ForegroundColor Red
} else {
    $reagentDir = Join-Path $ModPath "items\consumable\reagents"
    if ([string]::IsNullOrWhiteSpace($reagentDir)) {
        Write-Host "  [FAIL] reagentDir is null (ModPath: '$ModPath')" -ForegroundColor Red
        Write-Host "  Skipping reagent icon generation" -ForegroundColor Yellow
    } else {
        if (Test-Path $reagentDir) {
            $reagentFiles = Get-ChildItem -Path $reagentDir -Filter "*.item"
            
            foreach ($file in $reagentFiles) {
                try {
                    $data = Get-Content $file.FullName -Raw | ConvertFrom-Json
                    
                    # Validate required fields
                    $itemId = if ($data.itemName) { $data.itemName } else { "" }
                    if ([string]::IsNullOrWhiteSpace($itemId)) {
                        Write-Host "  [SKIP] Empty itemName in $($file.Name)" -ForegroundColor Yellow
                        continue
                    }
                    
                    $name = if ($data.shortdescription) { $data.shortdescription } else { $itemId }
                    $description = if ($data.description) { $data.description } else { "A reagent item for alchemical crafting" }
                    
                    # Extract element from reagentData if available
                    $element = ""
                    if ($data.reagentData -and $data.reagentData.reagentType) {
                        $element = $data.reagentData.reagentType
                    }
                    
                    # Validate ModPath before using it
                    if ([string]::IsNullOrWhiteSpace($ModPath)) {
                        Write-Host "  [FAIL] ModPath is null or empty, skipping: $itemId" -ForegroundColor Red
                        continue
                    }
                    
                    $reagentOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($reagentOutputDir)) {
                        Write-Host "  [FAIL] OutputDir is null for: $itemId (ModPath: '$ModPath')" -ForegroundColor Red
                        continue
                    }
                    
                    Generate-Sprite `
                        -ItemId $itemId `
                        -Name $name `
                        -Description $description `
                        -Category "reagent" `
                        -Rarity $(if ($data.rarity) { $data.rarity.ToLower() } else { "common" }) `
                        -Element $element `
                        -OutputDir $reagentOutputDir
                } catch {
                    Write-Host "  [ERROR] Failed to parse $($file.Name): $_" -ForegroundColor Red
                }
            }
        }
    }
}

# ============================================================
# 4. UNIQUE WEAPONS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weapon Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weapons = @(
    @{
        Id = "alchemical_grenade_launcher"
        Name = "Alchemical Grenade Launcher"
        Description = "A sophisticated launcher that mixes alchemical compounds to create devastating chemical reactions."
        Prompt = "alchemical grenade launcher weapon sprite, chemical mixing device, green and blue colors, mechanical appearance"
    }
)

foreach ($weapon in $weapons) {
    # Validate Id is not empty
    if ([string]::IsNullOrWhiteSpace($weapon.Id)) {
        Write-Host "  [SKIP] Skipping weapon with empty Id: $($weapon.Name)" -ForegroundColor Yellow
        continue
    }
    
    # Validate ModPath before using it
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        Write-Host "  [FAIL] ModPath is null or empty, skipping: $($weapon.Name)" -ForegroundColor Red
        continue
    }
    
    $weaponOutputDir = Join-Path $ModPath "assets"
    if ([string]::IsNullOrWhiteSpace($weaponOutputDir)) {
        Write-Host "  [FAIL] OutputDir is null for: $($weapon.Name) (ModPath: '$ModPath')" -ForegroundColor Red
        continue
    }
    
    Generate-Sprite `
        -ItemId $weapon.Id `
        -Name $weapon.Name `
        -Description $weapon.Prompt `
        -Category "weapon" `
        -Rarity "rare" `
        -OutputDir $weaponOutputDir
}

# ============================================================
# 5. PROJECTILES
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Projectile Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$projectiles = @(
    @{
        Id = "chemicalgrenade"
        Name = "Chemical Grenade"
        Description = "A bouncing chemical orb containing mixed reagents that explodes on impact"
    },
    @{
        Id = "magitech_bolt"
        Name = "Magitech Bolt"
        Description = "A magical energy bolt with arcane properties"
    },
    @{
        Id = "magitech_burst"
        Name = "Magitech Burst"
        Description = "A burst of magical energy projectiles"
    }
)

foreach ($projectile in $projectiles) {
    # Validate Id is not empty
    if ([string]::IsNullOrWhiteSpace($projectile.Id)) {
        Write-Host "  [SKIP] Skipping projectile with empty Id: $($projectile.Name)" -ForegroundColor Yellow
        continue
    }
    
    # Validate ModPath before using it
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        Write-Host "  [FAIL] ModPath is null or empty, skipping: $($projectile.Name)" -ForegroundColor Red
        continue
    }
    
    $projectileOutputDir = Join-Path $ModPath "assets"
    if ([string]::IsNullOrWhiteSpace($projectileOutputDir)) {
        Write-Host "  [FAIL] OutputDir is null for: $($projectile.Name) (ModPath: '$ModPath')" -ForegroundColor Red
        continue
    }
    
    Generate-Sprite `
        -ItemId $projectile.Id `
        -Name $projectile.Name `
        -Description $projectile.Description `
        -Category "projectile" `
        -Rarity "common" `
        -OutputDir $projectileOutputDir
}

# ============================================================
# 6. OBJECTS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Object Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$objects = @(
    @{
        Id = "deviceworkbench"
        Name = "Device Workbench"
        Description = "A magitech workbench for crafting devices and equipment"
    },
    @{
        Id = "magitechspellcraftingstation"
        Name = "Magitech Spellcrafting Station"
        Description = "An advanced station for crafting and modifying spells"
    }
)

foreach ($obj in $objects) {
    # Validate Id is not empty
    if ([string]::IsNullOrWhiteSpace($obj.Id)) {
        Write-Host "  [SKIP] Skipping object with empty Id: $($obj.Name)" -ForegroundColor Yellow
        continue
    }
    
    # Validate ModPath before using it
    if ([string]::IsNullOrWhiteSpace($ModPath)) {
        Write-Host "  [FAIL] ModPath is null or empty, skipping: $($obj.Name)" -ForegroundColor Red
        continue
    }
    
    $objOutputDir = Join-Path $ModPath "assets"
    if ([string]::IsNullOrWhiteSpace($objOutputDir)) {
        Write-Host "  [FAIL] OutputDir is null for: $($obj.Name) (ModPath: '$ModPath')" -ForegroundColor Red
        continue
    }
    
    Generate-Sprite `
        -ItemId $obj.Id `
        -Name $obj.Name `
        -Description $obj.Description `
        -Category "object" `
        -Rarity "common" `
        -OutputDir $objOutputDir
}

# ============================================================
# 7. RUNIC WANDS & STAVES
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Runic Wand & Staff Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wandStaffScript = Join-Path $PSScriptRoot "GenerateWandStaffSprites.ps1"
if (Test-Path $wandStaffScript) {
    try {
        $output = & $wandStaffScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) 2>&1
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
            Write-Host "  [FAIL] Wand and staff generation: Script exited with code $LASTEXITCODE" -ForegroundColor Red
            Write-Host "  Error output: $($output -join "`n")" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK] Wand and staff sprites generated" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [FAIL] Wand and staff generation: $_" -ForegroundColor Red
        Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  Stack: $($_.ScriptStackTrace)" -ForegroundColor Gray
    }
} else {
    Write-Host "  [SKIP] Wand/staff generator script not found" -ForegroundColor Gray
}

# ============================================================
# 8. UNIVERSE SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Universe System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$universeScript = Join-Path $PSScriptRoot "GenerateUniverseAssets.ps1"
if (Test-Path $universeScript) {
    try {
        & $universeScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Universe assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Universe asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Universe asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 9. SPELL SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellScript = Join-Path $PSScriptRoot "GenerateSpellAssets.ps1"
if (Test-Path $spellScript) {
    try {
        & $spellScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Spell assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Spell asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Spell asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 10. ALCHEMY SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Alchemy System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$alchemyScript = Join-Path $PSScriptRoot "GenerateAlchemyAssets.ps1"
if (Test-Path $alchemyScript) {
    try {
        & $alchemyScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Alchemy assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Alchemy asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Alchemy asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 11. DUNGEON SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Dungeon System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$dungeonScript = Join-Path $PSScriptRoot "GenerateDungeonAssets.ps1"
if (Test-Path $dungeonScript) {
    try {
        & $dungeonScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Dungeon assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Dungeon asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Dungeon asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 12. MECH SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mech System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$mechScript = Join-Path $PSScriptRoot "GenerateMechAssets.ps1"
if (Test-Path $mechScript) {
    try {
        & $mechScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Mech assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Mech asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Mech asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 13. WEAPON SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weapon System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weaponScript = Join-Path $PSScriptRoot "GenerateWeaponAssets.ps1"
if (Test-Path $weaponScript) {
    try {
        & $weaponScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Weapon assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Weapon asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Weapon asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 14. SPELLBUS AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating SpellBusAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellBusScript = Join-Path $PSScriptRoot "GenerateSpellBusAssets.ps1"
if (Test-Path $spellBusScript) {
    try {
        & $spellBusScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] SpellBus assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] SpellBus asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] SpellBus asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 15. TEXTURE SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Texture System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$textureSystemScript = Join-Path $PSScriptRoot "GenerateTextureSystemAssets.ps1"
if (Test-Path $textureSystemScript) {
    try {
        & $textureSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Texture system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Texture system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Texture system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 16. SHADER SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Shader System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$shaderSystemScript = Join-Path $PSScriptRoot "GenerateShaderAssets.ps1"
if (Test-Path $shaderSystemScript) {
    try {
        & $shaderSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Shader system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Shader system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Shader system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 17. PORTAL SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalSystemScript = Join-Path $PSScriptRoot "GeneratePortalAssets.ps1"
if (Test-Path $portalSystemScript) {
    try {
        & $portalSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Portal system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Portal system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Portal system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 18. TECH MODULE SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Tech Module System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$techSystemScript = Join-Path $PSScriptRoot "GenerateTechAssets.ps1"
if (Test-Path $techSystemScript) {
    try {
        & $techSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Tech module system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Tech module system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Tech module system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 19. ACID/LIQUID PROJECTILE ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Acid/Liquid Projectile Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$acidLiquidScript = Join-Path $PSScriptRoot "GenerateAcidLiquidAssets.ps1"
if (Test-Path $acidLiquidScript) {
    try {
        & $acidLiquidScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Acid/liquid projectile assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Acid/liquid projectile asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Acid/liquid projectile asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 20. CLUSTER BOMB ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cluster Bomb Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$clusterBombScript = Join-Path $PSScriptRoot "GenerateClusterBombAssets.ps1"
if (Test-Path $clusterBombScript) {
    try {
        & $clusterBombScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Cluster bomb assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Cluster bomb asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Cluster bomb asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 21. ALL GENERATOR MODULE ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating All Generator Module Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$allGeneratorScript = Join-Path $PSScriptRoot "GenerateAllGeneratorAssets.ps1"
if (Test-Path $allGeneratorScript) {
    try {
        & $allGeneratorScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] All generator module assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Generator module asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Generator module asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 22. RUNIC WEAPON SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Runic Weapon System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$runicWeaponScript = Join-Path $PSScriptRoot "GenerateRunicWeaponAssets.ps1"
if (Test-Path $runicWeaponScript) {
    try {
        & $runicWeaponScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Runic weapon system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Runic weapon system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Runic weapon system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 23. BIOME GENERATION SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Biome Generation System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$biomeScript = Join-Path $PSScriptRoot "GenerateBiomeAssets.ps1"
if (Test-Path $biomeScript) {
    try {
        & $biomeScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Biome generation system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Biome generation system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Biome generation system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 24. CREATURE SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Creature System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$creatureScript = Join-Path $PSScriptRoot "GenerateCreatureAssets.ps1"
if (Test-Path $creatureScript) {
    try {
        & $creatureScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Creature system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Creature system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Creature system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 25. RACE GENERATION SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Race Generation System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$raceScript = Join-Path $PSScriptRoot "GenerateRaceAssets.ps1"
if (Test-Path $raceScript) {
    try {
        & $raceScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Race generation system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Race generation system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Race generation system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 26. SHIP STEERING SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Ship Steering System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$shipSteeringScript = Join-Path $PSScriptRoot "GenerateShipSteeringAssets.ps1"
if (Test-Path $shipSteeringScript) {
    try {
        & $shipSteeringScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Ship steering system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Ship steering system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Ship steering system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 27. SPELLBUS SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating SpellBus System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellBusScript = Join-Path $PSScriptRoot "GenerateSpellBusAssets.ps1"
if (Test-Path $spellBusScript) {
    try {
        & $spellBusScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] SpellBus system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] SpellBus system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] SpellBus system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 28. SPELL SYSTEM ASSETS (Spellcasting, Reactions, Spells)
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellSystemScript = Join-Path $PSScriptRoot "GenerateSpellSystemAssets.ps1"
if (Test-Path $spellSystemScript) {
    try {
        & $spellSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Spell system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Spell system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Spell system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 29. STAR SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Star System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$starSystemScript = Join-Path $PSScriptRoot "GenerateStarSystemAssets.ps1"
if (Test-Path $starSystemScript) {
    try {
        & $starSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Star system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Star system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Star system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 30. TAMING SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Taming System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$tamingSystemScript = Join-Path $PSScriptRoot "GenerateTamingSystemAssets.ps1"
if (Test-Path $tamingSystemScript) {
    try {
        & $tamingSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Taming system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Taming system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Taming system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 31. REMAINING SYSTEM ASSETS (UI, Weapons, Wildfire, Status Effects, Traps, Tiles)
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Remaining System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$remainingSystemScript = Join-Path $PSScriptRoot "GenerateRemainingSystemAssets.ps1"
if (Test-Path $remainingSystemScript) {
    try {
        & $remainingSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Remaining system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Remaining system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Remaining system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 32. ANOMALY SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Anomaly System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$anomalySystemScript = Join-Path $PSScriptRoot "GenerateAnomalyAssets.ps1"
if (Test-Path $anomalySystemScript) {
    try {
        & $anomalySystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Anomaly system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Anomaly system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Anomaly system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 33. PLUGIN SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Plugin System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$pluginSystemScript = Join-Path $PSScriptRoot "GeneratePluginAssets.ps1"
if (Test-Path $pluginSystemScript) {
    try {
        & $pluginSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Plugin system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Plugin system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Plugin system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 34. SKILL SYSTEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Skill System Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$skillSystemScript = Join-Path $PSScriptRoot "GenerateSkillSystemAssets.ps1"
if (Test-Path $skillSystemScript) {
    try {
        & $skillSystemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Skill system assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Skill system asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Skill system asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 35. GENERATOR AGENT UI ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating GeneratorAgent UI Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$generatorAgentScript = Join-Path $PSScriptRoot "GenerateGeneratorAgentAssets.ps1"
if (Test-Path $generatorAgentScript) {
    try {
        & $generatorAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] GeneratorAgent UI assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] GeneratorAgent UI asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] GeneratorAgent UI asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 36. MEGAFORM AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating MegaFormAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$megaFormAgentScript = Join-Path $PSScriptRoot "GenerateMegaFormAgentAssets.ps1"
if (Test-Path $megaFormAgentScript) {
    try {
        & $megaFormAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] MegaFormAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] MegaFormAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] MegaFormAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 37. WAND AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating WandAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wandAgentScript = Join-Path $PSScriptRoot "GenerateWandAgentAssets.ps1"
if (Test-Path $wandAgentScript) {
    try {
        & $wandAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] WandAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] WandAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] WandAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 38. SIMULATION AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating SimulationAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$simulationAgentScript = Join-Path $PSScriptRoot "GenerateSimulationAgentAssets.ps1"
if (Test-Path $simulationAgentScript) {
    try {
        & $simulationAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] SimulationAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] SimulationAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] SimulationAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 39. PORTAL AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating PortalAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalAgentScript = Join-Path $PSScriptRoot "GeneratePortalAgentAssets.ps1"
if (Test-Path $portalAgentScript) {
    try {
        & $portalAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] PortalAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] PortalAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] PortalAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 40. GOLEM ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Golem Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$golemScript = Join-Path $PSScriptRoot "GenerateGolemAssets.ps1"
if (Test-Path $golemScript) {
    try {
        & $golemScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Golem assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Golem asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Golem asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 41. INVENTORY AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating InventoryAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$inventoryAgentScript = Join-Path $PSScriptRoot "GenerateInventoryAgentAssets.ps1"
if (Test-Path $inventoryAgentScript) {
    try {
        & $inventoryAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] InventoryAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] InventoryAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] InventoryAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 42. COMPOSITION AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating CompositionAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$compositionAgentScript = Join-Path $PSScriptRoot "GenerateCompositionAgentAssets.ps1"
if (Test-Path $compositionAgentScript) {
    try {
        & $compositionAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] CompositionAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] CompositionAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] CompositionAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 43. BUFF AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating BuffAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$buffAgentScript = Join-Path $PSScriptRoot "GenerateBuffAgentAssets.ps1"
if (Test-Path $buffAgentScript) {
    try {
        & $buffAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] BuffAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] BuffAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] BuffAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 44. DURABILITY AGENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating DurabilityAgent Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$durabilityAgentScript = Join-Path $PSScriptRoot "GenerateDurabilityAgentAssets.ps1"
if (Test-Path $durabilityAgentScript) {
    try {
        & $durabilityAgentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] DurabilityAgent assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] DurabilityAgent asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] DurabilityAgent asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 45. VFS ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating VFS Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$vfsScript = Join-Path $PSScriptRoot "GenerateVFSAssets.ps1"
if (Test-Path $vfsScript) {
    try {
        & $vfsScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] VFS assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] VFS asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] VFS asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 46. ENCHANTMENT ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Enchantment Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$enchantmentScript = Join-Path $PSScriptRoot "GenerateEnchantmentAssets.ps1"
if (Test-Path $enchantmentScript) {
    try {
        & $enchantmentScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Enchantment assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Enchantment asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Enchantment asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 47. ALCHEMIST BUS ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating AlchemistBus Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$alchemistBusScript = Join-Path $PSScriptRoot "GenerateAlchemistBusAssets.ps1"
if (Test-Path $alchemistBusScript) {
    try {
        & $alchemistBusScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] AlchemistBus assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] AlchemistBus asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] AlchemistBus asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 48. ORBITAL ASSETS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Orbital Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$orbitalScript = Join-Path $PSScriptRoot "GenerateOrbitalAssets.ps1"
if (Test-Path $orbitalScript) {
    try {
        & $orbitalScript -ModPath $ModPath -OllamaModel $OllamaModel -UseCppBackend:($UseCppBackend.IsPresent) | Out-Null
        Write-Host "  [OK] Orbital assets generated" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Orbital asset generation: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  [SKIP] Orbital asset generator script not found" -ForegroundColor Gray
}

# ============================================================
# 49. ANIMATIONS
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Animation Spritesheets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$animations = @(
    @{
        Id = "magitech_device"
        Name = "Magitech Device"
        Description = "Magitech device activation animation with 6 frames, pulsing energy, blue and purple colors"
        FrameCount = 6
        AnimationCycle = 1.0
        AnimationType = "DeviceActivation"
    },
    @{
        Id = "spell_cast"
        Name = "Spell Cast"
        Description = "Spell casting animation with growing magical energy, swirling particles"
        FrameCount = 8
        AnimationCycle = 0.6
        AnimationType = "SpellCast"
    },
    @{
        Id = "magic_aura"
        Name = "Magic Aura"
        Description = "Magical aura status effect animation, shimmering energy field"
        FrameCount = 4
        AnimationCycle = 0.8
        AnimationType = "StatusEffect"
    }
)

foreach ($anim in $animations) {
    # Validate animation ID is not empty
    if ([string]::IsNullOrWhiteSpace($anim.Id)) {
        $failed++
        Write-Host "  [FAIL] Skipping animation with empty ID: $($anim.Name)" -ForegroundColor Red
        continue
    }
    
    Write-Host "Generating: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
        $tempOutputDir = Join-Path $ModPath "assets"
        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            Write-Host "  Skipping animation generation" -ForegroundColor Yellow
        } else {
            $params = @{
                AssetType = "AnimationSprite"
                AssetName = $anim.Id
                Prompt = $anim.Description
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
                QualityAssessmentDepth = $QualityAssessmentDepth
                }
            
            # Add animation-specific parameters
            $paramHashtable = @{
                FrameCount = $anim.FrameCount
                AnimationCycle = $anim.AnimationCycle
                AnimationType = $anim.AnimationType
            }
            $params['Parameters'] = $paramHashtable
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($anim.Name)" -ForegroundColor Green
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] $($anim.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 8. GENERATE ASSETS FOR MOD DIRECTORIES
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Assets for Mod Directories" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Generate particles
# Validate $ModPath before Join-Path
$particlesDir = Join-Path $ModPath "particles\magitech"
if ([string]::IsNullOrWhiteSpace($particlesDir)) {
    Write-Host "  [FAIL] particlesDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping particle generation" -ForegroundColor Yellow
} else {
    if (Test-Path $particlesDir) {
        Write-Host "Scanning particles directory..." -ForegroundColor Cyan
        $particleFiles = Get-ChildItem -Path $particlesDir -Filter "*.particle" -ErrorAction SilentlyContinue
        foreach ($file in $particleFiles) {
            $particleName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
            if (-not [string]::IsNullOrWhiteSpace($particleName)) {
                try {
                    # Validate $ModPath before Join-Path
                    $tempOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        Write-Host "  Skipping particle generation" -ForegroundColor Yellow
                    } else {
                        $params = @{
                            AssetType = "Particle"
                            AssetName = $particleName
                            Prompt = "A magical particle effect for $particleName"
                            OllamaModel = $OllamaModel
                            PlanningModel = $PlanningModel
                            VisualModel = $VisualModel
                            OutputDir = $tempOutputDir
                            QualityAssessmentDepth = $QualityAssessmentDepth
                        }
                        $params['UseCppBackend'] = $UseCppBackend
                        
                        & $assetGenerator @params | Out-Null
                        $generated++
                        Write-Host "  [OK] Generated particle: $particleName" -ForegroundColor Green
                    }
                } catch {
                    $failed++
                    Write-Host "  [FAIL] Particle $particleName : $_" -ForegroundColor Red
                }
            }
        }
    }
}

# Generate animations
$animationsDirs = @(
    Join-Path $ModPath "animations\magitech",
    Join-Path $ModPath "animations\spells"
)
foreach ($animDir in $animationsDirs) {
    if (Test-Path $animDir) {
        Write-Host "Scanning animations directory: $animDir..." -ForegroundColor Cyan
        $animFiles = Get-ChildItem -Path $animDir -Filter "*.animation" -ErrorAction SilentlyContinue
        foreach ($file in $animFiles) {
            $animName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
            if (-not [string]::IsNullOrWhiteSpace($animName)) {
                try {
                    # Validate $ModPath before Join-Path
                    $tempOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        Write-Host "  Skipping animation generation" -ForegroundColor Yellow
                    } else {
                        $params = @{
                            AssetType = "AnimationSprite"
                            AssetName = $animName
                            Prompt = "An animation spritesheet for $animName"
                            OllamaModel = $OllamaModel
                            PlanningModel = $PlanningModel
                            VisualModel = $VisualModel
                            OutputDir = $tempOutputDir
                            QualityAssessmentDepth = $QualityAssessmentDepth
                        }
                        $params['UseCppBackend'] = $UseCppBackend
                        
                        & $assetGenerator @params | Out-Null
                        $generated++
                        Write-Host "  [OK] Generated animation: $animName" -ForegroundColor Green
                    }
                } catch {
                    $failed++
                    Write-Host "  [FAIL] Animation $animName : $_" -ForegroundColor Red
                }
            }
        }
    }
}

# Generate projectiles
# Validate $ModPath before Join-Path
$projectilesDir = Join-Path $ModPath "projectiles\magitech"
if ([string]::IsNullOrWhiteSpace($projectilesDir)) {
    Write-Host "  [FAIL] projectilesDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping projectile generation" -ForegroundColor Yellow
} elseif (Test-Path $projectilesDir) {
    Write-Host "Scanning projectiles directory..." -ForegroundColor Cyan
    $projectileFiles = Get-ChildItem -Path $projectilesDir -Filter "*.projectile" -ErrorAction SilentlyContinue
    foreach ($file in $projectileFiles) {
        $projectileName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        if (-not [string]::IsNullOrWhiteSpace($projectileName)) {
            try {
                # Validate $ModPath before Join-Path
                $tempOutputDir = Join-Path $ModPath "assets"
                if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    Write-Host "  Skipping projectile generation" -ForegroundColor Yellow
                } else {
                    $params = @{
                        AssetType = "Projectile"
                        AssetName = $projectileName
                        Prompt = "A magical projectile sprite for $projectileName"
                        OllamaModel = $OllamaModel
                        QualityAssessmentDepth = $QualityAssessmentDepth
                        PlanningModel = $PlanningModel
                        VisualModel = $VisualModel
                        OutputDir = $tempOutputDir
                    }
                    $params['UseCppBackend'] = $UseCppBackend
                    
                    & $assetGenerator @params | Out-Null
                    $generated++
                    Write-Host "  [OK] Generated projectile: $projectileName" -ForegroundColor Green
                }
            } catch {
                $failed++
                Write-Host "  [FAIL] Projectile $projectileName : $_" -ForegroundColor Red
            }
        }
    }
}

# Generate status effect icons
# Validate $ModPath before Join-Path
$statusFile = Join-Path $ModPath "status\statusEffects.config"
if ([string]::IsNullOrWhiteSpace($statusFile)) {
    Write-Host "  [FAIL] statusFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping status effect icon generation" -ForegroundColor Yellow
} elseif (Test-Path $statusFile) {
    Write-Host "Scanning status effects..." -ForegroundColor Cyan
    try {
        $statusData = Get-Content $statusFile -Raw | ConvertFrom-Json
        if ($statusData.statusEffects) {
            $statusData.statusEffects.PSObject.Properties | ForEach-Object {
                $statusId = $_.Name
                $status = $_.Value
                if (-not [string]::IsNullOrWhiteSpace($statusId)) {
                    try {
                        $statusName = if ($status.name) { $status.name } else { $statusId }
                        # Validate $ModPath before Join-Path
                        $tempOutputDir = Join-Path $ModPath "assets"
                        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            Write-Host "  Skipping status icon generation" -ForegroundColor Yellow
                        } else {
                            $params = @{
                                AssetType = "Icon"
                                AssetName = "${statusId}_icon"
                                Prompt = "An icon for status effect: $statusName"
                                OllamaModel = $OllamaModel
                                PlanningModel = $PlanningModel
                                VisualModel = $VisualModel
                                OutputDir = $tempOutputDir
                                QualityAssessmentDepth = $QualityAssessmentDepth
                            }
                            $params['UseCppBackend'] = $UseCppBackend
                            
                            & $assetGenerator @params | Out-Null
                            $generated++
                            Write-Host "  [OK] Generated status icon: $statusId" -ForegroundColor Green
                        }
                    } catch {
                        $failed++
                        Write-Host "  [FAIL] Status icon $statusId : $_" -ForegroundColor Red
                    }
                }
            }
        }
    } catch {
        Write-Host "  [WARN] Could not parse statusEffects.config: $_" -ForegroundColor Yellow
    }
}

# Generate codex icons
# Validate $ModPath before Join-Path
$codexDir = Join-Path $ModPath "codex\magitech"
if ([string]::IsNullOrWhiteSpace($codexDir)) {
    Write-Host "  [FAIL] codexDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping codex icon generation" -ForegroundColor Yellow
} elseif (Test-Path $codexDir) {
    Write-Host "Scanning codex entries..." -ForegroundColor Cyan
    $codexFiles = Get-ChildItem -Path $codexDir -Filter "*.codex" -ErrorAction SilentlyContinue
    foreach ($file in $codexFiles) {
        try {
            $codexData = Get-Content $file.FullName -Raw | ConvertFrom-Json
            $codexId = if ($codexData.id) { $codexData.id } else { [System.IO.Path]::GetFileNameWithoutExtension($file.Name) }
            $codexTitle = if ($codexData.title) { $codexData.title } else { $codexId }
            
            if (-not [string]::IsNullOrWhiteSpace($codexId)) {
                # Generate icon if not already specified or if it doesn't exist
                $iconName = if ($codexData.icon) { 
                    [System.IO.Path]::GetFileNameWithoutExtension($codexData.icon) 
                } else { 
                    "${codexId}_icon" 
                }
                
                # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "interface\codex\$iconName.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
                    Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
                    Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
                if (-not (Test-Path $iconPath)) {
                    try {
                        # Validate $ModPath before Join-Path
                        $tempOutputDir = Join-Path $ModPath "assets"
                        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            Write-Host "  Skipping codex icon generation" -ForegroundColor Yellow
                        } else {
                            $params = @{
                                AssetType = "Icon"
                                AssetName = $iconName
                                Prompt = "An icon for codex entry: $codexTitle"
                                OllamaModel = $OllamaModel
                                PlanningModel = $PlanningModel
                                VisualModel = $VisualModel
                                OutputDir = $tempOutputDir
                                QualityAssessmentDepth = $QualityAssessmentDepth
                            }
                            $params['UseCppBackend'] = $UseCppBackend
                            
                            & $assetGenerator @params | Out-Null
                            $generated++
                            Write-Host "  [OK] Generated codex icon: $codexId" -ForegroundColor Green
                        }
                    } catch {
                        $failed++
                        Write-Host "  [FAIL] Codex icon $codexId : $_" -ForegroundColor Red
                    }
                } else {
                    $skipped++
                    Write-Host "  [SKIP] Codex icon already exists: $codexId" -ForegroundColor Gray
                }
            }
        } catch {
            Write-Host "  [WARN] Could not parse codex file $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

# Generate monster/minion animations and sprites
# Validate $ModPath before Join-Path
$monstersDir = Join-Path $ModPath "monsters\minions"
if ([string]::IsNullOrWhiteSpace($monstersDir)) {
    Write-Host "  [FAIL] monstersDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping monster/minion generation" -ForegroundColor Yellow
} elseif (Test-Path $monstersDir) {
    Write-Host "Scanning monsters/minions..." -ForegroundColor Cyan
    $monsterFiles = Get-ChildItem -Path $monstersDir -Filter "*.monstertype" -ErrorAction SilentlyContinue
    foreach ($file in $monsterFiles) {
        try {
            $monsterData = Get-Content $file.FullName -Raw | ConvertFrom-Json
            $monsterType = if ($monsterData.type) { $monsterData.type } else { [System.IO.Path]::GetFileNameWithoutExtension($file.Name) }
            $monsterName = if ($monsterData.shortdescription) { $monsterData.shortdescription } else { $monsterType }
            
            if (-not [string]::IsNullOrWhiteSpace($monsterType)) {
                # Generate animation if referenced
                if ($monsterData.animation) {
                    $animPath = $monsterData.animation -replace '^/', ''
                    $animName = [System.IO.Path]::GetFileNameWithoutExtension($animPath)
                    
                    if (-not [string]::IsNullOrWhiteSpace($animName)) {
                        $animFullPath = Join-Path $ModPath $animPath
                        if (-not (Test-Path $animFullPath)) {
                            try {
                                # Validate $ModPath before Join-Path
                                $tempOutputDir = Join-Path $ModPath "assets"
                                if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                    Write-Host "  Skipping monster animation generation" -ForegroundColor Yellow
                                } else {
                                    $params = @{
                                        AssetType = "AnimationSprite"
                                        AssetName = $animName
                                        Prompt = "An animation spritesheet for monster: $monsterName"
                                        OllamaModel = $OllamaModel
                                        PlanningModel = $PlanningModel
                                        VisualModel = $VisualModel
                                        OutputDir = $tempOutputDir
                                        QualityAssessmentDepth = $QualityAssessmentDepth
                                    }
                                    $params['UseCppBackend'] = $UseCppBackend
                                    
                                    & $assetGenerator @params | Out-Null
                                    $generated++
                                    Write-Host "  [OK] Generated monster animation: $monsterType" -ForegroundColor Green
                                }
                            } catch {
                                $failed++
                                Write-Host "  [FAIL] Monster animation $monsterType : $_" -ForegroundColor Red
                            }
                        }
                    }
                }
                
                # Generate monster sprite/icon
                try {
                    # Validate $ModPath before Join-Path
                    $tempOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        Write-Host "  Skipping monster sprite generation" -ForegroundColor Yellow
                    } else {
                        $params = @{
                            AssetType = "Sprite"
                            AssetName = "${monsterType}_sprite"
                            Prompt = "A sprite for monster: $monsterName"
                            OllamaModel = $OllamaModel
                            PlanningModel = $PlanningModel
                            VisualModel = $VisualModel
                            OutputDir = $tempOutputDir
                            QualityAssessmentDepth = $QualityAssessmentDepth
                        }
                        $params['UseCppBackend'] = $UseCppBackend
                        
                        & $assetGenerator @params | Out-Null
                        $generated++
                        Write-Host "  [OK] Generated monster sprite: $monsterType" -ForegroundColor Green
                    }
                } catch {
                    $failed++
                    Write-Host "  [FAIL] Monster sprite $monsterType : $_" -ForegroundColor Red
                }
            }
        } catch {
            Write-Host "  [WARN] Could not parse monster file $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

# Generate spellform assets
$spellformsDirs = @(
    Join-Path $ModPath "spellforms\base",
    Join-Path $ModPath "spellforms\integration",
    Join-Path $ModPath "spellforms\community\examples"
)
foreach ($spellformsDir in $spellformsDirs) {
    if (Test-Path $spellformsDir) {
        Write-Host "Scanning spellforms directory: $spellformsDir..." -ForegroundColor Cyan
        $spellformFiles = Get-ChildItem -Path $spellformsDir -Filter "*.json" -ErrorAction SilentlyContinue
        
        foreach ($file in $spellformFiles) {
            try {
                $spellformData = Get-Content $file.FullName -Raw | ConvertFrom-Json
                
                # Handle both single spellform and spellforms array
                $spellformsToProcess = @()
                
                if ($spellformData.spellform) {
                    # Single spellform (sig_*.json files)
                    $spellformsToProcess += $spellformData.spellform
                } elseif ($spellformData.spellforms) {
                    # Multiple spellforms (projectile_spellforms.json, etc.)
                    $spellformData.spellforms.PSObject.Properties | ForEach-Object {
                        $spellformsToProcess += $_.Value
                    }
                }
                
                foreach ($spellform in $spellformsToProcess) {
                    if (-not $spellform) { continue }
                    
                    $spellformId = if ($spellform.id) { $spellform.id } else { "" }
                    if ([string]::IsNullOrWhiteSpace($spellformId)) { continue }
                    
                    $spellformName = if ($spellform.name) { $spellform.name } else { $spellformId }
                    $spellformElement = if ($spellform.element) { $spellform.element } else { "" }
                    $spellformCategory = if ($spellform.category) { $spellform.category } else { "spell" }
                    
                    # Generate spellform icon
                    try {
                        $iconName = "${spellformId}_icon"
                        # Validate $ModPath before Join-Path
                        $tempOutputDir = Join-Path $ModPath "assets"
                        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            Write-Host "  Skipping spellform icon generation" -ForegroundColor Yellow
                        } else {
                            $params = @{
                                AssetType = "Icon"
                                AssetName = $iconName
                                Prompt = "An icon for $spellformCategory spell: $spellformName ($spellformElement elemental)"
                                OllamaModel = $OllamaModel
                                PlanningModel = $PlanningModel
                                VisualModel = $VisualModel
                                OutputDir = $tempOutputDir
                            }
                            $params['UseCppBackend'] = $UseCppBackend
                            
                            & $assetGenerator @params | Out-Null
                            $generated++
                            Write-Host "  [OK] Generated spellform icon: $spellformId" -ForegroundColor Green
                        }
                    } catch {
                        $failed++
                        $script:failedAssets += [PSCustomObject]@{ AssetName = "${spellformId}_icon"; Reason = $_.Exception.Message; Category = "Spellform Icon" }
                        Write-Host "  [FAIL] Spellform icon $spellformId : $_" -ForegroundColor Red
                    }
                    
                    # Generate projectile sprite if it's a projectile spellform
                    if ($spellform.form -eq "projectile" -or $spellformCategory -eq "projectile") {
                        try {
                            $projectileName = "${spellformId}_projectile"
                            $projectilePrompt = "A $spellformElement elemental projectile sprite for spell: $spellformName"
                            if ($spellform.effects -and $spellform.effects.color) {
                                $color = $spellform.effects.color
                                $projectilePrompt += " with color RGB($($color[0]), $($color[1]), $($color[2]))"
                            }
                            
                            # Validate $ModPath before Join-Path
                            $tempOutputDir = Join-Path $ModPath "assets"
                            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                Write-Host "  Skipping spellform projectile generation" -ForegroundColor Yellow
                            } else {
                                $params = @{
                                    AssetType = "Projectile"
                                    AssetName = $projectileName
                                    Prompt = $projectilePrompt
                                    OllamaModel = $OllamaModel
                                    PlanningModel = $PlanningModel
                                    VisualModel = $VisualModel
                                    OutputDir = $tempOutputDir
                                }
                                $params['UseCppBackend'] = $UseCppBackend
                                
                                & $assetGenerator @params | Out-Null
                                $generated++
                                Write-Host "  [OK] Generated spellform projectile: $spellformId" -ForegroundColor Green
                            }
                        } catch {
                            $failed++
                            $script:failedAssets += [PSCustomObject]@{ AssetName = "${spellformId}_projectile"; Reason = $_.Exception.Message; Category = "Spellform Projectile" }
                            Write-Host "  [FAIL] Spellform projectile $spellformId : $_" -ForegroundColor Red
                        }
                    }
                    
                    # Generate particle effect if referenced
                    if ($spellform.effects -and $spellform.effects.particleEffect) {
                        $particleRef = $spellform.effects.particleEffect
                        $particleName = $particleRef -replace '^.*:', '' -replace '^magitech:', ''
                        
                        if (-not [string]::IsNullOrWhiteSpace($particleName)) {
                            try {
                                # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\magitech\${particleName}.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
                                    Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                    continue
                                }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
                                    Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                    continue
                                }
                                if (-not (Test-Path $particlePath)) {
                                    # Validate $ModPath before Join-Path
                                    $tempOutputDir = Join-Path $ModPath "assets"
                                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                        Write-Host "  Skipping spellform particle generation" -ForegroundColor Yellow
                                    } else {
                                        $params = @{
                                            AssetType = "Particle"
                                            AssetName = $particleName
                                            Prompt = "A $spellformElement elemental particle effect for spell: $spellformName"
                                            OllamaModel = $OllamaModel
                                            PlanningModel = $PlanningModel
                                            VisualModel = $VisualModel
                                            OutputDir = $tempOutputDir
                                        }
                                        $params['UseCppBackend'] = $UseCppBackend
                                        
                                        & $assetGenerator @params | Out-Null
                                        $generated++
                                        Write-Host "  [OK] Generated spellform particle: $particleName" -ForegroundColor Green
                                    }
                                }
                            } catch {
                                $failed++
                                $script:failedAssets += [PSCustomObject]@{ AssetName = "Form particle $particleName"; Reason = $_.Exception.Message; Category = "Spellform Particle" }
                                Write-Host "  [FAIL] Spellform particle $particleName : $_" -ForegroundColor Red
                            }
                        }
                    }
                }
            } catch {
                Write-Host "  [WARN] Could not parse spellform file $($file.Name): $_" -ForegroundColor Yellow
            }
        }
    }
}

# Generate mech form assets (Rhino, etc.)
# Validate $ModPath before Join-Path
$mechFormsDir = Join-Path $ModPath "Data\Config\Mechs"
if ([string]::IsNullOrWhiteSpace($mechFormsDir)) {
    Write-Host "  [FAIL] mechFormsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping mech form generation" -ForegroundColor Yellow
} elseif (Test-Path $mechFormsDir) {
    Write-Host "Scanning mech forms directory..." -ForegroundColor Cyan
    $mechFormFiles = Get-ChildItem -Path $mechFormsDir -Filter "*Form.json" -ErrorAction SilentlyContinue
    
    foreach ($file in $mechFormFiles) {
        try {
            $formData = Get-Content $file.FullName -Raw | ConvertFrom-Json
            $formId = if ($formData.id) { $formData.id } else { [System.IO.Path]::GetFileNameWithoutExtension($file.Name) }
            $formName = if ($formData.displayName) { $formData.displayName } else { $formId }
            
            if ([string]::IsNullOrWhiteSpace($formId)) { continue }
            
            Write-Host "Processing mech form: $formName ($formId)" -ForegroundColor Cyan
            
            # Generate VFX particles
            $vfxPaths = @()
            if ($formData.vfxEnter) { $vfxPaths += $formData.vfxEnter }
            if ($formData.vfxLoop) { $vfxPaths += $formData.vfxLoop }
            if ($formData.vfxExit) { $vfxPaths += $formData.vfxExit }
            
            # Check abilities for VFX
            if ($formData.abilities) {
                $formData.abilities.PSObject.Properties | ForEach-Object {
                    $ability = $_.Value
                    if ($ability.vfxTrail) { $vfxPaths += $ability.vfxTrail }
                }
            }
            
            foreach ($vfxPath in $vfxPaths) {
                if (-not [string]::IsNullOrWhiteSpace($vfxPath)) {
                    $particleName = $vfxPath -replace '^/particles/', '' -replace '^particles/', '' -replace '\.particle$', ''
                    if (-not [string]::IsNullOrWhiteSpace($particleName)) {
                        # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\$particleName.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
                            Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            continue
                        }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
                            Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            continue
                        }
                        $particleDir = Split-Path -Parent $particlePath
                        if (-not (Test-Path $particleDir)) {
                            New-Item -ItemType Directory -Path $particleDir -Force | Out-Null
                        }
                        
                        if (-not (Test-Path $particlePath)) {
                            try {
                                # Validate $ModPath before Join-Path
                                $tempOutputDir = Join-Path $ModPath "assets"
                                if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                    Write-Host "  Skipping form particle generation" -ForegroundColor Yellow
                                } else {
                                    $params = @{
                                        AssetType = "Particle"
                                        AssetName = $particleName
                                        Prompt = "A particle effect for $formName mech form: $particleName (earth elemental, charging energy, dust and debris)"
                                        OllamaModel = $OllamaModel
                                        PlanningModel = $PlanningModel
                                        VisualModel = $VisualModel
                                        OutputDir = $tempOutputDir
                                    }
                                    $params['UseCppBackend'] = $UseCppBackend
                                    
                                    & $assetGenerator @params | Out-Null
                                    $generated++
                                    Write-Host "  [OK] Generated form particle: $particleName" -ForegroundColor Green
                                }
                            } catch {
                                $failed++
                                $failed++
                                $script:failedAssets += [PSCustomObject]@{ AssetName = "Form particle $particleName"; Reason = $_.Exception.Message; Category = "Mech Form Particle" }
                                Write-Host "  [FAIL] Form particle $particleName : $_" -ForegroundColor Red
                            }
                        } else {
                            $skipped++
                            Write-Host "  [SKIP] Particle already exists: $particleName" -ForegroundColor Gray
                        }
                    }
                }
            }
            
            # Generate form icon/sprite
            try {
                # Validate ModPath is not empty
                if ([string]::IsNullOrWhiteSpace($ModPath)) {
                    $script:failed++
                    Write-Host "  [FAIL] Form icon $formId : ModPath is empty" -ForegroundColor Red
                    continue
                }
                
                $formIconName = "${formId}_form_icon"
                # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                    Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
                    Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
                
                # Validate outputDir is not null
                if ([string]::IsNullOrWhiteSpace($outputDir)) {
                    $script:failed++
                    Write-Host "  [FAIL] Form icon $formId : OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
                    continue
                }
                
                $params = @{
                    AssetType = "Icon"
                    AssetName = $formIconName
                    Prompt = "An icon for mech form: $formName ($formId) - $($formData.tags -join ', ') form"
                    OllamaModel = $OllamaModel
                    PlanningModel = $PlanningModel
                    VisualModel = $VisualModel
                    OutputDir = $outputDir
                }
                $params['UseCppBackend'] = $UseCppBackend
                
                & $assetGenerator @params | Out-Null
                $script:generated++
                Write-Host "  [OK] Generated form icon: $formId" -ForegroundColor Green
            } catch {
                $script:failed++
                Write-Host "  [FAIL] Form icon $formId : $_" -ForegroundColor Red
            }
            
            # Generate sound effects
            $sfxPaths = @()
            if ($formData.sfxEnter) { $sfxPaths += $formData.sfxEnter }
            if ($formData.sfxExit) { $sfxPaths += $formData.sfxExit }
            
            # Check abilities for SFX
            if ($formData.abilities) {
                $formData.abilities.PSObject.Properties | ForEach-Object {
                    $ability = $_.Value
                    if ($ability.sfxStart) { $sfxPaths += $ability.sfxStart }
                    if ($ability.sfxImpact) { $sfxPaths += $ability.sfxImpact }
                }
            }
            
            foreach ($sfxPath in $sfxPaths) {
                if (-not [string]::IsNullOrWhiteSpace($sfxPath)) {
                    $soundName = [System.IO.Path]::GetFileNameWithoutExtension($sfxPath)
                    if (-not [string]::IsNullOrWhiteSpace($soundName)) {
                        # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "sfx\$soundName.ogg"
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
                            Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            continue
                        }
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
                            Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                            continue
                        }
                        $soundDir = Split-Path -Parent $soundPath
                        if (-not (Test-Path $soundDir)) {
                            New-Item -ItemType Directory -Path $soundDir -Force | Out-Null
                        }
                        
                        if (-not (Test-Path $soundPath)) {
                            try {
                                # Determine sound type from name
                                $soundType = "Impact"
                                $soundNameLower = $soundName.ToLower()
                                if ($soundNameLower -match "charge|building") { $soundType = "Charge" }
                                elseif ($soundNameLower -match "roar|growl") { $soundType = "Roar" }
                                elseif ($soundNameLower -match "impact|hit") { $soundType = "Impact" }
                                elseif ($soundNameLower -match "magic|magical") { $soundType = "Magic" }
                                elseif ($soundNameLower -match "mechanical") { $soundType = "Mechanical" }
                                
                                # Validate $ModPath before Join-Path
                                $tempOutputDir = Join-Path $ModPath "assets"
                                if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                    Write-Host "  Skipping form sound generation" -ForegroundColor Yellow
                                } else {
                                    $params = @{
                                        AssetType = "Sound"
                                        AssetName = $soundName
                                        Prompt = "A sound effect for $formName mech form: $soundName ($soundType type)"
                                        OllamaModel = $OllamaModel
                                        PlanningModel = $PlanningModel
                                        VisualModel = $VisualModel
                                        OutputDir = $tempOutputDir
                                    }
                                    $params['UseCppBackend'] = $UseCppBackend
                                    
                                    # Add sound-specific parameters
                                    $soundParams = @{
                                        SoundType = $soundType
                                        Format = "ogg"
                                    }
                                    $params['Parameters'] = $soundParams
                                    
                                    & $assetGenerator @params | Out-Null
                                    $generated++
                                    Write-Host "  [OK] Generated form sound: $soundName" -ForegroundColor Green
                                }
                            } catch {
                                $failed++
                                $failed++
                                $script:failedAssets += [PSCustomObject]@{ AssetName = "Form sound $soundName"; Reason = $_.Exception.Message; Category = "Mech Form Sound" }
                                Write-Host "  [FAIL] Form sound $soundName : $_" -ForegroundColor Red
                            }
                        } else {
                            $skipped++
                            Write-Host "  [SKIP] Sound already exists: $soundName" -ForegroundColor Gray
                        }
                    }
                }
            }
        } catch {
            Write-Host "  [WARN] Could not parse mech form file $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

# Generate mech assets for shiftable mechs
# Validate $ModPath before Join-Path
$mechsDir = Join-Path $ModPath "assets\mechs"
 if ([string]::IsNullOrWhiteSpace($mechsDir)) {
    Write-Host "  [FAIL] mechsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($mechsDir)) {
    Write-Host "  [FAIL] mechsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $mechsDir) {
    Write-Host "Scanning mechs directory..." -ForegroundColor Cyan
    $mechFiles = Get-ChildItem -Path $mechsDir -Filter "*.mechdef" -ErrorAction SilentlyContinue
    
    foreach ($file in $mechFiles) {
        try {
            $mechContent = Get-Content $file.FullName -Raw
            $mechName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
            
            # Parse basic mech info from mechdef
            $mechDescription = ""
            if ($mechContent -match 'description:\s*"([^"]+)"') {
                $mechDescription = $matches[1]
            } elseif ($mechContent -match 'description:\s*([^\n]+)') {
                $mechDescription = $matches[1].Trim()
            }
            
            if ([string]::IsNullOrWhiteSpace($mechDescription)) {
                $mechDescription = "A shiftable Magitech mech with form-changing capabilities"
            }
            
            # Extract form types from morphProfiles
            $forms = @()
            if ($mechContent -match 'fromForm:\s*"([^"]+)"') {
                $forms += $matches[1]
            }
            if ($mechContent -match 'toForm:\s*"([^"]+)"') {
                $forms += $matches[1]
            }
            $forms = $forms | Select-Object -Unique
            
            $formDescription = if ($forms.Count -gt 0) {
                " with forms: $($forms -join ', ')"
            } else {
                ""
            }
            
            if (-not [string]::IsNullOrWhiteSpace($mechName)) {
                # Generate mech sprite (main visual)
                try {
                    # Validate $ModPath before Join-Path
                    $tempOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        Write-Host "  Skipping mech sprite generation" -ForegroundColor Yellow
                    } else {
                        $params = @{
                            AssetType = "MechSprite"
                            AssetName = $mechName
                            Prompt = "$mechDescription$formDescription"
                            OllamaModel = $OllamaModel
                            PlanningModel = $PlanningModel
                            VisualModel = $VisualModel
                            OutputDir = $tempOutputDir
                        }
                        $params['UseCppBackend'] = $UseCppBackend
                        
                        & $assetGenerator @params | Out-Null
                        $generated++
                        Write-Host "  [OK] Generated mech sprite: $mechName" -ForegroundColor Green
                    }
                } catch {
                    $failed++
                    Write-Host "  [FAIL] Mech sprite $mechName : $_" -ForegroundColor Red
                }
                
                # Generate mech icon
                try {
                    $iconName = "${mechName}_icon"
                    # Validate $ModPath before Join-Path
                    $tempOutputDir = Join-Path $ModPath "assets"
                    if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        Write-Host "  Skipping mech icon generation" -ForegroundColor Yellow
                    } else {
                        $params = @{
                            AssetType = "Icon"
                            AssetName = $iconName
                            Prompt = "An icon for shiftable mech: $mechName$formDescription"
                            OllamaModel = $OllamaModel
                            PlanningModel = $PlanningModel
                            VisualModel = $VisualModel
                            OutputDir = $tempOutputDir
                        }
                        $params['UseCppBackend'] = $UseCppBackend
                        
                        & $assetGenerator @params | Out-Null
                        $generated++
                        Write-Host "  [OK] Generated mech icon: $mechName" -ForegroundColor Green
                    }
                } catch {
                    $failed++
                    Write-Host "  [FAIL] Mech icon $mechName : $_" -ForegroundColor Red
                }
                
                # Generate form-specific sprites if forms are defined
                foreach ($form in $forms) {
                    if (-not [string]::IsNullOrWhiteSpace($form)) {
                        try {
                            $formSpriteName = "${mechName}_${form.ToLower()}"
                            # Validate $ModPath before Join-Path
                            $tempOutputDir = Join-Path $ModPath "assets"
                            if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                                Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                                Write-Host "  Skipping mech form sprite generation" -ForegroundColor Yellow
                            } else {
                                $params = @{
                                    AssetType = "MechSprite"
                                    AssetName = $formSpriteName
                                    Prompt = "$mechDescription in $form form"
                                    OllamaModel = $OllamaModel
                                    PlanningModel = $PlanningModel
                                    VisualModel = $VisualModel
                                    OutputDir = $tempOutputDir
                                }
                                $params['UseCppBackend'] = $UseCppBackend
                                
                                & $assetGenerator @params | Out-Null
                                $generated++
                                Write-Host "  [OK] Generated mech form sprite: $formSpriteName" -ForegroundColor Green
                            }
                        } catch {
                            $failed++
                            Write-Host "  [FAIL] Mech form sprite ${mechName}_${form} : $_" -ForegroundColor Red
                        }
                    }
                }
            }
        } catch {
            Write-Host "  [WARN] Could not parse mech file $($file.Name): $_" -ForegroundColor Yellow
        }
    }
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated sprites" -ForegroundColor Green
Write-Host "Skipped: $skipped sprites (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed sprites" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
if ($script:lowQualityCount -gt 0) {
    Write-Host "  (Includes $script:lowQualityCount low-quality colored backgrounds that were deleted)" -ForegroundColor Yellow
}
Write-Host ""

# Output failure report if there are failures
if ($script:failedAssets.Count -gt 0) {
    $failureReportPath = Join-Path $ModPath "ASSET_GENERATION_FAILURES.txt"
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  Failed Assets Report" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    
    $reportLines = @()
    $reportLines += "Asset Generation Failure Report"
    $reportLines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $reportLines += "=" * 60
    $reportLines += ""
    $reportLines += "Total Failed Assets: $($script:failedAssets.Count)"
    $reportLines += ""
    
    # Group by category
    $byCategory = $script:failedAssets | Group-Object -Property Category
    foreach ($category in $byCategory) {
        $reportLines += "Category: $($category.Name) ($($category.Count) failures)"
        $reportLines += "-" * 60
        foreach ($asset in $category.Group) {
            $reportLines += "  - $($asset.AssetName)"
            $reportLines += "    Reason: $($asset.Reason)"
        }
        $reportLines += ""
    }
    
    # Detailed list
    $reportLines += "=" * 60
    $reportLines += "Detailed Failure List:"
    $reportLines += "=" * 60
    $reportLines += ""
    foreach ($asset in $script:failedAssets) {
        $reportLines += "Asset: $($asset.AssetName)"
        $reportLines += "Category: $($asset.Category)"
        $reportLines += "Reason: $($asset.Reason)"
        $reportLines += ""
    }
    
    $reportLines | Out-File -FilePath $failureReportPath -Encoding UTF8
    Write-Host "Failure report saved to: $failureReportPath" -ForegroundColor Yellow
    Write-Host ""
    
    # Display summary
    Write-Host "Failed Assets Summary:" -ForegroundColor Red
    foreach ($category in $byCategory) {
        Write-Host "  $($category.Name): $($category.Count) failures" -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Delete failed asset files
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Cleaning Up Failed Assets" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    # Function to detect low-quality images (colored backgrounds with minimal detail)
    function Test-LowQualityImage {
        param([string]$ImagePath)
        
        if (-not (Test-Path $ImagePath)) {
            return $false
        }
        
        try {
            # Use ImageMagick to analyze image quality
            $magickExe = "magick"
            $magickCmd = Get-Command $magickExe -ErrorAction SilentlyContinue
            
            if ($magickCmd) {
                # Check image statistics: standard deviation of colors
                # Low-quality images (colored backgrounds) have very low standard deviation
                $stats = & $magickExe $ImagePath -format "%[fx:standard_deviation]" info: 2>&1
                
                if ($LASTEXITCODE -eq 0 -and $stats) {
                    $stdDev = [double]$stats
                    # If standard deviation is very low (< 0.1), it's likely just a solid/colored background
                    if ($stdDev -lt 0.1) {
                        return $true
                    }
                }
                
                # Also check for very few unique colors (another indicator of low quality)
                $uniqueColors = & $magickExe $ImagePath -format "%[fx:colors]" info: 2>&1
                if ($LASTEXITCODE -eq 0 -and $uniqueColors) {
                    $colorCount = [int]$uniqueColors
                    # If image has very few colors (< 10), it's likely low quality
                    if ($colorCount -lt 10) {
                        return $true
                    }
                }
            }
        }
        catch {
            # If ImageMagick not available, use file size as heuristic
            # Very small files might be placeholders
            $fileInfo = Get-Item $ImagePath -ErrorAction SilentlyContinue
            if ($fileInfo -and $fileInfo.Length -lt 500) {
                # Files smaller than 500 bytes are likely placeholders
                return $true
            }
        }
        
        return $false
    }
    
    $deletedCount = 0
    $deletedFiles = @()
    $script:lowQualityCount = 0
    
    foreach ($failedAsset in $script:failedAssets) {
        $assetName = $failedAsset.AssetName
        $category = $failedAsset.Category
        
        # Skip validation errors (no files created)
        if ($category -eq "Validation") {
            continue
        }
        
        # Determine file paths based on asset type and name
        $filesToDelete = @()
        
        # Extract base name (remove prefixes like "Form particle ", "Form sound ")
        $baseName = $assetName
        if ($baseName -match "^Form (particle|sound) (.+)$") {
            $baseName = $matches[2]
        }
        elseif ($baseName -match "^(.+)_(icon|projectile)$") {
            $baseName = $matches[1]
        }
        
        # Determine asset type from category
        $assetType = switch -Wildcard ($category) {
            "*Particle*" { "Particle" }
            "*Sound*" { "Sound" }
            "*Icon*" { "Icon" }
            "*Projectile*" { "Projectile" }
            "*Sprite*" { "Sprite" }
            default { "Unknown" }
        }
        
        # Build potential file paths
        $assetsDir = Join-Path $ModPath "assets"
        
        if ($assetType -eq "Particle") {
            # Particles can be in subdirectories (e.g., coilSerpent/enter.particle)
            if ($baseName -match "^(.+)/(.+)$") {
                $subDir = $matches[1]
                $particleFile = $matches[2]
                $particlePath = Join-Path $assetsDir "$subDir\$particleFile.particle"
            } else {
                $particlePath = Join-Path $assetsDir "$baseName.particle"
            }
            $filesToDelete += $particlePath
        }
        elseif ($assetType -eq "Sound") {
            # Sounds in sfx directory
            $soundPath = Join-Path $assetsDir "sfx\$baseName.ogg"
            $filesToDelete += $soundPath
            $soundPath = Join-Path $assetsDir "sfx\$baseName.wav"
            $filesToDelete += $soundPath
        }
        elseif ($assetType -eq "Icon" -or $assetType -eq "Sprite") {
            # Icons and sprites with .png and .frames
            $spritePath = Join-Path $assetsDir "items\sprites\$baseName.png"
            $filesToDelete += $spritePath
            $framesPath = Join-Path $assetsDir "items\sprites\$baseName.frames"
            $filesToDelete += $framesPath
            # Also check interface/icons
            $iconPath = Join-Path $assetsDir "interface\icons\$baseName.png"
            $filesToDelete += $iconPath
            $iconFramesPath = Join-Path $assetsDir "interface\icons\$baseName.frames"
            $filesToDelete += $iconFramesPath
        }
        elseif ($assetType -eq "Projectile") {
            # Projectiles
            $projectilePath = Join-Path $assetsDir "projectiles\$baseName.png"
            $filesToDelete += $projectilePath
            $projectileFramesPath = Join-Path $assetsDir "projectiles\$baseName.frames"
            $filesToDelete += $projectileFramesPath
        }
        
        # Use FilePath from failed asset if available, otherwise use computed paths
        if ($failedAsset.FilePath -and (Test-Path $failedAsset.FilePath)) {
            $filesToDelete = @($failedAsset.FilePath)
            # Also check for .frames file
            $framesPath = $failedAsset.FilePath -replace '\.png$', '.frames'
            if (Test-Path $framesPath) {
                $filesToDelete += $framesPath
            }
        }
        
        # Delete files that exist
        foreach ($filePath in $filesToDelete) {
            if (-not [string]::IsNullOrWhiteSpace($filePath) -and (Test-Path $filePath)) {
                # Always delete failed assets (they're known failures)
                try {
                    Remove-Item -Path $filePath -Force -ErrorAction Stop
                    $deletedCount++
                    $deletedFiles += $filePath
                    Write-Host "  [DELETED] Failed asset: $filePath" -ForegroundColor Gray
                } catch {
                    Write-Host "  [WARNING] Could not delete $filePath : $_" -ForegroundColor Yellow
                }
            }
        }
    }
    
    # Also scan for and delete low-quality images that weren't tracked as failures
    # These are "colored backgrounds with specs" - complete failures that need cleanup
    Write-Host "Scanning for low-quality generated assets (colored backgrounds/placeholders)..." -ForegroundColor Gray
    $assetsDir = Join-Path $ModPath "assets"
    if (Test-Path $assetsDir) {
        # Check all PNG files created in the last 2 hours (during this generation run)
        $imageFiles = Get-ChildItem -Path $assetsDir -Filter "*.png" -Recurse -File -ErrorAction SilentlyContinue | 
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-2) }  # Check recently created files
        
        Write-Host "  Checking $($imageFiles.Count) recently generated image(s) for quality..." -ForegroundColor Gray
        
        foreach ($imageFile in $imageFiles) {
            # Skip if already in deletion list
            if ($deletedFiles -contains $imageFile.FullName) {
                continue
            }
            
            # Check if it's low quality (colored background with minimal detail)
            if (Test-LowQualityImage -ImagePath $imageFile.FullName) {
                try {
                    Remove-Item -Path $imageFile.FullName -Force -ErrorAction Stop
                    $deletedCount++
                    $script:lowQualityCount++
                    $deletedFiles += $imageFile.FullName
                    Write-Host "  [DELETED] Low quality (colored background): $($imageFile.Name)" -ForegroundColor Yellow
                    
                    # Also delete .frames file if it exists
                    $framesFile = $imageFile.FullName -replace '\.png$', '.frames'
                    if (Test-Path $framesFile) {
                        Remove-Item -Path $framesFile -Force -ErrorAction SilentlyContinue
                        $deletedFiles += $framesFile
                    }
                    
                    # Track this as a low-quality failure
                    $script:failedAssets += [PSCustomObject]@{ 
                        AssetName = $imageFile.BaseName; 
                        Reason = "Low quality - colored background with minimal detail"; 
                        Category = "Low Quality"
                        FilePath = $imageFile.FullName
                    }
                } catch {
                    Write-Host "  [WARNING] Could not delete $($imageFile.FullName) : $_" -ForegroundColor Yellow
                }
            }
        }
    }
    
    if ($deletedCount -gt 0) {
        Write-Host ""
        Write-Host "Deleted $deletedCount failed/low-quality asset file(s)" -ForegroundColor Green
        if ($script:lowQualityCount -gt 0) {
            Write-Host "  ($script:lowQualityCount were low-quality colored backgrounds - complete failures)" -ForegroundColor Yellow
            Write-Host "  These will be regenerated on next run" -ForegroundColor Gray
        }
        Write-Host ""
        
        # Update failure count to include low-quality detections
        $failed += $script:lowQualityCount
        
        # Add deletion info to failure report
        $deletionInfo = @()
        $deletionInfo += ""
        $deletionInfo += "=" * 60
        $deletionInfo += "Deleted Files:"
        $deletionInfo += "=" * 60
        $deletionInfo += ""
        $deletionInfo += "Total deleted: $deletedCount"
        if ($script:lowQualityCount -gt 0) {
            $deletionInfo += "Low-quality (colored backgrounds/placeholders): $script:lowQualityCount"
            $deletionInfo += "  These are complete failures - just colored backgrounds with minimal detail"
        }
        $deletionInfo += ""
        foreach ($file in $deletedFiles) {
            $deletionInfo += "  - $file"
        }
        $deletionInfo | Out-File -FilePath $failureReportPath -Append -Encoding UTF8
    } else {
        Write-Host "No failed asset files found to delete" -ForegroundColor Gray
        Write-Host ""
    }
}

# Final Summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Generated: $generated sprites" -ForegroundColor Green
Write-Host "Skipped: $skipped sprites (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed sprites" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host "Total processed: $($generated + $skipped + $failed)" -ForegroundColor Cyan
Write-Host ""
if ($script:failedAssets.Count -gt 0) {
    Write-Host "Failed Assets by Category:" -ForegroundColor Yellow
    $categoryGroups = $script:failedAssets | Group-Object -Property Category
    foreach ($group in $categoryGroups) {
        Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  See failed_assets_report.txt for detailed failure information" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Sprites saved to: $(Join-Path $ModPath 'assets\items\sprites')" -ForegroundColor Gray
Write-Host ""
Write-Host "Next step: Run UpdateItemSprites.ps1 to update JSON references" -ForegroundColor Yellow
Write-Host ""

# Unload any remaining Ollama models to free VRAM
if (Get-Command Unload-OllamaModel -ErrorAction SilentlyContinue) {
    Write-Host "Unloading Ollama models to free VRAM..." -ForegroundColor Gray
    try {
        # Get list of loaded models
        $ollamaUrl = "http://localhost:11434"
        $response = Invoke-RestMethod -Uri "$ollamaUrl/api/ps" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response -and $response.models) {
            foreach ($model in $response.models) {
                if ($model.name) {
                    Unload-OllamaModel -ModelName $model.name
                    Write-Host "  Unloaded: $($model.name)" -ForegroundColor Gray
                }
            }
        }
    } catch {
        # Ignore errors - models may already be unloaded
    }
    Write-Host "  VRAM freed" -ForegroundColor Green
    Write-Host ""
}
