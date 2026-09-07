#include "GyroProjectileFactory.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/Shaders.hpp"
#include "core/particles/ParticleSystem.hpp"
#include "core/audio/AudioSystem.hpp"
#include "core/physics/Simulation.hpp"
#include "core/physics/Collision.hpp"
#include "core/utils/TemplateEngine.hpp"
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>
#include <random>

namespace MagiTech {
namespace GyroProjectiles {

#define LOG_GYRO_GEN(Action, Id) Log::info("GyroGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t GyroParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(GyroParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}

uint64_t FlightParams::hashKey() const { 
    return XXH64(this, sizeof(FlightParams), 0); 
}

uint64_t TrailParams::hashKey() const { 
    return XXH64(this, sizeof(TrailParams), 0); 
}

uint64_t VFXParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(VFXParams) - 2 * sizeof(std::string));
    XXH64_update(&s, shaderTemplate.c_str(), shaderTemplate.length());
    for (const auto& d : defines) { 
        XXH64_update(&s, d.c_str(), d.length()); 
    }
    return XXH64_digest(&s);
}

uint64_t ParticleParams::hashKey() const { 
    return XXH64(this, sizeof(ParticleParams), 0); 
}

uint64_t AudioParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(AudioParams) - 2 * sizeof(std::string));
    XXH64_update(&s, humFile.c_str(), humFile.length());
    XXH64_update(&s, impactFile.c_str(), impactFile.length());
    return XXH64_digest(&s);
}

uint64_t CollisionParams::hashKey() const { 
    return XXH64(this, sizeof(CollisionParams), 0); 
}

// ============================================================================
// MESH GENERATION
// ============================================================================

namespace MeshGen {
    MeshHandle buildGyroMesh(const GyroParams& g) {
        LOG_GYRO_GEN(BuildingMesh, g.id);
        
        Mesh gyroMesh;
        
        switch (g.shape) {
            case GyroShape::Disc:
                if (g.hollow) {
                    // Ring shape
                    auto ring = Primitives::createTorus(g.radius, g.thickness, 32, 8);
                    gyroMesh.append(ring);
                } else {
                    // Solid disc
                    auto disc = Primitives::createCylinder(g.radius, g.thickness, 32);
                    gyroMesh.append(disc);
                }
                break;
                
            case GyroShape::Ring:
                // Always hollow ring
                auto ring = Primitives::createTorus(g.radius, g.thickness, 32, 8);
                gyroMesh.append(ring);
                break;
                
            case GyroShape::Spindle:
                // Capsule shape for spindle
                auto spindle = Primitives::createCapsule(g.radius, g.radius * 2.0f, 16);
                gyroMesh.append(spindle);
                break;
                
            case GyroShape::CustomMesh:
                // Load custom mesh from file
                if (!g.id.empty()) {
                    // In a real implementation, this would load from file
                    // For now, create a default disc
                    auto custom = Primitives::createCylinder(g.radius, g.thickness, 24);
                    gyroMesh.append(custom);
                }
                break;
        }
        
        // Apply dynamic tessellation if enabled
        if (g.dynamicTess) {
            gyroMesh.enableTessellation();
        }
        
        gyroMesh.optimize();
        return gyroMesh.upload();
    }
}

// ============================================================================
// FLIGHT SIMULATION
// ============================================================================

namespace FlightSim {
    SimulationHandle setupGyro(const GyroParams& g, const FlightParams& f) {
        LOG_GYRO_GEN(SettingUpFlightSim, g.id);
        
        GyroSimDesc desc;
        desc.initialSpeed = f.initialSpeed;
        desc.spinRate = f.spinRateRPM / 60.0f; // Convert to Hz
        desc.precessionRate = glm::radians(f.precessionRateDeg);
        desc.stabilityFactor = f.stabilityFactor;
        desc.gravityEnabled = f.gravityEnabled;
        desc.gravityScale = f.gravityScale;
        desc.gyroRadius = g.radius;
        desc.gyroThickness = g.thickness;
        
        return Simulation::createGyro(desc);
    }
}

// ============================================================================
// TRAIL GENERATION
// ============================================================================

namespace TrailGen {
    MeshHandle buildGyroTrail(const TrailParams& t) {
        LOG_GYRO_GEN(BuildingTrail, static_cast<int>(t.type));
        
        if (!t.enableTrail) {
            return 0;
        }
        
        Mesh trailMesh;
        
        switch (t.type) {
            case TrailType::Ribbon: {
                // Create camera-facing ribbon strip
                int segments = static_cast<int>(t.length * 10.0f);
                float segmentLength = t.length / segments;
                
                for (int i = 0; i < segments; ++i) {
                    float t_val = i / static_cast<float>(segments);
                    glm::vec4 color = glm::mix(t.headColor, t.tailColor, t_val);
                    
                    // Create quad for ribbon segment
                    auto quad = Primitives::createQuad(t.width, segmentLength);
                    
                    // Position along trail
                    glm::mat4 transform = glm::translate(glm::mat4(1.0f), 
                        glm::vec3(-i * segmentLength, 0, 0));
                    
                    trailMesh.append(quad, transform);
                }
                break;
            }
            
            case TrailType::Streaks: {
                // Create motion blur streaks
                int streakCount = 8;
                for (int i = 0; i < streakCount; ++i) {
                    float angle = i * glm::two_pi<float>() / streakCount;
                    float radius = t.width * 0.5f;
                    
                    auto streak = Primitives::createCylinder(0.01f, t.length, 4);
                    glm::mat4 transform = glm::translate(glm::mat4(1.0f), 
                        glm::vec3(cos(angle) * radius, 0, sin(angle) * radius));
                    transform = glm::rotate(transform, angle, glm::vec3(0, 1, 0));
                    
                    trailMesh.append(streak, transform);
                }
                break;
            }
            
            case TrailType::Particles:
                // Particles are handled separately in ParticleGen
                // Return empty mesh for particle trails
                break;
        }
        
        if (!trailMesh.isEmpty()) {
            trailMesh.optimize();
            return trailMesh.upload();
        }
        
        return 0;
    }
}

// ============================================================================
// SHADER GENERATION
// ============================================================================

namespace ShaderGen {
    ShaderHandle buildVFX(const VFXParams& v) {
        LOG_GYRO_GEN(BuildingShader, v.shaderTemplate);
        
        if (v.shaderTemplate.empty()) {
            return 0;
        }
        
        // Template expansion
        std::map<std::string, std::string> replacements;
        replacements["%GLOW_INTENSITY%"] = std::to_string(v.glowIntensity);
        replacements["%FLICKER_SPEED%"] = std::to_string(v.flickerSpeed);
        
        // Add defines
        for (const auto& define : v.defines) {
            replacements["%DEFINES%"] += "#define " + define + "\n";
        }
        
        // Expand template
        std::string shaderSource = TemplateEngine::expand(v.shaderTemplate, replacements);
        
        // Compile shader
        ShaderDesc desc;
        desc.source = shaderSource;
        desc.stage = ShaderStage::Fragment;
        desc.language = ShaderLanguage::GLSL;
        desc.target = ShaderTarget::SPIRV;
        
        // Add uniforms
        desc.uniforms = {
            {"uTime", 0.0f},
            {"uSpinRate", 0.0f},
            {"uGlowIntensity", v.glowIntensity},
            {"uFlickerSpeed", v.flickerSpeed},
            {"uFlickerMode", static_cast<int>(v.flickerMode)}
        };
        
        return Shaders::compile(desc);
    }
}

// ============================================================================
// PARTICLE GENERATION
// ============================================================================

namespace ParticleGen {
    ParticleHandle buildGyroParticles(const ParticleParams& p) {
        LOG_GYRO_GEN(BuildingParticles, static_cast<int>(p.style));
        
        if (!p.enableParticles) {
            return 0;
        }
        
        ParticleSystemDesc desc;
        desc.maxParticles = p.count;
        desc.emissionRate = p.spawnRate;
        desc.particleLifetime = p.lifeTime;
        desc.velocityMin = p.velocityMin;
        desc.velocityMax = p.velocityMax;
        
        // Style-specific settings
        switch (p.style) {
            case ParticleStyle::Sparks:
                desc.startColor = glm::vec4(1.0f, 0.8f, 0.2f, 1.0f);
                desc.endColor = glm::vec4(0.5f, 0.3f, 0.1f, 0.0f);
                desc.startSize = 0.02f;
                desc.endSize = 0.05f;
                desc.gravity = glm::vec3(0, -9.8f, 0);
                break;
                
            case ParticleStyle::Smoke:
                desc.startColor = glm::vec4(0.3f, 0.3f, 0.3f, 0.8f);
                desc.endColor = glm::vec4(0.1f, 0.1f, 0.1f, 0.0f);
                desc.startSize = 0.1f;
                desc.endSize = 0.3f;
                desc.gravity = glm::vec3(0, 2.0f, 0);
                break;
                
            case ParticleStyle::Sparkle:
                desc.startColor = glm::vec4(1.0f, 1.0f, 1.0f, 1.0f);
                desc.endColor = glm::vec4(0.8f, 0.9f, 1.0f, 0.0f);
                desc.startSize = 0.01f;
                desc.endSize = 0.03f;
                desc.gravity = glm::vec3(0, 0, 0);
                break;
        }
        
        return ParticleSystem::create(desc);
    }
}

// ============================================================================
// AUDIO GENERATION
// ============================================================================

namespace AudioGen {
    AudioHandle load(const std::string& file, float vol, float pitchVar) {
        if (file.empty()) return 0;
        
        LOG_GYRO_GEN(LoadingAudio, file);
        
        AudioDesc desc;
        desc.filename = file;
        desc.volume = vol;
        desc.pitchVariance = pitchVar;
        desc.looping = false;
        
        return AudioSystem::load(desc);
    }
}

// ============================================================================
// COLLISION GENERATION
// ============================================================================

namespace CollisionGen {
    ColliderHandle buildGyroCollider(const CollisionParams& c) {
        LOG_GYRO_GEN(BuildingCollider, c.radius);
        
        if (!c.enableCollider) {
            return 0;
        }
        
        ColliderDesc desc;
        
        if (c.meshCollider) {
            desc.shape = CollisionShape::Mesh;
        } else {
            desc.shape = CollisionShape::Sphere;
        }
        
        desc.radius = c.radius;
        desc.triggerOnly = c.triggerOnly;
        desc.enableCCD = c.enableCCD;
        desc.material = CollisionMaterial::Projectile;
        
        return Collision::createCollider(desc);
    }
}

} // namespace GyroProjectiles
} // namespace MagiTech
