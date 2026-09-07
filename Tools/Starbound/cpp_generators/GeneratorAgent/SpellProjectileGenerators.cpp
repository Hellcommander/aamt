#include "SpellAssetFactory.hpp"
#include "core/Log.hpp"
#include <cmath>
#include <algorithm>

namespace MagiTech {
namespace SpellProjectiles {

#define LOG_SPELL_GEN(Action, Id) Log::info("SpellGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t SpellParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(SpellParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}
uint64_t TrailParams::hashKey() const { return XXH64(this, sizeof(TrailParams), 0); }
uint64_t VFXParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(VFXParams) - 2*sizeof(std::string));
    XXH64_update(&s, shaderTemplate.c_str(), shaderTemplate.length());
    for(const auto& d : defines) { XXH64_update(&s, d.c_str(), d.length()); }
    return XXH64_digest(&s);
}
uint64_t ParticleParams::hashKey() const { return XXH64(this, sizeof(ParticleParams), 0); }
uint64_t LightParams::hashKey() const { return XXH64(this, sizeof(LightParams), 0); }
uint64_t AudioParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(AudioParams) - sizeof(std::string));
    XXH64_update(&s, sfxFile.c_str(), sfxFile.length());
    return XXH64_digest(&s);
}
uint64_t CollisionParams::hashKey() const { return XXH64(this, sizeof(CollisionParams), 0); }

// Helper functions for geometry generation
namespace GeometryHelpers {
    // Generate sphere vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateSphere(float radius, int segments, int rings) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        for (int ring = 0; ring <= rings; ++ring) {
            float phi = ring * M_PI / rings;
            float y = radius * std::cos(phi);
            float ringRadius = radius * std::sin(phi);
            
            for (int segment = 0; segment <= segments; ++segment) {
                float theta = segment * 2 * M_PI / segments;
                float x = ringRadius * std::cos(theta);
                float z = ringRadius * std::sin(theta);
                vertices.emplace_back(x, y, z);
            }
        }
        
        // Generate indices for triangles
        for (int ring = 0; ring < rings; ++ring) {
            for (int segment = 0; segment < segments; ++segment) {
                uint32_t current = ring * (segments + 1) + segment;
                uint32_t next = current + segments + 1;
                
                indices.push_back(current);
                indices.push_back(next);
                indices.push_back(current + 1);
                
                indices.push_back(next);
                indices.push_back(next + 1);
                indices.push_back(current + 1);
            }
        }
        
        return {vertices, indices};
    }
    
    // Generate cone vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateCone(float baseRadius, float height, int segments) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        // Base center
        vertices.emplace_back(0, 0, 0);
        
        // Base ring
        for (int i = 0; i <= segments; ++i) {
            float angle = i * 2 * M_PI / segments;
            float x = baseRadius * std::cos(angle);
            float z = baseRadius * std::sin(angle);
            vertices.emplace_back(x, 0, z);
        }
        
        // Apex
        vertices.emplace_back(0, height, 0);
        
        // Generate indices
        // Base triangles
        for (int i = 1; i < segments; ++i) {
            indices.push_back(0);
            indices.push_back(i);
            indices.push_back(i + 1);
        }
        
        // Side triangles
        for (int i = 1; i <= segments; ++i) {
            indices.push_back(i);
            indices.push_back(vertices.size() - 1); // Apex
            indices.push_back(i == segments ? 1 : i + 1);
        }
        
        return {vertices, indices};
    }
    
    // Generate torus vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateTorus(float majorRadius, float minorRadius, int majorSegments, int minorSegments) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        for (int i = 0; i <= majorSegments; ++i) {
            float majorAngle = i * 2 * M_PI / majorSegments;
            float cosMajor = std::cos(majorAngle);
            float sinMajor = std::sin(majorAngle);
            
            for (int j = 0; j <= minorSegments; ++j) {
                float minorAngle = j * 2 * M_PI / minorSegments;
                float cosMinor = std::cos(minorAngle);
                float sinMinor = std::sin(minorAngle);
                
                float x = (majorRadius + minorRadius * cosMinor) * cosMajor;
                float y = (majorRadius + minorRadius * cosMinor) * sinMajor;
                float z = minorRadius * sinMinor;
                
                vertices.emplace_back(x, y, z);
            }
        }
        
        // Generate indices
        for (int i = 0; i < majorSegments; ++i) {
            for (int j = 0; j < minorSegments; ++j) {
                uint32_t current = i * (minorSegments + 1) + j;
                uint32_t next = current + minorSegments + 1;
                
                indices.push_back(current);
                indices.push_back(next);
                indices.push_back(current + 1);
                
                indices.push_back(next);
                indices.push_back(next + 1);
                indices.push_back(current + 1);
            }
        }
        
        return {vertices, indices};
    }
}

namespace GeometryGen {
    MeshHandle build(const SpellParams& s) {
        LOG_SPELL_GEN(BuildingGeometry, s.id);
        
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        switch (s.shape) {
            case SpellShape::Sphere: {
                auto [verts, inds] = GeometryHelpers::generateSphere(s.baseRadius, 16, 16);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Cone: {
                auto [verts, inds] = GeometryHelpers::generateCone(s.baseRadius, s.length, 16);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Torus: {
                auto [verts, inds] = GeometryHelpers::generateTorus(s.baseRadius, s.baseRadius * 0.3f, 16, 8);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Ribbon: {
                // Generate ribbon geometry (simplified)
                float width = s.baseRadius * 0.1f;
                float length = s.length;
                
                // Create a simple ribbon strip
                vertices = {
                    {-width, 0, 0}, {width, 0, 0},
                    {-width, 0, length}, {width, 0, length}
                };
                
                indices = {0, 1, 2, 1, 3, 2};
                break;
            }
            case SpellShape::CustomMesh:
            default:
                // Default to sphere
                auto [verts, inds] = GeometryHelpers::generateSphere(s.baseRadius, 16, 16);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
        }
        
        // Convert to mesh handle (simplified)
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace TrailGen {
    MeshHandle build(const TrailParams& t, const SpellParams& s) {
        if (!t.enableTrail) return 0;
        
        LOG_SPELL_GEN(BuildingTrail, s.id);
        
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        switch (t.mode) {
            case TrailMode::Ribbon: {
                // Generate ribbon trail
                int segments = static_cast<int>(t.trailLength * 10);
                float segmentLength = t.trailLength / segments;
                
                for (int i = 0; i <= segments; ++i) {
                    float t = static_cast<float>(i) / segments;
                    float alpha = 1.0f - t; // Fade from head to tail
                    
                    // Interpolate color
                    glm::vec4 color = glm::mix(t.headColor, t.tailColor, t);
                    
                    // Create ribbon strip
                    float width = t.width * alpha;
                    vertices.emplace_back(-width, 0, i * segmentLength);
                    vertices.emplace_back(width, 0, i * segmentLength);
                }
                
                // Generate indices for ribbon
                for (int i = 0; i < segments; ++i) {
                    uint32_t base = i * 2;
                    indices.push_back(base);
                    indices.push_back(base + 1);
                    indices.push_back(base + 2);
                    indices.push_back(base + 1);
                    indices.push_back(base + 3);
                    indices.push_back(base + 2);
                }
                break;
            }
            case TrailMode::SDFRibbon: {
                // Generate SDF-based ribbon (simplified)
                int segments = static_cast<int>(t.trailLength * 8);
                float segmentLength = t.trailLength / segments;
                
                for (int i = 0; i <= segments; ++i) {
                    float t = static_cast<float>(i) / segments;
                    float alpha = 1.0f - t;
                    
                    // Create SDF ribbon with more detail
                    float width = t.width * alpha;
                    for (int j = 0; j < 4; ++j) {
                        float angle = j * M_PI / 2;
                        float x = width * std::cos(angle);
                        float y = width * std::sin(angle);
                        vertices.emplace_back(x, y, i * segmentLength);
                    }
                }
                
                // Generate indices for SDF ribbon
                for (int i = 0; i < segments; ++i) {
                    uint32_t base = i * 4;
                    for (int j = 0; j < 4; ++j) {
                        uint32_t current = base + j;
                        uint32_t next = base + ((j + 1) % 4);
                        uint32_t nextRow = base + 4 + j;
                        uint32_t nextRowNext = base + 4 + ((j + 1) % 4);
                        
                        indices.push_back(current);
                        indices.push_back(next);
                        indices.push_back(nextRow);
                        
                        indices.push_back(next);
                        indices.push_back(nextRowNext);
                        indices.push_back(nextRow);
                    }
                }
                break;
            }
            case TrailMode::Particles:
            default:
                // Particle trail (simplified)
                int particleCount = static_cast<int>(t.trailLength * 20);
                for (int i = 0; i < particleCount; ++i) {
                    float t = static_cast<float>(i) / particleCount;
                    float alpha = 1.0f - t;
                    
                    // Random particle positions along trail
                    float x = (static_cast<float>(rand()) / RAND_MAX - 0.5f) * t.width * alpha;
                    float y = (static_cast<float>(rand()) / RAND_MAX - 0.5f) * t.width * alpha;
                    float z = t * t.trailLength;
                    
                    vertices.emplace_back(x, y, z);
                }
                break;
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace ShaderGen {
    ShaderHandle build(const VFXParams& v) {
        LOG_SPELL_GEN(BuildingShader, v.shaderTemplate);
        
        // Template-based shader generation
        std::string shaderSource = "// Generated VFX Shader\n";
        shaderSource += "// Template: " + v.shaderTemplate + "\n";
        shaderSource += "// Defines: ";
        for (const auto& define : v.defines) {
            shaderSource += define + " ";
        }
        shaderSource += "\n\n";
        
        // Add shader content based on defines
        for (const auto& define : v.defines) {
            if (define == "USE_NOISE") {
                shaderSource += "#define USE_NOISE\n";
                shaderSource += "uniform float uNoiseIntensity = " + std::to_string(v.noiseIntensity) + ";\n";
            }
            if (define == "ALPHA_PULSE") {
                shaderSource += "#define ALPHA_PULSE\n";
                shaderSource += "uniform float uPulseFreq = " + std::to_string(v.pulseFreq) + ";\n";
            }
        }
        
        // Add basic shader structure
        shaderSource += R"(
uniform float uTime;
uniform vec4 uColor = vec4(1.0, 1.0, 1.0, 1.0);

void main() {
    vec4 color = uColor;
    
    #ifdef USE_NOISE
    float noise = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
    color.rgb += noise * uNoiseIntensity;
    #endif
    
    #ifdef ALPHA_PULSE
    float pulse = 0.5 + 0.5 * sin(uTime * uPulseFreq);
    color.a *= pulse;
    #endif
    
    gl_FragColor = color;
}
)";
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace ParticleGen {
    ParticleHandle build(const ParticleParams& p) {
        LOG_SPELL_GEN(BuildingParticles, (int)p.style);
        
        // Particle system configuration
        switch (p.style) {
            case ParticleStyle::Sparks: {
                // Configure spark particles
                // High velocity, short lifetime, bright colors
                break;
            }
            case ParticleStyle::Smoke: {
                // Configure smoke particles
                // Low velocity, long lifetime, dark colors
                break;
            }
            case ParticleStyle::Ember: {
                // Configure ember particles
                // Medium velocity, medium lifetime, orange/red colors
                break;
            }
            case ParticleStyle::Cosmic: {
                // Configure cosmic particles
                // Variable velocity, long lifetime, purple/blue colors
                break;
            }
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace LightGen {
    LightHandle build(const LightParams& l) {
        LOG_SPELL_GEN(BuildingLight, l.intensity);
        
        // Light configuration
        switch (l.flickerMode) {
            case LightFlicker::None:
                // Static light
                break;
            case LightFlicker::Sinusoidal:
                // Sinusoidal flicker
                break;
            case LightFlicker::NoiseDriven:
                // Noise-based flicker
                break;
            case LightFlicker::Pulse:
                // Pulsing light
                break;
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace AudioGen {
    AudioHandle build(const AudioParams& a) {
        LOG_SPELL_GEN(BuildingAudio, a.sfxFile);
        
        // Audio configuration
        // - Load audio file
        // - Set volume
        // - Configure looping
        // - Set 3D positioning
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace CollisionGen {
    ColliderHandle build(const CollisionParams& c, const SpellParams& s) {
        LOG_SPELL_GEN(BuildingCollider, s.id);
        
        // Collision configuration
        if (c.meshCollider) {
            // Use mesh-based collision
        } else {
            // Use sphere collision with radius
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

} // namespace SpellProjectiles
} // namespace MagiTech
