#include "DroneMinionFactory.hpp"
#include "core/Log.hpp"
#include "core/graphics/Common.hpp" // For Mesh, Image, etc.
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace MagiTech {
namespace DroneMinions {

#define LOG_GEN(Asset, Id) Log::info("Building Drone Minion {}: {}", #Asset, Id)

namespace MeshGen {
    MeshHandle buildDroneBody(const DroneMinionParams& p) {
        LOG_GEN(Body Mesh, p.id);
        Graphics::Mesh bodyMesh;
        
        // Simple cylinder for the body
        int detail = p.bodyDetail;
        for (int i = 0; i < detail; ++i) {
            float angle1 = 2.0f * M_PI * i / detail;
            float angle2 = 2.0f * M_PI * (i + 1) / detail;
            
            // Top circle
            bodyMesh.vertices.push_back({{p.bodyRadius * cos(angle1), p.bodyHeight/2, p.bodyRadius * sin(angle1)}, {0,0}, p.bodyColorPrimary});
            bodyMesh.vertices.push_back({{p.bodyRadius * cos(angle2), p.bodyHeight/2, p.bodyRadius * sin(angle2)}, {0,0}, p.bodyColorPrimary});
            bodyMesh.vertices.push_back({{0, p.bodyHeight/2, 0}, {0,0}, p.bodyColorPrimary});
            
            // Bottom circle
            bodyMesh.vertices.push_back({{p.bodyRadius * cos(angle1), -p.bodyHeight/2, p.bodyRadius * sin(angle1)}, {0,0}, p.bodyColorPrimary});
            bodyMesh.vertices.push_back({{p.bodyRadius * cos(angle2), -p.bodyHeight/2, p.bodyRadius * sin(angle2)}, {0,0}, p.bodyColorPrimary});
            bodyMesh.vertices.push_back({{0, -p.bodyHeight/2, 0}, {0,0}, p.bodyColorPrimary});
        }
        
        // This is a very simplified mesh generation. A real implementation would be more complex.
        return Graphics::AssetRegistry::registerMesh(bodyMesh);
    }

    MeshHandle buildDroneRotors(const DroneMinionParams& p) {
        LOG_GEN(Rotor Mesh, p.id);
        Graphics::Mesh rotorMesh;
        
        for (int i = 0; i < p.rotorCount; ++i) {
            float angle = 2.0f * M_PI * i / p.rotorCount;
            // Create a simple quad for each rotor blade
        }
        
        return Graphics::AssetRegistry::registerMesh(rotorMesh);
    }
} // namespace MeshGen

namespace TextureGen {
    TextureHandle buildDroneTexture(const DroneMinionParams& p) {
        LOG_GEN(Body Texture, p.id);
        Graphics::Image image(256, 256);
        for(int y=0; y<256; ++y) {
            for(int x=0; x<256; ++x) {
                image.setPixel(x, y, (x % 32 < 16) ? p.bodyColorPrimary : p.bodyColorSecondary);
            }
        }
        return Graphics::AssetRegistry::registerTexture(image);
    }
} // namespace TextureGen

namespace ShaderGen {
    ShaderHandle buildDroneShader(const DroneMinionParams& p) {
        LOG_GEN(Body Shader, p.id);
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
} // namespace ShaderGen

namespace ParticleGen {
    ParticleHandle buildThruster(const DroneMinionParams& p) {
        LOG_GEN(Thruster VFX, p.id);
        static uint32_t nextParticleSystemId = 1;
        return p.enableThrusterFX ? nextParticleSystemId++ : 0;
    }
    ParticleHandle buildJointSparks(const DroneMinionParams& p) {
        LOG_GEN(Joint Sparks, p.id);
        static uint32_t nextParticleSystemId = 1;
        return (p.sparkCount > 0) ? nextParticleSystemId++ : 0;
    }
} // namespace ParticleGen

namespace PhysGen {
    PhysicsHandle buildFlightModel(const DroneMinionParams& p) {
        LOG_GEN(Flight Physics, p.id);
        // This would create a physics body with the specified properties
        static uint32_t nextPhysicsHandle = 1;
        return nextPhysicsHandle++;
    }
} // namespace PhysGen

namespace AIGen {
    AIHandle buildDroneAI(const DroneMinionParams& p) {
        LOG_GEN(AI Controller, p.id);
        // This would create a behavior tree or state machine for the drone's AI
        static uint32_t nextAIHandle = 1;
        return nextAIHandle++;
    }
} // namespace AIGen

namespace IconGen {
    TextureHandle buildDroneIcon(const DroneMinionParams& p) {
        LOG_GEN(UI Icon, p.id);
        Graphics::Image icon(64, 64);
        // Simple icon generation
        for (int y = 24; y < 40; ++y) {
            for (int x = 24; x < 40; ++x) {
                icon.setPixel(x, y, p.bodyColorPrimary);
            }
        }
        return Graphics::AssetRegistry::registerTexture(icon);
    }
} // namespace IconGen

} // namespace DroneMinions
} // namespace MagiTech
