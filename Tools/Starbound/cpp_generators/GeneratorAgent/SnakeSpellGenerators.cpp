#include "SnakeSpellFactory.hpp"
#include "core/Log.hpp"
#include <cmath>
#include <algorithm>

namespace MagiTech {
namespace SnakeSpells {

#define LOG_SNAKE_GEN(Action, Id) Log::info("SnakeSpellGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t SnakeBodyParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(SnakeBodyParams) - sizeof(std::string));
    XXH64_update(&s, scaleMaterial.c_str(), scaleMaterial.length());
    return XXH64_digest(&s);
}
uint64_t MotionParams::hashKey() const { return XXH64(this, sizeof(MotionParams), 0); }
uint64_t ScaleVFXParams::hashKey() const { return XXH64(this, sizeof(ScaleVFXParams), 0); }
uint64_t ParticleParams::hashKey() const { return XXH64(this, sizeof(ParticleParams), 0); }
uint64_t AudioParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(AudioParams) - 2 * sizeof(std::string));
    XXH64_update(&s, hissFile.c_str(), hissFile.length());
    XXH64_update(&s, rattleFile.c_str(), rattleFile.length());
    return XXH64_digest(&s);
}
uint64_t CollisionParams::hashKey() const { return XXH64(this, sizeof(CollisionParams), 0); }

// Helper functions for spline generation
namespace SplineHelpers {
    // Generate a 3D spline with control points
    std::vector<glm::vec3> generateSpline(float length, int segments, bool dynamicMorph) {
        std::vector<glm::vec3> controlPoints;
        
        // Create a smooth spline path
        for (int i = 0; i <= segments; ++i) {
            float t = static_cast<float>(i) / segments;
            float x = t * length;
            float y = 0.0f; // Base path is straight
            float z = 0.0f;
            
            // Add some natural curve if dynamic morphing is enabled
            if (dynamicMorph) {
                y = 0.1f * std::sin(t * M_PI * 2) * length * 0.1f;
                z = 0.05f * std::cos(t * M_PI * 3) * length * 0.1f;
            }
            
            controlPoints.emplace_back(x, y, z);
        }
        
        return controlPoints;
    }
    
    // Generate cylindrical segments along the spline
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateCylindricalSegments(
        const std::vector<glm::vec3>& splinePoints, float radius, int segments, int radialSegments) {
        
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        
        for (int i = 0; i < segments; ++i) {
            glm::vec3 current = splinePoints[i];
            glm::vec3 next = splinePoints[i + 1];
            glm::vec3 direction = glm::normalize(next - current);
            
            // Create a coordinate system for the segment
            glm::vec3 up = glm::vec3(0, 1, 0);
            if (std::abs(glm::dot(direction, up)) > 0.9f) {
                up = glm::vec3(1, 0, 0);
            }
            glm::vec3 right = glm::normalize(glm::cross(direction, up));
            up = glm::normalize(glm::cross(right, direction));
            
            // Generate vertices for this segment
            for (int j = 0; j <= radialSegments; ++j) {
                float angle = j * 2 * M_PI / radialSegments;
                glm::vec3 offset = right * std::cos(angle) * radius + up * std::sin(angle) * radius;
                vertices.push_back(current + offset);
            }
        }
        
        // Generate indices for the cylindrical mesh
        for (int i = 0; i < segments - 1; ++i) {
            for (int j = 0; j < radialSegments; ++j) {
                uint32_t current = i * (radialSegments + 1) + j;
                uint32_t next = current + 1;
                uint32_t nextRing = (i + 1) * (radialSegments + 1) + j;
                uint32_t nextRingNext = nextRing + 1;
                
                // First triangle
                indices.push_back(current);
                indices.push_back(nextRing);
                indices.push_back(next);
                
                // Second triangle
                indices.push_back(next);
                indices.push_back(nextRing);
                indices.push_back(nextRingNext);
            }
        }
        
        return {vertices, indices};
    }
}

namespace SnakeMeshGen {
    MeshHandle buildSplineMesh(const SnakeBodyParams& b) {
        LOG_SNAKE_GEN(BuildingSplineMesh, b.scaleMaterial);
        
        // Generate spline control points
        auto splinePoints = SplineHelpers::generateSpline(b.totalLength, b.segmentCount, b.dynamicMorph);
        
        // Generate cylindrical segments along the spline
        int radialSegments = 8; // Number of vertices around each segment
        auto [vertices, indices] = SplineHelpers::generateCylindricalSegments(
            splinePoints, b.segmentRadius, b.segmentCount, radialSegments);
        
        // Apply scale material UV mapping
        // UV coordinates would be generated here based on the scale material
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace MotionSim {
    SimulationHandle setupSnake(const SnakeBodyParams& b, const MotionParams& m) {
        LOG_SNAKE_GEN(SettingUpMotionSim, b.segmentCount);
        
        // Setup serpentine motion simulation
        if (m.curlEnabled) {
            // Configure curling motion
            // - Frequency: m.curlFrequency waves per second
            // - Amplitude: m.curlAmplitude lateral offset
            // - Phase: varies per segment for natural motion
        }
        
        if (m.homing) {
            // Configure homing behavior
            // - Turn rate: m.homingTurnRate degrees per second
            // - Target tracking enabled
        }
        
        // Combine curling and homing for slithering motion
        // Each segment follows the previous with slight delay
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace ScaleVFXGen {
    MaterialSetup setup(int segments, const ScaleVFXParams& v) {
        LOG_SNAKE_GEN(SettingUpScaleVFX, v.glowColor.r);
        
        // Create emissive material for scales
        if (v.enableGlow) {
            // Set up emissive properties
            // - Color: v.glowColor
            // - Intensity: v.glowIntensity
            
            if (v.pulsate) {
                // Animate emissive strength
                // - Frequency: v.pulsateSpeed cycles per second
                // - Use sine wave for smooth pulsing
            }
        }
        
        // Apply scale texture and normal mapping
        // Generate UV coordinates for scale pattern
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace ParticleGen {
    ParticleHandle buildVenomAndSmoke(const ParticleParams& p) {
        LOG_SNAKE_GEN(BuildingParticles, p.venomColor.r);
        
        if (p.venomDrip) {
            // Setup venom drip particles
            // - Spawn rate: p.dripRate droplets per second
            // - Color: p.venomColor
            // - Physics: gravity, collision with ground
            // - Emitter: capsule head position
        }
        
        if (p.smokeTrail) {
            // Setup smoke trail particles
            // - Density: p.smokeDensity
            // - Color: gray/black smoke
            // - Emitter: ribbon following spline tail
            // - Physics: upward drift, fade over time
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace AudioGen {
    AudioBundle loadSnakeAudio(const AudioParams& a) {
        LOG_SNAKE_GEN(LoadingAudio, a.hissFile);
        
        // Load and configure snake audio
        if (a.hissOnLaunch) {
            // Load hiss sound effect
            // - File: a.hissFile
            // - Volume: a.hissVolume
            // - Play on spell spawn
        }
        
        if (a.rattleOnImpact) {
            // Load rattle sound effect
            // - File: a.rattleFile
            // - Volume: 1.0 (full volume for impact)
            // - Play on collision
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

namespace CollisionGen {
    ColliderHandle buildCapsuleChain(int segments, const CollisionParams& c, float segmentLength) {
        LOG_SNAKE_GEN(BuildingCapsuleChain, segments);
        
        // Create capsule chain collision
        for (int i = 0; i < segments; ++i) {
            // Create capsule for each segment
            // - Radius: c.capsuleRadius
            // - Length: segmentLength
            // - Position: along spline path
            // - Orientation: aligned with spline direction
        }
        
        // Enable continuous collision detection if requested
        if (c.enableCCD) {
            // Configure CCD for fast-moving snake
            // - Sweep testing for high-speed projectiles
            // - Collision prediction for smooth motion
        }
        
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
}

} // namespace SnakeSpells
} // namespace MagiTech
