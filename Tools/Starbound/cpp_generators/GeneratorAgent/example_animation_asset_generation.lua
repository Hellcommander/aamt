-- Animation Asset Generation Pipeline Example
-- Demonstrates procedurally creating, blending, and optimizing animation assets

local AnimationAsset = require("AnimationAsset")
local AnimationAssetUtils = require("AnimationAssetUtils")
local AnimationAssetPresets = require("AnimationAssetPresets")

-- Initialize the animation asset factory
AnimationAsset.initialize(4) -- 4 threads

-- Enable performance monitoring
AnimationAsset.enablePerformanceMonitoring(true)
AnimationAsset.setPerformanceThresholds(100.0, 50.0) -- 100ms generation, 50ms load

print("=== Animation Asset Generation Pipeline Example ===")

-- Example 1: Basic skeleton and clip generation
print("\n--- Example 1: Basic Skeleton and Clip Generation ---")
local skeletonParams = AnimationAssetPresets.humanoidSkeleton()
local clipParams = AnimationAssetPresets.walkClip()

if AnimationAssetUtils.validateSkeletonParams(skeletonParams) and AnimationAssetUtils.validateAnimationClipParams(clipParams) then
    local bundle = AnimationAsset.generateSync(skeletonParams, clipParams)
    if bundle.isValid then
        print("Successfully generated humanoid skeleton with walk animation")
    else
        print("Failed to generate animation:", bundle.errorMessage)
    end
else
    print("Invalid skeleton or clip parameters")
end

-- Example 2: Animation with blend space
print("\n--- Example 2: Animation with Blend Space ---")
local runClipParams = AnimationAssetPresets.runClip()
local blendSpaceParams = AnimationAssetPresets.walkRunBlendSpace()

if AnimationAssetUtils.validateAnimationClipParams(runClipParams) and AnimationAssetUtils.validateBlendSpaceParams(blendSpaceParams) then
    local bundle = AnimationAsset.generateSync(skeletonParams, runClipParams, blendSpaceParams)
    if bundle.isValid then
        print("Successfully generated animation with blend space")
    else
        print("Failed to generate animation with blend space:", bundle.errorMessage)
    end
else
    print("Invalid clip or blend space parameters")
end

-- Example 3: Animation with procedural layer
print("\n--- Example 3: Animation with Procedural Layer ---")
local idleClipParams = AnimationAssetPresets.idleClip()
local procLayerParams = AnimationAssetPresets.noiseLayer()

if AnimationAssetUtils.validateAnimationClipParams(idleClipParams) and AnimationAssetUtils.validateProcLayerParams(procLayerParams) then
    local bundle = AnimationAsset.generateSync(skeletonParams, idleClipParams, nil, procLayerParams)
    if bundle.isValid then
        print("Successfully generated animation with procedural layer")
    else
        print("Failed to generate animation with procedural layer:", bundle.errorMessage)
    end
else
    print("Invalid clip or procedural layer parameters")
end

-- Example 4: Custom skeleton and animation parameters
print("\n--- Example 4: Custom Skeleton and Animation Parameters ---")
local customSkeleton = AnimationAssetUtils.createSkeletonParams({
    id = "custom_creature",
    bones = {"root", "body", "head", "tail"},
    parentIndices = {-1, 0, 1, 1},
    rootPosition = {0.0, 0.0, 0.0},
    rootRotation = {1.0, 0.0, 0.0, 0.0},
    enableInverseBindPose = true,
    enableGPUOptimization = true
})

local customClip = AnimationAssetUtils.createAnimationClipParams({
    id = "custom_animation",
    skeletonId = "custom_creature",
    duration = 3.0,
    sampleRate = 30.0,
    interp = "Hermite",
    loop = true,
    enableRootMotion = false,
    compress = true,
    compressionTolerance = 1.0,
    enableEvents = true,
    eventNames = {"custom_event"},
    enableBlending = true,
    blendInTime = 0.5,
    blendOutTime = 0.5
})

if AnimationAssetUtils.validateSkeletonParams(customSkeleton) and AnimationAssetUtils.validateAnimationClipParams(customClip) then
    local bundle = AnimationAsset.generateSync(customSkeleton, customClip)
    if bundle.isValid then
        print("Successfully generated custom creature animation")
    else
        print("Failed to generate custom animation:", bundle.errorMessage)
    end
else
    print("Invalid custom parameters")
end

-- Example 5: Async animation generation
print("\n--- Example 5: Async Animation Generation ---")
local quadrupedSkeleton = AnimationAssetPresets.quadrupedSkeleton()
local quadrupedClip = AnimationAssetUtils.createAnimationClipParams({
    id = "quadruped_walk",
    skeletonId = "quadruped",
    duration = 1.5,
    sampleRate = 60.0,
    interp = "Hermite",
    loop = true,
    enableRootMotion = true
})

if AnimationAssetUtils.validateSkeletonParams(quadrupedSkeleton) and AnimationAssetUtils.validateAnimationClipParams(quadrupedClip) then
    local future = AnimationAsset.generateAsync(quadrupedSkeleton, quadrupedClip)
    print("Async animation generation started for quadruped")
    -- In a real application, you would wait for the future to complete
end

-- Example 6: Batch animation generation
print("\n--- Example 6: Batch Animation Generation ---")
local skeletonParamsList = {
    AnimationAssetPresets.humanoidSkeleton(),
    AnimationAssetPresets.quadrupedSkeleton()
}

local clipParamsList = {
    AnimationAssetPresets.walkClip(),
    AnimationAssetUtils.createAnimationClipParams({
        id = "quadruped_idle",
        skeletonId = "quadruped",
        duration = 2.0,
        sampleRate = 30.0,
        interp = "Linear",
        loop = true
    })
}

-- Set unique IDs for batch generation
for i, params in ipairs(skeletonParamsList) do
    params.id = "batch_skeleton_" .. i
end

for i, params in ipairs(clipParamsList) do
    params.id = "batch_clip_" .. i
    params.skeletonId = skeletonParamsList[i].id
end

local futures = AnimationAsset.generateBatch(skeletonParamsList, clipParamsList)
print("Started batch generation for", #futures, "animations")

-- Example 7: Complex animation with all features
print("\n--- Example 7: Complex Animation with All Features ---")
local complexSkeleton = AnimationAssetPresets.humanoidSkeleton()
complexSkeleton.id = "complex_humanoid"

local complexClip = AnimationAssetPresets.walkClip()
complexClip.id = "complex_walk"
complexClip.skeletonId = "complex_humanoid"

local complexBlendSpace = AnimationAssetPresets.directionalBlendSpace()
complexBlendSpace.id = "complex_directional"

local complexProcLayer = AnimationAssetPresets.aimLayer()
complexProcLayer.id = "complex_aim"
complexProcLayer.skeletonId = "complex_humanoid"

if AnimationAssetUtils.validateSkeletonParams(complexSkeleton) and 
   AnimationAssetUtils.validateAnimationClipParams(complexClip) and
   AnimationAssetUtils.validateBlendSpaceParams(complexBlendSpace) and
   AnimationAssetUtils.validateProcLayerParams(complexProcLayer) then
    
    local bundle = AnimationAsset.generateSync(complexSkeleton, complexClip, complexBlendSpace, complexProcLayer)
    if bundle.isValid then
        print("Successfully generated complex animation with all features")
    else
        print("Failed to generate complex animation:", bundle.errorMessage)
    end
else
    print("Invalid complex animation parameters")
end

-- Example 8: IK procedural layer
print("\n--- Example 8: IK Procedural Layer ---")
local ikLayer = AnimationAssetPresets.basicIKLayer()
ikLayer.id = "test_ik"
ikLayer.skeletonId = "humanoid"

if AnimationAssetUtils.validateProcLayerParams(ikLayer) then
    local bundle = AnimationAsset.generateSync(skeletonParams, clipParams, nil, ikLayer)
    if bundle.isValid then
        print("Successfully generated animation with IK procedural layer")
    else
        print("Failed to generate animation with IK:", bundle.errorMessage)
    end
else
    print("Invalid IK layer parameters")
end

-- Example 9: Physics procedural layer
print("\n--- Example 9: Physics Procedural Layer ---")
local physicsLayer = AnimationAssetPresets.physicsLayer()
physicsLayer.id = "test_physics"
physicsLayer.skeletonId = "humanoid"

if AnimationAssetUtils.validateProcLayerParams(physicsLayer) then
    local bundle = AnimationAsset.generateSync(skeletonParams, clipParams, nil, physicsLayer)
    if bundle.isValid then
        print("Successfully generated animation with physics procedural layer")
    else
        print("Failed to generate animation with physics:", bundle.errorMessage)
    end
else
    print("Invalid physics layer parameters")
end

-- Example 10: Performance monitoring
print("\n--- Example 10: Performance Monitoring ---")
local stats = AnimationAsset.getStats()
print("Animation Asset Factory Statistics:")
print("  Total assets:", stats.totalAssets)
print("  Cached assets:", stats.cachedAssets)
print("  Generated assets:", stats.generatedAssets)
print("  Failed assets:", stats.failedAssets)
print("  Average generation time:", stats.averageGenerationTime, "ms")
print("  Average load time:", stats.averageLoadTime, "ms")
print("  Total async jobs:", stats.totalAsyncJobs)
print("  Completed jobs:", stats.completedJobs)
print("  Failed jobs:", stats.failedJobs)
print("  Total skeletons:", stats.totalSkeletons)
print("  Total clips:", stats.totalClips)
print("  Total blend spaces:", stats.totalBlendSpaces)
print("  Total proc layers:", stats.totalProcLayers)

-- Example 11: Cache management
print("\n--- Example 11: Cache Management ---")
print("Current cache size:", AnimationAsset.getCacheSize())
print("Max cache size:", AnimationAsset.getMaxCacheSize())

-- Set new cache size
AnimationAsset.setCacheSize(500)
print("Cache size set to 500")

-- Example 12: Asset validation and error handling
print("\n--- Example 12: Asset Validation and Error Handling ---")

-- Try to create invalid skeleton parameters
local invalidSkeleton = AnimationAssetUtils.createSkeletonParams({
    id = "", -- Empty ID should fail validation
    bones = {}, -- Empty bones should fail validation
    parentIndices = {1, 0}, -- Invalid parent indices should fail validation
})

if not AnimationAssetUtils.validateSkeletonParams(invalidSkeleton) then
    print("Correctly detected invalid skeleton parameters")
end

-- Try to create invalid clip parameters
local invalidClip = AnimationAssetUtils.createAnimationClipParams({
    id = "", -- Empty ID should fail validation
    skeletonId = "", -- Empty skeleton ID should fail validation
    duration = 0.0, -- Zero duration should fail validation
    sampleRate = 0.0, -- Zero sample rate should fail validation
})

if not AnimationAssetUtils.validateAnimationClipParams(invalidClip) then
    print("Correctly detected invalid clip parameters")
end

-- Example 13: Different skeleton types
print("\n--- Example 13: Different Skeleton Types ---")

-- Humanoid skeleton
local humanoidSkeleton = AnimationAssetPresets.humanoidSkeleton()
humanoidSkeleton.id = "test_humanoid"
local bundle1 = AnimationAsset.generateSync(humanoidSkeleton, clipParams)
print("Humanoid skeleton generation:", bundle1.isValid and "success" or "failed")

-- Quadruped skeleton
local quadrupedSkeleton = AnimationAssetPresets.quadrupedSkeleton()
quadrupedSkeleton.id = "test_quadruped"
local bundle2 = AnimationAsset.generateSync(quadrupedSkeleton, quadrupedClip)
print("Quadruped skeleton generation:", bundle2.isValid and "success" or "failed")

-- Example 14: Different clip types
print("\n--- Example 14: Different Clip Types ---")

-- Walk clip
local walkClip = AnimationAssetPresets.walkClip()
walkClip.id = "test_walk"
local bundle1 = AnimationAsset.generateSync(skeletonParams, walkClip)
print("Walk clip generation:", bundle1.isValid and "success" or "failed")

-- Run clip
local runClip = AnimationAssetPresets.runClip()
runClip.id = "test_run"
local bundle2 = AnimationAsset.generateSync(skeletonParams, runClip)
print("Run clip generation:", bundle2.isValid and "success" or "failed")

-- Idle clip
local idleClip = AnimationAssetPresets.idleClip()
idleClip.id = "test_idle"
local bundle3 = AnimationAsset.generateSync(skeletonParams, idleClip)
print("Idle clip generation:", bundle3.isValid and "success" or "failed")

-- Example 15: Different blend space types
print("\n--- Example 15: Different Blend Space Types ---")

-- 1D blend space
local blend1D = AnimationAssetPresets.walkRunBlendSpace()
blend1D.id = "test_blend1d"
local bundle1 = AnimationAsset.generateSync(skeletonParams, clipParams, blend1D)
print("1D blend space generation:", bundle1.isValid and "success" or "failed")

-- 2D blend space
local blend2D = AnimationAssetPresets.directionalBlendSpace()
blend2D.id = "test_blend2d"
local bundle2 = AnimationAsset.generateSync(skeletonParams, clipParams, blend2D)
print("2D blend space generation:", bundle2.isValid and "success" or "failed")

-- Example 16: Different procedural layer types
print("\n--- Example 16: Different Procedural Layer Types ---")

-- IK layer
local ikLayer = AnimationAssetPresets.basicIKLayer()
ikLayer.id = "test_ik"
local bundle1 = AnimationAsset.generateSync(skeletonParams, clipParams, nil, ikLayer)
print("IK layer generation:", bundle1.isValid and "success" or "failed")

-- Noise layer
local noiseLayer = AnimationAssetPresets.noiseLayer()
noiseLayer.id = "test_noise"
local bundle2 = AnimationAsset.generateSync(skeletonParams, clipParams, nil, noiseLayer)
print("Noise layer generation:", bundle2.isValid and "success" or "failed")

-- Aim layer
local aimLayer = AnimationAssetPresets.aimLayer()
aimLayer.id = "test_aim"
local bundle3 = AnimationAsset.generateSync(skeletonParams, clipParams, nil, aimLayer)
print("Aim layer generation:", bundle3.isValid and "success" or "failed")

-- Physics layer
local physicsLayer = AnimationAssetPresets.physicsLayer()
physicsLayer.id = "test_physics"
local bundle4 = AnimationAsset.generateSync(skeletonParams, clipParams, nil, physicsLayer)
print("Physics layer generation:", bundle4.isValid and "success" or "failed")

-- Example 17: Procedural animation generation
print("\n--- Example 17: Procedural Animation Generation ---")

-- Generate a series of animations with different parameters
for i = 1, 5 do
    local skeletonParams = AnimationAssetUtils.createSkeletonParams({
        id = "procedural_skeleton_" .. i,
        bones = {"root", "bone_" .. i},
        parentIndices = {-1, 0},
        enableInverseBindPose = true,
        enableGPUOptimization = true
    })
    
    local clipParams = AnimationAssetUtils.createAnimationClipParams({
        id = "procedural_clip_" .. i,
        skeletonId = "procedural_skeleton_" .. i,
        duration = 1.0 + i * 0.5,
        sampleRate = 30.0 + i * 10,
        interp = "Linear",
        loop = true,
        enableRootMotion = (i % 2 == 0),
        compress = true,
        compressionTolerance = 0.5 + i * 0.1
    })
    
    local bundle = AnimationAsset.generateSync(skeletonParams, clipParams)
    print("Procedural animation", i, "generation:", bundle.isValid and "success" or "failed")
end

-- Example 18: Integration with existing systems
print("\n--- Example 18: Integration with Existing Systems ---")

-- This would integrate with your existing animation systems
-- For example, converting between different animation formats
local convertToAnimationAsset = function(existingAnimDef)
    local skeletonParams = AnimationAssetUtils.createSkeletonParams({
        id = existingAnimDef.skeletonId .. "_converted",
        bones = existingAnimDef.bones or {"root"},
        parentIndices = existingAnimDef.parentIndices or {-1},
        enableInverseBindPose = existingAnimDef.enableInverseBindPose or true,
        enableGPUOptimization = existingAnimDef.enableGPUOptimization or true
    })
    
    local clipParams = AnimationAssetUtils.createAnimationClipParams({
        id = existingAnimDef.id .. "_converted",
        skeletonId = existingAnimDef.skeletonId .. "_converted",
        duration = existingAnimDef.duration or 1.0,
        sampleRate = existingAnimDef.sampleRate or 30.0,
        interp = existingAnimDef.interp or "Linear",
        loop = existingAnimDef.loop or false,
        enableRootMotion = existingAnimDef.enableRootMotion or false
    })
    
    return skeletonParams, clipParams
end

print("Integration utilities available")

-- Example 19: Performance optimization
print("\n--- Example 19: Performance Optimization ---")

-- Set stricter performance thresholds
AnimationAsset.setPerformanceThresholds(50.0, 25.0) -- 50ms generation, 25ms load

-- Monitor performance during intensive operations
for i = 1, 10 do
    local skeletonParams = AnimationAssetUtils.createSkeletonParams({
        id = "performance_test_skeleton_" .. i,
        bones = {"root", "bone_1", "bone_2", "bone_3"},
        parentIndices = {-1, 0, 1, 2},
        enableInverseBindPose = true,
        enableGPUOptimization = true
    })
    
    local clipParams = AnimationAssetUtils.createAnimationClipParams({
        id = "performance_test_clip_" .. i,
        skeletonId = "performance_test_skeleton_" .. i,
        duration = math.random() * 2 + 0.5,
        sampleRate = math.random(15, 60),
        interp = "Linear",
        loop = true,
        enableRootMotion = (i % 2 == 0),
        compress = true,
        compressionTolerance = math.random() * 2 + 0.1
    })
    
    local bundle = AnimationAsset.generateSync(skeletonParams, clipParams)
    if bundle.isValid then
        print("Performance test", i, "completed successfully")
    else
        print("Performance test", i, "failed:", bundle.errorMessage)
    end
end

-- Example 20: Asset management
print("\n--- Example 20: Asset Management ---")

-- Check if specific assets are loaded
local assetId = "humanoid"
if AnimationAsset.isAssetLoaded(assetId) then
    print("Asset is loaded:", assetId)
    local asset = AnimationAsset.getAsset(assetId)
    if asset then
        print("Asset retrieved successfully")
    end
else
    print("Asset not loaded:", assetId)
end

-- Example 21: Cleanup and shutdown
print("\n--- Example 21: Cleanup and Shutdown ---")

-- Unload all assets
AnimationAsset.unloadAllAssets()
print("All assets unloaded")

-- Clear cache
AnimationAsset.clearCache()
print("Cache cleared")

-- Reset statistics
AnimationAsset.resetStats()
print("Statistics reset")

-- Final statistics
local finalStats = AnimationAsset.getStats()
print("Final Statistics:")
print("  Total assets:", finalStats.totalAssets)
print("  Generated assets:", finalStats.generatedAssets)
print("  Failed assets:", finalStats.failedAssets)
print("  Total async jobs:", finalStats.totalAsyncJobs)
print("  Completed jobs:", finalStats.completedJobs)
print("  Failed jobs:", finalStats.failedJobs)
print("  Total skeletons:", finalStats.totalSkeletons)
print("  Total clips:", finalStats.totalClips)
print("  Total blend spaces:", finalStats.totalBlendSpaces)
print("  Total proc layers:", finalStats.totalProcLayers)

print("\n=== Animation Asset Generation Pipeline Example Complete ===")

-- Return the system for further use
return {
    AnimationAsset = AnimationAsset,
    AnimationAssetUtils = AnimationAssetUtils,
    AnimationAssetPresets = AnimationAssetPresets
} 