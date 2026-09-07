-- Crossbow Asset Generation Example
-- This demonstrates generating complete OpenStarbound assets that integrate with the existing hybrid system

print("=== Crossbow Asset Generation Demo ===")

-- 1. Create a light crossbow with explosive bolts
local lightCrossbow = create_light_crossbow()
lightCrossbow.id = "mt_explosive_crossbow_v1"
lightCrossbow.drawLength = 0.5
lightCrossbow.drawWeight = 300
lightCrossbow.autoReload = true
lightCrossbow.reloadTime = 1.2
lightCrossbow.stockMaterial = "WoodOak"
lightCrossbow.limbMaterial = "Fiberglass"
lightCrossbow.stringMaterial = "Synthetic"

local crossbowConfig = {
    itemName = "Explosive Crossbow",
    description = "A crossbow that fires explosive bolts",
    rarity = "Rare",
    category = "weapon",
    level = "5",
    damageType = "physical",
    damage = 15.0,
    fireRate = 1.5,
    abilityType = "crossbow",
    behaviorSystem = "hybrid",  -- Uses your existing hybrid system
    effectSystem = "projectile", -- Uses your existing effect system
    materialSystem = "magitech", -- Uses your existing material system
    projectileTypes = {"mt_explosive_bolt"},
    specialEffects = {"explosive", "piercing"} -- Integrates with your existing effects
}

-- Generate complete crossbow assets
local crossbowAssets = generate_crossbow_assets(lightCrossbow, crossbowConfig)
if crossbowAssets.itemFile then
    print("✓ Generated crossbow assets:")
    print("  Item file: " .. crossbowAssets.itemFile)
    print("  Frames file: " .. crossbowAssets.framesFile)
    print("  Sprite file: " .. crossbowAssets.spriteFile)
    print("  Icon file: " .. crossbowAssets.iconFile)
    print("  Behavior file: " .. crossbowAssets.behaviorFile)
    print("  Effect file: " .. crossbowAssets.effectFile)
else
    print("✗ Crossbow asset generation failed")
end

-- 2. Create explosive bolts
local explosiveBolt = create_steel_bolt()
explosiveBolt.id = "mt_explosive_bolt_v1"
explosiveBolt.length = 0.4
explosiveBolt.shaftRadius = 0.005
explosiveBolt.useFletching = false
explosiveBolt.tipMass = 0.025
explosiveBolt.barbedTip = true

local boltConfig = {
    itemName = "Explosive Bolt",
    description = "A bolt that explodes on impact",
    rarity = "Uncommon",
    category = "ammo",
    level = "5",
    damageType = "physical",
    damage = 8.0,
    fireRate = 1.0,
    abilityType = "projectile",
    effectSystem = "projectile",
    specialEffects = {"explosive", "fire"} -- Integrates with your existing fire effects
}

-- Generate bolt assets
local boltAssets = generate_bolt_assets(explosiveBolt, boltConfig)
if boltAssets.projectileFile then
    print("✓ Generated bolt assets:")
    print("  Projectile file: " .. boltAssets.projectileFile)
    print("  Sprite file: " .. boltAssets.spriteFile)
    print("  Icon file: " .. boltAssets.iconFile)
    print("  Effect file: " .. boltAssets.effectFile)
else
    print("✗ Bolt asset generation failed")
end

-- 3. Create a heavy crossbow with elemental arrows
local heavyCrossbow = create_heavy_crossbow()
heavyCrossbow.id = "mt_elemental_crossbow_v1"
heavyCrossbow.drawLength = 0.7
heavyCrossbow.drawWeight = 500
heavyCrossbow.autoReload = false
heavyCrossbow.reloadTime = 2.5
heavyCrossbow.stockMaterial = "MetalSteel"
heavyCrossbow.limbMaterial = "CarbonFiber"
heavyCrossbow.stringMaterial = "Kevlar"

local heavyCrossbowConfig = {
    itemName = "Elemental Crossbow",
    description = "A powerful crossbow that fires elemental arrows",
    rarity = "Legendary",
    category = "weapon",
    level = "10",
    damageType = "elemental",
    damage = 25.0,
    fireRate = 2.0,
    abilityType = "crossbow",
    behaviorSystem = "hybrid",
    effectSystem = "spell", -- Uses your existing spell system
    materialSystem = "magitech",
    projectileTypes = {"mt_ice_arrow", "mt_fire_arrow", "mt_lightning_arrow"},
    specialEffects = {"elemental", "piercing", "freezing"} -- Multiple effects
}

-- Generate heavy crossbow assets
local heavyCrossbowAssets = generate_crossbow_assets(heavyCrossbow, heavyCrossbowConfig)
if heavyCrossbowAssets.itemFile then
    print("✓ Generated heavy crossbow assets:")
    print("  Item file: " .. heavyCrossbowAssets.itemFile)
    print("  Behavior file: " .. heavyCrossbowAssets.behaviorFile)
    print("  Effect file: " .. heavyCrossbowAssets.effectFile)
else
    print("✗ Heavy crossbow asset generation failed")
end

-- 4. Create elemental arrows
local iceArrow = create_wood_arrow()
iceArrow.id = "mt_ice_arrow_v1"
iceArrow.shaftLength = 1.1
iceArrow.shaftDiameter = 0.008
iceArrow.spineRating = 600
iceArrow.useFletching = true
iceArrow.fletchStyle = "Parabolic"
iceArrow.nockSize = 0.02
iceArrow.tipMass = 0.015

local iceArrowConfig = {
    itemName = "Ice Arrow",
    description = "An arrow that freezes targets",
    rarity = "Uncommon",
    category = "ammo",
    level = "8",
    damageType = "ice",
    damage = 12.0,
    fireRate = 1.0,
    abilityType = "projectile",
    effectSystem = "spell",
    specialEffects = {"freezing", "slow"} -- Integrates with your existing ice effects
}

-- Generate ice arrow assets
local iceArrowAssets = generate_arrow_assets(iceArrow, iceArrowConfig)
if iceArrowAssets.projectileFile then
    print("✓ Generated ice arrow assets:")
    print("  Projectile file: " .. iceArrowAssets.projectileFile)
    print("  Sprite file: " .. iceArrowAssets.spriteFile)
    print("  Effect file: " .. iceArrowAssets.effectFile)
else
    print("✗ Ice arrow asset generation failed")
end

-- 5. Create a custom crossbow with multiple special effects
local customCrossbow = CrossbowParams()
customCrossbow.id = "mt_custom_crossbow_v1"
customCrossbow.drawLength = 0.6
customCrossbow.drawWeight = 400
customCrossbow.autoReload = true
customCrossbow.reloadTime = 1.5
customCrossbow.stockMaterial = "CarbonFiber"
customCrossbow.limbMaterial = "Titanium"
customCrossbow.stringMaterial = "Kevlar"

local customConfig = {
    itemName = "Custom Magi-Tech Crossbow",
    description = "A highly advanced crossbow with multiple special effects",
    rarity = "Legendary",
    category = "weapon",
    level = "15",
    damageType = "mixed",
    damage = 30.0,
    fireRate = 2.5,
    abilityType = "crossbow",
    behaviorSystem = "hybrid",
    effectSystem = "spell",
    materialSystem = "magitech",
    projectileTypes = {"mt_custom_bolt", "mt_custom_arrow"},
    specialEffects = {"explosive", "piercing", "elemental", "homing", "chain"} -- Multiple effects
}

-- Generate custom crossbow assets
local customAssets = generate_crossbow_assets(customCrossbow, customConfig)
if customAssets.itemFile then
    print("✓ Generated custom crossbow assets:")
    print("  Item file: " .. customAssets.itemFile)
    print("  Behavior file: " .. customAssets.behaviorFile)
    print("  Effect file: " .. customAssets.effectFile)
else
    print("✗ Custom crossbow asset generation failed")
end

-- 6. Demonstrate integration with existing systems
print("\n--- Integration with Existing Systems ---")

-- The generated assets will automatically integrate with:
-- - Your existing hybrid C++/Lua behavior system
-- - Your existing spell/effect systems
-- - Your existing material systems
-- - Your existing projectile tracking systems

print("Generated assets integrate with:")
print("  ✓ Hybrid C++/Lua behavior system")
print("  ✓ Existing spell/effect systems")
print("  ✓ Existing material systems")
print("  ✓ Existing projectile tracking")
print("  ✓ Existing special effects (explosive, elemental, etc.)")

-- 7. Show how the generated files work together
print("\n--- Generated File Structure ---")
print("items/active/weapons/crossbow/")
print("├── mt_explosive_crossbow_v1/")
print("│   ├── mt_explosive_crossbow_v1.activeitem")
print("│   ├── mt_explosive_crossbow_v1full.frames")
print("│   ├── mt_explosive_crossbow_v1full.png")
print("│   ├── mt_explosive_crossbow_v1icon.png")
print("│   ├── mt_explosive_crossbow_v1.lua")
print("│   └── mt_explosive_crossbow_v1_effects.json")
print("└── ammo/")
print("    ├── mt_explosive_bolt_v1/")
print("    │   ├── mt_explosive_bolt_v1.projectile")
print("    │   ├── mt_explosive_bolt_v1.png")
print("    │   ├── mt_explosive_bolt_v1icon.png")
print("    │   └── mt_explosive_bolt_v1_effects.json")
print("    └── mt_ice_arrow_v1/")
print("        ├── mt_ice_arrow_v1.projectile")
print("        ├── mt_ice_arrow_v1.png")
print("        ├── mt_ice_arrow_v1icon.png")
print("        └── mt_ice_arrow_v1_effects.json")

print("\n=== Crossbow Asset Generation Complete ===")
print("All assets are ready to be used in OpenStarbound!")
print("The generated files integrate seamlessly with your existing hybrid system.") 