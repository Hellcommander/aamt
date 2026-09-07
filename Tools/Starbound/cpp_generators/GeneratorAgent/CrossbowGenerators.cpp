#include "CrossbowAssetFactory.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/Materials.hpp"
#include "core/physics/Collision.hpp"
#include "core/animation/Animation.hpp"
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>

namespace MagiTech {
namespace Crossbows {

#define LOG_CROSSBOW_GEN(Action, Id) Log::info("CrossbowGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t CrossbowParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(CrossbowParams) - 4 * sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, stockMaterial.c_str(), stockMaterial.length());
    XXH64_update(&s, limbMaterial.c_str(), limbMaterial.length());
    XXH64_update(&s, stringMaterial.c_str(), stringMaterial.length());
    return XXH64_digest(&s);
}

uint64_t BoltParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(BoltParams) - 2 * sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, fletchMaterial.c_str(), fletchMaterial.length());
    return XXH64_digest(&s);
}

uint64_t ArrowParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(ArrowParams) - 2 * sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, fletchStyle.c_str(), fletchStyle.length());
    return XXH64_digest(&s);
}

// Enhanced Generator Implementations
namespace BowGen {
    MeshHandle buildCrossbowMesh(const CrossbowParams& p) {
        LOG_CROSSBOW_GEN(BuildingCrossbowMesh, p.id);
        
        Mesh crossbowMesh;
        
        // Stock (main body) - rectangular prism with ergonomic curves
        float stockLength = p.drawLength * 2.5f;
        float stockWidth = p.drawWeight * 0.001f;
        float stockHeight = stockWidth * 0.6f;
        
        auto stock = Primitives::createBox(stockLength, stockHeight, stockWidth);
        crossbowMesh.append(stock);
        
        // Limbs (curved bow arms) - using spline-based curves
        float limbLength = p.drawLength * 1.8f;
        float limbThickness = p.drawWeight * 0.0005f;
        
        // Create curved limbs using multiple segments
        for (int i = 0; i < 8; ++i) {
            float t = i / 7.0f;
            float curve = sin(t * glm::pi<float>()) * 0.3f;
            
            auto limbSegment = Primitives::createCylinder(limbThickness, limbLength / 8.0f, 6);
            glm::mat4 transform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(limbLength * 0.5f, curve * limbLength, 0));
            transform = glm::rotate(transform, t * glm::pi<float>() * 0.5f, glm::vec3(0, 0, 1));
            crossbowMesh.append(limbSegment, transform);
        }
        
        // Trigger mechanism
        auto trigger = Primitives::createBox(stockWidth * 0.3f, stockHeight * 0.4f, stockWidth * 0.2f);
        glm::mat4 triggerTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(-stockLength * 0.3f, -stockHeight * 0.3f, 0));
        crossbowMesh.append(trigger, triggerTransform);
        
        // Sight rail
        auto sightRail = Primitives::createCylinder(stockWidth * 0.05f, stockLength * 0.8f, 8);
        glm::mat4 railTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, stockHeight * 0.4f, 0));
        railTransform = glm::rotate(railTransform, glm::pi<float>() * 0.5f, glm::vec3(0, 0, 1));
        crossbowMesh.append(sightRail, railTransform);
        
        crossbowMesh.optimize();
        return crossbowMesh.upload();
    }
}

namespace StringGen {
    MeshHandle buildString(float drawLength, const std::string& material) {
        LOG_CROSSBOW_GEN(BuildingString, material);
        
        Mesh stringMesh;
        
        // Main bowstring - thin cylinder with tension
        float stringLength = drawLength * 1.2f;
        float stringRadius = 0.002f;
        
        auto mainString = Primitives::createCylinder(stringRadius, stringLength, 8);
        stringMesh.append(mainString);
        
        // String loops at ends
        auto endLoop = Primitives::createTorus(stringRadius * 2.0f, stringRadius, 8, 6);
        glm::mat4 leftLoop = glm::translate(glm::mat4(1.0f), glm::vec3(-stringLength * 0.5f, 0, 0));
        glm::mat4 rightLoop = glm::translate(glm::mat4(1.0f), glm::vec3(stringLength * 0.5f, 0, 0));
        stringMesh.append(endLoop, leftLoop);
        stringMesh.append(endLoop, rightLoop);
        
        stringMesh.optimize();
        return stringMesh.upload();
    }
}

namespace AnimGen {
    AnimationHandle buildReload(bool autoReload, float reloadTime) {
        LOG_CROSSBOW_GEN(BuildingReloadAnim, reloadTime);
        
        Animation anim;
        anim.setDuration(reloadTime);
        
        if (autoReload) {
            // Auto-reload animation sequence
            anim.addKeyframe(0.0f, "draw_start", 0.0f);
            anim.addKeyframe(reloadTime * 0.3f, "draw_mid", 0.5f);
            anim.addKeyframe(reloadTime * 0.7f, "draw_full", 1.0f);
            anim.addKeyframe(reloadTime, "release", 0.0f);
        } else {
            // Manual reload - longer draw phase
            anim.addKeyframe(0.0f, "idle", 0.0f);
            anim.addKeyframe(reloadTime * 0.6f, "draw_manual", 1.0f);
            anim.addKeyframe(reloadTime, "ready", 0.0f);
        }
        
        return anim.upload();
    }
}

namespace MaterialGen {
    MaterialSet assignBowMaterials(const std::string& stockMat, const std::string& limbMat) {
        LOG_CROSSBOW_GEN(AssigningBowMaterials, stockMat);
        
        MaterialSet materials;
        
        // Stock material (wood, metal, etc.)
        MaterialHandle stockHandle = Materials::load(stockMat + "_diffuse");
        materials.materials.emplace_back("stock", stockHandle);
        
        // Limb material (fiberglass, carbon fiber, etc.)
        MaterialHandle limbHandle = Materials::load(limbMat + "_diffuse");
        materials.materials.emplace_back("limb", limbHandle);
        
        // Trigger material (metal)
        MaterialHandle triggerHandle = Materials::load("metal_steel_diffuse");
        materials.materials.emplace_back("trigger", triggerHandle);
        
        return materials;
    }
    
    MaterialHandle assignShaftMaterial(const std::string& id) {
        LOG_CROSSBOW_GEN(AssigningShaftMaterial, id);
        
        // Determine material based on projectile ID
        std::string materialName;
        if (id.find("steel") != std::string::npos) {
            materialName = "metal_steel_diffuse";
        } else if (id.find("wood") != std::string::npos) {
            materialName = "wood_oak_diffuse";
        } else if (id.find("carbon") != std::string::npos) {
            materialName = "carbon_fiber_diffuse";
        } else {
            materialName = "metal_aluminum_diffuse"; // default
        }
        
        return Materials::load(materialName);
    }
}

namespace BoltGen {
    MeshHandle buildBoltMesh(const BoltParams& p) {
        LOG_CROSSBOW_GEN(BuildingBoltMesh, p.id);
        
        Mesh boltMesh;
        
        // Main shaft (cylinder)
        auto shaft = Primitives::createCylinder(p.shaftRadius, p.length, 8);
        boltMesh.append(shaft);
        
        // Bolt tip (cone with optional barbs)
        float tipLength = p.length * 0.3f;
        auto tip = Primitives::createCone(p.shaftRadius * 1.2f, tipLength, 8);
        glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, p.length * 0.5f + tipLength * 0.5f, 0));
        boltMesh.append(tip, tipTransform);
        
        if (p.barbedTip) {
            // Add barbed edges to tip
            for (int i = 0; i < 4; ++i) {
                float angle = i * glm::pi<float>() * 0.5f;
                auto barb = Primitives::createCone(p.shaftRadius * 0.3f, tipLength * 0.4f, 4);
                glm::mat4 barbTransform = glm::translate(glm::mat4(1.0f), 
                    glm::vec3(0, p.length * 0.5f + tipLength * 0.3f, 0));
                barbTransform = glm::rotate(barbTransform, angle, glm::vec3(0, 1, 0));
                barbTransform = glm::rotate(barbTransform, glm::pi<float>() * 0.5f, glm::vec3(1, 0, 0));
                boltMesh.append(barb, barbTransform);
            }
        }
        
        // Fletching (if enabled)
        if (p.useFletching) {
            for (int i = 0; i < 3; ++i) {
                float angle = i * glm::pi<float>() * 2.0f / 3.0f;
                auto fletch = Primitives::createBox(p.fletchLength, p.shaftRadius * 2.0f, p.shaftRadius * 0.1f);
                glm::mat4 fletchTransform = glm::translate(glm::mat4(1.0f), 
                    glm::vec3(0, -p.length * 0.5f - p.fletchLength * 0.5f, 0));
                fletchTransform = glm::rotate(fletchTransform, angle, glm::vec3(0, 1, 0));
                boltMesh.append(fletch, fletchTransform);
            }
        }
        
        boltMesh.optimize();
        return boltMesh.upload();
    }
}

namespace ArrowGen {
    MeshHandle buildArrowMesh(const ArrowParams& p) {
        LOG_CROSSBOW_GEN(BuildingArrowMesh, p.id);
        
        Mesh arrowMesh;
        
        // Arrow shaft (longer, thinner than bolt)
        auto shaft = Primitives::createCylinder(p.shaftDiameter * 0.5f, p.shaftLength, 8);
        arrowMesh.append(shaft);
        
        // Arrow tip (narrower, longer than bolt)
        float tipLength = p.shaftLength * 0.25f;
        auto tip = Primitives::createCone(p.shaftDiameter * 0.8f, tipLength, 8);
        glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, p.shaftLength * 0.5f + tipLength * 0.5f, 0));
        arrowMesh.append(tip, tipTransform);
        
        // Nock (string attachment point)
        auto nock = Primitives::createTorus(p.nockSize, p.shaftDiameter * 0.2f, 8, 6);
        glm::mat4 nockTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, -p.shaftLength * 0.5f - p.nockSize, 0));
        arrowMesh.append(nock, nockTransform);
        
        // Fletching (more elaborate than bolt)
        if (p.useFletching) {
            int fletchCount = (p.fletchStyle == "Parabolic") ? 4 : 3;
            float fletchSize = (p.fletchStyle == "Shield") ? 1.5f : 1.0f;
            
            for (int i = 0; i < fletchCount; ++i) {
                float angle = i * glm::pi<float>() * 2.0f / fletchCount;
                auto fletch = Primitives::createBox(p.shaftLength * 0.15f, 
                    p.shaftDiameter * 2.0f * fletchSize, p.shaftDiameter * 0.05f);
                glm::mat4 fletchTransform = glm::translate(glm::mat4(1.0f), 
                    glm::vec3(0, -p.shaftLength * 0.3f, 0));
                fletchTransform = glm::rotate(fletchTransform, angle, glm::vec3(0, 1, 0));
                arrowMesh.append(fletch, fletchTransform);
            }
        }
        
        arrowMesh.optimize();
        return arrowMesh.upload();
    }
}

namespace VFXGen {
    MeshHandle buildTrail(const std::string& style, float intensity) {
        LOG_CROSSBOW_GEN(BuildingVFXTrail, style);
        
        Mesh trailMesh;
        
        if (style == "spark") {
            // Spark trail - particle system mesh
            for (int i = 0; i < 20; ++i) {
                auto spark = Primitives::createSphere(intensity * 0.01f, 4);
                glm::mat4 sparkTransform = glm::translate(glm::mat4(1.0f), 
                    glm::vec3(i * intensity * 0.02f, 0, 0));
                trailMesh.append(spark, sparkTransform);
            }
        } else if (style == "feather") {
            // Feather trail - ribbon-like mesh
            for (int i = 0; i < 10; ++i) {
                auto feather = Primitives::createQuad(intensity * 0.05f, intensity * 0.02f);
                glm::mat4 featherTransform = glm::translate(glm::mat4(1.0f), 
                    glm::vec3(i * intensity * 0.03f, 0, 0));
                featherTransform = glm::rotate(featherTransform, i * 0.1f, glm::vec3(0, 0, 1));
                trailMesh.append(feather, featherTransform);
            }
        }
        
        trailMesh.optimize();
        return trailMesh.upload();
    }
}

namespace ProjectileSim {
    SimulationHandle setupLinear(float length, float tipMass, float fletchLength) {
        LOG_CROSSBOW_GEN(SettingUpLinearSim, length);
        
        // Linear projectile simulation parameters
        SimulationParams params;
        params.dragCoefficient = 0.3f;
        params.gravityInfluence = 0.8f;
        params.maxDistance = 100.0f;
        params.tipMass = tipMass;
        params.fletchDrag = fletchLength * 0.1f;
        
        return Simulation::createLinearProjectile(params);
    }
    
    SimulationHandle setupFletched(float shaftLength, int spineRating, const std::string& fletchStyle) {
        LOG_CROSSBOW_GEN(SettingUpFletchedSim, shaftLength);
        
        // Fletched projectile simulation with stability
        SimulationParams params;
        params.dragCoefficient = 0.2f;
        params.gravityInfluence = 0.6f;
        params.maxDistance = 150.0f;
        params.spineRating = spineRating;
        params.fletchStability = (fletchStyle == "Parabolic") ? 1.2f : 1.0f;
        
        return Simulation::createFletchedProjectile(params);
    }
}

namespace CollisionGen {
    ColliderHandle buildCylinder(float radius, float height) {
        LOG_CROSSBOW_GEN(BuildingCylinderCollider, radius);
        
        ColliderDesc desc;
        desc.shape = CollisionShape::Capsule;
        desc.radius = radius;
        desc.height = height;
        desc.enableCCD = true;
        desc.material = CollisionMaterial::Projectile;
        
        return Collision::createCollider(desc);
    }
}

} // namespace Crossbows
} // namespace MagiTech
