-- Procedural Generation of Mesh-Based Mechs with Animation
-- Demonstrates runtime generation of mech parts, skeletons, and animations
-- without requiring pre-made art assets

local ProceduralMech = require("ProceduralMech")
local ProceduralMechFactory = require("ProceduralMechFactory")

print("=== Procedural Generation of Mesh-Based Mechs with Animation ===")

-- Initialize the procedural mech factory
ProceduralMechFactory.initialize()

-- Example 1: Basic Part Generation
print("\n--- Example 1: Basic Part Generation ---")

-- Generate a simple torso part
local torsoParams = {
    type = "torso",
    dimensions = {2.0, 1.2, 0.8},  -- width, height, depth
    bevelRadius = 0.1,
    complexity = 0.3,
    colorSeed = 42,
    metallic = 0.8,
    roughness = 0.2,
    mountingPoints = {
        {0.0, 0.5, 0.0},   -- top socket
        {0.0, -0.5, 0.0},  -- bottom socket
        {1.0, 0.0, 0.0},   -- right socket
        {-1.0, 0.0, 0.0}   -- left socket
    },
    enableSymmetry = true,
    symmetryAxis = 0  -- X-axis symmetry
}

local torsoPart = ProceduralMechFactory.generatePart("torso", torsoParams)
if torsoPart then
    print("Successfully generated torso part")
    print("  Vertices:", #torsoPart.vertices)
    print("  Indices:", #torsoPart.indices)
    print("  Sockets:", #torsoPart.sockets)
    print("  Dimensions:", torsoPart:getDimensions().x, torsoPart:getDimensions().y, torsoPart:getDimensions().z)
else
    print("Failed to generate torso part")
end

-- Generate a limb part
local limbParams = {
    type = "limb",
    dimensions = {0.3, 1.5, 0.3},  -- width, length, depth
    bevelRadius = 0.05,
    complexity = 0.2,
    colorSeed = 123,
    metallic = 0.9,
    roughness = 0.1,
    mountingPoints = {
        {0.0, 0.75, 0.0},   -- top socket
        {0.0, -0.75, 0.0}   -- bottom socket
    },
    enableSymmetry = false
}

local limbPart = ProceduralMechFactory.generatePart("limb", limbParams)
if limbPart then
    print("Successfully generated limb part")
    print("  Vertices:", #limbPart.vertices)
    print("  Indices:", #limbPart.indices)
    print("  Sockets:", #limbPart.sockets)
else
    print("Failed to generate limb part")
end

-- Generate a weapon part
local weaponParams = {
    type = "weapon",
    dimensions = {0.2, 2.0, 0.2},  -- width, length, depth
    bevelRadius = 0.02,
    complexity = 0.4,
    colorSeed = 456,
    metallic = 0.7,
    roughness = 0.3,
    mountingPoints = {
        {0.0, -1.0, 0.0}   -- mounting socket
    },
    enableSymmetry = true,
    symmetryAxis = 0
}

local weaponPart = ProceduralMechFactory.generatePart("weapon", weaponParams)
if weaponPart then
    print("Successfully generated weapon part")
    print("  Vertices:", #weaponPart.vertices)
    print("  Indices:", #weaponPart.indices)
    print("  Sockets:", #weaponPart.sockets)
else
    print("Failed to generate weapon part")
end

-- Example 2: Procedural Animation Generation
print("\n--- Example 2: Procedural Animation Generation ---")

-- Generate idle animation
local idleParams = {
    type = "idle",
    duration = 2.0,
    frequency = 0.5,
    amplitude = 0.1,
    phase = {0.0, 0.0, 0.0},
    loop = true,
    enableRootMotion = false,
    affectedBones = {"torso", "head"},
    boneFrequencies = {torso = 0.3, head = 0.7},
    boneAmplitudes = {torso = 0.05, head = 0.1}
}

local idleAnimation = ProceduralMechFactory.generateAnimation("idle", idleParams, torsoPart.skeleton)
if idleAnimation then
    print("Successfully generated idle animation")
    print("  Duration:", idleAnimation.duration)
    print("  Tracks:", #idleAnimation.tracks)
    print("  Loop:", idleAnimation.loop)
else
    print("Failed to generate idle animation")
end

-- Generate walk animation
local walkParams = {
    type = "walk",
    duration = 1.0,
    frequency = 1.0,
    amplitude = 0.3,
    phase = {0.0, 0.0, 0.0},
    loop = true,
    enableRootMotion = true,
    affectedBones = {"left_leg", "right_leg", "left_arm", "right_arm"},
    boneFrequencies = {left_leg = 1.0, right_leg = 1.0, left_arm = 1.0, right_arm = 1.0},
    boneAmplitudes = {left_leg = 0.2, right_leg = 0.2, left_arm = 0.15, right_arm = 0.15}
}

local walkAnimation = ProceduralMechFactory.generateAnimation("walk", walkParams, torsoPart.skeleton)
if walkAnimation then
    print("Successfully generated walk animation")
    print("  Duration:", walkAnimation.duration)
    print("  Tracks:", #walkAnimation.tracks)
    print("  Root motion enabled:", walkAnimation.enableRootMotion)
else
    print("Failed to generate walk animation")
end

-- Example 3: Complete Mech Generation
print("\n--- Example 3: Complete Mech Generation ---")

-- Define mech parts
local mechParts = {
    {type = "torso", params = {
        type = "torso",
        dimensions = {2.0, 1.5, 1.0},
        bevelRadius = 0.15,
        complexity = 0.4,
        colorSeed = 42,
        metallic = 0.8,
        roughness = 0.2,
        mountingPoints = {
            {0.0, 0.75, 0.0},   -- head socket
            {0.0, -0.75, 0.0},  -- legs socket
            {1.0, 0.0, 0.0},    -- right arm socket
            {-1.0, 0.0, 0.0}    -- left arm socket
        },
        enableSymmetry = true,
        symmetryAxis = 0
    }},
    
    {type = "head", params = {
        type = "head",
        dimensions = {0.8, 0.8, 0.8},
        bevelRadius = 0.1,
        complexity = 0.5,
        colorSeed = 123,
        metallic = 0.7,
        roughness = 0.3,
        mountingPoints = {
            {0.0, -0.4, 0.0}   -- neck socket
        },
        enableSymmetry = true,
        symmetryAxis = 0
    }},
    
    {type = "limb", params = {
        type = "limb",
        dimensions = {0.4, 1.8, 0.4},
        bevelRadius = 0.08,
        complexity = 0.3,
        colorSeed = 456,
        metallic = 0.9,
        roughness = 0.1,
        mountingPoints = {
            {0.0, 0.9, 0.0},   -- shoulder socket
            {0.0, -0.9, 0.0}   -- hand socket
        },
        enableSymmetry = false
    }},
    
    {type = "limb", params = {
        type = "limb",
        dimensions = {0.5, 2.2, 0.5},
        bevelRadius = 0.1,
        complexity = 0.3,
        colorSeed = 789,
        metallic = 0.9,
        roughness = 0.1,
        mountingPoints = {
            {0.0, 1.1, 0.0},   -- hip socket
            {0.0, -1.1, 0.0}   -- foot socket
        },
        enableSymmetry = false
    }},
    
    {type = "weapon", params = {
        type = "weapon",
        dimensions = {0.3, 2.5, 0.3},
        bevelRadius = 0.05,
        complexity = 0.6,
        colorSeed = 101,
        metallic = 0.6,
        roughness = 0.4,
        mountingPoints = {
            {0.0, -1.25, 0.0}  -- mounting socket
        },
        enableSymmetry = true,
        symmetryAxis = 0
    }}
}

-- Generate complete mech
local mech = ProceduralMechFactory.generateMechFromParams("test_mech", mechParts, 12345)
if mech then
    print("Successfully generated procedural mech")
    print("  Parts:", #mech.parts)
    print("  Master skeleton bones:", mech.masterSkeleton and mech.masterSkeleton:getBoneCount() or 0)
    print("  Assembled mesh vertices:", mech.assembledMesh and "generated" or "none")
    print("  Animations:", #mech.animations)
    print("  Blend spaces:", #mech.blendSpaces)
    print("  Procedural layers:", #mech.proceduralLayers)
    
    -- Test mech properties
    print("  Center of mass:", mech:getCenterOfMass().x, mech:getCenterOfMass().y, mech:getCenterOfMass().z)
    print("  Total mass:", mech:getTotalMass())
    print("  Dimensions:", mech:getDimensions().x, mech:getDimensions().y, mech:getDimensions().z)
else
    print("Failed to generate procedural mech")
end

-- Example 4: Runtime Animation Control
print("\n--- Example 4: Runtime Animation Control ---")

if mech then
    -- Play idle animation
    mech:playAnimation("idle", true)
    print("Playing idle animation")
    
    -- Simulate animation update
    for i = 1, 10 do
        mech:update(0.016) -- 60 FPS
        print("  Animation time:", mech.animationTime)
        print("  Current animation:", mech.currentAnimation)
        print("  Animation playing:", mech.animationPlaying)
    end
    
    -- Switch to walk animation
    mech:playAnimation("walk", true)
    print("Switched to walk animation")
    
    -- Simulate more animation updates
    for i = 1, 5 do
        mech:update(0.016)
        print("  Animation time:", mech.animationTime)
    end
    
    -- Stop animation
    mech:stopAnimation()
    print("Stopped animation")
end

-- Example 5: Preset Mech Generation
print("\n--- Example 5: Preset Mech Generation ---")

-- Generate a preset mech
local presetMech = ProceduralMechFactory.generatePresetMech("scout_mech", 54321)
if presetMech then
    print("Successfully generated preset mech: scout_mech")
    print("  Parts:", #presetMech.parts)
    print("  Master skeleton bones:", presetMech.masterSkeleton and presetMech.masterSkeleton:getBoneCount() or 0)
    print("  Animations:", #presetMech.animations)
else
    print("Failed to generate preset mech")
end

-- List available presets
local presets = ProceduralMechFactory.getAvailablePresets()
print("Available presets:")
for _, preset in ipairs(presets) do
    print("  -", preset)
end

-- Example 6: Advanced Part Generation Techniques
print("\n--- Example 6: Advanced Part Generation Techniques ---")

-- Generate complex part with SDF
local complexParams = {
    type = "complex",
    dimensions = {1.5, 1.5, 1.5},
    bevelRadius = 0.2,
    complexity = 0.8,
    colorSeed = 999,
    metallic = 0.5,
    roughness = 0.5,
    mountingPoints = {
        {0.0, 0.75, 0.0},
        {0.0, -0.75, 0.0}
    },
    enableSymmetry = true,
    symmetryAxis = 1
}

local complexPart = ProceduralMechFactory.generatePart("complex", complexParams)
if complexPart then
    print("Successfully generated complex part")
    print("  Vertices:", #complexPart.vertices)
    print("  Indices:", #complexPart.indices)
    print("  Complexity:", complexPart.params.complexity)
else
    print("Failed to generate complex part")
end

-- Generate weapon with CSG
local weaponCSGParams = {
    type = "weapon_csg",
    dimensions = {0.4, 3.0, 0.4},
    bevelRadius = 0.05,
    complexity = 0.7,
    colorSeed = 777,
    metallic = 0.8,
    roughness = 0.2,
    mountingPoints = {
        {0.0, -1.5, 0.0}
    },
    enableSymmetry = true,
    symmetryAxis = 0
}

local weaponCSGPart = ProceduralMechFactory.generatePart("weapon_csg", weaponCSGParams)
if weaponCSGPart then
    print("Successfully generated CSG weapon part")
    print("  Vertices:", #weaponCSGPart.vertices)
    print("  Indices:", #weaponCSGPart.indices)
else
    print("Failed to generate CSG weapon part")
end

-- Example 7: Procedural Animation Techniques
print("\n--- Example 7: Procedural Animation Techniques ---")

-- Generate sinusoidal animation
local sinusoidalParams = {
    type = "sinusoidal",
    duration = 3.0,
    frequency = 0.8,
    amplitude = 0.2,
    phase = {0.0, 0.5, 1.0},
    loop = true,
    enableRootMotion = false,
    affectedBones = {"torso", "head", "arms"},
    boneFrequencies = {torso = 0.4, head = 0.6, arms = 0.8},
    boneAmplitudes = {torso = 0.1, head = 0.15, arms = 0.2}
}

local sinusoidalAnimation = ProceduralMechFactory.generateAnimation("sinusoidal", sinusoidalParams, torsoPart.skeleton)
if sinusoidalAnimation then
    print("Successfully generated sinusoidal animation")
    print("  Duration:", sinusoidalAnimation.duration)
    print("  Frequency:", sinusoidalParams.frequency)
    print("  Amplitude:", sinusoidalParams.amplitude)
else
    print("Failed to generate sinusoidal animation")
end

-- Generate spline-based animation
local splineParams = {
    type = "spline",
    duration = 2.0,
    frequency = 1.0,
    amplitude = 0.3,
    phase = {0.0, 0.0, 0.0},
    loop = true,
    enableRootMotion = true,
    affectedBones = {"legs"},
    boneFrequencies = {legs = 1.0},
    boneAmplitudes = {legs = 0.25}
}

local splineAnimation = ProceduralMechFactory.generateAnimation("spline", splineParams, torsoPart.skeleton)
if splineAnimation then
    print("Successfully generated spline animation")
    print("  Duration:", splineAnimation.duration)
    print("  Root motion enabled:", splineAnimation.enableRootMotion)
else
    print("Failed to generate spline animation")
end

-- Example 8: Performance and Caching
print("\n--- Example 8: Performance and Caching ---")

-- Test caching with identical parameters
local startTime = os.clock()
for i = 1, 5 do
    local cachedPart = ProceduralMechFactory.generatePart("torso", torsoParams)
    if cachedPart then
        print("  Generated cached part", i, "in", (os.clock() - startTime) * 1000, "ms")
    end
end

-- Get factory statistics
local stats = ProceduralMechFactory.getStats()
print("Procedural Mech Factory Statistics:")
print("  Generated mechs:", stats.generatedMechs)
print("  Generated parts:", stats.generatedParts)
print("  Generated animations:", stats.generatedAnimations)
print("  Cache hits:", stats.cacheHits)
print("  Cache misses:", stats.cacheMisses)
print("  Average generation time:", stats.averageGenerationTime, "ms")

-- Test cache management
print("Cache size:", ProceduralMechFactory.getCacheSize())
ProceduralMechFactory.setCacheSize(100)
print("Set cache size to 100")

-- Example 9: Integration with Existing Systems
print("\n--- Example 9: Integration with Existing Systems ---")

-- Create a procedural mech and integrate with entity system
local function createProceduralMechEntity(mechId, position, rotation)
    local mech = ProceduralMechFactory.generateMech(mechId, os.time())
    if mech then
        -- Set transform
        mech.position = position
        mech.rotation = rotation
        mech:updateTransform()
        
        -- Create entity
        local entity = {
            id = "procedural_mech_" .. mechId,
            type = "procedural_mech",
            position = position,
            rotation = rotation,
            mech = mech,
            components = {}
        }
        
        -- Add physics component
        entity.components.physics = {
            mass = mech:getTotalMass(),
            centerOfMass = mech:getCenterOfMass(),
            dimensions = mech:getDimensions(),
            enabled = true
        }
        
        -- Add rendering component
        entity.components.rendering = {
            mesh = mech.assembledMesh,
            skeleton = mech.masterSkeleton,
            animations = mech.animations,
            blendSpaces = mech.blendSpaces,
            proceduralLayers = mech.proceduralLayers
        }
        
        -- Add animation component
        entity.components.animation = {
            currentTime = 0.0,
            currentAnimation = "",
            playing = false,
            loop = true
        }
        
        print("Created procedural mech entity:", entity.id)
        print("  Mass:", entity.components.physics.mass)
        print("  Dimensions:", entity.components.physics.dimensions.x, 
              entity.components.physics.dimensions.y, 
              entity.components.physics.dimensions.z)
        print("  Animations:", #entity.components.rendering.animations)
        
        return entity
    end
    return nil
end

-- Test entity creation
local mechEntity = createProceduralMechEntity("test_entity", {0, 0, 0}, {1, 0, 0, 0})
if mechEntity then
    print("Successfully created procedural mech entity")
else
    print("Failed to create procedural mech entity")
end

-- Example 10: Advanced Features
print("\n--- Example 10: Advanced Features ---")

-- Test symmetry generation
local symmetricParams = {
    type = "symmetric",
    dimensions = {2.0, 1.0, 1.0},
    bevelRadius = 0.1,
    complexity = 0.5,
    colorSeed = 555,
    metallic = 0.7,
    roughness = 0.3,
    mountingPoints = {
        {0.0, 0.5, 0.0},
        {0.0, -0.5, 0.0}
    },
    enableSymmetry = true,
    symmetryAxis = 1  -- Y-axis symmetry
}

local symmetricPart = ProceduralMechFactory.generatePart("symmetric", symmetricParams)
if symmetricPart then
    print("Successfully generated symmetric part")
    print("  Symmetry enabled:", symmetricPart.params.enableSymmetry)
    print("  Symmetry axis:", symmetricPart.params.symmetryAxis)
    print("  Vertices:", #symmetricPart.vertices)
else
    print("Failed to generate symmetric part")
end

-- Test procedural material generation
local materialParams = {
    type = "material_test",
    dimensions = {1.0, 1.0, 1.0},
    bevelRadius = 0.05,
    complexity = 0.3,
    colorSeed = 888,
    metallic = 0.9,
    roughness = 0.1,
    mountingPoints = {},
    enableSymmetry = false
}

local materialPart = ProceduralMechFactory.generatePart("material_test", materialParams)
if materialPart then
    print("Successfully generated material test part")
    print("  Color seed:", materialPart.params.colorSeed)
    print("  Metallic:", materialPart.params.metallic)
    print("  Roughness:", materialPart.params.roughness)
else
    print("Failed to generate material test part")
end

-- Example 11: Cleanup and Shutdown
print("\n--- Example 11: Cleanup and Shutdown ---")

-- Clear cache
ProceduralMechFactory.clearCache()
print("Cleared procedural mech factory cache")

-- Reset statistics
ProceduralMechFactory.resetStats()
print("Reset procedural mech factory statistics")

-- Shutdown
ProceduralMechFactory.shutdown()
print("Procedural mech factory shutdown complete")

print("\n=== Procedural Generation of Mesh-Based Mechs with Animation Complete ===")

-- Return the system for further use
return {
    ProceduralMech = ProceduralMech,
    ProceduralMechFactory = ProceduralMechFactory,
    createProceduralMechEntity = createProceduralMechEntity
} 