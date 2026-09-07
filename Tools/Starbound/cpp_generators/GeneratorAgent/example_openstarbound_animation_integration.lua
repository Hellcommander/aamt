-- OpenStarbound Animation Asset Integration Example
-- Demonstrates loading skeletons, clips, blend spaces, and procedural layers
-- with full OpenStarbound integration and runtime instantiation

local AnimationAsset = require("AnimationAsset")
local AnimationAssetUtils = require("AnimationAssetUtils")

-- Initialize the animation asset manager
AnimationAsset.initialize()
AnimationAsset.enableHotReload(true)

-- Watch directories for hot reload
AnimationAsset.watchDirectory("assets/animations")
AnimationAsset.watchDirectory("assets/skeletons")

print("=== OpenStarbound Animation Asset Integration Example ===")

-- Example 1: Loading assets from files
print("\n--- Example 1: Loading Assets from Files ---")

-- Load skeleton from file
local skeleton = AnimationAsset.loadSkeleton("assets/skeletons/humanoid.skeleton.json")
if skeleton then
    print("Successfully loaded skeleton:", skeleton.name)
    print("  Bone count:", skeleton:getBoneCount())
    print("  Has root bone:", skeleton:hasBone("root"))
    print("  Has hip bone:", skeleton:hasBone("hip"))
else
    print("Failed to load skeleton from file")
end

-- Load animation clip from file
local walkClip = AnimationAsset.loadAnimationClip("assets/animations/humanoid_walk.animbin")
if walkClip then
    print("Successfully loaded animation clip:", walkClip.name)
    print("  Duration:", walkClip.duration, "seconds")
    print("  Sample rate:", walkClip.sampleRate, "fps")
    print("  Track count:", #walkClip.tracks)
    print("  Loop:", walkClip.loop)
    print("  Root motion enabled:", walkClip.enableRootMotion)
else
    print("Failed to load animation clip from file")
end

-- Load blend space from file
local locomotionBlendSpace = AnimationAsset.loadBlendSpace("assets/animations/humanoid_locomotion.blendspace")
if locomotionBlendSpace then
    print("Successfully loaded blend space:", locomotionBlendSpace.name)
    print("  Type:", locomotionBlendSpace.type == "OneD" and "1D" or "2D")
    print("  Sample count:", #locomotionBlendSpace.samples)
    print("  Smoothing enabled:", locomotionBlendSpace.enableSmoothing)
else
    print("Failed to load blend space from file")
end

-- Load procedural layer from file
local ikLayer = AnimationAsset.loadProceduralLayer("assets/animations/humanoid_ik.proclayer")
if ikLayer then
    print("Successfully loaded procedural layer:", ikLayer.name)
    print("  Type:", ikLayer.type)
    print("  Weight:", ikLayer.weight)
    print("  Enabled:", ikLayer:isEnabled())
else
    print("Failed to load procedural layer from file")
end

-- Example 2: Creating assets programmatically
print("\n--- Example 2: Creating Assets Programmatically ---")

-- Create skeleton programmatically
local customSkeleton = AnimationAsset.createSkeleton("custom_creature")
customSkeleton:addBone(Bone("root", -1, glm.mat4(1.0f)))
customSkeleton:addBone(Bone("body", 0, glm.mat4(1.0f)))
customSkeleton:addBone(Bone("head", 1, glm.mat4(1.0f)))
customSkeleton:addBone(Bone("tail", 1, glm.mat4(1.0f)))

if customSkeleton:validate() then
    print("Successfully created custom skeleton")
    print("  Bone count:", customSkeleton:getBoneCount())
    print("  Valid hierarchy:", customSkeleton:validateHierarchy())
else
    print("Failed to create valid custom skeleton")
end

-- Create animation clip programmatically
local customClip = AnimationAsset.createAnimationClip("custom_animation")
customClip.skeletonName = "custom_creature"
customClip.duration = 2.0
customClip.sampleRate = 30.0
customClip.loop = true
customClip.enableRootMotion = false

-- Add keyframe track
local track = KeyframeTrack("body", "Linear")
track:addKeyframe(Keyframe(0.0, glm.vec3(0, 0, 0), glm.quat(1, 0, 0, 0), glm.vec3(1, 1, 1)))
track:addKeyframe(Keyframe(1.0, glm.vec3(0, 1, 0), glm.quat(1, 0, 0, 0), glm.vec3(1, 1, 1)))
track:addKeyframe(Keyframe(2.0, glm.vec3(0, 0, 0), glm.quat(1, 0, 0, 0), glm.vec3(1, 1, 1)))

customClip:addTrack(track)

if customClip:validate() then
    print("Successfully created custom animation clip")
    print("  Duration:", customClip.duration, "seconds")
    print("  Track count:", #customClip.tracks)
else
    print("Failed to create valid custom animation clip")
end

-- Create blend space programmatically
local customBlendSpace = AnimationAsset.createBlendSpace("custom_blendspace", "TwoD")
customBlendSpace:addSample(BlendSample("idle", glm.vec2(0.5, 0.5), 1.0))
customBlendSpace:addSample(BlendSample("walk", glm.vec2(0.5, 1.0), 1.0))
customBlendSpace:addSample(BlendSample("run", glm.vec2(1.0, 1.0), 1.0))
customBlendSpace.enableSmoothing = true
customBlendSpace.smoothingRadius = 0.2

if customBlendSpace:validate() then
    print("Successfully created custom blend space")
    print("  Type:", customBlendSpace.type == "OneD" and "1D" or "2D")
    print("  Sample count:", #customBlendSpace.samples)
else
    print("Failed to create valid custom blend space")
end

-- Create procedural layer programmatically
local customIKLayer = AnimationAsset.createProceduralLayer("custom_ik", "IK")
customIKLayer.endEffectorBone = "hand_r"
customIKLayer.targetPosition = glm.vec3(1.0, 1.5, 0.0)
customIKLayer.maxIterations = 10
customIKLayer.tolerance = 0.001
customIKLayer:setWeight(1.0)
customIKLayer:setEnabled(true)

if customIKLayer:validate() then
    print("Successfully created custom IK layer")
    print("  End effector:", customIKLayer.endEffectorBone)
    print("  Target position:", customIKLayer.targetPosition.x, customIKLayer.targetPosition.y, customIKLayer.targetPosition.z)
    print("  Weight:", customIKLayer:getWeight())
else
    print("Failed to create valid custom IK layer")
end

-- Example 3: Runtime workflow with entity integration
print("\n--- Example 3: Runtime Workflow with Entity Integration ---")

-- Simulate entity spawn hook
local function onEntitySpawn(entity)
    print("Entity spawned, setting up animation system")
    
    -- Load assets for this entity type
    local entitySkeleton = AnimationAsset.loadSkeleton("assets/skeletons/" .. entity.type .. ".skeleton.json")
    local walkClip = AnimationAsset.loadAnimationClip("assets/animations/" .. entity.type .. "_walk.animbin")
    local runClip = AnimationAsset.loadAnimationClip("assets/animations/" .. entity.type .. "_run.animbin")
    local idleClip = AnimationAsset.loadAnimationClip("assets/animations/" .. entity.type .. "_idle.animbin")
    
    if entitySkeleton and walkClip and runClip and idleClip then
        -- Create blend space for locomotion
        local locomotionBS = AnimationAsset.createBlendSpace("locomotion", "TwoD")
        locomotionBS:addSample(BlendSample("idle", glm.vec2(0.5, 0.5), 1.0))
        locomotionBS:addSample(BlendSample("walk", glm.vec2(0.5, 1.0), 1.0))
        locomotionBS:addSample(BlendSample("run", glm.vec2(1.0, 1.0), 1.0))
        locomotionBS.enableSmoothing = true
        
        -- Create procedural layers
        local footIK = AnimationAsset.createProceduralLayer("foot_ik", "IK")
        footIK.endEffectorBone = "foot_l"
        footIK:setWeight(1.0)
        
        local noiseLayer = AnimationAsset.createProceduralLayer("noise", "Noise")
        noiseLayer.frequency = 0.25
        noiseLayer.amplitude = 0.05
        noiseLayer:setWeight(0.3)
        
        -- Store animation components in entity
        entity.animation = {
            skeleton = entitySkeleton,
            clips = { walk = walkClip, run = runClip, idle = idleClip },
            blendSpace = locomotionBS,
            layers = { footIK, noiseLayer }
        }
        
        print("  Animation system setup complete for entity:", entity.id)
        print("    Skeleton:", entitySkeleton.name)
        print("    Clips loaded:", 3)
        print("    Blend space:", locomotionBS.name)
        print("    Procedural layers:", 2)
    else
        print("  Failed to load animation assets for entity:", entity.id)
    end
end

-- Simulate entity update
local function onEntityUpdate(entity, deltaTime)
    if entity.animation then
        -- Update blend space parameters based on entity state
        local speed = entity.velocity:length()
        local direction = entity.velocity:normalize()
        
        -- Evaluate blend space
        local weights = entity.animation.blendSpace:evaluateWeights(glm.vec2(speed, direction.x))
        local activeClips = entity.animation.blendSpace:getActiveClips(glm.vec2(speed, direction.x))
        
        -- Sample poses from active clips
        local currentTime = entity.animationTime or 0.0
        local finalPose = {}
        
        for i, clipName in ipairs(activeClips) do
            local clip = entity.animation.clips[clipName]
            if clip then
                local pose = clip:samplePose(currentTime, true)
                local weight = weights[i] or 0.0
                
                -- Blend poses
                for j, transform in ipairs(pose) do
                    if not finalPose[j] then
                        finalPose[j] = transform * weight
                    else
                        finalPose[j] = finalPose[j] + transform * weight
                    end
                end
            end
        end
        
        -- Apply procedural layers
        for _, layer in ipairs(entity.animation.layers) do
            if layer:isEnabled() then
                layer:apply(finalPose, deltaTime)
            end
        end
        
        -- Update entity transform
        entity.animationTime = (entity.animationTime or 0.0) + deltaTime
        
        print("  Updated animation for entity:", entity.id)
        print("    Speed:", speed)
        print("    Active clips:", table.concat(activeClips, ", "))
        print("    Pose transforms:", #finalPose)
    end
end

-- Example 4: Asset management and hot reload
print("\n--- Example 4: Asset Management and Hot Reload ---")

-- Check if assets are loaded
local assetPaths = {
    "assets/skeletons/humanoid.skeleton.json",
    "assets/animations/humanoid_walk.animbin",
    "assets/animations/humanoid_locomotion.blendspace"
}

for _, path in ipairs(assetPaths) do
    if AnimationAsset.isAssetLoaded(path) then
        print("Asset is loaded:", path)
    else
        print("Asset not loaded:", path)
    end
end

-- Get asset manager statistics
local stats = AnimationAsset.getStats()
print("Asset Manager Statistics:")
print("  Loaded skeletons:", stats.loadedSkeletons)
print("  Loaded animation clips:", stats.loadedAnimationClips)
print("  Loaded blend spaces:", stats.loadedBlendSpaces)
print("  Loaded procedural layers:", stats.loadedProceduralLayers)
print("  Cache hits:", stats.cacheHits)
print("  Cache misses:", stats.cacheMisses)
print("  Average load time:", stats.averageLoadTime, "ms")

-- Example 5: JSON-based asset creation
print("\n--- Example 5: JSON-based Asset Creation ---")

-- Create skeleton from JSON
local skeletonJSON = [[
{
  "name": "json_skeleton",
  "rootPosition": [0.0, 0.0, 0.0],
  "rootRotation": [0.0, 0.0, 0.0, 1.0],
  "enableGPUOptimization": true,
  "bones": [
    {
      "name": "root",
      "parentIndex": -1,
      "bindPose": [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
      ]
    },
    {
      "name": "body",
      "parentIndex": 0,
      "bindPose": [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
      ]
    }
  ]
}
]]

local jsonSkeleton = AnimationAssetUtils.createSkeletonFromJSON(skeletonJSON)
if jsonSkeleton then
    print("Successfully created skeleton from JSON")
    print("  Name:", jsonSkeleton.name)
    print("  Bone count:", jsonSkeleton:getBoneCount())
    print("  Valid:", jsonSkeleton:validate())
else
    print("Failed to create skeleton from JSON")
end

-- Create blend space from JSON
local blendSpaceJSON = [[
{
  "name": "json_blendspace",
  "type": "TwoD",
  "enableSmoothing": true,
  "smoothingRadius": 0.2,
  "samples": [
    {
      "clipName": "idle",
      "coordinates": [0.5, 0.5],
      "weight": 1.0
    },
    {
      "clipName": "walk",
      "coordinates": [0.5, 1.0],
      "weight": 1.0
    },
    {
      "clipName": "run",
      "coordinates": [1.0, 1.0],
      "weight": 1.0
    }
  ]
}
]]

local jsonBlendSpace = AnimationAssetUtils.createBlendSpaceFromJSON(blendSpaceJSON)
if jsonBlendSpace then
    print("Successfully created blend space from JSON")
    print("  Name:", jsonBlendSpace.name)
    print("  Type:", jsonBlendSpace.type == "OneD" and "1D" or "2D")
    print("  Sample count:", #jsonBlendSpace.samples)
    print("  Valid:", jsonBlendSpace:validate())
else
    print("Failed to create blend space from JSON")
end

-- Example 6: Integration with existing OpenStarbound systems
print("\n--- Example 6: Integration with Existing OpenStarbound Systems ---")

-- Simulate integration with entity system
local function setupEntityAnimation(entityType, entityId)
    print("Setting up animation for entity:", entityType, entityId)
    
    -- Load appropriate assets based on entity type
    local skeletonPath = "assets/skeletons/" .. entityType .. ".skeleton.json"
    local skeleton = AnimationAsset.loadSkeleton(skeletonPath)
    
    if skeleton then
        -- Create animation component
        local animationComponent = {
            skeleton = skeleton,
            clips = {},
            blendSpaces = {},
            proceduralLayers = {},
            currentTime = 0.0,
            currentClip = nil,
            currentBlendSpace = nil
        }
        
        -- Load common clips for this entity type
        local commonClips = {"idle", "walk", "run", "attack", "death"}
        for _, clipName in ipairs(commonClips) do
            local clipPath = "assets/animations/" .. entityType .. "_" .. clipName .. ".animbin"
            local clip = AnimationAsset.loadAnimationClip(clipPath)
            if clip then
                animationComponent.clips[clipName] = clip
            end
        end
        
        -- Load blend spaces
        local locomotionBS = AnimationAsset.loadBlendSpace("assets/animations/" .. entityType .. "_locomotion.blendspace")
        if locomotionBS then
            animationComponent.blendSpaces["locomotion"] = locomotionBS
        end
        
        -- Load procedural layers
        local ikLayer = AnimationAsset.loadProceduralLayer("assets/animations/" .. entityType .. "_ik.proclayer")
        if ikLayer then
            table.insert(animationComponent.proceduralLayers, ikLayer)
        end
        
        local noiseLayer = AnimationAsset.loadProceduralLayer("assets/animations/" .. entityType .. "_noise.proclayer")
        if noiseLayer then
            table.insert(animationComponent.proceduralLayers, noiseLayer)
        end
        
        print("  Animation component created")
        print("    Clips loaded:", #animationComponent.clips)
        print("    Blend spaces loaded:", #animationComponent.blendSpaces)
        print("    Procedural layers loaded:", #animationComponent.proceduralLayers)
        
        return animationComponent
    else
        print("  Failed to load skeleton for entity type:", entityType)
        return nil
    end
end

-- Simulate entity animation update
local function updateEntityAnimation(animationComponent, entityState, deltaTime)
    if not animationComponent then return end
    
    -- Update animation time
    animationComponent.currentTime = animationComponent.currentTime + deltaTime
    
    -- Determine current animation based on entity state
    local currentClip = nil
    if entityState.isDead then
        currentClip = animationComponent.clips["death"]
    elseif entityState.isAttacking then
        currentClip = animationComponent.clips["attack"]
    elseif entityState.velocity:length() > 0.1 then
        -- Use blend space for locomotion
        local locomotionBS = animationComponent.blendSpaces["locomotion"]
        if locomotionBS then
            local speed = entityState.velocity:length()
            local direction = entityState.velocity:normalize()
            local weights = locomotionBS:evaluateWeights(glm.vec2(speed, direction.x))
            
            -- Blend between walk and run based on speed
            local walkWeight = math.max(0, 1 - speed)
            local runWeight = math.min(1, speed)
            
            local walkClip = animationComponent.clips["walk"]
            local runClip = animationComponent.clips["run"]
            
            if walkClip and runClip then
                local walkPose = walkClip:samplePose(animationComponent.currentTime, true)
                local runPose = runClip:samplePose(animationComponent.currentTime, true)
                
                -- Blend poses
                local finalPose = {}
                for i, walkTransform in ipairs(walkPose) do
                    local runTransform = runPose[i] or glm.mat4(1.0f)
                    finalPose[i] = walkTransform * walkWeight + runTransform * runWeight
                end
                
                -- Apply procedural layers
                for _, layer in ipairs(animationComponent.proceduralLayers) do
                    if layer:isEnabled() then
                        layer:apply(finalPose, deltaTime)
                    end
                end
                
                return finalPose
            end
        end
    else
        currentClip = animationComponent.clips["idle"]
    end
    
    -- Use single clip if no blend space
    if currentClip then
        local pose = currentClip:samplePose(animationComponent.currentTime, true)
        
        -- Apply procedural layers
        for _, layer in ipairs(animationComponent.proceduralLayers) do
            if layer:isEnabled() then
                layer:apply(pose, deltaTime)
            end
        end
        
        return pose
    end
    
    return {}
end

-- Example 7: Performance monitoring and optimization
print("\n--- Example 7: Performance Monitoring and Optimization ---")

-- Set cache size for performance
AnimationAsset.setCacheSize(500)
print("Cache size set to 500")

-- Monitor performance during intensive operations
local startTime = os.clock()
for i = 1, 100 do
    local skeleton = AnimationAsset.loadSkeleton("assets/skeletons/test_skeleton_" .. i .. ".skeleton.json")
    local clip = AnimationAsset.loadAnimationClip("assets/animations/test_clip_" .. i .. ".animbin")
    
    if skeleton and clip then
        -- Simulate animation update
        local pose = clip:samplePose(0.5, true)
        if #pose > 0 then
            print("  Processed animation", i, "with", #pose, "transforms")
        end
    end
end
local endTime = os.clock()
print("Performance test completed in", (endTime - startTime) * 1000, "ms")

-- Get final statistics
local finalStats = AnimationAsset.getStats()
print("Final Asset Manager Statistics:")
print("  Loaded skeletons:", finalStats.loadedSkeletons)
print("  Loaded animation clips:", finalStats.loadedAnimationClips)
print("  Loaded blend spaces:", finalStats.loadedBlendSpaces)
print("  Loaded procedural layers:", finalStats.loadedProceduralLayers)
print("  Cache hits:", finalStats.cacheHits)
print("  Cache misses:", finalStats.cacheMisses)
print("  Average load time:", finalStats.averageLoadTime, "ms")

-- Example 8: Hot reload testing
print("\n--- Example 8: Hot Reload Testing ---")

if AnimationAsset.isHotReloadEnabled() then
    print("Hot reload is enabled")
    print("Watched directories:")
    -- This would show watched directories in a real implementation
    
    -- Simulate file change
    print("Simulating asset file change...")
    -- In a real implementation, this would trigger the hot reload system
else
    print("Hot reload is disabled")
end

-- Example 9: Asset validation and error handling
print("\n--- Example 9: Asset Validation and Error Handling ---")

-- Test asset validation
local testAssets = {
    skeleton = AnimationAsset.createSkeleton("test_skeleton"),
    clip = AnimationAsset.createAnimationClip("test_clip"),
    blendSpace = AnimationAsset.createBlendSpace("test_blendspace", "OneD"),
    layer = AnimationAsset.createProceduralLayer("test_layer", "IK")
}

for assetType, asset in pairs(testAssets) do
    if asset then
        local isValid = AnimationAssetUtils["validate" .. assetType:sub(1,1):upper() .. assetType:sub(2)](asset)
        print("  " .. assetType .. " validation:", isValid and "PASS" or "FAIL")
    else
        print("  " .. assetType .. " creation: FAIL")
    end
end

-- Example 10: Cleanup and shutdown
print("\n--- Example 10: Cleanup and Shutdown ---")

-- Unload all assets
AnimationAsset.unloadAllAssets()
print("All assets unloaded")

-- Clear cache
AnimationAsset.clearCache()
print("Cache cleared")

-- Reset statistics
AnimationAsset.resetStats()
print("Statistics reset")

-- Disable hot reload
AnimationAsset.enableHotReload(false)
print("Hot reload disabled")

print("\n=== OpenStarbound Animation Asset Integration Example Complete ===")

-- Return the system for further use
return {
    AnimationAsset = AnimationAsset,
    AnimationAssetUtils = AnimationAssetUtils,
    setupEntityAnimation = setupEntityAnimation,
    updateEntityAnimation = updateEntityAnimation,
    onEntitySpawn = onEntitySpawn,
    onEntityUpdate = onEntityUpdate
} 