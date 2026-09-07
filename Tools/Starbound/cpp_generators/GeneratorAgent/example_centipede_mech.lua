-- ============================================================================
-- Centipede Mech Asset Generation Pipeline - Example Usage
-- ============================================================================
-- This script demonstrates the comprehensive C++/Lua framework for 
-- procedurally generating multi-segment centipede mechs with articulated
-- legs, logical cockpit interiors, sensor arrays, weapons hardpoints,
-- and fully customizable materials, VFX, audio, and physics.

-- ============================================================================
-- 1. PARAMETER SCHEMAS AND VALIDATION
-- ============================================================================

-- High-Level Mech Parameters
local function createMechParams(id, segmentCount, segmentLength, segmentRadius, baseColor, seamlessJoints)
    local params = MechParams()
    params.id = id
    params.segmentCount = segmentCount
    params.segmentLength = segmentLength
    params.segmentRadius = segmentRadius
    params.baseColor = baseColor
    params.seamlessJoints = seamlessJoints
    return params
end

-- Leg Parameters (per segment)
local function createLegParams(legsPerSegment, upperLegLength, lowerLegLength, jointRadius, armorPlates, footType)
    local params = LegParams()
    params.legsPerSegment = legsPerSegment
    params.upperLegLength = upperLegLength
    params.lowerLegLength = lowerLegLength
    params.jointRadius = jointRadius
    params.armorPlates = armorPlates
    params.footType = footType
    return params
end

-- Cockpit Parameters
local function createCockpitParams(hasCockpit, cockpitPosition, width, height, depth, enableDisplays, displayCount, seatMaterial, controlStyle)
    local params = CockpitParams()
    params.hasCockpit = hasCockpit
    params.cockpitPosition = cockpitPosition
    params.width = width
    params.height = height
    params.depth = depth
    params.enableDisplays = enableDisplays
    params.displayCount = displayCount
    params.seatMaterial = seatMaterial
    params.controlStyle = controlStyle
    return params
end

-- Weapon & Sensor Parameters
local function createHardpointParams(missileTubes, autocannonSlots, enableTurret, enableRadarArray, radarRange)
    local params = HardpointParams()
    params.missileTubes = missileTubes
    params.autocannonSlots = autocannonSlots
    params.enableTurret = enableTurret
    params.enableRadarArray = enableRadarArray
    params.radarRange = radarRange
    return params
end

-- ============================================================================
-- 2. VALIDATION FUNCTIONS
-- ============================================================================

local function validateMechConfiguration(mechParams, legParams, cockpitParams, hardpointParams)
    print("Validating mech configuration...")
    
    -- Validate MechParams
    if not mechParams:validate() then
        print("ERROR: Invalid MechParams")
        return false
    end
    
    -- Validate LegParams
    if not legParams:validate() then
        print("ERROR: Invalid LegParams")
        return false
    end
    
    -- Validate CockpitParams
    if not cockpitParams:validate() then
        print("ERROR: Invalid CockpitParams")
        return false
    end
    
    -- Validate HardpointParams
    if not hardpointParams:validate() then
        print("ERROR: Invalid HardpointParams")
        return false
    end
    
    print("All parameters validated successfully!")
    return true
end

-- ============================================================================
-- 3. MECH CONFIGURATION TEMPLATES
-- ============================================================================

-- Scout Mech - Fast, light, reconnaissance
local function createScoutMech()
    print("Creating Scout Mech configuration...")
    
    local mechParams = createMechParams(
        "Scout_MK_I",           -- id
        6,                      -- segmentCount
        0.8,                    -- segmentLength
        0.2,                    -- segmentRadius
        {0.2, 0.8, 0.2, 1.0},  -- baseColor (green)
        true                    -- seamlessJoints
    )
    
    local legParams = createLegParams(
        2,      -- legsPerSegment
        0.6,    -- upperLegLength
        0.4,    -- lowerLegLength
        0.08,   -- jointRadius
        false,  -- armorPlates
        "Pad"   -- footType
    )
    
    local cockpitParams = createCockpitParams(
        true,                   -- hasCockpit
        {0, 0, 0},             -- cockpitPosition
        0.8,                    -- width
        0.6,                    -- height
        1.0,                    -- depth
        true,                   -- enableDisplays
        2,                      -- displayCount
        "Light",                -- seatMaterial
        "Joystick"              -- controlStyle
    )
    
    local hardpointParams = createHardpointParams(
        1,      -- missileTubes
        0,      -- autocannonSlots
        false,  -- enableTurret
        true,   -- enableRadarArray
        200.0   -- radarRange
    )
    
    return mechParams, legParams, cockpitParams, hardpointParams
end

-- Assault Mech - Balanced, combat-focused
local function createAssaultMech()
    print("Creating Assault Mech configuration...")
    
    local mechParams = createMechParams(
        "Assault_MK_I",         -- id
        10,                     -- segmentCount
        1.4,                    -- segmentLength
        0.4,                    -- segmentRadius
        {0.8, 0.2, 0.2, 1.0},  -- baseColor (red)
        true                    -- seamlessJoints
    )
    
    local legParams = createLegParams(
        4,      -- legsPerSegment
        1.0,    -- upperLegLength
        0.8,    -- lowerLegLength
        0.12,   -- jointRadius
        true,   -- armorPlates
        "Claw"  -- footType
    )
    
    local cockpitParams = createCockpitParams(
        true,                   -- hasCockpit
        {0, 0, 0},             -- cockpitPosition
        1.2,                    -- width
        1.0,                    -- height
        1.4,                    -- depth
        true,                   -- enableDisplays
        6,                      -- displayCount
        "Heavy",                -- seatMaterial
        "Holographic"           -- controlStyle
    )
    
    local hardpointParams = createHardpointParams(
        4,      -- missileTubes
        2,      -- autocannonSlots
        true,   -- enableTurret
        true,   -- enableRadarArray
        500.0   -- radarRange
    )
    
    return mechParams, legParams, cockpitParams, hardpointParams
end

-- Heavy Mech - Massive, heavily armed
local function createHeavyMech()
    print("Creating Heavy Mech configuration...")
    
    local mechParams = createMechParams(
        "Heavy_MK_I",           -- id
        12,                     -- segmentCount
        1.6,                    -- segmentLength
        0.5,                    -- segmentRadius
        {0.3, 0.3, 0.8, 1.0},  -- baseColor (blue)
        true                    -- seamlessJoints
    )
    
    local legParams = createLegParams(
        6,      -- legsPerSegment
        1.2,    -- upperLegLength
        1.0,    -- lowerLegLength
        0.15,   -- jointRadius
        true,   -- armorPlates
        "Tread" -- footType
    )
    
    local cockpitParams = createCockpitParams(
        true,                   -- hasCockpit
        {0, 0, 0},             -- cockpitPosition
        1.5,                    -- width
        1.2,                    -- height
        1.8,                    -- depth
        true,                   -- enableDisplays
        8,                      -- displayCount
        "Command",              -- seatMaterial
        "Levers"                -- controlStyle
    )
    
    local hardpointParams = createHardpointParams(
        8,      -- missileTubes
        4,      -- autocannonSlots
        true,   -- enableTurret
        true,   -- enableRadarArray
        800.0   -- radarRange
    )
    
    return mechParams, legParams, cockpitParams, hardpointParams
end

-- ============================================================================
-- 4. ASYNC GENERATION AND ASSET MANAGEMENT
-- ============================================================================

-- Callback function for when mech generation completes
function on_mech_generated(mechId, bundle)
    print("=== MECH GENERATION COMPLETE ===")
    print("Mech ID: " .. mechId)
    print("Segments: " .. bundle:getSegmentCount())
    print("Joints: " .. bundle:getJointCount())
    print("Legs: " .. bundle:getLegCount())
    print("Has Cockpit: " .. tostring(bundle:hasCockpit()))
    print("Has Weapons: " .. tostring(bundle:hasWeapons()))
    print("Has Sensors: " .. tostring(bundle:hasSensors()))
    print("================================")
end

-- Generate mech with validation
local function generateMech(mechParams, legParams, cockpitParams, hardpointParams)
    if not validateMechConfiguration(mechParams, legParams, cockpitParams, hardpointParams) then
        print("ERROR: Mech configuration validation failed!")
        return nil
    end
    
    print("Starting async mech generation for: " .. mechParams.id)
    local mechId = spawn_centipede_mech(mechParams, legParams, cockpitParams, hardpointParams)
    print("Mech generation queued with ID: " .. mechId)
    return mechId
end

-- ============================================================================
-- 5. BATCH GENERATION AND TESTING
-- ============================================================================

local function runBatchGeneration()
    print("=== STARTING BATCH MECH GENERATION ===")
    
    -- Generate Scout Mech
    local scoutMech, scoutLegs, scoutCockpit, scoutHardpoints = createScoutMech()
    local scoutId = generateMech(scoutMech, scoutLegs, scoutCockpit, scoutHardpoints)
    
    -- Generate Assault Mech
    local assaultMech, assaultLegs, assaultCockpit, assaultHardpoints = createAssaultMech()
    local assaultId = generateMech(assaultMech, assaultLegs, assaultCockpit, assaultHardpoints)
    
    -- Generate Heavy Mech
    local heavyMech, heavyLegs, heavyCockpit, heavyHardpoints = createHeavyMech()
    local heavyId = generateMech(heavyMech, heavyLegs, heavyCockpit, heavyHardpoints)
    
    print("Batch generation started. Pending mechs: " .. get_pending_mech_count())
end

-- ============================================================================
-- 6. UTILITY FUNCTIONS
-- ============================================================================

local function checkFactoryStatus()
    local status = get_mech_factory_status()
    print("Mech Factory Status: " .. tostring(status))
    return status
end

local function monitorGeneration()
    local pendingCount = get_pending_mech_count()
    print("Pending mech generations: " .. pendingCount)
    return pendingCount
end

local function clearAllPending()
    print("Clearing all pending mech generations...")
    clear_pending_mechs()
    print("All pending generations cleared.")
end

-- ============================================================================
-- 7. MAIN EXECUTION
-- ============================================================================

print("=== CENTIPEDE MECH ASSET GENERATION PIPELINE ===")
print("Initializing comprehensive mech generation system...")

-- Check factory status
if not checkFactoryStatus() then
    print("ERROR: Mech factory not initialized!")
    return
end

-- Run batch generation
runBatchGeneration()

-- Monitor progress
local function monitorProgress()
    local pending = monitorGeneration()
    if pending == 0 then
        print("All mech generations completed!")
        return true
    end
    return false
end

-- Simple monitoring loop (in real usage, this would be called from the main game loop)
print("Monitoring generation progress...")
-- Note: In actual usage, poll_assets() would be called from the main game loop
-- This is just for demonstration

print("=== PIPELINE INITIALIZATION COMPLETE ===")
print("Ready for mech generation!") 