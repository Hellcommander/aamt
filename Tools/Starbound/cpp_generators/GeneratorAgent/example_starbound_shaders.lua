-- Starbound Shader Suite Example
-- Demonstrates GLSL shaders for offline baking and real-time VFX

require("shaders")

-- Example 1: Basic shader usage
function basicShaderUsage()
    -- Get a shader program
    local paletteShader = StarboundShaders.getPaletteQuantizationShader()
    local cellShadingShader = StarboundShaders.getCellShadingShader()
    
    if paletteShader and paletteShader.isLoaded then
        print("Palette quantization shader loaded successfully")
    end
    
    if cellShadingShader and cellShadingShader.isLoaded then
        print("Cell shading shader loaded successfully")
    end
end

-- Example 2: Palette quantization for texture baking
function applyPaletteQuantization(sourceTexture, paletteTexture)
    local pass = StarboundShaders.createPaletteQuantizationPass(paletteTexture)
    
    -- Set uniforms
    pass:setInt("paletteSize", 32)
    pass:setBool("useDithering", true)
    pass:setBool("useLAB", false)
    
    -- Set textures
    pass:setTexture("sourceTex", sourceTexture, 0)
    pass:setTexture("paletteTex", paletteTexture, 1)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Palette quantization applied")
end

-- Example 3: Pixel grid snapping for crisp sprites
function applyPixelGridSnap(sourceTexture, targetResolution)
    local pass = StarboundShaders.createPixelGridSnapPass(targetResolution)
    
    -- Set uniforms
    pass:setBool("enableSnap", true)
    pass:setFloat("snapStrength", 1.0)
    
    -- Set textures
    pass:setTexture("sceneTex", sourceTexture, 0)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Pixel grid snapping applied")
end

-- Example 4: Outline extraction for sprite frames
function extractOutlines(sourceTexture, targetResolution)
    local pass = StarboundShaders.createOutlineExtractionPass(targetResolution)
    
    -- Set uniforms
    pass:setVec4("outlineColor", {0.0, 0.0, 0.0, 1.0}) -- Black outline
    pass:setFloat("outlineThreshold", 0.5)
    pass:setFloat("outlineWidth", 1.0)
    
    -- Set textures
    pass:setTexture("src", sourceTexture, 0)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Outline extraction completed")
end

-- Example 5: Cell shading for toon lighting
function applyCellShading(baseTexture, normalTexture, lightDirection, lightColor)
    local pass = StarboundShaders.createCellShadingPass(lightDirection, lightColor)
    
    -- Set uniforms
    pass:setInt("shadingLevels", 3)
    pass:setBool("useNormalMap", true)
    pass:setBool("useRimLighting", true)
    pass:setFloat("rimPower", 4.0)
    pass:setFloat("rimIntensity", 0.5)
    pass:setVec3("lightColor", lightColor)
    pass:setVec3("ambientColor", {0.3, 0.3, 0.3})
    pass:setFloat("lightIntensity", 1.0)
    
    -- Set textures
    pass:setTexture("diffuseTex", baseTexture, 0)
    pass:setTexture("normalTex", normalTexture, 1)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Cell shading applied")
end

-- Example 6: Emissive glow for magical effects
function applyEmissiveGlow(baseTexture, emissiveTexture, time)
    local pass = StarboundShaders.createEmissiveGlowPass(time)
    
    -- Set uniforms
    pass:setVec3("glowColor", {1.0, 0.5, 0.0}) -- Orange glow
    pass:setFloat("glowIntensity", 1.0)
    pass:setFloat("pulseSpeed", 3.0)
    pass:setFloat("pulseAmplitude", 0.5)
    pass:setFloat("glowRadius", 2.0)
    pass:setBool("additiveBlend", true)
    
    -- Set textures
    pass:setTexture("baseTex", baseTexture, 0)
    pass:setTexture("emissiveMap", emissiveTexture, 1)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Emissive glow applied")
end

-- Example 7: Dissolve effect for magic spells
function applyDissolveEffect(baseTexture, noiseTexture, threshold, time)
    local pass = StarboundShaders.createDissolvePass(threshold, noiseTexture)
    
    -- Set uniforms
    pass:setVec3("dissolveColor", {1.0, 0.5, 0.0}) -- Orange dissolve
    pass:setFloat("dissolveWidth", 0.1)
    pass:setBool("animated", true)
    pass:setFloat("animationSpeed", 1.0)
    
    -- Set textures
    pass:setTexture("baseTex", baseTexture, 0)
    pass:setTexture("noiseTex", noiseTexture, 1)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Dissolve effect applied")
end

-- Example 8: Damage overlay for damaged items
function applyDamageOverlay(baseTexture, damageMask, damageDecal, intensity)
    local pass = StarboundShaders.createDamageOverlayPass(damageMask, damageDecal, intensity)
    
    -- Set uniforms
    pass:setVec3("damageTint", {0.8, 0.2, 0.1}) -- Reddish damage color
    pass:setFloat("damageSaturation", 1.5)
    pass:setBool("useDamageTint", true)
    pass:setBool("useDamageDecal", true)
    
    -- Set textures
    pass:setTexture("baseTex", baseTexture, 0)
    pass:setTexture("damageMask", damageMask, 1)
    pass:setTexture("damageDecal", damageDecal, 2)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Damage overlay applied")
end

-- Example 9: Water ripple effect
function applyWaterRipple(sceneTexture, rippleMap, time)
    local pass = StarboundShaders.createWaterRipplePass(time, rippleMap)
    
    -- Set uniforms
    pass:setFloat("rippleSpeed", 0.1)
    pass:setFloat("rippleStrength", 0.03)
    pass:setFloat("rippleScale", 1.0)
    pass:setVec2("rippleDirection", {1.0, 0.0})
    pass:setBool("animated", true)
    
    -- Set textures
    pass:setTexture("sceneTex", sceneTexture, 0)
    pass:setTexture("rippleMap", rippleMap, 1)
    
    -- Execute the shader pass
    pass:execute()
    
    print("Water ripple effect applied")
end

-- Example 10: Complete baking pipeline
function runBakingPipeline(meshTexture, paletteTexture, targetResolution)
    local pipeline = StarboundShaders.createBakingPipeline(targetResolution, paletteTexture)
    
    print("Running baking pipeline with " .. #pipeline .. " passes")
    
    -- Execute each pass in sequence
    for i, pass in ipairs(pipeline) do
        print("Executing pass " .. i .. ": " .. pass.name)
        
        -- Set input texture for first pass
        if i == 1 then
            pass:setTexture("sourceTex", meshTexture, 0)
        end
        
        pass:execute()
    end
    
    print("Baking pipeline completed")
end

-- Example 11: VFX pipeline for real-time effects
function runVFXPipeline(baseTexture, time)
    local pipeline = StarboundShaders.createVFXPipeline()
    
    print("Running VFX pipeline with " .. #pipeline .. " passes")
    
    -- Execute each pass in sequence
    for i, pass in ipairs(pipeline) do
        print("Executing VFX pass " .. i .. ": " .. pass.name)
        
        -- Set common uniforms
        if pass.name == "emissiveGlow" then
            pass:setFloat("time", time)
        end
        
        -- Set base texture
        pass:setTexture("baseTex", baseTexture, 0)
        
        pass:execute()
    end
    
    print("VFX pipeline completed")
end

-- Example 12: Custom shader creation
function createCustomShader()
    local vertexSource = [[
        #version 330 core
        layout(location = 0) in vec2 position;
        layout(location = 1) in vec2 texCoord;
        
        out vec2 vTexCoord;
        
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            vTexCoord = texCoord;
        }
    ]]
    
    local fragmentSource = [[
        #version 330 core
        in vec2 vTexCoord;
        
        uniform sampler2D baseTex;
        uniform float intensity;
        uniform vec3 tintColor;
        
        out vec4 fragColor;
        
        void main() {
            vec4 base = texture(baseTex, vTexCoord);
            vec3 tinted = mix(base.rgb, tintColor, intensity);
            fragColor = vec4(tinted, base.a);
        }
    ]]
    
    local customShader = ShaderUtils.createShaderFromSource("custom_tint", vertexSource, fragmentSource)
    
    if customShader then
        print("Custom shader created successfully")
        return customShader
    else
        print("Failed to create custom shader")
        return nil
    end
end

-- Example 13: Shader pass with custom uniforms
function createCustomShaderPass()
    local shader = createCustomShader()
    if not shader then return nil end
    
    local pass = ShaderUtils.createShaderPass("custom_tint_pass", shader)
    
    -- Set uniforms
    pass:setFloat("intensity", 0.5)
    pass:setVec3("tintColor", {1.0, 0.0, 0.0}) -- Red tint
    
    return pass
end

-- Example 14: Animated effects
function createAnimatedEffects(baseTexture, time)
    -- Create multiple passes for different effects
    local passes = {}
    
    -- Emissive glow with pulsing
    local glowPass = StarboundShaders.createEmissiveGlowPass(time)
    glowPass:setTexture("baseTex", baseTexture, 0)
    glowPass:setFloat("pulseSpeed", 2.0)
    table.insert(passes, glowPass)
    
    -- Water ripple effect
    local ripplePass = StarboundShaders.createWaterRipplePass(time, "textures/ripple.png")
    ripplePass:setTexture("sceneTex", baseTexture, 0)
    ripplePass:setFloat("rippleSpeed", 0.15)
    table.insert(passes, ripplePass)
    
    -- Execute all passes
    ShaderUtils.executePipeline(passes)
    
    print("Animated effects applied")
end

-- Example 15: Performance monitoring
function monitorShaderPerformance()
    local stats = StarboundShaders.getStats()
    
    print("Shader Performance Statistics:")
    print("  Total shaders: " .. stats.totalShaders)
    print("  Loaded shaders: " .. stats.loadedShaders)
    print("  Failed shaders: " .. stats.failedShaders)
    print("  Shader reloads: " .. stats.shaderReloads)
    print("  Average compile time: " .. stats.averageCompileTime .. " seconds")
    
    -- Performance recommendations
    if stats.failedShaders > 0 then
        print("Warning: " .. stats.failedShaders .. " shaders failed to compile")
    end
    
    if stats.averageCompileTime > 1.0 then
        print("Warning: Shader compilation is taking longer than expected")
    end
end

-- Example 16: Hot-reload testing
function testHotReload()
    print("Testing shader hot-reload...")
    
    -- Enable file watching
    StarboundShaders.watchShaderFiles()
    
    -- Monitor for changes
    local lastUpdate = 0
    while true do
        local currentTime = os.time()
        if currentTime - lastUpdate >= 1 then
            StarboundShaders.update()
            lastUpdate = currentTime
        end
        
        -- Check if any shaders were reloaded
        local stats = StarboundShaders.getStats()
        if stats.shaderReloads > 0 then
            print("Shaders reloaded: " .. stats.shaderReloads)
            break
        end
    end
    
    -- Disable file watching
    StarboundShaders.unwatchShaderFiles()
    
    print("Hot-reload test completed")
end

-- Example 17: Integration with texture generation
function integrateWithTextureGeneration()
    -- Get mesh texture
    local meshTexture = "textures/mesh_rendered.png"
    local paletteTexture = "palettes/starbound_default.png"
    
    -- Apply baking shaders
    applyPixelGridSnap(meshTexture, {64, 64})
    applyPaletteQuantization(meshTexture, paletteTexture)
    extractOutlines(meshTexture, {64, 64})
    
    print("Texture generation with shaders completed")
end

-- Example 18: Integration with crossbow bolts
function applyBoltsEffects(boltTexture, time)
    -- Apply cell shading for 3D effect
    applyCellShading(boltTexture, "textures/normal_map.png", 
                    {0.7, 0.7, 0.0}, {1.0, 1.0, 1.0})
    
    -- Apply emissive glow for magical bolts
    applyEmissiveGlow(boltTexture, "textures/emissive_map.png", time)
    
    -- Apply water ripple for special effects
    applyWaterRipple(boltTexture, "textures/ripple.png", time)
    
    print("Bolt effects applied")
end

-- Example 19: Damage system integration
function applyDamageToItem(itemTexture, damageLevel)
    local damageMask = "textures/damage_masks/cracks.png"
    local damageDecal = "textures/damage_decals/scorch.png"
    
    -- Apply damage overlay based on damage level
    local intensity = math.min(damageLevel / 100.0, 1.0)
    applyDamageOverlay(itemTexture, damageMask, damageDecal, intensity)
    
    print("Damage applied to item: " .. damageLevel .. "%")
end

-- Example 20: Magic spell effects
function createMagicSpellEffect(baseTexture, spellType, time)
    if spellType == "fire" then
        -- Fire spell with orange glow and dissolve
        applyEmissiveGlow(baseTexture, "textures/fire_emissive.png", time)
        applyDissolveEffect(baseTexture, "textures/fire_noise.png", 0.3, time)
        
    elseif spellType == "ice" then
        -- Ice spell with blue glow and water ripple
        local icePass = StarboundShaders.createEmissiveGlowPass(time)
        icePass:setVec3("glowColor", {0.3, 0.6, 1.0}) -- Blue glow
        icePass:setTexture("baseTex", baseTexture, 0)
        icePass:execute()
        
        applyWaterRipple(baseTexture, "textures/ice_ripple.png", time)
        
    elseif spellType == "lightning" then
        -- Lightning spell with yellow glow and scanlines
        local lightningPass = StarboundShaders.createEmissiveGlowPass(time)
        lightningPass:setVec3("glowColor", {1.0, 1.0, 0.0}) -- Yellow glow
        lightningPass:setFloat("pulseSpeed", 10.0) -- Fast pulsing
        lightningPass:setTexture("baseTex", baseTexture, 0)
        lightningPass:execute()
    end
    
    print("Magic spell effect applied: " .. spellType)
end

-- Main usage example
function main()
    print("Starbound Shader Suite Example")
    print("==============================")
    
    -- Initialize the shader suite
    StarboundShaderSuite:initialize()
    
    -- Example usage
    print("1. Testing basic shader usage...")
    basicShaderUsage()
    
    print("2. Creating custom shader...")
    local customShader = createCustomShader()
    
    print("3. Running baking pipeline...")
    runBakingPipeline("textures/mesh.png", "palettes/starbound_default.png", {64, 64})
    
    print("4. Applying bolt effects...")
    applyBoltsEffects("textures/bolt.png", 0.0)
    
    print("5. Creating magic spell effects...")
    createMagicSpellEffect("textures/spell.png", "fire", 0.0)
    
    print("6. Monitoring performance...")
    monitorShaderPerformance()
    
    print("Shader suite examples completed!")
end

-- Run the example
main() 