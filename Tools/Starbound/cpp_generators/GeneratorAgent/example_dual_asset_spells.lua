-- Dual Asset Spell System Example
-- Demonstrates unified PNG-based and mesh-based spell projectiles

local DualAssetSpell = require("DualAssetSpell")
local DualAssetSpellUtils = require("DualAssetSpellUtils")
local DualAssetSpellPresets = require("DualAssetSpellPresets")

-- Initialize the dual asset spell system
DualAssetSpell.initialize()

-- Enable performance monitoring
DualAssetSpell.enablePerformanceMonitoring(true)
DualAssetSpell.setPerformanceThresholds(16.0, 16.0) -- 16ms thresholds

print("=== Dual Asset Spell System Example ===")

-- Example 1: Basic sprite-based spell
print("\n--- Example 1: Sprite-based Fireball ---")
local spriteFireball = DualAssetSpellPresets.spriteFireball()
if DualAssetSpellUtils.validateSpellDef(spriteFireball) then
    local spellId = DualAssetSpell.cast(spriteFireball, {
        x = 0, y = 0, z = 0,
        dx = 1, dy = 0, dz = 0
    })
    print("Spawned sprite fireball with ID:", spellId)
else
    print("Invalid sprite fireball definition")
end

-- Example 2: Mesh-based spell with custom shader
print("\n--- Example 2: Mesh-based Lightning Bolt ---")
local meshLightning = DualAssetSpellPresets.meshLightningBolt()
if DualAssetSpellUtils.validateSpellDef(meshLightning) then
    local spellId = DualAssetSpell.cast(meshLightning, {
        x = 5, y = 2, z = 0,
        dx = -1, dy = 0.5, dz = 0
    })
    print("Spawned mesh lightning bolt with ID:", spellId)
else
    print("Invalid mesh lightning definition")
end

-- Example 3: Auto-generated mesh from sprite
print("\n--- Example 3: Auto-generated Mesh from Sprite ---")
local autoFireball = DualAssetSpellPresets.autoFireball()
if DualAssetSpellUtils.validateSpellDef(autoFireball) then
    local spellId = DualAssetSpell.cast(autoFireball, {
        x = -5, y = 1, z = 0,
        dx = 1, dy = 0.2, dz = 0
    })
    print("Spawned auto-generated mesh fireball with ID:", spellId)
else
    print("Invalid auto fireball definition")
end

-- Example 4: Custom spell definition
print("\n--- Example 4: Custom Spell Definition ---")
local customSpell = DualAssetSpellUtils.createSpellDef({
    id = "custom_arcane_bolt",
    type = "projectile",
    assetType = "mesh",
    meshPath = "meshes/custom_bolt.obj",
    textureAtlasPath = "textures/custom_atlas.png",
    useBakedTextures = true,
    bakePalette = "starbound_arcane",
    useShapeDeformation = true,
    shapeProfile = "spiral",
    speed = 18.0,
    lifetime = 4.5,
    damage = 35.0,
    useGPUAcceleration = true
})

if DualAssetSpellUtils.validateSpellDef(customSpell) then
    local spellId = DualAssetSpell.cast(customSpell, {
        x = 0, y = 3, z = 0,
        dx = 0.8, dy = -0.3, dz = 0
    })
    print("Spawned custom arcane bolt with ID:", spellId)
else
    print("Invalid custom spell definition")
end

-- Example 5: Batch spawning
print("\n--- Example 5: Batch Spell Spawning ---")
local spellDefs = {
    DualAssetSpellPresets.spriteFireball(),
    DualAssetSpellPresets.meshLightningBolt(),
    DualAssetSpellPresets.autoFireball()
}

local positions = {
    {x = -10, y = 0, z = 0},
    {x = 0, y = 2, z = 0},
    {x = 10, y = 1, z = 0}
}

local directions = {
    {dx = 1, dy = 0, dz = 0},
    {dx = 0, dy = -1, dz = 0},
    {dx = -1, dy = 0.5, dz = 0}
}

local spellIds = DualAssetSpell.castBatch(spellDefs, positions, directions)
print("Spawned batch of spells:", #spellIds, "spells")

-- Example 6: Async asset loading
print("\n--- Example 6: Async Asset Loading ---")
local asyncSpell = DualAssetSpellPresets.meshArcaneBlast()
local asset = DualAssetSpell.loadAssetAsync(asyncSpell)
if asset then
    print("Asset loaded synchronously")
else
    print("Asset loading started asynchronously")
end

-- Example 7: Shape deformation
print("\n--- Example 7: Shape Deformation ---")
local deformedSpell = DualAssetSpellPresets.meshLightningBolt()
deformedSpell.useShapeDeformation = true
deformedSpell.shapeProfile = "zigzag"

local spellId = DualAssetSpell.cast(deformedSpell, {
    x = 0, y = 0, z = 0,
    dx = 1, dy = 0, dz = 0
})

-- Add custom shape component
local shape = {
    kind = "Zigzag",
    amplitude = 0.3,
    frequency = 8.0,
    speed = 2.0,
    useGPU = true
}

DualAssetSpell.addShapeComponent(spellId, shape)
print("Added shape deformation to spell:", spellId)

-- Example 8: Asset generation pipeline
print("\n--- Example 8: Asset Generation Pipeline ---")

-- Generate mesh from sprite
local spritePath = "sprites/custom_projectile.png"
local meshDef = DualAssetSpellUtils.createSpellDef({
    id = "generated_mesh_spell",
    assetType = "mesh",
    useMeshExtrusion = true,
    meshThickness = 0.2,
    useBakedTextures = true,
    bakePalette = "starbound_default"
})

if DualAssetSpell.generateMeshFromSprite(meshDef, spritePath) then
    print("Successfully generated mesh from sprite")
    
    -- Bake texture for the generated mesh
    if DualAssetSpell.bakeTextureForMesh(meshDef, "generated_mesh.obj") then
        print("Successfully baked texture for mesh")
    end
end

-- Example 9: Query and management
print("\n--- Example 9: Query and Management ---")

-- Get all spells in a radius
local center = {x = 0, y = 0, z = 0}
local radius = 10.0
local spellsInRadius = DualAssetSpell.getSpellsInRadius(center, radius)
print("Spells in radius:", #spellsInRadius)

-- Get spells by type
local projectileSpells = DualAssetSpell.getSpellsByType("projectile")
print("Projectile spells:", #projectileSpells)

-- Get spells by asset type
local spriteSpells = DualAssetSpell.getSpellsByAssetType("Sprite")
local meshSpells = DualAssetSpell.getSpellsByAssetType("Mesh")
print("Sprite spells:", #spriteSpells, "Mesh spells:", #meshSpells)

-- Example 10: Performance monitoring
print("\n--- Example 10: Performance Monitoring ---")

-- Get system statistics
local stats = DualAssetSpell.getStats()
print("System Statistics:")
print("  Total spells:", stats.totalSpells)
print("  Sprite spells:", stats.spriteSpells)
print("  Mesh spells:", stats.meshSpells)
print("  Auto spells:", stats.autoSpells)
print("  Loaded assets:", stats.loadedAssets)
print("  Cached assets:", stats.cachedAssets)
print("  Active shape components:", stats.activeShapeComponents)
print("  Total spawned:", stats.totalSpawned)
print("  Total destroyed:", stats.totalDestroyed)

-- Example 11: Hot-reload support
print("\n--- Example 11: Hot-Reload Support ---")

-- Watch asset files for changes
DualAssetSpell.watchAssetFiles()

-- Simulate file change
DualAssetSpell.onAssetFileChanged("sprites/fireball.png")
print("Asset file change detected and handled")

-- Example 12: Asset type conversion utilities
print("\n--- Example 12: Asset Type Utilities ---")

local assetType = DualAssetSpellUtils.stringToAssetType("mesh")
local assetTypeStr = DualAssetSpellUtils.assetTypeToString(assetType)
print("Asset type conversion:", "mesh" .. " -> " .. assetTypeStr)

-- Example 13: Advanced spell with all features
print("\n--- Example 13: Advanced Spell with All Features ---")

local advancedSpell = DualAssetSpellUtils.createSpellDef({
    id = "advanced_dual_spell",
    type = "projectile",
    assetType = "auto",
    spritePath = "sprites/advanced_projectile.png",
    useMeshExtrusion = true,
    meshThickness = 0.25,
    useBakedTextures = true,
    bakePalette = "starbound_advanced",
    useCustomShader = true,
    customShaderPath = "shaders/advanced_spell.glsl",
    useShapeDeformation = true,
    shapeProfile = "vortex",
    useCollisionSync = true,
    useGPUAcceleration = true,
    useAsyncGeneration = true,
    useHotReload = true,
    speed = 25.0,
    lifetime = 6.0,
    damage = 50.0,
    radius = 2.0
})

if DualAssetSpellUtils.validateSpellDef(advancedSpell) then
    local spellId = DualAssetSpell.cast(advancedSpell, {
        x = 0, y = 5, z = 0,
        dx = 0.7, dy = -0.7, dz = 0
    })
    print("Spawned advanced dual asset spell with ID:", spellId)
else
    print("Invalid advanced spell definition")
end

-- Example 14: Runtime spell management
print("\n--- Example 14: Runtime Spell Management ---")

-- Get all active spells
local allSpells = DualAssetSpell.getAllSpells()
print("Total active spells:", #allSpells)

-- Update all shape deformations
DualAssetSpell.updateAllShapeDeformations(0.016) -- 16ms delta time

-- Example 15: Asset management
print("\n--- Example 15: Asset Management ---")

-- Check if specific assets are loaded
local assetKey = "sprite_fireball_Sprite_sprites/fireball.png"
if DualAssetSpell.isAssetLoaded(assetKey) then
    print("Asset is loaded:", assetKey)
    local asset = DualAssetSpell.getAsset(assetKey)
    if asset then
        print("Asset type:", DualAssetSpellUtils.assetTypeToString(asset.assetType))
        print("Sprite loaded:", asset.isSpriteLoaded)
        print("Mesh loaded:", asset.isMeshLoaded)
    end
else
    print("Asset not loaded:", assetKey)
end

-- Example 16: Error handling and validation
print("\n--- Example 16: Error Handling and Validation ---")

-- Try to create invalid spell definition
local invalidSpell = DualAssetSpellUtils.createSpellDef({
    id = "invalid_spell",
    assetType = "mesh",
    -- Missing required meshPath for mesh asset type
})

if not DualAssetSpellUtils.validateSpellDef(invalidSpell) then
    print("Correctly detected invalid spell definition")
end

-- Example 17: Integration with existing systems
print("\n--- Example 17: Integration with Existing Systems ---")

-- This would integrate with your existing spell systems
-- For example, converting between different spell types
local convertToDualAsset = function(existingSpellDef)
    local dualDef = DualAssetSpellUtils.createSpellDef({
        id = existingSpellDef.id .. "_dual",
        type = existingSpellDef.type,
        assetType = "auto",
        spritePath = existingSpellDef.spritePath or "",
        meshPath = existingSpellDef.meshPath or "",
        speed = existingSpellDef.speed,
        lifetime = existingSpellDef.lifetime,
        damage = existingSpellDef.damage
    })
    return dualDef
end

print("Integration utilities available")

-- Example 18: Performance optimization
print("\n--- Example 18: Performance Optimization ---")

-- Set performance thresholds
DualAssetSpell.setPerformanceThresholds(8.0, 8.0) -- Stricter thresholds

-- Monitor performance during intensive operations
for i = 1, 10 do
    local spell = DualAssetSpellPresets.spriteFireball()
    spell.id = "performance_test_" .. i
    DualAssetSpell.cast(spell, {
        x = math.random(-10, 10),
        y = math.random(-5, 5),
        z = 0,
        dx = math.random(-1, 1),
        dy = math.random(-1, 1),
        dz = 0
    })
end

print("Performance test completed")

-- Example 19: Cleanup and shutdown
print("\n--- Example 19: Cleanup and Shutdown ---")

-- Destroy all spells
DualAssetSpell.destroyAllSpells()
print("All spells destroyed")

-- Unload all assets
DualAssetSpell.unloadAllAssets()
print("All assets unloaded")

-- Reset statistics
DualAssetSpell.resetStats()
print("Statistics reset")

-- Final statistics
local finalStats = DualAssetSpell.getStats()
print("Final Statistics:")
print("  Total spells:", finalStats.totalSpells)
print("  Total spawned:", finalStats.totalSpawned)
print("  Total destroyed:", finalStats.totalDestroyed)

print("\n=== Dual Asset Spell System Example Complete ===")

-- Return the system for further use
return {
    DualAssetSpell = DualAssetSpell,
    DualAssetSpellUtils = DualAssetSpellUtils,
    DualAssetSpellPresets = DualAssetSpellPresets
} 