-- Crossbow Bolts, Arrows & Crossbow Generation Pipeline Example
-- This script demonstrates the complete asset generation pipeline for crossbows and projectiles

-- Initialize the crossbow factory
print("=== Crossbow Generation Pipeline Demo ===")

-- 1. Create Crossbow Parameters
local lightCrossbow = create_light_crossbow()
lightCrossbow.id = "mt_light_crossbow_v1"
lightCrossbow.drawLength = 0.5
lightCrossbow.drawWeight = 300
lightCrossbow.autoReload = true
lightCrossbow.reloadTime = 1.2
lightCrossbow.stockMaterial = "WoodOak"
lightCrossbow.limbMaterial = "Fiberglass"
lightCrossbow.stringMaterial = "Synthetic"

local heavyCrossbow = create_heavy_crossbow()
heavyCrossbow.id = "mt_heavy_crossbow_v1"
heavyCrossbow.drawLength = 0.7
heavyCrossbow.drawWeight = 500
heavyCrossbow.autoReload = false
heavyCrossbow.reloadTime = 2.5
heavyCrossbow.stockMaterial = "MetalSteel"
heavyCrossbow.limbMaterial = "CarbonFiber"
heavyCrossbow.stringMaterial = "Kevlar"

-- 2. Create Bolt Parameters
local steelBolt = create_steel_bolt()
steelBolt.id = "mt_steel_bolt_v1"
steelBolt.length = 0.4
steelBolt.shaftRadius = 0.005
steelBolt.useFletching = false
steelBolt.tipMass = 0.02
steelBolt.barbedTip = true

local carbonBolt = BoltParams()
carbonBolt.id = "mt_carbon_bolt_v1"
carbonBolt.length = 0.35
carbonBolt.shaftRadius = 0.004
carbonBolt.useFletching = true
carbonBolt.fletchMaterial = "Plastic"
carbonBolt.fletchLength = 0.03
carbonBolt.tipMass = 0.015
carbonBolt.barbedTip = false

-- 3. Create Arrow Parameters
local woodArrow = create_wood_arrow()
woodArrow.id = "mt_wood_arrow_v1"
woodArrow.shaftLength = 1.1
woodArrow.shaftDiameter = 0.008
woodArrow.spineRating = 600
woodArrow.useFletching = true
woodArrow.fletchStyle = "Parabolic"
woodArrow.nockSize = 0.02
woodArrow.tipMass = 0.015

local carbonArrow = ArrowParams()
carbonArrow.id = "mt_carbon_arrow_v1"
carbonArrow.shaftLength = 1.0
carbonArrow.shaftDiameter = 0.006
carbonArrow.spineRating = 800
carbonArrow.useFletching = true
carbonArrow.fletchStyle = "Shield"
carbonArrow.nockSize = 0.018
carbonArrow.tipMass = 0.012

-- 4. Generate Assets Synchronously (Immediate Access)
print("\n--- Synchronous Generation ---")

local lightCrossbowBundle = generate_crossbow(lightCrossbow)
if lightCrossbowBundle.mesh ~= 0 then
    print("✓ Light crossbow generated successfully")
    print("  Mesh: " .. lightCrossbowBundle.mesh)
    print("  String: " .. lightCrossbowBundle.string)
    print("  Animation: " .. lightCrossbowBundle.reloadAnim)
    print("  Materials: " .. #lightCrossbowBundle.materials.materials)
else
    print("✗ Light crossbow generation failed")
end

local steelBoltBundle = generate_bolt(steelBolt)
if steelBoltBundle.mesh ~= 0 then
    print("✓ Steel bolt generated successfully")
    print("  Mesh: " .. steelBoltBundle.mesh)
    print("  Material: " .. steelBoltBundle.material)
    print("  VFX Trail: " .. steelBoltBundle.vfxTrail)
    print("  Flight Sim: " .. steelBoltBundle.flightSim)
    print("  Collider: " .. steelBoltBundle.collider)
else
    print("✗ Steel bolt generation failed")
end

local woodArrowBundle = generate_arrow(woodArrow)
if woodArrowBundle.mesh ~= 0 then
    print("✓ Wood arrow generated successfully")
    print("  Mesh: " .. woodArrowBundle.mesh)
    print("  Material: " .. woodArrowBundle.material)
    print("  VFX Trail: " .. woodArrowBundle.vfxTrail)
    print("  Flight Sim: " .. woodArrowBundle.flightSim)
    print("  Collider: " .. woodArrowBundle.collider)
else
    print("✗ Wood arrow generation failed")
end

-- 5. Generate Assets Asynchronously (Background Processing)
print("\n--- Asynchronous Generation ---")

-- Set up completion callbacks
function on_crossbow_ready(id, bundle)
    print("✓ Crossbow ready: " .. id)
    print("  Mesh: " .. bundle.mesh)
    print("  String: " .. bundle.string)
    print("  Animation: " .. bundle.reloadAnim)
end

function on_projectile_ready(id, bundle)
    print("✓ Projectile ready: " .. id)
    print("  Mesh: " .. bundle.mesh)
    print("  Material: " .. bundle.material)
    print("  VFX Trail: " .. bundle.vfxTrail)
    print("  Flight Sim: " .. bundle.flightSim)
    print("  Collider: " .. bundle.collider)
end

function on_crossbow_error(id, error)
    print("✗ Crossbow generation failed: " .. id .. " - " .. error)
end

function on_projectile_error(id, error)
    print("✗ Projectile generation failed: " .. id .. " - " .. error)
end

-- Start async generation
local success1 = spawn_crossbow(heavyCrossbow)
local success2 = spawn_bolt(carbonBolt)
local success3 = spawn_arrow(carbonArrow)

if success1 then print("✓ Heavy crossbow generation started") else print("✗ Heavy crossbow generation failed to start") end
if success2 then print("✓ Carbon bolt generation started") else print("✗ Carbon bolt generation failed to start") end
if success3 then print("✓ Carbon arrow generation started") else print("✗ Carbon arrow generation failed to start") end

-- 6. Monitor Progress
print("\n--- Monitoring Progress ---")

local function checkProgress()
    local pending = get_pending_count()
    print("Pending crossbows: " .. pending.crossbows)
    print("Pending projectiles: " .. pending.projectiles)
    
    if pending.crossbows == 0 and pending.projectiles == 0 then
        print("✓ All asset generation completed!")
        return true
    end
    return false
end

-- Simulate polling (in real usage, this would be called periodically)
print("Initial status:")
checkProgress()

-- 7. Advanced Usage Examples
print("\n--- Advanced Usage Examples ---")

-- Create a custom crossbow with specific parameters
local customCrossbow = CrossbowParams()
customCrossbow.id = "mt_custom_crossbow_v1"
customCrossbow.drawLength = 0.6
customCrossbow.drawWeight = 400
customCrossbow.autoReload = true
customCrossbow.reloadTime = 1.5
customCrossbow.stockMaterial = "WoodOak"
customCrossbow.limbMaterial = "Fiberglass"
customCrossbow.stringMaterial = "Synthetic"

if customCrossbow:validate() then
    local customBundle = generate_crossbow(customCrossbow)
    if customBundle.mesh ~= 0 then
        print("✓ Custom crossbow generated successfully")
    end
else
    print("✗ Custom crossbow parameters invalid")
end

-- Create a specialized bolt for heavy crossbows
local heavyBolt = BoltParams()
heavyBolt.id = "mt_heavy_bolt_v1"
heavyBolt.length = 0.45
heavyBolt.shaftRadius = 0.006
heavyBolt.useFletching = true
heavyBolt.fletchMaterial = "Plastic"
heavyBolt.fletchLength = 0.04
heavyBolt.tipMass = 0.03
heavyBolt.barbedTip = true

if heavyBolt:validate() then
    local heavyBoltBundle = generate_bolt(heavyBolt)
    if heavyBoltBundle.mesh ~= 0 then
        print("✓ Heavy bolt generated successfully")
    end
else
    print("✗ Heavy bolt parameters invalid")
end

-- Create a specialized arrow for long-range shooting
local longRangeArrow = ArrowParams()
longRangeArrow.id = "mt_longrange_arrow_v1"
longRangeArrow.shaftLength = 1.2
longRangeArrow.shaftDiameter = 0.007
longRangeArrow.spineRating = 700
longRangeArrow.useFletching = true
longRangeArrow.fletchStyle = "Parabolic"
longRangeArrow.nockSize = 0.019
longRangeArrow.tipMass = 0.013

if longRangeArrow:validate() then
    local longRangeBundle = generate_arrow(longRangeArrow)
    if longRangeBundle.mesh ~= 0 then
        print("✓ Long-range arrow generated successfully")
    end
else
    print("✗ Long-range arrow parameters invalid")
end

-- 8. Cache Management
print("\n--- Cache Management ---")
print("Current cache size: " .. get_cache_size())
clear_crossbow_cache()
print("Cache cleared")

-- 9. Performance Testing
print("\n--- Performance Testing ---")

local function benchmarkGeneration()
    local startTime = os.clock()
    
    -- Generate multiple assets
    for i = 1, 5 do
        local testCrossbow = create_light_crossbow()
        testCrossbow.id = "benchmark_crossbow_" .. i
        local bundle = generate_crossbow(testCrossbow)
    end
    
    for i = 1, 10 do
        local testBolt = create_steel_bolt()
        testBolt.id = "benchmark_bolt_" .. i
        local bundle = generate_bolt(testBolt)
    end
    
    for i = 1, 10 do
        local testArrow = create_wood_arrow()
        testArrow.id = "benchmark_arrow_" .. i
        local bundle = generate_arrow(testArrow)
    end
    
    local endTime = os.clock()
    local duration = endTime - startTime
    print("Generated 25 assets in " .. string.format("%.3f", duration) .. " seconds")
    print("Average time per asset: " .. string.format("%.3f", duration / 25) .. " seconds")
end

benchmarkGeneration()

print("\n=== Crossbow Generation Pipeline Demo Complete ===")
print("This demonstrates:")
print("- Parameter validation and error handling")
print("- Synchronous and asynchronous asset generation")
print("- Mesh, material, animation, and simulation generation")
print("- VFX trail and collision system integration")
print("- Cache management and performance optimization")
print("- Real-time progress monitoring")
print("- Advanced customization options") 