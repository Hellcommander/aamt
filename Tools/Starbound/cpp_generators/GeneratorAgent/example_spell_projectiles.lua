-- Spell Projectile System Example
-- Demonstrates 3D mesh projectiles with advanced features

require("spells")

-- Example 1: Basic fireball projectile
function castFireball(player, targetPos)
    local fireballDef = ProjectileDefs.fireball()
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local projectileId = SpellProjectile.spawn(fireballDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- On impact callback
        world:spawnDamage(player.id, hit.position, fireballDef.damage, fireballDef.damageType)
        world:spawnParticles("fire_explosion", hit.position, hit.normal)
        world:playSound("fireball_explosion", hit.position)
    end)
    
    return projectileId
end

-- Example 2: Homing lightning bolt
function castLightningBolt(player, targetEntityId)
    local lightningDef = ProjectileDefs.lightningBolt()
    
    local playerPos = player:getPosition()
    local targetPos = world:getEntityPosition(targetEntityId)
    local direction = (targetPos - playerPos):normalize()
    
    local projectileId = SpellProjectile.spawn(lightningDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Chain lightning effect
        local nearbyEnemies = world:getEntitiesInRadius(hit.position, lightningDef.chainRange, "enemy")
        local chainCount = 0
        
        for _, enemyId in ipairs(nearbyEnemies) do
            if chainCount < lightningDef.maxChainCount then
                local damage = lightningDef.damage * math.pow(lightningDef.chainDamageFalloff, chainCount)
                world:spawnDamage(player.id, world:getEntityPosition(enemyId), damage, lightningDef.damageType)
                world:spawnParticles("lightning_chain", world:getEntityPosition(enemyId))
                chainCount = chainCount + 1
            end
        end
        
        world:playSound("lightning_impact", hit.position)
    end)
    
    return projectileId
end

-- Example 3: Bouncing ice bolt
function castIceBolt(player, direction)
    local iceDef = ProjectileDefs.iceBolt()
    
    local playerPos = player:getPosition()
    
    local projectileId = SpellProjectile.spawn(iceDef, {
        x = playerPos.x,
        y = playerPos.y,
        z = playerPos.z,
        dx = direction.x,
        dy = direction.y,
        dz = direction.z
    }, function(hit)
        -- Ice bolt can pierce and bounce
        if hit.isPenetrating then
            -- Continue projectile with reduced damage
            local newDef = iceDef
            newDef.damage = newDef.damage * 0.7
            SpellProjectile.spawn(newDef, {
                x = hit.position.x,
                y = hit.position.y,
                z = hit.position.z,
                dx = hit.normal.x,
                dy = hit.normal.y,
                dz = hit.normal.z
            })
        else
            world:spawnDamage(player.id, hit.position, iceDef.damage, iceDef.damageType)
            world:spawnParticles("ice_impact", hit.position, hit.normal)
        end
        
        world:playSound("ice_impact", hit.position)
    end)
    
    return projectileId
end

-- Example 4: Custom projectile definition
function createCustomProjectile()
    local customDef = SpellUtils.createDef({
        id = "custom_missile",
        meshPath = "models/projectiles/custom_missile.glb",
        speed = 25.0,
        lifetime = 5.0,
        collisionRadius = 0.4,
        damage = 50,
        damageType = "magic",
        homing = true,
        impactEffect = "particles/custom_explosion.json",
        trailEffect = "particles/custom_trail.json",
        behaviors = {"explosive", "piercing"}
    })
    
    return customDef
end

-- Example 5: Batch projectile spawning
function castMultiProjectile(player, targetPos)
    local projectileDefs = {
        ProjectileDefs.fireball(),
        ProjectileDefs.iceBolt(),
        ProjectileDefs.lightningBolt()
    }
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local positions = {
        playerPos + glm.vec3(0.5, 0, 0),
        playerPos + glm.vec3(-0.5, 0, 0),
        playerPos + glm.vec3(0, 0.5, 0)
    }
    
    local projectileIds = SpellProjectile.spawnBatch(projectileDefs, positions, function(hit)
        world:spawnDamage(player.id, hit.position, 30, "mixed")
        world:spawnParticles("mixed_explosion", hit.position, hit.normal)
    end)
    
    return projectileIds
end

-- Example 6: Advanced projectile with custom behavior
function castAdvancedProjectile(player, targetPos)
    local def = ProjectileDefs.arcaneMissile()
    
    -- Modify the definition for advanced behavior
    def.homingStrength = 0.8
    def.maxChainCount = 5
    def.chainRange = 4.0
    def.explosionRadius = 3.0
    def.explosionDamage = 25.0
    
    local playerPos = player:getPosition()
    local direction = (targetPos - playerPos):normalize()
    
    local projectileId = SpellProjectile.spawn(def, {
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
            world:applyStatusEffect(hit.entityId, "arcane_burn", 5.0)
            
            -- Chain to nearby enemies
            local nearbyEnemies = world:getEntitiesInRadius(hit.position, def.chainRange, "enemy")
            local chainCount = 0
            
            for _, enemyId in ipairs(nearbyEnemies) do
                if enemyId ~= hit.entityId and chainCount < def.maxChainCount then
                    local chainDamage = def.damage * math.pow(0.8, chainCount)
                    world:spawnDamage(player.id, world:getEntityPosition(enemyId), chainDamage, def.damageType)
                    world:spawnParticles("arcane_chain", world:getEntityPosition(enemyId))
                    chainCount = chainCount + 1
                end
            end
            
            -- Explosion effect
            if def.explosionRadius > 0 then
                local explosionTargets = world:getEntitiesInRadius(hit.position, def.explosionRadius, "enemy")
                for _, targetId in ipairs(explosionTargets) do
                    local distance = (world:getEntityPosition(targetId) - hit.position):length()
                    local damage = def.explosionDamage * (1.0 - distance / def.explosionRadius)
                    world:spawnDamage(player.id, world:getEntityPosition(targetId), damage, def.damageType)
                end
            end
        else
            -- Hit on environment
            world:spawnParticles("arcane_impact", hit.position, hit.normal)
        end
        
        world:playSound("arcane_explosion", hit.position)
    end)
    
    return projectileId
end

-- Example 7: Projectile management and queries
function manageProjectiles()
    -- Get all active projectiles
    local allProjectiles = SpellProjectile.getByType("fireball")
    
    -- Get projectiles in a specific area
    local centerPos = glm.vec3(10, 5, 0)
    local nearbyProjectiles = SpellProjectile.getInRadius(centerPos, 5.0)
    
    -- Find targets for homing projectiles
    local playerPos = player:getPosition()
    local nearestEnemy = SpellProjectile.findNearestTarget(playerPos, "enemy", 20.0)
    
    if nearestEnemy then
        local enemyPos = world:getEntityPosition(nearestEnemy)
        castLightningBolt(player, nearestEnemy)
    end
    
    -- Destroy specific projectile
    if allProjectiles[1] then
        SpellProjectile.destroy(allProjectiles[1].entityId)
    end
end

-- Example 8: Custom projectile with mesh generation
function createGeneratedProjectile()
    -- Generate a custom mesh projectile using the mesh system
    local meshData = {
        vertices = {
            -- Custom vertex data for projectile
            {position = {0, 0, 0}, normal = {0, 1, 0}, texcoord = {0, 0}},
            {position = {1, 0, 0}, normal = {0, 1, 0}, texcoord = {1, 0}},
            {position = {0, 1, 0}, normal = {0, 1, 0}, texcoord = {0, 1}}
        },
        indices = {0, 1, 2}
    }
    
    -- Create mesh asset
    local meshAsset = MeshManager:createMeshFromData(meshData.vertices, meshData.indices, "custom_projectile")
    
    -- Create projectile definition using the generated mesh
    local def = SpellUtils.createDef({
        id = "generated_projectile",
        meshPath = meshAsset.path,
        speed = 15.0,
        lifetime = 3.0,
        damage = 20,
        damageType = "physical"
    })
    
    return def
end

-- Example 9: Integration with AI art generation
function createAIGeneratedProjectile()
    -- Use AI art generation to create projectile textures
    local artPrompt = {
        description = "magical energy projectile, glowing blue, 3D model texture",
        style = "pixel-art",
        resolution = 64,
        frameCount = 1,
        direction = "single",
        useAlpha = true,
        specialEffects = {"glowing", "magical"}
    }
    
    -- Generate art using the AI system
    local artOutput = AIArtGenerator:generateSprite(artPrompt)
    
    if artOutput.success then
        -- Create projectile definition with AI-generated texture
        local def = SpellUtils.createDef({
            id = "ai_generated_projectile",
            meshPath = "models/projectiles/default.glb",
            materialPath = artOutput.spriteFile,
            speed = 18.0,
            lifetime = 4.0,
            damage = 25,
            damageType = "magic",
            useGlow = true,
            glowColor = {0.3, 0.6, 1.0},
            glowIntensity = 0.8
        })
        
        return def
    end
    
    return nil
end

-- Example 10: Performance monitoring
function monitorProjectilePerformance()
    local stats = SpellProjectile.getStats()
    
    print("Projectile Statistics:")
    print("  Total spawned: " .. stats.totalProjectilesSpawned)
    print("  Total destroyed: " .. stats.totalProjectilesDestroyed)
    print("  Total impacts: " .. stats.totalImpacts)
    print("  Total chains: " .. stats.totalChains)
    print("  Total explosions: " .. stats.totalExplosions)
    print("  Active projectiles: " .. stats.activeProjectiles)
    print("  Average lifetime: " .. stats.averageLifetime)
    
    -- Clear cache if needed
    if stats.activeProjectiles > 100 then
        SpellProjectile.clearCache()
        print("Cache cleared due to high projectile count")
    end
end

-- Main usage example
function main()
    print("Spell Projectile System Example")
    print("================================")
    
    -- Initialize systems
    SpellProjectileSystem:initialize()
    
    -- Example usage
    local player = world:getPlayer()
    local targetPos = glm.vec3(20, 10, 0)
    
    -- Cast different types of projectiles
    local fireballId = castFireball(player, targetPos)
    local lightningId = castLightningBolt(player, 123) -- target entity ID
    local iceId = castIceBolt(player, glm.vec3(1, 0, 0))
    
    -- Create custom projectile
    local customDef = createCustomProjectile()
    local customId = SpellProjectile.spawn(customDef, {
        x = 0, y = 5, z = 0,
        dx = 1, dy = 0, dz = 0
    })
    
    -- Monitor performance
    monitorProjectilePerformance()
    
    print("Projectiles spawned successfully!")
    print("Fireball ID: " .. fireballId)
    print("Lightning ID: " .. lightningId)
    print("Ice Bolt ID: " .. iceId)
    print("Custom ID: " .. customId)
end

-- Run the example
main() 