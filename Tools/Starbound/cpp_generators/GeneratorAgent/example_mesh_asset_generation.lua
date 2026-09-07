-- Updated Mesh Asset Generation Pipeline Example
-- Demonstrates procedurally creating, optimizing, and streaming 3D mesh assets
-- Now integrated with the new mesh system

local MeshAsset = require("MeshAsset")
local MeshAssetUtils = require("MeshAssetUtils")
local MeshAssetPresets = require("MeshAssetPresets")

-- Initialize the mesh asset factory with the new system
MeshAsset.initialize(4) -- 4 threads

-- Enable performance monitoring
MeshAsset.enablePerformanceMonitoring(true)
MeshAsset.setPerformanceThresholds(100.0, 50.0) -- 100ms generation, 50ms load

print("=== Updated Mesh Asset Generation Pipeline Example ===")
print("Using new mesh system integration")

-- Example 1: Basic primitive mesh generation with new system
print("\n--- Example 1: Basic Primitive Mesh Generation (New System) ---")
local cubeParams = MeshAssetPresets.cube({2.0, 2.0, 2.0})
if MeshAssetUtils.validateMeshParams(cubeParams) then
    local bundle = MeshAsset.generateSync(cubeParams)
    if bundle.isValid then
        print("Successfully generated cube mesh with new system")
        print("  Asset ID:", bundle.assetId)
        print("  Memory Usage:", bundle.memoryUsage, "bytes")
        print("  Generation Time:", bundle.generationTime, "seconds")
    else
        print("Failed to generate cube mesh:", bundle.errorMessage)
    end
else
    print("Invalid cube parameters")
end

-- Example 2: Sphere with advanced features
print("\n--- Example 2: Sphere with Advanced Features ---")
local sphereParams = MeshAssetPresets.sphere(1.0, 32)
sphereParams.optimizeMesh = true
sphereParams.cacheResult = true

-- Add material
sphereParams.materialParams = MeshAssetPresets.pbrMetal()

-- Add UV generation
sphereParams.uvParams = MeshAssetPresets.optimizedUV()

if MeshAssetUtils.validateMeshParams(sphereParams) then
    local bundle = MeshAsset.generateSync(sphereParams)
    if bundle.isValid then
        print("Successfully generated sphere with material and UVs")
        print("  Asset ID:", bundle.assetId)
        print("  Memory Usage:", bundle.memoryUsage, "bytes")
        print("  Generation Time:", bundle.generationTime, "seconds")
    else
        print("Failed to generate sphere:", bundle.errorMessage)
    end
else
    print("Invalid sphere parameters")
end

-- Example 3: Terrain mesh with LOD
print("\n--- Example 3: Terrain Mesh with LOD (New System) ---")
local terrainParams = MeshAssetPresets.terrain({100.0, 100.0}, 256)
local lodParams = MeshAssetPresets.standardLOD()
lodParams.baseMeshId = terrainParams.id

-- Combine parameters
terrainParams.lodParams = lodParams

if MeshAssetUtils.validateMeshParams(terrainParams) and MeshAssetUtils.validateLODParams(lodParams) then
    local bundle = MeshAsset.generateSync(terrainParams)
    if bundle.isValid then
        print("Successfully generated terrain mesh with LOD")
        print("  Asset ID:", bundle.assetId)
        print("  Memory Usage:", bundle.memoryUsage, "bytes")
        print("  LOD Count:", #bundle.lods)
    else
        print("Failed to generate terrain mesh:", bundle.errorMessage)
    end
else
    print("Invalid terrain or LOD parameters")
end

-- Example 4: Procedural mesh with custom parameters
print("\n--- Example 4: Procedural Mesh with Custom Parameters ---")
local customParams = MeshAssetUtils.createMeshParams({
    id = "custom_cylinder",
    type = "procedural",
    meshParams = {
        type = "Cylinder",
        dimensions = {2.0, 3.0, 2.0},
        subdivisions = 24,
        generateNormals = true,
        generateUVs = true,
        weldVertices = true
    },
    materialParams = {
        id = "custom_material",
        shaderType = "PBR",
        albedo = {0.6, 0.5, 0.4, 1.0},
        metallic = 0.8,
        roughness = 0.3
    },
    uvParams = {
        atlasSize = {1024, 1024},
        padding = 4.0,
        texelDensity = 1.5
    }
})

if MeshAssetUtils.validateMeshParams(customParams) then
    local bundle = MeshAsset.generateSync(customParams)
    if bundle.isValid then
        print("Successfully generated custom cylinder mesh")
        print("  Asset ID:", bundle.assetId)
        print("  Memory Usage:", bundle.memoryUsage, "bytes")
    else
        print("Failed to generate custom cylinder mesh:", bundle.errorMessage)
    end
else
    print("Invalid custom parameters")
end

-- Example 5: Async mesh generation with new system
print("\n--- Example 5: Async Mesh Generation (New System) ---")
local sphereParams = MeshAssetPresets.sphere(0.5, 16)
if MeshAssetUtils.validateMeshParams(sphereParams) then
    local future = MeshAsset.generateAsync(sphereParams)
    print("Async mesh generation started for sphere")
    
    -- In a real application, you would wait for the future to complete
    -- For this example, we'll just log that it was started
end

-- Example 6: Batch generation with new system
print("\n--- Example 6: Batch Mesh Generation (New System) ---")
local meshParamsList = {
    MeshAssetPresets.cube({1.0, 1.0, 1.0}),
    MeshAssetPresets.sphere(0.5, 16),
    MeshAssetPresets.cylinder(0.3, 1.0, 16)
}

-- Set unique IDs for batch generation
for i, params in ipairs(meshParamsList) do
    params.id = "batch_mesh_" .. i
end

local futures = MeshAsset.generateBatch(meshParamsList)
print("Started batch generation for", #futures, "meshes")

-- Example 7: Material variations with new system
print("\n--- Example 7: Material Variations (New System) ---")

-- Metal material
local metalMaterial = MeshAssetPresets.pbrMetal()
local cubeParams = MeshAssetPresets.cube({1.0, 1.0, 1.0})
cubeParams.materialParams = metalMaterial
cubeParams.id = "metal_cube"

local bundle1 = MeshAsset.generateSync(cubeParams)
print("Metal material generation:", bundle1.isValid and "success" or "failed")

-- Plastic material
local plasticMaterial = MeshAssetPresets.pbrPlastic()
cubeParams.materialParams = plasticMaterial
cubeParams.id = "plastic_cube"

local bundle2 = MeshAsset.generateSync(cubeParams)
print("Plastic material generation:", bundle2.isValid and "success" or "failed")

-- Wood material
local woodMaterial = MeshAssetPresets.pbrWood()
cubeParams.materialParams = woodMaterial
cubeParams.id = "wood_cube"

local bundle3 = MeshAsset.generateSync(cubeParams)
print("Wood material generation:", bundle3.isValid and "success" or "failed")

-- Example 8: LOD variations with new system
print("\n--- Example 8: LOD Variations (New System) ---")

-- Standard LOD
local standardLOD = MeshAssetPresets.standardLOD()
local terrainParams = MeshAssetPresets.terrain({50.0, 50.0}, 128)
terrainParams.lodParams = standardLOD
terrainParams.id = "terrain_standard_lod"

local bundle1 = MeshAsset.generateSync(terrainParams)
print("Standard LOD generation:", bundle1.isValid and "success" or "failed")

-- Aggressive LOD
local aggressiveLOD = MeshAssetPresets.aggressiveLOD()
terrainParams.lodParams = aggressiveLOD
terrainParams.id = "terrain_aggressive_lod"

local bundle2 = MeshAsset.generateSync(terrainParams)
print("Aggressive LOD generation:", bundle2.isValid and "success" or "failed")

-- Example 9: Procedural mesh generation with new system
print("\n--- Example 9: Procedural Mesh Generation (New System) ---")

-- Generate a series of spheres with different parameters
for i = 1, 5 do
    local sphereParams = MeshAssetPresets.proceduralSphere(i * 0.2, 8 + i * 4)
    sphereParams.id = "procedural_sphere_" .. i
    
    local bundle = MeshAsset.generateSync(sphereParams)
    print("Procedural sphere", i, "generation:", bundle.isValid and "success" or "failed")
end

-- Example 10: Performance monitoring with new system
print("\n--- Example 10: Performance Monitoring (New System) ---")
local stats = MeshAsset.getStats()
print("Mesh Asset Factory Statistics:")
print("  Total assets:", stats.totalAssets)
print("  Generated assets:", stats.generatedAssets)
print("  Cached assets:", stats.cachedAssets)
print("  Failed assets:", stats.failedAssets)
print("  Average generation time:", stats.averageGenerationTime, "ms")
print("  Average load time:", stats.averageLoadTime, "ms")
print("  Total async jobs:", stats.totalAsyncJobs)
print("  Completed jobs:", stats.completedJobs)
print("  Failed jobs:", stats.failedJobs)
print("  Total memory usage:", stats.totalMemoryUsage, "bytes")

-- Example 11: Cache management with new system
print("\n--- Example 11: Cache Management (New System) ---")
print("Current cache size:", MeshAsset.getCacheSize())
print("Max cache size:", MeshAsset.getMaxCacheSize())
print("Cache hit rate:", string.format("%.2f%%", MeshAsset.getCacheHitRate() * 100))

-- Set new cache size
MeshAsset.setCacheSize(500)
print("Cache size set to 500")

-- Example 12: Asset validation and error handling with new system
print("\n--- Example 12: Asset Validation and Error Handling (New System) ---")

-- Try to create invalid mesh parameters
local invalidParams = MeshAssetUtils.createMeshParams({
    id = "", -- Empty ID should fail validation
    type = "Primitive",
    meshParams = {
        dimensions = {0.0, 0.0, 0.0}, -- Zero dimensions should fail
        subdivisions = 0 -- Zero subdivisions should fail
    }
})

if not MeshAssetUtils.validateMeshParams(invalidParams) then
    print("Correctly detected invalid mesh parameters")
end

-- Try to create invalid LOD parameters
local invalidLOD = MeshAssetUtils.createMeshParams({
    lodParams = {
        baseMeshId = "", -- Empty base mesh ID should fail
        screenSizes = {}, -- Empty screen sizes should fail
        targetRatios = {1.0, 0.5}, -- Mismatched sizes should fail
        maxTriangles = 0 -- Zero triangles should fail
    }
})

if not MeshAssetUtils.validateLODParams(invalidLOD.lodParams) then
    print("Correctly detected invalid LOD parameters")
end

-- Example 13: Different mesh types with new system
print("\n--- Example 13: Different Mesh Types (New System) ---")

-- Primitive mesh
local primitiveParams = MeshAssetPresets.cube({1.0, 1.0, 1.0})
primitiveParams.id = "test_primitive"
local bundle1 = MeshAsset.generateSync(primitiveParams)
print("Primitive mesh generation:", bundle1.isValid and "success" or "failed")

-- Terrain mesh
local terrainParams = MeshAssetPresets.mountain({100.0, 100.0}, 256)
terrainParams.id = "test_terrain"
local bundle2 = MeshAsset.generateSync(terrainParams)
print("Terrain mesh generation:", bundle2.isValid and "success" or "failed")

-- Procedural mesh
local proceduralParams = MeshAssetPresets.proceduralCube({1.5, 1.5, 1.5})
proceduralParams.id = "test_procedural"
local bundle3 = MeshAsset.generateSync(proceduralParams)
print("Procedural mesh generation:", bundle3.isValid and "success" or "failed")

-- Example 14: Asset management with new system
print("\n--- Example 14: Asset Management (New System) ---")

-- Check if specific assets are loaded
local assetId = "cube"
if MeshAsset.isAssetLoaded(assetId) then
    print("Asset is loaded:", assetId)
    local asset = MeshAsset.getAsset(assetId)
    if asset.isValid then
        print("Asset retrieved successfully")
    end
else
    print("Asset not loaded:", assetId)
end

-- Get loaded asset IDs
local loadedIds = MeshAsset.getLoadedAssetIds()
print("Loaded asset IDs:", table.concat(loadedIds, ", "))

-- Example 15: Memory usage monitoring with new system
print("\n--- Example 15: Memory Usage Monitoring (New System) ---")
local totalMemory = MeshAsset.getTotalMemoryUsage()
print("Total memory usage:", totalMemory, "bytes")
print("Total memory usage (MB):", string.format("%.2f", totalMemory / (1024 * 1024)))

-- Example 16: Asset comparison with new system
print("\n--- Example 16: Asset Comparison (New System) ---")

-- Generate two similar assets
local sphere1 = MeshAssetPresets.sphere(1.0, 16)
sphere1.id = "sphere1"
local bundle1 = MeshAsset.generateSync(sphere1)

local sphere2 = MeshAssetPresets.sphere(1.0, 16)
sphere2.id = "sphere2"
local bundle2 = MeshAsset.generateSync(sphere2)

-- Compare assets
local areEqual = MeshAssetUtils.compareAssets(bundle1, bundle2)
print("Assets are equal:", areEqual)

local similarity = MeshAssetUtils.calculateSimilarity(bundle1, bundle2)
print("Asset similarity:", string.format("%.2f%%", similarity * 100))

-- Example 17: Integration with existing systems
print("\n--- Example 17: Integration with Existing Systems (New System) ---")

-- This would integrate with your existing mesh systems
-- For example, converting between different mesh formats
local convertToMeshAsset = function(existingMeshDef)
    local meshParams = MeshAssetUtils.createMeshParams({
        id = existingMeshDef.id .. "_converted",
        type = existingMeshDef.type or "Primitive",
        meshParams = {
            dimensions = existingMeshDef.dimensions or {1.0, 1.0, 1.0},
            subdivisions = existingMeshDef.subdivisions or 1,
            generateNormals = existingMeshDef.generateNormals or true,
            generateUVs = existingMeshDef.generateUVs or true
        }
    })
    return meshParams
end

print("Integration utilities available")

-- Example 18: Performance optimization with new system
print("\n--- Example 18: Performance Optimization (New System) ---")

-- Set stricter performance thresholds
MeshAsset.setPerformanceThresholds(50.0, 25.0) -- 50ms generation, 25ms load

-- Monitor performance during intensive operations
for i = 1, 10 do
    local params = MeshAssetUtils.createMeshParams({
        id = "performance_test_" .. i,
        type = "procedural",
        meshParams = {
            type = "Sphere",
            dimensions = {math.random() * 2 + 0.5, math.random() * 2 + 0.5, math.random() * 2 + 0.5},
            subdivisions = math.random(8, 32),
            generateNormals = true,
            generateUVs = true
        }
    })
    
    local bundle = MeshAsset.generateSync(params)
    if bundle.isValid then
        print("Performance test", i, "completed successfully")
    else
        print("Performance test", i, "failed:", bundle.errorMessage)
    end
end

-- Example 19: Asset management with new system
print("\n--- Example 19: Asset Management (New System) ---")

-- Check if specific assets are loaded
local assetId = "cube"
if MeshAsset.isAssetLoaded(assetId) then
    print("Asset is loaded:", assetId)
    local asset = MeshAsset.getAsset(assetId)
    if asset.isValid then
        print("Asset retrieved successfully")
    end
else
    print("Asset not loaded:", assetId)
end

-- Example 20: Cleanup and shutdown with new system
print("\n--- Example 20: Cleanup and Shutdown (New System) ---")

-- Unload all assets
MeshAsset.unloadAllAssets()
print("All assets unloaded")

-- Clear cache
MeshAsset.clearCache()
print("Cache cleared")

-- Reset statistics
MeshAsset.resetStats()
print("Statistics reset")

-- Final statistics
local finalStats = MeshAsset.getStats()
print("Final Statistics:")
print("  Total assets:", finalStats.totalAssets)
print("  Generated assets:", finalStats.generatedAssets)
print("  Failed assets:", finalStats.failedAssets)
print("  Total async jobs:", finalStats.totalAsyncJobs)
print("  Completed jobs:", finalStats.completedJobs)
print("  Failed jobs:", finalStats.failedJobs)

print("\n=== Updated Mesh Asset Generation Pipeline Example Complete ===")
print("New mesh system integration successful!")

-- Return the system for further use
return {
    MeshAsset = MeshAsset,
    MeshAssetUtils = MeshAssetUtils,
    MeshAssetPresets = MeshAssetPresets
} 