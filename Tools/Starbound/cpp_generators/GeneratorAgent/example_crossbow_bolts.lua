-- Crossbow Bolt System Example
-- Demonstrates various bolt types and behaviors

require("weapons")

-- Example 1: Basic steel bolt
function fireSteelBolt(player, targetPos)
    local steelBoltDef = BoltDefs.steelBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(steelBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Basic impact - direct damage only
        world:spawnDamage(player.id, hit.position, steelBoltDef.damage, steelBoltDef.damageType)
        world:playSound("bolt_impact", hit.position)
    end)
    
    return boltId
end

-- Example 2: Explosive bolt
function fireExplosiveBolt(player, targetPos)
    local explosiveBoltDef = BoltDefs.explosiveBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(explosiveBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Explosive impact - area damage
        world:spawnDamage(player.id, hit.position, explosiveBoltDef.damage, explosiveBoltDef.damageType)
        world:spawnParticles("explosion", hit.position, hit.normal)
        
        -- Area of effect damage
        local nearbyEnemies = world:getEntitiesInRadius(hit.position, explosiveBoltDef.areaRadius, "enemy")
        for _, enemyId in ipairs(nearbyEnemies) do
            local distance = (world:getEntityPosition(enemyId) - hit.position):length()
            local damage = explosiveBoltDef.damage * (1.0 - distance / explosiveBoltDef.areaRadius)
            world:spawnDamage(player.id, world:getEntityPosition(enemyId), damage, explosiveBoltDef.damageType)
        end
        
        world:playSound("explosion", hit.position)
    end)
    
    return boltId
end

-- Example 3: Frost bolt with spell effects
function fireFrostBolt(player, targetPos)
    local frostBoltDef = BoltDefs.frostBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(frostBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Spell impact - apply status effects
        world:spawnDamage(player.id, hit.position, frostBoltDef.damage, frostBoltDef.damageType)
        world:spawnParticles("frost_burst", hit.position, hit.normal)
        
        -- Apply frost status effect
        if hit.entityId > 0 then
            world:applyStatusEffect(hit.entityId, frostBoltDef.statusEffect, frostBoltDef.spellDuration)
        end
        
        -- Frost area effect
        local nearbyEnemies = world:getEntitiesInRadius(hit.position, frostBoltDef.spellRadius, "enemy")
        for _, enemyId in ipairs(nearbyEnemies) do
            world:applyStatusEffect(enemyId, "slow", frostBoltDef.spellDuration)
            world:spawnParticles("frost_chill", world:getEntityPosition(enemyId))
        end
        
        world:playSound("frost_impact", hit.position)
    end)
    
    return boltId
end

-- Example 4: Lightning bolt with chaining
function fireLightningBolt(player, targetPos)
    local lightningBoltDef = BoltDefs.lightningBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(lightningBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Lightning impact with chaining
        world:spawnDamage(player.id, hit.position, lightningBoltDef.damage, lightningBoltDef.damageType)
        world:spawnParticles("lightning_burst", hit.position, hit.normal)
        
        -- Apply shock status effect
        if hit.entityId > 0 then
            world:applyStatusEffect(hit.entityId, lightningBoltDef.statusEffect, lightningBoltDef.spellDuration)
        end
        
        -- Chain lightning effect
        local nearbyEnemies = world:getEntitiesInRadius(hit.position, lightningBoltDef.spellRadius, "enemy")
        local chainCount = 0
        local maxChains = 3
        
        for _, enemyId in ipairs(nearbyEnemies) do
            if chainCount < maxChains then
                local chainDamage = lightningBoltDef.damage * math.pow(0.7, chainCount)
                world:spawnDamage(player.id, world:getEntityPosition(enemyId), chainDamage, lightningBoltDef.damageType)
                world:spawnParticles("lightning_chain", world:getEntityPosition(enemyId))
                world:applyStatusEffect(enemyId, "stun", 1.0)
                chainCount = chainCount + 1
            end
        end
        
        world:playSound("lightning_impact", hit.position)
    end)
    
    return boltId
end

-- Example 5: Piercing bolt
function firePiercingBolt(player, targetPos)
    local piercingBoltDef = BoltDefs.piercingBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(piercingBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Piercing impact - can pass through multiple targets
        if hit.isPenetrating then
            -- Continue bolt with reduced damage
            local newDef = piercingBoltDef
            newDef.damage = math.floor(newDef.damage * piercingBoltDef.penetrationDamageFalloff)
            
            Crossbow.spawn(newDef, {
                x = hit.position.x,
                y = hit.position.y,
                z = hit.position.z,
                dx = hit.normal.x,
                dy = hit.normal.y,
                dz = hit.normal.z
            })
        else
            -- Final impact
            world:spawnDamage(player.id, hit.position, piercingBoltDef.damage, piercingBoltDef.damageType)
        end
        
        world:playSound("piercing_impact", hit.position)
    end)
    
    return boltId
end

-- Example 6: Homing bolt
function fireHomingBolt(player, targetEntityId)
    local homingBoltDef = BoltDefs.homingBolt()
    
    local playerPos = player:getPosition()
    local targetPos = world:getEntityPosition(targetEntityId)
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(homingBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Homing bolt impact
        world:spawnDamage(player.id, hit.position, homingBoltDef.damage, homingBoltDef.damageType)
        world:spawnParticles("homing_impact", hit.position, hit.normal)
        world:playSound("homing_impact", hit.position)
    end)
    
    return boltId
end

-- Example 7: Arcane bolt with complex effects
function fireArcaneBolt(player, targetPos)
    local arcaneBoltDef = BoltDefs.arcaneBolt()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(arcaneBoltDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Arcane impact with multiple effects
        world:spawnDamage(player.id, hit.position, arcaneBoltDef.damage, arcaneBoltDef.damageType)
        world:spawnParticles("arcane_burst", hit.position, hit.normal)
        
        -- Apply arcane burn status effect
        if hit.entityId > 0 then
            world:applyStatusEffect(hit.entityId, arcaneBoltDef.statusEffect, arcaneBoltDef.spellDuration)
        end
        
        -- Arcane area effect
        local nearbyEnemies = world:getEntitiesInRadius(hit.position, arcaneBoltDef.spellRadius, "enemy")
        for _, enemyId in ipairs(nearbyEnemies) do
            -- Apply weakening effect
            world:applyStatusEffect(enemyId, "weaken", arcaneBoltDef.spellDuration)
            
            -- Apply burning damage over time
            world:applyStatusEffect(enemyId, "burn", arcaneBoltDef.spellDuration)
            
            -- Visual effect
            world:spawnParticles("arcane_burn", world:getEntityPosition(enemyId))
        end
        
        world:playSound("arcane_impact", hit.position)
    end)
    
    return boltId
end

-- Example 8: Custom bolt definition
function createCustomBolt()
    local customBoltDef = BoltUtils.createDef({
        id = "custom_bolt",
        meshPath = "models/bolts/bolt_custom.glb",
        speed = 38.0,
        lifetime = 4.0,
        collisionRadius = 0.18,
        behavior = "spell",
        damage = 35,
        damageType = "magic",
        spellEffect = "particles/custom_burst.json",
        statusEffect = "custom_effect",
        spellRadius = 2.5,
        spellDuration = 3.5,
        spellBehaviors = {"custom_effect", "visual_flash"}
    })
    
    return customBoltDef
end

-- Example 9: Batch bolt firing
function fireBoltVolley(player, targetPos)
    local boltDefs = {
        BoltDefs.steelBolt(),
        BoltDefs.explosiveBolt(),
        BoltDefs.frostBolt()
    }
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    -- Spread the bolts slightly
    local positions = {
        playerPos + glm.vec3(0.3, 0, 0),
        playerPos + glm.vec3(-0.3, 0, 0),
        playerPos + glm.vec3(0, 0.3, 0)
    }
    
    local boltIds = Crossbow.spawnBatch(boltDefs, positions, function(hit)
        world:spawnDamage(player.id, hit.position, 25, "mixed")
        world:spawnParticles("mixed_impact", hit.position, hit.normal)
    end)
    
    return boltIds
end

-- Example 10: Bolt management and queries
function manageBolts()
    -- Get all active bolts
    local allBolts = Crossbow.getByType("steelBolt")
    
    -- Get bolts in a specific area
    local centerPos = glm.vec3(10, 5, 0)
    local nearbyBolts = Crossbow.getInRadius(centerPos, 5.0)
    
    -- Find targets for homing bolts
    local playerPos = player:getPosition()
    local nearestEnemy = Crossbow.findNearestTarget(playerPos, "enemy", 20.0)
    
    if nearestEnemy then
        fireHomingBolt(player, nearestEnemy)
    end
    
    -- Destroy specific bolt
    if allBolts[1] then
        Crossbow.destroy(allBolts[1].entityId)
    end
    
    -- Get statistics
    local stats = Crossbow.getStats()
    print("Active bolts: " .. stats.activeBolts)
    print("Total spawned: " .. stats.totalBoltsSpawned)
    print("Total impacts: " .. stats.totalImpacts)
end

-- Example 11: Integration with crossbow generation
function createCrossbowWithBolts()
    -- Generate crossbow with custom bolt support
    local crossbowParams = CrossbowParams()
    crossbowParams.id = "magic_crossbow"
    crossbowParams.useMeshProjectiles = true
    crossbowParams.projectileType = "bolt"
    
    -- Register custom bolt types
    Crossbow.registerBoltDef(BoltDefs.arcaneBolt())
    Crossbow.registerBoltDef(BoltDefs.lightningBolt())
    
    -- Generate the crossbow assets
    local crossbowBundle = generateCrossbowAssets(crossbowParams, config)
    
    return crossbowBundle
end

-- Example 12: Performance monitoring
function monitorBoltPerformance()
    local stats = Crossbow.getStats()
    
    print("Bolt System Statistics:")
    print("  Total spawned: " .. stats.totalBoltsSpawned)
    print("  Total destroyed: " .. stats.totalBoltsDestroyed)
    print("  Total impacts: " .. stats.totalImpacts)
    print("  Total penetrations: " .. stats.totalPenetrations)
    print("  Total explosions: " .. stats.totalExplosions)
    print("  Total spell triggers: " .. stats.totalSpellTriggers)
    print("  Active bolts: " .. stats.activeBolts)
    print("  Average lifetime: " .. stats.averageLifetime)
    
    -- Clear cache if needed
    if stats.activeBolts > 50 then
        Crossbow.clearCache()
        print("Cache cleared due to high bolt count")
    end
end

-- Example 13: Advanced bolt with multiple behaviors
function fireAdvancedBolt(player, targetPos)
    local def = BoltDefs.arcaneBolt()
    
    -- Modify for advanced behavior
    def.behavior = "spell"
    def.spellRadius = 4.0
    def.spellDuration = 5.0
    def.maxPenetrations = 2
    def.penetrationDamageFalloff = 0.8
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local boltId = Crossbow.spawn(def, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Complex impact behavior
        if hit.entityType == "enemy" then
            -- Direct hit on enemy
            world:spawnDamage(player.id, hit.position, def.damage, def.damageType)
            
            -- Apply status effect
            world:applyStatusEffect(hit.entityId, def.statusEffect, def.spellDuration)
            
            -- Arcane area effect
            local nearbyEnemies = world:getEntitiesInRadius(hit.position, def.spellRadius, "enemy")
            for _, enemyId in ipairs(nearbyEnemies) do
                if enemyId ~= hit.entityId then
                    local distance = (world:getEntityPosition(enemyId) - hit.position):length()
                    local damage = def.damage * (1.0 - distance / def.spellRadius)
                    world:spawnDamage(player.id, world:getEntityPosition(enemyId), damage, def.damageType)
                    world:applyStatusEffect(enemyId, "weaken", def.spellDuration)
                    world:spawnParticles("arcane_chain", world:getEntityPosition(enemyId))
                end
            end
        else
            -- Hit on environment
            world:spawnParticles("arcane_impact", hit.position, hit.normal)
        end
        
        world:playSound("arcane_explosion", hit.position)
    end)
    
    return boltId
end

-- Main usage example
function main()
    print("Crossbow Bolt System Example")
    print("============================")
    
    -- Initialize systems
    CrossbowBoltSystem:initialize()
    
    -- Example usage
    local player = world:getPlayer()
    local targetPos = glm.vec3(20, 10, 0)
    
    -- Fire different types of bolts
    local steelId = fireSteelBolt(player, targetPos)
    local explosiveId = fireExplosiveBolt(player, targetPos)
    local frostId = fireFrostBolt(player, targetPos)
    local lightningId = fireLightningBolt(player, targetPos)
    local piercingId = firePiercingBolt(player, targetPos)
    
    -- Create custom bolt
    local customDef = createCustomBolt()
    local customId = Crossbow.spawn(customDef, {
        x = 0, y = 5, z = 0,
        dx = 1, dy = 0, dz = 0
    })
    
    -- Monitor performance
    monitorBoltPerformance()
    
    print("Bolts fired successfully!")
    print("Steel Bolt ID: " .. steelId)
    print("Explosive Bolt ID: " .. explosiveId)
    print("Frost Bolt ID: " .. frostId)
    print("Lightning Bolt ID: " .. lightningId)
    print("Piercing Bolt ID: " .. piercingId)
    print("Custom Bolt ID: " .. customId)
end

-- Run the example
main() 