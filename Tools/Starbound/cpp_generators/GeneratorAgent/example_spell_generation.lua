-- Spell Generation Pipeline Example
-- Demonstrates mesh-based spell casting with texture baking and shader effects

require("spells")

-- Example 1: Basic spell casting
function castBasicSpell()
    local bolt = SpellPresets.fireBolt()
    
    -- Cast from player position towards mouse
    local playerPos = player:getPosition()
    local mousePos = input:getMouseWorldPosition()
    local direction = (mousePos - playerPos):normalize()
    
    local entityId = Spell.cast(bolt, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    })
    
    print("Cast fire bolt: " .. entityId)
    return entityId
end

-- Example 2: Async spell casting with callback
function castAsyncSpell()
    local lightning = SpellPresets.lightningBolt()
    
    -- Set up homing target
    local target = world:findNearestEnemy(player:getPosition(), 10.0)
    if target then
        lightning.targetEntityId = target.id
    end
    
    Spell.castAsync(lightning, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    }, function(entityId)
        print("Lightning bolt spawned: " .. entityId)
        
        -- Set up homing behavior
        local spell = Spell.getSpell(entityId)
        if spell and target then
            spell.hasTarget = true
            spell.targetEntityId = target.id
            spell.targetPosition = target:getPosition()
        end
    end)
end

-- Example 3: Batch spell casting
function castSpellBatch()
    local spells = {}
    
    -- Create multiple fire bolts in a spread pattern
    for i = 1, 5 do
        local angle = (i - 3) * 0.3 -- Spread angle
        local direction = {
            x = math.cos(angle),
            y = math.sin(angle),
            z = 0
        }
        
        local bolt = SpellPresets.fireBolt()
        bolt.speed = 12.0 + (i * 2.0) -- Varying speeds
        
        table.insert(spells, {
            def = bolt,
            x = player:getPosition().x,
            y = player:getPosition().y,
            z = player:getPosition().z,
            dx = direction.x,
            dy = direction.y,
            dz = direction.z
        })
    end
    
    local entityIds = Spell.castBatch(spells)
    print("Cast spell batch: " .. #entityIds .. " spells")
    
    return entityIds
end

-- Example 4: Area of effect spell
function castAreaSpell()
    local fireball = SpellPresets.fireball()
    fireball.areaRadius = 3.0
    fireball.damage = 50
    
    local targetPos = input:getMouseWorldPosition()
    
    local entityId = Spell.cast(fireball, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        z = player:getPosition().z,
        dx = targetPos.x - player:getPosition().x,
        dy = targetPos.y - player:getPosition().y
    })
    
    print("Cast fireball: " .. entityId)
    return entityId
end

-- Example 5: Custom spell definition
function createCustomSpell()
    local customSpell = SpellUtils.createSpellDef({
        id = "customArcaneBolt",
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
        useAnimation = true,
        animationName = "pulse",
        animationSpeed = 2.0,
        loopAnimation = true,
        dragCoefficient = 0.05,
        gravityScale = 0.0,
        useWind = true,
        windInfluence = 0.2
    })
    
    -- Validate the spell definition
    if SpellUtils.validateSpellDef(customSpell) then
        local entityId = Spell.cast(customSpell, {
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = input:getMouseWorldPosition().x - player:getPosition().x,
            dy = input:getMouseWorldPosition().y - player:getPosition().y
        })
        
        print("Cast custom spell: " .. entityId)
        return entityId
    else
        print("Invalid spell definition")
        return nil
    end
end

-- Example 6: Spell asset preloading
function preloadSpellAssets()
    local spellsToPreload = {
        SpellPresets.fireBolt(),
        SpellPresets.iceBolt(),
        SpellPresets.lightningBolt(),
        SpellPresets.arcaneBolt(),
        SpellPresets.fireball(),
        SpellPresets.iceStorm()
    }
    
    print("Preloading spell assets...")
    
    for _, spellDef in ipairs(spellsToPreload) do
        Spell.loadAssetAsync(spellDef)
    end
    
    print("Spell asset preloading started")
end

-- Example 7: Spell monitoring and management
function monitorSpells()
    local stats = Spell.getStats()
    
    print("Spell System Statistics:")
    print("  Total spells spawned: " .. stats.totalSpellsSpawned)
    print("  Total spells destroyed: " .. stats.totalSpellsDestroyed)
    print("  Total impacts: " .. stats.totalImpacts)
    print("  Total area effects: " .. stats.totalAreaEffects)
    print("  Active spells: " .. stats.activeSpells)
    print("  Cached assets: " .. stats.cachedAssets)
    print("  Average spawn time: " .. stats.averageSpawnTime .. "s")
    print("  Average load time: " .. stats.averageLoadTime .. "s")
    
    -- Get active spells in player area
    local playerPos = player:getPosition()
    local nearbySpells = Spell.getSpellsInRadius({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, 10.0)
    
    print("Nearby spells: " .. #nearbySpells)
    for i, spell in ipairs(nearbySpells) do
        print("  Spell " .. i .. ": " .. spell.definition.id .. " (ID: " .. spell.entityId .. ")")
    end
end

-- Example 8: Advanced spell behaviors
function castAdvancedSpells()
    -- Homing lightning bolt
    local lightning = SpellPresets.lightningBolt()
    lightning.behavior = "homing"
    
    local target = world:findNearestEnemy(player:getPosition(), 15.0)
    if target then
        local entityId = Spell.cast(lightning, {
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = target:getPosition().x - player:getPosition().x,
            dy = target:getPosition().y - player:getPosition().y
        })
        
        -- Set up homing target
        local spell = Spell.getSpell(entityId)
        if spell then
            spell.hasTarget = true
            spell.targetEntityId = target.id
            spell.targetPosition = target:getPosition()
        end
    end
    
    -- Arcane bolt with arc trajectory
    local arcane = SpellPresets.arcaneBolt()
    arcane.behavior = "arc"
    arcane.gravityScale = 0.5 -- Add gravity for arc effect
    
    Spell.cast(arcane, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
end

-- Example 9: Spell effect spawning
function spawnSpellEffects()
    -- Spawn impact effect at mouse position
    local mousePos = input:getMouseWorldPosition()
    Spell.spawnImpactEffect("particles/fireBurst.json", {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, {
        x = 0,
        y = 0,
        z = 1
    })
    
    -- Spawn area effect
    local fireball = SpellPresets.fireball()
    Spell.spawnAreaEffect(fireball, {
        x = mousePos.x,
        y = mousePos.y,
        z = mousePos.z
    }, 3.0)
end

-- Example 10: Target finding and homing
function castHomingSpells()
    local playerPos = player:getPosition()
    
    -- Find nearest enemy
    local nearestTarget = Spell.findNearestTarget({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 20.0)
    
    if nearestTarget > 0 then
        local lightning = SpellPresets.lightningBolt()
        lightning.behavior = "homing"
        
        local entityId = Spell.cast(lightning, {
            x = playerPos.x,
            y = playerPos.y,
            dx = 1.0, -- Will be overridden by homing
            dy = 0.0
        })
        
        print("Cast homing lightning at target: " .. nearestTarget)
    end
    
    -- Find all enemies in radius
    local targets = Spell.findTargetsInRadius({
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z
    }, "enemy", 10.0)
    
    print("Found " .. #targets .. " enemies in radius")
    
    -- Cast area spell at each target
    for _, targetId in ipairs(targets) do
        local iceStorm = SpellPresets.iceStorm()
        local targetPos = world:getEntityPosition(targetId)
        
        Spell.cast(iceStorm, {
            x = targetPos.x,
            y = targetPos.y,
            z = targetPos.z
        })
    end
end

-- Example 11: Spell hot-reloading
function setupSpellHotReload()
    -- Watch for spell definition changes
    Spell.watchFiles()
    
    -- Reload specific spell
    Spell.reloadDefinition("fireBolt")
    
    -- Reload all spell definitions
    Spell.reloadAllDefinitions()
    
    print("Spell hot-reload setup complete")
end

-- Example 12: Performance optimization
function optimizeSpellPerformance()
    -- Preload commonly used spell assets
    preloadSpellAssets()
    
    -- Clear asset cache if needed
    local stats = Spell.getStats()
    if stats.cachedAssets > 50 then
        print("Clearing spell asset cache...")
        Spell.clearAssetCache()
    end
    
    -- Monitor spell performance
    if stats.averageSpawnTime > 0.016 then -- 16ms target
        print("Warning: Spell spawn time exceeds 16ms target")
    end
    
    if stats.activeSpells > 100 then
        print("Warning: Too many active spells, destroying old ones")
        -- Destroy spells older than 10 seconds
        local currentTime = world:getTime()
        local spells = Spell.getSpellsByType("projectile")
        for _, spell in ipairs(spells) do
            if spell.currentTime > 10.0 then
                Spell.destroy(spell.entityId)
            end
        end
    end
end

-- Example 13: Integration with existing systems
function integrateWithSystems()
    -- Cast spell and integrate with mesh system
    local bolt = SpellPresets.fireBolt()
    local entityId = Spell.cast(bolt, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    local spell = Spell.getSpell(entityId)
    if spell and spell.asset and spell.asset.meshAsset then
        -- Integrate with mesh system
        MeshManager.loadMeshFromAsset(spell.asset.meshAsset)
        
        -- Integrate with physics system
        if spell.definition.collisionRadius > 0 then
            Physics.addCollisionShape(spell.asset.meshAsset)
        end
        
        -- Integrate with rendering system
        Renderer.addMeshToLayer(spell.asset.meshAsset, "spells")
        
        print("Spell integrated with existing systems")
    end
end

-- Example 14: Complex spell combinations
function castSpellCombination()
    local playerPos = player:getPosition()
    local targetPos = input:getMouseWorldPosition()
    
    -- Cast multiple spell types in sequence
    local spells = {
        {def = SpellPresets.fireBolt(), delay = 0.0},
        {def = SpellPresets.iceBolt(), delay = 0.2},
        {def = SpellPresets.lightningBolt(), delay = 0.4},
        {def = SpellPresets.arcaneBolt(), delay = 0.6}
    }
    
    for i, spellData in ipairs(spells) do
        timer:schedule(spellData.delay, function()
            Spell.cast(spellData.def, {
                x = playerPos.x,
                y = playerPos.y,
                dx = targetPos.x - playerPos.x,
                dy = targetPos.y - playerPos.y
            })
        end)
    end
    
    print("Cast spell combination with delays")
end

-- Main usage example
function main()
    print("Spell Generation Pipeline Example")
    print("=================================")
    
    -- Initialize the spell system
    Spell.update(0.0) -- Initialize if needed
    
    -- Run examples
    print("1. Casting basic spell...")
    local basicSpellId = castBasicSpell()
    
    print("2. Casting async spell...")
    castAsyncSpell()
    
    print("3. Casting spell batch...")
    local batchIds = castSpellBatch()
    
    print("4. Casting area spell...")
    local areaSpellId = castAreaSpell()
    
    print("5. Creating custom spell...")
    local customSpellId = createCustomSpell()
    
    print("6. Preloading spell assets...")
    preloadSpellAssets()
    
    print("7. Monitoring spells...")
    monitorSpells()
    
    print("8. Casting advanced spells...")
    castAdvancedSpells()
    
    print("9. Spawning spell effects...")
    spawnSpellEffects()
    
    print("10. Casting homing spells...")
    castHomingSpells()
    
    print("11. Setting up hot-reload...")
    setupSpellHotReload()
    
    print("12. Optimizing performance...")
    optimizeSpellPerformance()
    
    print("13. Integrating with systems...")
    integrateWithSystems()
    
    print("14. Casting spell combinations...")
    castSpellCombination()
    
    print("Spell generation examples completed!")
    print("Generated spells active in world")
end

-- Run the example
main() 