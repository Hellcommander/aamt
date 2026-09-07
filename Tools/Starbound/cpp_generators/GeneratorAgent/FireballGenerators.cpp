#include "FireballFactory.hpp"
#include "core/Log.hpp"
#include "core/graphics/Common.hpp" // For Mesh, Image, etc.
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace MagiTech {
namespace Fireballs {

#define LOG_GEN(Asset, Id) Log::info("Building Fireball {}: {}", #Asset, Id)

namespace MeshGen {
    MeshHandle buildCore(const FireballParams& p) {
        LOG_GEN(Core Mesh, p.id);
        Graphics::Mesh coreMesh;
        
        // Basic UV sphere generation
        for(int i = 0; i <= p.coreLatitudeSegs; i++) {
            for(int j = 0; j <= p.coreLongitudeSegs; j++) {
                float theta = i * M_PI / p.coreLatitudeSegs;
                float phi = j * 2 * M_PI / p.coreLongitudeSegs;
                float x = p.coreRadius * sin(theta) * cos(phi);
                float y = p.coreRadius * cos(theta);
                float z = p.coreRadius * sin(theta) * sin(phi);
                coreMesh.vertices.push_back({{x,y,z}, {(float)j/p.coreLongitudeSegs, (float)i/p.coreLatitudeSegs}, {1,1,0,1}});
            }
        }
        return Graphics::AssetRegistry::registerMesh(coreMesh);
    }
    
    MeshHandle buildFlames(const FireballParams& p) {
        LOG_GEN(Flames Mesh, p.id);
        // This would be another mesh, likely larger and more distorted than the core
        Graphics::Mesh flameMesh;
        return Graphics::AssetRegistry::registerMesh(flameMesh);
    }
} // namespace MeshGen

namespace ParticleGen {
    ParticleSystemHandle buildEmbers(const FireballParams& p) {
        LOG_GEN(Ember Particles, p.id);
        static uint32_t nextParticleSystemId = 1;
        return nextParticleSystemId++;
    }
    ParticleSystemHandle buildSmokeTrail(const FireballParams& p) {
        LOG_GEN(Smoke Trail, p.id);
        static uint32_t nextParticleSystemId = 1;
        return nextParticleSystemId++;
    }
} // namespace ParticleGen

namespace ShaderGen {
    ShaderHandle buildFireShader(const FireballParams& p) {
        LOG_GEN(Fire Shader, p.id);
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
} // namespace ShaderGen

namespace DecalGen {
    DecalHandle buildScorchMark(const FireballParams& p) {
        LOG_GEN(Scorch Decal, p.id);
        // This would generate a texture for the scorch mark decal
        static uint32_t nextDecalId = 1;
        return nextDecalId++;
    }
} // namespace DecalGen

namespace PhysGen {
    PhysicsHandle buildBehavior(const FireballParams& p) {
        LOG_GEN(Physics Behavior, p.id);
        static uint32_t nextPhysicsHandle = 1;
        return nextPhysicsHandle++;
    }
} // namespace PhysGen

} // namespace Fireballs
} // namespace MagiTech
