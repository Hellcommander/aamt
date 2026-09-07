#include "GasGrenadeFactory.hpp"
#include "core/Log.hpp"
#include "core/graphics/Common.hpp" // For Mesh, Image, etc.
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace MagiTech {
namespace GasGrenades {

#define LOG_GEN(Asset, Id) Log::info("Building Gas Grenade {}: {}", #Asset, Id)

namespace MeshGen {
    MeshHandle buildGasGrenadeBody(const GasGrenadeParams& p) {
        LOG_GEN(Body Mesh, p.id);
        Graphics::Mesh bodyMesh;
        
        // Simplified sphere or cylinder generation
        int detail = p.seamSegments;
        if (p.bodyHeight > 0) { // Cylinder
            // ... cylinder generation logic
        } else { // Sphere
            // ... sphere generation logic
        }

        return Graphics::AssetRegistry::registerMesh(bodyMesh);
    }
} // namespace MeshGen

namespace TextureGen {
    TextureHandle buildGasGrenadeTexture(const GasGrenadeParams& p) {
        LOG_GEN(Body Texture, p.id);
        Graphics::Image image(128, 128);
        for(int y=0; y<128; ++y) {
            for(int x=0; x<128; ++x) {
                image.setPixel(x, y, glm::vec4(0.3f, 0.4f, 0.3f, 1.0f));
            }
        }
        return Graphics::AssetRegistry::registerTexture(image);
    }
} // namespace TextureGen

namespace ShaderGen {
    ShaderHandle buildGasCloudShader(const GasGrenadeParams& p) {
        LOG_GEN(Cloud Shader, p.id);
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
} // namespace ShaderGen

namespace ParticleGen {
    ParticleHandle buildGasCloud(const GasGrenadeParams& p) {
        LOG_GEN(Cloud Particles, p.id);
        static uint32_t nextParticleSystemId = 1;
        return nextParticleSystemId++;
    }
} // namespace ParticleGen

namespace PhysGen {
    PhysicsHandle buildGasPhysics(const GasGrenadeParams& p) {
        LOG_GEN(Physics, p.id);
        static uint32_t nextPhysicsHandle = 1;
        return nextPhysicsHandle++;
    }
} // namespace PhysGen

namespace AudioGen {
    AudioHandle buildGasHiss(const GasGrenadeParams& p) {
        LOG_GEN(Hiss Audio, p.id);
        // This would generate procedural audio data.
        static uint32_t nextAudioHandle = 1;
        return nextAudioHandle++;
    }
} // namespace AudioGen

namespace IconGen {
    TextureHandle buildGasIcon(const GasGrenadeParams& p, const UIParams& u) {
        LOG_GEN(UI Icon, p.id);
        Graphics::Image icon(u.iconSize, u.iconSize);
        glm::vec4 color;
        switch(p.cloudType) {
            case CloudType::Poison: color = glm::vec4(0.5, 1, 0.5, 1); break;
            case CloudType::TearGas: color = glm::vec4(1, 1, 0.5, 1); break;
            case CloudType::Corrosive: color = glm::vec4(1, 0.5, 0, 1); break;
            default: color = glm::vec4(0.8, 0.8, 0.8, 1); break;
        }
        
        for(int y=0; y<u.iconSize; ++y) {
            for(int x=0; x<u.iconSize; ++x) {
                icon.setPixel(x, y, color);
            }
        }
        
        return Graphics::AssetRegistry::registerTexture(icon);
    }
} // namespace IconGen

} // namespace GasGrenades
} // namespace MagiTech
