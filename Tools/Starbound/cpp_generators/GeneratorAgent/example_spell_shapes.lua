-- Dynamic Spell-Shaping for Mesh-Based Projectiles Example
-- Demonstrates runtime shape alterations and mesh deformation

require("spell_shapes")

-- Example 1: Basic shape application
function applyBasicShapes()
    -- Cast a spell with straight shape (no deformation)
    local straightSpell = SpellDef()
    straightSpell.id = "straightBolt"
    straightSpell.type = "projectile"
    straightSpell.sourceSprite = "icons/energyBolt.png"
    straightSpell.meshThickness = 0.05
    straightSpell.speed = 15.0
    straightSpell.lifetime = 3.0
    straightSpell.behavior = "direct"
    straightSpell.damage = 20
    
    local straightShape = SpellShapePresets.straight()
    straightSpell.shape = straightShape
    
    local entityId = Spell.cast(straightSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    -- Add shape component to the spell
    SpellShape.addShape(entityId, straightShape)
    
    print("Cast straight spell: " .. entityId)
    return entityId
end

-- Example 2: Wave shape deformation
function applyWaveShape()
    local waveSpell = SpellDef()
    waveSpell.id = "emberWave"
    waveSpell.type = "projectile"
    waveSpell.sourceSprite = "icons/ember.png"
    waveSpell.meshThickness = 0.03
    waveSpell.speed = 10.0
    waveSpell.lifetime = 2.5
    waveSpell.behavior = "direct"
    waveSpell.damage = 12
    
    -- Create wave shape with GPU deformation
    local waveShape = SpellShapeUtils.createShape({
        kind = SpellShape.Kind.Wave,
        amplitude = 0.3,
        frequency = 6.0,
        speed = 1.5,
        warpShader = "shaders/waveWarp.glsl",
        useGPU = true,
        syncCollision = true
    })
    
    waveSpell.shape = waveShape
    
    local entityId = Spell.cast(waveSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    -- Add shape component and bind GPU shader
    SpellShape.addShape(entityId, waveShape)
    SpellShape.bindWarpShader(entityId)
    
    print("Cast wave spell: " .. entityId)
    return entityId
end

-- Example 3: Arc shape deformation
function applyArcShape()
    local arcSpell = SpellDef()
    arcSpell.id = "lightningArc"
    arcSpell.type = "projectile"
    arcSpell.sourceSprite = "icons/lightning.png"
    arcSpell.meshThickness = 0.04
    arcSpell.speed = 18.0
    arcSpell.lifetime = 2.0
    arcSpell.behavior = "direct"
    arcSpell.damage = 25
    
    -- Create arc shape
    local arcShape = SpellShapePresets.arc(1.2, 60.0)
    arcShape.warpShader = "shaders/lightningWarp.glsl"
    arcShape.useGPU = true
    
    arcSpell.shape = arcShape
    
    local entityId = Spell.cast(arcSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, arcShape)
    SpellShape.bindWarpShader(entityId)
    
    print("Cast arc spell: " .. entityId)
    return entityId
end

-- Example 4: Spiral shape deformation
function applySpiralShape()
    local spiralSpell = SpellDef()
    spiralSpell.id = "fireSpiral"
    spiralSpell.type = "projectile"
    spiralSpell.sourceSprite = "icons/fireSpiral.png"
    spiralSpell.meshThickness = 0.06
    spiralSpell.speed = 12.0
    spiralSpell.lifetime = 4.0
    spiralSpell.behavior = "direct"
    spiralSpell.damage = 30
    
    -- Create spiral shape
    local spiralShape = SpellShapePresets.spiral(0.8, 4.0)
    spiralShape.speed = 2.0
    spiralShape.warpShader = "shaders/spiralWarp.glsl"
    spiralShape.useGPU = true
    
    spiralSpell.shape = spiralShape
    
    local entityId = Spell.cast(spiralSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, spiralShape)
    SpellShape.bindWarpShader(entityId)
    
    print("Cast spiral spell: " .. entityId)
    return entityId
end

-- Example 5: Vortex shape deformation
function applyVortexShape()
    local vortexSpell = SpellDef()
    vortexSpell.id = "iceVortex"
    vortexSpell.type = "projectile"
    vortexSpell.sourceSprite = "icons/iceVortex.png"
    vortexSpell.meshThickness = 0.05
    vortexSpell.speed = 14.0
    vortexSpell.lifetime = 3.5
    vortexSpell.behavior = "direct"
    vortexSpell.damage = 28
    
    -- Create vortex shape
    local vortexShape = SpellShapePresets.vortex(1.0, 3.0)
    vortexShape.speed = 1.8
    vortexShape.warpShader = "shaders/vortexWarp.glsl"
    vortexShape.useGPU = true
    
    vortexSpell.shape = vortexShape
    
    local entityId = Spell.cast(vortexSpell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, vortexShape)
    SpellShape.bindWarpShader(entityId)
    
    print("Cast vortex spell: " .. entityId)
    return entityId
end

-- Example 6: Advanced shape examples
function applyAdvancedShapes()
    local shapes = {
        -- Burst fan shape
        {
            name = "arcaneBurst",
            spell = function()
                local spell = SpellDef()
                spell.id = "arcaneBurst"
                spell.type = "projectile"
                spell.sourceSprite = "icons/arcaneBurst.png"
                spell.meshThickness = 0.08
                spell.speed = 8.0
                spell.lifetime = 5.0
                spell.behavior = "direct"
                spell.damage = 40
                return spell
            end,
            shape = SpellShapeExamples.arcaneBurst()
        },
        
        -- Zigzag shape
        {
            name = "shadowZigzag",
            spell = function()
                local spell = SpellDef()
                spell.id = "shadowZigzag"
                spell.type = "projectile"
                spell.sourceSprite = "icons/shadowBolt.png"
                spell.meshThickness = 0.04
                spell.speed = 16.0
                spell.lifetime = 3.0
                spell.behavior = "direct"
                spell.damage = 22
                return spell
            end,
            shape = SpellShapeExamples.shadowZigzag()
        },
        
        -- Pulse shape
        {
            name = "energyPulse",
            spell = function()
                local spell = SpellDef()
                spell.id = "energyPulse"
                spell.type = "projectile"
                spell.sourceSprite = "icons/energyPulse.png"
                spell.meshThickness = 0.07
                spell.speed = 10.0
                spell.lifetime = 4.0
                spell.behavior = "direct"
                spell.damage = 35
                return spell
            end,
            shape = SpellShapeExamples.energyPulse()
        },
        
        -- Sawtooth shape
        {
            name = "chaosSawtooth",
            spell = function()
                local spell = SpellDef()
                spell.id = "chaosSawtooth"
                spell.type = "projectile"
                spell.sourceSprite = "icons/chaosBolt.png"
                spell.meshThickness = 0.05
                spell.speed = 20.0
                spell.lifetime = 2.5
                spell.behavior = "direct"
                spell.damage = 45
                return spell
            end,
            shape = SpellShapeExamples.chaosSawtooth()
        }
    }
    
    local entityIds = {}
    
    for i, shapeData in ipairs(shapes) do
        local spell = shapeData.spell()
        spell.shape = shapeData.shape
        
        local entityId = Spell.cast(spell, {
            x = player:getPosition().x,
            y = player:getPosition().y,
            dx = input:getMouseWorldPosition().x - player:getPosition().x,
            dy = input:getMouseWorldPosition().y - player:getPosition().y
        })
        
        SpellShape.addShape(entityId, shapeData.shape)
        SpellShape.bindWarpShader(entityId)
        
        table.insert(entityIds, entityId)
        print("Cast " .. shapeData.name .. " spell: " .. entityId)
        
        -- Delay between casts
        timer:schedule(i * 0.5, function()
            -- Update shader uniforms for this entity
            SpellShape.updateShaderUniforms(entityId, 0.0)
        end)
    end
    
    return entityIds
end

-- Example 7: Dynamic shape switching
function demonstrateShapeSwitching()
    -- Cast a spell with initial shape
    local spell = SpellDef()
    spell.id = "morphingSpell"
    spell.type = "projectile"
    spell.sourceSprite = "icons/morphingBolt.png"
    spell.meshThickness = 0.05
    spell.speed = 12.0
    spell.lifetime = 6.0
    spell.behavior = "direct"
    spell.damage = 25
    
    local initialShape = SpellShapePresets.straight()
    spell.shape = initialShape
    
    local entityId = Spell.cast(spell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, initialShape)
    
    print("Cast morphing spell: " .. entityId)
    
    -- Switch shapes over time
    local shapes = {
        {shape = SpellShapePresets.wave(0.3, 4.0), time = 1.0},
        {shape = SpellShapePresets.spiral(0.6, 2.0), time = 2.0},
        {shape = SpellShapePresets.vortex(0.8, 3.0), time = 3.0},
        {shape = SpellShapePresets.zigzag(0.4, 6.0), time = 4.0},
        {shape = SpellShapePresets.pulse(0.5, 3.0), time = 5.0}
    }
    
    for i, shapeData in ipairs(shapes) do
        timer:schedule(shapeData.time, function()
            -- Remove old shape and add new one
            SpellShape.removeShape(entityId)
            SpellShape.addShape(entityId, shapeData.shape)
            SpellShape.bindWarpShader(entityId)
            
            print("Switched spell " .. entityId .. " to shape " .. i)
        end)
    end
    
    return entityId
end

-- Example 8: CPU vs GPU deformation
function compareCPUGPUShapes()
    -- CPU deformation spell
    local cpuSpell = SpellDef()
    cpuSpell.id = "cpuWaveSpell"
    cpuSpell.type = "projectile"
    cpuSpell.sourceSprite = "icons/waveBolt.png"
    cpuSpell.meshThickness = 0.04
    cpuSpell.speed = 10.0
    cpuSpell.lifetime = 3.0
    cpuSpell.behavior = "direct"
    cpuSpell.damage = 15
    
    local cpuShape = SpellShapeUtils.createShape({
        kind = SpellShape.Kind.Wave,
        amplitude = 0.2,
        frequency = 4.0,
        useGPU = false,
        syncCollision = true
    })
    
    cpuSpell.shape = cpuShape
    
    local cpuEntityId = Spell.cast(cpuSpell, {
        x = player:getPosition().x - 2.0,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(cpuEntityId, cpuShape)
    
    -- GPU deformation spell
    local gpuSpell = SpellDef()
    gpuSpell.id = "gpuWaveSpell"
    gpuSpell.type = "projectile"
    gpuSpell.sourceSprite = "icons/waveBolt.png"
    gpuSpell.meshThickness = 0.04
    gpuSpell.speed = 10.0
    gpuSpell.lifetime = 3.0
    gpuSpell.behavior = "direct"
    gpuSpell.damage = 15
    
    local gpuShape = SpellShapeUtils.createShape({
        kind = SpellShape.Kind.Wave,
        amplitude = 0.2,
        frequency = 4.0,
        useGPU = true,
        warpShader = "shaders/waveWarp.glsl",
        syncCollision = true
    })
    
    gpuSpell.shape = gpuShape
    
    local gpuEntityId = Spell.cast(gpuSpell, {
        x = player:getPosition().x + 2.0,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(gpuEntityId, gpuShape)
    SpellShape.bindWarpShader(gpuEntityId)
    
    print("Cast CPU wave spell: " .. cpuEntityId)
    print("Cast GPU wave spell: " .. gpuEntityId)
    
    return {cpuEntityId, gpuEntityId}
end

-- Example 9: Collision shape updates
function demonstrateCollisionUpdates()
    local spell = SpellDef()
    spell.id = "collisionTestSpell"
    spell.type = "projectile"
    spell.sourceSprite = "icons/testBolt.png"
    spell.meshThickness = 0.05
    spell.speed = 8.0
    spell.lifetime = 5.0
    spell.behavior = "direct"
    spell.damage = 20
    
    -- Create a shape that changes collision bounds
    local collisionShape = SpellShapeUtils.createShape({
        kind = SpellShape.Kind.Pulse,
        amplitude = 0.8,
        frequency = 2.0,
        useGPU = true,
        warpShader = "shaders/pulseWarp.glsl",
        syncCollision = true
    })
    
    spell.shape = collisionShape
    
    local entityId = Spell.cast(spell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, collisionShape)
    SpellShape.bindWarpShader(entityId)
    
    -- Monitor collision updates
    timer:schedule(0.1, function()
        local shapeComponent = SpellShape.getShape(entityId)
        if shapeComponent then
            print("Spell " .. entityId .. " collision updated: " .. 
                  (shapeComponent.needsCollisionUpdate and "true" or "false"))
        end
    end)
    
    print("Cast collision test spell: " .. entityId)
    return entityId
end

-- Example 10: Shape monitoring and statistics
function monitorShapeSystem()
    local stats = SpellShape.getStats()
    
    print("Spell Shape System Statistics:")
    print("  Active shape components: " .. stats.activeShapeComponents)
    print("  GPU deformed meshes: " .. stats.gpuDeformedMeshes)
    print("  CPU deformed meshes: " .. stats.cpuDeformedMeshes)
    print("  Collision updates: " .. stats.collisionUpdates)
    print("  Average deformation time: " .. stats.averageDeformationTime .. "ms")
    print("  Average collision update time: " .. stats.averageCollisionUpdateTime .. "ms")
    
    -- Get all active shape components
    local activeShapes = {}
    for entityId, component in pairs(SpellShape.getAllShapes()) do
        if component.isActive then
            table.insert(activeShapes, {
                entityId = entityId,
                shapeKind = component.shape.kind,
                normalizedTime = component.normalizedTime,
                useGPU = component.shape.useGPU
            })
        end
    end
    
    print("Active shape components: " .. #activeShapes)
    for i, shapeInfo in ipairs(activeShapes) do
        print("  Entity " .. shapeInfo.entityId .. ": " .. 
              shapeInfo.shapeKind .. " (t=" .. string.format("%.2f", shapeInfo.normalizedTime) .. 
              ", GPU=" .. (shapeInfo.useGPU and "true" or "false") .. ")")
    end
end

-- Example 11: Hot-reload shape definitions
function setupShapeHotReload()
    -- Watch for shape definition changes
    SpellShape.watchShapeFiles()
    
    -- Reload shape definitions
    SpellShape.reloadShapeDefinitions()
    
    -- Reload warp shaders
    SpellShape.reloadWarpShaders()
    
    print("Shape system hot-reload setup complete")
end

-- Example 12: Performance optimization
function optimizeShapePerformance()
    local stats = SpellShape.getStats()
    
    -- Monitor deformation performance
    if stats.averageDeformationTime > 1.0 then
        print("Warning: Deformation time exceeds 1ms target")
        
        -- Switch complex shapes to GPU
        local activeShapes = SpellShape.getAllShapes()
        for entityId, component in pairs(activeShapes) do
            if not component.shape.useGPU and component.shape.kind ~= SpellShape.Kind.Straight then
                component.shape.useGPU = true
                SpellShape.bindWarpShader(entityId)
                print("Switched entity " .. entityId .. " to GPU deformation")
            end
        end
    end
    
    -- Monitor collision update performance
    if stats.averageCollisionUpdateTime > 0.5 then
        print("Warning: Collision update time exceeds 0.5ms target")
        
        -- Disable collision sync for non-critical shapes
        local activeShapes = SpellShape.getAllShapes()
        for entityId, component in pairs(activeShapes) do
            if component.shape.syncCollision and component.shape.kind == SpellShape.Kind.Straight then
                component.shape.syncCollision = false
                print("Disabled collision sync for entity " .. entityId)
            end
        end
    end
    
    -- Clean up inactive shapes
    if stats.activeShapeComponents > 100 then
        print("Too many active shape components, cleaning up...")
        SpellShape.cleanupInactiveShapes()
    end
end

-- Example 13: Integration with existing systems
function integrateWithSystems()
    -- Cast a spell with shape deformation
    local spell = SpellDef()
    spell.id = "integratedShapeSpell"
    spell.type = "projectile"
    spell.sourceSprite = "icons/integratedBolt.png"
    spell.meshThickness = 0.06
    spell.speed = 14.0
    spell.lifetime = 3.5
    spell.behavior = "direct"
    spell.damage = 30
    
    local shape = SpellShapeExamples.fireSpiral()
    spell.shape = shape
    
    local entityId = Spell.cast(spell, {
        x = player:getPosition().x,
        y = player:getPosition().y,
        dx = input:getMouseWorldPosition().x - player:getPosition().x,
        dy = input:getMouseWorldPosition().y - player:getPosition().y
    })
    
    SpellShape.addShape(entityId, shape)
    SpellShape.bindWarpShader(entityId)
    
    -- Integrate with mesh system
    local shapeComponent = SpellShape.getShape(entityId)
    if shapeComponent then
        -- Apply shape to mesh asset
        local meshAsset = Spell.getSpell(entityId).asset.meshAsset
        if meshAsset then
            SpellShape.applyShapeToMesh(entityId, meshAsset)
            print("Applied shape deformation to mesh asset")
        end
        
        -- Update collision shape
        SpellShape.updateCollisionForEntity(entityId)
        print("Updated collision shape for entity " .. entityId)
    end
    
    print("Cast integrated shape spell: " .. entityId)
    return entityId
end

-- Example 14: Complex shape combinations
function castShapeCombination()
    local playerPos = player:getPosition()
    local targetPos = input:getMouseWorldPosition()
    
    -- Cast multiple shaped spells in sequence
    local shapeSpells = {
        {
            name = "Wave Spell",
            shape = SpellShapeExamples.emberWave(),
            delay = 0.0
        },
        {
            name = "Arc Spell",
            shape = SpellShapeExamples.lightningArc(),
            delay = 0.5
        },
        {
            name = "Spiral Spell",
            shape = SpellShapeExamples.fireSpiral(),
            delay = 1.0
        },
        {
            name = "Vortex Spell",
            shape = SpellShapeExamples.iceVortex(),
            delay = 1.5
        },
        {
            name = "Burst Spell",
            shape = SpellShapeExamples.arcaneBurst(),
            delay = 2.0
        }
    }
    
    local entityIds = {}
    
    for i, spellData in ipairs(shapeSpells) do
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
            
            SpellShape.addShape(entityId, spellData.shape)
            SpellShape.bindWarpShader(entityId)
            
            table.insert(entityIds, entityId)
            print("Cast " .. spellData.name .. ": " .. entityId)
        end)
    end
    
    print("Cast shape combination with delays")
    return entityIds
end

-- Main usage example
function main()
    print("Dynamic Spell-Shaping for Mesh-Based Projectiles Example")
    print("========================================================")
    
    -- Initialize the shape system
    SpellShape.update(0.0) -- Initialize if needed
    
    -- Run examples
    print("1. Applying basic shapes...")
    local straightId = applyBasicShapes()
    
    print("2. Applying wave shape...")
    local waveId = applyWaveShape()
    
    print("3. Applying arc shape...")
    local arcId = applyArcShape()
    
    print("4. Applying spiral shape...")
    local spiralId = applySpiralShape()
    
    print("5. Applying vortex shape...")
    local vortexId = applyVortexShape()
    
    print("6. Applying advanced shapes...")
    local advancedIds = applyAdvancedShapes()
    
    print("7. Demonstrating shape switching...")
    local morphingId = demonstrateShapeSwitching()
    
    print("8. Comparing CPU vs GPU deformation...")
    local comparisonIds = compareCPUGPUShapes()
    
    print("9. Demonstrating collision updates...")
    local collisionId = demonstrateCollisionUpdates()
    
    print("10. Monitoring shape system...")
    monitorShapeSystem()
    
    print("11. Setting up shape hot-reload...")
    setupShapeHotReload()
    
    print("12. Optimizing shape performance...")
    optimizeShapePerformance()
    
    print("13. Integrating with systems...")
    local integratedId = integrateWithSystems()
    
    print("14. Casting shape combinations...")
    local combinationIds = castShapeCombination()
    
    print("Dynamic spell-shaping examples completed!")
    print("Generated shaped spells with mesh deformation and GPU warping")
end

-- Run the example
main() 