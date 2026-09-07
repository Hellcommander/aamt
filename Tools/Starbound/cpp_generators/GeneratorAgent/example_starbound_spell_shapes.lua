-- Starbound Spell-Shaping with Full Projectile Math Example
-- Demonstrates all vanilla Starbound projectile patterns with mesh deformation

require("starbound_spell_shapes")

-- Example 1: Basic Starbound projectile patterns
function demonstrateStarboundPatterns()
    -- Straight projectile (constant velocity)
    local straightSpell = SpellDef()
    straightSpell.id = "straightBolt"
    straightSpell.type = "projectile"
    straightSpell.sourceSprite = "icons/energyBolt.png"
    straightSpell.meshThickness = 0.05
    straightSpell.speed = 15.0
    straightSpell.lifetime = 3.0
    straightSpell.behavior = "direct"
    straightSpell.damage = 20
    
    local straightShape = StarboundSpellShapePresets.straight()
    straightSpell.shape = straightShape
    
    local entityId = Spell.cast(straightSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, straightShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast straight projectile: " .. entityId)
    return entityId
end

-- Example 2: Arc projectile (parabolic drop)
function demonstrateArcPattern()
    local arcSpell = SpellDef()
    arcSpell.id = "lightningArc"
    arcSpell.type = "projectile"
    arcSpell.sourceSprite = "icons/lightning.png"
    arcSpell.meshThickness = 0.04
    arcSpell.speed = 18.0
    arcSpell.lifetime = 2.0
    arcSpell.behavior = "direct"
    arcSpell.damage = 25
    
    local arcShape = StarboundSpellShapePresets.arc(5.0, 0.8, 2.0)
    arcShape.warpShader = "shaders/lightningArcWarp.glsl"
    arcShape.useGPU = true
    
    arcSpell.shape = arcShape
    
    local entityId = Spell.cast(arcSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, arcShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast arc projectile: " .. entityId)
    return entityId
end

-- Example 3: Wave projectile (sinusoidal oscillation)
function demonstrateWavePattern()
    local waveSpell = SpellDef()
    waveSpell.id = "sandWave"
    waveSpell.type = "projectile"
    waveSpell.sourceSprite = "icons/sand.png"
    waveSpell.meshThickness = 0.03
    waveSpell.speed = 12.0
    waveSpell.lifetime = 2.5
    waveSpell.behavior = "direct"
    waveSpell.damage = 15
    
    local waveShape = StarboundSpellShapePresets.wave(0.25, 6.0, 0.0)
    waveShape.warpShader = "shaders/sandWaveWarp.glsl"
    waveShape.useGPU = true
    
    waveSpell.shape = waveShape
    
    local entityId = Spell.cast(waveSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, waveShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast wave projectile: " .. entityId)
    return entityId
end

-- Example 4: Spiral projectile (rotating offset)
function demonstrateSpiralPattern()
    local spiralSpell = SpellDef()
    spiralSpell.id = "fireSpiral"
    spiralSpell.type = "projectile"
    spiralSpell.sourceSprite = "icons/fireSpiral.png"
    spiralSpell.meshThickness = 0.06
    spiralSpell.speed = 14.0
    spiralSpell.lifetime = 3.0
    spiralSpell.behavior = "direct"
    spiralSpell.damage = 30
    
    local spiralShape = StarboundSpellShapePresets.spiral(4.0, 0.3, 2.0)
    spiralShape.warpShader = "shaders/fireSpiralWarp.glsl"
    spiralShape.useGPU = true
    
    spiralSpell.shape = spiralShape
    
    local entityId = Spell.cast(spiralSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, spiralShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast spiral projectile: " .. entityId)
    return entityId
end

-- Example 5: Boomerang projectile (forward then return)
function demonstrateBoomerangPattern()
    local boomerangSpell = SpellDef()
    boomerangSpell.id = "iceBoomerang"
    boomerangSpell.type = "projectile"
    boomerangSpell.sourceSprite = "icons/iceBoomerang.png"
    boomerangSpell.meshThickness = 0.05
    boomerangSpell.speed = 16.0
    boomerangSpell.lifetime = 4.0
    boomerangSpell.behavior = "direct"
    boomerangSpell.damage = 35
    
    local boomerangShape = StarboundSpellShapePresets.boomerang(0.6, 1.2, true)
    boomerangShape.warpShader = "shaders/iceBoomerangWarp.glsl"
    boomerangShape.useGPU = true
    
    boomerangSpell.shape = boomerangShape
    
    local entityId = Spell.cast(boomerangSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, boomerangShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast boomerang projectile: " .. entityId)
    return entityId
end

-- Example 6: Ricochet projectile (bounce off surfaces)
function demonstrateRicochetPattern()
    local ricochetSpell = SpellDef()
    ricochetSpell.id = "plasmaRicochet"
    ricochetSpell.type = "projectile"
    ricochetSpell.sourceSprite = "icons/plasma.png"
    ricochetSpell.meshThickness = 0.04
    ricochetSpell.speed = 20.0
    ricochetSpell.lifetime = 5.0
    ricochetSpell.behavior = "direct"
    ricochetSpell.damage = 40
    
    local ricochetShape = StarboundSpellShapePresets.ricochet(3, 0.7, 20.0)
    ricochetShape.warpShader = "shaders/plasmaRicochetWarp.glsl"
    ricochetShape.useGPU = true
    
    ricochetSpell.shape = ricochetShape
    
    local entityId = Spell.cast(ricochetSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, ricochetShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast ricochet projectile: " .. entityId)
    return entityId
end

-- Example 7: Homing projectile (turn toward target)
function demonstrateHomingPattern()
    local homingSpell = SpellDef()
    homingSpell.id = "arcaneHoming"
    homingSpell.type = "projectile"
    homingSpell.sourceSprite = "icons/arcane.png"
    homingSpell.meshThickness = 0.05
    homingSpell.speed = 12.0
    homingSpell.lifetime = 3.5
    homingSpell.behavior = "homing"
    homingSpell.damage = 45
    
    -- Find nearest target
    local target = world:findNearestEnemy(player:getPosition(), 20.0)
    local targetId = target and target.id or 0
    
    local homingShape = StarboundSpellShapePresets.homing(targetId, 180.0, 30.0)
    homingShape.warpShader = "shaders/arcaneHomingWarp.glsl"
    homingShape.useGPU = true
    
    homingSpell.shape = homingShape
    
    local entityId = Spell.cast(homingSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, homingShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast homing projectile: " .. entityId)
    return entityId
end

-- Example 8: Radial burst projectile (burst pattern)
function demonstrateRadialPattern()
    local radialSpell = SpellDef()
    radialSpell.id = "energyBurst"
    radialSpell.type = "projectile"
    radialSpell.sourceSprite = "icons/energyBurst.png"
    radialSpell.meshThickness = 0.06
    radialSpell.speed = 10.0
    radialSpell.lifetime = 2.0
    radialSpell.behavior = "direct"
    radialSpell.damage = 25
    
    local radialShape = StarboundSpellShapePresets.radial(12, 360.0, 0.1)
    radialShape.warpShader = "shaders/energyBurstWarp.glsl"
    radialShape.useGPU = true
    
    radialSpell.shape = radialShape
    
    local entityId = Spell.cast(radialSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, radialShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast radial burst projectile: " .. entityId)
    return entityId
end

-- Example 9: Composite projectile (blend multiple patterns)
function demonstrateCompositePattern()
    local compositeSpell = SpellDef()
    compositeSpell.id = "chaosComposite"
    compositeSpell.type = "projectile"
    compositeSpell.sourceSprite = "icons/chaos.png"
    compositeSpell.meshThickness = 0.07
    compositeSpell.speed = 8.0
    compositeSpell.lifetime = 4.0
    compositeSpell.behavior = "direct"
    compositeSpell.damage = 50
    
    local compositeShape = StarboundSpellShapePresets.composite({
        StarboundSpellShape.Kind.Wave,
        StarboundSpellShape.Kind.Spiral,
        StarboundSpellShape.Kind.Arc
    }, {0.4, 0.3, 0.3})
    
    compositeShape.warpShader = "shaders/chaosCompositeWarp.glsl"
    compositeShape.useGPU = true
    
    compositeSpell.shape = compositeShape
    
    local entityId = Spell.cast(compositeSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, compositeShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast composite projectile: " .. entityId)
    return entityId
end

-- Example 10: Custom Starbound shape with advanced parameters
function createCustomStarboundShape()
    local customSpell = SpellDef()
    customSpell.id = "customStarboundSpell"
    customSpell.type = "projectile"
    customSpell.sourceSprite = "icons/custom.png"
    customSpell.meshThickness = 0.05
    customSpell.speed = 15.0
    customSpell.lifetime = 3.0
    customSpell.behavior = "direct"
    customSpell.damage = 30
    
    -- Create custom shape with advanced parameters
    local customShape = StarboundSpellShapeUtils.createShape({
        kind = StarboundSpellShape.Kind.Wave,
        amplitude = 0.4,
        frequency = 8.0,
        phase = 0.5,
        waveDirection = 45.0,
        duration = 3.0,
        noiseScale = 0.2,
        turbulence = 0.1,
        useGPU = true,
        syncCollision = true,
        warpShader = "shaders/customWaveWarp.glsl"
    })
    
    customSpell.shape = customShape
    
    local entityId = Spell.cast(customSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, customShape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    print("Cast custom Starbound projectile: " .. entityId)
    return entityId
end

-- Example 11: Starbound shape monitoring and statistics
function monitorStarboundShapes()
    local stats = StarboundSpellShape.getStats()
    
    print("Starbound Spell Shape System Statistics:")
    print("  Active shape components: " .. stats.activeShapeComponents)
    print("  GPU deformed meshes: " .. stats.gpuDeformedMeshes)
    print("  CPU deformed meshes: " .. stats.cpuDeformedMeshes)
    print("  Collision updates: " .. stats.collisionUpdates)
    print("  Ricochet bounces: " .. stats.ricochetBounces)
    print("  Homing updates: " .. stats.homingUpdates)
    print("  Radial bursts: " .. stats.radialBursts)
    print("  Average deformation time: " .. stats.averageDeformationTime .. "ms")
    print("  Average collision update time: " .. stats.averageCollisionUpdateTime .. "ms")
    print("  Average homing time: " .. stats.averageHomingTime .. "ms")
    
    -- Get all active shape components
    local activeShapes = {}
    for entityId, component in pairs(StarboundSpellShape.getAllShapes()) do
        if component.isActive then
            table.insert(activeShapes, {
                entityId = entityId,
                shapeKind = component.shape.kind,
                normalizedTime = component.normalizedTime,
                useGPU = component.shape.useGPU,
                bounceCount = component.bounceCount,
                hasTarget = component.hasTarget
            })
        end
    end
    
    print("Active Starbound shape components: " .. #activeShapes)
    for i, shapeInfo in ipairs(activeShapes) do
        print("  Entity " .. shapeInfo.entityId .. ": " .. 
              shapeInfo.shapeKind .. " (t=" .. string.format("%.2f", shapeInfo.normalizedTime) .. 
              ", GPU=" .. (shapeInfo.useGPU and "true" or "false") .. 
              ", Bounces=" .. shapeInfo.bounceCount .. 
              ", Target=" .. (shapeInfo.hasTarget and "true" or "false") .. ")")
    end
end

-- Example 12: Starbound shape hot-reload support
function setupStarboundShapeHotReload()
    -- Watch for Starbound shape definition changes
    StarboundSpellShape.watchShapeFiles()
    
    -- Reload Starbound shape definitions
    StarboundSpellShape.reloadShapeDefinitions()
    
    -- Reload Starbound warp shaders
    StarboundSpellShape.reloadWarpShaders()
    
    print("Starbound shape system hot-reload setup complete")
end

-- Example 13: Starbound shape performance optimization
function optimizeStarboundShapes()
    local stats = StarboundSpellShape.getStats()
    
    -- Monitor deformation performance
    if stats.averageDeformationTime > 1.0 then
        print("Warning: Starbound deformation time exceeds 1ms target")
        
        -- Switch complex shapes to GPU
        local activeShapes = StarboundSpellShape.getAllShapes()
        for entityId, component in pairs(activeShapes) do
            if not component.shape.useGPU and component.shape.kind ~= StarboundSpellShape.Kind.Straight then
                component.shape.useGPU = true
                StarboundSpellShape.bindWarpShader(entityId)
                print("Switched entity " .. entityId .. " to GPU deformation")
            end
        end
    end
    
    -- Monitor collision update performance
    if stats.averageCollisionUpdateTime > 0.5 then
        print("Warning: Starbound collision update time exceeds 0.5ms target")
        
        -- Disable collision sync for non-critical shapes
        local activeShapes = StarboundSpellShape.getAllShapes()
        for entityId, component in pairs(activeShapes) do
            if component.shape.syncCollision and component.shape.kind == StarboundSpellShape.Kind.Straight then
                component.shape.syncCollision = false
                print("Disabled collision sync for entity " .. entityId)
            end
        end
    end
    
    -- Monitor homing performance
    if stats.averageHomingTime > 0.3 then
        print("Warning: Starbound homing time exceeds 0.3ms target")
        
        -- Reduce homing update frequency for distant targets
        local activeShapes = StarboundSpellShape.getAllShapes()
        for entityId, component in pairs(activeShapes) do
            if component.hasTarget and component.shape.kind == StarboundSpellShape.Kind.Homing then
                -- Increase homing timer to reduce updates
                component.homingTimer = math.min(component.homingTimer + 0.1, 0.5)
                print("Reduced homing updates for entity " .. entityId)
            end
        end
    end
    
    -- Clean up inactive shapes
    if stats.activeShapeComponents > 100 then
        print("Too many active Starbound shape components, cleaning up...")
        StarboundSpellShape.cleanupInactiveShapes()
    end
end

-- Example 14: Integration with existing systems
function integrateStarboundShapesWithSystems()
    -- Cast a Starbound spell with shape deformation
    local spell = SpellDef()
    spell.id = "integratedStarboundSpell"
    spell.type = "projectile"
    spell.sourceSprite = "icons/integrated.png"
    spell.meshThickness = 0.06
    spell.speed = 14.0
    spell.lifetime = 3.5
    spell.behavior = "direct"
    spell.damage = 35
    
    local shape = StarboundSpellShapeExamples.sandWave()
    spell.shape = shape
    
    local entityId = Spell.cast(spell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    StarboundSpellShape.addShape(entityId, shape, {
        x = player:getPosition().x,
        y = player:getPosition().y
    }, {
        x = input:getMouseWorldPosition().x - player:getPosition().x,
        y = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    -- Integrate with mesh system
    local shapeComponent = StarboundSpellShape.getShape(entityId)
    if shapeComponent then
        -- Apply shape to mesh asset
        local meshAsset = Spell.getSpell(entityId).asset.meshAsset
        if meshAsset then
            StarboundSpellShape.applyShapeToMesh(entityId, meshAsset)
            print("Applied Starbound shape deformation to mesh asset")
        end
        
        -- Update collision shape
        StarboundSpellShape.updateCollisionForEntity(entityId)
        print("Updated collision shape for Starbound entity " .. entityId)
    end
    
    print("Cast integrated Starbound spell: " .. entityId)
    return entityId
end

-- Example 15: Complex Starbound shape combinations
function castStarboundShapeCombination()
    local playerPos = player:getPosition()
    local targetPos = input:getMouseWorldPosition()
    
    -- Cast multiple Starbound patterns in sequence
    local starboundSpells = {
        {
            name = "Sand Wave",
            shape = StarboundSpellShapeExamples.sandWave(),
            delay = 0.0
        },
        {
            name = "Lightning Arc",
            shape = StarboundSpellShapeExamples.lightningArc(),
            delay = 0.5
        },
        {
            name = "Fire Spiral",
            shape = StarboundSpellShapeExamples.fireSpiral(),
            delay = 1.0
        },
        {
            name = "Ice Boomerang",
            shape = StarboundSpellShapeExamples.iceBoomerang(),
            delay = 1.5
        },
        {
            name = "Plasma Ricochet",
            shape = StarboundSpellShapeExamples.plasmaRicochet(),
            delay = 2.0
        },
        {
            name = "Arcane Homing",
            shape = StarboundSpellShapeExamples.arcaneHoming(),
            delay = 2.5
        },
        {
            name = "Energy Burst",
            shape = StarboundSpellShapeExamples.energyBurst(),
            delay = 3.0
        },
        {
            name = "Chaos Composite",
            shape = StarboundSpellShapeExamples.chaosComposite(),
            delay = 3.5
        }
    }
    
    local entityIds = {}
    
    for i, spellData in ipairs(starboundSpells) do
        timer:schedule(spellData.delay, function()
            local spell = SpellDef()
            spell.id = spellData.name:gsub(" ", ""):lower()
            spell.type = "projectile"
            spell.sourceSprite = "icons/" .. spell.id .. ".png"
            spell.meshThickness = 0.05
            spell.speed = 12.0 + (i * 2.0)
            spell.lifetime = 3.0
            spell.behavior = "direct"
            spell.damage = 20 + (i * 5)
            spell.shape = spellData.shape
            
            local entityId = Spell.cast(spell, {
                x = playerPos.x,
                y = playerPos.y,
                dx = targetPos.x - playerPos.x,
                dy = targetPos.y - playerPos.y
            })
            
            StarboundSpellShape.addShape(entityId, spellData.shape, {
                x = playerPos.x,
                y = playerPos.y
            }, {
                x = targetPos.x - playerPos.x,
                y = targetPos.y - playerPos.y
            })
            
            table.insert(entityIds, entityId)
            print("Cast " .. spellData.name .. ": " .. entityId)
        end)
    end
    
    print("Cast Starbound shape combination with delays")
    return entityIds
end

-- Main usage example
function main()
    print("Starbound Spell-Shaping with Full Projectile Math Example")
    print("========================================================")
    
    -- Initialize the Starbound shape system
    StarboundSpellShape.update(0.0) -- Initialize if needed
    
    -- Run examples
    print("1. Demonstrating Starbound patterns...")
    local straightId = demonstrateStarboundPatterns()
    
    print("2. Demonstrating arc pattern...")
    local arcId = demonstrateArcPattern()
    
    print("3. Demonstrating wave pattern...")
    local waveId = demonstrateWavePattern()
    
    print("4. Demonstrating spiral pattern...")
    local spiralId = demonstrateSpiralPattern()
    
    print("5. Demonstrating boomerang pattern...")
    local boomerangId = demonstrateBoomerangPattern()
    
    print("6. Demonstrating ricochet pattern...")
    local ricochetId = demonstrateRicochetPattern()
    
    print("7. Demonstrating homing pattern...")
    local homingId = demonstrateHomingPattern()
    
    print("8. Demonstrating radial pattern...")
    local radialId = demonstrateRadialPattern()
    
    print("9. Demonstrating composite pattern...")
    local compositeId = demonstrateCompositePattern()
    
    print("10. Creating custom Starbound shape...")
    local customId = createCustomStarboundShape()
    
    print("11. Monitoring Starbound shapes...")
    monitorStarboundShapes()
    
    print("12. Setting up Starbound shape hot-reload...")
    setupStarboundShapeHotReload()
    
    print("13. Optimizing Starbound shapes...")
    optimizeStarboundShapes()
    
    print("14. Integrating with systems...")
    local integratedId = integrateStarboundShapesWithSystems()
    
    print("15. Casting Starbound shape combinations...")
    local combinationIds = castStarboundShapeCombination()
    
    print("Starbound spell-shaping examples completed!")
    print("Generated Starbound-compatible projectiles with full mathematical accuracy")
end

-- Run the example
main() 