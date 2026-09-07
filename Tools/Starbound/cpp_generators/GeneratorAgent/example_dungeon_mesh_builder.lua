-- Dungeon Mesh Builder Example
-- Demonstrates PNG-to-mesh conversion with extrusion, collision, and parallax support

require("dungeon")

-- Example 1: Basic chunk generation from tilemap
function generateBasicChunk()
    -- Create chunk definition
    local def = ChunkPresets.midground(0, 0)
    def.tileW = 32
    def.tileH = 32
    def.tileSize = 0.5
    def.thickness = 0.1
    def.generateCollision = true
    def.generateSideFaces = true
    
    -- Create simple tilemap data
    local tileArray = {}
    for y = 0, 31 do
        for x = 0, 31 do
            local index = y * 32 + x
            if y < 16 then
                tileArray[index + 1] = 1  -- Ground tiles
            else
                tileArray[index + 1] = 0  -- Air
            end
        end
    end
    
    local tilemap = DungeonUtils.createTilemapFromArray(tileArray, 32, 32)
    
    -- Create atlas layout
    local atlas = DungeonUtils.createAtlasLayout({
        atlasPath = "textures/dungeon_atlas.png",
        tileWidth = 16,
        tileHeight = 16,
        atlasWidth = 256,
        atlasHeight = 256,
        tilesPerRow = 16
    })
    
    -- Build chunk
    local result = Dungeon.buildChunk(def, tilemap, atlas)
    
    if result.success then
        print("Chunk generated successfully!")
        print("  Vertices: " .. (result.meshAsset and result.meshAsset.submeshes[1].vertexCount or 0))
        print("  Indices: " .. (result.meshAsset and result.meshAsset.submeshes[1].indexCount or 0))
        print("  Collision points: " .. #result.collisionPolygon)
        print("  Generation time: " .. result.generationTime .. "s")
        
        return result
    else
        print("Chunk generation failed: " .. result.errorMessage)
        return nil
    end
end

-- Example 2: Async chunk generation with callback
function generateChunkAsync()
    local def = ChunkPresets.foreground(1, 0)
    def.tileW = 64
    def.tileH = 64
    def.thickness = 0.15
    
    -- Load tilemap and atlas
    Dungeon.loadTilemap("cave", "data/tilemaps/cave.tmx")
    Dungeon.loadAtlas("dungeon", "textures/dungeon_atlas.png")
    
    local tilemap = Dungeon.getTilemap("cave")
    local atlas = Dungeon.getAtlas("dungeon")
    
    if not tilemap or not atlas then
        print("Failed to load tilemap or atlas")
        return
    end
    
    -- Request chunk asynchronously
    Dungeon.requestChunk(def, function(result)
        if result.success then
            print("Async chunk generated: " .. result.meshAsset.name)
            
            -- Spawn the chunk in the world
            world.spawnChunkMesh(result.meshAsset)
            
            -- Set up collision
            if #result.collisionPolygon > 0 then
                world.setChunkCollider(result.collisionPolygon)
            end
        else
            print("Async chunk failed: " .. result.errorMessage)
        end
    end)
    
    print("Chunk request submitted, processing...")
end

-- Example 3: Multi-layer parallax dungeon
function generateParallaxDungeon()
    local layers = {
        {name = "background", preset = ChunkPresets.background, offset = 0.5},
        {name = "midground", preset = ChunkPresets.midground, offset = 1.0},
        {name = "foreground", preset = ChunkPresets.foreground, offset = 1.5}
    }
    
    local tilemap = Dungeon.getTilemap("cave")
    local atlas = Dungeon.getAtlas("dungeon")
    
    if not tilemap or not atlas then
        print("Failed to load tilemap or atlas")
        return
    end
    
    -- Generate chunks for each layer
    for layerIndex, layer in ipairs(layers) do
        for chunkX = -2, 2 do
            for chunkY = -1, 1 do
                local def = layer.preset(chunkX, chunkY)
                def.tileSizeMultiplier = layer.offset
                
                -- Request chunk for this layer
                Dungeon.requestChunk(def, function(result)
                    if result.success then
                        print("Generated " .. layer.name .. " chunk (" .. chunkX .. ", " .. chunkY .. ")")
                        
                        -- Apply parallax offset
                        local parallaxOffset = (layer.offset - 1.0) * 0.5
                        world.spawnChunkMeshWithParallax(result.meshAsset, parallaxOffset)
                    end
                end)
            end
        end
    end
    
    print("Parallax dungeon generation started...")
end

-- Example 4: Batch chunk generation
function generateChunkBatch()
    local defs = {}
    
    -- Create multiple chunk definitions
    for x = -1, 1 do
        for y = -1, 1 do
            local def = ChunkPresets.midground(x, y)
            def.tileW = 32
            def.tileH = 32
            table.insert(defs, def)
        end
    end
    
    local tilemap = Dungeon.getTilemap("cave")
    local atlas = Dungeon.getAtlas("dungeon")
    
    if not tilemap or not atlas then
        print("Failed to load tilemap or atlas")
        return
    end
    
    print("Starting batch generation of " .. #defs .. " chunks...")
    
    -- Generate all chunks in parallel
    local futures = Dungeon.buildChunkBatchAsync(defs, tilemap, atlas)
    
    -- Wait for completion
    for i, future in ipairs(futures) do
        local result = future:get()
        if result.success then
            print("Batch chunk " .. i .. " completed")
            world.spawnChunkMesh(result.meshAsset)
        else
            print("Batch chunk " .. i .. " failed: " .. result.errorMessage)
        end
    end
    
    print("Batch generation completed!")
end

-- Example 5: Dynamic tilemap modification
function modifyTilemapDynamically()
    local tilemap = Dungeon.getTilemap("cave")
    if not tilemap then
        print("No tilemap loaded")
        return
    end
    
    -- Modify some tiles
    for x = 10, 15 do
        for y = 10, 15 do
            tilemap:setTile(x, y, 2) -- Set to different tile type
        end
    end
    
    -- Regenerate affected chunks
    local def = ChunkPresets.midground(0, 0)
    local atlas = Dungeon.getAtlas("dungeon")
    
    Dungeon.requestChunk(def, function(result)
        if result.success then
            print("Dynamic tilemap chunk regenerated")
            world.updateChunkMesh(result.meshAsset)
        end
    end)
end

-- Example 6: Advanced collision generation
function generateAdvancedCollision()
    local def = ChunkPresets.midground(0, 0)
    def.generateCollision = true
    def.generateSideFaces = true
    def.thickness = 0.2
    
    local tilemap = Dungeon.getTilemap("cave")
    local atlas = Dungeon.getAtlas("dungeon")
    
    if not tilemap or not atlas then
        print("Failed to load tilemap or atlas")
        return
    end
    
    -- Extract tile runs for analysis
    local runs = Dungeon.extractTileRuns(tilemap, def)
    print("Extracted " .. #runs .. " tile runs")
    
    -- Generate collision polygon
    local collisionPoly = Dungeon.generateCollisionPolygon(runs, def)
    print("Generated collision polygon with " .. #collisionPoly .. " points")
    
    -- Generate side faces
    local sideFaces = Dungeon.generateSideFaces(runs, def)
    print("Generated " .. #sideFaces .. " side faces")
    
    -- Build complete chunk
    local result = Dungeon.buildChunk(def, tilemap, atlas)
    
    if result.success then
        print("Advanced collision chunk generated")
        print("  Collision polygon points: " .. #result.collisionPolygon)
        print("  Bounding box: " .. 
              "(" .. result.boundingBoxMin.x .. ", " .. result.boundingBoxMin.y .. ", " .. result.boundingBoxMin.z .. ") to " ..
              "(" .. result.boundingBoxMax.x .. ", " .. result.boundingBoxMax.y .. ", " .. result.boundingBoxMax.z .. ")")
    end
end

-- Example 7: Performance monitoring
function monitorPerformance()
    local stats = Dungeon.getStats()
    
    print("Dungeon Mesh Builder Statistics:")
    print("  Total chunks built: " .. stats.totalChunksBuilt)
    print("  Total chunks cached: " .. stats.totalChunksCached)
    print("  Total tile runs: " .. stats.totalTileRuns)
    print("  Total quads: " .. stats.totalQuads)
    print("  Total collision polygons: " .. stats.totalCollisionPolygons)
    print("  Average build time: " .. stats.averageBuildTime .. "s")
    print("  Total build time: " .. stats.totalBuildTime .. "s")
    print("  Active jobs: " .. stats.activeJobs)
    
    -- Performance recommendations
    if stats.averageBuildTime > 0.016 then -- 16ms target
        print("Warning: Average build time exceeds 16ms target")
    end
    
    if stats.activeJobs > std.thread.hardware_concurrency() then
        print("Warning: Too many active jobs, consider reducing batch size")
    end
end

-- Example 8: Custom tilemap generation
function generateCustomTilemap()
    local width, height = 64, 64
    local tileArray = {}
    
    -- Generate procedural cave
    for y = 0, height - 1 do
        for x = 0, width - 1 do
            local index = y * width + x
            
            -- Simple cave generation
            local noise = math.sin(x * 0.1) * math.cos(y * 0.1)
            local groundLevel = 32 + noise * 8
            
            if y < groundLevel then
                if y < groundLevel - 4 then
                    tileArray[index + 1] = 3  -- Deep stone
                else
                    tileArray[index + 1] = 1  -- Surface stone
                end
            else
                tileArray[index + 1] = 0  -- Air
            end
        end
    end
    
    local tilemap = DungeonUtils.createTilemapFromArray(tileArray, width, height)
    
    -- Create chunk definitions for different layers
    local backgroundDef = ChunkPresets.background(0, 0)
    backgroundDef.tileW = 32
    backgroundDef.tileH = 32
    
    local midgroundDef = ChunkPresets.midground(0, 0)
    midgroundDef.tileW = 32
    midgroundDef.tileH = 32
    
    local atlas = Dungeon.getAtlas("dungeon")
    
    -- Generate chunks
    local backgroundResult = Dungeon.buildChunk(backgroundDef, tilemap, atlas)
    local midgroundResult = Dungeon.buildChunk(midgroundDef, tilemap, atlas)
    
    if backgroundResult.success and midgroundResult.success then
        print("Custom tilemap chunks generated successfully")
        world.spawnChunkMesh(backgroundResult.meshAsset)
        world.spawnChunkMesh(midgroundResult.meshAsset)
    end
end

-- Example 9: Hot-reload tilemap changes
function setupHotReload()
    -- Watch for tilemap file changes
    local function onTilemapChanged(filename)
        print("Tilemap changed: " .. filename)
        
        -- Reload tilemap
        if Dungeon.loadTilemap("cave", filename) then
            print("Tilemap reloaded successfully")
            
            -- Regenerate all cached chunks for this tilemap
            Dungeon.clearCacheForLayer("midground")
            Dungeon.clearCacheForLayer("foreground")
            
            -- Request regeneration of visible chunks
            for x = -1, 1 do
                for y = -1, 1 do
                    local def = ChunkPresets.midground(x, y)
                    Dungeon.requestChunk(def, function(result)
                        if result.success then
                            world.updateChunkMesh(result.meshAsset)
                        end
                    end)
                end
            end
        end
    end
    
    -- Set up file watcher (platform-specific)
    -- fileWatcher.watch("data/tilemaps/cave.tmx", onTilemapChanged)
    
    print("Hot-reload setup complete")
end

-- Example 10: Integration with existing systems
function integrateWithExistingSystems()
    -- Load tilemap and atlas
    Dungeon.loadTilemap("cave", "data/tilemaps/cave.tmx")
    Dungeon.loadAtlas("dungeon", "textures/dungeon_atlas.png")
    
    local tilemap = Dungeon.getTilemap("cave")
    local atlas = Dungeon.getAtlas("dungeon")
    
    if not tilemap or not atlas then
        print("Failed to load assets")
        return
    end
    
    -- Generate chunks for different layers
    local layers = {
        {name = "background", preset = ChunkPresets.background},
        {name = "midground", preset = ChunkPresets.midground},
        {name = "foreground", preset = ChunkPresets.foreground}
    }
    
    for _, layer in ipairs(layers) do
        local def = layer.preset(0, 0)
        
        Dungeon.requestChunk(def, function(result)
            if result.success then
                print("Generated " .. layer.name .. " layer")
                
                -- Integrate with mesh system
                if result.meshAsset then
                    MeshManager.loadMeshFromAsset(result.meshAsset)
                end
                
                -- Integrate with physics system
                if result.collisionAsset then
                    Physics.addCollisionAsset(result.collisionAsset)
                end
                
                -- Integrate with rendering system
                if result.meshAsset then
                    Renderer.addMeshToLayer(result.meshAsset, layer.name)
                end
            end
        end)
    end
    
    print("Integration with existing systems complete")
end

-- Main usage example
function main()
    print("Dungeon Mesh Builder Example")
    print("============================")
    
    -- Initialize the dungeon system
    Dungeon.update() -- Initialize if needed
    
    -- Load assets
    Dungeon.loadTilemap("cave", "data/tilemaps/cave.tmx")
    Dungeon.loadAtlas("dungeon", "textures/dungeon_atlas.png")
    
    -- Run examples
    print("1. Generating basic chunk...")
    local basicChunk = generateBasicChunk()
    
    print("2. Generating async chunk...")
    generateChunkAsync()
    
    print("3. Generating parallax dungeon...")
    generateParallaxDungeon()
    
    print("4. Generating chunk batch...")
    generateChunkBatch()
    
    print("5. Monitoring performance...")
    monitorPerformance()
    
    print("6. Generating custom tilemap...")
    generateCustomTilemap()
    
    print("7. Setting up hot-reload...")
    setupHotReload()
    
    print("8. Integrating with existing systems...")
    integrateWithExistingSystems()
    
    print("Dungeon mesh builder examples completed!")
    print("Generated chunks saved to world")
end

-- Run the example
main() 
main() 