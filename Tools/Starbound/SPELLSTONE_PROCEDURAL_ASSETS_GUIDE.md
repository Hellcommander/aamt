# Spellstone Procedural Asset System Guide

## Overview

Spellstones are **procedural items** that contain:
1. **Spellform** - A base spell (e.g., fireBolt, iceShard, lightningBolt) with a delivery type (projectile, beam, area, self, etc.)
2. **Spellshapes** - Modifiers that alter the spellform (e.g., amplify, pierce, split, homing) with different strength levels

This guide explains how to structure and use multiple spellstone asset types for procedural item generation that accounts for spellform types, delivery types, spellshape modifiers, and strength levels.

### Template-Based Generation

Instead of generating assets from scratch, this system uses a **base template image** (the detailed spellstone design) and creates variants by:
- **Color modification** - Changing the core glow and energy pattern colors for different elements
- **Intensity adjustment** - Modifying glow intensity and pattern density for strength levels
- **Animation generation** - Creating pulsing, swirling, and glow effects using OpenStarbound's animation system
- **Layered composition** - Combining base spellform + spellshape overlays + delivery effects

## Problem Statement

Unlike static items with fixed sprites, procedural spellstones need:
- **Dynamic asset selection** based on spellform type, delivery type, element, and spellshape modifiers
- **Multiple asset variants** for spellform/spellshape combinations
- **Strength level visualization** for spellshape effects (weak, moderate, strong, extreme)
- **Layered composition** (base sprite + spellform effects + spellshape overlays)
- **Runtime asset assignment** when items are generated procedurally

## Solution Architecture

### 1. Asset Organization Structure

Organize spellstone assets using a **hierarchical naming convention** that supports procedural selection based on spellform, delivery type, element, and spellshape modifiers:

```
assets/spellstones/
├── spellforms/              # Base spellform sprites organized by delivery type
│   ├── projectile/          # Projectile-based spellforms
│   │   ├── fireBolt/
│   │   │   ├── fireBolt_base_01.png
│   │   │   ├── fireBolt_base_02.png
│   │   │   └── fireBolt_base_03.png
│   │   ├── iceShard/
│   │   ├── lightningBolt/
│   │   └── ...
│   ├── beam/                # Beam-based spellforms
│   │   ├── fireBeam/
│   │   ├── iceBeam/
│   │   └── ...
│   ├── area/                # Area-effect spellforms
│   │   ├── fireNova/
│   │   ├── iceBlast/
│   │   └── ...
│   └── self/                # Self-targeted spellforms
│       ├── fireShield/
│       ├── iceArmor/
│       └── ...
│
├── spellshapes/             # Spellshape modifier overlays
│   ├── amplify/             # Amplification modifier
│   │   ├── weak/           # Weak strength level
│   │   │   ├── amplify_weak_01.png
│   │   │   └── amplify_weak_02.png
│   │   ├── moderate/
│   │   ├── strong/
│   │   └── extreme/
│   ├── pierce/              # Piercing modifier
│   │   ├── weak/
│   │   ├── moderate/
│   │   ├── strong/
│   │   └── extreme/
│   ├── split/              # Splitting modifier
│   ├── homing/              # Homing modifier
│   ├── explode/             # Explosive modifier
│   ├── chain/               # Chain modifier
│   └── ...
│
├── delivery_effects/        # Delivery type visual effects
│   ├── projectile_trail.particle
│   ├── beam_glow.particle
│   ├── area_ring.particle
│   └── self_aura.particle
│
└── ui/                      # UI icons and frames
    ├── spellform_icons/
    ├── spellshape_icons/
    └── frames/
```

### 2. Asset Naming Convention

Use a **structured naming pattern** that encodes spellform, delivery type, element, spellshape modifiers, and strength levels:

#### Spellform Assets:
```
{spellformId}_{deliveryType}_{variant}.{ext}
```

**Examples:**
- `fireBolt_projectile_01.png` - Fire bolt spellform, projectile delivery, variant 1
- `iceShard_projectile_02.png` - Ice shard spellform, projectile delivery, variant 2
- `lightningBeam_beam_01.png` - Lightning beam spellform, beam delivery, variant 1
- `fireNova_area_01.png` - Fire nova spellform, area delivery, variant 1

#### Spellshape Overlay Assets:
```
{spellshapeId}_{strengthLevel}_{variant}.{ext}
```

**Examples:**
- `amplify_weak_01.png` - Amplify spellshape, weak strength, variant 1
- `pierce_moderate_02.png` - Pierce spellshape, moderate strength, variant 2
- `split_strong_01.png` - Split spellshape, strong strength, variant 1
- `homing_extreme_01.png` - Homing spellshape, extreme strength, variant 1

#### Combined Spellstone Asset:
```
spellstone_{spellformId}_{deliveryType}_{spellshapeIds}_{variant}.{ext}
```

**Examples:**
- `spellstone_fireBolt_projectile_amplify_01.png` - Fire bolt with amplify modifier
- `spellstone_iceShard_projectile_pierce_split_01.png` - Ice shard with pierce and split modifiers
- `spellstone_lightningBeam_beam_chain_extreme_01.png` - Lightning beam with extreme chain modifier

**Pattern Components:**
- `{spellformId}`: fireBolt, iceShard, lightningBolt, fireNova, etc.
- `{deliveryType}`: projectile, beam, area, self, channel, etc.
- `{spellshapeId}`: amplify, pierce, split, homing, explode, chain, etc.
- `{strengthLevel}`: weak, moderate, strong, extreme
- `{variant}`: 01, 02, 03... (for multiple visual variants)
- `{ext}`: .png for sprites, .particle for effects

### 3. Procedural Asset Selection System

Create a Lua function that selects assets based on spellform, delivery type, spellshapes, and strength levels:

```lua
-- Procedural Spellstone Asset Selector
local SpellstoneAssetSelector = {}

-- Select sprite asset based on spellstone properties
function SpellstoneAssetSelector.selectSprite(spellstoneData)
    local spellformId = spellstoneData.spellformId or "fireBolt"
    local deliveryType = spellstoneData.deliveryType or "projectile"
    local spellshapes = spellstoneData.spellshapes or {}
    
    -- Determine variant based on spellform properties or random selection
    local variant = SpellstoneAssetSelector.selectVariant(spellstoneData)
    
    -- Build base spellform asset path
    local spellformPath = string.format(
        "/items/spellstones/spellforms/%s/%s/%s_%s_%02d.png",
        deliveryType,
        spellformId,
        spellformId,
        deliveryType,
        variant
    )
    
    -- Verify spellform asset exists, fallback to default if not
    if not SpellstoneAssetSelector.assetExists(spellformPath) then
        spellformPath = SpellstoneAssetSelector.getFallbackSpellform(spellformId, deliveryType)
    end
    
    -- Build spellshape overlay paths
    local overlayPaths = {}
    for _, spellshape in ipairs(spellshapes) do
        local overlayPath = SpellstoneAssetSelector.selectSpellshapeOverlay(
            spellshape.id,
            spellshape.strength or "moderate"
        )
        if overlayPath then
            table.insert(overlayPaths, overlayPath)
        end
    end
    
    return {
        base = spellformPath,
        overlays = overlayPaths,
        deliveryEffect = SpellstoneAssetSelector.selectDeliveryEffect(deliveryType)
    }
end

-- Select spellshape overlay based on type and strength level
function SpellstoneAssetSelector.selectSpellshapeOverlay(spellshapeId, strengthLevel)
    local variant = math.random(1, 3)  -- Random variant for variety
    
    local overlayPath = string.format(
        "/items/spellstones/spellshapes/%s/%s/%s_%s_%02d.png",
        spellshapeId,
        strengthLevel,
        spellshapeId,
        strengthLevel,
        variant
    )
    
    -- Verify overlay exists, fallback to moderate strength if not
    if not SpellstoneAssetSelector.assetExists(overlayPath) then
        overlayPath = string.format(
            "/items/spellstones/spellshapes/%s/moderate/%s_moderate_%02d.png",
            spellshapeId,
            spellshapeId,
            variant
        )
        
        -- Final fallback: no overlay
        if not SpellstoneAssetSelector.assetExists(overlayPath) then
            return nil
        end
    end
    
    return overlayPath
end

-- Select delivery type visual effect
function SpellstoneAssetSelector.selectDeliveryEffect(deliveryType)
    local effectMap = {
        projectile = "/fx/particles/spellstone_projectile_trail.particle",
        beam = "/fx/particles/spellstone_beam_glow.particle",
        area = "/fx/particles/spellstone_area_ring.particle",
        self = "/fx/particles/spellstone_self_aura.particle",
        channel = "/fx/particles/spellstone_channel_stream.particle"
    }
    
    return effectMap[deliveryType] or effectMap.projectile
end

-- Select overlay effect based on element
function SpellstoneAssetSelector.selectOverlay(element)
    local overlayMap = {
        fire = "/fx/particles/spellstone_fire_glow.particle",
        ice = "/fx/particles/spellstone_ice_crystal.particle",
        lightning = "/fx/particles/spellstone_lightning_arc.particle",
        nature = "/fx/particles/spellstone_nature_vine.particle",
        arcane = "/fx/particles/spellstone_arcane_swirl.particle",
        void = "/fx/particles/spellstone_void_smoke.particle",
        cosmic = "/fx/particles/spellstone_cosmic_star.particle",
        temporal = "/fx/particles/spellstone_temporal_gear.particle"
    }
    
    return overlayMap[element] or nil
end

-- Select variant number (for visual variety)
function SpellstoneAssetSelector.selectVariant(spellstoneData)
    -- Option 1: Based on power level
    if spellstoneData.powerLevel then
        return math.min(spellstoneData.powerLevel, 3)  -- Max 3 variants
    end
    
    -- Option 2: Random selection
    return math.random(1, 3)
    
    -- Option 3: Based on item seed (for consistent procedural generation)
    if spellstoneData.seed then
        return (spellstoneData.seed % 3) + 1
    end
    
    return 1  -- Default to variant 1
end

-- Get fallback asset if primary doesn't exist
function SpellstoneAssetSelector.getFallbackAsset(element, rarity)
    -- Fallback hierarchy: element -> base -> common
    local fallbacks = {
        element = string.format("/items/spellstones/elemental/%s/spellstone_%s_common_01.png", element, element),
        base = string.format("/items/spellstones/base/spellstone_base_%s_01.png", rarity:lower()),
        default = "/items/spellstones/base/spellstone_base_common_01.png"
    }
    
    for _, path in pairs(fallbacks) do
        if SpellstoneAssetSelector.assetExists(path) then
            return path
        end
    end
    
    return fallbacks.default
end

-- Check if asset exists
function SpellstoneAssetSelector.assetExists(path)
    -- Use Starbound asset system to check
    return root.assetExists(path)
end

return SpellstoneAssetSelector
```

### 4. Integration with Item Generation

When generating procedural spellstone items, use the asset selector:

```lua
-- Generate procedural spellstone item
function generateProceduralSpellstone(properties)
    local spellstoneData = {
        element = properties.element or "base",
        rarity = properties.rarity or "common",
        powerLevel = properties.powerLevel or 1,
        seed = properties.seed or math.random(1, 1000000)
    }
    
    -- Select assets procedurally
    local spritePath = SpellstoneAssetSelector.selectSprite(spellstoneData)
    local overlayPath = SpellstoneAssetSelector.selectOverlay(spellstoneData.element)
    
    -- Create item definition
    local itemDef = {
        itemName = string.format("spellstone_%s_%s", spellstoneData.element, spellstoneData.rarity),
        inventoryIcon = spritePath,
        description = generateSpellstoneDescription(spellstoneData),
        rarity = spellstoneData.rarity,
        properties = {
            elementalAffinity = spellstoneData.element,
            powerLevel = spellstoneData.powerLevel
        },
        -- Store asset paths for runtime use
        assets = {
            sprite = spritePath,
            overlay = overlayPath
        }
    }
    
    return itemDef
end
```

### 5. Runtime Asset Assignment

For items that are generated at runtime (not pre-defined), assign assets dynamically:

```lua
-- Apply assets to procedurally generated item
function applySpellstoneAssets(item, spellstoneData)
    -- Get asset paths
    local spritePath = SpellstoneAssetSelector.selectSprite(spellstoneData)
    local overlayPath = SpellstoneAssetSelector.selectOverlay(spellstoneData.element)
    
    -- Set inventory icon
    item.inventoryIcon = spritePath
    
    -- Apply overlay effect if available
    if overlayPath then
        item.overlayEffect = overlayPath
    end
    
    -- Store asset metadata for later reference
    item.assetMetadata = {
        sprite = spritePath,
        overlay = overlayPath,
        element = spellstoneData.element,
        rarity = spellstoneData.rarity,
        variant = SpellstoneAssetSelector.selectVariant(spellstoneData)
    }
    
    return item
end
```

### 6. Asset Generation Script

Create a script to generate all spellstone asset variants:

```powershell
# GenerateSpellstoneAssets.ps1
# Generates all spellstone asset variants for procedural use

param(
    [string]$Element = "all",  # fire, ice, lightning, etc. or "all"
    [string]$Rarity = "all",   # common, rare, epic, legendary or "all"
    [int]$Variants = 3         # Number of variants per element/rarity combo
)

$elements = if ($Element -eq "all") {
    @("base", "fire", "ice", "lightning", "nature", "arcane", "void", "cosmic", "temporal")
} else {
    @($Element)
}

$rarities = if ($Rarity -eq "all") {
    @("common", "rare", "epic", "legendary")
} else {
    @($Rarity)
}

foreach ($element in $elements) {
    foreach ($rarity in $rarities) {
        for ($variant = 1; $variant -le $Variants; $variant++) {
            $assetName = "spellstone_${element}_${rarity}_$(($variant).ToString('00'))"
            $description = "A $rarity $element spellstone crystal with magical properties"
            
            Write-Host "Generating: $assetName" -ForegroundColor Cyan
            
            # Generate sprite using asset generator
            & ".\StarboundOllamaAssetGenerator.ps1" `
                -AssetType "ItemSprite" `
                -AssetName $assetName `
                -Description $description `
                -OutputDir "assets/spellstones/$element"
        }
    }
}
```

### 7. Asset Registry System

Register all spellstone assets for easy lookup:

```lua
-- Spellstone Asset Registry
local SpellstoneAssetRegistry = {
    -- Organized by element -> rarity -> variants
    assets = {},
    
    -- Initialize registry
    function initialize()
        -- Load all spellstone assets from directory structure
        local basePath = "/items/spellstones"
        
        -- Register base cores
        for rarity in {"common", "rare", "epic", "legendary"} do
            for variant = 1, 3 do
                local path = string.format("%s/base/spellstone_base_%s_%02d.png", basePath, rarity, variant)
                if root.assetExists(path) then
                    SpellstoneAssetRegistry.register("base", rarity, variant, path)
                end
            end
        end
        
        -- Register elemental variants
        local elements = {"fire", "ice", "lightning", "nature", "arcane", "void", "cosmic", "temporal"}
        for _, element in ipairs(elements) do
            for rarity in {"common", "rare", "epic", "legendary"} do
                for variant = 1, 3 do
                    local path = string.format("%s/elemental/%s/spellstone_%s_%s_%02d.png", 
                        basePath, element, element, rarity, variant)
                    if root.assetExists(path) then
                        SpellstoneAssetRegistry.register(element, rarity, variant, path)
                    end
                end
            end
        end
    end,
    
    -- Register an asset
    function register(element, rarity, variant, path)
        if not SpellstoneAssetRegistry.assets[element] then
            SpellstoneAssetRegistry.assets[element] = {}
        end
        if not SpellstoneAssetRegistry.assets[element][rarity] then
            SpellstoneAssetRegistry.assets[element][rarity] = {}
        end
        SpellstoneAssetRegistry.assets[element][rarity][variant] = path
    end,
    
    -- Get asset by properties
    function get(element, rarity, variant)
        variant = variant or 1
        if SpellstoneAssetRegistry.assets[element] and
           SpellstoneAssetRegistry.assets[element][rarity] and
           SpellstoneAssetRegistry.assets[element][rarity][variant] then
            return SpellstoneAssetRegistry.assets[element][rarity][variant]
        end
        return nil
    end,
    
    -- Get random variant
    function getRandom(element, rarity)
        if not SpellstoneAssetRegistry.assets[element] or
           not SpellstoneAssetRegistry.assets[element][rarity] then
            return nil
        end
        
        local variants = SpellstoneAssetRegistry.assets[element][rarity]
        local variantKeys = {}
        for k, _ in pairs(variants) do
            table.insert(variantKeys, k)
        end
        
        if #variantKeys > 0 then
            local randomVariant = variantKeys[math.random(#variantKeys)]
            return variants[randomVariant]
        end
        
        return nil
    end
}

return SpellstoneAssetRegistry
```

### 8. Usage Examples

#### Example 1: Generate Procedural Spellstone Item

```lua
-- Generate a fire bolt spellstone with amplify modifier
local spellstone = generateProceduralSpellstone({
    spellformId = "fireBolt",
    deliveryType = "projectile",
    spellshapes = {
        {id = "amplify", strength = "moderate"}
    },
    seed = 12345  -- For consistent generation
})

-- Assets are automatically selected based on spellform + spellshape
print("Base sprite: " .. spellstone.assets.base)
print("Overlays: " .. table.concat(spellstone.assets.overlays, ", "))
print("Delivery effect: " .. spellstone.assets.deliveryEffect)
```

#### Example 2: Select Asset for Existing Spellstone Item

```lua
-- Get spellstone data from existing item
local item = player.getItem("spellstone_fireBolt_amplify_01")
local spellstoneData = {
    spellformId = item.properties.spellformId,
    deliveryType = item.properties.deliveryType,
    spellshapes = item.properties.spellshapes  -- Array of {id, strength}
}

-- Select appropriate assets
local assets = SpellstoneAssetSelector.selectSprite(spellstoneData)
item.inventoryIcon = assets.base
item.overlayEffects = assets.overlays
item.deliveryEffect = assets.deliveryEffect
```

#### Example 3: Complex Spellstone with Multiple Spellshapes

```lua
-- Generate ice shard with pierce and split modifiers
local spellstone = generateProceduralSpellstone({
    spellformId = "iceShard",
    deliveryType = "projectile",
    spellshapes = {
        {id = "pierce", strength = "strong"},
        {id = "split", strength = "moderate"}
    }
})

-- Multiple overlays will be combined
print("Base: " .. spellstone.assets.base)
print("Overlay 1 (pierce): " .. spellstone.assets.overlays[1])
print("Overlay 2 (split): " .. spellstone.assets.overlays[2])
```

#### Example 4: Batch Generate Spellstone Assets

```powershell
# Generate all fireBolt projectile spellform variants
.\GenerateSpellstoneAssets.ps1 -AssetType spellform -SpellformId fireBolt -DeliveryType projectile -Variants 3

# Generate all amplify spellshape variants for all strength levels
.\GenerateSpellstoneAssets.ps1 -AssetType spellshape -SpellshapeId amplify -StrengthLevel all -Variants 2

# Generate complete spellstone asset set
.\GenerateSpellstoneAssets.ps1 -AssetType all
```

## Best Practices

1. **Consistent Naming**: Always use the structured naming convention for easy asset lookup
2. **Fallback Assets**: Always provide fallback assets for missing variants
3. **Asset Variants**: Generate 2-3 variants per element/rarity combo for visual variety
4. **Layered Composition**: Use base sprite + overlay effects for richer visuals
5. **Registry System**: Maintain an asset registry for fast lookups
6. **Procedural Selection**: Use item properties (element, rarity, power) to select assets
7. **Seed-Based Selection**: Use seeds for consistent procedural generation

## Asset Generation Workflow

1. **Generate Base Assets**: Create base spellstone sprites for each rarity
2. **Generate Elemental Variants**: Create elemental variants for each element/rarity combo
3. **Generate Overlays**: Create particle effects for each element
4. **Register Assets**: Register all assets in the asset registry
5. **Test Selection**: Test asset selection with various property combinations
6. **Generate Items**: Use procedural generation to create spellstone items with selected assets

## Spellstone System Overview

### How Spellstones Work

A **spellstone** is a procedural item that contains:

1. **Spellform** - The base spell (e.g., `fireBolt`, `iceShard`, `lightningBolt`)
   - Has a **delivery type** (projectile, beam, area, self, channel)
   - Has base stats (damage, range, speed, mana cost, cooldown)
   - Has an element (fire, ice, lightning, nature, arcane, void, cosmic, temporal)

2. **Spellshapes** - Modifiers that alter the spellform (can have multiple)
   - Examples: `amplify`, `pierce`, `split`, `homing`, `explode`, `chain`
   - Each spellshape has a **strength level**: weak, moderate, strong, extreme
   - Strength level affects the intensity of the modifier's effect
   - Multiple spellshapes can be combined (up to maxStacks)

### Example Spellstone Combinations

**Example 1: Fire Bolt with Amplify**
- Spellform: `fireBolt` (projectile delivery)
- Spellshape: `amplify` (moderate strength)
- Result: A fire projectile with increased damage

**Example 2: Ice Shard with Pierce and Split**
- Spellform: `iceShard` (projectile delivery)
- Spellshapes: `pierce` (strong), `split` (moderate)
- Result: An ice projectile that pierces enemies and splits on impact

**Example 3: Lightning Beam with Chain (Extreme)**
- Spellform: `lightningBeam` (beam delivery)
- Spellshape: `chain` (extreme strength)
- Result: A lightning beam that chains to many enemies with maximum effect

### Asset Selection Logic

When generating a procedural spellstone:

1. **Select base spellform sprite** based on spellform ID and delivery type
2. **Select spellshape overlay sprites** for each spellshape modifier
3. **Select delivery effect particles** based on delivery type
4. **Combine assets** using layered composition:
   - Base spellform sprite (bottom layer)
   - Spellshape overlay sprites (middle layers, one per spellshape)
   - Delivery effect particles (top layer)

## Shared Settings Configuration

All asset generation tools use a shared settings file: `AssetGenerationSettings.ps1`

This file contains:
- **ImageMagick Path**: `E:\tools\ImageMagick` (configured location)
- **Output Directories**: Default paths for generated assets
- **Ollama Configuration**: API URL and model settings
- **Default Values**: Variants, animation frames, etc.

To update settings, edit `AssetGenerationSettings.ps1`. All scripts will automatically use the updated configuration.

### Testing Settings

Run the test script to verify configuration:
```powershell
.\Test-AssetGenerationSettings.ps1
```

## Summary

For procedural spellstone items:
- **Organize assets hierarchically** by spellform, delivery type, and spellshape
- **Use structured naming** that encodes spellform, delivery type, spellshape, and strength
- **Create multiple variants** for visual variety
- **Select assets dynamically** based on spellform + spellshape combinations
- **Support strength levels** for spellshape modifiers (weak, moderate, strong, extreme)
- **Maintain asset registry** for fast lookups
- **Provide fallbacks** for missing assets
- **Use layered composition** (base sprite + spellshape overlays + delivery effects) for richer visuals

This system allows you to generate unlimited procedural spellstone items (spellform + spellshape combinations) while using a finite set of pre-generated assets.
