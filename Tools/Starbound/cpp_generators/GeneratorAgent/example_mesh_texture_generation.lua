-- Mesh Texture Generation Pipeline Example
-- Demonstrates creating pixel-art textures from 3D meshes for Starbound

require("textures")

-- Example 1: Basic texture baking for a crossbow bolt
function bakeCrossbowBoltTexture()
    local settings = TextureUtils.createBakeSettings({
        resolution = 64,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = false,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3},
        contrast = 1.1,
        saturation = 1.0,
        brightness = 1.0
    })
    
    local result = MeshTexture.bakeOffline("models/bolts/bolt_steel.glb", settings)
    
    if result.success then
        print("Bolt texture baked successfully!")
        print("Bake time: " .. result.bakeTime .. " seconds")
        
        -- Export the texture
        MeshTexture.exportAtlasAsPNG(result.atlas, "textures/bolts/bolt_steel.png")
        MeshTexture.exportAtlasAsJSON(result.atlas, "textures/bolts/bolt_steel.json")
        
        return result.atlas
    else
        print("Bake failed: " .. result.errorMessage)
        return nil
    end
end

-- Example 2: In-engine baking for real-time texture generation
function bakeMeshInEngine(meshAsset)
    local settings = TextureUtils.createBakeSettings({
        resolution = 128,
        directions = 4,
        paletteName = "starbound_warm",
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = true,
        lightIntensity = 0.8,
        lightDirection = {0.5, 0.8, 0.2},
        ambientColor = {0.4, 0.3, 0.2},
        contrast = 1.2,
        saturation = 0.9,
        brightness = 1.1
    })
    
    local result = MeshTexture.bakeInEngine(meshAsset, settings)
    
    if result.success then
        print("In-engine bake successful!")
        print("Bake time: " .. result.bakeTime .. " seconds")
        
        -- Cache the result for reuse
        local key = "mesh_" .. meshAsset.name .. "_" .. settings.resolution .. "_" .. settings.directions
        MeshTexture.cacheAtlas(key, result.atlas)
        
        return result.atlas
    else
        print("In-engine bake failed: " .. result.errorMessage)
        return nil
    end
end

-- Example 3: Batch baking for multiple meshes
function bakeMeshBatch()
    local meshPaths = {
        "models/weapons/sword_steel.glb",
        "models/weapons/axe_iron.glb",
        "models/weapons/mace_gold.glb",
        "models/armor/helmet_steel.glb",
        "models/armor/chestplate_iron.glb"
    }
    
    local settings = TextureUtils.createBakeSettings({
        resolution = 64,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = false,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    print("Starting batch bake of " .. #meshPaths .. " meshes...")
    local results = MeshTexture.bakeBatch(meshPaths, settings)
    
    local successCount = 0
    for i, result in ipairs(results) do
        if result.success then
            successCount = successCount + 1
            print("Baked " .. meshPaths[i] .. " successfully")
            
            -- Export each texture
            local filename = string.gsub(meshPaths[i], "models/", "textures/")
            filename = string.gsub(filename, "%.glb$", ".png")
            MeshTexture.exportAtlasAsPNG(result.atlas, filename)
        else
            print("Failed to bake " .. meshPaths[i] .. ": " .. result.errorMessage)
        end
    end
    
    print("Batch bake completed: " .. successCount .. "/" .. #meshPaths .. " successful")
    return results
end

-- Example 4: Custom palette creation and usage
function createCustomPalette()
    local customColors = {
        {0.0, 0.0, 0.0, 1.0},       -- Black
        {0.2, 0.1, 0.0, 1.0},       -- Dark brown
        {0.4, 0.2, 0.0, 1.0},       -- Brown
        {0.6, 0.3, 0.0, 1.0},       -- Light brown
        {0.8, 0.4, 0.0, 1.0},       -- Orange brown
        {1.0, 0.5, 0.0, 1.0},       -- Orange
        {1.0, 0.7, 0.0, 1.0},       -- Yellow orange
        {1.0, 0.9, 0.0, 1.0},       -- Yellow
        {0.8, 0.8, 0.0, 1.0},       -- Olive
        {0.6, 0.6, 0.0, 1.0},       -- Dark olive
        {0.4, 0.4, 0.0, 1.0},       -- Very dark olive
        {0.2, 0.2, 0.0, 1.0},       -- Almost black olive
        {0.5, 0.3, 0.1, 1.0},       -- Red brown
        {0.7, 0.4, 0.1, 1.0},       -- Light red brown
        {0.9, 0.5, 0.1, 1.0},       -- Very light red brown
        {0.3, 0.2, 0.1, 1.0},       -- Dark red brown
        {0.1, 0.1, 0.0, 1.0},       -- Very dark brown
        {0.6, 0.4, 0.2, 1.0},       -- Tan
        {0.8, 0.6, 0.3, 1.0},       -- Light tan
        {0.4, 0.3, 0.2, 1.0},       -- Dark tan
        {0.2, 0.1, 0.1, 1.0},       -- Very dark tan
        {0.9, 0.7, 0.4, 1.0},       -- Cream
        {0.7, 0.5, 0.3, 1.0},       -- Dark cream
        {0.0, 0.0, 0.0, 0.0}        -- Transparent
    }
    
    local customPalette = TextureUtils.createPalette("custom_warm", customColors)
    
    -- Register the palette
    MeshTexture.loadPaletteFromJSON("custom_warm", customPalette:toJSON())
    
    return customPalette
end

-- Example 5: Runtime texture generation for dynamic content
function generateRuntimeTexture(meshPath, paletteName)
    local settings = TextureUtils.createBakeSettings({
        resolution = 32,
        directions = 4,
        paletteName = paletteName,
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = false,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    local result = MeshTexture.bakeRuntime(meshPath, settings)
    
    if result.success then
        print("Runtime texture generated successfully!")
        
        -- Use the texture immediately
        local textureId = result.atlas.gpuTexture
        return textureId
    else
        print("Runtime generation failed: " .. result.errorMessage)
        return nil
    end
end

-- Example 6: Advanced texture baking with multiple passes
function bakeAdvancedTexture(meshPath)
    -- First pass: Generate base texture
    local baseSettings = TextureUtils.createBakeSettings({
        resolution = 128,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = false,
        useAmbientOcclusion = true,
        useEmissive = false,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    local baseResult = MeshTexture.bakeOffline(meshPath, baseSettings)
    
    if not baseResult.success then
        print("Base texture bake failed: " .. baseResult.errorMessage)
        return nil
    end
    
    -- Second pass: Generate emissive texture
    local emissiveSettings = TextureUtils.createBakeSettings({
        resolution = 128,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = false,
        useAmbientOcclusion = false,
        useEmissive = true,
        lightIntensity = 0.0,
        lightDirection = {0.0, 0.0, 0.0},
        ambientColor = {0.0, 0.0, 0.0}
    })
    
    local emissiveResult = MeshTexture.bakeOffline(meshPath, emissiveSettings)
    
    if not emissiveResult.success then
        print("Emissive texture bake failed: " .. emissiveResult.errorMessage)
        return baseResult.atlas
    end
    
    -- Combine the textures
    local combinedAtlas = baseResult.atlas
    -- TODO: Implement texture combination logic
    
    print("Advanced texture baking completed!")
    return combinedAtlas
end

-- Example 7: Texture optimization and caching
function optimizeTextureGeneration()
    -- Load commonly used palettes
    MeshTexture.loadPalette("starbound_default", "palettes/starbound_default.json")
    MeshTexture.loadPalette("starbound_warm", "palettes/starbound_warm.json")
    MeshTexture.loadPalette("starbound_cool", "palettes/starbound_cool.json")
    
    -- Pre-bake common meshes
    local commonMeshes = {
        "models/weapons/sword_steel.glb",
        "models/weapons/axe_iron.glb",
        "models/armor/helmet_steel.glb"
    }
    
    local settings = TextureUtils.createBakeSettings({
        resolution = 64,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = true,
        useAmbientOcclusion = true
    })
    
    for _, meshPath in ipairs(commonMeshes) do
        local result = MeshTexture.bakeOffline(meshPath, settings)
        if result.success then
            local key = "prebaked_" .. string.gsub(meshPath, "/", "_")
            MeshTexture.cacheAtlas(key, result.atlas)
            print("Pre-baked and cached: " .. meshPath)
        end
    end
    
    print("Texture optimization completed!")
end

-- Example 8: Integration with crossbow bolt system
function generateBoltTextures()
    local boltMeshes = {
        "models/bolts/bolt_steel.glb",
        "models/bolts/bolt_explosive.glb",
        "models/bolts/bolt_frost.glb",
        "models/bolts/bolt_lightning.glb",
        "models/bolts/bolt_piercing.glb",
        "models/bolts/bolt_homing.glb",
        "models/bolts/bolt_arcane.glb"
    }
    
    local settings = TextureUtils.createBakeSettings({
        resolution = 64,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = true,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    local boltTextures = {}
    
    for _, meshPath in ipairs(boltMeshes) do
        local result = MeshTexture.bakeOffline(meshPath, settings)
        if result.success then
            local boltName = string.match(meshPath, "bolt_(%w+)%.glb")
            boltTextures[boltName] = result.atlas
            
            -- Export texture
            local texturePath = "textures/bolts/" .. boltName .. ".png"
            MeshTexture.exportAtlasAsPNG(result.atlas, texturePath)
            
            print("Generated texture for " .. boltName .. " bolt")
        end
    end
    
    return boltTextures
end

-- Example 9: Performance monitoring
function monitorTexturePerformance()
    local stats = MeshTexture.getStats()
    
    print("Texture Generation Statistics:")
    print("  Total bakes: " .. stats.totalBakes)
    print("  Offline bakes: " .. stats.offlineBakes)
    print("  Engine bakes: " .. stats.engineBakes)
    print("  Cache hits: " .. stats.cacheHits)
    print("  Cache misses: " .. stats.cacheMisses)
    print("  Average bake time: " .. stats.averageBakeTime .. " seconds")
    print("  Total bake time: " .. stats.totalBakeTime .. " seconds")
    print("  Atlas cache size: " .. MeshTexture.getAtlasCacheSize())
    
    -- Performance recommendations
    if stats.cacheMisses > stats.cacheHits then
        print("Recommendation: Consider pre-baking more textures")
    end
    
    if stats.averageBakeTime > 1.0 then
        print("Recommendation: Consider reducing resolution or directions")
    end
    
    if MeshTexture.getAtlasCacheSize() > 100 then
        print("Recommendation: Consider clearing cache to free memory")
        MeshTexture.clearAtlasCache()
    end
end

-- Example 10: Custom shader integration
function bakeWithCustomShader(meshPath, shaderPath)
    local settings = TextureUtils.createBakeSettings({
        resolution = 128,
        directions = 8,
        paletteName = "starbound_default",
        useDithering = true,
        useAmbientOcclusion = true,
        useEmissive = true,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    -- Load custom shader
    -- TODO: Implement custom shader loading
    
    local result = MeshTexture.bakeOffline(meshPath, settings)
    
    if result.success then
        print("Custom shader bake successful!")
        return result.atlas
    else
        print("Custom shader bake failed: " .. result.errorMessage)
        return nil
    end
end

-- Example 11: Palette switching for day/night cycles
function switchPaletteForTimeOfDay()
    local currentTime = world:getTimeOfDay()
    local paletteName = "starbound_default"
    
    if currentTime < 0.25 or currentTime > 0.75 then
        -- Night time - use cooler palette
        paletteName = "starbound_cool"
    elseif currentTime > 0.4 and currentTime < 0.6 then
        -- Day time - use warmer palette
        paletteName = "starbound_warm"
    end
    
    -- Re-bake textures with new palette
    local settings = TextureUtils.createBakeSettings({
        resolution = 64,
        directions = 8,
        paletteName = paletteName,
        useDithering = true,
        useAmbientOcclusion = true,
        lightIntensity = 1.0,
        lightDirection = {0.7, 0.7, 0.0},
        ambientColor = {0.3, 0.3, 0.3}
    })
    
    -- Re-bake active meshes
    local activeMeshes = MeshManager.getActiveMeshes()
    for _, mesh in ipairs(activeMeshes) do
        local result = MeshTexture.bakeRuntime(mesh.path, settings)
        if result.success then
            mesh:updateTexture(result.atlas)
        end
    end
    
    print("Switched to " .. paletteName .. " palette for time of day")
end

-- Example 12: Texture quality comparison
function compareTextureQuality(meshPath)
    local resolutions = {32, 64, 128, 256}
    local directions = {1, 4, 8}
    
    for _, resolution in ipairs(resolutions) do
        for _, direction in ipairs(directions) do
            local settings = TextureUtils.createBakeSettings({
                resolution = resolution,
                directions = direction,
                paletteName = "starbound_default",
                useDithering = true,
                useAmbientOcclusion = true,
                lightIntensity = 1.0,
                lightDirection = {0.7, 0.7, 0.0},
                ambientColor = {0.3, 0.3, 0.3}
            })
            
            local result = MeshTexture.bakeOffline(meshPath, settings)
            if result.success then
                local filename = string.format("textures/comparison/%dx%d_%ddir.png", 
                                             resolution, resolution, direction)
                MeshTexture.exportAtlasAsPNG(result.atlas, filename)
                print("Generated comparison texture: " .. filename .. " (bake time: " .. result.bakeTime .. "s)")
            end
        end
    end
end

-- Main usage example
function main()
    print("Mesh Texture Generation Pipeline Example")
    print("========================================")
    
    -- Initialize the texture generator
    MeshTextureGenerator:initialize()
    
    -- Load default palettes
    local defaultPalette = Palettes.starboundDefault()
    local warmPalette = Palettes.starboundWarm()
    local coolPalette = Palettes.starboundCool()
    
    MeshTexture.loadPaletteFromJSON("starbound_default", defaultPalette:toJSON())
    MeshTexture.loadPaletteFromJSON("starbound_warm", warmPalette:toJSON())
    MeshTexture.loadPaletteFromJSON("starbound_cool", coolPalette:toJSON())
    
    -- Example usage
    print("1. Baking crossbow bolt texture...")
    local boltTexture = bakeCrossbowBoltTexture()
    
    print("2. Generating bolt textures...")
    local boltTextures = generateBoltTextures()
    
    print("3. Optimizing texture generation...")
    optimizeTextureGeneration()
    
    print("4. Monitoring performance...")
    monitorTexturePerformance()
    
    print("Texture generation examples completed!")
    print("Generated textures saved to textures/ directory")
end

-- Run the example
main() 