#include "AlchemicalGrenadeFactory.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/Shader.hpp"
#include "core/rendering/Texture.hpp"
#include "core/particles/ParticleSystem.hpp"
#include "core/audio/AudioEngine.hpp"
#include "core/ui/IconRenderer.hpp"
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>
#include <cmath>

namespace MagiTech {
namespace AlchemicalGrenades {

namespace {
// Local 2D value noise — avoids glm/gtx/noise (not in all GLM packages).
inline float simplex2(const glm::vec2& p) {
    const float n = std::sin(p.x * 12.9898f + p.y * 78.233f) * 43758.5453f;
    return (n - std::floor(n)) * 2.0f - 1.0f;
}
inline float simplex2(const glm::vec3& p) {
    const float n = std::sin(p.x * 12.9898f + p.y * 78.233f + p.z * 37.719f) * 43758.5453f;
    return (n - std::floor(n)) * 2.0f - 1.0f;
}
} // namespace

namespace MeshGen {
    MeshHandle buildItem(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade item mesh for: {}", g.id);
        
        Mesh mesh;
        
        // Build core grenade body
        auto core = Primitives::createSphere(g.coreRadius, 16);
        mesh.append(core);
        
        // Add casing based on material type
        if (g.casingMaterial == CasingMaterial::GLASS) {
            // Glass casing with beveled edges
            auto casing = Primitives::createSphere(g.coreRadius + g.casingThickness, 16);
            mesh.append(casing);
        }
        else if (g.casingMaterial == CasingMaterial::METAL) {
            // Metal casing with seams
            auto casing = Primitives::createSphere(g.coreRadius + g.casingThickness, 12);
            mesh.append(casing);
        }
        else if (g.casingMaterial == CasingMaterial::CERAMIC) {
            // Ceramic casing with texture
            auto casing = Primitives::createSphere(g.coreRadius + g.casingThickness, 14);
            mesh.append(casing);
        }
        
        // Add label plate if specified
        if (!g.description.empty()) {
            auto label = Primitives::createQuad(g.coreRadius * 0.3f, g.coreRadius * 0.1f);
            glm::mat4 labelTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, g.coreRadius * 0.8f, g.coreRadius * 0.6f));
            mesh.append(label, labelTransform);
        }
        
        mesh.optimize();
        return mesh.upload();
    }
    
    MeshHandle buildProjectile(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade projectile mesh for: {}", g.id);
        
        Mesh mesh;
        
        // Start with item mesh
        auto itemMesh = buildItem(g);
        mesh.append(itemMesh);
        
        // Add trail effect based on grenade type
        if (g.grenadeType == GrenadeType::FIRE) {
            auto trail = Primitives::createCone(g.coreRadius * 0.2f, g.coreRadius * 0.5f, 8);
            glm::mat4 trailTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, -g.coreRadius * 1.2f, 0));
            mesh.append(trail, trailTransform);
        }
        else if (g.grenadeType == GrenadeType::SMOKE) {
            auto smokeTrail = Primitives::createCylinder(g.coreRadius * 0.15f, g.coreRadius * 0.8f, 6);
            glm::mat4 smokeTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, -g.coreRadius * 1.0f, 0));
            mesh.append(smokeTrail, smokeTransform);
        }
        else if (g.grenadeType == GrenadeType::FROST) {
            auto frostTrail = Primitives::createCone(g.coreRadius * 0.25f, g.coreRadius * 0.6f, 8);
            glm::mat4 frostTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, -g.coreRadius * 1.1f, 0));
            mesh.append(frostTrail, frostTransform);
        }
        
        mesh.optimize();
        return mesh.upload();
    }
    
    MeshHandle buildGrenadeCore(const AlchemicalGrenadeParams& g) {
        return Primitives::createSphere(g.coreRadius, 16).upload();
    }
    
    MeshHandle buildCasing(const AlchemicalGrenadeParams& g) {
        return Primitives::createSphere(g.coreRadius + g.casingThickness, 16).upload();
    }
    
    MeshHandle buildLabel(const AlchemicalGrenadeParams& g) {
        return Primitives::createQuad(g.coreRadius * 0.3f, g.coreRadius * 0.1f).upload();
    }
    
    MeshHandle buildTrail(const AlchemicalGrenadeParams& g) {
        if (g.grenadeType == GrenadeType::FIRE) {
            return Primitives::createCone(g.coreRadius * 0.2f, g.coreRadius * 0.5f, 8).upload();
        }
        return 0;
    }
    
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes) {
        Mesh combined;
        for (auto handle : meshes) {
            if (handle > 0) {
                combined.append(handle);
            }
        }
        combined.optimize();
        return combined.upload();
    }
}

namespace ShaderGen {
    ShaderHandle buildItem(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade item shader for: {}", g.id);
        
        Shader s;
        s.addStage("vertex", "grenade_item.vert");
        s.addStage("fragment", "grenade_item.frag");
        
        s.setUniform("uCasingColorPrimary", g.casingColorPrimary);
        s.setUniform("uCasingColorSecondary", g.casingColorSecondary);
        s.setUniform("uLiquidColor", g.liquidColor);
        s.setUniform("uGlowColor", g.glowColor);
        s.setUniform("uNoiseScale", g.noiseScale);
        s.setUniform("uNoiseSpeed", g.noiseSpeed);
        s.setUniform("uGlowIntensity", g.glowIntensity);
        s.setUniform("uEmissivePower", g.emissivePower);
        s.setUniform("uTransparency", g.transparency);
        s.setUniform("uRefractionIndex", g.refractionIndex);
        s.setUniform("uMetallicness", g.metallicness);
        s.setUniform("uRoughness", g.roughness);
        
        // Add material-specific defines
        if (g.casingMaterial == CasingMaterial::GLASS) {
            s.addDefine("USE_GLASS");
            s.addDefine("USE_REFRACTION");
        }
        else if (g.casingMaterial == CasingMaterial::METAL) {
            s.addDefine("USE_METAL");
            s.addDefine("USE_REFLECTION");
        }
        else if (g.casingMaterial == CasingMaterial::CERAMIC) {
            s.addDefine("USE_CERAMIC");
        }
        
        // Add grenade type defines
        switch (g.grenadeType) {
            case GrenadeType::FIRE: s.addDefine("GRENADE_FIRE"); break;
            case GrenadeType::ACID: s.addDefine("GRENADE_ACID"); break;
            case GrenadeType::SMOKE: s.addDefine("GRENADE_SMOKE"); break;
            case GrenadeType::FROST: s.addDefine("GRENADE_FROST"); break;
            case GrenadeType::SHOCK: s.addDefine("GRENADE_SHOCK"); break;
            case GrenadeType::HEALING: s.addDefine("GRENADE_HEALING"); break;
            default: break;
        }
        
        return s.compile();
    }
    
    ShaderHandle buildProjectile(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade projectile shader for: {}", g.id);
        
        Shader s;
        s.addStage("vertex", "grenade_projectile.vert");
        s.addStage("fragment", "grenade_projectile.frag");
        
        s.setUniform("uLiquidColor", g.liquidColor);
        s.setUniform("uGlowColor", g.glowColor);
        s.setUniform("uNoiseScale", g.noiseScale);
        s.setUniform("uNoiseSpeed", g.noiseSpeed);
        s.setUniform("uGlowIntensity", g.glowIntensity);
        s.setUniform("uFuseTime", g.fuseTime);
        
        s.addDefine("USE_PROJECTILE");
        s.addDefine("USE_EMISSION");
        
        return s.compile();
    }
    
    ShaderHandle buildGrenadeShader(const AlchemicalGrenadeParams& g) {
        return buildItem(g);
    }
    
    ShaderHandle buildCasingShader(const AlchemicalGrenadeParams& g) {
        Shader s;
        s.addStage("vertex", "grenade_casing.vert");
        s.addStage("fragment", "grenade_casing.frag");
        
        s.setUniform("uCasingColorPrimary", g.casingColorPrimary);
        s.setUniform("uCasingColorSecondary", g.casingColorSecondary);
        s.setUniform("uMetallicness", g.metallicness);
        s.setUniform("uRoughness", g.roughness);
        
        return s.compile();
    }
    
    ShaderHandle buildLiquidShader(const AlchemicalGrenadeParams& g) {
        Shader s;
        s.addStage("vertex", "grenade_liquid.vert");
        s.addStage("fragment", "grenade_liquid.frag");
        
        s.setUniform("uLiquidColor", g.liquidColor);
        s.setUniform("uNoiseScale", g.noiseScale);
        s.setUniform("uNoiseSpeed", g.noiseSpeed);
        s.setUniform("uNoiseIntensity", g.noiseIntensity);
        
        s.addDefine("USE_LIQUID");
        s.addDefine("USE_NOISE");
        
        return s.compile();
    }
    
    std::string generateGrenadeShaderCode(const AlchemicalGrenadeParams& g) {
        std::string code = "#version 450 core\n\n";
        code += "// Auto-generated shader for grenade: " + g.id + "\n";
        code += "uniform vec3 uCasingColorPrimary;\n";
        code += "uniform vec3 uCasingColorSecondary;\n";
        code += "uniform vec4 uLiquidColor;\n";
        code += "uniform float uNoiseScale;\n";
        code += "uniform float uNoiseSpeed;\n";
        code += "uniform float uGlowIntensity;\n";
        code += "uniform float uFuseTime;\n\n";
        
        // Add material-specific code
        switch (g.casingMaterial) {
            case CasingMaterial::GLASS:
                code += "#define USE_GLASS\n";
                code += "#define USE_REFRACTION\n";
                break;
            case CasingMaterial::METAL:
                code += "#define USE_METAL\n";
                code += "#define USE_REFLECTION\n";
                break;
            case CasingMaterial::CERAMIC:
                code += "#define USE_CERAMIC\n";
                break;
            default:
                break;
        }
        
        return code;
    }
}

namespace TextureGen {
    TextureHandle buildItem(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade item texture for: {}", g.id);
        
        int W = 256, H = 256;
        std::vector<glm::u8vec4> pixels(W * H);
        
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float u = x / (float)W, v = y / (float)H;
                
                // Generate base texture with noise
                float noise = simplex2(glm::vec2(u * g.noiseScale, v * g.noiseScale));
                noise = (noise + 1.0f) * 0.5f;
                
                // Apply material-specific texture
                glm::vec3 color;
                if (g.casingMaterial == CasingMaterial::GLASS) {
                    color = glm::mix(g.casingColorPrimary, g.casingColorSecondary, noise * 0.3f);
                    color *= 1.0f + noise * 0.2f; // Glass highlights
                }
                else if (g.casingMaterial == CasingMaterial::METAL) {
                    color = glm::mix(g.casingColorPrimary, g.casingColorSecondary, noise * 0.5f);
                    color *= 0.8f + noise * 0.4f; // Metal variation
                }
                else {
                    color = glm::mix(g.casingColorPrimary, g.casingColorSecondary, noise * 0.4f);
                }
                
                color = glm::clamp(color, 0.0f, 1.0f);
                
                pixels[y * W + x] = glm::u8vec4(
                    static_cast<uint8_t>(color.r * 255),
                    static_cast<uint8_t>(color.g * 255),
                    static_cast<uint8_t>(color.b * 255),
                    255
                );
            }
        }
        
        return Texture::upload(W, H, pixels.data());
    }
    
    TextureHandle buildGrenadeTexture(const AlchemicalGrenadeParams& g) {
        return buildItem(g);
    }
    
    TextureHandle buildCasingTexture(const AlchemicalGrenadeParams& g) {
        int W = 128, H = 128;
        std::vector<glm::u8vec4> pixels(W * H);
        
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float u = x / (float)W, v = y / (float)H;
                float noise = simplex2(glm::vec2(u * 4.0f, v * 4.0f));
                noise = (noise + 1.0f) * 0.5f;
                
                glm::vec3 color = glm::mix(g.casingColorPrimary, g.casingColorSecondary, noise);
                color = glm::clamp(color, 0.0f, 1.0f);
                
                pixels[y * W + x] = glm::u8vec4(
                    static_cast<uint8_t>(color.r * 255),
                    static_cast<uint8_t>(color.g * 255),
                    static_cast<uint8_t>(color.b * 255),
                    255
                );
            }
        }
        
        return Texture::upload(W, H, pixels.data());
    }
    
    TextureHandle buildLiquidTexture(const AlchemicalGrenadeParams& g) {
        int W = 128, H = 128;
        std::vector<glm::u8vec4> pixels(W * H);
        
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float u = x / (float)W, v = y / (float)H;
                
                // Animated liquid noise
                float time = 0.0f; // Would be passed from shader
                float noise1 = simplex2(glm::vec3(u * g.noiseScale, v * g.noiseScale, time * g.noiseSpeed));
                float noise2 = simplex2(glm::vec3(u * g.noiseScale * 2.0f, v * g.noiseScale * 2.0f, time * g.noiseSpeed * 0.5f));
                
                float combinedNoise = (noise1 + noise2) * 0.5f;
                combinedNoise = (combinedNoise + 1.0f) * 0.5f;
                
                glm::vec4 color = g.liquidColor;
                color.rgb *= 0.8f + combinedNoise * 0.4f;
                color.a *= 0.7f + combinedNoise * 0.3f;
                
                color = glm::clamp(color, 0.0f, 1.0f);
                
                pixels[y * W + x] = glm::u8vec4(
                    static_cast<uint8_t>(color.r * 255),
                    static_cast<uint8_t>(color.g * 255),
                    static_cast<uint8_t>(color.b * 255),
                    static_cast<uint8_t>(color.a * 255)
                );
            }
        }
        
        return Texture::upload(W, H, pixels.data());
    }
    
    TextureHandle buildNoiseTexture(const AlchemicalGrenadeParams& g) {
        int W = 64, H = 64;
        std::vector<glm::u8vec4> pixels(W * H);
        
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float u = x / (float)W, v = y / (float)H;
                float noise = simplex2(glm::vec2(u * g.noiseScale, v * g.noiseScale));
                noise = (noise + 1.0f) * 0.5f;
                
                uint8_t value = static_cast<uint8_t>(noise * 255);
                pixels[y * W + x] = glm::u8vec4(value, value, value, 255);
            }
        }
        
        return Texture::upload(W, H, pixels.data());
    }
    
    TextureHandle mergeGrenadeTextures(const TextureHandle& casing, const TextureHandle& liquid) {
        // Simple texture merging - in practice would use more sophisticated blending
        return casing; // Placeholder
    }
}

namespace ParticleGen {
    ParticleHandle buildExplosion(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade explosion particles for: {}", g.id);
        
        ParticleSystem ps;
        ps.setType(ParticleType::BURST);
        ps.setCount(g.particleBurstCount);
        ps.setLifetime(g.particleLifetime);
        ps.setSpeed(g.particleSpeed);
        ps.setSize(g.particleSize);
        ps.setSpread(g.particleSpread);
        ps.setGravity(g.particleGravity);
        ps.setColor(g.explosionColor);
        
        // Add grenade type-specific effects
        switch (g.grenadeType) {
            case GrenadeType::FIRE:
                ps.addEffect("fire_burst");
                ps.addEffect("ember_trail");
                break;
            case GrenadeType::ACID:
                ps.addEffect("acid_splash");
                ps.addEffect("corrosive_cloud");
                break;
            case GrenadeType::SMOKE:
                ps.addEffect("smoke_puff");
                ps.addEffect("ash_particles");
                break;
            case GrenadeType::FROST:
                ps.addEffect("frost_spike");
                ps.addEffect("ice_crystal");
                break;
            case GrenadeType::SHOCK:
                ps.addEffect("electric_spark");
                ps.addEffect("lightning_arc");
                break;
            case GrenadeType::HEALING:
                ps.addEffect("healing_glow");
                ps.addEffect("restoration_particles");
                break;
            default:
                ps.addEffect("generic_explosion");
                break;
        }
        
        return ps.upload();
    }
    
    ParticleHandle buildResidue(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade residue particles for: {}", g.id);
        
        ParticleSystem ps;
        ps.setType(ParticleType::AREA_PUFF);
        ps.setCount(g.particleBurstCount / 2);
        ps.setLifetime(g.residueDuration);
        ps.setSpeed(g.particleSpeed * 0.5f);
        ps.setSize(g.particleSize * 1.5f);
        ps.setSpread(g.residueSpread);
        ps.setColor(g.residueColor);
        
        // Add residue type-specific effects
        switch (g.residueType) {
            case ResidueType::LINGERING_CLOUD:
                ps.addEffect("lingering_cloud");
                break;
            case ResidueType::SURFACE_DECAL:
                ps.addEffect("surface_decal");
                break;
            case ResidueType::DRIPPING_FLUID:
                ps.addEffect("dripping_fluid");
                break;
            case ResidueType::BURNING_GROUND:
                ps.addEffect("burning_ground");
                break;
            case ResidueType::FROST_PATCH:
                ps.addEffect("frost_patch");
                break;
            default:
                ps.addEffect("generic_residue");
                break;
        }
        
        return ps.upload();
    }
    
    ParticleHandle buildShrapnel(const AlchemicalGrenadeParams& g) {
        ParticleSystem ps;
        ps.setType(ParticleType::SHARD_BURST);
        ps.setCount(g.shrapnelCount);
        ps.setLifetime(g.shardLifetime);
        ps.setSpeed(g.shardSpeed);
        ps.setSize(g.shardSize);
        ps.setColor(g.casingColorPrimary);
        
        return ps.upload();
    }
    
    ParticleHandle buildTrail(const AlchemicalGrenadeParams& g) {
        ParticleSystem ps;
        ps.setType(ParticleType::TRAIL);
        ps.setCount(g.particleBurstCount / 4);
        ps.setLifetime(g.particleLifetime * 0.5f);
        ps.setSpeed(g.particleSpeed * 0.3f);
        ps.setSize(g.particleSize * 0.8f);
        ps.setColor(g.glowColor);
        
        return ps.upload();
    }
    
    ParticleHandle buildBurstEffect(const AlchemicalGrenadeParams& g) {
        return buildExplosion(g);
    }
}

namespace AudioGen {
    AudioHandle buildExplosion(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade explosion audio for: {}", g.id);
        
        AudioClip clip;
        clip.setVolume(g.soundVolume);
        clip.setPitch(g.soundPitch);
        clip.setDuration(g.soundDuration);
        clip.setSpatial(g.enableSpatialAudio);
        clip.setDistance(g.audioDistance);
        
        // Add grenade type-specific sounds
        switch (g.grenadeType) {
            case GrenadeType::FIRE:
                clip.addLayer("fire_explosion");
                clip.addLayer("glass_shatter");
                break;
            case GrenadeType::ACID:
                clip.addLayer("acid_hiss");
                clip.addLayer("corrosive_bubble");
                break;
            case GrenadeType::SMOKE:
                clip.addLayer("smoke_puff");
                clip.addLayer("ash_rustle");
                break;
            case GrenadeType::FROST:
                clip.addLayer("frost_crystal");
                clip.addLayer("ice_shatter");
                break;
            case GrenadeType::SHOCK:
                clip.addLayer("electric_zap");
                clip.addLayer("thunder_crack");
                break;
            case GrenadeType::HEALING:
                clip.addLayer("healing_chime");
                clip.addLayer("restoration_hum");
                break;
            default:
                clip.addLayer("generic_explosion");
                break;
        }
        
        if (g.enableEcho) {
            clip.addEffect("echo", g.echoDelay, g.echoDecay);
        }
        
        return clip.upload();
    }
    
    AudioHandle buildGrenadeAudio(const AlchemicalGrenadeParams& g) {
        return buildExplosion(g);
    }
    
    AudioHandle buildCasingSound(const AlchemicalGrenadeParams& g) {
        AudioClip clip;
        clip.setVolume(g.soundVolume * 0.7f);
        clip.setPitch(g.soundPitch);
        
        switch (g.casingMaterial) {
            case CasingMaterial::GLASS:
                clip.addLayer("glass_tinkle");
                break;
            case CasingMaterial::METAL:
                clip.addLayer("metal_clank");
                break;
            case CasingMaterial::CERAMIC:
                clip.addLayer("ceramic_crack");
                break;
            default:
                clip.addLayer("generic_casing");
                break;
        }
        
        return clip.upload();
    }
}

namespace IconGen {
    IconHandle buildItemIcon(const AlchemicalGrenadeParams& g, const UIItemParams& u) {
        Log::info("Building grenade icon for: {}", g.id);
        
        IconRenderer renderer(u.iconSize, u.iconSize);
        
        // Draw background shape
        switch (u.backgroundShape) {
            case BackgroundShape::CIRCLE:
                renderer.drawCircle(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::SQUARE:
                renderer.drawSquare(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::HEXAGON:
                renderer.drawHexagon(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::DIAMOND:
                renderer.drawDiamond(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            default:
                break;
        }
        
        // Draw grenade silhouette
        renderer.drawCircle(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.25f, g.casingColorPrimary);
        
        // Add elemental overlay
        switch (g.grenadeType) {
            case GrenadeType::FIRE:
                renderer.drawOverlay("fire_symbol", g.glowColor);
                break;
            case GrenadeType::ACID:
                renderer.drawOverlay("acid_symbol", g.liquidColor);
                break;
            case GrenadeType::SMOKE:
                renderer.drawOverlay("smoke_symbol", glm::vec3(0.5f));
                break;
            case GrenadeType::FROST:
                renderer.drawOverlay("frost_symbol", glm::vec3(0.7f, 0.9f, 1.0f));
                break;
            case GrenadeType::SHOCK:
                renderer.drawOverlay("shock_symbol", glm::vec3(1.0f, 1.0f, 0.3f));
                break;
            case GrenadeType::HEALING:
                renderer.drawOverlay("healing_symbol", glm::vec3(0.3f, 1.0f, 0.3f));
                break;
            default:
                break;
        }
        
        // Add glow effect if enabled
        if (u.enableGlow) {
            renderer.addGlow(g.glowColor, u.glowIntensity);
        }
        
        // Add pulse effect if enabled
        if (u.enablePulse) {
            renderer.addPulse(u.pulseFrequency, u.pulseAmplitude);
        }
        
        return renderer.finalize();
    }
    
    IconHandle buildGrenadeIcon(const AlchemicalGrenadeParams& g) {
        UIItemParams defaultUI;
        defaultUI.iconSize = 64;
        defaultUI.backgroundShape = BackgroundShape::CIRCLE;
        defaultUI.borderColor = glm::vec4(1.0f);
        return buildItemIcon(g, defaultUI);
    }
    
    IconHandle buildBackgroundShape(const UIItemParams& u) {
        IconRenderer renderer(u.iconSize, u.iconSize);
        
        switch (u.backgroundShape) {
            case BackgroundShape::CIRCLE:
                renderer.drawCircle(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::SQUARE:
                renderer.drawSquare(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::HEXAGON:
                renderer.drawHexagon(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            case BackgroundShape::DIAMOND:
                renderer.drawDiamond(glm::vec2(u.iconSize * 0.5f), u.iconSize * 0.4f, u.borderColor);
                break;
            default:
                break;
        }
        
        return renderer.finalize();
    }
    
    IconHandle buildElementalOverlay(const AlchemicalGrenadeParams& g) {
        IconRenderer renderer(32, 32);
        
        switch (g.grenadeType) {
            case GrenadeType::FIRE:
                renderer.drawOverlay("fire_symbol", g.glowColor);
                break;
            case GrenadeType::ACID:
                renderer.drawOverlay("acid_symbol", g.liquidColor);
                break;
            case GrenadeType::SMOKE:
                renderer.drawOverlay("smoke_symbol", glm::vec3(0.5f));
                break;
            case GrenadeType::FROST:
                renderer.drawOverlay("frost_symbol", glm::vec3(0.7f, 0.9f, 1.0f));
                break;
            case GrenadeType::SHOCK:
                renderer.drawOverlay("shock_symbol", glm::vec3(1.0f, 1.0f, 0.3f));
                break;
            case GrenadeType::HEALING:
                renderer.drawOverlay("healing_symbol", glm::vec3(0.3f, 1.0f, 0.3f));
                break;
            default:
                break;
        }
        
        return renderer.finalize();
    }
}

namespace PhysGen {
    PhysicsHandle buildShrapnel(const AlchemicalGrenadeParams& g) {
        Log::info("Building grenade shrapnel physics for: {}", g.id);
        
        PhysicsSystem ps;
        
        for (int i = 0; i < g.shrapnelCount; ++i) {
            std::string name = "shard_" + std::to_string(i);
            
            // Create rigid body for shard
            ps.addRigidBody(name, g.shardMass);
            
            // Add capsule collider
            ps.addCollider(name, ColliderType::CAPSULE, g.shardSize);
            
            // Set initial velocity in random direction
            glm::vec3 direction = glm::normalize(glm::vec3(
                (float)rand() / RAND_MAX * 2.0f - 1.0f,
                (float)rand() / RAND_MAX * 2.0f - 1.0f,
                (float)rand() / RAND_MAX * 2.0f - 1.0f
            ));
            ps.setInitialVelocity(name, direction * g.shardSpeed);
            
            // Set lifetime
            ps.setLifetime(name, g.shardLifetime);
        }
        
        return ps.upload();
    }
    
    PhysicsHandle buildGrenadePhysics(const AlchemicalGrenadeParams& g) {
        PhysicsSystem ps;
        
        // Create main grenade body
        ps.addRigidBody("grenade", g.mass);
        ps.addCollider("grenade", ColliderType::SPHERE, g.coreRadius);
        
        // Set physics properties
        ps.setBounciness("grenade", g.bounciness);
        ps.setFriction("grenade", g.friction);
        ps.setAirResistance("grenade", g.airResistance);
        
        // Enable gravity if specified
        if (g.enableGravity) {
            ps.enableGravity("grenade");
        }
        
        return ps.upload();
    }
    
    PhysicsHandle buildExplosionPhysics(const AlchemicalGrenadeParams& g) {
        PhysicsSystem ps;
        
        // Create explosion force field
        ps.addForceField("explosion", g.explosionRadius, g.explosionForce);
        
        // Add shockwave if enabled
        if (g.enableShockwave) {
            ps.addShockwave("shockwave", g.shockwaveRadius, g.shockwaveForce);
        }
        
        return ps.upload();
    }
}

} // namespace AlchemicalGrenades
} // namespace MagiTech
