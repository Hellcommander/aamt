-- Context-Aware Spell Generation Pipeline Example
-- Demonstrates unified spell casting for both world and dungeon contexts

require("context_spells")

-- Example 1: Basic context-aware spell casting
function castContextSpell()
    local bolt = ContextSpellPresets.worldFireBolt()
    
    -- Cast in world context
    local worldEntityId = ContextSpell.castWorld(bolt, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast world fire bolt: " .. worldEntityId)
    
    -- Cast same spell in dungeon context
    local dungeonBolt = ContextSpellPresets.dungeonIceBolt()
    local dungeonEntityId = ContextSpell.castDungeon(dungeonBolt, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast dungeon ice bolt: " .. dungeonEntityId)
    
    return {worldEntityId, dungeonEntityId}
end

-- Example 2: Custom context spell definition
function createCustomContextSpell()
    local customWorldSpell = ContextSpellUtils.createContextSpellDef({
        id = "customWorldArcaneBolt",
        context = "world",
        type = "projectile",
        sourceSprite = "icons/customArcane.png",
        meshThickness = 0.07,
        speed = 16.0,
        lifetime = 4.0,
        collisionRadius = 0.25,
        effectShader = "shaders/customArcaneGlow.glsl",
        impactEffect = "particles/customArcaneBurst.json",
        behavior = "arc",
        damage = 35,
        colorTint = {0.9, 0.4, 0.8},
        useGlow = true,
        glowColor = {0.7, 0.3, 0.6},
        glowIntensity = 0.9,
        worldLayer = "foreground",
        useParallax = true,
        parallaxOffset = 1.2,
        useWorldPhysics = true,
        worldGravityScale = 0.3,
        worldWindInfluence = 0.4,
        worldBounce = true,
        worldBounceElasticity = 0.7
    })
    
    local customDungeonSpell = ContextSpellUtils.createContextSpellDef({
        id = "customDungeonArcaneBolt",
        context = "dungeon",
        type = "projectile",
        sourceSprite = "icons/customArcane.png",
        meshThickness = 0.07,
        speed = 16.0,
        lifetime = 4.0,
        collisionRadius = 0.25,
        effectShader = "shaders/customArcaneGlow.glsl",
        impactEffect = "particles/customArcaneBurst.json",
        behavior = "arc",
        damage = 35,
        colorTint = {0.9, 0.4, 0.8},
        useGlow = true,
        glowColor = {0.7, 0.3, 0.6},
        glowIntensity = 0.9,
        dungeonLayer = 2, -- foreground
        dungeonUseChunkCollision = true,
        dungeonUseSideScrollPhysics = true,
        dungeonScrollSpeed = 1.5
    })
    
    -- Validate both spells
    if ContextSpellUtils.validateContextSpellDef(customWorldSpell) and 
       ContextSpellUtils.validateContextSpellDef(customDungeonSpell) then
        
        -- Cast in both contexts
        local worldId = ContextSpell.castWorld(customWorldSpell, {
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = input:getMouseWorldPosition().x - player:getPosition().x,
            dy = input:getMouseWorldPosition().y - player:getPosition().y
        })
        
        local dungeonId = ContextSpell.castDungeon(customDungeonSpell, {
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = input:getMouseWorldPosition().x - player:getPosition().x,
            dy = input:getMouseWorldPosition().y - player:getPosition().y
        })
        
        print("Cast custom spells - World: " .. worldId .. ", Dungeon: " .. dungeonId)
        return {worldId, dungeonId}
    else
        print("Invalid custom spell definitions")
        return nil
    end
end

-- Example 3: Batch casting with context
function castContextSpellBatch()
    local spells = {}
    
    -- Create world spells
    for i = 1, 3 do
        local angle = (i - 2) * 0.4
        local direction = {
            x = math.cos(angle),
            y = math.sin(angle)
        }
        
        local worldSpell = ContextSpellPresets.worldFireBolt()
        worldSpell.speed = 12.0 + (i * 2.0)
        
        table.insert(spells, {
            def = worldSpell,
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = direction.x,
            dy = direction.y
        })
    end
    
    -- Create dungeon spells
    for i = 1, 3 do
        local angle = (i - 2) * 0.3
        local direction = {
            x = math.cos(angle),
            y = math.sin(angle)
        }
        
        local dungeonSpell = ContextSpellPresets.dungeonIceBolt()
        dungeonSpell.speed = 10.0 + (i * 1.5)
        
        table.insert(spells, {
            def = dungeonSpell,
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = direction.x,
            dy = direction.y
        })
    end
    
    local entityIds = ContextSpell.castBatch(spells)
    print("Cast context spell batch: " .. #entityIds .. " spells")
    
    return entityIds
end

-- Example 4: Context-specific target finding
function findContextTargets()
    local playerPos = player:getPosition()
    
    -- Find world targets
    local nearestWorldTarget = ContextSpell.findNearestWorldTarget({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 20.0)
    
    local worldTargets = ContextSpell.findWorldTargetsInRadius({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 10.0)
    
    -- Find dungeon targets
    local nearestDungeonTarget = ContextSpell.findNearestDungeonTarget({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 15.0)
    
    local dungeonTargets = ContextSpell.findDungeonTargetsInRadius({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 8.0)
    
    print("Found " .. #worldTargets .. " world targets, " .. #dungeonTargets .. " dungeon targets")
    
    -- Cast homing spells at targets
    if nearestWorldTarget > 0 then
        local lightning = ContextSpellPresets.worldLightningBolt()
        ContextSpell.castWorld(lightning, {
            x = playerPos.x,
            y = playerPos.y,
            dx = 1.0, -- Will be overridden by homing
            dy = 0.0
        })
    end
    
    if nearestDungeonTarget > 0 then
        local arcane = ContextSpellPresets.dungeonArcaneBolt()
        ContextSpell.castDungeon(arcane, {
            x = playerPos.x,
            y = playerPos.y,
            dx = 1.0, -- Will be overridden by homing
            dy = 0.0
        })
    end
    
    return {nearestWorldTarget, nearestDungeonTarget, worldTargets, dungeonTargets}
end

-- Example 5: Context switching
function demonstrateContextSwitching()
    -- Cast a spell in world context
    local worldSpell = ContextSpellPresets.worldFireBolt()
    local entityId = ContextSpell.castWorld(worldSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = 1.0,
        dy = 0.0
    })
    
    print("Cast spell in world context: " .. entityId)
    
    -- Wait a moment, then transfer to dungeon context
    timer:schedule(2.0, function()
        ContextSpell.transferToContext(entityId, "dungeon")
        print("Transferred spell " .. entityId .. " to dungeon context")
        
        -- Transfer back to world after another moment
        timer:schedule(2.0, function()
            ContextSpell.transferToContext(entityId, "world")
            print("Transferred spell " .. entityId .. " back to world context")
        end)
    end)
    
    return entityId
end

-- Example 6: Context-specific effects
function spawnContextEffects()
    local mousePos = input:getMouseWorldPosition()
    
    -- Spawn world impact effect
    ContextSpell.spawnWorldImpactEffect("particles/fireBurst.json", {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, {
        x = 0,
        y = 0,
        z = 1
    })
    
    -- Spawn dungeon impact effect
    ContextSpell.spawnDungeonImpactEffect("particles/iceBurst.json", {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, {
        x = 0,
        y = 0,
        z = 1
    })
    
    -- Spawn world area effect
    local fireball = ContextSpellPresets.worldFireball()
    ContextSpell.spawnWorldAreaEffect(fireball, {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, 3.0)
    
    -- Spawn dungeon area effect
    local iceStorm = ContextSpellPresets.dungeonIceStorm()
    ContextSpell.spawnDungeonAreaEffect(iceStorm, {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, 2.5)
    
    print("Spawned context-specific effects")
end

-- Example 7: Context monitoring and management
function monitorContextSpells()
    local stats = ContextSpell.getContextStats()
    
    print("Context Spell System Statistics:")
    print("  World spells spawned: " .. stats.totalWorldSpellsSpawned)
    print("  Dungeon spells spawned: " .. stats.totalDungeonSpellsSpawned)
    print("  World impacts: " .. stats.totalWorldImpacts)
    print("  Dungeon impacts: " .. stats.totalDungeonImpacts)
    print("  Active world spells: " .. stats.activeWorldSpells)
    print("  Active dungeon spells: " .. stats.activeDungeonSpells)
    print("  Cached world assets: " .. stats.cachedWorldAssets)
    print("  Cached dungeon assets: " .. stats.cachedDungeonAssets)
    print("  Average world spawn time: " .. stats.averageWorldSpawnTime .. "s")
    print("  Average dungeon spawn time: " .. stats.averageDungeonSpawnTime .. "s")
    
    -- Get spells by context
    local worldSpells = ContextSpell.getWorldSpells()
    local dungeonSpells = ContextSpell.getDungeonSpells()
    
    print("Active world spells: " .. #worldSpells)
    for i, spell in ipairs(worldSpells) do
        print("  World spell " .. i .. ": " .. spell.definition.id .. " (ID: " .. spell.entityId .. ")")
    end
    
    print("Active dungeon spells: " .. #dungeonSpells)
    for i, spell in ipairs(dungeonSpells) do
        print("  Dungeon spell " .. i .. ": " .. spell.definition.id .. " (ID: " .. spell.entityId .. ")")
    end
end

-- Example 8: Asset management by context
function manageContextAssets()
    -- Preload world spell assets
    local worldSpells = {
        ContextSpellPresets.worldFireBolt(),
        ContextSpellPresets.worldLightningBolt(),
        ContextSpellPresets.worldFireball()
    }
    
    print("Preloading world spell assets...")
    for _, spellDef in ipairs(worldSpells) do
        ContextSpell.loadAssetAsync(spellDef)
    end
    
    -- Preload dungeon spell assets
    local dungeonSpells = {
        ContextSpellPresets.dungeonIceBolt(),
        ContextSpellPresets.dungeonArcaneBolt(),
        ContextSpellPresets.dungeonIceStorm()
    }
    
    print("Preloading dungeon spell assets...")
    for _, spellDef in ipairs(dungeonSpells) do
        ContextSpell.loadAssetAsync(spellDef)
    end
    
    -- Clear assets by context if needed
    local stats = ContextSpell.getContextStats()
    if stats.cachedWorldAssets > 20 then
        print("Clearing world asset cache...")
        ContextSpell.clearAssetCacheByContext("world")
    end
    
    if stats.cachedDungeonAssets > 20 then
        print("Clearing dungeon asset cache...")
        ContextSpell.clearAssetCacheByContext("dungeon")
    end
end

-- Example 9: Advanced context behaviors
function demonstrateAdvancedBehaviors()
    -- World spell with parallax and physics
    local worldSpell = ContextSpellPresets.worldFireBolt()
    worldSpell.useParallax = true
    worldSpell.parallaxOffset = 1.5
    worldSpell.worldBounce = true
    worldSpell.worldBounceElasticity = 0.8
    worldSpell.worldWindInfluence = 0.3
    
    local worldId = ContextSpell.castWorld(worldSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    -- Dungeon spell with side-scroll physics
    local dungeonSpell = ContextSpellPresets.dungeonArcaneBolt()
    dungeonSpell.dungeonLayer = 2 -- foreground
    dungeonSpell.dungeonUseSideScrollPhysics = true
    dungeonSpell.dungeonScrollSpeed = 1.5
    dungeonSpell.behavior = "arc"
    
    local dungeonId = ContextSpell.castDungeon(dungeonSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast advanced context spells - World: " .. worldId .. ", Dungeon: " .. dungeonId)
    return {worldId, dungeonId}
end

-- Example 10: Hot-reload support for context spells
function setupContextHotReload()
    -- Watch for context spell definition changes
    ContextSpell.watchFiles()
    
    -- Reload specific context spell
    ContextSpell.reloadDefinition("worldFireBolt")
    ContextSpell.reloadDefinition("dungeonIceBolt")
    
    -- Reload all context definitions
    ContextSpell.reloadAllDefinitions()
    
    -- Reload definitions by context
    ContextSpell.reloadContextDefinitions("world")
    ContextSpell.reloadContextDefinitions("dungeon")
    
    print("Context spell hot-reload setup complete")
end

-- Example 11: Performance optimization for context spells
function optimizeContextPerformance()
    -- Monitor context performance
    local stats = ContextSpell.getContextStats()
    
    if stats.averageWorldSpawnTime > 0.016 then
        print("Warning: World spell spawn time exceeds 16ms target")
    end
    
    if stats.averageDungeonSpawnTime > 0.016 then
        print("Warning: Dungeon spell spawn time exceeds 16ms target")
    end
    
    -- Destroy old spells by context
    if stats.activeWorldSpells > 50 then
        print("Too many active world spells, destroying old ones")
        local worldSpells = ContextSpell.getWorldSpells()
        for i = 1, math.min(10, #worldSpells) do
            if worldSpells[i].currentTime > 10.0 then
                ContextSpell.destroy(worldSpells[i].entityId)
            end
        end
    end
    
    if stats.activeDungeonSpells > 50 then
        print("Too many active dungeon spells, destroying old ones")
        local dungeonSpells = ContextSpell.getDungeonSpells()
        for i = 1, math.min(10, #dungeonSpells) do
            if dungeonSpells[i].currentTime > 10.0 then
                ContextSpell.destroy(dungeonSpells[i].entityId)
            end
        end
    end
end

-- Example 12: Integration with existing systems
function integrateWithSystems()
    -- Cast context spells and integrate with existing systems
    local worldSpell = ContextSpellPresets.worldFireBolt()
    local worldId = ContextSpell.castWorld(worldSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    local dungeonSpell = ContextSpellPresets.dungeonIceBolt()
    local dungeonId = ContextSpell.castDungeon(dungeonSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    local worldSpellEntity = ContextSpell.getSpell(worldId)
    local dungeonSpellEntity = ContextSpell.getSpell(dungeonId)
    
    if worldSpellEntity and worldSpellEntity.asset and worldSpellEntity.asset.worldMeshAsset then
        -- Integrate with mesh system
        MeshManager.loadMeshFromAsset(worldSpellEntity.asset.worldMeshAsset)
        
        -- Integrate with physics system
        if worldSpellEntity.definition.collisionRadius > 0 then
            Physics.addCollisionShape(worldSpellEntity.asset.worldMeshAsset)
        end
        
        -- Integrate with rendering system
        Renderer.addMeshToLayer(worldSpellEntity.asset.worldMeshAsset, "world_spells")
        
        print("World spell integrated with existing systems")
    end
    
    if dungeonSpellEntity and dungeonSpellEntity.asset and dungeonSpellEntity.asset.dungeonMeshAsset then
        -- Integrate with mesh system
        MeshManager.loadMeshFromAsset(dungeonSpellEntity.asset.dungeonMeshAsset)
        
        -- Integrate with physics system
        if dungeonSpellEntity.definition.collisionRadius > 0 then
            Physics.addCollisionShape(dungeonSpellEntity.asset.dungeonMeshAsset)
        end
        
        -- Integrate with rendering system
        Renderer.addMeshToLayer(dungeonSpellEntity.asset.dungeonMeshAsset, "dungeon_spells")
        
        print("Dungeon spell integrated with existing systems")
    end
end

-- Example 13: Complex context spell combinations
function castContextSpellCombination()
    local playerPos = player:getPosition()
    local targetPos = input:getMouseWorldPosition()
    
    -- Cast multiple context spells in sequence
    local worldSpells = {
        {def = ContextSpellPresets.worldFireBolt(), delay = 0.0},
        {def = ContextSpellPresets.worldLightningBolt(), delay = 0.2},
        {def = ContextSpellPresets.worldFireball(), delay = 0.4}
    }
    
    local dungeonSpells = {
        {def = ContextSpellPresets.dungeonIceBolt(), delay = 0.1},
        {def = ContextSpellPresets.dungeonArcaneBolt(), delay = 0.3},
        {def = ContextSpellPresets.dungeonIceStorm(), delay = 0.5}
    }
    
    -- Cast world spells
    for i, spellData in ipairs(worldSpells) do
        timer:schedule(spellData.delay, function()
            ContextSpell.castWorld(spellData.def, {
                x = playerPos.x,
                y = playerPos.y,
                dx = targetPos.x - playerPos.x,
                dy = targetPos.y - playerPos.y
            })
        end)
    end
    
    -- Cast dungeon spells
    for i, spellData in ipairs(dungeonSpells) do
        timer:schedule(spellData.delay, function()
            ContextSpell.castDungeon(spellData.def, {
                x = playerPos.x,
                y = playerPos.y,
                dx = targetPos.x - playerPos.x,
                dy = targetPos.y - playerPos.y
            })
        end)
    end
    
    print("Cast context spell combination with delays")
end

-- Main usage example
function main()
    print("Context-Aware Spell Generation Pipeline Example")
    print("==============================================")
    
    -- Initialize the context spell system
    ContextSpell.update(0.0) -- Initialize if needed
    
    -- Run examples
    print("1. Casting context spells...")
    local contextSpellIds = castContextSpell()
    
    print("2. Creating custom context spells...")
    local customSpellIds = createCustomContextSpell()
    
    print("3. Casting context spell batch...")
    local batchIds = castContextSpellBatch()
    
    print("4. Finding context targets...")
    local targetInfo = findContextTargets()
    
    print("5. Demonstrating context switching...")
    local switchEntityId = demonstrateContextSwitching()
    
    print("6. Spawning context effects...")
    spawnContextEffects()
    
    print("7. Monitoring context spells...")
    monitorContextSpells()
    
    print("8. Managing context assets...")
    manageContextAssets()
    
    print("9. Demonstrating advanced behaviors...")
    local advancedIds = demonstrateAdvancedBehaviors()
    
    print("10. Setting up context hot-reload...")
    setupContextHotReload()
    
    print("11. Optimizing context performance...")
    optimizeContextPerformance()
    
    print("12. Integrating with systems...")
    integrateWithSystems()
    
    print("13. Casting context combinations...")
    castContextSpellCombination()
    
    print("Context-aware spell generation examples completed!")
    print("Generated spells active in both world and dungeon contexts")
end

-- Run the example
main() 