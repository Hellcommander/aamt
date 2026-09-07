#include "ProjectileGenerators.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Primitives.hpp"
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>

namespace MagiTech {
namespace Projectiles {

namespace MeshGen {
    MeshHandle buildMesh(const ProjectileParams& p) {
        Log::info("Building projectile mesh for: {}", p.id);
        
        Mesh mesh;
        
        if (p.projType == "arrow") {
            // Arrow shaft (cylinder)
            auto shaft = Primitives::createCylinder(p.radius * 0.5f, p.length, p.shapeDetail * 8);
            mesh.append(shaft);
            
            // Arrow tip (cone)
            auto tip = Primitives::createCone(p.radius, p.length * 0.2f, p.shapeDetail * 8);
            glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, p.length * 0.5f + p.length * 0.1f, 0));
            mesh.append(tip, tipTransform);
            
            // Arrow fletching (small cones at base)
            auto fletching = Primitives::createCone(p.radius * 0.3f, p.length * 0.15f, p.shapeDetail * 4);
            glm::mat4 fletchTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, -p.length * 0.5f - p.length * 0.075f, 0));
            mesh.append(fletching, fletchTransform);
        }
        else if (p.projType == "fireball" || p.projType == "shard") {
            // Spherical projectile
            auto sphere = Primitives::createSphere(p.radius, p.shapeDetail * 16);
            mesh.append(sphere);
        }
        else if (p.projType == "laser") {
            // Thin rectangular beam
            auto beam = Primitives::createQuad(0.02f, p.length);
            glm::mat4 beamTransform = glm::rotate(glm::mat4(1.0f), 
                glm::radians(90.0f), glm::vec3(1, 0, 0));
            beamTransform = glm::translate(beamTransform, glm::vec3(0, 0, p.length * 0.5f));
            mesh.append(beam, beamTransform);
        }
        else if (p.projType == "bolt") {
            // Bolt with jagged edges
            auto bolt = Primitives::createCylinder(p.radius * 0.3f, p.length, p.shapeDetail * 6);
            mesh.append(bolt);
            
            // Add jagged tip
            auto jaggedTip = Primitives::createCone(p.radius * 0.4f, p.length * 0.3f, p.shapeDetail * 4);
            glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, p.length * 0.5f + p.length * 0.15f, 0));
            mesh.append(jaggedTip, tipTransform);
        }
        else if (p.projType == "bullet") {
            // Simple bullet shape
            auto bullet = Primitives::createCylinder(p.radius * 0.8f, p.length * 0.7f, p.shapeDetail * 8);
            mesh.append(bullet);
            
            // Bullet tip
            auto tip = Primitives::createCone(p.radius * 0.8f, p.length * 0.3f, p.shapeDetail * 8);
            glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, p.length * 0.5f + p.length * 0.15f, 0));
            mesh.append(tip, tipTransform);
        }
        
        mesh.optimize();
        return mesh.upload();
    }
}

namespace TextureGen {
    TextureHandle buildTexture(const ProjectileParams& p) {
        Log::info("Building projectile texture for: {}", p.id);
        
        int W = 128 << p.shapeDetail, H = W;
        std::vector<glm::u8vec4> pixels(W * H);
        
        // Simple gradient-based texture generation
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float u = x / (float)W, v = y / (float)H;
                
                // Radial gradient from center
                float d = glm::length(glm::vec2(u - 0.5f, v - 0.5f)) * 2.0f;
                d = glm::smoothstep(1.0f, 0.0f, d);
                
                // Add some noise variation
                float noise = (sin(u * 20.0f) * sin(v * 20.0f)) * 0.1f;
                
                glm::vec3 col = glm::mix(p.colorEdge, p.colorCore, d) + noise;
                col = glm::clamp(col, 0.0f, 1.0f);
                
                pixels[y * W + x] = glm::u8vec4(
                    static_cast<uint8_t>(col.r * 255),
                    static_cast<uint8_t>(col.g * 255),
                    static_cast<uint8_t>(col.b * 255),
                    255
                );
            }
        }
        
        return Texture::upload(W, H, pixels.data());
    }
}

namespace ShaderGen {
    ShaderHandle buildShader(const ProjectileParams& p) {
        Log::info("Building projectile shader for: {}", p.id);
        
        Shader s;
        s.addStage("vertex", "projectile.vert");
        s.addStage("fragment", "projectile.frag");
        
        s.setUniform("uCoreCol", p.colorCore);
        s.setUniform("uEdgeCol", p.colorEdge);
        s.addDefine("SHAPE_DETAIL", std::to_string(p.shapeDetail));
        
        if (p.projType == "laser") {
            s.addDefine("USE_ADDITIVE");
        }
        
        if (p.projType == "fireball") {
            s.addDefine("USE_EMISSION");
        }
        
        return s.compile();
    }
}

namespace EffectsGen {
    EffectHandle buildTrail(const ProjectileParams& p) {
        Log::info("Building projectile trail effect for: {}", p.id);
        
        if (p.trailEffect.empty()) {
            return 0; // No trail effect
        }
        
        Effect e;
        e.addParticleSystem(p.trailEffect, {
            {"duration", p.trailLength},
            {"colorCore", p.colorCore},
            {"colorEdge", p.colorEdge},
            {"speed", p.speed}
        });
        
        return e.upload();
    }
    
    EffectHandle buildImpact(const ProjectileParams& p) {
        Log::info("Building projectile impact effect for: {}", p.id);
        
        if (p.impactEffect.empty()) {
            return 0; // No impact effect
        }
        
        Effect e;
        e.addParticleSystem(p.impactEffect, {
            {"damageType", p.damageType},
            {"fragmentCount", p.fragmentationCount},
            {"colorCore", p.colorCore},
            {"colorEdge", p.colorEdge}
        });
        
        return e.upload();
    }
}

} // namespace Projectiles
} // namespace MagiTech
